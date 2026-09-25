"""
Web Backend & API Server for Resonance - Export Outreach & Lead Operations.
Provides REST endpoints and serves the modern B2B frontend interface.
"""

import os
import csv
import io
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import Response, FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from config import BASE_DIR, load_settings, save_settings
from app_logging.activity_logger import ActivityLogger
from search.discovery_engine import DiscoveryEngine
from search.models import DiscoveryProfile, ProviderHealth, NormalizedBuyerLead
from classification.ai_classifier import AIClassifier
from outreach.gmail_sender import GmailSender
from outreach.attachment_handler import AttachmentHandler
from reports.report_generator import ReportGenerator

# AI Lead Intelligence & Enrichment Services
from ai.gemini_client import GeminiClient
from ai.classifier import LeadClassifier
from ai.enricher import LeadEnricher

# Campaigns, Audience & Outreach Queue Services (Phase 4)
from campaigns.models import AudienceFilters, CampaignRecord, OutreachDraft
from campaigns.audience import AudienceSelector
from campaigns.draft_validator import DraftValidator
from campaigns.personalization import PersonalizationEngine
from campaigns.campaign_store import CampaignStore

# Controlled Dispatch Engine, Telemetry & Analytics Services (Phase 5)
from dispatch.dispatcher import DispatchCoordinator
from dispatch.analytics import AnalyticsService
from dispatch.suppression import SuppressionManager
from dispatch.queue import DispatchQueue
from dispatch.models import (
    DispatchConfirmPayload,
    TestSendPayload,
    SuppressionCreatePayload
)

app = FastAPI(
    title="Resonance - Export Outreach & Lead Operations",
    description="Operational Sales & Lead Discovery Platform for US Home Decor & Export Goods",
    version="2.0.0"
)

# Environment-driven CORS configuration (Part 17)
cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if cors_env:
    allowed_origins = [orig.strip() for orig in cors_env.split(",") if orig.strip()]
    for dev_orig in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"]:
        if dev_orig not in allowed_origins:
            allowed_origins.append(dev_orig)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

logger = ActivityLogger()
report_gen = ReportGenerator(logger)
discovery_engine = DiscoveryEngine(logger)
gemini_client = GeminiClient()
lead_classifier = LeadClassifier(gemini_client)
lead_enricher = LeadEnricher(gemini_client)
campaign_store = CampaignStore()
audience_selector = AudienceSelector()
personalization_engine = PersonalizationEngine(gemini_client)
dispatch_coordinator = DispatchCoordinator(campaign_store=campaign_store)
analytics_service = AnalyticsService(campaign_store=campaign_store)
suppression_manager = SuppressionManager()
dispatch_queue = DispatchQueue()

# Shared In-Memory Operation State for background jobs
pipeline_state = {
    "discovery": {
        "is_running": False,
        "progress": 0,
        "status_message": "Idle",
        "current_source": "",
        "last_discovered_count": 0,
        "discovered_leads": []
    },
    "intelligence": {
        "is_running": False,
        "progress": 0,
        "status_message": "Idle",
        "current_lead": "",
        "enriched_count": 0,
        "failed_count": 0,
        "skipped_count": 0
    },
    "classification": {
        "is_running": False,
        "progress": 0,
        "status_message": "Idle",
        "business_count": 0,
        "individual_count": 0
    },
    "campaign": {
        "is_running": False,
        "progress": 0,
        "current_recipient": "",
        "status_message": "Idle",
        "sent_count": 0,
        "failed_count": 0,
        "total_queued": 0,
        "demo_suppressed": 0,
        "logs": []
    },
    "campaign_generation": {
        "is_running": False,
        "campaign_id": None,
        "progress": 0,
        "status_message": "Idle",
        "current_lead": "",
        "generated_count": 0,
        "failed_count": 0,
        "total_targets": 0
    }
}


# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class SettingsPayload(BaseModel):
    gmail_email: Optional[str] = None
    gmail_app_password: Optional[str] = None
    monitoring_cc_email: Optional[str] = None
    search_keyword: Optional[str] = None
    default_qualifiers: Optional[List[str]] = None
    daily_send_limit: Optional[int] = None
    send_delay_seconds: Optional[int] = None
    presentation_path: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    classification_batch_size: Optional[int] = None
    google_cse_api_key: Optional[str] = None
    google_cse_cx: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    facebook_access_token: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    default_subject: Optional[str] = None
    default_body: Optional[str] = None
    # Phase 5 Dispatch Controls
    dry_run: Optional[bool] = None
    max_emails_per_day: Optional[int] = None
    max_emails_per_campaign: Optional[int] = None
    max_emails_per_run: Optional[int] = None
    min_delay_seconds: Optional[int] = None
    max_delay_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    test_recipient_email: Optional[str] = None


class DiscoveryRequest(BaseModel):
    keyword: Optional[str] = "Singing Bowls"
    qualifiers: Optional[List[str]] = None
    sources: Optional[List[str]] = ["google", "facebook", "linkedin", "directory", "website"]
    max_per_source: Optional[int] = 5
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    product_description: Optional[str] = None
    target_country: Optional[str] = None
    target_state: Optional[str] = None
    buyer_types: Optional[List[str]] = None


class SearchBuyersPayload(BaseModel):
    product_name: Optional[str] = "Singing Bowls"
    product_category: Optional[str] = "Home Decor"
    product_description: Optional[str] = None
    target_country: Optional[str] = "United States"
    target_state: Optional[str] = ""
    buyer_types: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    max_per_source: Optional[int] = 5


class ClassifyRequest(BaseModel):
    batch_size: Optional[int] = 20
    force_all: Optional[bool] = False


class CampaignRequest(BaseModel):
    audience: Optional[str] = "business"  # 'business', 'individual', 'all'
    subject: Optional[str] = None
    body: Optional[str] = None


class LeadPatchRequest(BaseModel):
    validation_status: Optional[str] = None
    classification: Optional[str] = None
    notes: Optional[str] = None
    company_name: Optional[str] = None
    buyer_name: Optional[str] = None
    country: Optional[str] = None


class IntelligenceRunRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    force_refresh: Optional[bool] = False
    allow_demo: Optional[bool] = False


class ClassifyActionRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    force_all: Optional[bool] = False
    allow_demo: Optional[bool] = False


class CreateCampaignRequest(BaseModel):
    name: str
    audience_filters: Optional[Dict[str, Any]] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    attachment_path: Optional[str] = None
    reply_to: Optional[str] = None
    sender_identity: Optional[str] = None


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    audience_filters: Optional[Dict[str, Any]] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    attachment_path: Optional[str] = None
    reply_to: Optional[str] = None
    sender_identity: Optional[str] = None
    status: Optional[str] = None


class AudiencePreviewRequest(BaseModel):
    dataset: Optional[str] = "real"
    classification: Optional[List[str]] = ["Business"]
    validation_status: Optional[List[str]] = ["Valid"]
    buyer_relevance: Optional[List[str]] = ["High", "Medium"]
    country: Optional[str] = None
    source_platform: Optional[str] = None
    enrichment_status: Optional[str] = None
    outreach_status: Optional[str] = None
    contacted_status: Optional[str] = "never"


class GenerateDraftsRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    force_regenerate: Optional[bool] = False


class UpdateDraftRequest(BaseModel):
    subject: Optional[str] = None
    opening_line: Optional[str] = None
    body: Optional[str] = None
    closing: Optional[str] = None
    status: Optional[str] = None


class RejectDraftRequest(BaseModel):
    reason: Optional[str] = "Unspecified"


class BulkDraftActionRequest(BaseModel):
    draft_ids: List[str]
    reason: Optional[str] = "Bulk action"


# -------------------------------------------------------------
# Background Task Runners
# -------------------------------------------------------------
def run_campaign_generation_task(campaign_id: str, lead_ids: Optional[List[str]], force_regenerate: bool):
    import time
    pipeline_state["campaign_generation"]["is_running"] = True
    pipeline_state["campaign_generation"]["campaign_id"] = campaign_id
    pipeline_state["campaign_generation"]["progress"] = 5
    pipeline_state["campaign_generation"]["status_message"] = "Initializing draft generation..."
    pipeline_state["campaign_generation"]["generated_count"] = 0
    pipeline_state["campaign_generation"]["failed_count"] = 0
    pipeline_state["campaign_generation"]["total_targets"] = 0

    try:
        camp = campaign_store.get_campaign(campaign_id)
        if not camp:
            pipeline_state["campaign_generation"]["status_message"] = "Campaign not found."
            return

        all_buyers = logger.get_all_buyers()
        filters = AudienceFilters(**(camp.get("audience_filters") or {}))

        if lead_ids:
            targets = [b for b in all_buyers if b.get("lead_id") in lead_ids]
        else:
            preview = audience_selector.evaluate_all(all_buyers, filters)
            target_ids = set(preview.eligible_lead_ids)
            targets = [b for b in all_buyers if b.get("lead_id") in target_ids]

        if not force_regenerate:
            existing_drafts = campaign_store.list_drafts(campaign_id)
            existing_lead_ids = set(d.get("lead_id") for d in existing_drafts)
            targets = [t for t in targets if t.get("lead_id") not in existing_lead_ids]

        total = len(targets)
        pipeline_state["campaign_generation"]["total_targets"] = total

        if total == 0:
            pipeline_state["campaign_generation"]["progress"] = 100
            pipeline_state["campaign_generation"]["status_message"] = "All eligible leads already have drafts."
            campaign_store.recalculate_campaign_stats(campaign_id)
            return

        campaign_store.update_campaign(campaign_id, {"status": "Generating Drafts"})

        for i, lead in enumerate(targets):
            email = lead.get("email") or "prospect"
            company = lead.get("company_name") or "Company"
            pipeline_state["campaign_generation"]["current_lead"] = f"{company} ({email})"
            pipeline_state["campaign_generation"]["status_message"] = f"Personalizing ({i+1}/{total}): {company}"
            pipeline_state["campaign_generation"]["progress"] = int(((i) / total) * 100)

            try:
                draft = personalization_engine.generate_draft(
                    lead=lead,
                    campaign_id=campaign_id,
                    subject_template=camp.get("subject_template"),
                    body_template=camp.get("body_template")
                )
                campaign_store.save_draft(draft)
                pipeline_state["campaign_generation"]["generated_count"] += 1
            except Exception as e:
                pipeline_state["campaign_generation"]["failed_count"] += 1

            pipeline_state["campaign_generation"]["progress"] = int(((i + 1) / total) * 100)
            time.sleep(0.05)

        campaign_store.recalculate_campaign_stats(campaign_id)
        gen = pipeline_state["campaign_generation"]["generated_count"]
        fail = pipeline_state["campaign_generation"]["failed_count"]
        pipeline_state["campaign_generation"]["status_message"] = (
            f"Draft generation complete: {gen} drafts generated, {fail} errors."
        )
    except Exception as e:
        pipeline_state["campaign_generation"]["status_message"] = f"Generation error: {str(e)}"
    finally:
        pipeline_state["campaign_generation"]["is_running"] = False
def run_intelligence_task(lead_ids: Optional[List[str]], force_refresh: bool, allow_demo: bool):
    pipeline_state["intelligence"]["is_running"] = True
    pipeline_state["intelligence"]["progress"] = 5
    pipeline_state["intelligence"]["status_message"] = "Initializing intelligence batch..."
    pipeline_state["intelligence"]["enriched_count"] = 0
    pipeline_state["intelligence"]["failed_count"] = 0
    pipeline_state["intelligence"]["skipped_count"] = 0

    try:
        all_buyers = logger.get_all_buyers()
        if lead_ids:
            targets = [b for b in all_buyers if b.get("lead_id") in lead_ids]
        else:
            # By default only process real leads
            targets = [b for b in all_buyers if str(b.get("is_demo", "")).lower() != "true"]
            if not force_refresh:
                targets = [b for b in targets if b.get("enrichment_status") != "enriched"]

        if not targets:
            pipeline_state["intelligence"]["progress"] = 100
            pipeline_state["intelligence"]["status_message"] = "No eligible leads requiring enrichment."
            return

        def on_prog(idx, count, email, status):
            prog = int((idx / count) * 100) if count > 0 else 100
            pipeline_state["intelligence"]["progress"] = prog
            pipeline_state["intelligence"]["current_lead"] = email or "Prospect Web"
            pipeline_state["intelligence"]["status_message"] = f"Enriching ({idx}/{count}): {email or 'Company Domain'}"
            if status == "enriched":
                pipeline_state["intelligence"]["enriched_count"] += 1
            elif status in ("failed", "blocked"):
                pipeline_state["intelligence"]["failed_count"] += 1
            else:
                pipeline_state["intelligence"]["skipped_count"] += 1

        run_res = lead_enricher.enrich_batch(
            targets,
            force_refresh=force_refresh,
            allow_demo=allow_demo,
            progress_callback=on_prog
        )

        pipeline_state["intelligence"]["progress"] = 100
        pipeline_state["intelligence"]["status_message"] = (
            f"Enrichment completed: {run_res.successful_count} enriched, "
            f"{run_res.failed_count} failed/blocked, {run_res.skipped_count} skipped."
        )
    except Exception as e:
        pipeline_state["intelligence"]["status_message"] = f"Enrichment run encountered an error: {str(e)}"
    finally:
        pipeline_state["intelligence"]["is_running"] = False
def run_discovery_task(
    keyword: str,
    qualifiers: List[str],
    sources: List[str],
    max_results: int,
    profile: Optional[DiscoveryProfile] = None
):
    pipeline_state["discovery"]["is_running"] = True
    pipeline_state["discovery"]["progress"] = 5
    display_name = profile.product_name if profile else keyword
    pipeline_state["discovery"]["status_message"] = f"Initializing discovery for '{display_name}' in United States..."
    pipeline_state["discovery"]["current_source"] = ""
    pipeline_state["discovery"]["discovered_leads"] = []

    def on_progress(current_source: str, progress_pct: int, status_message: str):
        pipeline_state["discovery"]["current_source"] = current_source
        pipeline_state["discovery"]["progress"] = progress_pct
        pipeline_state["discovery"]["status_message"] = status_message

    try:
        if profile is not None:
            res = discovery_engine.search_buyers(
                profile=profile,
                enabled_sources=sources,
                max_results_per_source=max_results,
                progress_callback=on_progress
            )
        else:
            res = discovery_engine.execute_discovery(
                keyword=keyword,
                qualifiers=qualifiers,
                enabled_sources=sources,
                max_results_per_source=max_results,
                progress_callback=on_progress
            )
        pipeline_state["discovery"]["discovered_leads"] = res.get("discovered_leads", [])
        pipeline_state["discovery"]["last_discovered_count"] = res.get("extracted_lead_count", 0)
        pipeline_state["discovery"]["progress"] = 100
        pipeline_state["discovery"]["status_message"] = (
            f"Discovery complete in {res.get('duration_seconds')}s: "
            f"Extracted {res.get('extracted_lead_count')}, {res.get('new_leads_added')} new leads saved."
        )
    except Exception as e:
        pipeline_state["discovery"]["status_message"] = f"Discovery run failed: {str(e)}"
    finally:
        pipeline_state["discovery"]["is_running"] = False


def run_classification_task(batch_size: int, force_all: bool):
    pipeline_state["classification"]["is_running"] = True
    pipeline_state["classification"]["progress"] = 10
    pipeline_state["classification"]["status_message"] = "Preparing records for classification..."

    try:
        all_buyers = logger.get_all_buyers()
        if force_all:
            target = all_buyers
        else:
            target = [b for b in all_buyers if b.get("classification") in ("Unclassified", "", None)]

        if not target:
            pipeline_state["classification"]["progress"] = 100
            pipeline_state["classification"]["status_message"] = "All records are already classified."
            return

        classifier = AIClassifier(batch_size=batch_size)
        pipeline_state["classification"]["status_message"] = f"Classifying {len(target)} contacts..."
        bus, ind = classifier.classify_records(target)
        logger.save_classified_emails(bus, ind)

        pipeline_state["classification"]["business_count"] = len(bus)
        pipeline_state["classification"]["individual_count"] = len(ind)
        pipeline_state["classification"]["progress"] = 100
        pipeline_state["classification"]["status_message"] = f"Classification finished: {len(bus)} Business, {len(ind)} Individual."

    finally:
        pipeline_state["classification"]["is_running"] = False


def run_campaign_task(audience: str, subject: str, body: str):
    pipeline_state["campaign"]["is_running"] = True
    pipeline_state["campaign"]["progress"] = 5
    pipeline_state["campaign"]["status_message"] = f"Queuing audience '{audience}'..."
    pipeline_state["campaign"]["logs"] = []

    sender = GmailSender(logger)

    def on_progress(idx, total, email, status):
        prog = int((idx / total) * 100) if total > 0 else 100
        pipeline_state["campaign"]["progress"] = prog
        pipeline_state["campaign"]["current_recipient"] = email
        pipeline_state["campaign"]["status_message"] = f"Sending ({idx}/{total}) to {email}..."
        pipeline_state["campaign"]["logs"].append({
            "email": email,
            "status": status,
            "step": f"{idx}/{total}"
        })

    try:
        res = sender.send_campaign(
            audience=audience,
            subject=subject,
            body=body,
            progress_callback=on_progress
        )
        pipeline_state["campaign"]["sent_count"] = res.get("success_count", 0)
        pipeline_state["campaign"]["failed_count"] = res.get("failed_count", 0)
        pipeline_state["campaign"]["total_queued"] = res.get("total_queued", 0)
        pipeline_state["campaign"]["demo_suppressed"] = res.get("demo_suppressed", 0)
        pipeline_state["campaign"]["progress"] = 100
        
        msg = f"Campaign complete: {res.get('success_count', 0)} sent, {res.get('failed_count', 0)} failed, {res.get('duplicates_skipped', 0)} duplicates skipped."
        if res.get("demo_suppressed", 0) > 0:
            msg += f" ({res.get('demo_suppressed')} demo contacts safely suppressed)."
        if res.get("error"):
            msg += f" (Notice: {res.get('error')})"
        pipeline_state["campaign"]["status_message"] = msg

    finally:
        pipeline_state["campaign"]["is_running"] = False


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.get("/api/stats")
def get_stats():
    """Operational metrics overview distinguishing real vs demo leads."""
    return logger.get_summary_statistics()


@app.get("/api/leads")
def get_leads(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    data_type: Optional[str] = Query("all")  # 'all', 'real', 'demo'
):
    """Retrieve all buyer leads with filtering and search."""
    buyers = logger.get_all_buyers()
    filtered = buyers

    # Data type filter (real vs demo)
    if data_type and data_type.lower() == "real":
        filtered = [b for b in filtered if str(b.get("is_demo", "")).lower() != "true"]
    elif data_type and data_type.lower() == "demo":
        filtered = [b for b in filtered if str(b.get("is_demo", "")).lower() == "true"]

    if search:
        s = search.lower().strip()
        filtered = [
            b for b in filtered
            if s in b.get("email", "").lower()
            or s in b.get("buyer_name", "").lower()
            or s in b.get("company_name", "").lower()
            or s in b.get("website", "").lower()
            or s in b.get("country", "").lower()
            or s in b.get("notes", "").lower()
        ]

    if status and status.lower() != "all":
        # Handle 'malformed' mapping to 'invalid'
        target_status = "invalid" if status.lower() == "malformed" else status.lower()
        filtered = [b for b in filtered if b.get("validation_status", "").lower() == target_status]

    if classification and classification.lower() != "all":
        filtered = [b for b in filtered if b.get("classification", "").lower() == classification.lower()]

    if source and source.lower() != "all":
        filtered = [b for b in filtered if b.get("source_platform", "").lower() == source.lower()]

    # Return newest first
    return list(reversed(filtered))


@app.get("/api/leads/{identifier}")
def get_lead_detail(identifier: str):
    """Retrieve single lead detail by lead_id or email."""
    lead = logger.get_lead_by_id_or_email(identifier)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead record not found")
    return lead


@app.patch("/api/leads/{identifier}")
def update_lead_detail(identifier: str, payload: LeadPatchRequest):
    """Update lead fields (notes, validation status, classification, name, company)."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No update fields supplied")

    success = logger.update_lead(identifier, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Lead record not found")
    return {"status": "success", "message": "Lead updated successfully", "updated_lead": logger.get_lead_by_id_or_email(identifier)}


@app.delete("/api/leads/{identifier}")
def delete_lead(identifier: str):
    """Remove a lead record from buyers.csv."""
    success = logger.delete_lead(identifier)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "message": f"Removed lead {identifier}"}


@app.post("/api/leads/upload")
async def upload_leads_csv(file: UploadFile = File(...)):
    """Upload CSV file containing leads and ingest into buyers.csv (marked as real leads)."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except Exception:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    records = []
    for row in reader:
        email = (
            row.get("email") or row.get("email_address") or row.get("Email") or row.get("Contact Email") or ""
        ).strip()
        company = (row.get("company_name") or row.get("Company") or row.get("Organization") or "").strip()

        # If neither email nor company exists, skip
        if not email and not company:
            continue

        records.append({
            "email": email,
            "buyer_name": row.get("buyer_name") or row.get("Name") or row.get("Contact") or "",
            "company_name": company or "Imported Prospect",
            "website": row.get("website") or row.get("Website") or row.get("URL") or "",
            "country": row.get("country") or row.get("Country") or "International",
            "source_platform": row.get("source_platform") or row.get("Source") or "CSV Upload",
            "source_url": row.get("source_url") or "",
            "is_demo": "false",
            "discovery_run_id": f"upload_{file.filename[:15]}"
        })

    ingest_res = logger.append_buyers_detailed(records)
    added = ingest_res["newly_added"]
    skipped = ingest_res["duplicates_skipped"]

    return {
        "total_parsed": len(records),
        "newly_added": added,
        "duplicates_skipped": skipped,
        "message": f"Successfully processed {len(records)} records ({added} newly added, {skipped} duplicates skipped)."
    }


# -------------------------------------------------------------
# Discovery API Endpoints (Phase 6 US Home Decor & API Hardening)
# -------------------------------------------------------------
@app.get("/api/discovery/config")
def get_discovery_config():
    """Get active discovery configuration, default seller profile, and source health statuses."""
    settings = load_settings()
    health_list = discovery_engine.orchestrator.registry.get_all_health()
    default_profile = settings.get("default_seller_profile", {
        "product_name": "Singing Bowls",
        "product_category": "Home Decor",
        "product_description": "Handcrafted singing bowls suitable for home decor, wellness spaces, meditation stores and lifestyle retailers.",
        "target_country": "United States",
        "target_state": "",
        "buyer_types": [
            "Importer", "Distributor", "Wholesaler", "Retailer",
            "Home Decor Store", "Gift Shop", "Wellness Store",
            "Interior Decor Business", "Lifestyle Store", "Boutique Store",
            "B2B Buyer", "Specialty Store"
        ]
    })
    return {
        "default_keyword": settings.get("search_keyword", "Singing Bowls"),
        "default_qualifiers": settings.get("default_qualifiers", [
            "wholesale", "distributor", "importer", "sound healing", "meditation", "yoga studio", "supplier"
        ]),
        "default_profile": default_profile,
        "sources_health": [h.dict() for h in health_list]
    }


@app.get("/api/discovery/providers")
def list_discovery_providers():
    """List all registered discovery providers with configuration & operational readiness."""
    health_list = discovery_engine.orchestrator.registry.get_all_health()
    return [h.model_dump() if hasattr(h, "model_dump") else h.dict() for h in health_list]


@app.get("/api/discovery/providers/{provider_id}/health")
def get_provider_health_detail(provider_id: str):
    """Retrieve detailed health check for a single discovery provider."""
    health = discovery_engine.orchestrator.registry.get_provider_health(provider_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    return health.model_dump() if hasattr(health, "model_dump") else health.dict()


@app.post("/api/discovery/search")
def search_buyers_api(payload: SearchBuyersPayload):
    """
    Execute multi-source buyer discovery with seller profile parameters.
    Returns structured results, queries, US matches, and summary.
    """
    settings = load_settings()
    default_profile_cfg = settings.get("default_seller_profile", {})

    profile = DiscoveryProfile(
        product_name=payload.product_name or default_profile_cfg.get("product_name", "Singing Bowls"),
        product_category=payload.product_category or default_profile_cfg.get("product_category", "Home Decor"),
        product_description=payload.product_description or default_profile_cfg.get("product_description", ""),
        target_country=payload.target_country or default_profile_cfg.get("target_country", "United States"),
        target_state=payload.target_state or "",
        buyer_types=payload.buyer_types or default_profile_cfg.get("buyer_types", [
            "Importer", "Distributor", "Wholesaler", "Retailer", "Home Decor Store", "Gift Shop"
        ]),
        keywords=payload.keywords or []
    )

    sources = payload.sources or ["google", "directory", "website"]
    max_results = payload.max_per_source or 5

    res = discovery_engine.search_buyers(
        profile=profile,
        enabled_sources=sources,
        max_results_per_source=max_results
    )

    return {
        "run_id": res["run_id"],
        "status": "completed",
        "providers": list(res.get("sources_status", {}).keys()),
        "queries": res.get("queries", []),
        "results": res.get("discovered_leads", []),
        "summary": {
            "raw_count": res.get("raw_result_count", 0),
            "extracted_count": res.get("extracted_lead_count", 0),
            "us_match_count": res.get("us_match_count", 0),
            "valid_email_count": res.get("valid_email_count", 0),
            "duplicate_count": res.get("duplicate_count", 0),
            "new_leads_added": res.get("new_leads_added", 0),
            "duration_seconds": res.get("duration_seconds", 0.0),
            "errors": res.get("errors", [])
        }
    }


@app.get("/api/discovery/stats")
def get_discovery_stats():
    """Aggregate statistics across all historical discovery runs."""
    runs = discovery_engine.get_run_history()
    total_runs = len(runs)
    total_raw = sum(r.get("raw_result_count", 0) for r in runs)
    total_extracted = sum(r.get("extracted_lead_count", 0) for r in runs)
    total_us = sum(r.get("us_match_count", 0) for r in runs)
    total_valid_emails = sum(r.get("valid_email_count", 0) for r in runs)
    total_duplicates = sum(r.get("duplicate_count", 0) for r in runs)
    total_new_leads = sum(r.get("new_leads_added", 0) for r in runs)

    providers = discovery_engine.orchestrator.registry.get_all_health()
    configured_count = sum(1 for p in providers if p.is_configured)

    return {
        "total_runs": total_runs,
        "total_raw_prospects": total_raw,
        "total_leads_extracted": total_extracted,
        "total_us_matches": total_us,
        "total_valid_emails": total_valid_emails,
        "total_duplicates_skipped": total_duplicates,
        "total_new_leads_added": total_new_leads,
        "total_providers": len(providers),
        "configured_providers": configured_count
    }


@app.get("/api/discovery/config/status")
def get_discovery_config_status():
    """Return safe configuration status for all external APIs without leaking secrets."""
    settings = load_settings()
    has_google = bool(
        (settings.get("google_api_key") or settings.get("google_cse_api_key"))
        and (settings.get("google_cse_id") or settings.get("google_cse_cx"))
    )
    has_gemini = bool(settings.get("gemini_api_key"))
    has_gmail = bool(settings.get("gmail_email") and settings.get("gmail_app_password"))
    has_fb = bool(settings.get("facebook_access_token"))
    has_li = bool(settings.get("linkedin_access_token"))

    return {
        "google_search": {
            "name": "Google Custom Search API",
            "configured": has_google,
            "status": "READY" if has_google else "NOT CONFIGURED",
            "required_credentials": ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"],
            "description": "Enables Google Search API with US geographic restriction."
        },
        "directory_search": {
            "name": "US B2B Trade Directory",
            "configured": True,
            "status": "READY",
            "required_credentials": [],
            "description": "Built-in index of US trade registries and wholesale directories."
        },
        "website_crawler": {
            "name": "Direct Website Contact Crawler",
            "configured": True,
            "status": "READY",
            "required_credentials": [],
            "description": "Crawls US showroom & boutique websites for direct contact emails."
        },
        "facebook_api": {
            "name": "Meta Graph API (Facebook)",
            "configured": has_fb,
            "status": "READY" if has_fb else "NOT CONFIGURED",
            "required_credentials": ["FACEBOOK_ACCESS_TOKEN"],
            "description": "Requires official Meta Graph API developer token for page search."
        },
        "linkedin_api": {
            "name": "LinkedIn Organization API",
            "configured": has_li,
            "status": "READY" if has_li else "NOT CONFIGURED",
            "required_credentials": ["LINKEDIN_ACCESS_TOKEN"],
            "description": "Requires official LinkedIn Marketing Developer credentials."
        },
        "gemini_api": {
            "name": "Google Gemini AI",
            "configured": has_gemini,
            "status": "READY" if has_gemini else "NOT CONFIGURED",
            "model": gemini_client.effective_model,
            "model_display": "Gemini 3 Flash",
            "required_credentials": ["GEMINI_API_KEY"],
            "description": "Enables AI B2B classification, grounding audit, and personalized drafting."
        },
        "gmail_smtp": {
            "name": "Gmail SMTP Outreach",
            "configured": has_gmail,
            "status": "READY" if has_gmail else "NOT CONFIGURED",
            "required_credentials": ["GMAIL_EMAIL", "GMAIL_APP_PASSWORD"],
            "description": "Enables controlled email dispatch to approved campaign recipients."
        }
    }


@app.post("/api/discovery/run")
def start_discovery(payload: DiscoveryRequest, background_tasks: BackgroundTasks):
    """Trigger buyer search discovery across configured sources."""
    if pipeline_state["discovery"]["is_running"]:
        raise HTTPException(status_code=409, detail="Discovery task already in progress.")

    settings = load_settings()
    keyword = payload.keyword or settings.get("search_keyword", "Singing Bowls")
    qualifiers = payload.qualifiers if payload.qualifiers is not None else settings.get("default_qualifiers", [])
    sources = payload.sources or ["google", "facebook", "linkedin", "directory", "website"]

    # Construct profile if seller inputs supplied
    profile = None
    if payload.product_name or payload.buyer_types:
        profile = DiscoveryProfile(
            product_name=payload.product_name or keyword,
            product_category=payload.product_category or "Home Decor",
            product_description=payload.product_description or "",
            target_country=payload.target_country or "United States",
            target_state=payload.target_state or "",
            buyer_types=payload.buyer_types or qualifiers
        )

    background_tasks.add_task(
        run_discovery_task,
        keyword=keyword,
        qualifiers=qualifiers,
        sources=sources,
        max_results=payload.max_per_source or 5,
        profile=profile
    )
    return {"status": "started", "message": f"Discovery pipeline initiated for '{keyword}'."}


@app.get("/api/discovery/status")
def get_discovery_status():
    """Poll discovery task status."""
    return pipeline_state["discovery"]


@app.get("/api/discovery/runs")
def list_discovery_runs():
    """Retrieve history of all discovery runs."""
    return discovery_engine.get_run_history()


@app.get("/api/discovery/runs/{run_id}")
def get_discovery_run_detail(run_id: str):
    """Retrieve details of a specific discovery run."""
    run = discovery_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return run


# -------------------------------------------------------------
# Lead Intelligence & Enrichment API Endpoints
# -------------------------------------------------------------
@app.get("/api/intelligence/stats")
def get_intelligence_stats():
    """Aggregated intelligence metrics, relevance distribution, and AI configuration status."""
    buyers = logger.get_all_buyers()
    real_leads = [b for b in buyers if str(b.get("is_demo", "")).lower() != "true"]
    demo_leads = [b for b in buyers if str(b.get("is_demo", "")).lower() == "true"]

    enriched = [b for b in real_leads if b.get("enrichment_status") == "enriched"]
    needs_enrichment = [b for b in real_leads if b.get("enrichment_status") != "enriched"]

    rel_counts = {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    for b in real_leads:
        r = b.get("buyer_relevance") or "Unknown"
        rel_counts[r] = rel_counts.get(r, 0) + 1

    runs = lead_enricher.load_enrichment_runs()
    last_run = runs[0] if runs else None

    return {
        "total_real_leads": len(real_leads),
        "total_demo_leads": len(demo_leads),
        "total_enriched": len(enriched),
        "needs_enrichment": len(needs_enrichment),
        "relevance_distribution": rel_counts,
        "ai_status": gemini_client.get_status(),
        "last_run": last_run
    }


@app.get("/api/intelligence/leads")
def get_intelligence_leads(
    dataset: Optional[str] = Query("real"),  # 'all', 'real', 'demo'
    status: Optional[str] = Query(None),     # 'needs_enrichment', 'enriched', 'failed', 'blocked'
    classification: Optional[str] = Query(None),
    relevance: Optional[str] = Query(None),   # 'High', 'Medium', 'Low', 'Unknown'
    search: Optional[str] = Query(None)
):
    """Retrieve leads table with intelligence and enrichment parameters."""
    buyers = logger.get_all_buyers()
    filtered = buyers

    if dataset == "real":
        filtered = [b for b in filtered if str(b.get("is_demo", "")).lower() != "true"]
    elif dataset == "demo":
        filtered = [b for b in filtered if str(b.get("is_demo", "")).lower() == "true"]

    if status and status != "all":
        filtered = [b for b in filtered if b.get("enrichment_status", "").lower() == status.lower()]

    if classification and classification != "all":
        filtered = [b for b in filtered if b.get("classification", "").lower() == classification.lower()]

    if relevance and relevance != "all":
        filtered = [b for b in filtered if b.get("buyer_relevance", "").lower() == relevance.lower()]

    if search:
        s = search.lower().strip()
        filtered = [
            b for b in filtered
            if s in b.get("company_name", "").lower()
            or s in b.get("buyer_name", "").lower()
            or s in b.get("email", "").lower()
            or s in b.get("website", "").lower()
            or s in b.get("country", "").lower()
        ]

    return filtered


@app.get("/api/intelligence/leads/{lead_id}")
def get_intelligence_lead_detail(lead_id: str):
    """Retrieve complete intelligence profile for a single lead."""
    lead = logger.get_lead_by_id_or_email(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    enr = lead_enricher.get_enrichment_by_lead_id(lead.get("lead_id", ""))
    lead["enrichment"] = enr
    return lead


@app.post("/api/intelligence/leads/{lead_id}/enrich")
def enrich_single_lead_endpoint(lead_id: str):
    """Enrich a single lead immediately with forced refresh."""
    lead = logger.get_lead_by_id_or_email(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    is_demo = str(lead.get("is_demo", "")).lower() == "true"
    record = lead_enricher.enrich_lead(lead, force_refresh=True, allow_demo=is_demo)

    # Sync back classification if improved
    if record.classification and record.classification.classification != "Unclassified":
        logger.update_lead(lead["lead_id"], {"classification": record.classification.classification})

    return {
        "status": "success",
        "lead_id": lead_id,
        "enrichment": record.to_dict()
    }


@app.post("/api/intelligence/run")
def start_intelligence_run(payload: IntelligenceRunRequest, background_tasks: BackgroundTasks):
    """Trigger background batch intelligence and enrichment run."""
    if pipeline_state["intelligence"]["is_running"]:
        raise HTTPException(status_code=409, detail="Lead enrichment run already in progress.")

    background_tasks.add_task(
        run_intelligence_task,
        lead_ids=payload.lead_ids,
        force_refresh=payload.force_refresh or False,
        allow_demo=payload.allow_demo or False
    )
    return {"status": "started", "message": "Lead enrichment pipeline initiated."}


@app.get("/api/intelligence/status")
def get_intelligence_status():
    """Poll lead intelligence run progress."""
    return pipeline_state["intelligence"]


@app.get("/api/intelligence/runs")
def list_intelligence_runs():
    """Retrieve history of enrichment runs."""
    return lead_enricher.load_enrichment_runs()


@app.get("/api/intelligence/runs/{run_id}")
def get_intelligence_run_detail(run_id: str):
    """Retrieve details of a specific enrichment run."""
    runs = lead_enricher.load_enrichment_runs()
    for r in runs:
        if r.get("run_id") == run_id:
            return r
    raise HTTPException(status_code=404, detail="Enrichment run not found")


@app.post("/api/intelligence/classify")
def run_classification_action(payload: ClassifyActionRequest):
    """Classify unclassified leads or reclassify selected contacts."""
    all_buyers = logger.get_all_buyers()
    if payload.lead_ids:
        targets = [b for b in all_buyers if b.get("lead_id") in payload.lead_ids]
    elif payload.force_all:
        targets = all_buyers
    else:
        targets = [b for b in all_buyers if b.get("classification") in ("Unclassified", "", None)]

    # Strictly protect demo leads unless requested
    if not payload.allow_demo:
        targets = [b for b in targets if str(b.get("is_demo", "")).lower() != "true"]

    if not targets:
        return {
            "status": "skipped",
            "message": "No eligible leads found for classification.",
            "total_processed": 0,
            "business_count": 0,
            "individual_count": 0,
            "unclassified_count": 0
        }

    classified_results = lead_classifier.classify_batch(targets)
    business_count = 0
    individual_count = 0
    unclassified_count = 0

    for item in classified_results:
        lid = item.get("lead_id")
        c = item.get("classification", "Unclassified")
        if c == "Business":
            business_count += 1
        elif c == "Individual":
            individual_count += 1
        else:
            unclassified_count += 1

        logger.update_lead(lid, {
            "classification": c,
            "notes": f"AI Classified as {c} ({int(item.get('classification_confidence', 0.5)*100)}% conf). {item.get('classification_reason', '')}"[:250]
        })

    return {
        "status": "success",
        "total_processed": len(classified_results),
        "business_count": business_count,
        "individual_count": individual_count,
        "unclassified_count": unclassified_count
    }


# -------------------------------------------------------------
# Classification API Endpoints
# -------------------------------------------------------------
@app.post("/api/classify/run")
def start_classification(payload: ClassifyRequest, background_tasks: BackgroundTasks):
    """Trigger AI contact classification."""
    if pipeline_state["classification"]["is_running"]:
        raise HTTPException(status_code=409, detail="Classification already in progress.")

    background_tasks.add_task(
        run_classification_task,
        batch_size=payload.batch_size or 20,
        force_all=payload.force_all or False
    )
    return {"status": "started", "message": "AI Classification initiated."}


@app.get("/api/classify/status")
def get_classify_status():
    """Poll classification progress."""
    return pipeline_state["classification"]


# -------------------------------------------------------------
# Campaigns & Outreach Endpoints
# -------------------------------------------------------------
@app.post("/api/campaign/send")
def start_campaign(payload: CampaignRequest, background_tasks: BackgroundTasks):
    """Launch Gmail outreach campaign with demo safety suppression."""
    if pipeline_state["campaign"]["is_running"]:
        raise HTTPException(status_code=409, detail="Campaign dispatch currently running.")

    settings = load_settings()
    subject = payload.subject or settings.get("default_subject")
    body = payload.body or settings.get("default_body")

    background_tasks.add_task(
        run_campaign_task,
        audience=payload.audience or "business",
        subject=subject,
        body=body
    )
    return {"status": "started", "message": "Campaign outreach initiated."}


@app.get("/api/campaign/status")
def get_campaign_status():
    """Poll campaign progress and delivery logs."""
    return pipeline_state["campaign"]


# -------------------------------------------------------------
# Reports Endpoints
# -------------------------------------------------------------
@app.get("/api/reports")
def get_reports():
    """Campaign reports, delivery history, and analytics."""
    return report_gen.generate_summary()


@app.get("/download-report")
def download_report_csv():
    """Stream report as downloadable CSV file."""
    csv_data = report_gen.generate_csv_report()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=singing_bowls_export_report.csv"
        }
    )


# -------------------------------------------------------------
# Settings Endpoints
# -------------------------------------------------------------
@app.get("/api/settings")
def get_settings():
    """Fetch current system configuration with credentials safely masked."""
    s = load_settings()
    masked = s.copy()

    # Never return raw secrets
    pwd = masked.get("gmail_app_password", "")
    masked["gmail_app_password"] = ""
    masked["gmail_app_password_masked"] = "••••••••••••••••" if pwd else ""

    key = masked.get("gemini_api_key", "")
    masked["gemini_api_key"] = ""
    masked["gemini_api_key_masked"] = key[:4] + "••••••••" + key[-4:] if len(key) > 8 else ("••••••••" if key else "")

    cse_key = masked.get("google_api_key", "") or masked.get("google_cse_api_key", "")
    masked["google_api_key"] = ""
    masked["google_cse_api_key"] = ""
    masked["google_api_key_masked"] = cse_key[:4] + "••••••••" + cse_key[-4:] if len(cse_key) > 8 else ("••••••••" if cse_key else "")

    cse_id = masked.get("google_cse_id", "") or masked.get("google_cse_cx", "")
    masked["google_cse_id"] = ""
    masked["google_cse_cx"] = ""
    masked["google_cse_id_masked"] = cse_id[:4] + "••••••••" if len(cse_id) > 6 else ("••••••••" if cse_id else "")

    fb_tok = masked.get("facebook_access_token", "")
    masked["facebook_access_token"] = ""
    masked["facebook_access_token_masked"] = fb_tok[:4] + "••••••••" if fb_tok else ""

    li_tok = masked.get("linkedin_access_token", "")
    masked["linkedin_access_token"] = ""
    masked["linkedin_access_token_masked"] = li_tok[:4] + "••••••••" if li_tok else ""

    pres_path = masked.get("presentation_path", "")
    masked["presentation_exists"] = AttachmentHandler.validate_file(pres_path)
    masked["ai_status"] = gemini_client.get_status()
    # Phase 5 Safety Protections checklist
    masked["safety_protections"] = [
        {"name": "Demo Data Isolation", "status": "Active", "description": "is_demo records permanently blocked from SMTP"},
        {"name": "Dual-Key Duplicate Prevention", "status": "Active", "description": "sent_log.csv verification before every send"},
        {"name": "Suppression List Enforcement", "status": "Active", "description": "Persistent opt-out and bounce filtering"},
        {"name": "Deterministic Preflight Checks", "status": "Active", "description": "15-point pre-dispatch validation verification"},
        {"name": "Mandatory Human Confirmation", "status": "Active", "description": "Explicit operator confirmation required"}
    ]
    return masked


@app.put("/api/settings")
def update_settings(payload: SettingsPayload):
    """Update settings and reinitialize AI client configuration."""
    updates = {}
    payload_dict = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    for k, v in payload_dict.items():
        if v is not None:
            # Skip empty passwords if user did not type a new one
            if k in ("gmail_app_password", "gemini_api_key", "google_cse_api_key", "google_api_key", "google_cse_id", "google_cse_cx", "facebook_access_token", "linkedin_access_token") and isinstance(v, str) and v.strip() == "":
                continue
            updates[k] = v

    saved = save_settings(updates)
    # Refresh live clients
    new_settings = load_settings()
    gemini_client._api_key = new_settings.get("gemini_api_key", "").strip()
    gemini_client.model = new_settings.get("gemini_model", "gemini-3-flash-preview").strip()
    return {"status": "success", "message": "Settings saved successfully."}


@app.get("/api/ai/health")
def get_ai_health():
    """Verify live Gemini connectivity and model availability without exposing secrets."""
    return gemini_client.check_health()


# -------------------------------------------------------------
# Campaign Intelligence & Outreach Queue Endpoints (Phase 4)
# -------------------------------------------------------------
@app.get("/api/campaigns")
def list_campaigns():
    """List all campaigns with summary counts."""
    return campaign_store.list_campaigns()


@app.post("/api/campaigns")
def create_campaign(payload: CreateCampaignRequest):
    """Create a new outreach campaign."""
    camp = campaign_store.create_campaign(payload.model_dump())
    return camp


@app.get("/api/campaigns/attachment-info")
def get_attachment_info():
    """Verify company presentation attachment metadata."""
    from config import DEFAULT_PRESENTATION_PATH
    p = DEFAULT_PRESENTATION_PATH
    valid = AttachmentHandler.validate_file(str(p))
    size_kb = round(p.stat().st_size / 1024, 1) if p.exists() else 0.0
    return {
        "filename": p.name if p.exists() else "company_presentation.pdf",
        "path": str(p),
        "size_kb": size_kb,
        "valid": valid,
        "ready": valid,
        "status_label": "Attachment ready" if valid else "File missing or invalid"
    }


@app.post("/api/campaigns/preview-audience")
def preview_audience(payload: AudiencePreviewRequest):
    """Preview audience eligibility and exclusion breakdown for configured filters."""
    all_buyers = logger.get_all_buyers()
    filters = AudienceFilters(**payload.model_dump())
    preview = audience_selector.evaluate_all(all_buyers, filters)
    return preview.model_dump()


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    """Get single campaign details and audience breakdown."""
    camp = campaign_store.get_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp


@app.patch("/api/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, payload: UpdateCampaignRequest):
    """Update campaign configuration."""
    updated = campaign_store.update_campaign(campaign_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return updated


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str):
    """Delete campaign and associated drafts."""
    success = campaign_store.delete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"status": "success", "message": "Campaign and drafts deleted successfully"}


@app.post("/api/campaigns/{campaign_id}/audience/preview")
def preview_campaign_audience(campaign_id: str, payload: Optional[AudiencePreviewRequest] = None):
    """Preview audience eligibility using the campaign's saved or override filters."""
    camp = campaign_store.get_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    filters_dict = camp.get("audience_filters") or {}
    if payload:
        filters_dict.update(payload.model_dump(exclude_unset=True))

    all_buyers = logger.get_all_buyers()
    filters = AudienceFilters(**filters_dict)
    preview = audience_selector.evaluate_all(all_buyers, filters)

    # Update campaign record with latest counts
    campaign_store.update_campaign(campaign_id, {
        "eligible_count": preview.eligible_count,
        "excluded_count": preview.excluded_count
    })
    return preview.model_dump()


@app.post("/api/campaigns/{campaign_id}/generate")
def generate_campaign_drafts(
    campaign_id: str,
    payload: GenerateDraftsRequest,
    background_tasks: BackgroundTasks
):
    """Trigger background draft generation for eligible prospects."""
    camp = campaign_store.get_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if pipeline_state["campaign_generation"]["is_running"]:
        return {
            "status": "busy",
            "message": "A draft generation job is already running."
        }

    background_tasks.add_task(
        run_campaign_generation_task,
        campaign_id=campaign_id,
        lead_ids=payload.lead_ids,
        force_regenerate=payload.force_regenerate or False
    )
    return {
        "status": "started",
        "message": f"Draft generation initiated for campaign '{camp.get('name')}'."
    }


@app.get("/api/campaigns/{campaign_id}/status")
def get_campaign_generation_status(campaign_id: str):
    """Get active draft generation status and progress."""
    state = pipeline_state["campaign_generation"].copy()
    if state["campaign_id"] and state["campaign_id"] != campaign_id:
        return {
            "is_running": False,
            "progress": 0,
            "status_message": "Idle",
            "current_lead": "",
            "generated_count": 0,
            "failed_count": 0,
            "total_targets": 0
        }
    return state


@app.get("/api/campaigns/{campaign_id}/drafts")
def list_campaign_drafts(
    campaign_id: str,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List drafts in the review queue for a campaign."""
    camp = campaign_store.get_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign_store.list_drafts(campaign_id, status_filter=status, search=search)


@app.get("/api/campaigns/{campaign_id}/drafts/{draft_id}")
def get_campaign_draft(campaign_id: str, draft_id: str):
    """Get full details of a specific draft."""
    draft = campaign_store.get_draft(draft_id)
    if not draft or draft.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.patch("/api/campaigns/{campaign_id}/drafts/{draft_id}")
def update_campaign_draft(campaign_id: str, draft_id: str, payload: UpdateDraftRequest):
    """Operator edit of draft text or status. Preserves original AI draft."""
    draft = campaign_store.get_draft(draft_id)
    if not draft or draft.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    updated = campaign_store.update_draft(draft_id, payload.model_dump(exclude_unset=True))
    return updated


@app.post("/api/campaigns/{campaign_id}/drafts/{draft_id}/approve")
def approve_campaign_draft(campaign_id: str, draft_id: str):
    """
    Operator approves a draft for future dispatch.
    CRITICAL ARCHITECTURAL SAFETY: DOES NOT SEND LIVE EMAILS.
    """
    draft = campaign_store.get_draft(draft_id)
    if not draft or draft.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    approved = campaign_store.approve_draft(draft_id)
    return {
        "status": "success",
        "message": "Draft approved for future dispatch.",
        "draft": approved
    }


@app.post("/api/campaigns/{campaign_id}/drafts/{draft_id}/reject")
def reject_campaign_draft(campaign_id: str, draft_id: str, payload: RejectDraftRequest):
    """Operator rejects a draft with reason."""
    draft = campaign_store.get_draft(draft_id)
    if not draft or draft.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    rejected = campaign_store.reject_draft(draft_id, reason=payload.reason or "Unspecified")
    return {
        "status": "success",
        "message": "Draft rejected.",
        "draft": rejected
    }


@app.post("/api/campaigns/{campaign_id}/drafts/{draft_id}/regenerate")
def regenerate_campaign_draft(campaign_id: str, draft_id: str):
    """Regenerate a draft using AI/heuristics, preserving history."""
    draft = campaign_store.get_draft(draft_id)
    if not draft or draft.get("campaign_id") != campaign_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    camp = campaign_store.get_campaign(campaign_id)
    lead = logger.get_lead_by_id_or_email(draft.get("lead_id"))
    if not lead:
        # Fallback to draft recipient info
        lead = {
            "lead_id": draft.get("lead_id"),
            "email": draft.get("recipient_email"),
            "company_name": draft.get("company_name"),
            "buyer_name": draft.get("recipient_name"),
            "country": draft.get("country"),
            "classification": draft.get("classification"),
            "buyer_relevance": draft.get("buyer_relevance"),
            "is_demo": draft.get("is_demo")
        }

    new_draft = personalization_engine.generate_draft(
        lead=lead,
        campaign_id=campaign_id,
        subject_template=camp.get("subject_template") if camp else None,
        body_template=camp.get("body_template") if camp else None
    )

    regen = campaign_store.record_regeneration(
        draft_id=draft_id,
        new_subject=new_draft.subject,
        new_opening=new_draft.opening_line,
        new_body=new_draft.body,
        new_closing=new_draft.closing,
        new_confidence=new_draft.ai_confidence,
        reason=new_draft.personalization_reason or "Regenerated draft"
    )
    return {
        "status": "success",
        "message": "Draft regenerated successfully.",
        "draft": regen
    }


@app.post("/api/campaigns/{campaign_id}/drafts/bulk-approve")
def bulk_approve_campaign_drafts(campaign_id: str, payload: BulkDraftActionRequest):
    """Bulk approve selected drafts without sending."""
    count = campaign_store.bulk_approve(payload.draft_ids)
    return {
        "status": "success",
        "approved_count": count,
        "message": f"Successfully approved {count} drafts for future dispatch."
    }


@app.post("/api/campaigns/{campaign_id}/drafts/bulk-reject")
def bulk_reject_campaign_drafts(campaign_id: str, payload: BulkDraftActionRequest):
    """Bulk reject selected drafts with reason."""
    count = campaign_store.bulk_reject(payload.draft_ids, reason=payload.reason or "Bulk rejection")
    return {
        "status": "success",
        "rejected_count": count,
        "message": f"Successfully rejected {count} drafts."
    }


@app.post("/api/campaigns/{campaign_id}/drafts/bulk-archive")
def bulk_archive_campaign_drafts(campaign_id: str, payload: BulkDraftActionRequest):
    """Bulk archive selected drafts."""
    count = campaign_store.bulk_archive(payload.draft_ids)
    return {
        "status": "success",
        "archived_count": count,
        "message": f"Successfully archived {count} drafts."
    }


# -------------------------------------------------------------
# Dispatch Operations (Phase 5)
# -------------------------------------------------------------
@app.get("/api/campaigns/{campaign_id}/dispatch/preflight")
def get_campaign_preflight(campaign_id: str):
    """Deterministic final eligibility evaluation across all drafts for a campaign."""
    report = dispatch_coordinator.get_preflight(campaign_id)
    return report.model_dump()


@app.post("/api/campaigns/{campaign_id}/dispatch/queue")
def prepare_campaign_queue(campaign_id: str):
    """Enqueues approved, eligible drafts into the persistent dispatch queue."""
    res = dispatch_coordinator.prepare_queue(campaign_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.get("/api/campaigns/{campaign_id}/dispatch/status")
def get_campaign_dispatch_status(campaign_id: str):
    """Retrieve operational queue status, counts, and active worker state."""
    res = dispatch_coordinator.get_dispatch_status(campaign_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@app.post("/api/campaigns/{campaign_id}/dispatch/confirm")
def confirm_campaign_dispatch(campaign_id: str, payload: DispatchConfirmPayload):
    """
    CRITICAL OPERATOR CONFIRMATION ACTION.
    Requires explicit confirmation to initiate bounded dispatch.
    """
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Explicit operator confirmation is required.")
    res = dispatch_coordinator.confirm_and_dispatch(campaign_id, operator_notes=payload.operator_notes or "")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.post("/api/campaigns/{campaign_id}/dispatch/pause")
def pause_campaign_dispatch(campaign_id: str):
    """Pause an active or queued campaign dispatch."""
    res = dispatch_coordinator.pause_dispatch(campaign_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.post("/api/campaigns/{campaign_id}/dispatch/cancel")
def cancel_campaign_dispatch(campaign_id: str):
    """Cancel remaining unsent items in a campaign dispatch."""
    res = dispatch_coordinator.cancel_dispatch(campaign_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@app.get("/api/dispatch/{dispatch_id}")
def get_dispatch_item(dispatch_id: str):
    """Retrieve details of a specific dispatch queue item."""
    item = dispatch_queue.get_item(dispatch_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Dispatch item '{dispatch_id}' not found.")
    return item.model_dump()


@app.post("/api/dispatch/test")
def dispatch_test_send(payload: TestSendPayload):
    """
    Controlled operator test send to a verified address.
    Does not affect real lead outreach status or sent_log.csv.
    """
    res = dispatch_coordinator.execute_test_send(payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


# -------------------------------------------------------------
# Suppression Operations (Phase 5)
# -------------------------------------------------------------
@app.get("/api/suppression")
def list_suppressions():
    """List all suppressed contact records."""
    return suppression_manager.list_suppressions()


@app.post("/api/suppression")
def add_suppression(payload: SuppressionCreatePayload):
    """Operator action: Suppress contact by email."""
    rec = suppression_manager.add_suppression(
        email=payload.email,
        reason=payload.reason,
        operator_note=payload.operator_note
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    return rec.model_dump()


@app.delete("/api/suppression/{email}")
def remove_suppression(email: str):
    """Remove a contact from suppression list."""
    removed = suppression_manager.remove_suppression(email)
    return {"status": "success", "removed": removed, "email": email}


# -------------------------------------------------------------
# Analytics Operations (Phase 5)
# -------------------------------------------------------------
@app.get("/api/analytics/overview")
def get_analytics_overview():
    """Global operational overview metrics from real data."""
    return analytics_service.get_overview()


@app.get("/api/analytics/campaigns")
def get_analytics_campaigns():
    """Campaign operational performance table."""
    return analytics_service.get_campaigns_table()


@app.get("/api/analytics/campaigns/{campaign_id}")
def get_analytics_campaign_detail(campaign_id: str):
    """Detailed analytics breakdown for a single campaign."""
    res = analytics_service.get_campaign_detail(campaign_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    return res


@app.get("/api/analytics/recent-activity")
def get_analytics_recent_activity(limit: int = 50):
    """Recent delivery telemetry events."""
    return analytics_service.get_recent_activity(limit=limit)


# -------------------------------------------------------------
# Reports Exports (Phase 5)
# -------------------------------------------------------------
@app.get("/download-dispatch-log")
def download_dispatch_log_csv():
    """Export dispatch queue items as CSV."""
    items = dispatch_queue.get_all_items()
    output = io.StringIO()
    fieldnames = [
        "dispatch_id", "campaign_id", "draft_id", "lead_id", "recipient_email",
        "recipient_name", "company_name", "status", "queued_at", "completed_at",
        "attempt_count", "last_error", "is_demo"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        writer.writerow({
            "dispatch_id": item.dispatch_id,
            "campaign_id": item.campaign_id,
            "draft_id": item.draft_id,
            "lead_id": item.lead_id,
            "recipient_email": item.recipient_email,
            "recipient_name": item.recipient_name,
            "company_name": item.company_name,
            "status": item.status,
            "queued_at": item.queued_at,
            "completed_at": item.completed_at,
            "attempt_count": item.attempt_count,
            "last_error": item.last_error,
            "is_demo": item.is_demo
        })
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resonance_dispatch_queue_log.csv"}
    )


@app.get("/download-suppression-list")
def download_suppression_csv():
    """Export suppression list as CSV."""
    supps = suppression_manager.list_suppressions()
    output = io.StringIO()
    fieldnames = ["email", "reason", "operator_note", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for s in supps:
        writer.writerow({
            "email": s.get("email"),
            "reason": s.get("reason"),
            "operator_note": s.get("operator_note"),
            "created_at": s.get("created_at")
        })
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resonance_suppression_list.csv"}
    )



# -------------------------------------------------------------
# Static Files & SPA Route Handlers
# -------------------------------------------------------------
STATIC_DIR = BASE_DIR / "web" / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static_assets")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serve SPA index.html for client-side routing."""
    target_file = STATIC_DIR / full_path
    if target_file.is_file():
        return FileResponse(str(target_file))

    index_html = STATIC_DIR / "index.html"
    if index_html.is_file():
        return FileResponse(str(index_html))

    return HTMLResponse(
        "<h3>Resonance - Export Outreach & Lead Operations</h3><p>Building frontend assets... Please wait.</p>",
        status_code=200
    )
