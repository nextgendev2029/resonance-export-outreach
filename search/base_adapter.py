"""
Base Search Adapter Interface for Resonance.
Provides HTTP session management, health reporting, configurable query construction,
and standard result formatting.
"""

from typing import List, Dict, Any, Optional
import requests
from config import load_settings

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseSearchAdapter:
    def __init__(self, platform_id: str, platform_name: str, timeout: int = 10):
        self.platform_id = platform_id
        self.platform_name = platform_name
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @staticmethod
    def build_query(keyword: str, qualifiers: Optional[List[str]] = None, extra_operator: str = "") -> str:
        """
        Build a clean query by combining the primary keyword with selected intent qualifiers.
        Avoids hardcoding giant brittle queries.
        """
        base = f'"{keyword}"'
        if qualifiers and len(qualifiers) > 0:
            # Pick primary qualifiers for focused query
            joined_qualifiers = " OR ".join(f'"{q}"' for q in qualifiers[:4])
            query = f"{base} ({joined_qualifiers})"
        else:
            query = f'{base} wholesale distributor'

        if extra_operator:
            query = f"{extra_operator} {query}"

        return query.strip()

    def get_health_status(self) -> Dict[str, Any]:
        """
        Return the operational status of this source adapter.
        Returns:
            {
                'id': str,
                'name': str,
                'status': 'ready' | 'requires_config' | 'unavailable' | 'error',
                'status_label': str,
                'description': str,
                'is_configured': bool
            }
        """
        raise NotImplementedError("Subclasses must implement get_health_status()")

    def search(
        self,
        keyword: str,
        qualifiers: Optional[List[str]] = None,
        max_results: int = 5,
        run_id: str = ""
    ) -> Dict[str, Any]:
        """
        Execute search on source platform.
        Returns dictionary:
        {
            'source_id': str,
            'source_name': str,
            'status': 'completed' | 'failed' | 'requires_config',
            'raw_results_count': int,
            'records': List[Dict[str, Any]],
            'error': Optional[str]
        }
        """
        raise NotImplementedError("Subclasses must implement search()")
