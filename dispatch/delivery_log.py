"""
Delivery Telemetry and Consequential Audit Logger for Resonance Dispatch (Phase 5).
Maintains data/dispatch_log.json and data/audit_log.json.
Provides full lifecycle tracing without ever storing sensitive credentials.
"""

import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import DISPATCH_LOG_FILE, AUDIT_LOG_FILE
from dispatch.models import DeliveryLogEvent, AuditLogEntry


class DeliveryLogger:
    """Logs granular delivery lifecycle events to data/dispatch_log.json."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        storage_file: Optional[Path] = None
    ):
        self.log_file = log_file or storage_file or DISPATCH_LOG_FILE
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def log_event(
        self,
        dispatch_id: str,
        event: str = "",
        campaign_id: str = "",
        draft_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        recipient_email: str = "",
        status: Optional[str] = None,
        error: Optional[str] = None,
        event_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a delivery event."""
        # Sanitize details to never leak passwords
        clean_details = (details or {}).copy()
        if draft_id:
            clean_details["draft_id"] = draft_id
        if lead_id:
            clean_details["lead_id"] = lead_id

        for k in list(clean_details.keys()):
            if any(term in k.lower() for term in ("password", "secret", "token", "key")):
                clean_details[k] = "••••••••"

        resolved_event = event or event_type or "unknown"

        ev = DeliveryLogEvent(
            event_id=f"evt_{uuid.uuid4().hex[:10]}",
            dispatch_id=dispatch_id,
            campaign_id=campaign_id,
            recipient_email=recipient_email,
            event_type=resolved_event,
            status=status or resolved_event.capitalize(),
            error=error,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details=clean_details
        ).to_dict()

        with self._lock:
            self._ensure_storage()
            events = []
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                events = []

            events.insert(0, ev)
            # Cap at 2000 events to prevent runaway file size
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(events[:2000], f, indent=2)

        return ev

    def get_campaign_events(self, campaign_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List delivery events for a specific campaign."""
        return self.list_events(limit=limit, campaign_id=campaign_id)

    def get_all_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all delivery events."""
        return self.list_events(limit=limit)

    def list_events(
        self,
        limit: int = 100,
        campaign_id: Optional[str] = None,
        dispatch_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List delivery events sorted by timestamp descending."""
        with self._lock:
            self._ensure_storage()
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    events = json.load(f)
                    if campaign_id:
                        events = [e for e in events if e.get("campaign_id") == campaign_id]
                    if dispatch_id:
                        events = [e for e in events if e.get("dispatch_id") == dispatch_id]
                    return events[:limit]
            except Exception:
                return []


class AuditLogger:
    """Logs consequential operator actions to data/audit_log.json."""

    def __init__(
        self,
        audit_file: Optional[Path] = None,
        storage_file: Optional[Path] = None
    ):
        self.audit_file = audit_file or storage_file or AUDIT_LOG_FILE
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.audit_file.exists():
            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def log_event(
        self,
        event_type: str = "",
        campaign_id: str = "",
        draft_id: Optional[str] = None,
        operator: str = "Operator",
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Alias for log_action."""
        return self.log_action(
            action=action or event_type,
            operator=operator,
            campaign_id=campaign_id,
            draft_id=draft_id,
            details=details
        )

    def log_action(
        self,
        action: str,
        operator: str = "Operator",
        campaign_id: Optional[str] = None,
        draft_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an operator action."""
        clean_details = (details or {}).copy()
        for k in list(clean_details.keys()):
            if any(term in k.lower() for term in ("password", "secret", "token", "key")):
                clean_details[k] = "••••••••"

        entry = AuditLogEntry(
            audit_id=f"aud_{uuid.uuid4().hex[:10]}",
            action=action,
            timestamp=datetime.utcnow().isoformat() + "Z",
            operator=operator,
            campaign_id=campaign_id,
            draft_id=draft_id,
            details=clean_details
        ).to_dict()

        with self._lock:
            self._ensure_storage()
            entries = []
            try:
                with open(self.audit_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

            entries.insert(0, entry)
            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump(entries[:1000], f, indent=2)

        return entry

    def list_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_storage()
            try:
                with open(self.audit_file, "r", encoding="utf-8") as f:
                    return json.load(f)[:limit]
            except Exception:
                return []
