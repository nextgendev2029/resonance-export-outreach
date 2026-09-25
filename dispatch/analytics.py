"""
Campaign Analytics and Telemetry Aggregator for Resonance (Phase 5).
Computes genuine metrics from actual persisted campaign, queue, log, and sent history.
Strictly adheres to ground-truth reporting: displays 'Not available' for untracked metrics.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from campaigns.campaign_store import CampaignStore
from dispatch.queue import DispatchQueue
from dispatch.delivery_log import DeliveryLogger
from dispatch.suppression import SuppressionManager
from app_logging.activity_logger import ActivityLogger


class AnalyticsService:
    """Aggregates campaign and dispatch operational telemetry."""

    def __init__(
        self,
        campaign_store: Optional[CampaignStore] = None,
        queue: Optional[DispatchQueue] = None,
        delivery_logger: Optional[DeliveryLogger] = None,
        suppression_mgr: Optional[SuppressionManager] = None,
        activity_logger: Optional[ActivityLogger] = None
    ):
        self.campaign_store = campaign_store or CampaignStore()
        self.queue = queue or DispatchQueue()
        self.delivery_logger = delivery_logger or DeliveryLogger()
        self.suppression_mgr = suppression_mgr or SuppressionManager()
        self.activity_logger = activity_logger or ActivityLogger()

    def get_overview(self) -> Dict[str, Any]:
        """Global operations overview metrics."""
        campaigns = self.campaign_store.list_campaigns()
        queue_items = self.queue.get_all_items()
        drafts = self.campaign_store.list_all_drafts()
        suppressions = self.suppression_mgr.list_suppressions()

        total_campaigns = len(campaigns)
        total_drafts = len(drafts)
        approved_count = sum(1 for d in drafts if d.get("status") == "Approved")

        queued_count = sum(1 for i in queue_items if i.status == "Queued")
        sending_count = sum(1 for i in queue_items if i.status == "Sending")
        sent_count = sum(1 for i in queue_items if i.status == "Sent")
        failed_count = sum(1 for i in queue_items if i.status == "Failed")
        duplicate_count = sum(1 for i in queue_items if i.status == "Duplicate")
        blocked_count = sum(1 for i in queue_items if i.status in ("Blocked", "RateLimited"))
        suppressed_in_queue = sum(1 for i in queue_items if i.status == "Suppressed")

        total_suppressed_contacts = len(suppressions)

        return {
            "campaigns_count": total_campaigns,
            "drafts_count": total_drafts,
            "approved_count": approved_count,
            "queued_count": queued_count,
            "sending_count": sending_count,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "duplicate_count": duplicate_count,
            "blocked_count": blocked_count,
            "suppressed_count": total_suppressed_contacts,
            "suppressed_in_queue": suppressed_in_queue,
            # Factual reporting: untracked metrics are reported as unavailable
            "open_rate": "Not available",
            "reply_rate": "Not available",
            "conversion_rate": "Not available",
            "telemetry_note": "Resonance tracks verified SMTP submissions. External pixel tracking and read receipts are not simulated."
        }

    def get_campaigns_table(self) -> List[Dict[str, Any]]:
        """Performance breakdown table per campaign."""
        campaigns = self.campaign_store.list_campaigns()
        all_queue_items = self.queue.get_all_items()

        # Group queue items by campaign_id
        camp_queue: Dict[str, List[Any]] = {}
        for item in all_queue_items:
            cid = item.campaign_id
            if cid not in camp_queue:
                camp_queue[cid] = []
            camp_queue[cid].append(item)

        results = []
        for c in campaigns:
            cid = c.get("campaign_id")
            items = camp_queue.get(cid, [])

            sent = sum(1 for i in items if i.status == "Sent")
            failed = sum(1 for i in items if i.status == "Failed")
            queued = sum(1 for i in items if i.status in ("Queued", "Sending"))
            suppressed = sum(1 for i in items if i.status == "Suppressed")
            duplicate = sum(1 for i in items if i.status == "Duplicate")

            results.append({
                "campaign_id": cid,
                "name": c.get("name"),
                "status": c.get("status"),
                "audience_count": c.get("eligible_count", 0),
                "draft_count": c.get("draft_count", 0),
                "approved_count": c.get("approved_count", 0),
                "queued_count": queued,
                "sent_count": sent,
                "failed_count": failed,
                "suppressed_count": suppressed,
                "duplicate_count": duplicate,
                "updated_at": c.get("updated_at")
            })

        return results

    def get_campaign_detail(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Detailed metrics for a single campaign."""
        camp = self.campaign_store.get_campaign(campaign_id)
        if not camp:
            return None

        drafts = self.campaign_store.list_campaign_drafts(campaign_id, status_filter="all")
        items = self.queue.get_campaign_items(campaign_id)

        status_breakdown = {
            "Draft": sum(1 for d in drafts if d.get("status") == "Draft"),
            "Needs Review": sum(1 for d in drafts if d.get("status") == "Needs Review"),
            "Edited": sum(1 for d in drafts if d.get("status") == "Edited"),
            "Approved": sum(1 for d in drafts if d.get("status") == "Approved"),
            "Rejected": sum(1 for d in drafts if d.get("status") == "Rejected"),
            "Archived": sum(1 for d in drafts if d.get("status") == "Archived"),
        }

        queue_breakdown = {
            "Queued": sum(1 for i in items if i.status == "Queued"),
            "Sending": sum(1 for i in items if i.status == "Sending"),
            "Sent": sum(1 for i in items if i.status == "Sent"),
            "Failed": sum(1 for i in items if i.status == "Failed"),
            "Cancelled": sum(1 for i in items if i.status == "Cancelled"),
            "Blocked": sum(1 for i in items if i.status in ("Blocked", "RateLimited")),
            "Suppressed": sum(1 for i in items if i.status == "Suppressed"),
            "Duplicate": sum(1 for i in items if i.status == "Duplicate")
        }

        events = self.delivery_logger.get_campaign_events(campaign_id, limit=50)

        return {
            "campaign_id": campaign_id,
            "name": camp.get("name"),
            "status": camp.get("status"),
            "created_at": camp.get("created_at"),
            "updated_at": camp.get("updated_at"),
            "audience": {
                "eligible": camp.get("eligible_count", 0),
                "excluded": camp.get("excluded_count", 0),
            },
            "drafts": {
                "total": len(drafts),
                "breakdown": status_breakdown
            },
            "dispatch": {
                "total_queued": len(items),
                "breakdown": queue_breakdown,
                "sent_success_rate": f"{(queue_breakdown['Sent'] / len(items) * 100):.1f}%" if len(items) > 0 and queue_breakdown['Sent'] > 0 else "0.0%"
            },
            "recent_events": events,
            "open_rate": "Not available",
            "reply_rate": "Not available"
        }

    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get latest activity events mapped to campaign titles."""
        events = self.delivery_logger.get_all_events(limit=limit)
        campaigns = {c.get("campaign_id"): c.get("name") for c in self.campaign_store.list_campaigns()}

        activity = []
        for ev in events:
            cid = ev.get("campaign_id", "")
            cname = campaigns.get(cid) or (f"Campaign {cid[:8]}" if cid else "System")

            activity.append({
                "timestamp": ev.get("timestamp"),
                "campaign_id": cid,
                "campaign_name": cname,
                "dispatch_id": ev.get("dispatch_id"),
                "recipient_email": ev.get("recipient_email") or "-",
                "event": ev.get("event"),
                "status": ev.get("status"),
                "error": ev.get("error")
            })

        return activity
