"""
Unit and Integration Tests for Resonance - Export Outreach & Lead Operations.
Phase 2 Test Suite: Buyer Discovery, Extraction, Validation Taxonomy, Deduplication, & Demo Safety.
"""

import sys
import unittest
from pathlib import Path

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_settings, DEFAULT_SETTINGS, SETTINGS_FILE
from validation.email_validator import EmailValidator
from extraction.data_extractor import DataExtractor
from classification.ai_classifier import AIClassifier
from app_logging.activity_logger import ActivityLogger
from reports.report_generator import ReportGenerator
from outreach.attachment_handler import AttachmentHandler
from outreach.gmail_sender import GmailSender
from search.base_adapter import BaseSearchAdapter
from search.discovery_engine import DiscoveryEngine
from search.google_search import GoogleSearchAdapter
from search.facebook_search import FacebookSearchAdapter
from search.linkedin_search import LinkedInSearchAdapter
from search.directory_search import DirectorySearchAdapter
from search.website_search import WebsiteSearchAdapter


class TestResonanceSystem(unittest.TestCase):
    def setUp(self):
        self.logger = ActivityLogger()
        self.report_gen = ReportGenerator(self.logger)

    def test_settings_load(self):
        settings = load_settings()
        self.assertIn("search_keyword", settings)
        self.assertEqual(settings["search_keyword"], "Singing Bowls")
        self.assertIn("daily_send_limit", settings)

    def test_email_validation_taxonomy(self):
        # 1. Valid corporate email
        ok, status, _ = EmailValidator.validate("procurement@zenithsoundhealing.de")
        self.assertTrue(ok)
        self.assertEqual(status, "Valid")

        # 2. Review (disposable or placeholder domain)
        ok, status, _ = EmailValidator.validate("test@mailinator.com")
        self.assertFalse(ok)
        self.assertEqual(status, "Review")

        ok, status, _ = EmailValidator.validate("info@example.com")
        self.assertFalse(ok)
        self.assertEqual(status, "Review")

        # 3. Missing email (empty or whitespace)
        ok, status, _ = EmailValidator.validate("")
        self.assertFalse(ok)
        self.assertEqual(status, "Missing")

        ok, status, _ = EmailValidator.validate("   ")
        self.assertFalse(ok)
        self.assertEqual(status, "Missing")

        # 4. Invalid email (malformed, no TLD, or image asset)
        ok, status, _ = EmailValidator.validate("invalid-email-address")
        self.assertFalse(ok)
        self.assertEqual(status, "Invalid")

        ok, status, _ = EmailValidator.validate("user@missingdotdomain")
        self.assertFalse(ok)
        self.assertEqual(status, "Invalid")

        ok, status, _ = EmailValidator.validate("image@studio.com.png")
        self.assertFalse(ok)
        self.assertEqual(status, "Invalid")

    def test_data_extractor_and_normalization(self):
        raw_text = (
            "Welcome to Sound Meditation Studio! For wholesale inquiries, "
            "contact wholesale@soundmeditation.com or visit soundmeditation.com. "
            "Located in Germany."
        )
        emails = DataExtractor.extract_emails_from_text(raw_text)
        self.assertIn("wholesale@soundmeditation.com", emails)

        # Test obfuscation handling: user [at] domain [dot] com
        obfuscated_text = "Reach us at contact [at] soundhealinghub [dot] com for catalog."
        obf_emails = DataExtractor.extract_emails_from_text(obfuscated_text)
        self.assertIn("contact@soundhealinghub.com", obf_emails)

        record = DataExtractor.normalize_record(
            email="wholesale@soundmeditation.com",
            source_platform="Google Search",
            raw_text=raw_text,
            source_url="https://soundmeditation.com/contact"
        )
        self.assertEqual(record["email"], "wholesale@soundmeditation.com")
        self.assertEqual(record["country"], "Germany")
        self.assertEqual(record["validation_status"], "Valid")
        self.assertEqual(record["source_url"], "https://soundmeditation.com/contact")
        self.assertTrue(record["lead_id"].startswith("lead_"))

    def test_data_extractor_preserves_missing_email(self):
        # Documentation specifies missing/unparseable emails must NOT be silently discarded
        record = DataExtractor.normalize_record(
            email="",
            source_platform="Business Directory",
            company_name="Alpine Tibetan Acoustics",
            website="https://alpinetibetan.ch",
            source_url="https://alpinetibetan.ch/about"
        )
        self.assertEqual(record["email"], "")
        self.assertEqual(record["validation_status"], "Missing")
        self.assertEqual(record["company_name"], "Alpine Tibetan Acoustics")

    def test_query_builder(self):
        query = BaseSearchAdapter.build_query(
            keyword="Singing Bowls",
            qualifiers=["wholesale", "distributor", "importer"],
            extra_operator="site:linkedin.com"
        )
        self.assertIn('"Singing Bowls"', query)
        self.assertIn('"wholesale" OR "distributor" OR "importer"', query)
        self.assertIn("site:linkedin.com", query)

    def test_source_adapters_health(self):
        adapters = [
            GoogleSearchAdapter(),
            FacebookSearchAdapter(),
            LinkedInSearchAdapter(),
            DirectorySearchAdapter(),
            WebsiteSearchAdapter()
        ]
        for adapter in adapters:
            health = adapter.get_health_status()
            self.assertIn("id", health)
            self.assertIn("name", health)
            self.assertIn("status", health)
            self.assertIn(health["status"], ["ready", "requires_config", "unavailable"])
            self.assertIn("description", health)

    def test_dual_key_deduplication(self):
        # 1. Primary key: normalized email
        rec1 = {
            "email": "test-dedup-primary@resonance-test.org",
            "company_name": "Test Sound Co 1",
            "source_platform": "Google Search"
        }
        added1 = self.logger.append_buyers([rec1])
        self.assertEqual(added1, 1)

        # Duplicate with uppercase email should be skipped
        rec2 = {
            "email": "TEST-DEDUP-PRIMARY@resonance-test.org",
            "company_name": "Different Name",
            "source_platform": "Website Search"
        }
        added2 = self.logger.append_buyers([rec2])
        self.assertEqual(added2, 0)

        # 2. Secondary fingerprint: company + website when email is empty
        rec3 = {
            "email": "",
            "company_name": "Unique Sound Sanctuary",
            "website": "https://uniquesoundsanctuary.com",
            "source_platform": "Business Directory"
        }
        added3 = self.logger.append_buyers([rec3])
        self.assertEqual(added3, 1)

        rec4 = {
            "email": "",
            "company_name": "Unique Sound Sanctuary",
            "website": "https://uniquesoundsanctuary.com",
            "source_platform": "Google Search"
        }
        added4 = self.logger.append_buyers([rec4])
        self.assertEqual(added4, 0)

        # Clean up test records
        self.logger.delete_lead("test-dedup-primary@resonance-test.org")
        self.logger.delete_lead("https://uniquesoundsanctuary.com")

    def test_demo_safety_guard_in_outreach(self):
        sender = GmailSender()
        # Seeded demo leads in buyers.csv must be strictly suppressed from live dispatch
        result = sender.send_campaign(audience="business")
        self.assertGreaterEqual(result.get("demo_suppressed", 0), 1)

    def test_ai_classifier_heuristics(self):
        classifier = AIClassifier()
        sample_records = [
            {"email": "procurement@soundhealingcenter.com", "company_name": "Sound Healing Center LLC"},
            {"email": "john.doe.collector@gmail.com", "company_name": "Solo Buyer"}
        ]
        res = classifier.classify_batch_heuristic(sample_records)
        self.assertEqual(res[0]["classification"], "Business")
        self.assertEqual(res[1]["classification"], "Individual")

    def test_lead_update_and_persistence(self):
        test_rec = {
            "email": "patch-test@resonance-acoustics.com",
            "company_name": "Pre-Patch Acoustics",
            "source_platform": "Directory"
        }
        self.logger.append_buyers([test_rec])
        lead = self.logger.get_lead_by_id_or_email("patch-test@resonance-acoustics.com")
        self.assertIsNotNone(lead)

        updated = self.logger.update_lead(
            lead["lead_id"],
            {"company_name": "Post-Patch Acoustics Inc", "notes": "Verified buyer profile"}
        )
        self.assertTrue(updated)

        refreshed = self.logger.get_lead_by_id_or_email(lead["lead_id"])
        self.assertEqual(refreshed["company_name"], "Post-Patch Acoustics Inc")
        self.assertEqual(refreshed["notes"], "Verified buyer profile")

        # Clean up
        self.logger.delete_lead(lead["lead_id"])

    def test_presentation_attachment_verified(self):
        settings = load_settings()
        pres_path = settings.get("presentation_path")
        self.assertTrue(AttachmentHandler.validate_file(pres_path))


if __name__ == "__main__":
    unittest.main()
