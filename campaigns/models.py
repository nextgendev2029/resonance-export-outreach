"""
Data schemas and models for Resonance Campaigns & Outreach Queue (Phase 4).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AudienceFilters(BaseModel):
    """Configurable rules to evaluate lead eligibility for an outreach campaign."""
    dataset: str = "real"  # 'real', 'demo', 'all'
    classification: Optional[List[str]] = Field(default_factory=lambda: ["Business"])
    validation_status: Optional[List[str]] = Field(default_factory=lambda: ["Valid"])
    buyer_relevance: Optional[List[str]] = Field(default_factory=lambda: ["High", "Medium"])
    country: Optional[str] = None
    source_platform: Optional[str] = None
    enrichment_status: Optional[str] = None
    outreach_status: Optional[str] = None
    contacted_status: str = "never"  # 'never', 'attempted', 'contacted', 'failed', 'all'


class AudiencePreviewResponse(BaseModel):
    """Summary of audience evaluation, showing eligible leads and explicit exclusion reasons."""
    total_evaluated: int
    eligible_count: int
    excluded_count: int
    exclusion_reasons: Dict[str, int]
    eligible_lead_ids: List[str]
    sample_eligible: List[Dict[str, Any]] = Field(default_factory=list)
    sample_excluded: List[Dict[str, Any]] = Field(default_factory=list)


class PersonalizationEvidence(BaseModel):
    """Ground-truth citation used in an email draft."""
    field: str
    url: Optional[str] = None
    evidence: str


class DraftVersion(BaseModel):
    """Archived historical version of a draft."""
    version: int
    generated_at: str
    subject: str
    opening_line: str
    body: str
    closing: str
    ai_confidence: float
    personalization_reason: Optional[str] = None


class DraftValidationResult(BaseModel):
    """Validation report ensuring factual grounding and spam safety."""
    is_grounded: bool = True
    word_count: int = 0
    spam_detected: bool = False
    tone_appropriate: bool = True
    issues: List[str] = Field(default_factory=list)
    suggested_status: str = "Draft"  # 'Draft' or 'Needs Review'


class OutreachDraft(BaseModel):
    """Individual outreach draft for a specific prospect."""
    draft_id: str
    campaign_id: str
    lead_id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    company_name: Optional[str] = None
    country: Optional[str] = None

    subject: str
    opening_line: str
    body: str
    closing: str

    classification: str = "Business"
    buyer_relevance: str = "Unknown"
    ai_confidence: float = 0.85

    personalization_reason: Optional[str] = None
    personalization_evidence: List[Dict[str, Any]] = Field(default_factory=list)

    # Versioning & Auditability
    original_ai_draft: Dict[str, Any] = Field(default_factory=dict)
    operator_edited_draft: Optional[Dict[str, Any]] = None
    version_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Status: Draft, Needs Review, Edited, Approved, Rejected, Archived
    status: str = "Draft"
    validation: Dict[str, Any] = Field(default_factory=dict)

    created_at: str
    updated_at: str
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None

    is_demo: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CampaignRecord(BaseModel):
    """Campaign definition and aggregate operational metrics."""
    campaign_id: str
    name: str
    created_at: str
    updated_at: str
    # Status: Draft, Building Audience, Generating Drafts, Review, Partially Approved, Approved, Queued, Sending, Completed, Completed With Errors, Paused, Cancelled, Archived
    status: str = "Draft"

    audience_filters: Dict[str, Any] = Field(default_factory=dict)
    subject_template: str = "Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog & Export Pricing"
    body_template: str = ""
    attachment_path: str = "assets/company_presentation.pdf"
    attachment_ready: bool = True
    reply_to: Optional[str] = None
    sender_identity: Optional[str] = "Himalayan Singing Bowls Export Operations"

    # Metrics
    eligible_count: int = 0
    excluded_count: int = 0
    draft_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    needs_review_count: int = 0
    queued_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    suppressed_count: int = 0
    duplicate_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

