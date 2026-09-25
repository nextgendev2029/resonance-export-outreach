"""
Audience Selector and Eligibility Engine for Resonance Campaigns (Phase 4).
Evaluates prospect leads against configurable B2B audience rules and past outreach logs.
Ensures zero demo leads, zero invalid emails, and zero low-relevance prospects enter
the default outreach campaign queue without explicit operator authorization.
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from config import SENT_LOG_CSV
from campaigns.models import AudienceFilters, AudiencePreviewResponse


class AudienceSelector:
    """Evaluates prospect eligibility for campaigns and produces detailed exclusion breakdowns."""

    def __init__(self, sent_log_file: Optional[Path] = None):
        self.sent_log_file = sent_log_file or SENT_LOG_CSV

    def get_contacted_emails(self) -> Dict[str, str]:
        """
        Read data/sent_log.csv to map normalized recipient emails to their last delivery status.
        Status: 'sent', 'failed', 'delivered', etc.
        """
        contacted: Dict[str, str] = {}
        if not self.sent_log_file.exists():
            return contacted

        try:
            with open(self.sent_log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    em = (row.get("email") or "").strip().lower()
                    st = (row.get("status") or "").strip().lower()
                    if em:
                        contacted[em] = st
        except Exception:
            pass
        return contacted

    def evaluate_lead(
        self,
        lead: Dict[str, Any],
        filters: AudienceFilters,
        contacted_map: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate a single lead against AudienceFilters.
        Returns: (is_eligible, list_of_exclusion_reasons)
        """
        reasons: List[str] = []
        is_demo_raw = lead.get("is_demo", False)
        is_demo = str(is_demo_raw).strip().lower() in ("true", "1")

        # 1. Dataset check
        if filters.dataset == "real" and is_demo:
            reasons.append("demo_data")
        elif filters.dataset == "demo" and not is_demo:
            reasons.append("not_demo_data")

        # 2. Email presence
        email = (lead.get("email") or "").strip()
        if not email:
            reasons.append("missing_email")

        # 3. Validation status
        val_status = (lead.get("validation_status") or "Missing").strip().capitalize()
        if filters.validation_status:
            allowed_val = [v.capitalize() for v in filters.validation_status]
            if val_status not in allowed_val:
                if val_status == "Invalid":
                    reasons.append("invalid_email")
                elif val_status == "Missing":
                    if "missing_email" not in reasons:
                        reasons.append("missing_email")
                elif val_status == "Review":
                    reasons.append("unverified_email_review")
                else:
                    reasons.append(f"validation_{val_status.lower()}")

        # 4. Classification
        cls_status = (lead.get("classification") or "Unclassified").strip().capitalize()
        if filters.classification:
            allowed_cls = [c.capitalize() for c in filters.classification]
            if cls_status not in allowed_cls:
                if cls_status == "Individual":
                    reasons.append("individual_contact")
                elif cls_status == "Unclassified":
                    reasons.append("unclassified_contact")
                else:
                    reasons.append("wrong_classification")

        # 5. Buyer relevance
        # Look in nested enrichment object first, then top-level lead attribute
        enrichment = lead.get("enrichment") or {}
        buyer_rel_obj = enrichment.get("buyer_relevance") or {}
        relevance = buyer_rel_obj.get("relevance") or lead.get("buyer_relevance") or "Unknown"
        relevance = str(relevance).strip().capitalize()

        if filters.buyer_relevance:
            allowed_rel = [r.capitalize() for r in filters.buyer_relevance]
            if relevance not in allowed_rel:
                if relevance == "Low":
                    reasons.append("low_relevance")
                elif relevance == "Unknown":
                    reasons.append("unknown_relevance")
                else:
                    reasons.append("unmatched_relevance")

        # 6. Country filter
        if filters.country and filters.country.strip():
            target_country = filters.country.strip().lower()
            lead_country = (lead.get("country") or "").strip().lower()
            if target_country not in lead_country:
                reasons.append("country_mismatch")

        # 7. Contacted / Outreach history
        norm_email = email.lower()
        last_sent_status = contacted_map.get(norm_email)
        outreach_status = (lead.get("outreach_status") or "").strip().lower()

        if filters.contacted_status == "never":
            if last_sent_status in ("sent", "delivered", "success") or outreach_status == "contacted":
                reasons.append("already_contacted")
        elif filters.contacted_status == "contacted":
            if last_sent_status not in ("sent", "delivered", "success") and outreach_status != "contacted":
                reasons.append("not_yet_contacted")
        elif filters.contacted_status == "failed":
            if last_sent_status != "failed" and outreach_status != "failed":
                reasons.append("not_failed_contact")

        is_eligible = (len(reasons) == 0)
        return is_eligible, reasons

    def evaluate_all(
        self,
        leads: List[Dict[str, Any]],
        filters: AudienceFilters
    ) -> AudiencePreviewResponse:
        """
        Evaluate full list of leads and return comprehensive preview metrics and breakdown.
        """
        contacted_map = self.get_contacted_emails()
        eligible_lead_ids: List[str] = []
        exclusion_counts: Dict[str, int] = {}
        sample_eligible: List[Dict[str, Any]] = []
        sample_excluded: List[Dict[str, Any]] = []

        for lead in leads:
            is_eligible, reasons = self.evaluate_lead(lead, filters, contacted_map)
            lead_id = lead.get("lead_id") or ""
            enr = lead.get("enrichment") or {}
            rel_obj = enr.get("buyer_relevance") if isinstance(enr, dict) else {}
            relevance_val = (rel_obj.get("relevance") if isinstance(rel_obj, dict) else None) or lead.get("buyer_relevance", "Unknown")

            lead_summary = {
                "lead_id": lead_id,
                "email": lead.get("email", ""),
                "company_name": lead.get("company_name", ""),
                "buyer_name": lead.get("buyer_name", ""),
                "country": lead.get("country", ""),
                "classification": lead.get("classification", "Unclassified"),
                "validation_status": lead.get("validation_status", "Missing"),
                "buyer_relevance": relevance_val,
                "is_demo": str(lead.get("is_demo", "")).lower() in ("true", "1")
            }

            if is_eligible:
                eligible_lead_ids.append(lead_id)
                if len(sample_eligible) < 25:
                    sample_eligible.append(lead_summary)
            else:
                for r in reasons:
                    exclusion_counts[r] = exclusion_counts.get(r, 0) + 1
                if len(sample_excluded) < 25:
                    lead_summary["exclusion_reasons"] = reasons
                    sample_excluded.append(lead_summary)

        return AudiencePreviewResponse(
            total_evaluated=len(leads),
            eligible_count=len(eligible_lead_ids),
            excluded_count=len(leads) - len(eligible_lead_ids),
            exclusion_reasons=exclusion_counts,
            eligible_lead_ids=eligible_lead_ids,
            sample_eligible=sample_eligible,
            sample_excluded=sample_excluded
        )
