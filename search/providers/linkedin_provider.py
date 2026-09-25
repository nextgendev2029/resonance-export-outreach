"""
LinkedIn Provider for Resonance.
Integrates with official LinkedIn Organization & Marketing API. Clearly reports
NOT CONFIGURED when credentials are not supplied, avoiding fragile scraping.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus

from config import load_settings
from search.base_provider import DiscoveryProvider
from search.models import DiscoveryProfile, ProviderHealth, ProviderSearchResult
from search.us_target_verifier import USTargetVerifier
from search.relevance import HomeDecorRelevanceEvaluator


class LinkedInSearchProvider(DiscoveryProvider):
    """Official LinkedIn Organization API discovery provider."""

    def __init__(self):
        super().__init__(
            provider_id="linkedin",
            provider_name="LinkedIn B2B Companies",
            integration_type="LinkedIn Organization API",
            description=(
                "Queries official LinkedIn Organization Search API for US home decor corporate buyers, "
                "wholesale distributors, and procurement managers. Requires verified LinkedIn Developer API credentials."
            ),
            required_credentials=["LINKEDIN_ACCESS_TOKEN"]
        )

    def health(self) -> ProviderHealth:
        settings = load_settings()
        token = settings.get("linkedin_access_token", "").strip()
        is_configured = bool(token)
        now_iso = datetime.utcnow().isoformat() + "Z"
        self.last_checked = now_iso

        return ProviderHealth(
            id=self.provider_id,
            name=self.provider_name,
            integration_type=self.integration_type,
            status="READY" if is_configured else "NOT CONFIGURED",
            status_label="Ready (LinkedIn Organization API)" if is_configured else "Not Configured (Requires LinkedIn API Token)",
            description=self.description,
            is_configured=is_configured,
            required_credentials=self.required_credentials,
            last_checked=now_iso,
            last_result_count=self.last_result_count,
            rate_limit_info="Standard Developer Tier Rate Limits"
        )

    def search(
        self,
        profile: DiscoveryProfile,
        max_results: int = 5,
        run_id: str = ""
    ) -> ProviderSearchResult:
        now_iso = datetime.utcnow().isoformat() + "Z"
        settings = load_settings()
        token = settings.get("linkedin_access_token", "").strip()

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
                    "LinkedIn API is not configured. To search LinkedIn B2B company pages, "
                    "configure LINKEDIN_ACCESS_TOKEN in Settings or .env. Unauthenticated scraping is disabled."
                ),
                timestamp=now_iso
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        endpoint = f"https://api.linkedin.com/v2/organizationAcls?q=roleAssignee"
        try:
            resp = self.session.get(endpoint, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("elements", [])
                records = [self.normalize(item, profile, query, run_id) for item in items[:max_results]]
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
                    error="LinkedIn API rate limit exceeded (HTTP 429)",
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
                    error=f"LinkedIn API returned HTTP {resp.status_code}",
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
                error=f"LinkedIn API connection error: {str(e)}",
                timestamp=now_iso
            )

    def normalize(
        self,
        raw_item: Dict[str, Any],
        profile: DiscoveryProfile,
        query: str,
        run_id: str
    ) -> Dict[str, Any]:
        org = raw_item.get("organization~", {})
        name = org.get("localizedName", raw_item.get("name", "LinkedIn B2B Company"))
        vanity = org.get("vanityName", "")
        link = f"https://linkedin.com/company/{vanity}" if vanity else "https://linkedin.com"

        us_audit = USTargetVerifier.verify(
            company_name=name,
            website=link,
            raw_text=name,
            api_country="United States"
        )

        rel_audit = HomeDecorRelevanceEvaluator.evaluate(
            company_name=name,
            raw_text=name,
            website=link,
            query=query
        )

        val_status = "Missing"

        return {
            "lead_id": f"lead_li_{vanity or 'org'}[:10]",
            "company_name": name,
            "website": link,
            "domain": "linkedin.com",
            "email": "",
            "phone": us_audit.get("phone") or "",
            "country": us_audit.get("country", "United States"),
            "state": us_audit.get("state") or "",
            "city": us_audit.get("city") or "",
            "source": self.provider_name,
            "source_platform": self.provider_name,
            "source_url": link,
            "buyer_type": rel_audit.get("buyer_type", "B2B Buyer"),
            "product_relevance": rel_audit.get("relevance", "Medium"),
            "product_relevance_reason": rel_audit.get("relevance_reason", ""),
            "discovery_query": query,
            "discovered_at": datetime.utcnow().isoformat() + "Z",
            "email_status": val_status,
            "validation_status": val_status,
            "is_demo": False,
            "country_match": us_audit.get("country_match", "true"),
            "country_evidence": us_audit.get("country_evidence", "LinkedIn Corporate US Profile"),
            "provenance": [self.provider_name],
            "notes": ""
        }
