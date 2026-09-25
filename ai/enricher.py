"""
Controlled Website Context Extractor and AI Lead Enrichment Service.
Shallow web crawler with timeout/redirect safety, zero-hallucination extraction,
evidence snippet generation, and run tracking in data/enrichment_runs.json.
"""

import os
import re
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from config import DATA_DIR, load_settings
from .gemini_client import GeminiClient
from .prompts import build_enrichment_prompt
from .classifier import LeadClassifier
from .schemas import (
    LeadEnrichmentRecord,
    ClassificationResult,
    BuyerRelevanceResult,
    BusinessDetails,
    PublicContact,
    EvidenceItem,
    EnrichmentRunRecord
)

LEAD_ENRICHMENT_FILE = DATA_DIR / "lead_enrichment.json"
ENRICHMENT_RUNS_FILE = DATA_DIR / "enrichment_runs.json"

DEFAULT_CRAWLER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (Resonance/2.0 B2B Lead Intelligence)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

# Regex for phone numbers (international + standard domestic)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}"
)

# Target priority subpages for shallow crawl
PRIORITY_PATHS = [
    "/about", "/about-us", "/who-we-are",
    "/contact", "/contact-us", "/reach-us",
    "/wholesale", "/b2b", "/distributors",
    "/products", "/shop", "/services"
]


class WebsiteContextExtractor:
    """
    Controlled shallow website context crawler.
    Inspects homepage and up to 2 high-value subpages (/about, /contact, /wholesale).
    Respects rate limits, timeouts, and anti-bot blocks.
    """
    def __init__(self, timeout: int = 8, max_pages: int = 3, max_bytes: int = 25000):
        self.timeout = timeout
        self.max_pages = max_pages
        self.max_bytes = max_bytes
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_CRAWLER_HEADERS)

    def extract_clean_text(self, html: str) -> str:
        """Strip scripts, styles, boilerplate, and extract readable text."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            for elem in soup(["script", "style", "noscript", "svg", "header", "footer"]):
                elem.decompose()
            text = soup.get_text(separator=" ", strip=True)
            # Normalize whitespace
            return " ".join(text.split())
        except Exception:
            return ""

    def crawl_website(self, raw_url: str) -> Tuple[str, Dict[str, str], Dict[str, Any], List[str]]:
        """
        Shallow crawl of the website.
        Returns: (status, pages_text_dict, detected_meta, pages_crawled)
        status: 'completed', 'blocked', 'unreachable', 'invalid_url'
        """
        if not raw_url or not isinstance(raw_url, str) or not raw_url.strip():
            return "invalid_url", {}, {}, []

        raw_url = raw_url.strip()
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url

        try:
            parsed = urlparse(raw_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return "invalid_url", {}, {}, []

        pages_text: Dict[str, str] = {}
        pages_crawled: List[str] = []
        detected_meta: Dict[str, Any] = {
            "phones": [],
            "emails": [],
            "title": "",
            "description": ""
        }

        # 1. Fetch homepage
        try:
            resp = self.session.get(base_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code in (401, 403):
                return "blocked", {}, {}, [base_url]
            if resp.status_code != 200:
                # Try original raw_url if different
                if raw_url != base_url:
                    resp = self.session.get(raw_url, timeout=self.timeout, allow_redirects=True)
                    if resp.status_code != 200:
                        return "unreachable", {}, {}, [raw_url]
                else:
                    return "unreachable", {}, {}, [base_url]

            soup = BeautifulSoup(resp.text[:50000], "html.parser")
            if soup.title and soup.title.string:
                detected_meta["title"] = soup.title.string.strip()

            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc and meta_desc.get("content"):
                detected_meta["description"] = meta_desc["content"].strip()

            # Find mailto links
            for mailto in soup.select('a[href^="mailto:"]'):
                href = mailto.get("href", "")
                em = href.replace("mailto:", "").split("?")[0].strip().lower()
                if em and "@" in em and em not in detected_meta["emails"]:
                    detected_meta["emails"].append(em)

            # Extract phone patterns
            phone_matches = PHONE_REGEX.findall(resp.text[:self.max_bytes])
            for pm in phone_matches[:3]:
                clean_phone = pm.strip()
                if len(clean_phone) >= 7 and clean_phone not in detected_meta["phones"]:
                    detected_meta["phones"].append(clean_phone)

            home_text = self.extract_clean_text(resp.text[:self.max_bytes])
            pages_text[resp.url] = home_text
            pages_crawled.append(resp.url)

            # Discover internal links to /about, /contact, /wholesale
            discovered_links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full_url = urljoin(resp.url, href)
                parsed_href = urlparse(full_url)
                if parsed_href.netloc == parsed.netloc:
                    path_lower = parsed_href.path.lower()
                    if any(p in path_lower for p in PRIORITY_PATHS):
                        discovered_links.add(full_url)

            # Fetch up to (max_pages - 1) additional discovered pages
            for link in list(discovered_links)[: (self.max_pages - 1)]:
                if len(pages_crawled) >= self.max_pages:
                    break
                try:
                    sub_resp = self.session.get(link, timeout=self.timeout, allow_redirects=True)
                    if sub_resp.status_code == 200:
                        sub_text = self.extract_clean_text(sub_resp.text[:self.max_bytes])
                        pages_text[link] = sub_text
                        pages_crawled.append(link)

                        # Check for phones/emails on contact page
                        for mailto in BeautifulSoup(sub_resp.text[:20000], "html.parser").select('a[href^="mailto:"]'):
                            href = mailto.get("href", "")
                            em = href.replace("mailto:", "").split("?")[0].strip().lower()
                            if em and "@" in em and em not in detected_meta["emails"]:
                                detected_meta["emails"].append(em)
                except Exception:
                    continue

            return "completed", pages_text, detected_meta, pages_crawled
        except requests.exceptions.Timeout:
            return "unreachable", {}, {}, [base_url]
        except requests.exceptions.RequestException:
            return "unreachable", {}, {}, [base_url]
        except Exception:
            return "unreachable", {}, {}, [base_url]


class LeadEnricher:
    """
    Orchestrates website crawling, AI intelligence synthesis,
    evidence extraction, and persistence.
    """
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()
        self.crawler = WebsiteContextExtractor()
        self.classifier = LeadClassifier(self.gemini)
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure enrichment data files exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not LEAD_ENRICHMENT_FILE.exists():
            with open(LEAD_ENRICHMENT_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
        if not ENRICHMENT_RUNS_FILE.exists():
            with open(ENRICHMENT_RUNS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    def load_all_enrichments(self) -> Dict[str, Dict[str, Any]]:
        """Load dictionary of all lead enrichment records keyed by lead_id."""
        self._ensure_storage()
        try:
            with open(LEAD_ENRICHMENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_enrichment_by_lead_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get enrichment record for a single lead."""
        all_enr = self.load_all_enrichments()
        return all_enr.get(lead_id)

    def save_enrichment(self, record: LeadEnrichmentRecord):
        """Persist a single lead enrichment record."""
        self._ensure_storage()
        all_enr = self.load_all_enrichments()
        all_enr[record.lead_id] = record.to_dict()
        with open(LEAD_ENRICHMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_enr, f, indent=2)

    def load_enrichment_runs(self) -> List[Dict[str, Any]]:
        """Load history of enrichment runs."""
        self._ensure_storage()
        try:
            with open(ENRICHMENT_RUNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def record_run(self, run_record: EnrichmentRunRecord):
        """Append an enrichment run record to data/enrichment_runs.json."""
        self._ensure_storage()
        runs = self.load_enrichment_runs()
        runs.insert(0, run_record.to_dict())
        with open(ENRICHMENT_RUNS_FILE, "w", encoding="utf-8") as f:
            json.dump(runs[:100], f, indent=2)

    def _heuristic_enrichment(
        self,
        lead: Dict[str, Any],
        pages_text: Dict[str, str],
        meta: Dict[str, Any],
        pages_crawled: List[str]
    ) -> LeadEnrichmentRecord:
        """
        Rule-based factual extraction when Gemini API is unconfigured or unavailable.
        Zero hallucination: uses exact text evidence from crawled pages.
        """
        lead_id = lead.get("lead_id", "")
        company_name = lead.get("company_name") or meta.get("title") or "Unknown"
        website = lead.get("website", "")
        combined_text = " ".join(pages_text.values()).lower()

        evidence: List[EvidenceItem] = []

        # 1. Relevance Assessment
        high_terms = ["singing bowl", "singing bowls", "tibetan bowl", "sound healing", "sound bath", "sound therapy", "gong"]
        med_terms = ["yoga", "meditation", "wellness", "holistic", "spiritual", "musical instrument", "acoustics", "healing"]

        relevance = "Unknown"
        rel_confidence = 0.5
        rel_reason = "Insufficient website text to establish relevance."

        matched_high = [t for t in high_terms if t in combined_text]
        matched_med = [t for t in med_terms if t in combined_text]

        primary_url = pages_crawled[0] if pages_crawled else website

        if matched_high:
            relevance = "High"
            rel_confidence = 0.90
            rel_reason = f"Website explicitly references core sound healing goods: '{', '.join(matched_high[:3])}'."
            evidence.append(EvidenceItem(
                url=primary_url,
                field="buyer_relevance",
                evidence=rel_reason,
                confidence=0.90
            ))
        elif matched_med:
            relevance = "Medium"
            rel_confidence = 0.75
            rel_reason = f"Website references related holistic wellness disciplines: '{', '.join(matched_med[:3])}'."
            evidence.append(EvidenceItem(
                url=primary_url,
                field="buyer_relevance",
                evidence=rel_reason,
                confidence=0.75
            ))
        elif combined_text:
            relevance = "Low"
            rel_confidence = 0.70
            rel_reason = "Website active, but no sound healing, meditation, or yoga goods described."
            evidence.append(EvidenceItem(
                url=primary_url,
                field="buyer_relevance",
                evidence=rel_reason,
                confidence=0.70
            ))

        # 2. Business Type
        b_type = None
        wholesale_av = None
        if "wholesale" in combined_text or "distributor" in combined_text or "b2b" in combined_text:
            b_type = "Wholesale Distributor / B2B Supplier"
            wholesale_av = True
            evidence.append(EvidenceItem(
                url=primary_url,
                field="business_type",
                evidence="Wholesale / distribution inquiries actively referenced on website.",
                confidence=0.85
            ))
        elif "studio" in combined_text or "academy" in combined_text or "classes" in combined_text:
            b_type = "Sound Healing / Yoga Studio"
            wholesale_av = False
            evidence.append(EvidenceItem(
                url=primary_url,
                field="business_type",
                evidence="Studio or academy instruction terms identified in page content.",
                confidence=0.80
            ))
        elif "shop" in combined_text or "store" in combined_text or "cart" in combined_text:
            b_type = "Retail Wellness Boutique"
            wholesale_av = False

        # 3. Industry
        industry = "Wellness & Sound Therapy" if (matched_high or matched_med) else "Commercial Enterprise"

        # 4. Description from meta
        desc = meta.get("description") or (pages_text.get(primary_url, "")[:200] + "..." if pages_text else None)

        # 5. Public Contact
        phones = meta.get("phones", [])
        emails = meta.get("emails", [])
        phone_val = phones[0] if phones else None
        email_val = emails[0] if emails else (lead.get("email") or None)

        # 6. Classification
        class_res = self.classifier.classify_heuristic(lead)

        return LeadEnrichmentRecord(
            lead_id=lead_id,
            enrichment_status="enriched",
            enriched_at=datetime.utcnow().isoformat() + "Z",
            classification=class_res,
            buyer_relevance=BuyerRelevanceResult(
                relevance=relevance,
                confidence=rel_confidence,
                reason=rel_reason,
                evidence=[ev for ev in evidence if ev.field == "buyer_relevance"]
            ),
            business_details=BusinessDetails(
                company_name=company_name,
                business_type=b_type,
                industry=industry,
                company_description=desc,
                wholesale_available=wholesale_av,
                confidence=0.80 if b_type else 0.50
            ),
            public_contact=PublicContact(
                name=lead.get("buyer_name") or None,
                role="General Contact" if lead.get("buyer_name") else "Unknown",
                phone=phone_val,
                email=email_val,
                confidence=0.75 if (phone_val or email_val) else 0.0
            ),
            evidence=evidence,
            ai_model="heuristic_rule_engine",
            ai_confidence=rel_confidence,
            pages_crawled=pages_crawled,
            error=None
        )

    def enrich_lead(
        self,
        lead: Dict[str, Any],
        run_id: Optional[str] = None,
        force_refresh: bool = False,
        allow_demo: bool = False
    ) -> LeadEnrichmentRecord:
        """
        Enrich a single lead.
        Enforces demo lead protection: demo records are skipped unless allow_demo=True.
        """
        lead_id = lead.get("lead_id", "")
        website = (lead.get("website") or "").strip()
        is_demo = str(lead.get("is_demo", "")).strip().lower() == "true"

        # DEMO SAFETY: Protect demo leads from inadvertent real enrichment
        if is_demo and not allow_demo:
            return LeadEnrichmentRecord(
                lead_id=lead_id,
                enrichment_status="not_applicable",
                error="Demo lead excluded from live intelligence pipeline.",
                enriched_at=datetime.utcnow().isoformat() + "Z"
            )

        # Cache check
        if not force_refresh:
            existing = self.get_enrichment_by_lead_id(lead_id)
            if existing and existing.get("enrichment_status") == "enriched":
                try:
                    return LeadEnrichmentRecord(**existing)
                except Exception:
                    pass

        # If lead has no website
        if not website:
            # Run heuristic classification only
            class_res = self.classifier.classify_heuristic(lead)
            rec = LeadEnrichmentRecord(
                lead_id=lead_id,
                enrichment_status="not_applicable",
                enriched_at=datetime.utcnow().isoformat() + "Z",
                enrichment_run_id=run_id,
                classification=class_res,
                buyer_relevance=BuyerRelevanceResult(
                    relevance="Unknown",
                    confidence=0.3,
                    reason="No company website available to verify business activities."
                ),
                public_contact=PublicContact(
                    name=lead.get("buyer_name") or None,
                    role="Unknown",
                    email=lead.get("email") or None
                ),
                ai_model="heuristic_engine",
                ai_confidence=0.3,
                error="No company website found"
            )
            self.save_enrichment(rec)
            return rec

        # Crawl website
        crawl_status, pages_text, meta, pages_crawled = self.crawler.crawl_website(website)

        if crawl_status == "blocked":
            rec = LeadEnrichmentRecord(
                lead_id=lead_id,
                enrichment_status="blocked",
                enriched_at=datetime.utcnow().isoformat() + "Z",
                enrichment_run_id=run_id,
                pages_crawled=pages_crawled,
                error="Website access blocked by anti-bot, CAPTCHA, or HTTP 403"
            )
            self.save_enrichment(rec)
            return rec

        if crawl_status == "unreachable" or not pages_text:
            rec = LeadEnrichmentRecord(
                lead_id=lead_id,
                enrichment_status="failed",
                enriched_at=datetime.utcnow().isoformat() + "Z",
                enrichment_run_id=run_id,
                pages_crawled=pages_crawled,
                error=f"Website could not be reached ({crawl_status})"
            )
            self.save_enrichment(rec)
            return rec

        # AI Enrichment via Gemini if configured
        if self.gemini.is_configured():
            prompt = build_enrichment_prompt(
                company_name=lead.get("company_name", ""),
                website=website,
                page_texts=pages_text,
                email=lead.get("email")
            )
            parsed, err = self.gemini.generate_json(prompt)

            if parsed and isinstance(parsed, dict):
                try:
                    # Construct verified models
                    class_data = parsed.get("classification", {})
                    class_res = ClassificationResult(**class_data) if class_data else self.classifier.classify_heuristic(lead)

                    rel_data = parsed.get("buyer_relevance", {})
                    rel_res = BuyerRelevanceResult(**rel_data) if rel_data else BuyerRelevanceResult()

                    biz_data = parsed.get("business_details", {})
                    biz_res = BusinessDetails(**biz_data) if biz_data else BusinessDetails()

                    cont_data = parsed.get("public_contact", {})
                    # Ensure public phone falls back to meta phone if regex found one
                    if cont_data and not cont_data.get("phone") and meta.get("phones"):
                        cont_data["phone"] = meta["phones"][0]
                    cont_res = PublicContact(**cont_data) if cont_data else PublicContact()

                    ev_items = [EvidenceItem(**ev) for ev in parsed.get("evidence", []) if isinstance(ev, dict)]

                    avg_conf = (class_res.confidence + rel_res.confidence) / 2.0

                    rec = LeadEnrichmentRecord(
                        lead_id=lead_id,
                        enrichment_status="enriched",
                        enriched_at=datetime.utcnow().isoformat() + "Z",
                        enrichment_run_id=run_id,
                        classification=class_res,
                        buyer_relevance=rel_res,
                        business_details=biz_res,
                        public_contact=cont_res,
                        evidence=ev_items,
                        ai_model=self.gemini.model,
                        ai_confidence=round(avg_conf, 2),
                        pages_crawled=pages_crawled,
                        error=None
                    )
                    self.save_enrichment(rec)
                    return rec
                except Exception:
                    pass

        # Fallback to heuristic factual enrichment
        rec = self._heuristic_enrichment(lead, pages_text, meta, pages_crawled)
        rec.enrichment_run_id = run_id
        self.save_enrichment(rec)
        return rec

    def enrich_batch(
        self,
        leads: List[Dict[str, Any]],
        force_refresh: bool = False,
        allow_demo: bool = False,
        progress_callback: Optional[callable] = None
    ) -> EnrichmentRunRecord:
        """
        Execute an enrichment batch over a list of leads.
        Tracks execution in data/enrichment_runs.json.
        """
        run_id = f"enrich_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        started_at = datetime.utcnow().isoformat() + "Z"
        start_time = time.time()

        run_record = EnrichmentRunRecord(
            run_id=run_id,
            started_at=started_at,
            lead_count=len(leads),
            status="running"
        )

        success = 0
        failed = 0
        skipped = 0
        ai_calls_start = self.gemini.request_count
        websites_crawled = 0

        for i, lead in enumerate(leads):
            is_demo = str(lead.get("is_demo", "")).strip().lower() == "true"
            if is_demo and not allow_demo:
                skipped += 1
                continue

            try:
                res = self.enrich_lead(lead, run_id=run_id, force_refresh=force_refresh, allow_demo=allow_demo)
                if res.enrichment_status == "enriched":
                    success += 1
                elif res.enrichment_status in ("failed", "blocked"):
                    failed += 1
                else:
                    skipped += 1

                if res.pages_crawled:
                    websites_crawled += len(res.pages_crawled)

                if progress_callback:
                    progress_callback(i + 1, len(leads), lead.get("email", ""), res.enrichment_status)

                # Polite throttle to respect external hosts and API limits
                time.sleep(0.5)
            except Exception as e:
                failed += 1

        duration = round(time.time() - start_time, 2)
        run_record.completed_at = datetime.utcnow().isoformat() + "Z"
        run_record.successful_count = success
        run_record.failed_count = failed
        run_record.skipped_count = skipped
        run_record.ai_calls = self.gemini.request_count - ai_calls_start
        run_record.websites_crawled = websites_crawled
        run_record.status = "completed"
        run_record.duration = duration

        self.record_run(run_record)
        return run_record
