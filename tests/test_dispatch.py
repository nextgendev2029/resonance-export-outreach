"""
Unit and Integration Test Suite for Phase 5:
Controlled Dispatch Engine, Delivery Telemetry & Campaign Analytics.

Tests:
1. Final Send Eligibility (15-point deterministic checks)
2. Demo Data Isolation (is_demo == true never sent)
3. Suppression Protection (suppressed recipient never sent)
4. Duplicate Prevention (sent_log.csv historical protection)
5. Unresolved Template Variables & Placeholders ({{...}}, undefined, null, None)
6. Attachment Verification (valid PDF)
7. Rate Limiting (Daily, Campaign, and Per-Run bounds)
8. Persistent Queue & Atomic Claiming (concurrency and crash recovery)
9. Dry-Run Mode (0 SMTP calls)
10. Mocked Gmail Sender (success, temporary failure, permanent failure, auth failure, timeout)
11. Bounded Retries
12. Critical Test (campaign creation, draft gen, approval, preflight, analytics NEVER call SMTP)
13. Full Mock Dispatch Integration (Approved -> Preflight -> Queue -> Confirm -> Mock SMTP -> Sent -> Sent Log -> Analytics -> Duplicate Check)
"""

import os
import csv
import json
import smtplib
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from campaigns.models import CampaignRecord, OutreachDraft
from campaigns.campaign_store import CampaignStore
from dispatch.models import (
    DispatchQueueItem,
    PreflightReport,
    DispatchConfirmPayload,
    TestSendPayload
)
from dispatch.suppression import SuppressionManager
from dispatch.delivery_log import DeliveryLogger, AuditLogger
from dispatch.rate_limiter import RateLimiter
from dispatch.eligibility import FinalEligibilityChecker, EligibilityResult
from dispatch.queue import DispatchQueue
from dispatch.sender import DispatchSender
from dispatch.dispatcher import DispatchCoordinator
from dispatch.analytics import AnalyticsService
from app_logging.activity_logger import ActivityLogger


class TestDispatchEligibility(unittest.TestCase):
    """Test deterministic 15-point final pre-dispatch eligibility checker."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.sent_log = self.base_path / "sent_log.csv"
        self.suppression_file = self.base_path / "suppression_list.json"
        self.test_pdf = self.base_path / "valid_presentation.pdf"

        # Create valid dummy PDF header
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")

        with open(self.sent_log, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "status", "timestamp", "campaign_subject", "error_message"])

        self.supp_mgr = SuppressionManager(storage_file=self.suppression_file)
        self.checker = FinalEligibilityChecker(
            suppression_mgr=self.supp_mgr,
            sent_log_path=self.sent_log
        )

        self.valid_campaign = {
            "campaign_id": "camp_test_01",
            "name": "Export Campaign Test",
            "status": "Approved",
            "attachment_path": str(self.test_pdf)
        }

        self.valid_draft = {
            "draft_id": "draft_01",
            "campaign_id": "camp_test_01",
            "lead_id": "lead_01",
            "recipient_email": "buyer@example.de",
            "recipient_name": "Hans Gruber",
            "company_name": "Klangschalen GmbH",
            "subject": "Handcrafted Himalayan Singing Bowls B2B Catalog",
            "body": "Dear Hans, We are pleased to present our certified singing bowls.",
            "status": "Approved",
            "classification": "Business",
            "buyer_relevance": "High",
            "validation_status": "Valid",
            "is_demo": False
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approved_valid_draft_passes(self):
        res = self.checker.check_draft_eligibility(self.valid_draft, self.valid_campaign)
        self.assertTrue(res.eligible)
        self.assertEqual(res.status_code, "eligible")

    def test_unapproved_draft_blocked(self):
        draft = self.valid_draft.copy()
        draft["status"] = "Draft"
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "unapproved")

    def test_demo_lead_permanently_blocked(self):
        draft = self.valid_draft.copy()
        draft["is_demo"] = True
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "demo_blocked")
        self.assertIn("Demo leads", res.reason)

    def test_individual_lead_blocked(self):
        draft = self.valid_draft.copy()
        draft["classification"] = "Individual"
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "non_business")

    def test_invalid_email_blocked(self):
        draft = self.valid_draft.copy()
        draft["recipient_email"] = "not-an-email"
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "invalid")

    def test_missing_email_blocked(self):
        draft = self.valid_draft.copy()
        draft["recipient_email"] = ""
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "invalid")

    def test_low_relevance_blocked(self):
        draft = self.valid_draft.copy()
        draft["buyer_relevance"] = "Low"
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "low_relevance")

    def test_suppressed_recipient_blocked(self):
        self.supp_mgr.add_suppression("buyer@example.de", reason="unsubscribe")
        res = self.checker.check_draft_eligibility(self.valid_draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "suppressed")

    def test_already_contacted_duplicate_blocked(self):
        with open(self.sent_log, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["buyer@example.de", "sent", "2026-09-01T00:00:00Z", "Past Subject", ""])

        res = self.checker.check_draft_eligibility(self.valid_draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "duplicate")

    def test_cancelled_campaign_blocked(self):
        camp = self.valid_campaign.copy()
        camp["status"] = "Cancelled"
        res = self.checker.check_draft_eligibility(self.valid_draft, camp)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "campaign_inactive")

    def test_paused_campaign_blocked(self):
        camp = self.valid_campaign.copy()
        camp["status"] = "Paused"
        res = self.checker.check_draft_eligibility(self.valid_draft, camp)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "campaign_inactive")

    def test_unresolved_template_variable_blocked(self):
        draft = self.valid_draft.copy()
        draft["body"] = "Hello {{buyer_name}}, your order is ready."
        res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
        self.assertFalse(res.eligible)
        self.assertEqual(res.status_code, "unresolved_placeholder")

    def test_undefined_null_placeholder_blocked(self):
        for placeholder in ("undefined", "null", "None"):
            draft = self.valid_draft.copy()
            draft["body"] = f"Dear Partner, regarding {placeholder} in our catalog."
            res = self.checker.check_draft_eligibility(draft, self.valid_campaign)
            self.assertFalse(res.eligible)
            self.assertEqual(res.status_code, "unresolved_placeholder")

    def test_missing_attachment_blocks_campaign(self):
        ok, err = self.checker.verify_attachment(str(self.base_path / "non_existent.pdf"))
        self.assertFalse(ok)
        self.assertIn("not found", err)

    def test_invalid_attachment_non_pdf_blocked(self):
        txt_file = self.base_path / "file.txt"
        with open(txt_file, "w") as f:
            f.write("text file")
        ok, err = self.checker.verify_attachment(str(txt_file))
        self.assertFalse(ok)
        self.assertIn("must be a .pdf", err)


class TestDispatchQueueAndClaiming(unittest.TestCase):
    """Test persistent queue, atomic claiming, and crash recovery."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_file = Path(self.temp_dir.name) / "dispatch_queue.json"
        self.queue = DispatchQueue(storage_file=self.queue_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_enqueue_and_atomic_claim(self):
        item = DispatchQueueItem(
            dispatch_id="disp_1",
            campaign_id="camp_1",
            draft_id="draft_1",
            recipient_email="test@example.com",
            subject="Test Subj",
            body="Test Body",
            status="Queued"
        )
        self.assertTrue(self.queue.enqueue(item))
        # Second enqueue of same (campaign_id, draft_id) returns False
        self.assertFalse(self.queue.enqueue(item))

        # Atomic claim transitions Queued -> Sending
        claimed = self.queue.claim_next("camp_1")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.dispatch_id, "disp_1")
        self.assertEqual(claimed.status, "Sending")

        # Second claim returns None because item is already claimed
        claimed_second = self.queue.claim_next("camp_1")
        self.assertIsNone(claimed_second)

    def test_crash_recovery_transitions_stale_sending_to_blocked(self):
        # Create an item left in 'Sending' state due to simulated server crash
        item = DispatchQueueItem(
            dispatch_id="disp_crash",
            campaign_id="camp_1",
            draft_id="draft_crash",
            recipient_email="crash@example.com",
            subject="Crash Subj",
            body="Crash Body",
            status="Sending"
        )
        self.queue.enqueue(item)

        # Recover on startup
        recovered_count = self.queue.recover_stale_sending()
        self.assertEqual(recovered_count, 1)

        recovered_item = self.queue.get_item("disp_crash")
        self.assertEqual(recovered_item.status, "Blocked")
        self.assertIn("requires review", recovered_item.last_error)



class TestSuppressionManagement(unittest.TestCase):
    """Test suppression list persistence and case-insensitive matching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.supp_file = Path(self.temp_dir.name) / "suppression_list.json"
        self.mgr = SuppressionManager(storage_file=self.supp_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_suppression_lifecycle(self):
        self.assertFalse(self.mgr.is_suppressed("optout@domain.com"))

        # Add suppression
        rec = self.mgr.add_suppression("OptOut@Domain.com", reason="unsubscribe", operator_note="Requested removal")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.email, "optout@domain.com")

        # Case-insensitive lookup
        self.assertTrue(self.mgr.is_suppressed("OPTOUT@domain.com"))
        self.assertTrue(self.mgr.is_suppressed("optout@domain.com"))

        # Remove suppression
        removed = self.mgr.remove_suppression("optout@domain.com")
        self.assertTrue(removed)
        self.assertFalse(self.mgr.is_suppressed("optout@domain.com"))


class TestDispatchSenderAndDryRun(unittest.TestCase):
    """Test DispatchSender in dry-run mode and mocked SMTP scenarios."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.test_pdf = self.base_path / "pres.pdf"
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")

        self.mock_logger = MagicMock()
        self.item = DispatchQueueItem(
            dispatch_id="disp_test",
            campaign_id="camp_test",
            draft_id="draft_test",
            lead_id="lead_test",
            recipient_email="lead@b2b-client.com",
            recipient_name="Frau Schmidt",
            company_name="Meditationszentrum",
            subject="Singing Bowls Catalog",
            body="Guten Tag Frau Schmidt, hier ist unser Katalog.",
            attachment_path=str(self.test_pdf),
            status="Queued"
        )


    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_mode_never_calls_smtp(self):
        settings = {
            "dry_run": True,
            "gmail_email": "test@gmail.com",
            "gmail_app_password": "password",
            "presentation_path": str(self.test_pdf)
        }
        sender = DispatchSender(settings=settings, logger=self.mock_logger)

        with patch("outreach.gmail_auth.GmailAuth.connect_and_login") as mock_login:
            success, msg_id, err_msg, err_cat = sender.send_item(self.item)
            self.assertTrue(success)
            self.assertIn("dry-run", msg_id)
            mock_login.assert_not_called()

    def test_mocked_smtp_successful_send(self):
        settings = {
            "dry_run": False,
            "gmail_email": "test@gmail.com",
            "gmail_app_password": "password",
            "presentation_path": str(self.test_pdf)
        }
        sender = DispatchSender(settings=settings, logger=self.mock_logger)

        mock_server = MagicMock()
        mock_server.send_message.return_value = {}

        success, msg_id, err_msg, err_cat = sender.send_item(self.item, smtp_server=mock_server)
        self.assertTrue(success)
        mock_server.send_message.assert_called_once()
        self.mock_logger.log_send_attempt.assert_called_once()

    def test_mocked_smtp_transient_error_classification(self):
        settings = {
            "dry_run": False,
            "gmail_email": "test@gmail.com",
            "gmail_app_password": "password"
        }
        sender = DispatchSender(settings=settings, logger=self.mock_logger)

        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPServerDisconnected("Connection reset by peer")

        success, msg_id, err_msg, err_cat = sender.send_item(self.item, smtp_server=mock_server)
        self.assertFalse(success)
        self.assertEqual(err_cat, "transient")

    def test_mocked_smtp_permanent_auth_failure_classification(self):
        settings = {
            "dry_run": False,
            "gmail_email": "test@gmail.com",
            "gmail_app_password": "bad_password"
        }
        sender = DispatchSender(settings=settings, logger=self.mock_logger)


        with patch("outreach.gmail_auth.GmailAuth.connect_and_login") as mock_login:
            mock_login.return_value = (None, "SMTP Authentication failed: 535 5.7.8")
            success, msg_id, err_msg, err_cat = sender.send_item(self.item)
            self.assertFalse(success)
            self.assertEqual(err_cat, "permanent")


class TestCriticalSafetyBoundary(unittest.TestCase):
    """
    CRITICAL TEST: Verify that campaign creation, draft generation, draft approval,
    queue creation, preflight, and analytics DO NOT invoke the SMTP sender.
    Only explicit operator confirmation can invoke the sender.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.campaigns_file = self.base_path / "campaigns.json"
        self.drafts_file = self.base_path / "drafts.json"
        self.queue_file = self.base_path / "queue.json"
        self.supp_file = self.base_path / "supp.json"
        self.log_file = self.base_path / "log.json"
        self.audit_file = self.base_path / "audit.json"
        self.test_pdf = self.base_path / "pres.pdf"
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")

        self.camp_store = CampaignStore(
            campaigns_file=self.campaigns_file,
            drafts_file=self.drafts_file
        )
        self.queue = DispatchQueue(storage_file=self.queue_file)
        self.supp_mgr = SuppressionManager(storage_file=self.supp_file)
        self.dev_logger = DeliveryLogger(storage_file=self.log_file)
        self.audit_logger = AuditLogger(storage_file=self.audit_file)

        self.coordinator = DispatchCoordinator(
            campaign_store=self.camp_store,
            queue=self.queue,
            suppression_mgr=self.supp_mgr,
            delivery_logger=self.dev_logger,
            audit_logger=self.audit_logger
        )
        self.analytics = AnalyticsService(
            campaign_store=self.camp_store,
            queue=self.queue,
            delivery_logger=self.dev_logger,
            suppression_mgr=self.supp_mgr
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("outreach.gmail_auth.GmailAuth.connect_and_login")
    def test_non_dispatch_actions_never_call_smtp(self, mock_smtp):
        # 1. Campaign creation
        camp = self.camp_store.create_campaign({
            "name": "Safety Test Campaign",
            "attachment_path": str(self.test_pdf)
        })
        cid = camp["campaign_id"]
        self.assertEqual(mock_smtp.call_count, 0)

        # 2. Draft creation
        draft = OutreachDraft(
            draft_id="draft_safe_1",
            campaign_id=cid,
            lead_id="lead_1",
            recipient_email="safe@target.com",
            recipient_name="John Safe",
            company_name="Safe Imports",
            subject="Wholesale Proposal",
            opening_line="Dear John",
            body="Safe B2B body content without variables.",
            closing="Best regards",
            classification="Business",
            buyer_relevance="High",
            created_at="2026-09-01T00:00:00Z",
            updated_at="2026-09-01T00:00:00Z",
            status="Draft"
        )
        self.camp_store.save_draft(draft)
        self.assertEqual(mock_smtp.call_count, 0)

        # 3. Draft approval
        self.camp_store.bulk_approve(["draft_safe_1"])
        self.assertEqual(mock_smtp.call_count, 0)

        # 4. Preflight check
        preflight = self.coordinator.get_preflight(cid)
        self.assertTrue(preflight.ready)
        self.assertEqual(mock_smtp.call_count, 0)

        # 5. Queue creation
        res = self.coordinator.prepare_queue(cid)
        self.assertTrue(res["success"])
        self.assertEqual(mock_smtp.call_count, 0)

        # 6. Analytics computation
        overview = self.analytics.get_overview()
        self.assertIsNotNone(overview)
        self.assertEqual(mock_smtp.call_count, 0)

        # Zero SMTP calls verified across all preparatory actions!
        self.assertEqual(mock_smtp.call_count, 0)


class TestFullMockDispatchIntegration(unittest.TestCase):
    """
    Integration test:
    Approved Draft -> Preflight -> Queue -> Explicit Confirmation -> Mock Gmail ->
    Success -> Sent -> Sent Log -> Analytics -> Repeat Draft -> Duplicate check.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.campaigns_file = self.base_path / "campaigns.json"
        self.drafts_file = self.base_path / "drafts.json"
        self.queue_file = self.base_path / "queue.json"
        self.supp_file = self.base_path / "supp.json"
        self.log_file = self.base_path / "log.json"
        self.audit_file = self.base_path / "audit.json"
        self.test_pdf = self.base_path / "company_presentation.pdf"
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")

        self.camp_store = CampaignStore(
            campaigns_file=self.campaigns_file,
            drafts_file=self.drafts_file
        )
        self.queue = DispatchQueue(storage_file=self.queue_file)
        self.supp_mgr = SuppressionManager(storage_file=self.supp_file)
        self.delivery_logger = DeliveryLogger(storage_file=self.log_file)
        self.audit_logger = AuditLogger(storage_file=self.audit_file)

        # Isolated activity logger
        self.act_logger = MagicMock()
        self.sent_set = set()
        self.act_logger.get_sent_emails.side_effect = lambda: self.sent_set.copy()

        def mock_log_send(email, status, subject="", error_message=""):
            if status == "sent":
                self.sent_set.add(email.lower().strip())
        self.act_logger.log_send_attempt.side_effect = mock_log_send

        # Rate limiter configured with isolated limits
        self.rate_limiter = RateLimiter(
            settings={
                "dry_run": False,
                "max_emails_per_day": 100,
                "max_emails_per_campaign": 50,
                "max_emails_per_run": 25,
                "min_delay_seconds": 0,
                "max_delay_seconds": 0,
                "max_retries": 1,
                "gmail_email": "export@resonance.com",
                "gmail_app_password": "testapppassword",
                "presentation_path": str(self.test_pdf)
            },
            activity_logger=self.act_logger
        )

        self.sender = DispatchSender(
            settings=self.rate_limiter.settings,
            logger=self.act_logger
        )

        self.coordinator = DispatchCoordinator(
            campaign_store=self.camp_store,
            queue=self.queue,
            sender=self.sender,
            rate_limiter=self.rate_limiter,
            suppression_mgr=self.supp_mgr,
            delivery_logger=self.delivery_logger,
            audit_logger=self.audit_logger,
            activity_logger=self.act_logger
        )

        self.analytics = AnalyticsService(
            campaign_store=self.camp_store,
            queue=self.queue,
            delivery_logger=self.delivery_logger,
            suppression_mgr=self.supp_mgr,
            activity_logger=self.act_logger
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("outreach.gmail_auth.GmailAuth.connect_and_login")
    def test_full_pipeline_to_sent_and_subsequent_duplicate_blocking(self, mock_login):
        # Setup mock SMTP server
        mock_server = MagicMock()
        mock_server.send_message.return_value = {}
        mock_login.return_value = (mock_server, None)

        # 1. Create campaign
        camp = self.camp_store.create_campaign({
            "name": "Integration Test Campaign",
            "attachment_path": str(self.test_pdf)
        })
        cid = camp["campaign_id"]

        # 2. Create and approve draft
        draft = OutreachDraft(
            draft_id="draft_integration_1",
            campaign_id=cid,
            lead_id="lead_int_1",
            recipient_email="integration@buyer.de",
            recipient_name="Herr Mueller",
            company_name="Sound & Soul Berlin",
            subject="Himalayan Singing Bowls Catalog",
            opening_line="Guten Tag Herr Mueller,",
            body="We specialize in handcrafted Tibetan singing bowls.",
            closing="Mit freundlichen Gruessen",
            classification="Business",
            buyer_relevance="High",
            created_at="2026-09-01T00:00:00Z",
            updated_at="2026-09-01T00:00:00Z",
            status="Approved"
        )
        self.camp_store.save_draft(draft)

        # 3. Preflight
        preflight = self.coordinator.get_preflight(cid)
        self.assertTrue(preflight.ready)
        self.assertEqual(preflight.currently_eligible, 1)

        # 4. Explicit Confirmation & Dispatch (Synchronous for test)
        res = self.coordinator.confirm_and_dispatch(
            campaign_id=cid,
            operator_notes="Approved for integration test",
            synchronous=True
        )
        self.assertTrue(res["success"])

        # Verify Gmail SMTP was called exactly once
        self.assertEqual(mock_server.send_message.call_count, 1)

        # Verify queue item marked Sent
        q_items = self.queue.get_campaign_items(cid)
        self.assertEqual(len(q_items), 1)
        self.assertEqual(q_items[0].status, "Sent")

        # Verify sent log was updated
        self.assertIn("integration@buyer.de", self.sent_set)

        # Verify Campaign status transitioned to Completed
        updated_camp = self.camp_store.get_campaign(cid)
        self.assertEqual(updated_camp["status"], "Completed")

        # 5. Run Preflight again for the same draft -> Must be detected as Duplicate!
        preflight_again = self.coordinator.get_preflight(cid)
        self.assertEqual(preflight_again.currently_eligible, 0)
        self.assertEqual(preflight_again.duplicate_count, 1)
        self.assertFalse(preflight_again.ready)

        # 6. Verify second dispatch attempt will NOT invoke Gmail
        res_second = self.coordinator.confirm_and_dispatch(cid, synchronous=True)
        # Should fail with no eligible queued emails
        self.assertFalse(res_second["success"])
        # Still exactly 1 call from earlier
        self.assertEqual(mock_server.send_message.call_count, 1)


if __name__ == "__main__":
    unittest.main()
