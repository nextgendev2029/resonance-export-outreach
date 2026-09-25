"""
Company Website Search Adapter for Resonance.
Finds company websites in the sound healing, yoga, and meditation retail niche,
and crawls their contact/about pages for direct buyer emails.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

from search.base_adapter import BaseSearchAdapter
from extraction.data_extractor import DataExtractor


class WebsiteSearchAdapter(BaseSearchAdapter):
    def __init__(self):
        super().__init__(platform_id="website", platform_name="Company Website")

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "id": self.platform_id,
            "name": self.platform_name,
            "status": "ready",
            "status_label": "Ready (Contact Crawler)",
            "description": "Discovers relevant sound healing and acoustic instrument studio websites and directly crawls their contact pages.",
            "is_configured": True
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

        query = self.build_query(keyword, qualifiers, extra_operator='studio OR shop "contact"')
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        try:
            resp = self.session.get(search_url, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".result__body")
                raw_count = len(items)

                for item in items[:max_results]:
                    title_elem = item.select_one(".result__title a")
                    url_elem = item.select_one(".result__url")
                    snippet_elem = item.select_one(".result__snippet")

                    title = title_elem.get_text() if title_elem else ""
                    raw_url = url_elem.get_text().strip() if url_elem else ""
                    raw_snippet = snippet_elem.get_text() if snippet_elem else ""

                    if not raw_url:
                        continue

                    if not raw_url.startswith("http"):
                        raw_url = f"https://{raw_url}"

                    clean_company = title.split("|")[0].split("-")[0].strip()
                    discovered_emails = []
                    contact_url_used = raw_url

                    # Crawl homepage and contact pages
                    try:
                        page_resp = self.session.get(raw_url, timeout=5)
                        if page_resp.status_code == 200:
                            page_text = page_resp.text
                            discovered_emails = DataExtractor.extract_emails_from_text(page_text)

                            if not discovered_emails:
                                for contact_path in ["/contact", "/contact-us", "/about"]:
                                    test_url = urljoin(raw_url, contact_path)
                                    try:
                                        c_resp = self.session.get(test_url, timeout=4)
                                        if c_resp.status_code == 200:
                                            found = DataExtractor.extract_emails_from_text(c_resp.text)
                                            if found:
                                                discovered_emails = found
                                                contact_url_used = test_url
                                                break
                                    except Exception:
                                        continue
                    except Exception:
                        # Fallback to snippet if crawl failed
                        discovered_emails = DataExtractor.extract_emails_from_text(raw_snippet)

                    if discovered_emails:
                        for email in discovered_emails:
                            rec = DataExtractor.normalize_record(
                                email=email,
                                source_platform=self.platform_name,
                                source_url=contact_url_used,
                                company_name=clean_company,
                                website=raw_url,
                                raw_text=f"{title} {raw_snippet}",
                                discovery_run_id=run_id
                            )
                            records.append(rec)
                    else:
                        # Retain company with missing email
                        rec = DataExtractor.normalize_record(
                            email="",
                            source_platform=self.platform_name,
                            source_url=contact_url_used,
                            company_name=clean_company,
                            website=raw_url,
                            raw_text=f"{title} {raw_snippet}",
                            discovery_run_id=run_id
                        )
                        records.append(rec)
            else:
                error_msg = f"Search engine returned HTTP {resp.status_code}"
        except Exception as e:
            error_msg = f"Website discovery error: {str(e)}"

        return {
            "source_id": self.platform_id,
            "source_name": self.platform_name,
            "status": "failed" if (error_msg and raw_count == 0) else "completed",
            "raw_results_count": raw_count,
            "records": records,
            "error": error_msg
        }
