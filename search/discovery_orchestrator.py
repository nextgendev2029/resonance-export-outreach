"""
Discovery Orchestrator for Resonance - Export Outreach & Lead Operations.
Orchestrates multi-source buyer discovery, executes providers independently with
fault-isolation, performs cross-source deduplication and provenance merging,
evaluates US targeting, and persists run history in discovery_runs.json.
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from config import DISCOVERY_RUNS_FILE
from search.models import DiscoveryProfile, DiscoveryRunRecord, ProviderSearchResult
from search.provider_registry import ProviderRegistry
from app_logging.activity_logger import ActivityLogger


class DiscoveryOrchestrator:
    """Master orchestrator for Phase 6 US Home Decor Buyer Discovery."""

    def __init__(self, logger: Optional[ActivityLogger] = None, registry: Optional[ProviderRegistry] = None):
        self.logger = logger or ActivityLogger()
        self.registry = registry or ProviderRegistry()
        self._ensure_runs_file()

    def _ensure_runs_file(self):
        """Ensure discovery_runs.json exists."""
        if not DISCOVERY_RUNS_FILE.exists():
            with open(DISCOVERY_RUNS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_run_history(self) -> List[Dict[str, Any]]:
        """Return all historical discovery runs, newest first."""
        self._ensure_runs_file()
        try:
            with open(DISCOVERY_RUNS_FILE, "r", encoding="utf-8") as f:
                runs = json.load(f)
                return sorted(runs, key=lambda x: x.get("start_time", x.get("timestamp", "")), reverse=True)
        except Exception:
            return []

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a specific discovery run by ID."""
        runs = self.get_run_history()
        for r in runs:
            if r.get("run_id") == run_id:
                return r
        return None

    def _save_run_record(self, run_record: Dict[str, Any]):
        """Persist or update run record in discovery_runs.json."""
        self._ensure_runs_file()
        try:
            with open(DISCOVERY_RUNS_FILE, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception:
            runs = []

        existing_idx = next((i for i, r in enumerate(runs) if r.get("run_id") == run_record["run_id"]), -1)
        if existing_idx >= 0:
            runs[existing_idx] = run_record
        else:
            runs.append(run_record)

        with open(DISCOVERY_RUNS_FILE, "w", encoding="utf-8") as f:
            json.dump(runs, f, indent=2)

    @staticmethod
    def _make_company_domain_fingerprint(company: str, website: str) -> str:
        """Create a fingerprint for deduplicating companies across multiple providers."""
        clean_comp = "".join(filter(str.isalnum, (company or "").lower()))
        clean_domain = ""
        if website:
            try:
                parsed = urlparse(website if "://" in website else f"http://{website}")
                clean_domain = parsed.netloc.lower().replace("www.", "")
            except Exception:
                clean_domain = website.lower()
        return f"{clean_comp}:{clean_domain}"

    def deduplicate_and_merge_provenance(
        self,
        raw_records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Merge records identified by multiple providers into unified buyer leads with provenance.
        Deduplicates by:
        1. Email address
        2. Normalized company name + domain fingerprint
        Returns: (merged_records, duplicate_count)
        """
        merged_by_email: Dict[str, Dict[str, Any]] = {}
        merged_by_fp: Dict[str, Dict[str, Any]] = {}
        duplicate_count = 0

        for rec in raw_records:
            email = (rec.get("email") or "").strip().lower()
            company = (rec.get("company_name") or "").strip()
            website = (rec.get("website") or "").strip()
            source = rec.get("source") or rec.get("source_platform") or "Web Search"
            fp = self._make_company_domain_fingerprint(company, website)

            existing = None
            if email and email in merged_by_email:
                existing = merged_by_email[email]
            elif fp != ":" and fp in merged_by_fp:
                existing = merged_by_fp[fp]

            if existing:
                duplicate_count += 1
                # Merge provenance
                prov = existing.get("provenance") or [existing.get("source_platform", "")]
                if source not in prov:
                    prov.append(source)
                existing["provenance"] = prov
                existing["source_platform"] = ", ".join(prov)

                # Merge phone, state, city if newly found
                if not existing.get("phone") and rec.get("phone"):
                    existing["phone"] = rec.get("phone")
                if not existing.get("state") and rec.get("state"):
                    existing["state"] = rec.get("state")
                if not existing.get("city") and rec.get("city"):
                    existing["city"] = rec.get("city")
                if not existing.get("email") and email:
                    existing["email"] = email
                    existing["validation_status"] = rec.get("validation_status", "Valid")
                    existing["email_status"] = existing["validation_status"]
                    merged_by_email[email] = existing
            else:
                record_copy = dict(rec)
                record_copy["provenance"] = [source]
                record_copy["source_platform"] = source
                if email:
                    merged_by_email[email] = record_copy
                if fp != ":":
                    merged_by_fp[fp] = record_copy

        # Combine all unique records
        seen_ids = set()
        final_records = []
        for r in list(merged_by_email.values()) + list(merged_by_fp.values()):
            lid = r.get("lead_id")
            if lid and lid not in seen_ids:
                seen_ids.add(lid)
                final_records.append(r)

        return final_records, duplicate_count

    def execute_discovery(
        self,
        profile: DiscoveryProfile,
        enabled_sources: Optional[List[str]] = None,
        max_results_per_source: int = 5,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute full multi-source buyer discovery for the specified profile.
        Executes providers independently, merges results, evaluates US targeting,
        deduplicates against existing buyers, and persists telemetry.
        """
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        start_time = time.time()
        start_iso = datetime.utcnow().isoformat() + "Z"

        all_providers = self.registry.list_providers()
        sources_to_run = enabled_sources if enabled_sources is not None else [p.provider_id for p in all_providers]
        selected_providers = [p for p in all_providers if p.provider_id in sources_to_run]

        run_record = {
            "run_id": run_id,
            "timestamp": start_iso,
            "start_time": start_iso,
            "profile": profile.model_dump() if hasattr(profile, "model_dump") else profile.dict(),
            "keyword": f"{profile.product_name} ({profile.product_category})",
            "qualifiers": profile.buyer_types or [],
            "sources_used": [p.provider_name for p in selected_providers],
            "queries": [],
            "raw_result_count": 0,
            "extracted_lead_count": 0,
            "valid_email_count": 0,
            "us_match_count": 0,
            "duplicate_count": 0,
            "new_leads_added": 0,
            "status": "running",
            "duration_seconds": 0.0,
            "sources_status": {},
            "errors": []
        }
        self._save_run_record(run_record)

        all_raw_records = []
        total_raw = 0
        executed_queries = []
        total_sources = len(selected_providers) or 1

        for idx, provider in enumerate(selected_providers):
            if progress_callback:
                progress_callback(
                    current_source=provider.provider_name,
                    progress_pct=int((idx / total_sources) * 75) + 5,
                    status_message=f"Querying {provider.provider_name} for US {profile.product_name} buyers..."
                )

            try:
                search_res: ProviderSearchResult = provider.search(
                    profile=profile,
                    max_results=max_results_per_source,
                    run_id=run_id
                )
                if search_res.query_sent and search_res.query_sent not in executed_queries:
                    executed_queries.append(search_res.query_sent)

                raw_count = search_res.raw_results_count
                recs = search_res.records
                total_raw += raw_count
                all_raw_records.extend(recs)

                run_record["sources_status"][provider.provider_id] = {
                    "source_name": provider.provider_name,
                    "status": search_res.status,
                    "raw_count": raw_count,
                    "records_extracted": len(recs),
                    "query": search_res.query_sent,
                    "error": search_res.error
                }
                if search_res.error and search_res.status in ("failed", "error"):
                    run_record["errors"].append(f"{provider.provider_name}: {search_res.error}")
            except Exception as e:
                err_msg = str(e)
                run_record["sources_status"][provider.provider_id] = {
                    "source_name": provider.provider_name,
                    "status": "failed",
                    "raw_count": 0,
                    "records_extracted": 0,
                    "query": "",
                    "error": err_msg
                }
                run_record["errors"].append(f"{provider.provider_name}: {err_msg}")

        # Cross-provider deduplication & provenance merging
        if progress_callback:
            progress_callback(
                current_source="Normalization",
                progress_pct=80,
                status_message="Merging multi-source provenance and resolving duplicates..."
            )

        merged_records, cross_provider_dups = self.deduplicate_and_merge_provenance(all_raw_records)

        # Count US matches
        us_matches = sum(1 for r in merged_records if str(r.get("country_match", "")).lower() == "true")
        valid_emails = sum(1 for r in merged_records if r.get("validation_status") == "Valid")

        # Database deduplication & persistence
        if progress_callback:
            progress_callback(
                current_source="Database",
                progress_pct=90,
                status_message="Deduplicating leads against buyers.csv and persisting..."
            )

        # Ingest into buyers.csv with real dataset flag
        for r in merged_records:
            r["is_demo"] = False
            r["discovery_run_id"] = run_id

        ingest_res = self.logger.append_buyers_detailed(merged_records)
        new_added = ingest_res["newly_added"]
        db_duplicates = ingest_res["duplicates_skipped"]
        total_duplicates = cross_provider_dups + db_duplicates

        duration = round(time.time() - start_time, 2)
        end_iso = datetime.utcnow().isoformat() + "Z"

        run_record.update({
            "end_time": end_iso,
            "queries": executed_queries,
            "raw_result_count": total_raw,
            "extracted_lead_count": len(merged_records),
            "us_match_count": us_matches,
            "valid_email_count": valid_emails,
            "duplicate_count": total_duplicates,
            "new_leads_added": new_added,
            "created_lead_ids": [r.get("lead_id", "") for r in merged_records],
            "status": "completed",
            "duration_seconds": duration,
        })
        self._save_run_record(run_record)

        if progress_callback:
            progress_callback(
                current_source="Complete",
                progress_pct=100,
                status_message=(
                    f"Discovery completed in {duration}s: {len(merged_records)} unique US buyers extracted "
                    f"({new_added} new leads ingested, {total_duplicates} duplicates skipped)."
                )
            )

        return {
            "run_id": run_id,
            "status": "completed",
            "profile": profile.model_dump() if hasattr(profile, "model_dump") else profile.dict(),
            "raw_result_count": total_raw,
            "extracted_lead_count": len(merged_records),
            "us_match_count": us_matches,
            "valid_email_count": valid_emails,
            "duplicate_count": total_duplicates,
            "new_leads_added": new_added,
            "duration_seconds": duration,
            "sources_status": run_record["sources_status"],
            "queries": executed_queries,
            "errors": run_record["errors"],
            "discovered_leads": merged_records
        }
