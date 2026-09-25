"""
Facebook Provider for Resonance.
Integrates with official Meta Graph API. Clearly reports NOT CONFIGURED
when official credentials are not supplied, without performing brittle scraping.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus, urlparse

from config import load_settings
from search.base_provider import DiscoveryProvider
from search.models import DiscoveryProfile, ProviderHealth, ProviderSearchResult
from search.us_target_verifier import USTargetVerifier
from search.relevance import HomeDecorRelevanceEvaluator


class FacebookSearchProvider(DiscoveryProvider):
    """Meta Graph API provider for discovering verified US business pages."""

    def __init__(self):
        super().__init__(
            provider_id="facebook",
            provider_name="Facebook Business Pages",
            integration_type="Meta Graph API",
            description=(
                "Queries official Meta Graph API for verified US home decor showrooms, wellness studios, "
                "and lifestyle retailer business pages. Requires official Meta developer credentials."
            ),
            required_credentials=["FACEBOOK_ACCESS_TOKEN"]
        )

    def health(self) -> ProviderHealth:
        settings = load_settings()
        token = settings.get("facebook_access_token", "").strip()
        is_configured = bool(token)
        now_iso = datetime.utcnow().isoformat() + "Z"
        self.last_checked = now_iso

        return ProviderHealth(
            id=self.provider_id,
            name=self.provider_name,
            integration_type=self.integration_type,
            status="READY" if is_configured else "NOT CONFIGURED",
            status_label="Ready (Meta Graph API)" if is_configured else "Not Configured (Requires Meta Graph API Token)",
            description=self.description,
            is_configured=is_configured,
            required_credentials=self.required_credentials,
            last_checked=now_iso,
            last_result_count=self.last_result_count,
            rate_limit_info="200 calls/hr standard App Rate Limit"
        )

    def search(
        self,
        profile: DiscoveryProfile,
        max_results: int = 5,
        run_id: str = ""
    ) -> ProviderSearchResult:
        now_iso = datetime.utcnow().isoformat() + "Z"
        settings = load_settings()
        token = settings.get("facebook_access_token", "").strip()

        query = self.build_query(profile)

        # Enforce official API requirement
        if not token:
            return ProviderSearchResult(
                source_id=self.provider_id,
                source_name=self.provider_name,
                status="requires_config",
                query_sent=query,
                raw_results_count=0,
                records=[],
                error=(
                    "Meta Graph API is not configured. To search Facebook business pages, "
                    "configure FACEBOOK_ACCESS_TOKEN in Settings or .env. Unauthenticated scraping is disabled."
                ),
                timestamp=now_iso
            )

        endpoint = (
            f"https://graph.facebook.com/v19.0/pages/search"
            f"?q={quote_plus(query)}&access_token={token}&fields=id,name,link,location,emails,phone,category"
            f"&limit={min(max_results, 10)}"
        )
        records = []
        try:
            resp = self.session.get(endpoint, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
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
                    raw_results_count=len(items),
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
                    error="Meta Graph API rate limit encountered (HTTP 429)",
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
                    error=f"Meta Graph API returned HTTP {resp.status_code}",
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
                error=f"Meta Graph API request error: {str(e)}",
                timestamp=now_iso
            )

    def normalize(
        self,
        raw_item: Dict[str, Any],
        profile: DiscoveryProfile,
        query: str,
        run_id: str
    ) -> Dict[str, Any]:
        name = raw_item.get("name", "").strip()
        link = raw_item.get("link", f"https://facebook.com/{raw_item.get('id', '')}")
        loc = raw_item.get("location") or {}
        city = loc.get("city", "")
        state = loc.get("state", "")
        country = loc.get("country", "")

        emails = raw_item.get("emails") or []
        email = emails[0] if emails else ""
        phone = raw_item.get("phone") or ""

        us_audit = USTargetVerifier.verify(
            company_name=name,
            website=link,
            raw_text=f"{city} {state} {country}",
            api_country=country
        )

        rel_audit = HomeDecorRelevanceEvaluator.evaluate(
            company_name=name,
            raw_text=raw_item.get("category", ""),
            website=link,
            query=query
        )

        val_status = "Valid" if email else "Missing"

        return {
            "lead_id": f"lead_fb_{raw_item.get('id', '')[:10]}",
            "company_name": name or "Facebook Business Page",
            "website": link,
            "domain": "facebook.com",
            "email": email,
            "phone": phone or us_audit.get("phone") or "",
            "country": us_audit.get("country", "United States"),
            "state": state or us_audit.get("state") or "",
            "city": city or us_audit.get("city") or "",
            "source": self.provider_name,
            "source_platform": self.provider_name,
            "source_url": link,
            "buyer_type": rel_audit.get("buyer_type", "Retailer"),
            "product_relevance": rel_audit.get("relevance", "Medium"),
            "product_relevance_reason": rel_audit.get("relevance_reason", ""),
            "discovery_query": query,
            "discovered_at": datetime.utcnow().isoformat() + "Z",
            "email_status": val_status,
            "validation_status": val_status,
            "is_demo": False,
            "country_match": us_audit.get("country_match", "true"),
            "country_evidence": us_audit.get("country_evidence", "Meta Graph API Location Data"),
            "provenance": [self.provider_name],
            "notes": ""
        }
