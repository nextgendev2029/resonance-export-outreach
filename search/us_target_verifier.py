"""
United States Targeting & Location Verification Engine for Resonance.
Deterministic verification of US location signals using state dictionaries,
major commercial hubs, postal codes, telephone area codes, and address patterns.
Avoids assuming '.com' denotes a US business.
"""

import re
from typing import Dict, Any, Tuple, Optional

# 50 US States + DC
US_STATES: Dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY"
}

# Major US commercial cities & trade hubs
US_CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "Austin", "San Jose", "San Francisco",
    "Seattle", "Denver", "Boston", "Miami", "Atlanta", "Portland", "Las Vegas",
    "Nashville", "Charlotte", "Indianapolis", "Minneapolis", "Detroit", "Tampa",
    "Orlando", "Sacramento", "Salt Lake City", "Kansas City", "Raleigh", "Boulder",
    "Scottsdale", "Santa Monica", "Oakland", "Long Beach", "Fort Lauderdale"
]

# Foreign indicators that strongly point away from US
FOREIGN_INDICATORS = [
    (re.compile(r"\b(united kingdom|great britain|london|manchester|birmingham|edinburgh)\b", re.I), "United Kingdom"),
    (re.compile(r"\b(germany|deutschland|berlin|munich|münchen|hamburg|frankfurt|gmbh)\b", re.I), "Germany"),
    (re.compile(r"\b(canada|toronto|vancouver|montreal|calgary|ottawa)\b", re.I), "Canada"),
    (re.compile(r"\b(australia|sydney|melbourne|brisbane|perth|pty ltd)\b", re.I), "Australia"),
    (re.compile(r"\b(france|paris|lyon|marseille)\b", re.I), "France"),
    (re.compile(r"\b(india|delhi|mumbai|bangalore|pvt ltd)\b", re.I), "India"),
    (re.compile(r"\b(japan|tokyo|osaka|kyoto)\b", re.I), "Japan"),
    (re.compile(r"\b(switzerland|zurich|geneva|basel)\b", re.I), "Switzerland"),
    (re.compile(r"\b(netherlands|amsterdam|rotterdam)\b", re.I), "Netherlands"),
]

# Foreign TLDs
FOREIGN_TLDS = {
    ".uk", ".co.uk", ".de", ".ca", ".au", ".com.au", ".fr", ".in", ".co.in",
    ".jp", ".ch", ".nl", ".es", ".it", ".at", ".nz", ".se", ".no", ".sg"
}

# US Postal Code Pattern: e.g. "CA 94103" or "NY 10001-1234"
US_ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")

# US Phone Number Pattern: e.g. +1 (555) 123-4567 or 555-123-4567
US_PHONE_PATTERN = re.compile(r"(?:\+1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]([2-9]\d{2})[\s.-](\d{4})\b")


class USTargetVerifier:
    """Verifies whether a discovered lead operates within the United States."""

    @classmethod
    def verify(
        cls,
        company_name: str = "",
        website: str = "",
        raw_text: str = "",
        api_country: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate text, metadata, and web signals for US location presence.
        Returns:
            {
                "country": str ("United States", specific foreign country, or "Unknown"),
                "country_match": "true" | "false" | "unknown",
                "state": Optional[str],
                "city": Optional[str],
                "country_evidence": str,
                "phone": Optional[str]
            }
        """
        evidence = []
        state_found = None
        city_found = None
        phone_found = None

        combined = f"{company_name} {website} {raw_text}".strip()
        combined_lower = combined.lower()

        # 1. Check for foreign TLD
        if website:
            site_lower = website.lower()
            for tld in FOREIGN_TLDS:
                if site_lower.endswith(tld) or f"{tld}/" in site_lower:
                    return {
                        "country": "International",
                        "country_match": "false",
                        "state": None,
                        "city": None,
                        "country_evidence": f"Foreign TLD detected ({tld})",
                        "phone": None
                    }

        # 2. Check for explicit foreign signals
        for pattern, country_name in FOREIGN_INDICATORS:
            if pattern.search(combined_lower):
                # Ensure it's not a US business referencing international partners
                if not re.search(r"\b(usa|united states|u\.s\.|u\.s\.a\.)\b", combined_lower):
                    return {
                        "country": country_name,
                        "country_match": "false",
                        "state": None,
                        "city": None,
                        "country_evidence": f"Foreign geographic indicator: {country_name}",
                        "phone": None
                    }

        # 3. Check for US phone number
        phone_match = US_PHONE_PATTERN.search(combined)
        if phone_match:
            phone_found = phone_match.group(0).strip()
            evidence.append(f"US phone pattern: {phone_found}")

        # 4. Check for explicit US country mentions
        if re.search(r"\b(united states|u\.s\.a\.|u\.s\.|usa)\b", combined_lower):
            evidence.append("Explicit United States designation")

        # 5. Check for US States (full name or capitalized 2-letter postal code)
        for state_name, state_code in US_STATES.items():
            if re.search(rf"\b{re.escape(state_name)}\b", combined_lower):
                state_found = state_name.title()
                evidence.append(f"US state: {state_found}")
                break
            # Match 2-letter code if preceded by comma or space (e.g. "Austin, TX", "Miami FL 33101")
            code_match = re.search(rf"(?:,\s*|\b)({state_code})\b(?:\s+\d{{5}}|\b)", combined)
            if code_match:
                state_found = state_name.title()
                evidence.append(f"US state: {state_found} ({state_code})")
                break

        # 6. Check for US Cities
        for city in US_CITIES:
            if re.search(rf"\b{re.escape(city)}\b", combined, re.I):
                city_found = city
                evidence.append(f"US trade hub: {city}")
                break

        # 7. Check for US ZIP Code
        zip_match = US_ZIP_PATTERN.search(combined)
        if zip_match and (state_found or city_found or "Explicit United States designation" in evidence):
            evidence.append(f"US postal code: {zip_match.group(0)}")

        # 8. API location metadata override
        if api_country and api_country.lower() in ("united states", "usa", "us"):
            evidence.append("API provider location metadata: United States")

        # Compile verdict
        if evidence:
            return {
                "country": "United States",
                "country_match": "true",
                "state": state_found,
                "city": city_found,
                "country_evidence": "; ".join(evidence),
                "phone": phone_found
            }
        else:
            return {
                "country": "Unknown",
                "country_match": "unknown",
                "state": None,
                "city": None,
                "country_evidence": "Insufficient location signals in public metadata",
                "phone": None
            }
