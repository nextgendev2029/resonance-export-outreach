"""
Central configuration for Resonance - Export Outreach & Lead Operations.
Target Product: Singing Bowls (Export Goods)
"""

import os
import json
from pathlib import Path
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
ASSETS_DIR = BASE_DIR / "assets"

# Ensure data and assets directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Settings JSON path
SETTINGS_FILE = DATA_DIR / "settings.json"
DISCOVERY_RUNS_FILE = DATA_DIR / "discovery_runs.json"
ENRICHMENT_RUNS_FILE = DATA_DIR / "enrichment_runs.json"
LEAD_ENRICHMENT_FILE = DATA_DIR / "lead_enrichment.json"
CAMPAIGNS_FILE = DATA_DIR / "campaigns.json"
OUTREACH_DRAFTS_FILE = DATA_DIR / "outreach_drafts.json"
DISPATCH_QUEUE_FILE = DATA_DIR / "dispatch_queue.json"
DISPATCH_LOG_FILE = DATA_DIR / "dispatch_log.json"
SUPPRESSION_LIST_FILE = DATA_DIR / "suppression_list.json"
AUDIT_LOG_FILE = DATA_DIR / "audit_log.json"

# CSV Data Files
BUYERS_CSV = DATA_DIR / "buyers.csv"
BUSINESS_EMAILS_CSV = DATA_DIR / "business_emails.csv"
INDIVIDUAL_EMAILS_CSV = DATA_DIR / "individual_emails.csv"
SENT_LOG_CSV = DATA_DIR / "sent_log.csv"

# Presentation Attachment Path
DEFAULT_PRESENTATION_PATH = ASSETS_DIR / "company_presentation.pdf"
PRESENTATION_PATH = DEFAULT_PRESENTATION_PATH

# Gemini Model Defaults and Legacy Migration Identifiers
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
LEGACY_GEMINI_MODELS = {
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-3-flash",  # missing -preview suffix
    "gemini 3 flash",
    "gemini-pro"
}

# Default configuration dictionary (static baseline defaults)
DEFAULT_SETTINGS = {
    "app_name": "Resonance",
    "app_subtitle": "Export Outreach & Lead Operations",
    "gmail_email": "",
    "gmail_app_password": "",
    "monitoring_cc_email": "",
    "search_keyword": "Singing Bowls",
    "default_qualifiers": [
        "wholesale",
        "distributor",
        "importer",
        "sound healing",
        "meditation",
        "yoga studio",
        "musical instruments",
        "supplier"
    ],
    "daily_send_limit": 100,
    "send_delay_seconds": 5,
    "dry_run": True,
    "max_emails_per_day": 100,
    "max_emails_per_campaign": 50,
    "max_emails_per_run": 25,
    "min_delay_seconds": 3,
    "max_delay_seconds": 8,
    "max_retries": 2,
    "test_recipient_email": "",
    "presentation_path": str(DEFAULT_PRESENTATION_PATH),
    "gemini_api_key": "",
    "gemini_model": DEFAULT_GEMINI_MODEL,
    "classification_batch_size": 20,
    "google_cse_api_key": "",
    "google_cse_cx": "",
    "google_api_key": "",
    "google_cse_id": "",
    "facebook_access_token": "",
    "linkedin_access_token": "",
    "default_seller_profile": {
        "product_name": "Singing Bowls",
        "product_category": "Home Decor",
        "product_description": "Handcrafted singing bowls suitable for home decor, wellness spaces, meditation stores and lifestyle retailers.",
        "target_country": "United States",
        "target_state": "",
        "buyer_types": [
            "Importer",
            "Distributor",
            "Wholesaler",
            "Retailer",
            "Home Decor Store",
            "Gift Shop",
            "Wellness Store",
            "Interior Decor Business",
            "Lifestyle Store",
            "Boutique Store",
            "B2B Buyer",
            "Specialty Store"
        ]
    },
    "default_subject": "Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog & Export Pricing",
    "default_body": """Dear {{buyer_name}},

I hope this message finds you well.

We are specialized Himalayan artisans and direct exporters of authentic hand-hammered Singing Bowls, meditation gongs, and sound-healing instruments.

We noticed {{company_name}}'s focus on quality holistic wellness and musical instruments. We would love to share our latest Export Catalog and direct manufacturer wholesale price list with your procurement team.

Please find our complete company presentation and export specifications attached.

Key B2B Offerings:
• Authentic 7-metal hand-hammered singing bowls (graded Frequencies & Hz)
• Custom engraving and OEM private labeling for international distributors
• Direct worldwide door-to-door export shipping with full export documentation

Would you be open to reviewing our wholesale price sheet this week?

Warm regards,

Export Operations Team
Himalayan Singing Bowls Exporters
export@himalayanbowls.org | www.himalayanbowls.org
"""
}

# SMTP Constants
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT_STARTTLS = 587
SMTP_PORT_SSL = 465

# Normalized Buyer Schema Headers (including operational metadata)
BUYER_COLUMNS = [
    "lead_id",
    "email",
    "buyer_name",
    "company_name",
    "website",
    "country",
    "source_platform",
    "source_url",
    "validation_status",
    "classification",
    "outreach_status",
    "discovered_date",
    "discovery_run_id",
    "is_demo",
    "notes"
]

SENT_LOG_COLUMNS = [
    "email",
    "status",
    "timestamp",
    "campaign_subject",
    "error_message"
]


# Environment variable fallbacks for specific configuration keys
ENV_FALLBACKS = {
    "gemini_api_key": ("GEMINI_API_KEY",),
    "gemini_model": ("GEMINI_MODEL",),
    "classification_batch_size": ("CLASSIFICATION_BATCH_SIZE",),
    "google_api_key": ("GOOGLE_API_KEY", "GOOGLE_CSE_API_KEY"),
    "google_cse_api_key": ("GOOGLE_API_KEY", "GOOGLE_CSE_API_KEY"),
    "google_cse_id": ("GOOGLE_CSE_ID", "GOOGLE_CSE_CX"),
    "google_cse_cx": ("GOOGLE_CSE_ID", "GOOGLE_CSE_CX"),
    "facebook_access_token": ("FACEBOOK_ACCESS_TOKEN",),
    "linkedin_access_token": ("LINKEDIN_ACCESS_TOKEN",),
    "gmail_email": ("GMAIL_EMAIL",),
    "gmail_app_password": ("GMAIL_APP_PASSWORD",),
    "monitoring_cc_email": ("MONITORING_CC_EMAIL",),
    "search_keyword": ("SEARCH_KEYWORD",),
    "daily_send_limit": ("DAILY_SEND_LIMIT",),
    "send_delay_seconds": ("SEND_DELAY_SECONDS",),
    "dry_run": ("DRY_RUN",),
    "max_emails_per_day": ("MAX_EMAILS_PER_DAY",),
    "max_emails_per_campaign": ("MAX_EMAILS_PER_CAMPAIGN",),
    "max_emails_per_run": ("MAX_EMAILS_PER_RUN",),
    "min_delay_seconds": ("MIN_DELAY_SECONDS",),
    "max_delay_seconds": ("MAX_DELAY_SECONDS",),
    "max_retries": ("MAX_RETRIES",),
    "test_recipient_email": ("TEST_RECIPIENT_EMAIL",),
    "presentation_path": ("PRESENTATION_PATH",),
}


def get_env_setting(key: str) -> Optional[Any]:
    """Retrieve non-empty environment setting for a key if present in os.environ."""
    env_names = ENV_FALLBACKS.get(key, ())
    for env_name in env_names:
        raw = os.getenv(env_name)
        if raw is not None:
            raw_str = str(raw).strip()
            if raw_str:
                if key in (
                    "daily_send_limit", "send_delay_seconds", "max_emails_per_day",
                    "max_emails_per_campaign", "max_emails_per_run", "min_delay_seconds",
                    "max_delay_seconds", "max_retries", "classification_batch_size"
                ):
                    try:
                        return int(raw_str)
                    except ValueError:
                        return None
                elif key == "dry_run":
                    return raw_str.lower() in ("true", "1", "yes")
                return raw_str
    return None


def load_settings() -> dict:
    """
    Load effective settings with strict precedence:
      EXPLICIT PERSISTED OPERATOR SETTING (non-empty)
              >
      ENVIRONMENT VARIABLE (non-empty)
              >
      APPLICATION DEFAULT

    Empty or whitespace persisted credentials never override valid environment variables.
    """
    persisted = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    persisted = loaded
        except Exception:
            persisted = {}

    effective = {}

    # 1. Start with application defaults
    for k, default_val in DEFAULT_SETTINGS.items():
        effective[k] = default_val

    # 2. Layer in environment variables (dynamic from os.environ)
    for k in DEFAULT_SETTINGS.keys():
        env_val = get_env_setting(k)
        if env_val is not None:
            effective[k] = env_val

    persisted_migrated = False
    migrated_persisted = dict(persisted)

    # 3. Layer in persisted settings from settings.json
    # A persisted value overrides environment ONLY if non-empty
    for k, p_val in persisted.items():
        if p_val is not None:
            if isinstance(p_val, str):
                trimmed = p_val.strip()
                if trimmed:
                    if k == "gemini_model":
                        lower_m = trimmed.lower()
                        if lower_m in LEGACY_GEMINI_MODELS or lower_m.startswith("gemini-1.") or lower_m == "gemini-3-flash":
                            # Migrate legacy or malformed model string to Gemini 3 Flash standard
                            migrated_val = get_env_setting("gemini_model") or DEFAULT_GEMINI_MODEL
                            effective[k] = migrated_val
                            migrated_persisted[k] = migrated_val
                            persisted_migrated = True
                        else:
                            effective[k] = trimmed
                    else:
                        effective[k] = trimmed
                # If p_val is empty or whitespace, do NOT overwrite;
                # the environment variable (or default) remains active.
            else:
                effective[k] = p_val

    # Safely migrate legacy persisted configuration without losing other keys
    if persisted_migrated and SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(migrated_persisted, f, indent=2)
        except Exception:
            pass

    # 4. Synchronize aliases
    google_key = effective.get("google_api_key") or effective.get("google_cse_api_key") or ""
    if google_key:
        effective["google_api_key"] = google_key
        effective["google_cse_api_key"] = google_key

    google_cx = effective.get("google_cse_id") or effective.get("google_cse_cx") or ""
    if google_cx:
        effective["google_cse_id"] = google_cx
        effective["google_cse_cx"] = google_cx

    return effective


def save_settings(new_settings: dict) -> dict:
    """Save updated settings to settings.json and return effective configuration."""
    current = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    current = loaded
        except Exception:
            current = {}

    # Do not persist empty string credentials over existing valid settings
    for k, v in new_settings.items():
        if isinstance(v, str):
            trimmed_v = v.strip()
            if not trimmed_v and k in ENV_FALLBACKS:
                # If the user did not supply a new credential, keep whatever was already saved
                continue
            if k == "gemini_model":
                if not trimmed_v:
                    # An empty persisted model must NOT override env; remove from persisted
                    current.pop(k, None)
                    continue
                lower_v = trimmed_v.lower()
                if lower_v in LEGACY_GEMINI_MODELS or lower_v.startswith("gemini-1.") or lower_v == "gemini-3-flash":
                    current[k] = DEFAULT_GEMINI_MODEL
                    continue
                current[k] = trimmed_v
                continue
            current[k] = trimmed_v
        else:
            current[k] = v

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return load_settings()


def __getattr__(name: str):
    """Support config.settings module-level access dynamically."""
    if name == "settings":
        return load_settings()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

