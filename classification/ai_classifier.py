"""
AI Email Classification Module.
Segments contacts into 'Business' and 'Individual' using Gemini API with batching,
deduplication, and deterministic heuristic fallback.
"""

import json
import requests
from typing import List, Dict, Any, Tuple
from config import load_settings


class AIClassifier:
    def __init__(self, api_key: str = None, model: str = None, batch_size: int = None):
        settings = load_settings()
        self.api_key = api_key or settings.get("gemini_api_key", "")
        raw_model = (model or settings.get("gemini_model", "gemini-3-flash-preview")).strip()
        if raw_model.lower() in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-3-flash", "gemini-2.0-flash"):
            self.model = "gemini-3-flash-preview"
        else:
            self.model = raw_model or "gemini-3-flash-preview"
        self.batch_size = batch_size or int(settings.get("classification_batch_size", 20))

    def classify_batch_heuristic(self, records: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Deterministic heuristic classification used as fallback or when API key is unset.
        """
        results = []
        personal_domains = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
            "aol.com", "protonmail.com", "zoho.com", "mail.com", "yandex.com", "gmx.com"
        }
        business_prefixes = {
            "info", "sales", "contact", "support", "office", "wholesale",
            "procurement", "orders", "admin", "b2b", "inquiry", "team"
        }

        for r in records:
            email = r.get("email", "").strip().lower()
            if not email or "@" not in email:
                results.append({"email": email, "classification": "Individual", "reason": "Malformed email"})
                continue

            local, domain = email.split("@", 1)
            company = (r.get("company_name") or "").lower()
            name = (r.get("buyer_name") or "").lower()

            # High confidence business indicators
            if domain not in personal_domains:
                classification = "Business"
                reason = f"Corporate domain '{domain}'"
            elif any(local.startswith(p) for p in business_prefixes):
                classification = "Business"
                reason = f"Business role prefix '{local}'"
            elif any(term in company for term in ["ltd", "inc", "llc", "wholesale", "studio", "center", "shop", "distributor", "exports"]):
                classification = "Business"
                reason = f"Commercial entity name '{r.get('company_name')}'"
            else:
                classification = "Individual"
                reason = f"Personal webmail domain '{domain}' without commercial prefix"

            results.append({
                "email": email,
                "classification": classification,
                "reason": reason
            })

        return results

    def classify_batch_gemini(self, records: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Classify batch using Gemini API.
        """
        import os
        if not self.api_key or os.getenv("QUOTA_SAFE_MODE", "").strip().lower() in ("1", "true", "yes"):
            return self.classify_batch_heuristic(records)

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        prompt_data = [
            {
                "email": r.get("email"),
                "buyer_name": r.get("buyer_name"),
                "company_name": r.get("company_name"),
                "website": r.get("website")
            }
            for r in records
        ]

        system_instruction = (
            "You are an expert B2B export sales analyst for a Singing Bowls manufacturer. "
            "Classify each contact as either 'Business' (wholesale distributor, studio, sound healing academy, music shop, corporate importer) "
            "or 'Individual' (retail end-consumer, solo enthusiast, private yoga student). "
            "Return strictly a valid JSON array of objects with keys: 'email', 'classification' ('Business' or 'Individual'), and 'reason'."
        )

        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_instruction}\n\nContacts to classify:\n{json.dumps(prompt_data, indent=2)}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)
                if isinstance(parsed, list):
                    return parsed
        except Exception:
            pass

        # Fallback if API fails
        return self.classify_batch_heuristic(records)

    def classify_records(self, records: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Deduplicates records, runs classification in batches, and partitions into
        (business_records, individual_records).
        """
        # Deduplicate by email
        seen = set()
        unique_records = []
        for r in records:
            e = r.get("email", "").strip().lower()
            if e and e not in seen:
                seen.add(e)
                unique_records.append(r)

        business_list = []
        individual_list = []

        # Process in batches
        for i in range(0, len(unique_records), self.batch_size):
            chunk = unique_records[i : i + self.batch_size]
            classifications = self.classify_batch_gemini(chunk)

            # Map classification back to record
            class_map = {item.get("email", "").lower(): item.get("classification", "Individual") for item in classifications}

            for rec in chunk:
                e = rec.get("email", "").lower()
                assigned = class_map.get(e, "Individual")
                rec["classification"] = assigned
                if assigned == "Business":
                    business_list.append(rec)
                else:
                    individual_list.append(rec)

        return business_list, individual_list
