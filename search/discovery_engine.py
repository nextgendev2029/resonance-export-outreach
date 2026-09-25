"""
Discovery Engine Orchestrator for Resonance - Export Outreach & Lead Operations.
Coordinates multi-source queries, collects raw results, tracks live progress,
manages run history in discovery_runs.json, and ingests leads with deduplication.
Bridges legacy adapters with Phase 6 Discovery Orchestrator.
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import DISCOVERY_RUNS_FILE
from search.google_search import GoogleSearchAdapter
from search.facebook_search import FacebookSearchAdapter
from search.linkedin_search import LinkedInSearchAdapter
from search.directory_search import DirectorySearchAdapter
from search.website_search import WebsiteSearchAdapter
from search.discovery_orchestrator import DiscoveryOrchestrator
from search.models import DiscoveryProfile
from app_logging.activity_logger import ActivityLogger


class DiscoveryEngine:
    def __init__(self, logger: Optional[ActivityLogger] = None):
        self.logger = logger or ActivityLogger()
        self.adapters = {
            "google": GoogleSearchAdapter(),
            "facebook": FacebookSearchAdapter(),
            "linkedin": LinkedInSearchAdapter(),
            "directory": DirectorySearchAdapter(),
            "website": WebsiteSearchAdapter(),
        }
        self.orchestrator = DiscoveryOrchestrator(logger=self.logger)
        self._ensure_runs_file()

    def _ensure_runs_file(self):
        """Ensure discovery_runs.json exists."""
        if not DISCOVERY_RUNS_FILE.exists():
            with open(DISCOVERY_RUNS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_sources_health(self) -> List[Dict[str, Any]]:
        """Return health status and configuration requirements for all discovery adapters."""
        return [adapter.get_health_status() for adapter in self.adapters.values()]

    def get_run_history(self) -> List[Dict[str, Any]]:
        """Return all historical discovery runs, newest first."""
        return self.orchestrator.get_run_history()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a single discovery run by ID."""
        return self.orchestrator.get_run(run_id)

    def search_buyers(
        self,
        profile: DiscoveryProfile,
        enabled_sources: Optional[List[str]] = None,
        max_results_per_source: int = 5,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Phase 6 primary API for seller profile-guided buyer discovery."""
        return self.orchestrator.execute_discovery(
            profile=profile,
            enabled_sources=enabled_sources,
            max_results_per_source=max_results_per_source,
            progress_callback=progress_callback
        )

    def execute_discovery(
        self,
        keyword: str = "Singing Bowls",
        qualifiers: Optional[List[str]] = None,
        enabled_sources: Optional[List[str]] = None,
        max_results_per_source: int = 5,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute full multi-source buyer discovery.
        Constructs a DiscoveryProfile from keyword & qualifiers and delegates to orchestrator.
        """
        profile = DiscoveryProfile(
            product_name=keyword or "Singing Bowls",
            product_category="Home Decor",
            buyer_types=qualifiers or [
                "Importer", "Distributor", "Wholesaler", "Retailer", "Home Decor Store", "Gift Shop"
            ],
            target_country="United States"
        )
        return self.search_buyers(
            profile=profile,
            enabled_sources=enabled_sources,
            max_results_per_source=max_results_per_source,
            progress_callback=progress_callback
        )
