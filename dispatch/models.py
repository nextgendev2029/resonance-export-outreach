"""
Data models and schemas for Resonance Dispatch Engine & Campaign Analytics (Phase 5).
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DispatchQueueItem(BaseModel):
    """Represents a single message queued for dispatch."""
    dispatch_id: str
    campaign_id: str
    draft_id: str
    lead_id: Optional[str] = ""
    recipient_email: str
    recipient_name: Optional[str] = "Valued Partner"
    company_name: Optional[str] = "Organization"
    subject: str
    body: str
    attachment_path: Optional[str] = ""
    status: str = "Queued"  # Queued, Sending, Sent, Failed, Suppressed, Duplicate, Blocked, Cancelled, RetryScheduled
    queued_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempt_count: int = 0
    last_error: Optional[str] = None
    error_category: Optional[str] = None
    smtp_message_id: Optional[str] = None
    is_demo: bool = False
    is_dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class PreflightReport(BaseModel):
    """Pre-dispatch audit report verifying final eligibility and system constraints."""
    campaign_id: str
    campaign_name: Optional[str] = ""
    total_drafts: Optional[int] = 0
    approved_count: int = 0
    currently_eligible: int = 0
    blocked_count: int = 0
    duplicate_count: int = 0
    suppressed_count: int = 0
    demo_count: int = 0
    invalid_count: int = 0
    attachment_ready: bool = False
    attachment_filename: Optional[str] = None
    dry_run: bool = True
    daily_limit: int = 100
    sent_today: int = 0
    remaining_today: int = 100
    campaign_limit: Optional[int] = 50
    campaign_sent: Optional[int] = 0
    remaining_campaign: Optional[int] = 50
    ready: bool = False
    blocking_reasons: List[str] = Field(default_factory=list)
    eligible_draft_ids: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SuppressionRecord(BaseModel):
    """Contact suppression entry."""
    email: str
    reason: str  # unsubscribe, manual_suppression, bounce, complaint, invalid_contact, operator_block
    notes: Optional[str] = None
    operator_note: Optional[str] = None
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DeliveryLogEvent(BaseModel):
    """Granular delivery telemetry event."""
    event_id: str
    dispatch_id: str
    campaign_id: str
    recipient_email: str
    event_type: str  # queued, claimed, sending, sent, failed, retry_scheduled, suppressed, duplicate, cancelled, blocked
    status: Optional[str] = None
    error: Optional[str] = None
    timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AuditLogEntry(BaseModel):
    """Consequential action audit log entry."""
    audit_id: str
    action: str  # campaign_created, draft_approved, draft_rejected, dispatch_created, dispatch_confirmed, dispatch_started, dispatch_paused, dispatch_cancelled, contact_suppressed, test_send_requested
    timestamp: str
    operator: str = "Operator"
    campaign_id: Optional[str] = None
    draft_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DispatchConfirmPayload(BaseModel):
    """Explicit confirmation payload required to start dispatch."""
    confirmed: bool = True
    operator_notes: Optional[str] = ""


class TestSendPayload(BaseModel):
    """Explicit test send request."""
    draft_id: str
    test_recipient: str
    override_subject: Optional[str] = None
    override_body: Optional[str] = None


class SuppressionCreatePayload(BaseModel):
    """Request payload to manually suppress an email address."""
    email: str
    reason: str = "manual_suppression"
    operator_note: Optional[str] = ""
