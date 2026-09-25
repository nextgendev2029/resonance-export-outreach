"""
Provider Registry for Resonance - Export Outreach & Lead Operations.
Manages discovery provider lifecycle, health reporting, and lookup.
"""

from typing import Dict, List, Optional
from search.base_provider import DiscoveryProvider
from search.models import ProviderHealth
from search.providers.google_provider import GoogleSearchProvider
from search.providers.directory_provider import DirectorySearchProvider
from search.providers.website_provider import WebsiteSearchProvider
from search.providers.facebook_provider import FacebookSearchProvider
from search.providers.linkedin_provider import LinkedInSearchProvider


class ProviderRegistry:
    """Central registry and lifecycle manager for all discovery providers."""

    def __init__(self):
        self._providers: Dict[str, DiscoveryProvider] = {
            "google": GoogleSearchProvider(),
            "directory": DirectorySearchProvider(),
            "website": WebsiteSearchProvider(),
            "facebook": FacebookSearchProvider(),
            "linkedin": LinkedInSearchProvider(),
        }

    def get_provider(self, provider_id: str) -> Optional[DiscoveryProvider]:
        """Look up provider instance by identifier."""
        return self._providers.get(provider_id.lower())

    def list_providers(self) -> List[DiscoveryProvider]:
        """Return all registered provider instances."""
        return list(self._providers.values())

    def get_all_health(self) -> List[ProviderHealth]:
        """Poll health and configuration status for all discovery providers."""
        return [provider.health() for provider in self._providers.values()]

    def get_provider_health(self, provider_id: str) -> Optional[ProviderHealth]:
        """Get health for a specific provider."""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.health()
        return None

    def register_provider(self, provider_id: str, provider: DiscoveryProvider):
        """Register or override a provider (useful for testing and extensibility)."""
        self._providers[provider_id.lower()] = provider
