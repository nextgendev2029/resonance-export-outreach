"""
Regression and Integration Tests for Configuration Precedence and Credential Persistence.
Verifies:
  EXPLICIT PERSISTED OPERATOR SETTING (non-empty)
          >
  ENVIRONMENT VARIABLE (non-empty)
          >
  APPLICATION DEFAULT

Ensures empty/whitespace persisted settings do not override valid environment credentials,
validates Gemini client dynamic initialization, Google provider status, credential masking,
and endpoint safety.
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from ai.gemini_client import GeminiClient
from search.providers.google_provider import GoogleSearchProvider
from web.app import get_discovery_config_status, get_settings


class TestConfigPrecedence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_settings_file = Path(self.temp_dir.name) / "settings.json"
        self.settings_patcher = patch.object(config, "SETTINGS_FILE", self.test_settings_file)
        self.settings_patcher.start()

    def tearDown(self):
        self.settings_patcher.stop()
        self.temp_dir.cleanup()

    # CASE A: Environment credential exists. Persisted credential missing.
    def test_case_a_env_credential_exists_persisted_missing(self):
        # settings.json has other settings but no gemini_api_key
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"search_keyword": "Singing Bowls"}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_env_gemini_key_12345"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_api_key"), "dummy_env_gemini_key_12345")

    # CASE B: Environment credential exists. Persisted credential is empty string.
    def test_case_b_env_credential_exists_persisted_empty(self):
        # settings.json has legacy empty string for gemini_api_key
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "", "search_keyword": "Singing Bowls"}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_env_gemini_key_12345"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_api_key"), "dummy_env_gemini_key_12345")

    # CASE C: Environment credential exists. Persisted credential is whitespace.
    def test_case_c_env_credential_exists_persisted_whitespace(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "   \t  \n  ", "search_keyword": "Singing Bowls"}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_env_gemini_key_12345"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_api_key"), "dummy_env_gemini_key_12345")

    # CASE D: Persisted credential exists. Environment credential exists.
    def test_case_d_persisted_credential_overrides_env(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "explicit_operator_key_999"}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_env_gemini_key_12345"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_api_key"), "explicit_operator_key_999")

    # CASE E: Neither exists.
    def test_case_e_neither_exists(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": ""}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_api_key"), "")
            client = GeminiClient()
            self.assertFalse(client.is_configured())
            self.assertEqual(client.get_status()["status"], "not_configured")

    # CASE F: Google API key and CSE ID environment variables exist.
    def test_case_f_google_env_vars_ready(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"google_api_key": "", "google_cse_id": ""}, f)

        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "dummy_google_api_key_abc",
            "GOOGLE_CSE_ID": "dummy_google_cse_id_xyz"
        }):
            settings = config.load_settings()
            self.assertEqual(settings.get("google_api_key"), "dummy_google_api_key_abc")
            self.assertEqual(settings.get("google_cse_id"), "dummy_google_cse_id_xyz")
            # Verify alias synchronization
            self.assertEqual(settings.get("google_cse_api_key"), "dummy_google_api_key_abc")
            self.assertEqual(settings.get("google_cse_cx"), "dummy_google_cse_id_xyz")

            provider = GoogleSearchProvider()
            health = provider.health()
            self.assertEqual(health.status, "READY")
            self.assertTrue(health.is_configured)

    # CASE G: Gemini environment variable exists.
    def test_case_g_gemini_env_vars_ready(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": ""}, f)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyDummyGeminiKey12345"}):
            client = GeminiClient()
            self.assertTrue(client.is_configured())
            status = client.get_status()
            self.assertEqual(status["status"], "ready")
            self.assertTrue(status["is_configured"])

    # CASE H: Configuration status endpoint reflects the effective configuration.
    def test_case_h_config_status_endpoint(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "", "google_api_key": "", "google_cse_id": ""}, f)

        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "AIzaSyDummyGeminiKey12345",
            "GOOGLE_API_KEY": "dummy_google_key",
            "GOOGLE_CSE_ID": "dummy_cse_id"
        }):
            status = get_discovery_config_status()
            self.assertTrue(status["gemini_api"]["configured"])
            self.assertEqual(status["gemini_api"]["status"], "READY")
            self.assertTrue(status["google_search"]["configured"])
            self.assertEqual(status["google_search"]["status"], "READY")

    # CASE I: Settings API does not expose the actual credentials.
    def test_case_i_settings_api_masks_credentials(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": ""}, f)

        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "AIzaSyDummyGeminiKey12345",
            "GOOGLE_API_KEY": "dummy_google_key_9999",
            "GOOGLE_CSE_ID": "dummy_cse_id_0000"
        }):
            res = get_settings()
            # Raw secret keys must be blanked
            self.assertEqual(res.get("gemini_api_key"), "")
            self.assertEqual(res.get("google_api_key"), "")
            self.assertEqual(res.get("google_cse_api_key"), "")
            self.assertEqual(res.get("google_cse_id"), "")

            # Masked representations must be present and obscured
            self.assertIn("••••", res.get("gemini_api_key_masked", ""))
            self.assertIn("••••", res.get("google_api_key_masked", ""))
            self.assertIn("••••", res.get("google_cse_id_masked", ""))
            self.assertNotIn("AIzaSyDummyGeminiKey12345", str(res))

    # CASE J: Dynamic module property config.settings works
    def test_case_j_config_settings_module_access(self):
        with patch.dict(os.environ, {"SEARCH_KEYWORD": "Handcrafted Bowls"}):
            self.assertEqual(config.settings.get("search_keyword"), "Handcrafted Bowls")

    # CASE K: save_settings preserves non-empty credentials and does not overwrite with blank
    def test_case_k_save_settings_preserves_non_empty(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "operator_persisted_key_123"}, f)

        # Attempt to save empty string
        config.save_settings({"gemini_api_key": "", "search_keyword": "Updated Keyword"})

        with open(self.test_settings_file, "r", encoding="utf-8") as f:
            saved = json.load(f)

        self.assertEqual(saved.get("gemini_api_key"), "operator_persisted_key_123")
        self.assertEqual(saved.get("search_keyword"), "Updated Keyword")

    # CASE L: GEMINI_MODEL environment variable configuration
    def test_case_l_gemini_model_env_var(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({}, f)
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3-flash-preview"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_model"), "gemini-3-flash-preview")
            client = GeminiClient()
            self.assertEqual(client.effective_model, "gemini-3-flash-preview")
            self.assertEqual(client.model, "gemini-3-flash-preview")

    # CASE M: Blank persisted model does NOT override environment variable or safe default
    def test_case_m_blank_persisted_model_does_not_override_env(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({"gemini_model": "   \t  "}, f)
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3-flash-preview"}):
            settings = config.load_settings()
            self.assertEqual(settings.get("gemini_model"), "gemini-3-flash-preview")

    # CASE N: Legacy model in settings.json is automatically migrated to gemini-3-flash-preview
    def test_case_n_legacy_model_migration(self):
        legacy_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-3-flash", "gemini-2.0-flash"]
        for legacy in legacy_models:
            with open(self.test_settings_file, "w", encoding="utf-8") as f:
                json.dump({"gemini_model": legacy, "search_keyword": "Singing Bowls"}, f)
            with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3-flash-preview"}):
                settings = config.load_settings()
                self.assertEqual(settings.get("gemini_model"), "gemini-3-flash-preview")
                # Ensure the persisted file was safely updated
                with open(self.test_settings_file, "r", encoding="utf-8") as f:
                    updated_file = json.load(f)
                self.assertEqual(updated_file.get("gemini_model"), "gemini-3-flash-preview")
                self.assertEqual(updated_file.get("search_keyword"), "Singing Bowls")

    # CASE O: Gemini client uses configured model and builds correct request endpoint
    @patch("requests.post")
    def test_case_o_client_uses_configured_model_in_request(self, mock_post):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": '{"result": "success"}'}]}
            }]
        }
        mock_post.return_value = mock_resp

        client = GeminiClient(api_key="AIzaSyTestKey123", model="gemini-3-flash-preview")
        self.assertEqual(client.effective_model, "gemini-3-flash-preview")
        self.assertEqual(client.model, "gemini-3-flash-preview")

        parsed, err = client.generate_json("Test prompt")
        self.assertIsNone(err)
        self.assertEqual(parsed, {"result": "success"})

        # Verify exact endpoint URL called
        call_args, call_kwargs = mock_post.call_args
        called_url = call_args[0]
        self.assertIn("/models/gemini-3-flash-preview:generateContent", called_url)

    # CASE P: Config status reports Gemini correctly without leaking secrets
    def test_case_p_config_status_reports_gemini_safely(self):
        with open(self.test_settings_file, "w", encoding="utf-8") as f:
            json.dump({}, f)
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "AIzaSySecretNeverExposeMe",
            "GEMINI_MODEL": "gemini-3-flash-preview"
        }):
            status = get_discovery_config_status()
            gemini_status = status.get("gemini_api", {})
            self.assertTrue(gemini_status.get("configured"))
            self.assertEqual(gemini_status.get("status"), "READY")
            self.assertEqual(gemini_status.get("model"), "gemini-3-flash-preview")
            self.assertEqual(gemini_status.get("model_display"), "Gemini 3 Flash")
            # Verify secret is not in status
            self.assertNotIn("AIzaSySecretNeverExposeMe", str(status))

    # CASE Q: HTTP 404 is NOT silently treated as success and produces informative error
    @patch("requests.post")
    def test_case_q_404_not_silently_treated_as_success(self, mock_post):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = '{"error": {"code": 404, "message": "models/gemini-1.5-flash is not found"}}'
        mock_post.return_value = mock_resp

        client = GeminiClient(api_key="AIzaSyTestKey123", model="gemini-1.5-flash")
        parsed, err = client.generate_json("Test prompt")
        self.assertIsNone(parsed)
        self.assertIsNotNone(err)
        self.assertIn("404", err)
        self.assertIn("not found or unsupported", err.lower())


if __name__ == "__main__":
    unittest.main()
