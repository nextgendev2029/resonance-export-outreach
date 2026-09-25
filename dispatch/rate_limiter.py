"""
Rate Limiter and Operational Throttling Manager for Resonance Dispatch (Phase 5).
Tracks daily, campaign, and run volume thresholds. Calculates remaining capacity
and enforces polite pacing to preserve sender reputation.
"""

import csv
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from config import SENT_LOG_CSV, load_settings
from dispatch.delivery_log import DeliveryLogger


class RateLimiter:
    """Calculates operational send limits and pacing delays."""

    def __init__(
        self,
        settings: Optional[Dict[str, Any]] = None,
        sent_log_file: Optional[Path] = None,
        delivery_logger: Optional[DeliveryLogger] = None,
        activity_logger: Optional[Any] = None
    ):
        self.settings = settings or load_settings()
        self.sent_log_file = sent_log_file or SENT_LOG_CSV
        self.delivery_logger = delivery_logger or DeliveryLogger()
        self.activity_logger = activity_logger

    @property
    def max_per_day(self) -> int:
        return int(self.settings.get("max_emails_per_day", self.settings.get("daily_send_limit", 100)))

    @property
    def max_per_campaign(self) -> int:
        return int(self.settings.get("max_emails_per_campaign", 50))

    @property
    def max_per_run(self) -> int:
        return int(self.settings.get("max_emails_per_run", 25))

    @property
    def min_delay(self) -> float:
        return float(self.settings.get("min_delay_seconds", self.settings.get("send_delay_seconds", 3)))

    @property
    def max_delay(self) -> float:
        min_d = self.min_delay
        val = float(self.settings.get("max_delay_seconds", min_d + 5))
        return max(min_d, val)

    @property
    def max_retries(self) -> int:
        return int(self.settings.get("max_retries", 2))

    def get_sent_today_count(self) -> int:
        """Count successful sends recorded today in data/sent_log.csv."""
        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        count = 0

        if not self.sent_log_file.exists():
            return 0

        try:
            with open(self.sent_log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = (row.get("status") or "").strip().lower()
                    ts = (row.get("timestamp") or "").strip()
                    if status in ("sent", "delivered", "success") and ts.startswith(today_prefix):
                        count += 1
        except Exception:
            pass

        return count

    def get_sent_campaign_count(self, campaign_id: str) -> int:
        """Count successful sends for a specific campaign from delivery log."""
        if not campaign_id:
            return 0
        events = self.delivery_logger.list_events(limit=2000, campaign_id=campaign_id)
        return sum(1 for e in events if e.get("event_type") == "sent" or e.get("status") == "Sent")

    def get_campaign_sent_count(self, campaign_id: str) -> int:
        """Alias for get_sent_campaign_count."""
        return self.get_sent_campaign_count(campaign_id)

    def get_remaining_today(self) -> int:
        return max(0, self.max_per_day - self.get_sent_today_count())

    def get_remaining_campaign(self, campaign_id: str) -> int:
        return max(0, self.max_per_campaign - self.get_sent_campaign_count(campaign_id))

    def can_send_today(self) -> bool:
        return self.get_remaining_today() > 0

    def can_send_campaign(self, campaign_id: str) -> bool:
        return self.get_remaining_campaign(campaign_id) > 0

    def get_remaining_capacity(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate live capacity based on configured limits and historical counts."""
        daily_limit = self.max_per_day
        campaign_limit = self.max_per_campaign
        run_limit = self.max_per_run

        sent_today = self.get_sent_today_count()
        remaining_today = max(0, daily_limit - sent_today)

        campaign_sent = self.get_sent_campaign_count(campaign_id) if campaign_id else 0
        remaining_campaign = max(0, campaign_limit - campaign_sent)

        can_send = remaining_today > 0 and (remaining_campaign > 0 if campaign_id else True)

        return {
            "daily_limit": daily_limit,
            "sent_today": sent_today,
            "remaining_today": remaining_today,
            "campaign_limit": campaign_limit,
            "campaign_sent": campaign_sent,
            "remaining_campaign": remaining_campaign,
            "run_limit": run_limit,
            "can_send": can_send
        }

    def get_delay_seconds(self) -> float:
        """Calculate bounded delay between dispatches."""
        min_d = self.min_delay
        max_d = self.max_delay
        if min_d == max_d:
            return min_d
        return round(random.uniform(min_d, max_d), 2)

    def get_sleep_delay(self) -> float:
        """Alias for get_delay_seconds."""
        return self.get_delay_seconds()
