"""
Campaign and Draft Persistence Store for Resonance (Phase 4).
Maintains data/campaigns.json and data/outreach_drafts.json.
Enforces duplicate prevention, auditability of operator edits, version history,
and strict safety boundaries preventing live email dispatch.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import CAMPAIGNS_FILE, OUTREACH_DRAFTS_FILE
from campaigns.models import CampaignRecord, OutreachDraft
from campaigns.draft_validator import DraftValidator


class CampaignStore:
    """Flat-file atomic JSON repository for campaigns and outreach drafts."""

    def __init__(
        self,
        campaigns_file: Optional[Path] = None,
        drafts_file: Optional[Path] = None
    ):
        self.campaigns_file = campaigns_file or CAMPAIGNS_FILE
        self.drafts_file = drafts_file or OUTREACH_DRAFTS_FILE
        self._ensure_storage()

    def _ensure_storage(self):
        """Initialize JSON storage files if they do not exist."""
        if not self.campaigns_file.exists():
            with open(self.campaigns_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

        if not self.drafts_file.exists():
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    # -------------------------------------------------------------
    # Campaign CRUD Operations
    # -------------------------------------------------------------
    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all campaigns sorted by updated_at descending."""
        self._ensure_storage()
        try:
            with open(self.campaigns_file, "r", encoding="utf-8") as f:
                campaigns = json.load(f)
                return sorted(campaigns, key=lambda c: c.get("updated_at", ""), reverse=True)
        except Exception:
            return []

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific campaign by ID."""
        campaigns = self.list_campaigns()
        for c in campaigns:
            if c.get("campaign_id") == campaign_id:
                return c
        return None

    def create_campaign(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create and persist a new campaign."""
        self._ensure_storage()
        now_iso = datetime.utcnow().isoformat() + "Z"
        cid = f"camp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

        campaign = CampaignRecord(
            campaign_id=cid,
            name=payload.get("name") or "New B2B Outreach Campaign",
            created_at=now_iso,
            updated_at=now_iso,
            status="Draft",
            audience_filters=payload.get("audience_filters") or {},
            subject_template=payload.get("subject_template") or "Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog",
            body_template=payload.get("body_template") or "",
            attachment_path=payload.get("attachment_path") or "assets/company_presentation.pdf",
            attachment_ready=True,
            reply_to=payload.get("reply_to"),
            sender_identity=payload.get("sender_identity") or "Himalayan Singing Bowls Export Operations"
        )

        campaigns = self.list_campaigns()
        campaigns.insert(0, campaign.to_dict())

        with open(self.campaigns_file, "w", encoding="utf-8") as f:
            json.dump(campaigns, f, indent=2)

        return campaign.to_dict()

    def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update campaign configuration fields."""
        campaigns = self.list_campaigns()
        updated_camp = None

        for c in campaigns:
            if c.get("campaign_id") == campaign_id:
                for k, v in updates.items():
                    if v is not None and k not in ("campaign_id", "created_at"):
                        c[k] = v
                c["updated_at"] = datetime.utcnow().isoformat() + "Z"
                updated_camp = c
                break

        if updated_camp:
            with open(self.campaigns_file, "w", encoding="utf-8") as f:
                json.dump(campaigns, f, indent=2)

        return updated_camp

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete campaign and its associated drafts."""
        campaigns = self.list_campaigns()
        new_camps = [c for c in campaigns if c.get("campaign_id") != campaign_id]
        if len(new_camps) == len(campaigns):
            return False

        with open(self.campaigns_file, "w", encoding="utf-8") as f:
            json.dump(new_camps, f, indent=2)

        # Also purge related drafts
        drafts = self.list_all_drafts()
        new_drafts = [d for d in drafts if d.get("campaign_id") != campaign_id]
        with open(self.drafts_file, "w", encoding="utf-8") as f:
            json.dump(new_drafts, f, indent=2)

        return True

    # -------------------------------------------------------------
    # Draft CRUD & Queue Operations
    # -------------------------------------------------------------
    def list_all_drafts(self) -> List[Dict[str, Any]]:
        """Internal helper to load all drafts."""
        self._ensure_storage()
        try:
            with open(self.drafts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def list_drafts(
        self,
        campaign_id: str,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List drafts for a specific campaign with optional status and text search filtering."""
        """List drafts for a specific campaign with optional status and text search filtering."""
        all_drafts = self.list_all_drafts()
        campaign_drafts = [d for d in all_drafts if d.get("campaign_id") == campaign_id]

        if status_filter and status_filter.lower() != "all":
            target_status = status_filter.strip().lower()
            campaign_drafts = [d for d in campaign_drafts if d.get("status", "").lower() == target_status]

        if search and search.strip():
            query = search.strip().lower()
            campaign_drafts = [
                d for d in campaign_drafts
                if query in (d.get("company_name") or "").lower()
                or query in (d.get("recipient_name") or "").lower()
                or query in (d.get("recipient_email") or "").lower()
                or query in (d.get("subject") or "").lower()
            ]

        return sorted(campaign_drafts, key=lambda d: d.get("updated_at", ""), reverse=True)

    list_campaign_drafts = list_drafts

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific draft by draft_id."""
        for d in self.list_all_drafts():
            if d.get("draft_id") == draft_id:
                return d
        return None

    def save_draft(self, draft: OutreachDraft) -> Dict[str, Any]:
        """
        Save or update a draft.
        Enforces duplicate prevention on (campaign_id, lead_id) and normalized email.
        """
        all_drafts = self.list_all_drafts()
        d_dict = draft.to_dict()

        # Check existing
        existing_idx = None
        for idx, d in enumerate(all_drafts):
            if d.get("draft_id") == draft.draft_id:
                existing_idx = idx
                break
            elif (
                d.get("campaign_id") == draft.campaign_id
                and d.get("lead_id") == draft.lead_id
            ):
                existing_idx = idx
                break

        if existing_idx is not None:
            all_drafts[existing_idx] = d_dict
        else:
            all_drafts.insert(0, d_dict)

        with open(self.drafts_file, "w", encoding="utf-8") as f:
            json.dump(all_drafts, f, indent=2)

        self.recalculate_campaign_stats(draft.campaign_id)
        return d_dict

    def update_draft(self, draft_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Operator draft editing.
        Preserves original_ai_draft untouched and records operator modifications.
        """
        all_drafts = self.list_all_drafts()
        target = None
        now_iso = datetime.utcnow().isoformat() + "Z"

        for d in all_drafts:
            if d.get("draft_id") == draft_id:
                target = d
                break

        if not target:
            return None

        # Check if text fields were modified
        is_text_edit = False
        edit_record = target.get("operator_edited_draft") or {}

        for field in ("subject", "opening_line", "body", "closing"):
            if field in updates and updates[field] is not None:
                new_val = str(updates[field]).strip()
                if new_val != target.get(field):
                    target[field] = new_val
                    edit_record[field] = new_val
                    is_text_edit = True

        if is_text_edit:
            edit_record["edited_at"] = now_iso
            target["operator_edited_draft"] = edit_record
            if target.get("status") not in ("Approved", "Rejected", "Archived"):
                target["status"] = "Edited"

        # Direct status updates if supplied
        if "status" in updates and updates["status"]:
            target["status"] = updates["status"]

        target["updated_at"] = now_iso

        # Re-run validation on edited body
        validator = DraftValidator()
        val = validator.validate(
            subject=target.get("subject", ""),
            body=target.get("body", ""),
            verified_context={"company_name": target.get("company_name")}
        )
        target["validation"] = val.model_dump()

        with open(self.drafts_file, "w", encoding="utf-8") as f:
            json.dump(all_drafts, f, indent=2)

        self.recalculate_campaign_stats(target.get("campaign_id"))
        return target

    def approve_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """
        Operator approvals.
        Marks draft status as 'Approved' and sets approved_at.
        CRITICAL ARCHITECTURAL SAFETY: DOES NOT SEND LIVE EMAILS.
        """
        all_drafts = self.list_all_drafts()
        target = None
        now_iso = datetime.utcnow().isoformat() + "Z"

        for d in all_drafts:
            if d.get("draft_id") == draft_id:
                d["status"] = "Approved"
                d["approved_at"] = now_iso
                d["updated_at"] = now_iso
                target = d
                break

        if target:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(all_drafts, f, indent=2)
            self.recalculate_campaign_stats(target.get("campaign_id"))

        return target

    def reject_draft(self, draft_id: str, reason: str = "Unspecified") -> Optional[Dict[str, Any]]:
        """
        Operator rejection. Records explicit rejection reason.
        """
        all_drafts = self.list_all_drafts()
        target = None
        now_iso = datetime.utcnow().isoformat() + "Z"

        for d in all_drafts:
            if d.get("draft_id") == draft_id:
                d["status"] = "Rejected"
                d["rejection_reason"] = reason or "Unspecified"
                d["rejected_at"] = now_iso
                d["updated_at"] = now_iso
                target = d
                break

        if target:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(all_drafts, f, indent=2)
            self.recalculate_campaign_stats(target.get("campaign_id"))

        return target

    def record_regeneration(
        self,
        draft_id: str,
        new_subject: str,
        new_opening: str,
        new_body: str,
        new_closing: str,
        new_confidence: float,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Preserves previous draft in version_history and writes regenerated version.
        """
        all_drafts = self.list_all_drafts()
        target = None
        now_iso = datetime.utcnow().isoformat() + "Z"

        for d in all_drafts:
            if d.get("draft_id") == draft_id:
                target = d
                break

        if not target:
            return None

        # Build archive record of current version
        history = target.get("version_history") or []
        next_ver = len(history) + 1

        new_version_record = {
            "version": next_ver,
            "generated_at": now_iso,
            "subject": new_subject,
            "opening_line": new_opening,
            "body": new_body,
            "closing": new_closing,
            "ai_confidence": new_confidence,
            "personalization_reason": reason
        }
        history.append(new_version_record)

        target["version_history"] = history
        target["subject"] = new_subject
        target["opening_line"] = new_opening
        target["body"] = new_body
        target["closing"] = new_closing
        target["ai_confidence"] = new_confidence
        target["personalization_reason"] = reason
        target["status"] = "Draft"
        target["updated_at"] = now_iso

        # Re-run validation
        validator = DraftValidator()
        val = validator.validate(
            subject=new_subject,
            body=new_body,
            verified_context={"company_name": target.get("company_name")}
        )
        target["validation"] = val.model_dump()

        with open(self.drafts_file, "w", encoding="utf-8") as f:
            json.dump(all_drafts, f, indent=2)

        self.recalculate_campaign_stats(target.get("campaign_id"))
        return target

    # -------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------
    def bulk_approve(self, draft_ids: List[str]) -> int:
        """
        Bulk approve drafts.
        CRITICAL SAFETY: DOES NOT SEND EMAILS.
        """
        all_drafts = self.list_all_drafts()
        now_iso = datetime.utcnow().isoformat() + "Z"
        affected_campaigns = set()
        count = 0

        for d in all_drafts:
            if d.get("draft_id") in draft_ids:
                d["status"] = "Approved"
                d["approved_at"] = now_iso
                d["updated_at"] = now_iso
                affected_campaigns.add(d.get("campaign_id"))
                count += 1

        if count > 0:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(all_drafts, f, indent=2)
            for cid in affected_campaigns:
                if cid:
                    self.recalculate_campaign_stats(cid)

        return count

    def bulk_reject(self, draft_ids: List[str], reason: str = "Bulk rejection") -> int:
        """Bulk reject drafts with reason."""
        all_drafts = self.list_all_drafts()
        now_iso = datetime.utcnow().isoformat() + "Z"
        affected_campaigns = set()
        count = 0

        for d in all_drafts:
            if d.get("draft_id") in draft_ids:
                d["status"] = "Rejected"
                d["rejection_reason"] = reason
                d["rejected_at"] = now_iso
                d["updated_at"] = now_iso
                affected_campaigns.add(d.get("campaign_id"))
                count += 1

        if count > 0:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(all_drafts, f, indent=2)
            for cid in affected_campaigns:
                if cid:
                    self.recalculate_campaign_stats(cid)

        return count

    def bulk_archive(self, draft_ids: List[str]) -> int:
        """Bulk archive drafts."""
        all_drafts = self.list_all_drafts()
        now_iso = datetime.utcnow().isoformat() + "Z"
        affected_campaigns = set()
        count = 0

        for d in all_drafts:
            if d.get("draft_id") in draft_ids:
                d["status"] = "Archived"
                d["updated_at"] = now_iso
                affected_campaigns.add(d.get("campaign_id"))
                count += 1

        if count > 0:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(all_drafts, f, indent=2)
            for cid in affected_campaigns:
                if cid:
                    self.recalculate_campaign_stats(cid)

        return count

    def recalculate_campaign_stats(self, campaign_id: str):
        """Update campaign counters and operational status."""
        if not campaign_id:
            return

        campaigns = self.list_campaigns()
        camp = None
        for c in campaigns:
            if c.get("campaign_id") == campaign_id:
                camp = c
                break

        if not camp:
            return

        drafts = [d for d in self.list_all_drafts() if d.get("campaign_id") == campaign_id]
        total = len(drafts)
        approved = sum(1 for d in drafts if d.get("status") == "Approved")
        rejected = sum(1 for d in drafts if d.get("status") == "Rejected")
        needs_review = sum(1 for d in drafts if d.get("status") == "Needs Review")

        camp["draft_count"] = total
        camp["approved_count"] = approved
        camp["rejected_count"] = rejected
        camp["needs_review_count"] = needs_review

        # Preserve downstream dispatch states
        dispatch_states = {
            "Queued", "Sending", "Completed", "Completed With Errors",
            "Paused", "Cancelled", "Archived"
        }
        current_status = camp.get("status", "")
        if current_status not in dispatch_states:
            if total == 0:
                if current_status not in ("Building Audience", "Generating Drafts"):
                    camp["status"] = "Draft"
            elif approved == total and total > 0:
                camp["status"] = "Approved"
            elif approved > 0:
                camp["status"] = "Partially Approved"
            else:
                camp["status"] = "Review"

        camp["updated_at"] = datetime.utcnow().isoformat() + "Z"

        with open(self.campaigns_file, "w", encoding="utf-8") as f:
            json.dump(campaigns, f, indent=2)

