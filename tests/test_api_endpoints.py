"""
Resonance API Endpoints Integration Test Suite (Phase 2 & Phase 3).
Verifies REST API endpoints, discovery engine, and the AI Lead Intelligence & Enrichment layer.
"""

import sys
import unittest
import requests

BASE_URL = "http://127.0.0.1:8000"


class TestResonanceAPIEndpoints(unittest.TestCase):
    def test_health_and_root_branding(self):
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Resonance", resp.text)
        self.assertNotIn("API 3 - EXPORT Automation System", resp.text)

    def test_stats_endpoint_includes_real_and_demo(self):
        resp = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_leads", data)
        self.assertIn("real_leads_count", data)
        self.assertIn("demo_leads_count", data)
        self.assertIn("valid_emails", data)
        self.assertGreaterEqual(data["total_leads"], 1)

    def test_leads_endpoint_and_filtering(self):
        # All leads
        resp = requests.get(f"{BASE_URL}/api/leads", timeout=5)
        self.assertEqual(resp.status_code, 200)
        all_leads = resp.json()
        self.assertIsInstance(all_leads, list)

        # Real discovered leads only
        resp_real = requests.get(f"{BASE_URL}/api/leads?data_type=real", timeout=5)
        self.assertEqual(resp_real.status_code, 200)
        real_leads = resp_real.json()
        for r in real_leads:
            self.assertEqual(str(r.get("is_demo", "")).lower(), "false")

        # Demo leads only
        resp_demo = requests.get(f"{BASE_URL}/api/leads?data_type=demo", timeout=5)
        self.assertEqual(resp_demo.status_code, 200)
        demo_leads = resp_demo.json()
        for d in demo_leads:
            self.assertEqual(str(d.get("is_demo", "")).lower(), "true")

    def test_lead_detail_and_patch(self):
        resp = requests.get(f"{BASE_URL}/api/leads", timeout=5)
        leads = resp.json()
        self.assertGreaterEqual(len(leads), 1)
        target_lead = leads[0]
        lead_id = target_lead["lead_id"]

        # GET detail
        resp_detail = requests.get(f"{BASE_URL}/api/leads/{lead_id}", timeout=5)
        self.assertEqual(resp_detail.status_code, 200)
        detail_data = resp_detail.json()
        self.assertEqual(detail_data["lead_id"], lead_id)

        # PATCH update notes
        test_note = "Integration test verification note"
        resp_patch = requests.patch(
            f"{BASE_URL}/api/leads/{lead_id}",
            json={"notes": test_note},
            timeout=5
        )
        self.assertEqual(resp_patch.status_code, 200)
        patch_res = resp_patch.json()
        self.assertEqual(patch_res["status"], "success")
        self.assertEqual(patch_res["updated_lead"]["notes"], test_note)

    def test_discovery_config_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/discovery/config", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("default_keyword"), "Singing Bowls")
        self.assertIn("wholesale", data.get("default_qualifiers", []))
        self.assertIn("sources_health", data)

    def test_discovery_runs_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/discovery/runs", timeout=5)
        self.assertEqual(resp.status_code, 200)
        runs = resp.json()
        self.assertIsInstance(runs, list)

    def test_discovery_status_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/discovery/status", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("is_running", data)

    def test_settings_endpoint_masks_credentials(self):
        resp = requests.get(f"{BASE_URL}/api/settings", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("search_keyword"), "Singing Bowls")
        self.assertIn("ai_status", data)
        self.assertEqual(data["ai_status"]["model"], "gemini-3-flash-preview")
        # Ensure raw secret keys are NEVER exposed in response
        self.assertEqual(data.get("gemini_api_key", ""), "")
        self.assertEqual(data.get("gmail_app_password", ""), "")

    def test_download_report_stream(self):
        resp = requests.get(f"{BASE_URL}/download-report", timeout=5)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type", ""))
        self.assertIn("lead_id,email,buyer_name", resp.text)

    # ---------------------------------------------------------
    # Phase 3 Lead Intelligence API Tests
    # ---------------------------------------------------------
    def test_intelligence_stats_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/stats", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_real_leads", data)
        self.assertIn("total_enriched", data)
        self.assertIn("needs_enrichment", data)
        self.assertIn("relevance_distribution", data)
        self.assertIn("ai_status", data)
        self.assertIn("High", data["relevance_distribution"])
        self.assertIn("Unknown", data["relevance_distribution"])

    def test_intelligence_leads_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/intelligence/leads?dataset=real", timeout=5)
        self.assertEqual(resp.status_code, 200)
        leads = resp.json()
        self.assertIsInstance(leads, list)
        for l in leads:
            self.assertEqual(str(l.get("is_demo", "")).lower(), "false")
            self.assertIn("enrichment_status", l)
            self.assertIn("buyer_relevance", l)

    def test_intelligence_lead_detail_and_enrich_single(self):
        resp = requests.get(f"{BASE_URL}/api/leads", timeout=5)
        leads = resp.json()
        self.assertGreaterEqual(len(leads), 1)
        lead_id = leads[0]["lead_id"]

        # Detail endpoint
        resp_detail = requests.get(f"{BASE_URL}/api/intelligence/leads/{lead_id}", timeout=5)
        self.assertEqual(resp_detail.status_code, 200)
        detail = resp_detail.json()
        self.assertEqual(detail["lead_id"], lead_id)
        self.assertIn("enrichment", detail)

        # Single lead enrichment endpoint
        resp_enrich = requests.post(f"{BASE_URL}/api/intelligence/leads/{lead_id}/enrich", timeout=10)
        self.assertEqual(resp_enrich.status_code, 200)
        res_data = resp_enrich.json()
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["lead_id"], lead_id)
        self.assertIn("enrichment", res_data)

    def test_intelligence_runs_and_status(self):
        resp_runs = requests.get(f"{BASE_URL}/api/intelligence/runs", timeout=5)
        self.assertEqual(resp_runs.status_code, 200)
        self.assertIsInstance(resp_runs.json(), list)

        resp_status = requests.get(f"{BASE_URL}/api/intelligence/status", timeout=5)
        self.assertEqual(resp_status.status_code, 200)
        status_data = resp_status.json()
        self.assertIn("is_running", status_data)

    def test_intelligence_classify_action(self):
        resp = requests.post(
            f"{BASE_URL}/api/intelligence/classify",
            json={"force_all": False, "allow_demo": False},
            timeout=10
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("business_count", data)
        self.assertIn("individual_count", data)

    def test_campaign_attachment_info_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/campaigns/attachment-info", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("valid"))
        self.assertTrue(data.get("ready"))
        self.assertEqual(data.get("status_label"), "Attachment ready")

    def test_campaign_audience_preview_endpoint(self):
        resp = requests.post(
            f"{BASE_URL}/api/campaigns/preview-audience",
            json={"dataset": "all", "classification": ["Business"], "validation_status": ["Valid"]},
            timeout=5
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_evaluated", data)
        self.assertIn("eligible_count", data)
        self.assertIn("excluded_count", data)
        self.assertIn("exclusion_reasons", data)

    def test_campaign_lifecycle_and_draft_approval_endpoints(self):
        # 1. Create campaign
        create_resp = requests.post(
            f"{BASE_URL}/api/campaigns",
            json={"name": "API Test Campaign", "audience_filters": {"dataset": "all", "classification": ["Business"]}},
            timeout=5
        )
        self.assertEqual(create_resp.status_code, 200)
        camp = create_resp.json()
        cid = camp["campaign_id"]

        try:
            # 2. Get campaign
            get_resp = requests.get(f"{BASE_URL}/api/campaigns/{cid}", timeout=5)
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(get_resp.json()["name"], "API Test Campaign")

            # 3. Preview audience for this campaign
            prev_resp = requests.post(f"{BASE_URL}/api/campaigns/{cid}/audience/preview", timeout=5)
            self.assertEqual(prev_resp.status_code, 200)

            # 4. Update campaign
            patch_resp = requests.patch(
                f"{BASE_URL}/api/campaigns/{cid}",
                json={"subject_template": "Updated Subject for {{company_name}}"},
                timeout=5
            )
            self.assertEqual(patch_resp.status_code, 200)
            self.assertIn("Updated Subject", patch_resp.json()["subject_template"])
        finally:
            # Cleanup campaign
            del_resp = requests.delete(f"{BASE_URL}/api/campaigns/{cid}", timeout=5)
            self.assertEqual(del_resp.status_code, 200)

    def test_ai_health_and_config_status_endpoints(self):
        # 1. Config status returns Gemini 3 Flash model ID safely
        cfg_resp = requests.get(f"{BASE_URL}/api/discovery/config/status", timeout=5)
        self.assertEqual(cfg_resp.status_code, 200)
        data = cfg_resp.json()
        self.assertIn("gemini_api", data)
        self.assertEqual(data["gemini_api"]["model"], "gemini-3-flash-preview")
        self.assertEqual(data["gemini_api"]["model_display"], "Gemini 3 Flash")
        # Ensure no secrets in output
        self.assertNotIn("password", str(data).lower().replace("app_password", ""))

        # 2. AI Health endpoint
        health_resp = requests.get(f"{BASE_URL}/api/ai/health", timeout=15)
        self.assertEqual(health_resp.status_code, 200)
        health_data = health_resp.json()
        self.assertIn("status", health_data)
        self.assertEqual(health_data["model"], "gemini-3-flash-preview")
        self.assertIn(health_data["status"], ["READY", "NOT CONFIGURED"])


if __name__ == "__main__":
    unittest.main()

