"""
Persistent Concurrency-Safe Dispatch Queue for Resonance (Phase 5).
Maintains data/dispatch_queue.json. Enforces atomic item claiming (Queued -> Sending),
idempotency, and safe crash recovery.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import DISPATCH_QUEUE_FILE
from dispatch.models import DispatchQueueItem


class DispatchQueue:
    """Thread-safe persistent queue with atomic item claiming."""

    def __init__(
        self,
        queue_file: Optional[Path] = None,
        storage_file: Optional[Path] = None
    ):
        self.file_path = queue_file or storage_file or DISPATCH_QUEUE_FILE
        self._lock = threading.Lock()
        self._ensure_storage()
        # Run crash recovery on initialization
        self.recover_stale_sending()

    def _ensure_storage(self):
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _read_all_unlocked(self) -> List[Dict[str, Any]]:
        self._ensure_storage()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_all_unlocked(self, items: List[Dict[str, Any]]):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)

    def enqueue_items(self, items: List[DispatchQueueItem]) -> int:
        """
        Append queue items if they do not already exist in the queue for (campaign_id, draft_id).
        """
        with self._lock:
            existing = self._read_all_unlocked()
            existing_keys = {
                (q.get("campaign_id"), q.get("draft_id"))
                for q in existing
                if q.get("status") not in ("Cancelled",)
            }

            added = 0
            for item in items:
                key = (item.campaign_id, item.draft_id)
                if key not in existing_keys:
                    existing.append(item.to_dict())
                    existing_keys.add(key)
                    added += 1

            if added > 0:
                self._write_all_unlocked(existing)

            return added

    def enqueue(self, item: DispatchQueueItem) -> bool:
        """Enqueue a single item. Returns True if enqueued, False if already in queue."""
        added = self.enqueue_items([item])
        return added > 0

    def claim_next(self, campaign_id: Optional[str] = None) -> Optional[DispatchQueueItem]:
        """
        Atomically claim the next 'Queued' or 'RetryScheduled' item.
        Transitions state atomically from Queued -> Sending.
        Prevents race conditions and duplicate sends across concurrent workers.
        """
        with self._lock:
            items = self._read_all_unlocked()
            now_iso = datetime.utcnow().isoformat() + "Z"

            for item in items:
                if campaign_id and item.get("campaign_id") != campaign_id:
                    continue

                if item.get("status") in ("Queued", "RetryScheduled"):
                    item["status"] = "Sending"
                    item["started_at"] = now_iso
                    item["attempt_count"] = item.get("attempt_count", 0) + 1
                    self._write_all_unlocked(items)
                    return DispatchQueueItem(**item)

            return None

    def update_item(self, dispatch_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a specific queue item's status, error, or delivery telemetry."""
        with self._lock:
            items = self._read_all_unlocked()
            target = None

            for item in items:
                if item.get("dispatch_id") == dispatch_id:
                    for k, v in updates.items():
                        item[k] = v
                    target = item
                    break

            if target:
                self._write_all_unlocked(items)

            return target.copy() if target else None

    def mark_sent(self, dispatch_id: str, smtp_message_id: str = ""):
        """Mark an item as successfully sent."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        self.update_item(dispatch_id, {
            "status": "Sent",
            "completed_at": now_iso,
            "smtp_message_id": smtp_message_id,
            "last_error": None
        })

    def mark_failed(self, dispatch_id: str, error_message: str, error_category: str = "permanent"):
        """Mark an item as permanently failed."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        self.update_item(dispatch_id, {
            "status": "Failed",
            "completed_at": now_iso,
            "last_error": error_message,
            "error_category": error_category
        })

    def mark_retry(self, dispatch_id: str, error_message: str):
        """Mark an item for scheduled bounded retry."""
        self.update_item(dispatch_id, {
            "status": "RetryScheduled",
            "last_error": error_message
        })

    def get_item(self, dispatch_id: str) -> Optional[DispatchQueueItem]:
        """Retrieve a specific queue item by dispatch_id."""
        with self._lock:
            items = self._read_all_unlocked()
            for item in items:
                if item.get("dispatch_id") == dispatch_id:
                    return DispatchQueueItem(**item)
            return None

    def get_campaign_items(
        self,
        campaign_id: str,
        status_filter: Optional[str] = None
    ) -> List[DispatchQueueItem]:
        """List queue items for a specific campaign."""
        with self._lock:
            items = self._read_all_unlocked()
            res = [i for i in items if i.get("campaign_id") == campaign_id]
            if status_filter and status_filter.lower() != "all":
                res = [i for i in res if i.get("status", "").lower() == status_filter.lower()]
            return [DispatchQueueItem(**i) for i in res]

    def get_all_items(self) -> List[DispatchQueueItem]:
        """Retrieve all items in the queue."""
        with self._lock:
            items = self._read_all_unlocked()
            return [DispatchQueueItem(**i) for i in items]

    def list_items(
        self,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List raw queue dict items with optional filtering."""
        with self._lock:
            items = self._read_all_unlocked()
            if campaign_id:
                items = [i for i in items if i.get("campaign_id") == campaign_id]
            if status and status.lower() != "all":
                items = [i for i in items if i.get("status", "").lower() == status.lower()]
            return items

    def cancel_pending(self, campaign_id: str) -> int:
        """
        Cancel remaining pending items in a campaign.
        Already 'Sent' or 'Sending' items are preserved.
        """
        with self._lock:
            items = self._read_all_unlocked()
            now_iso = datetime.utcnow().isoformat() + "Z"
            cancelled_count = 0

            for item in items:
                if item.get("campaign_id") == campaign_id and item.get("status") in ("Queued", "RetryScheduled"):
                    item["status"] = "Cancelled"
                    item["completed_at"] = now_iso
                    item["last_error"] = "Cancelled by operator"
                    cancelled_count += 1

            if cancelled_count > 0:
                self._write_all_unlocked(items)

            return cancelled_count

    def recover_stale_sending(self) -> int:
        """
        Crash Recovery: If the system restarted while an item was in 'Sending' state,
        transition it to 'Blocked - Delivery state requires review' rather than blindly resending.
        """
        with self._lock:
            items = self._read_all_unlocked()
            recovered = 0
            now_iso = datetime.utcnow().isoformat() + "Z"

            for item in items:
                if item.get("status") == "Sending":
                    item["status"] = "Blocked"
                    item["completed_at"] = now_iso
                    item["last_error"] = "Blocked - Delivery state requires review after server restart."
                    item["error_category"] = "CrashRecovery"
                    recovered += 1

            if recovered > 0:
                self._write_all_unlocked(items)

            return recovered
