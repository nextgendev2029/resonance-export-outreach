"""
AI Lead Classification Service.
Segments contacts into 'Business', 'Individual', and 'Unclassified'
using Gemini API with strict validation and deterministic heuristic fallback.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from config import load_settings
from .gemini_client import GeminiClient
from .prompts import build_classification_prompt
from .schemas import ClassificationResult, EvidenceItem

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "protonmail.com", "zoho.com", "mail.com", "yandex.com",
    "gmx.com", "live.com", "msn.com", "comcast.net", "sbcglobal.net"
}

BUSINESS_PREFIXES = {
    "info", "sales", "contact", "support", "office", "wholesale",
    "procurement", "orders", "admin", "b2b", "inquiry", "team",
    "imports", "export", "director", "purchasing"
}

COMMERCIAL_TERMS = {
    "ltd", "inc", "llc", "gmbh", "wholesale", "studio", "center",
    "shop", "distributor", "exports", "importers", "academy", "trading",
    "corporation", "co", "enterprises", "sound", "instruments", "wellness"
}


class LeadClassifier:
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()

    def classify_heuristic(self, record: Dict[str, Any]) -> ClassificationResult:
        """
        Deterministic, rule-based classification used when Gemini is unconfigured or fails.
        Never forces uncertain records into Business or Individual; yields 'Unclassified'.
        """
        email = (record.get("email") or "").strip().lower()
        company = (record.get("company_name") or "").strip().lower()
        buyer_name = (record.get("buyer_name") or "").strip().lower()

        evidence = []

        if not email or "@" not in email:
            return ClassificationResult(
                classification="Unclassified",
                confidence=0.3,
                reason="No valid email address available to assess domain structure.",
                evidence=[]
            )

        local, domain = email.split("@", 1)

        # 1. Check corporate domain
        if domain not in PERSONAL_DOMAINS and "." in domain:
            evidence.append(EvidenceItem(
                field="classification",
                evidence=f"Corporate organization domain '@{domain}'",
                confidence=0.88
            ))
            return ClassificationResult(
                classification="Business",
                confidence=0.88,
                reason=f"Dedicated commercial email domain '{domain}' indicates corporate presence.",
                evidence=evidence
            )

        # 2. Check commercial role prefix on public webmail
        matching_prefix = None
        for p in BUSINESS_PREFIXES:
            if local.startswith(p) or local == p:
                matching_prefix = p
                break

        if matching_prefix:
            evidence.append(EvidenceItem(
                field="classification",
                evidence=f"Commercial department prefix '{matching_prefix}@' on '{domain}'",
                confidence=0.82
            ))
            return ClassificationResult(
                classification="Business",
                confidence=0.82,
                reason=f"Business function prefix '{matching_prefix}@' indicates commercial contact.",
                evidence=evidence
            )

        # 3. Check commercial keywords in company name
        matching_term = None
        for term in COMMERCIAL_TERMS:
            if term in company:
                matching_term = term
                break

        if matching_term and company != "sound & wellness prospect":
            evidence.append(EvidenceItem(
                field="classification",
                evidence=f"Commercial entity term '{matching_term}' in company '{record.get('company_name')}'",
                confidence=0.80
            ))
            return ClassificationResult(
                classification="Business",
                confidence=0.80,
                reason=f"Registered commercial entity naming '{record.get('company_name')}'.",
                evidence=evidence
            )

        # 4. Personal webmail with solo enthusiast characteristics
        if domain in PERSONAL_DOMAINS:
            # If buyer name exists without corporate company name
            if buyer_name and (not company or company in ("sound & wellness prospect", "solo buyer", "private collector")):
                evidence.append(EvidenceItem(
                    field="classification",
                    evidence=f"Personal webmail domain '{domain}' with personal recipient '{record.get('buyer_name')}'",
                    confidence=0.75
                ))
                return ClassificationResult(
                    classification="Individual",
                    confidence=0.75,
                    reason=f"Individual person with personal webmail '{domain}' and no commercial organization.",
                    evidence=evidence
                )

        # 5. Default to Unclassified rather than guessing
        return ClassificationResult(
            classification="Unclassified",
            confidence=0.4,
            reason="Ambiguous indicators; neither clear commercial structure nor individual retail proof found.",
            evidence=[]
        )

    def classify_batch(
        self,
        records: List[Dict[str, Any]],
        batch_size: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Classify a list of lead records using Gemini API with heuristic fallback.
        Preserves original records, annotates with classification fields, and
        stores classification metadata.
        """
        if not records:
            return []

        results = []

        # If Gemini is configured, run through Gemini in batches
        if self.client.is_configured():
            for i in range(0, len(records), batch_size):
                chunk = records[i : i + batch_size]
                prompt_items = [
                    {
                        "email": r.get("email"),
                        "company_name": r.get("company_name"),
                        "buyer_name": r.get("buyer_name"),
                        "website": r.get("website")
                    }
                    for r in chunk
                ]
                prompt = build_classification_prompt(prompt_items)
                parsed, err = self.client.generate_json(prompt)

                if parsed and isinstance(parsed, dict) and "contacts" in parsed:
                    classified_map = {}
                    for item in parsed.get("contacts", []):
                        e = (item.get("email") or "").strip().lower()
                        try:
                            res = ClassificationResult(**item)
                            classified_map[e] = res
                        except Exception:
                            pass

                    for r in chunk:
                        e = (r.get("email") or "").strip().lower()
                        if e in classified_map:
                            res = classified_map[e]
                        else:
                            res = self.classify_heuristic(r)

                        annotated = dict(r)
                        annotated["classification"] = res.classification
                        annotated["classification_confidence"] = res.confidence
                        annotated["classification_reason"] = res.reason
                        annotated["classification_model"] = self.client.model
                        annotated["classified_at"] = datetime.utcnow().isoformat() + "Z"
                        annotated["classification_evidence"] = [ev.model_dump() for ev in res.evidence]
                        results.append(annotated)
                    continue

                # If batch failed, fallback to heuristic for this chunk
                for r in chunk:
                    res = self.classify_heuristic(r)
                    annotated = dict(r)
                    annotated["classification"] = res.classification
                    annotated["classification_confidence"] = res.confidence
                    annotated["classification_reason"] = res.reason
                    annotated["classification_model"] = "heuristic_fallback"
                    annotated["classified_at"] = datetime.utcnow().isoformat() + "Z"
                    annotated["classification_evidence"] = [ev.model_dump() for ev in res.evidence]
                    results.append(annotated)
        else:
            # Heuristic classification for all records
            for r in records:
                res = self.classify_heuristic(r)
                annotated = dict(r)
                annotated["classification"] = res.classification
                annotated["classification_confidence"] = res.confidence
                annotated["classification_reason"] = res.reason
                annotated["classification_model"] = "heuristic_engine"
                annotated["classified_at"] = datetime.utcnow().isoformat() + "Z"
                annotated["classification_evidence"] = [ev.model_dump() for ev in res.evidence]
                results.append(annotated)

        return results
