"""
Base Discovery Provider Interface for Resonance - Export Outreach & Lead Operations.
Defines standard contracts for API search adapters, health reporting,
and result normalization.
"""

from typing import List, Dict, Any, Optional
import requests
from search.models import DiscoveryProfile, ProviderHealth, ProviderSearchResult, NormalizedBuyerLead
from search.us_target_verifier import USTargetVerifier
from search.relevance import HomeDecorRelevanceEvaluator

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 Resonance-Bot/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class DiscoveryProvider:
    """Abstract Base Class for all Resonance Buyer Discovery Providers."""

    def __init__(
        self,
        provider_id: str,
        provider_name: str,
        integration_type: str,
        description: str,
        required_credentials: Optional[List[str]] = None,
        timeout: int = 10
    ):
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.integration_type = integration_type
        self.description = description
        self.required_credentials = required_credentials or []
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.last_checked: Optional[str] = None
        self.last_result_count: int = 0

    def health(self) -> ProviderHealth:
        """Evaluate configuration and operational health status."""
        raise NotImplementedError("Subclasses must implement health()")

    def search(
        self,
        profile: DiscoveryProfile,
        max_results: int = 5,
        run_id: str = ""
    ) -> ProviderSearchResult:
        """Execute query across provider endpoint and return raw normalized records."""
        raise NotImplementedError("Subclasses must implement search()")

    def normalize(
        self,
        raw_item: Dict[str, Any],
        profile: DiscoveryProfile,
        query: str,
        run_id: str
    ) -> Dict[str, Any]:
        """Convert provider-specific payload into a unified buyer dictionary."""
        raise NotImplementedError("Subclasses must implement normalize()")

    def build_query(self, profile: DiscoveryProfile, extra_operator: str = "") -> str:
        """
        Dynamically synthesize search query from seller profile parameters.
        Combines product name, category, target country, state, and buyer types.
        """
        parts = []

        # Product name
        prod = profile.product_name.strip()
        if prod:
            parts.append(f'"{prod}"')

        # Category (if distinct from product name)
        cat = profile.product_category.strip()
        if cat and cat.lower() not in prod.lower():
            parts.append(f'"{cat}"')

        # Buyer type qualifiers (pick top 3 for targeted query)
        b_types = profile.buyer_types or ["importer", "distributor", "wholesaler"]
        cleaned_b_types = [t.lower().replace(" store", "").replace(" business", "") for t in b_types[:3]]
        if cleaned_b_types:
            joined = " OR ".join(f'"{t}"' for t in cleaned_b_types)
            parts.append(f"({joined})")

        # Target Country & State
        if profile.target_state and profile.target_state.strip():
            parts.append(f'"{profile.target_state.strip()}"')
        
        country = profile.target_country.strip()
        if country and country.lower() in ("united states", "usa", "us"):
            parts.append("USA")
        elif country:
            parts.append(f'"{country}"')

        # Explicit user-supplied keywords
        if profile.keywords:
            for kw in profile.keywords[:2]:
                parts.append(f'"{kw.strip()}"')

        if extra_operator:
            parts.insert(0, extra_operator)

        return " ".join(parts).strip()
