"""
Strict schemas and Pydantic models for AI Lead Intelligence and Enrichment.
Ensures zero fabricated data, explicit null handling, and evidence storage.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    """Specific evidence item supporting an AI-derived field."""
    url: Optional[str] = None
    field: str
    evidence: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ClassificationResult(BaseModel):
    """B2B vs Individual classification with reason and evidence."""
    classification: Literal["Business", "Individual", "Unclassified"] = "Unclassified"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    evidence: List[EvidenceItem] = []

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.5


class BuyerRelevanceResult(BaseModel):
    """Informational buyer relevance to the Singing Bowls export business."""
    relevance: Literal["High", "Medium", "Low", "Unknown"] = "Unknown"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    evidence: List[EvidenceItem] = []

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.5


VALID_ROLES = [
    "Owner",
    "Founder",
    "Director",
    "Procurement",
    "Purchasing",
    "Buyer",
    "Sales",
    "Wholesale",
    "Operations",
    "General Contact",
    "Unknown"
]


class PublicContact(BaseModel):
    """Public business contact extracted from verified web pages."""
    name: Optional[str] = None
    role: str = "Unknown"
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v):
        if not v or not isinstance(v, str):
            return "Unknown"
        v_clean = v.strip().title()
        for valid in VALID_ROLES:
            if valid.lower() in v_clean.lower():
                return valid
        return "General Contact" if v_clean else "Unknown"


class BusinessDetails(BaseModel):
    """Factual business capabilities extracted from verified web pages."""
    company_name: Optional[str] = None
    business_type: Optional[str] = None  # e.g., "Wholesale distributor", "Retail boutique", "Yoga studio"
    industry: Optional[str] = None       # e.g., "Sound Healing / Wellness", "Musical Instruments"
    company_description: Optional[str] = None
    wholesale_available: Optional[bool] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class LeadEnrichmentRecord(BaseModel):
    """Comprehensive lead intelligence document."""
    lead_id: str
    enrichment_status: Literal["enriched", "failed", "blocked", "needs_enrichment", "not_applicable"] = "needs_enrichment"
    enriched_at: Optional[str] = None
    enrichment_run_id: Optional[str] = None
    classification: Optional[ClassificationResult] = None
    buyer_relevance: Optional[BuyerRelevanceResult] = None
    business_details: Optional[BusinessDetails] = None
    public_contact: Optional[PublicContact] = None
    evidence: List[EvidenceItem] = []
    ai_model: Optional[str] = None
    ai_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    pages_crawled: List[str] = []
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class EnrichmentRunRecord(BaseModel):
    """Audit log of an enrichment batch run."""
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    lead_count: int = 0
    successful_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    ai_calls: int = 0
    websites_crawled: int = 0
    status: Literal["running", "completed", "failed"] = "running"
    duration: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
