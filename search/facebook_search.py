"""
Facebook Search Adapter for Resonance.
Discovers public Facebook sound therapy, meditation studio, and singing bowl business pages.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from search.base_adapter import BaseSearchAdapter
from extraction.data_extractor import DataExtractor


class FacebookSearchAdapter(BaseSearchAdapter):
    def __init__(self):
        super().__init__(platform_id="facebook", platform_name="Facebook")

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "id": self.platform_id,
            "name": self.platform_name,
            "status": "requires_config",
            "status_label": "Requires Configuration (Graph API)",
            "description": "Scrapes public business pages and sound healing groups. For direct authenticated access, a Meta Graph API token is required.",
            "is_configured": False
        }

    def search(
        self,
        keyword: str,
        qualifiers: Optional[List[str]] = None,
        max_results: int = 5,
        run_id: str = ""
    ) -> Dict[str, Any]:
        records = []
        raw_count = 0
        error_msg = None

        query = self.build_query(keyword, qualifiers, extra_operator="site:facebook.com")
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
                    clean_title = title.replace("Facebook", "").replace("|", "").strip()
                    emails = DataExtractor.extract_emails_from_text(combined_text)

                    if emails:
                        for email in emails:
                            rec = DataExtractor.normalize_record(
                                email=email,
                                source_platform=self.platform_name,
                                source_url=raw_url,
                                company_name=clean_title,
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
                            company_name=clean_title,
                            website=raw_url,
                            raw_text=combined_text,
                            discovery_run_id=run_id
                        )
                        records.append(rec)
            else:
                error_msg = f"Public index returned HTTP {resp.status_code}"
        except Exception as e:
            error_msg = f"Facebook search error: {str(e)}"

        return {
            "source_id": self.platform_id,
            "source_name": self.platform_name,
            "status": "failed" if (error_msg and raw_count == 0) else "completed",
            "raw_results_count": raw_count,
            "records": records,
            "error": error_msg
        }
