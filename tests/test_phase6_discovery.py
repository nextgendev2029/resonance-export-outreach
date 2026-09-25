"""
Phase 6 Test Suite: US Home-Decor Buyer Discovery & API Integration Hardening.
Tests provider registry, configuration detection, missing credentials isolation,
mocked API normalization, US targeting verification, Home Decor buyer relevance,
cross-provider deduplication, provenance preservation, run persistence, and REST APIs.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from search.models import DiscoveryProfile, ProviderHealth, ProviderSearchResult
from search.provider_registry import ProviderRegistry
from search.base_provider import DiscoveryProvider
from search.providers.google_provider import GoogleSearchProvider
from search.providers.directory_provider import DirectorySearchProvider
from search.providers.website_provider import WebsiteSearchProvider
from search.providers.facebook_provider import FacebookSearchProvider
from search.providers.linkedin_provider import LinkedInSearchProvider
from search.discovery_orchestrator import DiscoveryOrchestrator
from search.us_target_verifier import USTargetVerifier
from search.relevance import HomeDecorRelevanceEvaluator
from web.app import (
    SearchBuyersPayload,
    list_discovery_providers,
    get_provider_health_detail,
    search_buyers_api,
    get_discovery_stats,
    get_discovery_config_status
)


class TestPhase6Discovery(unittest.TestCase):
    def setUp(self):
        self.registry = ProviderRegistry()
        self.orchestrator = DiscoveryOrchestrator(registry=self.registry)

    # 1. Provider Registry
    def test_provider_registry(self):
        providers = self.registry.list_providers()
        self.assertEqual(len(providers), 5)
        provider_ids = [p.provider_id for p in providers]
        self.assertIn("google", provider_ids)
        self.assertIn("directory", provider_ids)
        self.assertIn("website", provider_ids)
        self.assertIn("facebook", provider_ids)
        self.assertIn("linkedin", provider_ids)

    # 2. Provider Configuration Status
    def test_provider_configuration_status(self):
        fb_health = self.registry.get_provider_health("facebook")
        self.assertIsNotNone(fb_health)
        self.assertIn(fb_health.status, ["READY", "NOT CONFIGURED"])
        self.assertIn("FACEBOOK_ACCESS_TOKEN", fb_health.required_credentials)

        dir_health = self.registry.get_provider_health("directory")
        self.assertIsNotNone(dir_health)
        self.assertEqual(dir_health.status, "READY")
        self.assertTrue(dir_health.is_configured)

    # 3. Missing API Credentials Never Crashes
    def test_missing_credentials_fails_gracefully(self):
        fb = FacebookSearchProvider()
        profile = DiscoveryProfile(product_name="Singing Bowls", product_category="Home Decor")
        with patch("search.providers.facebook_provider.load_settings", return_value={"facebook_access_token": ""}):
            res = fb.search(profile, max_results=3)
            self.assertEqual(res.status, "requires_config")
            self.assertEqual(len(res.records), 0)
            self.assertIn("FACEBOOK_ACCESS_TOKEN", res.error)

    # 4. Successful Provider Response Normalization (Mocked Google CSE API)
    @patch("requests.Session.get")
    def test_google_provider_normalization(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [
                {
                    "title": "Zenith Home Decor & Singing Bowls LLC - Wholesale Distributor",
                    "link": "https://zenithhomedecor.com",
                    "snippet": (
                        "Wholesale distributor of singing bowls and artisan home decor in Los Angeles, California. "
                        "Contact our sales team at procurement@zenithhomedecor.com or call (213) 555-0192."
                    )
                }
            ]
        }
        mock_get.return_value = mock_resp

        google_p = GoogleSearchProvider()
        profile = DiscoveryProfile(product_name="Singing Bowls", product_category="Home Decor")
        with patch("search.providers.google_provider.load_settings", return_value={"google_api_key": "dummy_key", "google_cse_id": "dummy_cx"}):
            res = google_p.search(profile, max_results=1)
            self.assertEqual(res.status, "completed")
            self.assertEqual(len(res.records), 1)
            rec = res.records[0]
            self.assertEqual(rec["email"], "procurement@zenithhomedecor.com")
            self.assertEqual(rec["country"], "United States")
            self.assertEqual(rec["state"], "California")
            self.assertEqual(rec["country_match"], "true")
            self.assertEqual(rec["product_relevance"], "High")
            self.assertEqual(rec["buyer_type"], "Wholesaler")

    # 5. Malformed Provider Response
    @patch("requests.Session.get")
    def test_malformed_response_handling(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>Malformed non-standard response without structure</html>"
        mock_get.return_value = mock_resp

        dir_p = DirectorySearchProvider()
        profile = DiscoveryProfile(product_name="Singing Bowls")
        res = dir_p.search(profile, max_results=3)
        self.assertIn(res.status, ["completed", "failed"])
        self.assertIsInstance(res.records, list)

    # 6. Provider Timeout Handling
    @patch("requests.Session.get", side_effect=Exception("Connection timeout"))
    def test_provider_timeout_isolated(self, mock_get):
        google_p = GoogleSearchProvider()
        profile = DiscoveryProfile(product_name="Singing Bowls")
        with patch("search.providers.google_provider.load_settings", return_value={"google_api_key": "k", "google_cse_id": "cx"}):
            res = google_p.search(profile, max_results=2)
            self.assertEqual(res.status, "failed")
            self.assertIn("timeout", res.error.lower())
            self.assertEqual(len(res.records), 0)

    # 7. 429 Rate Limit Handling
    @patch("requests.Session.get")
    def test_429_rate_limit_handling(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        google_p = GoogleSearchProvider()
        profile = DiscoveryProfile(product_name="Singing Bowls")
        with patch("search.providers.google_provider.load_settings", return_value={"google_api_key": "k", "google_cse_id": "cx"}):
            res = google_p.search(profile, max_results=2)
            self.assertEqual(res.status, "rate_limited")
            self.assertIn("rate limit", res.error.lower())

    # 8. Multiple Providers & Failure Isolation
    def test_multiple_providers_failure_isolation(self):
        failing_provider = MagicMock()
        failing_provider.provider_id = "failing"
        failing_provider.provider_name = "Failing Source"
        failing_provider.search.side_effect = RuntimeError("Service Down")

        working_provider = MagicMock()
        working_provider.provider_id = "working"
        working_provider.provider_name = "Working Source"
        working_provider.search.return_value = ProviderSearchResult(
            source_id="working",
            source_name="Working Source",
            status="completed",
            query_sent="test query",
            raw_results_count=1,
            records=[
                {
                    "lead_id": "lead_test_work_1",
                    "company_name": "Working Decor Store LLC",
                    "website": "https://workingdecor.com",
                    "domain": "workingdecor.com",
                    "email": "contact@workingdecor.com",
                    "phone": "(415) 555-1234",
                    "country": "United States",
                    "source": "Working Source",
                    "source_platform": "Working Source",
                    "source_url": "https://workingdecor.com",
                    "buyer_type": "Retailer",
                    "product_relevance": "High",
                    "discovered_at": "2026-09-24T00:00:00Z",
                    "email_status": "Valid",
                    "validation_status": "Valid",
                    "is_demo": False,
                    "country_match": "true",
                    "provenance": ["Working Source"]
                }
            ],
            timestamp="2026-09-24T00:00:00Z"
        )

        test_registry = ProviderRegistry()
        test_registry._providers = {"failing": failing_provider, "working": working_provider}
        orch = DiscoveryOrchestrator(registry=test_registry)

        profile = DiscoveryProfile(product_name="Singing Bowls", product_category="Home Decor")
        res = orch.execute_discovery(profile=profile, enabled_sources=["failing", "working"])

        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["extracted_lead_count"], 1)
        self.assertEqual(res["sources_status"]["failing"]["status"], "failed")
        self.assertEqual(res["sources_status"]["working"]["status"], "completed")
        self.assertGreaterEqual(len(res["errors"]), 1)

    # 9. Dynamic Query Generation
    def test_dynamic_query_generation(self):
        provider = GoogleSearchProvider()
        profile = DiscoveryProfile(
            product_name="Singing Bowls",
            product_category="Home Decor",
            target_country="United States",
            target_state="California",
            buyer_types=["Importer", "Distributor", "Wholesaler"]
        )
        query = provider.build_query(profile)
        self.assertIn('"Singing Bowls"', query)
        self.assertIn('"Home Decor"', query)
        self.assertIn('"California"', query)
        self.assertIn("USA", query)
        self.assertIn('"importer" OR "distributor" OR "wholesaler"', query)

    # 10. US Targeting Verification (Positive Case)
    def test_us_targeting_positive(self):
        res = USTargetVerifier.verify(
            company_name="Austin Acoustic Decor",
            website="https://austinacoustics.com",
            raw_text="Located in Austin, TX 78701. Contact (512) 555-8921. Wholesale USA."
        )
        self.assertEqual(res["country_match"], "true")
        self.assertEqual(res["country"], "United States")
        self.assertEqual(res["state"], "Texas")
        self.assertEqual(res["city"], "Austin")
        self.assertIn("Texas", res["country_evidence"])

    # 11. US Targeting Foreign Rejection
    def test_us_targeting_foreign_rejection(self):
        res = USTargetVerifier.verify(
            company_name="London Sound Therapy Ltd",
            website="https://londonsound.co.uk",
            raw_text="Operating across London and Manchester, United Kingdom."
        )
        self.assertEqual(res["country_match"], "false")
        self.assertNotEqual(res["country"], "United States")

    # 12. Country Unknown Handling (No False Assumption on .com)
    def test_country_unknown_handling(self):
        res = USTargetVerifier.verify(
            company_name="Universal Wellness Products",
            website="https://universalwellnessproducts.com",
            raw_text="Global provider of holistic handcrafted items. Contact via online form."
        )
        self.assertEqual(res["country_match"], "unknown")
        self.assertEqual(res["state"], None)

    # 13. Home Decor Buyer Relevance
    def test_home_decor_buyer_relevance(self):
        # High: Home Decor + Wholesaler
        high_res = HomeDecorRelevanceEvaluator.evaluate(
            company_name="Aura Home Decor & Wholesale Supply",
            raw_text="B2B wholesale distributor of handcrafted singing bowls and interior decor accents."
        )
        self.assertEqual(high_res["relevance"], "High")
        self.assertEqual(high_res["buyer_type"], "Wholesaler")

        # Medium: Commercial wholesale entity without specific decor niche in metadata
        med_res = HomeDecorRelevanceEvaluator.evaluate(
            company_name="Midwest Trade Distribution Co",
            raw_text="General commercial merchandise distributor and wholesale importer."
        )
        self.assertEqual(med_res["relevance"], "Medium")

        # Low: Irrelevant industry
        low_res = HomeDecorRelevanceEvaluator.evaluate(
            company_name="Apex Dental Software SaaS",
            raw_text="Cloud accounting and medical management software."
        )
        self.assertEqual(low_res["relevance"], "Low")

    # 14. Cross-Provider Deduplication & Provenance Preservation
    def test_cross_provider_deduplication_and_provenance(self):
        rec1 = {
            "lead_id": "lead_decor_1",
            "company_name": "Pacific Home Decor Importers",
            "website": "https://pacifichomedecor.com",
            "email": "trade@pacifichomedecor.com",
            "source": "Google Search API",
            "source_platform": "Google Search API",
            "country": "United States",
            "validation_status": "Valid",
            "country_match": "true"
        }
        rec2 = {
            "lead_id": "lead_decor_2",
            "company_name": "Pacific Home Decor Importers",
            "website": "https://pacifichomedecor.com",
            "email": "TRADE@pacifichomedecor.com",
            "phone": "(415) 555-9011",
            "source": "US B2B Trade Directory",
            "source_platform": "US B2B Trade Directory",
            "country": "United States",
            "validation_status": "Valid",
            "country_match": "true"
        }

        merged, dups = self.orchestrator.deduplicate_and_merge_provenance([rec1, rec2])
        self.assertEqual(len(merged), 1)
        self.assertEqual(dups, 1)
        unified = merged[0]
        self.assertIn("Google Search API", unified["provenance"])
        self.assertIn("US B2B Trade Directory", unified["provenance"])
        self.assertEqual(unified["phone"], "(415) 555-9011")

    # 15. Demo vs Real Lead Separation
    def test_real_vs_demo_lead_separation(self):
        mock_p = MagicMock()
        mock_p.provider_id = "mock"
        mock_p.provider_name = "Mock Provider"
        mock_p.search.return_value = ProviderSearchResult(
            source_id="mock",
            source_name="Mock Provider",
            status="completed",
            query_sent="q",
            raw_results_count=1,
            records=[
                {
                    "lead_id": "lead_test_real_1",
                    "company_name": "Real Discovered Company",
                    "website": "https://realcompany.com",
                    "source": "Mock Provider",
                    "source_platform": "Mock Provider",
                    "source_url": "https://realcompany.com",
                    "email": "buyer@realcompany.com",
                    "validation_status": "Valid",
                    "country": "United States",
                    "is_demo": False,
                    "country_match": "true"
                }
            ],
            timestamp="2026-09-24T00:00:00Z"
        )
        reg = ProviderRegistry()
        reg._providers = {"mock": mock_p}
        orch = DiscoveryOrchestrator(registry=reg)
        profile = DiscoveryProfile(product_name="Singing Bowls")
        res = orch.execute_discovery(profile=profile, enabled_sources=["mock"])
        for lead in res.get("discovered_leads", []):
            self.assertFalse(lead["is_demo"])

    # 16. REST API: list_discovery_providers()
    def test_api_list_providers(self):
        data = list_discovery_providers()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 5)
        p_ids = [p["id"] for p in data]
        self.assertIn("google", p_ids)
        self.assertIn("directory", p_ids)

    # 17. REST API: get_provider_health_detail()
    def test_api_provider_health(self):
        data = get_provider_health_detail("directory")
        self.assertEqual(data["id"], "directory")
        self.assertEqual(data["status"], "READY")

        # 404 for non-existent provider
        with self.assertRaises(HTTPException) as ctx:
            get_provider_health_detail("non_existent_api")
        self.assertEqual(ctx.exception.status_code, 404)

    # 18. REST API: search_buyers_api()
    @patch.object(DiscoveryOrchestrator, "execute_discovery")
    def test_api_search_buyers(self, mock_exec):
        mock_exec.return_value = {
            "run_id": "run_test_api_123",
            "profile": {"product_name": "Singing Bowls", "product_category": "Home Decor"},
            "raw_result_count": 5,
            "extracted_lead_count": 3,
            "us_match_count": 3,
            "valid_email_count": 2,
            "duplicate_count": 1,
            "new_leads_added": 2,
            "duration_seconds": 1.25,
            "sources_status": {"directory": {"status": "completed"}},
            "queries": ['"Singing Bowls" "Home Decor" USA'],
            "errors": [],
            "discovered_leads": [
                {
                    "lead_id": "lead_test_1",
                    "company_name": "Zenith Decor Store",
                    "email": "buyer@zenithdecor.com",
                    "country": "United States",
                    "validation_status": "Valid",
                    "country_match": "true"
                }
            ]
        }

        payload = SearchBuyersPayload(
            product_name="Singing Bowls",
            product_category="Home Decor",
            target_country="United States",
            buyer_types=["Importer", "Distributor"],
            sources=["directory"],
            max_per_source=3
        )
        data = search_buyers_api(payload)
        self.assertEqual(data["run_id"], "run_test_api_123")
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["summary"]["extracted_count"], 3)
        self.assertEqual(data["summary"]["us_match_count"], 3)
        self.assertEqual(len(data["results"]), 1)

    # 19. REST API: get_discovery_stats()
    def test_api_discovery_stats(self):
        data = get_discovery_stats()
        self.assertIn("total_runs", data)
        self.assertIn("total_raw_prospects", data)
        self.assertIn("total_us_matches", data)
        self.assertIn("total_providers", data)
        self.assertIn("configured_providers", data)

    # 20. REST API: get_discovery_config_status() (Never leaks secrets)
    def test_api_config_status_never_leaks_secrets(self):
        data = get_discovery_config_status()
        self.assertIn("google_search", data)
        self.assertIn("directory_search", data)
        self.assertIn("facebook_api", data)
        self.assertIn("linkedin_api", data)

        # Ensure no credential values are leaked
        for key, val in data.items():
            self.assertIn("configured", val)
            self.assertIn("status", val)
            self.assertIsInstance(val["configured"], bool)
            self.assertNotIn("password", str(val).lower().replace("app_password", ""))


if __name__ == "__main__":
    unittest.main()
