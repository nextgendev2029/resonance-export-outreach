"""
Phase 4 Unit and Integration Test Suite: Campaigns, Personalization & Review Queue.
Verifies audience eligibility, exclusion reasons, template variable substitution,
grounded AI generation, draft validation, operator editing, version history,
duplicate prevention, attachment verification, and CRITICAL no-send safety boundaries.
"""

import sys
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from campaigns.models import (
    AudienceFilters,
    AudiencePreviewResponse,
    OutreachDraft,
    CampaignRecord
)
from campaigns.audience import AudienceSelector
from campaigns.draft_validator import DraftValidator
from campaigns.personalization import PersonalizationEngine
from campaigns.campaign_store import CampaignStore
from outreach.attachment_handler import AttachmentHandler
from config import DEFAULT_PRESENTATION_PATH


class TestCampaignsIntelligence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.camps_file = self.temp_path / "test_campaigns.json"
        self.drafts_file = self.temp_path / "test_drafts.json"
        self.sent_file = self.temp_path / "test_sent_log.csv"

        # Initialize sample sent_log.csv
        with open(self.sent_file, "w", encoding="utf-8") as f:
            f.write("email,status,timestamp,campaign_subject,error_message\n")
            f.write("already.sent@example.com,sent,2026-09-20T10:00:00Z,Test Subject,\n")
            f.write("failed.lead@example.com,failed,2026-09-20T10:05:00Z,Test Subject,SMTP timeout\n")

        self.store = CampaignStore(campaigns_file=self.camps_file, drafts_file=self.drafts_file)
        self.audience_selector = AudienceSelector(sent_log_file=self.sent_file)
        self.validator = DraftValidator()
        self.personalizer = PersonalizationEngine()

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. Campaign CRUD & Persistence
    # -------------------------------------------------------------
    def test_campaign_creation_and_persistence(self):
        payload = {
            "name": "European Sound Healing Wholesalers",
            "subject_template": "Authentic Singing Bowls - B2B Export Catalog",
            "body_template": "Dear {{buyer_name}}, introduce our export collection to {{company_name}}."
        }
        camp = self.store.create_campaign(payload)
        self.assertIn("camp_", camp["campaign_id"])
        self.assertEqual(camp["name"], "European Sound Healing Wholesalers")
        self.assertEqual(camp["status"], "Draft")

        # Verify persistence
        loaded = self.store.get_campaign(camp["campaign_id"])
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["name"], "European Sound Healing Wholesalers")

        # Update campaign
        updated = self.store.update_campaign(camp["campaign_id"], {"name": "Updated UK Wholesalers"})
        self.assertEqual(updated["name"], "Updated UK Wholesalers")

    # -------------------------------------------------------------
    # 2. Audience Eligibility & Exclusion Reason Tests
    # -------------------------------------------------------------
    def test_audience_eligibility_and_exclusion_reasons(self):
        sample_leads = [
            # 1. Fully eligible real lead
            {
                "lead_id": "lead_01",
                "email": "procurement@soundwholesaler.com",
                "company_name": "Sound Wholesaler Ltd",
                "validation_status": "Valid",
                "classification": "Business",
                "buyer_relevance": "High",
                "is_demo": False,
                "outreach_status": "Not contacted"
            },
            # 2. Excluded: Demo lead
            {
                "lead_id": "lead_02",
                "email": "demo@example.com",
                "company_name": "Demo Wellness",
                "validation_status": "Valid",
                "classification": "Business",
                "buyer_relevance": "High",
                "is_demo": True,
                "outreach_status": "Not contacted"
            },
            # 3. Excluded: Invalid email
            {
                "lead_id": "lead_03",
                "email": "invalid-email-string",
                "company_name": "Invalid Email Corp",
                "validation_status": "Invalid",
                "classification": "Business",
                "buyer_relevance": "High",
                "is_demo": False,
                "outreach_status": "Not contacted"
            },
            # 4. Excluded: Missing email
            {
                "lead_id": "lead_04",
                "email": "",
                "company_name": "No Email Studio",
                "validation_status": "Missing",
                "classification": "Business",
                "buyer_relevance": "High",
                "is_demo": False,
                "outreach_status": "Not contacted"
            },
            # 5. Excluded: Individual contact
            {
                "lead_id": "lead_05",
                "email": "john.practitioner@gmail.com",
                "company_name": "John Yoga Solo",
                "validation_status": "Valid",
                "classification": "Individual",
                "buyer_relevance": "High",
                "is_demo": False,
                "outreach_status": "Not contacted"
            },
            # 6. Excluded: Low buyer relevance
            {
                "lead_id": "lead_06",
                "email": "contact@logisticsfreight.com",
                "company_name": "Freight Logistics",
                "validation_status": "Valid",
                "classification": "Business",
                "buyer_relevance": "Low",
                "is_demo": False,
                "outreach_status": "Not contacted"
            },
            # 7. Excluded: Already contacted in sent_log.csv
            {
                "lead_id": "lead_07",
                "email": "already.sent@example.com",
                "company_name": "Past Recipient Ltd",
                "validation_status": "Valid",
                "classification": "Business",
                "buyer_relevance": "High",
                "is_demo": False,
                "outreach_status": "Contacted"
            }
        ]

        filters = AudienceFilters(
            dataset="real",
            classification=["Business"],
            validation_status=["Valid"],
            buyer_relevance=["High", "Medium"],
            contacted_status="never"
        )

        preview = self.audience_selector.evaluate_all(sample_leads, filters)
        self.assertEqual(preview.total_evaluated, 7)
        self.assertEqual(preview.eligible_count, 1)
        self.assertEqual(preview.excluded_count, 6)
        self.assertEqual(preview.eligible_lead_ids, ["lead_01"])

        # Verify explicit exclusion breakdown counts
        reasons = preview.exclusion_reasons
        self.assertEqual(reasons.get("demo_data"), 1)
        self.assertEqual(reasons.get("invalid_email"), 1)
        self.assertEqual(reasons.get("missing_email"), 1)
        self.assertEqual(reasons.get("individual_contact"), 1)
        self.assertEqual(reasons.get("low_relevance"), 1)
        self.assertEqual(reasons.get("already_contacted"), 1)

    # -------------------------------------------------------------
    # 3. Variable Substitution & Safe Fallbacks
    # -------------------------------------------------------------
    def test_variable_substitution_safe_fallbacks(self):
        template = "Dear {{buyer_name}},\n\nI noticed that {{company_name}} operates in {{country}}."
        
        # Test with missing variables (must not render "undefined" or "{{ buyer_name }}")
        empty_context = {"buyer_name": None, "company_name": "", "country": None}
        rendered = self.personalizer.substitute_variables(template, empty_context)
        self.assertNotIn("undefined", rendered)
        self.assertNotIn("{{", rendered)
        self.assertIn("Procurement Team", rendered)
        self.assertIn("your organization", rendered)
        self.assertIn("international", rendered)

        # Test with valid variables
        full_context = {
            "buyer_name": "Sarah Jenkins",
            "company_name": "Aura Wellness UK",
            "country": "United Kingdom"
        }
        rendered_full = self.personalizer.substitute_variables(template, full_context)
        self.assertIn("Dear Sarah Jenkins,", rendered_full)
        self.assertIn("Aura Wellness UK", rendered_full)
        self.assertIn("United Kingdom", rendered_full)

    # -------------------------------------------------------------
    # 4. Draft Generation & Schema
    # -------------------------------------------------------------
    def test_draft_generation_schema_and_versioning(self):
        lead = {
            "lead_id": "lead_test_101",
            "email": "purchasing@zenhealing.de",
            "company_name": "Zen Healing Supplies GmbH",
            "country": "Germany",
            "buyer_name": "Marcus Becker",
            "classification": "Business",
            "buyer_relevance": "High",
            "is_demo": False,
            "enrichment": {
                "business_details": {
                    "business_type": "Wholesale Distributor",
                    "industry": "Sound Therapy & Meditation",
                    "company_description": "Importer of holistic acoustic instruments"
                },
                "buyer_relevance": {
                    "relevance": "High",
                    "reason": "Direct distributor of sound healing instruments"
                },
                "evidence": [
                    {
                        "field": "wholesale_available",
                        "url": "https://zenhealing.de/wholesale",
                        "evidence": "Supplying Tibetan sound bowls to German wellness centers."
                    }
                ]
            }
        }

        draft = self.personalizer.generate_draft(
            lead=lead,
            campaign_id="camp_test_01",
            subject_template="Wholesale Himalayan Singing Bowls for {{company_name}}",
            body_template=None
        )

        self.assertIsInstance(draft, OutreachDraft)
        self.assertEqual(draft.company_name, "Zen Healing Supplies GmbH")
        self.assertEqual(draft.recipient_email, "purchasing@zenhealing.de")
        self.assertIn("Zen Healing Supplies GmbH", draft.subject)
        self.assertTrue(len(draft.body) > 100)
        self.assertEqual(draft.status, "Draft")
        self.assertIn("subject", draft.original_ai_draft)
        self.assertEqual(len(draft.version_history), 1)
        self.assertEqual(draft.version_history[0]["version"], 1)

    # -------------------------------------------------------------
    # 5. Draft Validation (Grounding, Spam & Cliché Detection)
    # -------------------------------------------------------------
    def test_draft_validation_grounding_and_spam(self):
        # 1. Clean professional B2B draft
        clean_subj = "Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog"
        clean_body = """Dear Marcus Becker,

I noticed that Zen Healing Supplies specializes in wholesale acoustic and sound therapy instruments.

We are Himalayan artisan exporters of handcrafted 7-metal Tibetan Singing Bowls, meditation gongs, and sound-healing instruments. We would love to share our direct manufacturer export catalog and wholesale pricing with your purchasing team.

Please find our complete presentation and export specifications attached. Would you be open to reviewing our wholesale price sheet this week?

Warm regards,
Export Operations Team"""

        val_clean = self.validator.validate(clean_subj, clean_body, {"company_name": "Zen Healing Supplies"})
        self.assertTrue(val_clean.is_grounded)
        self.assertFalse(val_clean.spam_detected)
        self.assertTrue(val_clean.tone_appropriate)

        # 2. Spam & hype triggers detected
        spam_subj = "ACT NOW URGENT FREE 100% GUARANTEED SINGING BOWLS!!!"
        spam_body = "Click here to buy now and get special promotion with no risk at all!!!!!!"
        val_spam = self.validator.validate(spam_subj, spam_body, {})
        self.assertTrue(val_spam.spam_detected)
        self.assertEqual(val_spam.suggested_status, "Needs Review")

        # 3. Fake familiarity detected
        cliche_subj = "Singing bowls for you"
        cliche_body = "I hope this email finds you well! I came across your amazing website and we are thrilled to reach out."
        val_cliche = self.validator.validate(cliche_subj, cliche_body, {})
        self.assertFalse(val_cliche.tone_appropriate)
        self.assertIn("Generic marketing cliché", str(val_cliche.issues))

        # 4. Fabricated intent detected
        fake_intent_body = "I saw you are currently looking for new singing bowl suppliers and following up on our recent conversation."
        val_intent = self.validator.validate("Subject", fake_intent_body, {})
        self.assertFalse(val_intent.is_grounded)
        self.assertIn("Potential unsupported claim", str(val_intent.issues))

    # -------------------------------------------------------------
    # 6. Draft Operator Editing & Auditability
    # -------------------------------------------------------------
    def test_operator_editing_preserves_original_draft(self):
        lead = {
            "lead_id": "lead_edit_01",
            "email": "buyer@aura.co.uk",
            "company_name": "Aura Sound UK",
            "classification": "Business",
            "buyer_relevance": "High"
        }
        draft = self.personalizer.generate_draft(lead, "camp_001")
        saved = self.store.save_draft(draft)

        original_subject = saved["original_ai_draft"]["subject"]
        self.assertIsNotNone(original_subject)

        # Operator edits the draft
        updated = self.store.update_draft(
            saved["draft_id"],
            {"subject": "Custom Operator Subject: Himalayan Bowls for Aura Sound UK"}
        )

        self.assertEqual(updated["subject"], "Custom Operator Subject: Himalayan Bowls for Aura Sound UK")
        self.assertEqual(updated["status"], "Edited")
        # Ensure original AI draft was NOT overwritten
        self.assertEqual(updated["original_ai_draft"]["subject"], original_subject)
        self.assertIn("operator_edited_draft", updated)
        self.assertEqual(updated["operator_edited_draft"]["subject"], "Custom Operator Subject: Himalayan Bowls for Aura Sound UK")

    # -------------------------------------------------------------
    # 7. Draft Regeneration & Version History
    # -------------------------------------------------------------
    def test_draft_regeneration_version_history(self):
        lead = {
            "lead_id": "lead_regen_01",
            "email": "buyer@zen.com",
            "company_name": "Zen Corp",
            "classification": "Business",
            "buyer_relevance": "High"
        }
        draft = self.personalizer.generate_draft(lead, "camp_002")
        saved = self.store.save_draft(draft)
        self.assertEqual(len(saved["version_history"]), 1)

        # Regenerate draft
        regen = self.store.record_regeneration(
            draft_id=saved["draft_id"],
            new_subject="Regenerated Subject Version 2",
            new_opening="Regenerated opening line",
            new_body="Regenerated email body meeting B2B export criteria with full specifications.",
            new_closing="Best regards,\nExport Team",
            new_confidence=0.92,
            reason="Regenerated with expanded sound healing specifications."
        )

        self.assertEqual(regen["subject"], "Regenerated Subject Version 2")
        self.assertEqual(len(regen["version_history"]), 2)
        self.assertEqual(regen["version_history"][0]["version"], 1)
        self.assertEqual(regen["version_history"][1]["version"], 2)

    # -------------------------------------------------------------
    # 8. Approval, Rejection & Bulk Operations
    # -------------------------------------------------------------
    def test_approval_and_rejection_workflows(self):
        lead1 = {"lead_id": "l_app_1", "email": "a@test.com", "company_name": "A Co", "classification": "Business"}
        lead2 = {"lead_id": "l_app_2", "email": "b@test.com", "company_name": "B Co", "classification": "Business"}

        d1 = self.store.save_draft(self.personalizer.generate_draft(lead1, "camp_bulk"))
        d2 = self.store.save_draft(self.personalizer.generate_draft(lead2, "camp_bulk"))

        # Single approve
        app1 = self.store.approve_draft(d1["draft_id"])
        self.assertEqual(app1["status"], "Approved")
        self.assertIsNotNone(app1["approved_at"])

        # Single reject with reason
        rej2 = self.store.reject_draft(d2["draft_id"], reason="Wrong audience profile")
        self.assertEqual(rej2["status"], "Rejected")
        self.assertEqual(rej2["rejection_reason"], "Wrong audience profile")
        self.assertIsNotNone(rej2["rejected_at"])

        # Bulk approve
        bulk_count = self.store.bulk_approve([d2["draft_id"]])
        self.assertEqual(bulk_count, 1)
        self.assertEqual(self.store.get_draft(d2["draft_id"])["status"], "Approved")

    # -------------------------------------------------------------
    # 9. Duplicate Campaign/Lead Protection
    # -------------------------------------------------------------
    def test_duplicate_campaign_lead_protection(self):
        lead = {"lead_id": "dup_lead_99", "email": "same@company.com", "company_name": "Same Co"}
        d1 = self.personalizer.generate_draft(lead, "camp_dup")
        d2 = self.personalizer.generate_draft(lead, "camp_dup")  # Same campaign and lead

        self.store.save_draft(d1)
        self.store.save_draft(d2)

        drafts = self.store.list_drafts("camp_dup")
        # Must only have 1 draft for this (campaign_id, lead_id)
        self.assertEqual(len(drafts), 1)

    # -------------------------------------------------------------
    # 10. Attachment Validation
    # -------------------------------------------------------------
    def test_company_presentation_attachment_ready(self):
        self.assertTrue(DEFAULT_PRESENTATION_PATH.exists())
        self.assertTrue(AttachmentHandler.validate_file(str(DEFAULT_PRESENTATION_PATH)))
        self.assertEqual(DEFAULT_PRESENTATION_PATH.suffix.lower(), ".pdf")

    # -------------------------------------------------------------
    # 11. CRITICAL: No-Send Safety Boundary
    # -------------------------------------------------------------
    @patch("outreach.gmail_sender.GmailSender.send_campaign")
    def test_campaign_generation_and_approval_never_invokes_gmail(self, mock_send):
        """
        Hard safety test: proves campaign creation, draft generation, editing,
        and approval operations NEVER invoke GmailSender.send_campaign.
        """
        lead = {
            "lead_id": "safe_lead_01",
            "email": "critical.safety@prospect.com",
            "company_name": "Safety First Wellness",
            "classification": "Business",
            "buyer_relevance": "High"
        }
        camp = self.store.create_campaign({"name": "Safe Campaign"})
        draft = self.personalizer.generate_draft(lead, camp["campaign_id"])
        saved = self.store.save_draft(draft)

        # Operator approves draft
        self.store.approve_draft(saved["draft_id"])
        # Bulk approve
        self.store.bulk_approve([saved["draft_id"]])

        # Verify GmailSender was NOT called
        mock_send.assert_not_called()
        self.assertEqual(mock_send.call_count, 0)


if __name__ == "__main__":
    unittest.main()
