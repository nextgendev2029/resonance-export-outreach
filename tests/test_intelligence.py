"""
Phase 3 Unit and Integration Test Suite: AI Lead Intelligence & Enrichment Layer.
Verifies Gemini client configuration safety, schema validation, zero-hallucination extraction,
evidence tracking, demo lead exclusion, and run history persistence.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.schemas import (
    ClassificationResult,
    BuyerRelevanceResult,
    PublicContact,
    BusinessDetails,
    EvidenceItem,
    LeadEnrichmentRecord,
    EnrichmentRunRecord
)
from ai.gemini_client import GeminiClient
from ai.classifier import LeadClassifier
from ai.enricher import LeadEnricher, WebsiteContextExtractor
from app_logging.activity_logger import ActivityLogger


class TestLeadIntelligence(unittest.TestCase):
    def setUp(self):
        self.logger = ActivityLogger()
        self.client = GeminiClient(api_key="")
        self.classifier = LeadClassifier(self.client)
        self.enricher = LeadEnricher(self.client)

    def test_gemini_client_configuration_and_masking(self):
        # 1. Unconfigured detection
        unconf_client = GeminiClient(api_key="")
        self.assertFalse(unconf_client.is_configured())
        status = unconf_client.get_status()
        self.assertEqual(status["status"], "not_configured")
        self.assertFalse(status["is_configured"])
        self.assertNotIn("api_key", status)  # Never leak key

        # 2. Configured detection
        conf_client = GeminiClient(api_key="AIzaSyDummySecretKey123456")
        self.assertTrue(conf_client.is_configured())
        conf_status = conf_client.get_status()
        self.assertEqual(conf_status["status"], "ready")
        self.assertTrue(conf_status["is_configured"])
        self.assertNotIn("AIzaSyDummySecretKey123456", str(conf_status))  # Safe

    def test_ai_response_schemas_validation(self):
        # Valid classification
        c = ClassificationResult(
            classification="Business",
            confidence=0.92,
            reason="Wholesale sound healing instrument distributor",
            evidence=[EvidenceItem(field="classification", evidence="Direct B2B distributor", confidence=0.92)]
        )
        self.assertEqual(c.classification, "Business")
        self.assertEqual(c.confidence, 0.92)
        self.assertEqual(len(c.evidence), 1)

        # Buyer relevance clamping
        r = BuyerRelevanceResult(
            relevance="High",
            confidence=1.5,  # Exceeds 1.0, should clamp to 1.0
            reason="Explicitly stocks Himalayan Singing Bowls"
        )
        self.assertEqual(r.confidence, 1.0)
        self.assertEqual(r.relevance, "High")

        # Public contact role normalization
        contact = PublicContact(
            name="Sarah Jenkins",
            role="head of procurement",
            phone="+44 20 7946 0991"
        )
        self.assertEqual(contact.role, "Procurement")
        self.assertEqual(contact.name, "Sarah Jenkins")

    def test_classification_taxonomy_with_unclassified_fallback(self):
        # 1. Corporate domain -> Business
        r1 = self.classifier.classify_heuristic({
            "email": "procurement@himalayanacoustics.com",
            "company_name": "Himalayan Acoustics GmbH"
        })
        self.assertEqual(r1.classification, "Business")
        self.assertGreaterEqual(r1.confidence, 0.8)

        # 2. Commercial role prefix on generic webmail -> Business
        r2 = self.classifier.classify_heuristic({
            "email": "wholesale.orders@gmail.com",
            "company_name": "Acoustic Retreat Center"
        })
        self.assertEqual(r2.classification, "Business")

        # 3. Individual collector on personal webmail -> Individual
        r3 = self.classifier.classify_heuristic({
            "email": "michael.soundenthusiast@gmail.com",
            "buyer_name": "Michael Brown",
            "company_name": "Solo Buyer"
        })
        self.assertEqual(r3.classification, "Individual")

        # 4. Ambiguous evidence -> Unclassified (never force uncertain records)
        r4 = self.classifier.classify_heuristic({
            "email": "user9984@gmail.com",
            "company_name": "sound & wellness prospect"
        })
        self.assertEqual(r4.classification, "Unclassified")

    def test_zero_hallucination_guarantee_no_website(self):
        # Lead with missing website must not invent contact details or intent
        lead = {
            "lead_id": "test_lead_no_site_001",
            "company_name": "Unknown Studio",
            "email": "",
            "website": "",
            "is_demo": "false"
        }
        res = self.enricher.enrich_lead(lead, force_refresh=True)
        self.assertEqual(res.enrichment_status, "not_applicable")
        self.assertEqual(res.buyer_relevance.relevance, "Unknown")
        self.assertIsNone(res.public_contact.name)
        self.assertIsNone(res.public_contact.phone)
        self.assertEqual(res.public_contact.role, "Unknown")

    def test_demo_lead_exclusion_in_enrichment(self):
        # Seeded demo leads must be strictly excluded from live intelligence runs
        demo_lead = {
            "lead_id": "demo_lead_test_002",
            "company_name": "Demo Meditation Studio",
            "website": "https://demo-meditation.com",
            "is_demo": "true"
        }
        # allow_demo=False by default
        res = self.enricher.enrich_lead(demo_lead, allow_demo=False)
        self.assertEqual(res.enrichment_status, "not_applicable")
        self.assertIn("Demo lead excluded", res.error)

    def test_website_crawler_html_cleaning_and_evidence_extraction(self):
        crawler = WebsiteContextExtractor()
        sample_html = """
        <html>
            <head><title>Zenith Sound Therapy | Wholesale Singing Bowls</title></head>
            <body>
                <header><nav><a href="/home">Home</a></nav></header>
                <script>console.log("analytics");</script>
                <div class="content">
                    <h1>Handcrafted Himalayan Singing Bowls & Meditation Instruments</h1>
                    <p>We are a certified wholesale distributor of authentic 7-metal Tibetan singing bowls in Germany.</p>
                    <p>For procurement, call us at +49 89 123456 or email wholesale@zenithsound.de.</p>
                </div>
                <footer><p>© 2026 Zenith Sound</p></footer>
            </body>
        </html>
        """
        clean_text = crawler.extract_clean_text(sample_html)
        self.assertNotIn("console.log", clean_text)
        self.assertIn("wholesale distributor", clean_text)
        self.assertIn("Tibetan singing bowls", clean_text)

        # Test factual rule-based enrichment with mocked page texts
        lead = {
            "lead_id": "test_zenith_lead",
            "company_name": "Zenith Sound Therapy",
            "website": "https://zenithsound.de",
            "is_demo": "false"
        }
        pages_text = {"https://zenithsound.de": clean_text}
        meta = {"title": "Zenith Sound Therapy", "phones": ["+49 89 123456"], "emails": ["wholesale@zenithsound.de"]}

        enr = self.enricher._heuristic_enrichment(lead, pages_text, meta, ["https://zenithsound.de"])
        self.assertEqual(enr.enrichment_status, "enriched")
        self.assertEqual(enr.buyer_relevance.relevance, "High")
        self.assertGreaterEqual(enr.buyer_relevance.confidence, 0.85)
        self.assertEqual(enr.public_contact.phone, "+49 89 123456")
        self.assertTrue(len(enr.evidence) > 0)
        self.assertEqual(enr.evidence[0].url, "https://zenithsound.de")

    def test_enrichment_persistence_and_run_history(self):
        test_rec = LeadEnrichmentRecord(
            lead_id="test_persist_lead_99",
            enrichment_status="enriched",
            classification=ClassificationResult(classification="Business", confidence=0.9),
            buyer_relevance=BuyerRelevanceResult(relevance="High", confidence=0.88),
            business_details=BusinessDetails(business_type="Wholesale Distributor", industry="Sound Healing"),
            public_contact=PublicContact(phone="+1 555 0199", role="Procurement"),
            ai_model="test_model",
            ai_confidence=0.89
        )
        self.enricher.save_enrichment(test_rec)

        loaded = self.enricher.get_enrichment_by_lead_id("test_persist_lead_99")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["enrichment_status"], "enriched")
        self.assertEqual(loaded["buyer_relevance"]["relevance"], "High")
        self.assertEqual(loaded["public_contact"]["role"], "Procurement")

        # Test run logging
        run_entry = EnrichmentRunRecord(
            run_id="enrich_test_run_01",
            started_at="2026-09-23T14:00:00Z",
            completed_at="2026-09-23T14:00:02Z",
            lead_count=5,
            successful_count=4,
            failed_count=1,
            status="completed",
            duration=2.1
        )
        self.enricher.record_run(run_entry)
        runs = self.enricher.load_enrichment_runs()
        self.assertTrue(any(r["run_id"] == "enrich_test_run_01" for r in runs))


if __name__ == "__main__":
    unittest.main()
