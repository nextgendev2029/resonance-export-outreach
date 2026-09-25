"""
Persistent Suppression List Manager for Resonance Dispatch Engine (Phase 5).
Maintains data/suppression_list.json. Prevents dispatch to unsubscribed, bounced,
or operator-blocked recipients.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import SUPPRESSION_LIST_FILE
from dispatch.models import SuppressionRecord


class SuppressionManager:
    """Thread-safe persistent suppression list."""

    def __init__(
        self,
        suppression_file: Optional[Path] = None,
        storage_file: Optional[Path] = None
    ):
        self.file_path = suppression_file or storage_file or SUPPRESSION_LIST_FILE
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        """Initialize suppression JSON file if not present."""
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def list_suppressions(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all suppression entries, optionally filtered by email search query."""
        with self._lock:
            self._ensure_storage()
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if search and search.strip():
                        q = search.strip().lower()
                        data = [r for r in data if q in r.get("email", "").lower()]
                    return sorted(data, key=lambda x: x.get("created_at", ""), reverse=True)
            except Exception:
                return []

    def is_suppressed(self, email: str) -> bool:
        """Check if normalized email address is present in suppression list."""
        if not email:
            return False
        clean = email.strip().lower()
        records = self.list_suppressions()
        for r in records:
            if r.get("email", "").strip().lower() == clean:
                return True
        return False

    def get_suppression(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve suppression record for a specific email."""
        clean = email.strip().lower()
        records = self.list_suppressions()
        for r in records:
            if r.get("email", "").strip().lower() == clean:
                return r
        return None

    def add_suppression(
        self,
        email: str,
        reason: str = "manual_suppression",
        operator_note: str = "",
        notes: str = ""
    ) -> Optional[SuppressionRecord]:
        """Add an email to persistent suppression list."""
        clean = email.strip().lower()
        if not clean or "@" not in clean:
            return None

        now_iso = datetime.utcnow().isoformat() + "Z"
        note_val = operator_note or notes or ""

        with self._lock:
            self._ensure_storage()
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []

            # Check existing
            for r in data:
                if r.get("email", "").strip().lower() == clean:
                    r["reason"] = reason
                    r["operator_note"] = note_val
                    r["notes"] = note_val
                    r["created_at"] = now_iso
                    with open(self.file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    return SuppressionRecord(**r)

            record = SuppressionRecord(
                email=clean,
                reason=reason,
                operator_note=note_val,
                notes=note_val,
                created_at=now_iso
            )
            data.insert(0, record.to_dict())
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        return record

    def remove_suppression(self, email: str) -> bool:
        """Remove an email from suppression list."""
        clean = email.strip().lower()
        with self._lock:
            self._ensure_storage()
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []

            filtered = [r for r in data if r.get("email", "").strip().lower() != clean]
            if len(filtered) != len(data):
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, indent=2)
                return True
        return False
