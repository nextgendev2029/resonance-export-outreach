# Resonance - Export Outreach & Operations

> Operational B2B buyer discovery, lead intelligence, campaign staging, and controlled outreach platform for home-decor exporters targeting the United States market.

---

## 1. Overview

**Resonance** is an end-to-end export operations platform built for home-decor manufacturers and sellers (specialized in handcrafted Himalayan Singing Bowls, meditation gongs, and acoustic decor) seeking verified B2B wholesale buyers across the United States.

> **Important Operational Note**:
> **Buyer discovery is performed programmatically through configured APIs, trade directories, and website crawling. CSV is not a user input requirement.**
> Internal CSV and JSON files within `data/` serve strictly as application persistence and audit export artifacts; users discover, filter, classify, and stage buyer outreach entirely through the interactive web application.

---

## 2. Core Operational Workflow

The system enforces a disciplined, multi-stage export pipeline with mandatory operator review gates:

```
[Seller / Product Profile]
          ↓
[API & Multi-Source Discovery]
(Google Custom Search, US Trade Directory, Website Crawler)
          ↓
[Extraction & Normalization]
(Structured Contact Extraction, Metadata Harvesting)
          ↓
[Validation & Deduplication]
(Syntax Verification, MX Checks, Dual-Key Domain/Email Deduplication)
          ↓
[AI Intelligence & Segmentation]
(Gemini 3 Flash: Business vs. Individual, Grounded Relevance, Evidence Chain)
          ↓
[Campaign Staging & Personalization]
(Audience Selection, Verified Catalog PDF Attachment, Placeholder Generation)
          ↓
[Operator Review Queue]
(Draft Inspection, Edit, Versioning, Approval / Rejection Gate)
          ↓
[Controlled Dispatch Engine]
(15-Point Preflight Verification, Suppression, Rate Limiting, Dry-Run / Gmail SMTP)
          ↓
[Telemetry & Audit Logging]
(Persistent Queue State, SMTP Handshake Verification, CSV Delivery Exports)
```

---

## 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, Pydantic v2, Requests, BeautifulSoup4, PyPDF
- **Frontend**: React 18, Vite, Lucide React, Restrained Vanilla CSS B2B Design System
- **AI Intelligence**: Google Gemini API (`gemini-3-flash-preview`), Grounded Schema Validation
- **Discovery**: Google Custom Search JSON API, US B2B Trade Directory, Website Contact Crawler, Meta Graph API (Optional), LinkedIn Organization API (Optional)
- **Email Outreach**: Gmail SMTP over TLS (`smtp.gmail.com:587`) / SSL (`465`) with Google App Password authentication
- **Persistence**: Atomic flat-file JSON and CSV persistence layer (`data/`)

---

## 4. Discovery Providers & Integration Status

Resonance integrates multiple search channels with strict US geographic targeting and graceful degradation when credentials are unset:

| Provider | Provider ID | Status | Credential Requirements | Role |
|---|---|---|---|---|
| **Google Search API** | `google` | **READY** (Configured) | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID` | US geo-targeted wholesale query builder & index search |
| **US B2B Trade Directory** | `directory` | **READY** (Built-in) | *None* | High-precision index of US home-decor & gift showrooms |
| **Website Contact Crawler** | `website` | **READY** (Built-in) | *None* | Controlled shallow crawler for showroom `/contact` and `/wholesale` pages |
| **Meta Graph API (Facebook)** | `facebook` | **OPTIONAL** | `FACEBOOK_ACCESS_TOKEN` | Public business page contact search (fails gracefully if unconfigured) |
| **LinkedIn Organization API** | `linkedin` | **OPTIONAL** | `LINKEDIN_ACCESS_TOKEN` | Corporate company page discovery (fails gracefully if unconfigured) |

---

## 5. AI Lead Intelligence & Grounded Enrichment

Resonance utilizes Google Gemini (`gemini-3-flash-preview`) for factual lead analysis:

- **B2B Segmentation**: Categorizes contacts into `Business`, `Individual`, or `Unclassified` with confidence scores and reasoning.
- **Buyer Relevance**: Assesses buyer alignment (`High`, `Medium`, `Low`, `Unknown`) with Himalayan singing bowls and artisanal home decor.
- **Evidence Preservation**: Every derived attribute preserves citations and text evidence from public company pages.
- **Zero Hallucination Standard**: Factual heuristic fallback is automatically applied if the AI API is unconfigured or rate-limited.
- **Quota-Safe Guard**: Includes an explicit `QUOTA_SAFE_MODE` toggle to suppress non-essential API requests during testing or audits.

---

## 6. Campaigns & Operator Review Queue

Outreach is managed through structured campaign records rather than ad-hoc email sending:

1. **Audience Filtering**: Filter by validation status (`Valid`), segment (`Business`), relevance (`High`/`Medium`), and dataset (`Real` vs. `Demo`).
2. **Catalog Attachment Verification**: Automatically verifies the presence and PDF structural integrity of the export presentation (`company_presentation.pdf`, 3 KB) before draft staging.
3. **Template Substitution**: Grounded variable placeholders (`{{buyer_name}}`, `{{company_name}}`, `{{city}}`) with syntax validation.
4. **Human Review Gate**: Individual drafts must be operator-reviewed, edited, approved, or rejected with version logging. Only approved drafts proceed to the dispatch queue.

---

## 7. Dispatch Safety & Guardrails

To prevent accidental, duplicate, or unverified email transmission, Resonance includes comprehensive guardrails:

- **Dry-Run Mode (Default)**: Complete end-to-end dispatch simulation executing full preflight evaluation without opening external SMTP connections.
- **15-Point Preflight Eligibility**: Validates recipient syntax, campaign approval, persistent suppression list, duplicate send prevention (`sent_log.csv`), unresolved template tags, attachment validity, and daily sending caps.
- **Demo Data Isolation**: Leads flagged with `is_demo=true` are strictly isolated and prevented from receiving outbound communications.
- **Rate Throttling & Pacing**: Configurable per-run delay (default: 5 seconds) and daily dispatch limits (default: 100/day).
- **Persistent Queue with Atomic Claiming**: Concurrency-safe queue tracking item transitions (`Queued` → `Sending` → `Sent` / `Failed`).

---

## 8. Project Structure

```text
resonance-export-outreach/
├── main.py                     # CLI Pipeline Orchestrator
├── config.py                   # Central configuration & precedence engine
├── render.yaml                 # Render Blueprint deployment configuration
├── .python-version             # Python version specification (3.11.16)
├── requirements.txt            # Python backend dependencies
├── .env.example                # Documented environment variable template
├── .gitignore                  # Git exclusions (credentials, caches, build artifacts)
│
├── ai/                         # Gemini AI Client & Grounded Enrichment
│   ├── gemini_client.py        # Gemini 3 Flash REST client with backoff
│   ├── classifier.py           # B2B vs. Individual segmentation service
│   ├── enricher.py             # Controlled shallow crawler & intelligence layer
│   ├── prompts.py              # Zero-hallucination structured prompts
│   └── schemas.py              # Pydantic schemas with evidence tracking
│
├── search/                     # Discovery Engine & Provider Registry
│   ├── discovery_orchestrator.py # Multi-source query coordinator & deduplicator
│   ├── provider_registry.py    # Health monitoring & provider registration
│   ├── base_provider.py        # Provider abstract base class
│   ├── us_target_verifier.py   # US geographic validation engine
│   ├── relevance.py            # Home-decor buyer relevance scoring
│   └── providers/              # Provider implementations (Google, Directory, Website, etc.)
│
├── campaigns/                  # Campaign Management & Review Queue
│   ├── campaign_store.py       # Atomic campaign & draft persistence
│   ├── audience.py             # Audience eligibility & exclusion engine
│   ├── personalization.py      # Template substitution & AI draft generator
│   ├── draft_validator.py      # Preflight draft validation
│   └── models.py               # Pydantic campaign & draft models
│
├── dispatch/                   # Controlled Dispatch & Telemetry
│   ├── dispatcher.py           # Preflight evaluation & dispatch coordinator
│   ├── queue.py                # Persistent atomic dispatch queue
│   ├── sender.py               # Gmail SMTP sender with transient retry logic
│   ├── eligibility.py          # 15-point deterministic send check
│   ├── rate_limiter.py         # Daily & per-run pacing limits
│   ├── suppression.py          # Persistent suppression list manager
│   ├── delivery_log.py         # Structured event & audit logger
│   └── analytics.py            # Ground-truth telemetry aggregator
│
├── extraction/                 # Contact extraction & normalization
├── validation/                 # RFC email syntax & domain validation
├── outreach/                   # Gmail authentication & attachment verification
├── app_logging/                # Central data store & activity logger
├── reports/                    # CSV report generation & streaming
├── assets/                     # Collateral (company_presentation.pdf)
├── data/                       # Sanitized baseline fixtures & empty templates
│
├── web/                        # Web Server Layer
│   ├── app.py                  # FastAPI application & API router
│   └── static/                 # Production-built React single-page application
│
├── frontend/                   # React Single-Page Application Source
│   ├── src/
│   │   ├── components/         # Header, Sidebar, MetricCard, StatusBadge
│   │   ├── pages/              # Dashboard, Discovery, Leads, Intelligence, Campaigns, Analytics, etc.
│   │   ├── api.js              # REST API client with VITE_API_BASE_URL support
│   │   └── index.css           # Restrained B2B design system
│   ├── package.json
│   ├── vite.config.js          # Dynamic build target (Vercel dist / FastAPI static)
│   └── vercel.json             # Vercel SPA routing rewrites
│
└── tests/                      # Unit & Integration Test Suites
    ├── test_system.py          # Core pipeline unit tests
    ├── test_api_endpoints.py   # REST API endpoint tests
    ├── test_campaigns.py       # Campaign & review queue test suite
    ├── test_dispatch.py        # Controlled dispatch & eligibility tests
    ├── test_intelligence.py    # AI intelligence & schema tests
    ├── test_phase6_discovery.py# Discovery & provider registry tests
    └── test_config_precedence.py # Configuration precedence & safety tests
```

---

## 9. Environment Variables

Create a local `.env` file based on `.env.example`. Configuration precedence strictly follows:
1. Explicit persisted operator setting (via UI Settings)
2. Environment variables (`.env` or platform config)
3. Application defaults

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `GEMINI_API_KEY` | Optional | `""` | Google AI Studio API Key for AI Lead Intelligence |
| `GEMINI_MODEL` | Optional | `gemini-3-flash-preview` | Model identifier |
| `QUOTA_SAFE_MODE` | Optional | `true` | When `true`, suppresses live Gemini calls during audits |
| `GOOGLE_API_KEY` | Optional | `""` | Google Cloud API key for Custom Search JSON API |
| `GOOGLE_CSE_ID` | Optional | `""` | Google Programmable Search Engine CX identifier |
| `FACEBOOK_ACCESS_TOKEN` | Optional | `""` | Meta Graph API developer token |
| `LINKEDIN_ACCESS_TOKEN` | Optional | `""` | LinkedIn Organization API token |
| `GMAIL_EMAIL` | Optional | `""` | Sender Google Account address |
| `GMAIL_APP_PASSWORD` | Optional | `""` | 16-character Google App Password (NOT personal password) |
| `DRY_RUN` | Optional | `true` | Dispatch simulation mode (`true` prevents live email transmission) |
| `DAILY_SEND_LIMIT` | Optional | `100` | Maximum allowable emails per calendar day |
| `SEND_DELAY_SECONDS` | Optional | `5` | Pacing delay between outbound dispatches |
| `CORS_ALLOWED_ORIGINS` | Optional | `""` | Comma-separated frontend domains (e.g. `https://your-app.vercel.app`) |
| `DATA_DIR` | Optional | `data` | Directory path for persistence storage |
| `PORT` | Optional | `8000` | Port for the Uvicorn web server |

---

## 10. Installation & Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend development)

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/nextgendev2029/resonance-export-outreach.git
cd resonance-export-outreach

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your optional provider credentials
```

### 3. Run Backend (FastAPI)
```bash
python3.11 -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```
The application will serve the compiled React SPA at `http://127.0.0.1:8000`.

### 4. (Optional) Run Frontend Dev Server
If developing frontend components with Hot Module Replacement (HMR):
```bash
cd frontend
npm install
npm run dev
```
The Vite development server runs at `http://localhost:5173` and proxies API requests to `http://127.0.0.1:8000`.

---

## 11. Testing & Verification

Execute the complete automated test suite (108 unit and integration tests):
```bash
python3.11 -m unittest discover tests
```

Build the production frontend bundle:
```bash
cd frontend
npm run build
cd ..
```

---

## 12. Deployment Architecture

Resonance supports two production architectures:

### Option A: Unified Full-Stack on Render (Recommended)
FastAPI serves both the REST API endpoints and the pre-built React production bundle (`web/static/`).

- **Platform**: [Render](https://render.com) Web Service
- **Root Directory**: Repository root (`.`)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn web.app:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/discovery/config/status`
- **Persistent Disk**: Mount `data` at `/data` (1 GB) with `DATA_DIR=/data`

### Option B: Split Frontend (Vercel) + Backend (Render)
For teams preferring CDN frontend distribution with independent API hosting:

1. **Frontend on Vercel**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Environment Variable**: `VITE_API_BASE_URL=https://<your-render-backend>.onrender.com`
2. **Backend on Render**:
   - Configure Render with `CORS_ALLOWED_ORIGINS=https://<your-vercel-frontend>.vercel.app`
   - All backend API keys and Gmail credentials remain securely stored in Render environment variables.

---

## 13. Security & Open-Source Compliance

- **No Committed Secrets**: `.env` and all credential files are excluded via `.gitignore`.
- **Masked API Responses**: Settings and health endpoints never transmit raw passwords or keys to the client.
- **Sanitized Demo Telemetry**: Public repository files use RFC 2606 reserved domains (`example.com`, `example-*.com`) for sample fixtures.
- **Dry-Run Enforcement**: Outbound email outreach defaults to `DRY_RUN=true`.

---

## 14. License

This repository is published for demonstration and evaluation purposes. All rights reserved.
