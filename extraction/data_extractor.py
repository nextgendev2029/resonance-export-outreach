"""
Data Extraction Module for Resonance.
Normalizes raw textual / HTML content from discovery sources into structured Buyer records.
Preserves source URLs, extracts emails (including basic obfuscation), and avoids fabricating data.
"""

import re
import uuid
from typing import List, Dict, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from validation.email_validator import EmailValidator

# Standard email regex pattern
RAW_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE
)

# Common obfuscated email pattern: name [at] domain [dot] com
OBFUSCATED_EMAIL_REGEX = re.compile(
    r"([a-zA-Z0-9_.+-]+)\s*(?:\[at\]|\(at\)|\s+at\s+)\s*([a-zA-Z0-9-]+)\s*(?:\[dot\]|\(dot\)|\s+dot\s+|\.)\s*([a-zA-Z0-9-.]+)",
    re.IGNORECASE
)


class DataExtractor:
    @staticmethod
    def extract_emails_from_text(raw_text: str) -> List[str]:
        """Extract candidate email addresses from unstructured string or HTML."""
        if not raw_text:
            return []
        
        # De-obfuscate common patterns first: e.g. "info [at] soundhealing.com"
        deobfuscated = OBFUSCATED_EMAIL_REGEX.sub(r"\1@\2.\3", raw_text)

        # If HTML, extract text safely
        clean_text = deobfuscated
        try:
            if "<" in deobfuscated and ">" in deobfuscated:
                soup = BeautifulSoup(deobfuscated, "html.parser")
                # Also check mailto links
                mailto_links = soup.select('a[href^="mailto:"]')
                mailto_emails = [a["href"].replace("mailto:", "").split("?")[0].strip() for a in mailto_links]
                clean_text = soup.get_text(separator=" ") + " " + " ".join(mailto_emails)
        except Exception:
            clean_text = deobfuscated

        matches = RAW_EMAIL_REGEX.findall(clean_text)
        seen = set()
        candidates = []
        for m in matches:
            cleaned = m.strip().strip(".,;:()[]{}<>\"'")
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                candidates.append(cleaned)
        return candidates

    @staticmethod
    def infer_company_from_domain_or_text(website: str = "", raw_snippet: str = "") -> str:
        """Infer a company or studio name without fabricating a fake entity."""
        if website:
            try:
                parsed = urlparse(website if "://" in website else f"http://{website}")
                domain = parsed.netloc or parsed.path
                domain = domain.lower().replace("www.", "")
                base = domain.split(".")[0]
                # Filter out generic hosts
                if base not in ("facebook", "linkedin", "instagram", "youtube", "twitter", "yelp", "yellowpages"):
                    if len(base) > 2:
                        return base.replace("-", " ").replace("_", " ").title()
            except Exception:
                pass

        if raw_snippet:
            # Check for company markers
            patterns = [
                r"([A-Z][a-zA-Z0-9\s&]{2,30}(?:Sound|Singing\s+Bowls?|Yoga|Studio|Wellness|Meditation|Acoustics|Instruments|Therapy|Exports|Wholesale|GmbH|LLC|Ltd|Inc))",
                r"(?:at|company:?)\s+([A-Z][a-zA-Z0-9\s&]{2,30})"
            ]
            for pat in patterns:
                match = re.search(pat, raw_snippet)
                if match:
                    candidate = match.group(1).strip()
                    if len(candidate) > 3 and not candidate.startswith("The "):
                        return candidate

        return ""

    @staticmethod
    def infer_country(raw_text: str = "") -> str:
        """Infer country only when there is reasonable evidence, otherwise return empty."""
        if not raw_text:
            return ""

        countries = [
            ("United States", ["united states", "usa", " u.s.", "california", "new york", "texas", "florida"]),
            ("Germany", ["germany", "deutschland", "berlin", "munich", "hamburg", ".de/"]),
            ("United Kingdom", ["united kingdom", "uk", "london", "manchester", ".co.uk"]),
            ("Canada", ["canada", "toronto", "vancouver", "montreal", ".ca/"]),
            ("Australia", ["australia", "sydney", "melbourne", "brisbane", ".com.au"]),
            ("France", ["france", "paris", ".fr/"]),
            ("Japan", ["japan", "tokyo", "kyoto", ".jp/"]),
            ("Switzerland", ["switzerland", "zurich", "geneva", ".ch/"]),
            ("Austria", ["austria", "vienna", ".at/"]),
            ("Netherlands", ["netherlands", "amsterdam", ".nl/"]),
            ("Spain", ["spain", "madrid", "barcelona", ".es/"]),
            ("Italy", ["italy", "milan", "rome", ".it/"]),
            ("Singapore", ["singapore", ".sg/"]),
            ("India", ["india", "delhi", "mumbai", ".in/"]),
        ]

        text_lower = f" {raw_text.lower()} "
        for country_name, keywords in countries:
            for kw in keywords:
                if kw in text_lower:
                    return country_name
        return ""

    @classmethod
    def normalize_record(
        cls,
        email: str = "",
        source_platform: str = "Web Search",
        source_url: str = "",
        buyer_name: str = "",
        company_name: str = "",
        website: str = "",
        country: str = "",
        raw_text: str = "",
        discovery_run_id: str = "",
        is_demo: bool = False
    ) -> Dict[str, str]:
        """
        Produce a normalized Buyer Record adhering to the schema.
        Never fabricates names or countries; preserves source URLs and flags missing emails.
        """
        email_clean = (email or "").strip().lower()

        # Validate syntax
        is_acceptable, val_status, reason = EmailValidator.validate(email_clean)

        # Infer company name if not provided
        if not company_name:
            company_name = cls.infer_company_from_domain_or_text(website, raw_text)

        # Infer country if not provided
        if not country and raw_text:
            country = cls.infer_country(raw_text)

        # Clean website URL
        website_clean = website.strip()
        if website_clean and not website_clean.startswith("http"):
            website_clean = f"https://{website_clean}"

        # Clean source URL
        source_url_clean = source_url.strip()
        if not source_url_clean and website_clean:
            source_url_clean = website_clean

        lead_id = f"lead_{uuid.uuid4().hex[:10]}"

        return {
            "lead_id": lead_id,
            "email": email_clean,
            "buyer_name": buyer_name.strip(),
            "company_name": company_name.strip() or "Sound & Wellness Prospect",
            "website": website_clean,
            "country": country.strip() or "International",
            "source_platform": source_platform.strip(),
            "source_url": source_url_clean,
            "validation_status": val_status,
            "classification": "Unclassified",
            "outreach_status": "Not contacted",
            "discovery_run_id": discovery_run_id or "adhoc",
            "is_demo": "true" if is_demo else "false",
            "notes": ""
        }
