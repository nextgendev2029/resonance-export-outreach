"""
Discovery Data Models for Resonance - Export Outreach & Lead Operations.
Defines Pydantic schemas for seller discovery profiles, provider health,
normalized buyer leads, search results, and discovery run audit logs.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DiscoveryProfile(BaseModel):
    """Structured seller and product profile guiding buyer discovery."""
    product_name: str = Field(default="Singing Bowls", description="Target export product")
    product_category: str = Field(default="Home Decor", description="Broader trade category")
    product_description: Optional[str] = Field(
        default="Handcrafted singing bowls suitable for home decor, wellness spaces, meditation stores and lifestyle retailers.",
        description="Detailed product description and commercial positioning"
    )
    target_country: str = Field(default="United States", description="Target buyer market country")
    target_state: Optional[str] = Field(default="", description="Optional specific US state restriction")
    buyer_types: List[str] = Field(
        default_factory=lambda: [
            "Importer",
            "Distributor",
            "Wholesaler",
            "Retailer",
            "Home Decor Store",
            "Gift Shop",
            "Wellness Store",
            "Interior Decor Business",
            "Lifestyle Store",
            "Boutique Store",
            "B2B Buyer",
            "Specialty Store"
        ],
        description="Target buyer business classifications"
    )
    keywords: Optional[List[str]] = Field(default_factory=list, description="Explicit operator search qualifiers")
    preferred_buyer_size: Optional[str] = Field(default="any", description="Preferred scale of buyer organization")
    website_required: Optional[bool] = Field(default=False, description="Whether leads must possess a verified domain")
    email_required: Optional[bool] = Field(default=False, description="Whether leads without direct email should be skipped")


class ProviderHealth(BaseModel):
    """Health and operational readiness status for a discovery provider."""
    id: str
    name: str
    integration_type: str
    status: str  # 'READY', 'NOT CONFIGURED', 'ERROR', 'RATE LIMITED', 'DISABLED'
    status_label: str
    description: str
    is_configured: bool
    required_credentials: List[str] = Field(default_factory=list)
    last_checked: str
    last_result_count: int = 0
    rate_limit_info: Optional[str] = None


class NormalizedBuyerLead(BaseModel):
    """Standardized lead model across all discovery providers."""
    lead_id: str
    company_name: str
    website: Optional[str] = ""
    domain: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    country: str = "United States"
    state: Optional[str] = ""
    city: Optional[str] = ""
    source: str
    source_platform: str
    source_url: str
    buyer_type: Optional[str] = "Wholesaler"
    product_relevance: str = "High"  # High, Medium, Low, Unknown
    product_relevance_reason: Optional[str] = ""
    discovery_query: Optional[str] = ""
    discovered_at: str
    email_status: str = "Missing"  # Valid, Review, Missing, Invalid
    validation_status: str = "Missing"
    is_demo: bool = False
    country_match: str = "true"  # "true", "false", "unknown"
    country_evidence: Optional[str] = ""
    provenance: List[str] = Field(default_factory=list)
    notes: Optional[str] = ""


class ProviderSearchResult(BaseModel):
    """Standardized search outcome from an individual provider."""
    source_id: str
    source_name: str
    status: str  # 'completed', 'failed', 'requires_config', 'rate_limited'
    query_sent: str
    raw_results_count: int
    records: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str


class DiscoveryRunRecord(BaseModel):
    """Audit record for a complete multi-source discovery execution."""
    run_id: str
    profile: Dict[str, Any]
    selected_providers: List[str]
    queries: List[str]
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    provider_statuses: Dict[str, Any] = Field(default_factory=dict)
    raw_result_counts: int = 0
    normalized_result_counts: int = 0
    duplicate_count: int = 0
    us_match_count: int = 0
    valid_email_count: int = 0
    errors: List[str] = Field(default_factory=list)
    created_lead_ids: List[str] = Field(default_factory=list)
    status: str = "completed"
