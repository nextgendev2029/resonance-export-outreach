"""
Google Search Provider for Resonance.
Queries the official Google Custom Search Engine REST API with United States
country restriction (`gl=us`, `cr=countryUS`) and falls back to public web indexes
when API credentials are not configured.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup

from config import load_settings
from search.base_provider import DiscoveryProvider
from search.models import DiscoveryProfile, ProviderHealth, ProviderSearchResult
from search.us_target_verifier import USTargetVerifier
from search.relevance import HomeDecorRelevanceEvaluator
from extraction.data_extractor import DataExtractor


class GoogleSearchProvider(DiscoveryProvider):
    """Google Custom Search API discovery provider with US location targeting."""

    def __init__(self):
        super().__init__(
            provider_id="google",
            provider_name="Google Search API",
            integration_type="Official REST API (Custom Search Engine)",
            description=(
                "Queries Google Custom Search API with United States geo-targeting (gl=us, cr=countryUS) "
                "to discover wholesale decor distributors, sound therapy retailers, and importers."
            ),
            required_credentials=["GOOGLE_API_KEY", "GOOGLE_CSE_ID"]
        )

    def health(self) -> ProviderHealth:
        settings = load_settings()
        api_key = (
            settings.get("google_api_key")
            or settings.get("google_cse_api_key")
            or ""
        ).strip()
        cx = (
            settings.get("google_cse_id")
            or settings.get("google_cse_cx")
            or ""
        ).strip()

        is_configured = bool(api_key and cx)
        now_iso = datetime.utcnow().isoformat() + "Z"
        self.last_checked = now_iso

        return ProviderHealth(
            id=self.provider_id,
            name=self.provider_name,
            integration_type=self.integration_type,
            status="READY" if is_configured else "NOT CONFIGURED",
            status_label="Ready (Official REST API)" if is_configured else "Not Configured (Requires API Key & Search Engine ID)",
            description=self.description,
            is_configured=is_configured,
            required_credentials=self.required_credentials,
            last_checked=now_iso,
            last_result_count=self.last_result_count,
            rate_limit_info="100 queries/day free tier"
        )

    def search(
        self,
        profile: DiscoveryProfile,
        max_results: int = 5,
        run_id: str = ""
    ) -> ProviderSearchResult:
        settings = load_settings()
        api_key = (
            settings.get("google_api_key")
            or settings.get("google_cse_api_key")
            or ""
        ).strip()
        cx = (
            settings.get("google_cse_id")
            or settings.get("google_cse_cx")
            or ""
        ).strip()

        query = self.build_query(profile)
        now_iso = datetime.utcnow().isoformat() + "Z"
        records = []
        raw_count = 0
        error_msg = None
        status = "completed"

        # 1. Use Official Google Custom Search Engine REST API if configured
        if api_key and cx:
            endpoint = (
                f"https://www.googleapis.com/customsearch/v1"
                f"?key={api_key}&cx={cx}&q={quote_plus(query)}"
                f"&gl=us&cr=countryUS&num={min(max(max_results, 1), 10)}"
            )
            try:
                resp = self.session.get(endpoint, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    raw_count = len(items)
                    for item in items:
                        rec = self.normalize(item, profile, query, run_id)
                        if rec:
                            records.append(rec)
                    self.last_result_count = len(records)
                    return ProviderSearchResult(
                        source_id=self.provider_id,
                        source_name=self.provider_name,
                        status="completed",
                        query_sent=query,
                        raw_results_count=raw_count,
                        records=records,
                        error=None,
                        timestamp=now_iso
                    )
                elif resp.status_code == 429:
                    return ProviderSearchResult(
                        source_id=self.provider_id,
                        source_name=self.provider_name,
                        status="rate_limited",
                        query_sent=query,
                        raw_results_count=0,
                        records=[],
                        error="Google Custom Search API rate limit exceeded (HTTP 429)",
                        timestamp=now_iso
                    )
                elif resp.status_code in (401, 403):
                    return ProviderSearchResult(
                        source_id=self.provider_id,
                        source_name=self.provider_name,
                        status="requires_config",
                        query_sent=query,
                        raw_results_count=0,
                        records=[],
                        error=f"Google API authentication error (HTTP {resp.status_code}). Please check credentials.",
                        timestamp=now_iso
                    )
                else:
                    return ProviderSearchResult(
                        source_id=self.provider_id,
                        source_name=self.provider_name,
                        status="failed",
                        query_sent=query,
                        raw_results_count=0,
                        records=[],
                        error=f"Google Custom Search API returned HTTP {resp.status_code}",
                        timestamp=now_iso
                    )
            except Exception as e:
                return ProviderSearchResult(
                    source_id=self.provider_id,
                    source_name=self.provider_name,
                    status="failed",
                    query_sent=query,
                    raw_results_count=0,
                    records=[],
                    error=f"Google API connection error: {str(e)}",
                    timestamp=now_iso
                )

        # 2. Public web index fallback only if API credentials not configured
        fallback_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            resp = self.session.get(fallback_url, timeout=self.timeout)
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

                    clean_title = title.split("-")[0].split("|")[0].strip()
                    payload = {
                        "title": clean_title,
                        "link": raw_url,
                        "snippet": raw_snippet
                    }
                    rec = self.normalize(payload, profile, query, run_id)
                    if rec:
                        records.append(rec)
                status = "completed"
                error_msg = None
            elif resp.status_code == 429:
                status = "rate_limited"
                error_msg = "Public search index rate limited (HTTP 429)"
            else:
                if not error_msg:
                    error_msg = f"Public web index returned HTTP {resp.status_code}"
        except Exception as e:
            if not error_msg:
                error_msg = f"Public search error: {str(e)}"

        self.last_result_count = len(records)
        return ProviderSearchResult(
            source_id=self.provider_id,
            source_name=self.provider_name,
            status=status if records else ("failed" if error_msg else "completed"),
            query_sent=query,
            raw_results_count=raw_count,
            records=records,
            error=error_msg,
            timestamp=now_iso
        )

    def normalize(
        self,
        raw_item: Dict[str, Any],
        profile: DiscoveryProfile,
        query: str,
        run_id: str
    ) -> Dict[str, Any]:
        title = raw_item.get("title", "").strip()
        link = raw_item.get("link", "").strip()
        snippet = raw_item.get("snippet", "").strip()
        combined_text = f"{title} {snippet}"

        # Extract domain
        domain = ""
        if link:
            try:
                parsed = urlparse(link if "://" in link else f"https://{link}")
                domain = parsed.netloc.lower().replace("www.", "")
            except Exception:
                domain = link

        # Extract direct emails if present
        emails = DataExtractor.extract_emails_from_text(combined_text)
        primary_email = emails[0] if emails else ""

        # Verify US location
        us_audit = USTargetVerifier.verify(
            company_name=title,
            website=link,
            raw_text=combined_text,
            api_country="United States"
        )

        # Evaluate Home Decor buyer relevance
        rel_audit = HomeDecorRelevanceEvaluator.evaluate(
            company_name=title,
            raw_text=combined_text,
            website=link,
            query=query
        )

        val_status = "Valid" if primary_email else "Missing"

        return {
            "lead_id": f"lead_{domain.replace('.', '_')[:12]}",
            "company_name": title or domain.split(".")[0].title() or "US Home Decor Prospect",
            "website": link,
            "domain": domain,
            "email": primary_email,
            "phone": us_audit.get("phone") or "",
            "country": us_audit.get("country", "United States"),
            "state": us_audit.get("state") or "",
            "city": us_audit.get("city") or "",
            "source": self.provider_name,
            "source_platform": self.provider_name,
            "source_url": link,
            "buyer_type": rel_audit.get("buyer_type", "Wholesaler"),
            "product_relevance": rel_audit.get("relevance", "High"),
            "product_relevance_reason": rel_audit.get("relevance_reason", ""),
            "discovery_query": query,
            "discovered_at": datetime.utcnow().isoformat() + "Z",
            "email_status": val_status,
            "validation_status": val_status,
            "is_demo": False,
            "country_match": us_audit.get("country_match", "true"),
            "country_evidence": us_audit.get("country_evidence", "Google Search US geo-filter"),
            "provenance": [self.provider_name],
            "notes": ""
        }
