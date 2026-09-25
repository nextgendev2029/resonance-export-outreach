"""
Deterministic Final Pre-Dispatch Eligibility Checker for Resonance (Phase 5).
Evaluates every draft and lead immediately before queuing and immediately before
SMTP submission. Blocks dispatch if any business, compliance, or safety rule is violated.
"""

import re
import csv
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Set

from config import SENT_LOG_CSV, DEFAULT_PRESENTATION_PATH, PRESENTATION_PATH
from outreach.attachment_handler import AttachmentHandler
from campaigns.draft_validator import DraftValidator
from dispatch.suppression import SuppressionManager
from dispatch.rate_limiter import RateLimiter


class EligibilityResult:
    """Encapsulates the decision and exact reason for pre-dispatch eligibility."""
    def __init__(self, eligible: bool, reason: str, status_code: str = "eligible"):
        self.eligible = eligible
        self.reason = reason
        self.status_code = status_code

    def __bool__(self):
        return self.eligible

    def __repr__(self):
        return f"<EligibilityResult eligible={self.eligible} status_code={self.status_code} reason='{self.reason}'>"


class FinalEligibilityChecker:
    """Verifies complete pre-dispatch and dispatch-time eligibility rules."""

    def __init__(
        self,
        suppression_manager: Optional[SuppressionManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        sent_log_file: Optional[Path] = None,
        attachment_path: Optional[Path] = None,
        suppression_mgr: Optional[SuppressionManager] = None,
        sent_log_path: Optional[Path] = None,
        activity_logger: Optional[Any] = None
    ):
        self.suppression = suppression_manager or suppression_mgr or SuppressionManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.sent_log_file = sent_log_file or sent_log_path or SENT_LOG_CSV
        self.attachment_path = attachment_path or PRESENTATION_PATH or DEFAULT_PRESENTATION_PATH
        self.validator = DraftValidator()
        self.activity_logger = activity_logger

    def get_contacted_emails_set(self) -> Set[str]:
        """Get set of normalized emails that were successfully contacted."""
        if self.activity_logger and hasattr(self.activity_logger, "get_sent_emails"):
            try:
                res = self.activity_logger.get_sent_emails()
                if isinstance(res, set):
                    return res
            except Exception:
                pass

        contacted: Set[str] = set()
        if not self.sent_log_file.exists():
            return contacted


        try:
            with open(self.sent_log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    st = (row.get("status") or "").strip().lower()
                    em = (row.get("email") or "").strip().lower()
                    if em and st in ("sent", "delivered", "success"):
                        contacted.add(em)
        except Exception:
            pass

        return contacted

    def verify_attachment(self, attachment_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Verify the presentation attachment exists and is a valid readable PDF."""
        target_path = Path(attachment_path or str(self.attachment_path))
        if not target_path.exists():
            return False, f"Attachment file not found at '{target_path}'."
        if not target_path.is_file():
            return False, f"Attachment path '{target_path}' is not a valid file."
        if target_path.suffix.lower() != ".pdf":
            return False, f"Attachment '{target_path.name}' must be a .pdf document."
        try:
            with open(target_path, "rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF"):
                    return False, f"Attachment file '{target_path.name}' is corrupt or not a valid PDF."
        except Exception as e:
            return False, f"Could not read attachment file: {str(e)}"

        return True, None

    def check_draft_eligibility(
        self,
        draft: Dict[str, Any],
        campaign: Dict[str, Any],
        contacted_set: Optional[Set[str]] = None,
        check_rate_limits: bool = False
    ) -> EligibilityResult:
        """
        Evaluate a single draft immediately before queuing or dispatch.
        Returns: EligibilityResult
        """
        # 1. Draft Status Check
        status = draft.get("status", "")
        if status != "Approved":
            return EligibilityResult(False, f"Draft status is '{status}'; must be 'Approved' to dispatch.", "unapproved")

        # 2. Critical Demo Data Protection
        is_demo_raw = draft.get("is_demo", False)
        if is_demo_raw is True or str(is_demo_raw).strip().lower() in ("true", "1"):
            return EligibilityResult(False, "Demo leads and sample records are strictly forbidden from dispatch.", "demo_blocked")

        # 3. Campaign State Check
        camp_status = (campaign.get("status") or "").lower()
        if camp_status in ("cancelled", "canceled"):
            return EligibilityResult(False, "Campaign has been cancelled by operator.", "campaign_inactive")
        if camp_status in ("archived",):
            return EligibilityResult(False, "Campaign has been archived.", "campaign_inactive")
        if camp_status in ("paused",):
            return EligibilityResult(False, "Campaign is currently paused by operator.", "campaign_inactive")

        # 4. Email Presence & Syntax
        email = (draft.get("recipient_email") or "").strip()
        if not email:
            return EligibilityResult(False, "Recipient email is missing.", "invalid")

        if "@" not in email or "." not in email.split("@")[-1] or " " in email:
            return EligibilityResult(False, f"Recipient email '{email}' has invalid syntax.", "invalid")

        norm_email = email.lower()

        # 5. Suppression Check
        if self.suppression.is_suppressed(norm_email):
            supp = self.suppression.get_suppression(norm_email)
            reason = supp.get("reason", "unspecified") if supp else "suppressed"
            return EligibilityResult(False, f"Recipient is on suppression list (Reason: {reason}).", "suppressed")

        # 6. Duplicate Check (Historical Sent Log)
        c_set = contacted_set if contacted_set is not None else self.get_contacted_emails_set()
        if norm_email in c_set:
            return EligibilityResult(False, "Recipient was already successfully contacted in historical sent log.", "duplicate")

        # 7. Classification Check
        classification = (draft.get("classification") or "Unclassified").strip().capitalize()
        if classification != "Business":
            return EligibilityResult(False, f"Classification is '{classification}'; dispatch requires 'Business'.", "non_business")

        # 8. Buyer Relevance Check
        relevance = (draft.get("buyer_relevance") or "Unknown").strip().capitalize()
        if relevance not in ("High", "Medium"):
            return EligibilityResult(False, f"Buyer relevance is '{relevance}'; must be 'High' or 'Medium'.", "low_relevance")

        # 9. Email Content Integrity (Subject & Body)
        subject = (draft.get("subject") or "").strip()
        body = (draft.get("body") or "").strip()
        if not subject:
            return EligibilityResult(False, "Email subject is empty.", "invalid")
        if not body:
            return EligibilityResult(False, "Email body is empty.", "invalid")

        # 10. Unresolved Template Variables & Null Placeholders
        full_text = f"{subject}\n{body}"
        if re.search(r"\{\{.*?\}\}", full_text):
            return EligibilityResult(False, "Unresolved template variable (e.g. {{...}}) detected in message copy.", "unresolved_placeholder")

        for forbidden in ("undefined", "null", "None"):
            if re.search(rf"\b{forbidden}\b", full_text):
                return EligibilityResult(False, f"Forbidden placeholder string '{forbidden}' detected in message copy.", "unresolved_placeholder")

        # 11. Final Draft Validator Grounding & Spam Check
        validation = self.validator.validate(subject, body, {"company_name": draft.get("company_name")})
        if validation.spam_detected:
            return EligibilityResult(False, "Draft validation failed: Potential spam triggers or excessive capitalization detected.", "blocked")
        if not validation.is_grounded:
            return EligibilityResult(False, "Draft validation failed: Unsupported claims or fake intent detected.", "blocked")

        # 12. Presentation Attachment Check
        att_path = Path(draft.get("attachment_path") or str(self.attachment_path))
        att_ok, att_err = self.verify_attachment(str(att_path))
        if not att_ok:
            return EligibilityResult(False, att_err or "Invalid attachment.", "blocked")

        # 13. Operational Rate Limits
        if check_rate_limits:
            capacity = self.rate_limiter.get_remaining_capacity(campaign.get("campaign_id"))
            if capacity["remaining_today"] <= 0:
                return EligibilityResult(False, f"Daily limit reached ({capacity['sent_today']}/{capacity['daily_limit']} sent today).", "blocked")
            if capacity["remaining_campaign"] <= 0:
                return EligibilityResult(False, f"Campaign limit reached ({capacity['campaign_sent']}/{capacity['campaign_limit']} sent).", "blocked")

        return EligibilityResult(True, "Passed all pre-dispatch eligibility checks.", "eligible")

    def verify_draft_eligibility(
        self,
        draft: Dict[str, Any],
        campaign: Dict[str, Any],
        contacted_set: Optional[Set[str]] = None,
        check_rate_limits: bool = True
    ) -> Tuple[bool, str, str]:
        """Legacy helper returning tuple (eligible, reason, category)."""
        res = self.check_draft_eligibility(draft, campaign, contacted_set, check_rate_limits)
        category_map = {
            "eligible": "Eligible",
            "suppressed": "Suppressed",
            "duplicate": "Duplicate"
        }
        category = category_map.get(res.status_code, "Blocked")
        return res.eligible, res.reason, category
