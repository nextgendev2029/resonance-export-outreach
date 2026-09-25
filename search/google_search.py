"""
Google Search Adapter for Resonance.
Discovers wholesale Singing Bowls prospects using either Google Custom Search API
(if configured) or public web search with fallback.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from search.base_adapter import BaseSearchAdapter
from extraction.data_extractor import DataExtractor
from config import load_settings


class GoogleSearchAdapter(BaseSearchAdapter):
    def __init__(self):
        super().__init__(platform_id="google", platform_name="Google Search")

    def get_health_status(self) -> Dict[str, Any]:
        settings = load_settings()
        has_cse = bool(settings.get("google_cse_api_key") and settings.get("google_cse_cx"))
        return {
            "id": self.platform_id,
            "name": self.platform_name,
            "status": "ready",
            "status_label": "Ready (Custom Search API)" if has_cse else "Ready (Public Web Search)",
            "description": "Searches global web indexes for Singing Bowls distributors, sound therapy schools, and importers.",
            "is_configured": has_cse
        }

    def search(
        self,
        keyword: str,
        qualifiers: Optional[List[str]] = None,
        max_results: int = 5,
        run_id: str = ""
    ) -> Dict[str, Any]:
        settings = load_settings()
        api_key = settings.get("google_cse_api_key", "").strip()
        cx = settings.get("google_cse_cx", "").strip()

        records = []
        raw_count = 0
        error_msg = None

        query = self.build_query(keyword, qualifiers)

        # 1. If Google CSE configured, use official API
        if api_key and cx:
            endpoint = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={quote_plus(query)}&num={min(max_results, 10)}"
            try:
                resp = self.session.get(endpoint, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    raw_count = len(items)
                    for item in items:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        snippet = item.get("snippet", "")
                        combined = f"{title} {snippet}"
                        emails = DataExtractor.extract_emails_from_text(combined)

                        if emails:
                            for email in emails:
                                rec = DataExtractor.normalize_record(
                                    email=email,
                                    source_platform=self.platform_name,
                                    source_url=link,
                                    company_name=title.split("-")[0].split("|")[0].strip(),
                                    website=link,
                                    raw_text=combined,
                                    discovery_run_id=run_id
                                )
                                records.append(rec)
                        else:
                            # Retain as Missing email for sales rep review
                            rec = DataExtractor.normalize_record(
                                email="",
                                source_platform=self.platform_name,
                                source_url=link,
                                company_name=title.split("-")[0].split("|")[0].strip(),
                                website=link,
                                raw_text=combined,
                                discovery_run_id=run_id
                            )
                            records.append(rec)
                    return {
                        "source_id": self.platform_id,
                        "source_name": self.platform_name,
                        "status": "completed",
                        "raw_results_count": raw_count,
                        "records": records,
                        "error": None
                    }
                else:
                    error_msg = f"Google API returned HTTP {resp.status_code}"
            except Exception as e:
                error_msg = f"Google API error: {str(e)}"

        # 2. Public web search fallback
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            resp = self.session.get(search_url, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".result__body")
                raw_count = len(items)

                for item in items[:max_results]:
                    snippet_elem = item.select_one(".result__snippet")
                    title_elem = item.select_one(".result__title a")
                    url_elem = item.select_one(".result__url")

                    raw_snippet = snippet_elem.get_text() if snippet_elem else ""
                    title = title_elem.get_text() if title_elem else ""
                    raw_url = url_elem.get_text().strip() if url_elem else ""

                    if raw_url and not raw_url.startswith("http"):
                        raw_url = f"https://{raw_url}"

                    combined_text = f"{title} {raw_snippet}"
                    emails = DataExtractor.extract_emails_from_text(combined_text)

                    if emails:
                        for email in emails:
                            rec = DataExtractor.normalize_record(
                                email=email,
                                source_platform=self.platform_name,
                                source_url=raw_url,
                                company_name=title.split("-")[0].split("|")[0].strip(),
                                website=raw_url,
                                raw_text=combined_text,
                                discovery_run_id=run_id
                            )
                            records.append(rec)
                    else:
                        rec = DataExtractor.normalize_record(
                            email="",
                            source_platform=self.platform_name,
                            source_url=raw_url,
                            company_name=title.split("-")[0].split("|")[0].strip(),
                            website=raw_url,
                            raw_text=combined_text,
                            discovery_run_id=run_id
                        )
                        records.append(rec)
            else:
                error_msg = f"Search engine returned HTTP {resp.status_code}"
        except Exception as e:
            error_msg = f"Network timeout / search request failed: {str(e)}"

        return {
            "source_id": self.platform_id,
            "source_name": self.platform_name,
            "status": "failed" if (error_msg and raw_count == 0) else "completed",
            "raw_results_count": raw_count,
            "records": records,
            "error": error_msg
        }
