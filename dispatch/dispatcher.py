"""
Dispatch Coordinator for Resonance (Phase 5).
Orchestrates preflight checks, queue population, explicit confirmation,
idempotent background dispatch workers, rate limiting, and pause/cancel controls.
"""

import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from config import load_settings, PRESENTATION_PATH
from campaigns.campaign_store import CampaignStore
from campaigns.models import OutreachDraft
from dispatch.models import (
    DispatchQueueItem,
    PreflightReport,
    DispatchConfirmPayload,
    TestSendPayload
)
from dispatch.eligibility import FinalEligibilityChecker
from dispatch.queue import DispatchQueue
from dispatch.sender import DispatchSender
from dispatch.rate_limiter import RateLimiter
from dispatch.suppression import SuppressionManager
from dispatch.delivery_log import DeliveryLogger, AuditLogger
from app_logging.activity_logger import ActivityLogger


class DispatchCoordinator:
    """Singleton/thread-safe manager for campaign dispatch operations."""

    def __init__(
        self,
        campaign_store: Optional[CampaignStore] = None,
        queue: Optional[DispatchQueue] = None,
        eligibility_checker: Optional[FinalEligibilityChecker] = None,
        sender: Optional[DispatchSender] = None,
        rate_limiter: Optional[RateLimiter] = None,
        suppression_mgr: Optional[SuppressionManager] = None,
        delivery_logger: Optional[DeliveryLogger] = None,
        audit_logger: Optional[AuditLogger] = None,
        activity_logger: Optional[ActivityLogger] = None
    ):
        self.campaign_store = campaign_store or CampaignStore()
        self.queue = queue or DispatchQueue()
        self.suppression_mgr = suppression_mgr or SuppressionManager()
        self.delivery_logger = delivery_logger or DeliveryLogger()
        self.audit_logger = audit_logger or AuditLogger()
        self.activity_logger = activity_logger or ActivityLogger()
        self.rate_limiter = rate_limiter or RateLimiter(activity_logger=self.activity_logger)
        self.sender = sender or DispatchSender(logger=self.activity_logger)
        self.eligibility_checker = eligibility_checker or FinalEligibilityChecker(
            suppression_mgr=self.suppression_mgr,
            rate_limiter=self.rate_limiter,
            activity_logger=self.activity_logger
        )


        self._active_dispatches: Set[str] = set()
        self._lock = threading.Lock()

        # On startup, recover any stale 'Sending' items that may have crashed
        self.queue.recover_stale_sending()

    def get_preflight(self, campaign_id: str) -> PreflightReport:
        """Run deterministic preflight check across all drafts for a campaign."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return PreflightReport(
                campaign_id=campaign_id,
                total_drafts=0,
                approved_count=0,
                currently_eligible=0,
                blocked_count=0,
                duplicate_count=0,
                suppressed_count=0,
                demo_count=0,
                invalid_count=0,
                attachment_ready=False,
                dry_run=True,
                daily_limit=100,
                sent_today=0,
                remaining_today=0,
                ready=False,
                blocking_reasons=[f"Campaign '{campaign_id}' not found."]
            )

        drafts = self.campaign_store.list_campaign_drafts(campaign_id, status_filter="all")
        total_drafts = len(drafts)
        approved_drafts = [d for d in drafts if d.get("status") == "Approved"]
        approved_count = len(approved_drafts)

        currently_eligible = 0
        blocked_count = 0
        duplicate_count = 0
        suppressed_count = 0
        demo_count = 0
        invalid_count = 0
        eligible_draft_ids: List[str] = []
        blocking_reasons: List[str] = []

        # Attachment check
        att_path = camp.get("attachment_path") or str(PRESENTATION_PATH)
        att_ok, att_err = self.eligibility_checker.verify_attachment(att_path)
        if not att_ok and att_err:
            blocking_reasons.append(f"Attachment error: {att_err}")

        # Rate limit checks
        daily_lim = self.rate_limiter.max_per_day
        sent_today = self.rate_limiter.get_sent_today_count()
        remaining_today = self.rate_limiter.get_remaining_today()
        dry_run = bool(self.rate_limiter.settings.get("dry_run", True))

        if remaining_today <= 0:
            blocking_reasons.append(f"Daily send limit of {daily_lim} emails has been reached.")

        camp_sent = self.rate_limiter.get_sent_campaign_count(campaign_id)
        camp_remaining = self.rate_limiter.get_remaining_campaign(campaign_id)
        if camp_remaining <= 0:
            blocking_reasons.append(f"Campaign send limit of {self.rate_limiter.max_per_campaign} emails reached.")

        if camp.get("status") in ("Cancelled", "Archived"):
            blocking_reasons.append(f"Campaign is {camp.get('status')}. Dispatch not allowed.")

        # Check each approved draft
        for d in approved_drafts:
            res = self.eligibility_checker.check_draft_eligibility(d, camp)
            if res.eligible:
                currently_eligible += 1
                eligible_draft_ids.append(d.get("draft_id"))
            else:
                if res.status_code == "duplicate":
                    duplicate_count += 1
                elif res.status_code == "suppressed":
                    suppressed_count += 1
                elif res.status_code == "demo_blocked":
                    demo_count += 1
                elif res.status_code == "invalid":
                    invalid_count += 1
                else:
                    blocked_count += 1

        if approved_count == 0:
            blocking_reasons.append("No approved drafts found in this campaign.")
        elif currently_eligible == 0:
            blocking_reasons.append("Zero approved drafts passed final pre-dispatch eligibility.")

        ready = (
            att_ok
            and remaining_today > 0
            and camp_remaining > 0
            and currently_eligible > 0
            and camp.get("status") not in ("Cancelled", "Archived")
        )

        return PreflightReport(
            campaign_id=campaign_id,
            total_drafts=total_drafts,
            approved_count=approved_count,
            currently_eligible=currently_eligible,
            blocked_count=blocked_count,
            duplicate_count=duplicate_count,
            suppressed_count=suppressed_count,
            demo_count=demo_count,
            invalid_count=invalid_count,
            attachment_ready=att_ok,
            dry_run=dry_run,
            daily_limit=daily_lim,
            sent_today=sent_today,
            remaining_today=remaining_today,
            ready=ready,
            blocking_reasons=blocking_reasons,
            eligible_draft_ids=eligible_draft_ids
        )

    def prepare_queue(self, campaign_id: str) -> Dict[str, Any]:
        """
        Populate the persistent dispatch queue with currently eligible approved drafts.
        """
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return {"success": False, "error": f"Campaign '{campaign_id}' not found."}

        preflight = self.get_preflight(campaign_id)
        drafts = self.campaign_store.list_campaign_drafts(campaign_id, status_filter="Approved")

        now_iso = datetime.utcnow().isoformat() + "Z"
        enqueued_count = 0
        skipped_existing = 0

        existing_queue = self.queue.get_campaign_items(campaign_id)
        existing_draft_ids = {item.draft_id for item in existing_queue}

        for d in drafts:
            did = d.get("draft_id")
            if did not in preflight.eligible_draft_ids:
                continue

            if did in existing_draft_ids:
                skipped_existing += 1
                continue

            q_item = DispatchQueueItem(
                dispatch_id=f"disp_{uuid.uuid4().hex[:12]}",
                campaign_id=campaign_id,
                draft_id=did,
                lead_id=d.get("lead_id", ""),
                recipient_email=d.get("recipient_email", "").strip().lower(),
                recipient_name=d.get("recipient_name") or "Valued Partner",
                company_name=d.get("company_name") or "Organization",
                subject=d.get("subject", ""),
                body=d.get("body", ""),
                attachment_path=camp.get("attachment_path") or str(PRESENTATION_PATH),
                status="Queued",
                queued_at=now_iso,
                is_demo=bool(d.get("is_demo", False))
            )
            if self.queue.enqueue(q_item):
                enqueued_count += 1
                self.delivery_logger.log_event(
                    dispatch_id=q_item.dispatch_id,
                    event="queued",
                    campaign_id=campaign_id,
                    draft_id=did,
                    lead_id=q_item.lead_id,
                    recipient_email=q_item.recipient_email,
                    status="Queued"
                )

        if enqueued_count > 0:
            if camp.get("status") in ("Draft", "Review", "Partially Approved", "Approved"):
                self.campaign_store.update_campaign(campaign_id, {"status": "Queued"})
            self.audit_logger.log_event(
                event_type="dispatch_created",
                campaign_id=campaign_id,
                details={
                    "enqueued_count": enqueued_count,
                    "skipped_existing": skipped_existing
                }
            )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "enqueued_count": enqueued_count,
            "skipped_existing": skipped_existing,
            "total_in_queue": len(self.queue.get_campaign_items(campaign_id))
        }

    def get_dispatch_status(self, campaign_id: str) -> Dict[str, Any]:
        """Return operational queue metrics and active dispatch state."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return {"error": "Campaign not found"}

        items = self.queue.get_campaign_items(campaign_id)
        counts = {
            "Queued": 0,
            "Sending": 0,
            "Sent": 0,
            "Failed": 0,
            "Cancelled": 0,
            "Blocked": 0,
            "Suppressed": 0,
            "Duplicate": 0
        }
        for item in items:
            counts[item.status] = counts.get(item.status, 0) + 1

        with self._lock:
            is_dispatching = campaign_id in self._active_dispatches

        # Recent events
        events = self.delivery_logger.get_campaign_events(campaign_id, limit=20)

        # Rate limits
        daily_rem = self.rate_limiter.get_remaining_today()
        camp_rem = self.rate_limiter.get_remaining_campaign(campaign_id)

        return {
            "campaign_id": campaign_id,
            "campaign_name": camp.get("name"),
            "campaign_status": camp.get("status"),
            "is_dispatching": is_dispatching,
            "counts": counts,
            "total_items": len(items),
            "remaining_in_queue": counts.get("Queued", 0) + counts.get("Sending", 0),
            "daily_limit_remaining": daily_rem,
            "campaign_limit_remaining": camp_rem,
            "dry_run": bool(self.rate_limiter.settings.get("dry_run", True)),
            "recent_events": events
        }

    def confirm_and_dispatch(
        self,
        campaign_id: str,
        operator_notes: str = "",
        synchronous: bool = False
    ) -> Dict[str, Any]:
        """
        EXPLICIT OPERATOR CONFIRMATION ENDPOINT.
        Guarantees idempotency and executes the dispatch loop.
        """
        with self._lock:
            if campaign_id in self._active_dispatches:
                return {
                    "success": False,
                    "error": "Dispatch is already in progress for this campaign. Duplicate request prevented.",
                    "already_running": True
                }
            self._active_dispatches.add(campaign_id)

        try:
            camp = self.campaign_store.get_campaign(campaign_id)
            if not camp:
                self._release_dispatch(campaign_id)
                return {"success": False, "error": f"Campaign '{campaign_id}' not found."}

            if camp.get("status") in ("Cancelled", "Archived"):
                self._release_dispatch(campaign_id)
                return {"success": False, "error": f"Cannot dispatch {camp.get('status')} campaign."}

            # Automatically populate queue if not yet enqueued
            q_items = self.queue.get_campaign_items(campaign_id, status_filter="Queued")
            if not q_items:
                self.prepare_queue(campaign_id)
                q_items = self.queue.get_campaign_items(campaign_id, status_filter="Queued")

            if not q_items:
                self._release_dispatch(campaign_id)
                return {
                    "success": False,
                    "error": "No eligible queued emails to send. Run preflight to verify approved drafts."
                }

            # Audit confirmation
            self.audit_logger.log_event(
                event_type="dispatch_confirmed",
                campaign_id=campaign_id,
                details={
                    "queued_to_send": len(q_items),
                    "operator_notes": operator_notes,
                    "confirmed_at": datetime.utcnow().isoformat() + "Z"
                }
            )

            # Mark campaign Sending
            self.campaign_store.update_campaign(campaign_id, {"status": "Sending"})
            self.audit_logger.log_event(
                event_type="dispatch_started",
                campaign_id=campaign_id,
                details={"batch_size": len(q_items)}
            )

            if synchronous:
                self._execute_dispatch_loop(campaign_id)
                return {
                    "success": True,
                    "campaign_id": campaign_id,
                    "status": "completed",
                    "dispatched_count": len(q_items)
                }
            else:
                worker_thread = threading.Thread(
                    target=self._execute_dispatch_loop,
                    args=(campaign_id,),
                    daemon=True,
                    name=f"dispatch-worker-{campaign_id}"
                )
                worker_thread.start()
                return {
                    "success": True,
                    "campaign_id": campaign_id,
                    "status": "started",
                    "queued_count": len(q_items),
                    "message": f"Confirmed. Dispatch worker initiated for {len(q_items)} emails."
                }

        except Exception as exc:
            self._release_dispatch(campaign_id)
            return {"success": False, "error": f"Failed to start dispatch: {str(exc)}"}

    def _release_dispatch(self, campaign_id: str):
        with self._lock:
            self._active_dispatches.discard(campaign_id)

    def _execute_dispatch_loop(self, campaign_id: str):
        """Worker loop processing queued items with deterministic rate delays and safety re-checks."""
        try:
            sent_in_run = 0
            max_per_run = self.rate_limiter.max_per_run

            while True:
                # 1. Check if campaign paused or cancelled during execution
                camp = self.campaign_store.get_campaign(campaign_id)
                if not camp:
                    break

                if camp.get("status") == "Paused":
                    self.delivery_logger.log_event(
                        dispatch_id=f"camp_{campaign_id}",
                        event="paused",
                        campaign_id=campaign_id,
                        status="Paused",
                        details={"message": "Dispatch paused by operator."}
                    )
                    break

                if camp.get("status") == "Cancelled":
                    self.queue.cancel_pending(campaign_id)
                    self.delivery_logger.log_event(
                        dispatch_id=f"camp_{campaign_id}",
                        event="cancelled",
                        campaign_id=campaign_id,
                        status="Cancelled",
                        details={"message": "Remaining queue cancelled by operator."}
                    )
                    break

                # 2. Check limits
                if not self.rate_limiter.can_send_today():
                    self.delivery_logger.log_event(
                        dispatch_id=f"camp_{campaign_id}",
                        event="blocked",
                        campaign_id=campaign_id,
                        status="RateLimited",
                        details={"reason": "Daily send limit reached"}
                    )
                    break

                if not self.rate_limiter.can_send_campaign(campaign_id):
                    self.delivery_logger.log_event(
                        dispatch_id=f"camp_{campaign_id}",
                        event="blocked",
                        campaign_id=campaign_id,
                        status="RateLimited",
                        details={"reason": "Campaign send limit reached"}
                    )
                    break

                if sent_in_run >= max_per_run:
                    # Bounded batch completed
                    break

                # 3. Atomically claim next item (Queued -> Sending)
                item = self.queue.claim_next(campaign_id)
                if not item:
                    # No more items in queue
                    break

                self.delivery_logger.log_event(
                    dispatch_id=item.dispatch_id,
                    event="claimed",
                    campaign_id=campaign_id,
                    draft_id=item.draft_id,
                    lead_id=item.lead_id,
                    recipient_email=item.recipient_email,
                    status="Sending"
                )

                # 4. Critical Send-Time Re-checks
                # (A) Demo lead protection
                if item.is_demo:
                    self.queue.mark_failed(item.dispatch_id, "Demo lead blocked from dispatch", "demo_blocked")
                    self.delivery_logger.log_event(
                        dispatch_id=item.dispatch_id,
                        event="blocked",
                        campaign_id=campaign_id,
                        draft_id=item.draft_id,
                        recipient_email=item.recipient_email,
                        status="Blocked",
                        error="Demo records cannot be dispatched"
                    )
                    continue

                # (B) Fresh suppression check
                if self.suppression_mgr.is_suppressed(item.recipient_email):
                    self.queue.mark_failed(item.dispatch_id, "Recipient is on suppression list", "suppressed")
                    self.delivery_logger.log_event(
                        dispatch_id=item.dispatch_id,
                        event="suppressed",
                        campaign_id=campaign_id,
                        draft_id=item.draft_id,
                        recipient_email=item.recipient_email,
                        status="Suppressed",
                        error="Suppressed recipient"
                    )
                    continue

                # (C) Fresh sent_log check (dual-check duplicate protection)
                sent_history = self.activity_logger.get_sent_emails()
                if item.recipient_email.lower().strip() in sent_history:
                    self.queue.mark_failed(item.dispatch_id, "Recipient previously successfully contacted", "duplicate")
                    self.delivery_logger.log_event(
                        dispatch_id=item.dispatch_id,
                        event="duplicate",
                        campaign_id=campaign_id,
                        draft_id=item.draft_id,
                        recipient_email=item.recipient_email,
                        status="Duplicate",
                        error="Duplicate send prevented"
                    )
                    continue

                # 5. Dispatch via sender
                self.delivery_logger.log_event(
                    dispatch_id=item.dispatch_id,
                    event="sending",
                    campaign_id=campaign_id,
                    draft_id=item.draft_id,
                    recipient_email=item.recipient_email,
                    status="Sending"
                )

                success, msg_id, err_msg, err_cat = self.sender.send_item(item)

                if success:
                    sent_in_run += 1
                    self.queue.mark_sent(item.dispatch_id, msg_id or "")
                    self.delivery_logger.log_event(
                        dispatch_id=item.dispatch_id,
                        event="sent",
                        campaign_id=campaign_id,
                        draft_id=item.draft_id,
                        recipient_email=item.recipient_email,
                        status="Sent",
                        details={"smtp_message_id": msg_id}
                    )
                else:
                    # Retry handling
                    if err_cat == "transient" and item.attempt_count < self.rate_limiter.max_retries:
                        # Schedule retry
                        self.queue.mark_retry(item.dispatch_id, err_msg or "Transient network error")
                        self.delivery_logger.log_event(
                            dispatch_id=item.dispatch_id,
                            event="retry_scheduled",
                            campaign_id=campaign_id,
                            draft_id=item.draft_id,
                            recipient_email=item.recipient_email,
                            status="RetryScheduled",
                            error=err_msg
                        )
                    else:
                        self.queue.mark_failed(item.dispatch_id, err_msg or "Dispatch failed", err_cat or "permanent")
                        self.delivery_logger.log_event(
                            dispatch_id=item.dispatch_id,
                            event="failed",
                            campaign_id=campaign_id,
                            draft_id=item.draft_id,
                            recipient_email=item.recipient_email,
                            status="Failed",
                            error=err_msg
                        )

                # Delay between sends
                dry_run = bool(self.rate_limiter.settings.get("dry_run", True))
                if not dry_run:
                    delay = self.rate_limiter.get_sleep_delay()
                    if delay > 0:
                        time.sleep(delay)

            # Finalize campaign status
            self._finalize_campaign_state(campaign_id)

        finally:
            self._release_dispatch(campaign_id)

    def _finalize_campaign_state(self, campaign_id: str):
        """Update campaign record status after dispatch execution."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp or camp.get("status") in ("Paused", "Cancelled", "Archived"):
            return

        items = self.queue.get_campaign_items(campaign_id)
        pending = sum(1 for i in items if i.status in ("Queued", "Sending"))
        sent = sum(1 for i in items if i.status == "Sent")
        failed = sum(1 for i in items if i.status == "Failed")
        blocked = sum(1 for i in items if i.status in ("Blocked", "Suppressed", "Duplicate"))

        # Update counters
        updates = {
            "queued_count": len(items),
            "sent_count": sent,
            "failed_count": failed,
            "suppressed_count": sum(1 for i in items if i.status == "Suppressed"),
            "duplicate_count": sum(1 for i in items if i.status == "Duplicate")
        }

        if pending == 0 and len(items) > 0:
            if failed > 0 or blocked > 0:
                updates["status"] = "Completed With Errors"
            else:
                updates["status"] = "Completed"

        self.campaign_store.update_campaign(campaign_id, updates)

    def pause_dispatch(self, campaign_id: str) -> Dict[str, Any]:
        """Operator action: Pause campaign dispatch."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return {"success": False, "error": f"Campaign '{campaign_id}' not found."}

        self.campaign_store.update_campaign(campaign_id, {"status": "Paused"})
        self.audit_logger.log_event(
            event_type="dispatch_paused",
            campaign_id=campaign_id,
            details={"paused_at": datetime.utcnow().isoformat() + "Z"}
        )
        return {"success": True, "campaign_id": campaign_id, "status": "Paused"}

    def cancel_dispatch(self, campaign_id: str) -> Dict[str, Any]:
        """Operator action: Cancel remaining sends for campaign."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return {"success": False, "error": f"Campaign '{campaign_id}' not found."}

        cancelled_count = self.queue.cancel_pending(campaign_id)
        self.campaign_store.update_campaign(campaign_id, {"status": "Cancelled"})
        self.audit_logger.log_event(
            event_type="dispatch_cancelled",
            campaign_id=campaign_id,
            details={"cancelled_items": cancelled_count}
        )
        return {
            "success": True,
            "campaign_id": campaign_id,
            "status": "Cancelled",
            "cancelled_count": cancelled_count
        }

    def execute_test_send(self, payload: TestSendPayload) -> Dict[str, Any]:
        """
        Operator action: Test Send.
        Dispatches a specific draft strictly to the designated test recipient.
        Never alters campaign recipient's outreach history or sent_log.csv!
        """
        draft = self.campaign_store.get_draft(payload.draft_id)
        if not draft:
            return {"success": False, "error": f"Draft '{payload.draft_id}' not found."}

        camp = self.campaign_store.get_campaign(draft.get("campaign_id"))
        att_path = (camp.get("attachment_path") if camp else None) or str(PRESENTATION_PATH)

        q_item = DispatchQueueItem(
            dispatch_id=f"test_{uuid.uuid4().hex[:10]}",
            campaign_id=draft.get("campaign_id", ""),
            draft_id=draft.get("draft_id", ""),
            lead_id=draft.get("lead_id", ""),
            recipient_email=payload.test_recipient.strip().lower(),
            recipient_name=draft.get("recipient_name") or "Valued Partner",
            company_name=draft.get("company_name") or "Test Organization",
            subject=draft.get("subject", ""),
            body=draft.get("body", ""),
            attachment_path=att_path,
            status="Sending",
            queued_at=datetime.utcnow().isoformat() + "Z",
            is_demo=False
        )

        self.audit_logger.log_event(
            event_type="test_send_requested",
            campaign_id=draft.get("campaign_id", ""),
            draft_id=draft.get("draft_id"),
            details={"test_recipient": payload.test_recipient}
        )

        success, msg_id, err_msg, err_cat = self.sender.send_item(
            item=q_item,
            is_test=True,
            test_recipient=payload.test_recipient
        )

        self.delivery_logger.log_event(
            dispatch_id=q_item.dispatch_id,
            event="test_sent" if success else "failed",
            campaign_id=draft.get("campaign_id", ""),
            draft_id=draft.get("draft_id"),
            recipient_email=payload.test_recipient,
            status="Sent" if success else "Failed",
            error=err_msg,
            details={"is_test": True, "smtp_message_id": msg_id}
        )

        return {
            "success": success,
            "test_recipient": payload.test_recipient,
            "smtp_message_id": msg_id,
            "error": err_msg,
            "error_category": err_cat
        }
