"""
Activity Logger Module for Resonance.
Single point of truth for CSV operations with dual-key deduplication,
lead CRUD, demo/real lead separation, and comprehensive telemetry.
"""

import csv
import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Set, Optional, Tuple, Any

import json
from config import (
    BUYERS_CSV,
    SENT_LOG_CSV,
    BUSINESS_EMAILS_CSV,
    INDIVIDUAL_EMAILS_CSV,
    BUYER_COLUMNS,
    SENT_LOG_COLUMNS,
    LEAD_ENRICHMENT_FILE
)


class ActivityLogger:
    def __init__(self):
        self._ensure_files()
        self._migrate_existing_schema_and_mark_demo()

    def _ensure_files(self):
        """Ensure all required CSV files exist with appropriate headers."""
        if not BUYERS_CSV.exists():
            with open(BUYERS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(BUYER_COLUMNS)

        if not SENT_LOG_CSV.exists():
            with open(SENT_LOG_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(SENT_LOG_COLUMNS)

        if not BUSINESS_EMAILS_CSV.exists():
            with open(BUSINESS_EMAILS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["email", "buyer_name", "company_name", "classified_date"])

        if not INDIVIDUAL_EMAILS_CSV.exists():
            with open(INDIVIDUAL_EMAILS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["email", "buyer_name", "company_name", "classified_date"])

    def _migrate_existing_schema_and_mark_demo(self):
        """
        Migrate buyers.csv to support new columns (lead_id, source_url, is_demo, discovery_run_id, notes).
        Clearly flags pre-existing seed records as demo data (is_demo=true).
        """
        if not BUYERS_CSV.exists():
            return

        rows = []
        try:
            with open(BUYERS_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                needs_migration = not all(col in fieldnames for col in ("lead_id", "is_demo", "source_url"))

                for r in reader:
                    # If record lacks lead_id or is_demo, migrate it
                    row = dict(r)
                    if not row.get("lead_id"):
                        row["lead_id"] = f"lead_{uuid.uuid4().hex[:10]}"
                    if "is_demo" not in row or not row.get("is_demo"):
                        # Pre-existing records are demo seed data
                        row["is_demo"] = "true"
                        if not row.get("notes"):
                            row["notes"] = "Seeded sample contact for UI evaluation. Excluded from real outreach campaigns."
                    if not row.get("discovery_run_id"):
                        row["discovery_run_id"] = "demo_seed_dataset"
                    if not row.get("source_url"):
                        row["source_url"] = row.get("website", "")
                    if not row.get("notes"):
                        row["notes"] = ""
                    rows.append(row)

            if needs_migration and rows:
                with open(BUYERS_CSV, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=BUYER_COLUMNS)
                    writer.writeheader()
                    for row in rows:
                        clean_row = {k: row.get(k, "") for k in BUYER_COLUMNS}
                        writer.writerow(clean_row)
        except Exception:
            pass

    def get_lead_enrichments(self) -> Dict[str, Dict[str, Any]]:
        """Load enrichment data from data/lead_enrichment.json."""
        if not LEAD_ENRICHMENT_FILE.exists():
            return {}
        try:
            with open(LEAD_ENRICHMENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_all_buyers(self) -> List[Dict[str, Any]]:
        """Return all buyer records from buyers.csv merged with enrichment data."""
        self._ensure_files()
        buyers = []
        enrichments = self.get_lead_enrichments()
        try:
            with open(BUYERS_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Ensure defaults for all schema fields
                    full_row = {col: row.get(col, "") for col in BUYER_COLUMNS}
                    lid = full_row.get("lead_id", "")
                    enr = enrichments.get(lid, {})
                    full_row["enrichment"] = enr
                    full_row["enrichment_status"] = enr.get("enrichment_status", "needs_enrichment")
                    buyer_rel = enr.get("buyer_relevance")
                    if isinstance(buyer_rel, dict):
                        full_row["buyer_relevance"] = buyer_rel.get("relevance", "Unknown")
                    elif isinstance(buyer_rel, str):
                        full_row["buyer_relevance"] = buyer_rel
                    else:
                        full_row["buyer_relevance"] = "Unknown"
                    full_row["ai_confidence"] = enr.get("ai_confidence", 0.0)
                    buyers.append(full_row)
        except Exception:
            pass
        return buyers

    @staticmethod
    def _make_secondary_fingerprint(company: str, website: str) -> str:
        """Create a secondary fingerprint for records that lack an email."""
        clean_comp = "".join(filter(str.isalnum, (company or "").lower()))
        clean_domain = ""
        if website:
            try:
                parsed = urlparse(website if "://" in website else f"http://{website}")
                clean_domain = parsed.netloc.lower().replace("www.", "")
            except Exception:
                clean_domain = website.lower()
        return f"{clean_comp}:{clean_domain}"

    def get_existing_fingerprints(self) -> Tuple[Set[str], Set[str]]:
        """
        Return (known_emails, known_secondary_fingerprints).
        """
        buyers = self.get_all_buyers()
        known_emails = set()
        known_secondary = set()

        for b in buyers:
            email = b.get("email", "").strip().lower()
            if email:
                known_emails.add(email)
            else:
                fp = self._make_secondary_fingerprint(b.get("company_name", ""), b.get("website", ""))
                if fp != ":":
                    known_secondary.add(fp)

        return known_emails, known_secondary

    def append_buyers_detailed(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Append new buyer records using dual-key deduplication:
        1. Email address
        2. Normalized company + website (when email is missing)
        Returns: {'newly_added': int, 'duplicates_skipped': int}
        """
        self._ensure_files()
        known_emails, known_secondary = self.get_existing_fingerprints()

        new_records = []
        duplicates_skipped = 0
        now_iso = datetime.utcnow().isoformat() + "Z"

        for r in records:
            email = (r.get("email") or "").strip().lower()
            company = (r.get("company_name") or "").strip()
            website = (r.get("website") or "").strip()
            sec_fp = self._make_secondary_fingerprint(company, website)

            # Check duplicate by email
            if email:
                if email in known_emails:
                    duplicates_skipped += 1
                    continue
                known_emails.add(email)
            else:
                # Check duplicate by company + website
                if sec_fp != ":" and sec_fp in known_secondary:
                    duplicates_skipped += 1
                    continue
                if sec_fp != ":":
                    known_secondary.add(sec_fp)

            record_row = {
                "lead_id": r.get("lead_id") or f"lead_{uuid.uuid4().hex[:10]}",
                "email": email,
                "buyer_name": (r.get("buyer_name") or "").strip(),
                "company_name": company or "Sound & Wellness Prospect",
                "website": website,
                "country": (r.get("country") or "").strip() or "International",
                "source_platform": (r.get("source_platform") or "Web Search").strip(),
                "source_url": (r.get("source_url") or "").strip(),
                "validation_status": r.get("validation_status", "Valid" if email else "Missing").strip(),
                "classification": r.get("classification", "Unclassified").strip(),
                "outreach_status": r.get("outreach_status", "Not contacted").strip(),
                "discovered_date": r.get("discovered_date") or now_iso,
                "discovery_run_id": r.get("discovery_run_id") or "manual",
                "is_demo": "true" if str(r.get("is_demo", "")).lower() == "true" else "false",
                "notes": (r.get("notes") or "").strip(),
            }
            new_records.append(record_row)

        if new_records:
            with open(BUYERS_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=BUYER_COLUMNS)
                for rec in new_records:
                    writer.writerow(rec)

        return {
            "newly_added": len(new_records),
            "duplicates_skipped": duplicates_skipped
        }

    def append_buyers(self, records: List[Dict[str, Any]]) -> int:
        """Backward-compatible helper returning newly added count."""
        res = self.append_buyers_detailed(records)
        return res["newly_added"]

    def get_lead_by_id_or_email(self, identifier: str) -> Optional[Dict[str, str]]:
        """Find single lead by lead_id or email."""
        buyers = self.get_all_buyers()
        clean = identifier.strip().lower()
        for b in buyers:
            if b.get("lead_id", "").lower() == clean or b.get("email", "").lower() == clean:
                return b
        return None

    def update_lead(self, identifier: str, updates: Dict[str, Any]) -> bool:
        """Update fields for a lead matching lead_id or email."""
        self._ensure_files()
        buyers = self.get_all_buyers()
        clean = identifier.strip().lower()
        updated = False

        for b in buyers:
            if b.get("lead_id", "").lower() == clean or b.get("email", "").lower() == clean:
                for k, v in updates.items():
                    if k in BUYER_COLUMNS:
                        b[k] = str(v)
                updated = True
                break

        if updated:
            with open(BUYERS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=BUYER_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(buyers)

        return updated

    def delete_lead(self, identifier: str) -> bool:
        """Remove a lead matching lead_id, email, or website."""
        self._ensure_files()
        clean = (identifier or "").strip().lower()
        if not clean:
            return False

        buyers = self.get_all_buyers()

        def is_target(b: Dict[str, Any]) -> bool:
            if b.get("lead_id", "").lower() == clean:
                return True
            em = (b.get("email") or "").strip().lower()
            if em and em == clean:
                return True
            ws = (b.get("website") or "").strip().lower()
            if ws and ws == clean:
                return True
            return False

        remaining = [b for b in buyers if not is_target(b)]

        if len(remaining) == len(buyers):
            return False

        with open(BUYERS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=BUYER_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(remaining)

        # Also purge from lead_enrichment.json if present
        try:
            if LEAD_ENRICHMENT_FILE.exists():
                with open(LEAD_ENRICHMENT_FILE, "r", encoding="utf-8") as f:
                    enr_dict = json.load(f)
                to_delete_ids = [
                    b.get("lead_id") for b in buyers
                    if b.get("lead_id", "").lower() == clean
                    or b.get("email", "").lower() == clean
                    or b.get("website", "").lower() == clean
                ]
                changed = False
                for tid in to_delete_ids:
                    if tid and tid in enr_dict:
                        del enr_dict[tid]
                        changed = True
                if changed:
                    with open(LEAD_ENRICHMENT_FILE, "w", encoding="utf-8") as f:
                        json.dump(enr_dict, f, indent=2)
        except Exception:
            pass

        return True

    def get_sent_emails(self) -> Set[str]:
        """Return set of lowercased emails recorded in sent_log.csv."""
        self._ensure_files()
        sent_emails = set()
        try:
            with open(SENT_LOG_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("status") in ("sent", "delivered"):
                        sent_emails.add(row.get("email", "").strip().lower())
        except Exception:
            pass
        return sent_emails

    def log_send_attempt(self, email: str, status: str, subject: str = "", error_message: str = ""):
        """Append an entry to sent_log.csv and update lead outreach status."""
        self._ensure_files()
        timestamp = datetime.utcnow().isoformat() + "Z"
        row = {
            "email": email.strip().lower(),
            "status": status,
            "timestamp": timestamp,
            "campaign_subject": subject,
            "error_message": error_message,
        }
        with open(SENT_LOG_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SENT_LOG_COLUMNS)
            writer.writerow(row)

        outreach_status_map = {
            "sent": "Sent",
            "failed": "Failed",
            "duplicate_skipped": "Skipped",
        }
        self.update_lead(email, {"outreach_status": outreach_status_map.get(status, status)})

    def get_sent_logs(self) -> List[Dict[str, str]]:
        """Return all log entries from sent_log.csv."""
        self._ensure_files()
        logs = []
        try:
            with open(SENT_LOG_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logs.append(dict(row))
        except Exception:
            pass
        return logs

    def save_classified_emails(self, business: List[Dict[str, str]], individual: List[Dict[str, str]]):
        """Save classified records to business_emails.csv and individual_emails.csv and update buyers.csv."""
        self._ensure_files()
        now_iso = datetime.utcnow().isoformat() + "Z"

        if business:
            with open(BUSINESS_EMAILS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["email", "buyer_name", "company_name", "classified_date"])
                writer.writeheader()
                for b in business:
                    writer.writerow({
                        "email": b.get("email", ""),
                        "buyer_name": b.get("buyer_name", ""),
                        "company_name": b.get("company_name", ""),
                        "classified_date": now_iso
                    })
                    self.update_lead(b.get("email", ""), {"classification": "Business"})

        if individual:
            with open(INDIVIDUAL_EMAILS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["email", "buyer_name", "company_name", "classified_date"])
                writer.writeheader()
                for ind in individual:
                    writer.writerow({
                        "email": ind.get("email", ""),
                        "buyer_name": ind.get("buyer_name", ""),
                        "company_name": ind.get("company_name", ""),
                        "classified_date": now_iso
                    })
                    self.update_lead(ind.get("email", ""), {"classification": "Individual"})

    def get_classified_emails(self, audience: str = "all") -> List[Dict[str, str]]:
        """Return list of buyer records for specified audience."""
        all_buyers = self.get_all_buyers()
        if audience.lower() == "business":
            return [b for b in all_buyers if b.get("classification") == "Business"]
        elif audience.lower() == "individual":
            return [b for b in all_buyers if b.get("classification") == "Individual"]
        else:
            return all_buyers

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Compute operational metrics across all tables distinguishing real vs demo leads."""
        buyers = self.get_all_buyers()
        logs = self.get_sent_logs()

        total_leads = len(buyers)
        real_leads_count = sum(1 for b in buyers if str(b.get("is_demo", "")).lower() != "true")
        demo_leads_count = sum(1 for b in buyers if str(b.get("is_demo", "")).lower() == "true")

        valid_emails = sum(1 for b in buyers if b.get("validation_status") == "Valid")
        review_emails = sum(1 for b in buyers if b.get("validation_status") == "Review")
        missing_emails = sum(1 for b in buyers if b.get("validation_status") == "Missing")
        invalid_emails = sum(1 for b in buyers if b.get("validation_status") in ("Invalid", "Malformed"))

        business_contacts = sum(1 for b in buyers if b.get("classification") == "Business")
        individual_contacts = sum(1 for b in buyers if b.get("classification") == "Individual")
        unclassified_contacts = sum(1 for b in buyers if b.get("classification") in ("Unclassified", "", None))

        successful_sends = sum(1 for l in logs if l.get("status") in ("sent", "delivered"))
        failed_sends = sum(1 for l in logs if l.get("status") == "failed")
        duplicates_skipped = sum(1 for l in logs if l.get("status") == "duplicate_skipped")

        # Source breakdown
        source_counts = {}
        for b in buyers:
            src = b.get("source_platform") or "Web Search"
            source_counts[src] = source_counts.get(src, 0) + 1

        # Country breakdown
        country_counts = {}
        for b in buyers:
            c = b.get("country") or "International"
            country_counts[c] = country_counts.get(c, 0) + 1

        total_attempts = successful_sends + failed_sends
        success_rate = round((successful_sends / total_attempts * 100), 1) if total_attempts > 0 else 0.0

        return {
            "total_leads": total_leads,
            "real_leads_count": real_leads_count,
            "demo_leads_count": demo_leads_count,
            "valid_emails": valid_emails,
            "review_emails": review_emails,
            "missing_emails": missing_emails,
            "invalid_emails": invalid_emails,
            "business_contacts": business_contacts,
            "individual_contacts": individual_contacts,
            "unclassified_contacts": unclassified_contacts,
            "total_sent": successful_sends,
            "successful_deliveries": successful_sends,
            "failed_sends": failed_sends,
            "duplicates_skipped": duplicates_skipped,
            "success_rate": success_rate,
            "source_distribution": source_counts,
            "country_distribution": country_counts,
            "last_modified": datetime.utcnow().isoformat() + "Z"
        }
