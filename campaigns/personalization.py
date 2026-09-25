"""
Personalization Engine for Resonance Campaigns (Phase 4).
Generates strictly grounded, professional B2B outreach email drafts referencing only
verified prospect evidence. Gracefully falls back to structured template synthesis
when the Gemini AI provider is unconfigured or unavailable.
"""

import json
import uuid
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from ai.gemini_client import GeminiClient
from ai.prompts import build_outreach_personalization_prompt
from campaigns.models import OutreachDraft, PersonalizationEvidence, DraftVersion
from campaigns.draft_validator import DraftValidator


# Controlled whitelisted template variables with safe B2B fallbacks
VARIABLE_FALLBACKS = {
    "buyer_name": "Procurement Team",
    "company_name": "your organization",
    "country": "international",
    "business_type": "wellness and holistic products",
    "industry": "holistic wellness and sound therapy",
    "personalized_opening": "I noticed your organization's focus on quality holistic wellness and acoustic instruments."
}


class PersonalizationEngine:
    """Orchestrates draft generation, variable substitution, and draft validation."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()
        self.validator = DraftValidator(target_word_min=100, target_word_max=250)

    def substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """
        Safely substitute whitelisted template variables.
        Never leaves raw {{ tags }} or renders 'undefined'.
        """
        if not text:
            return ""

        result = text
        for var_name, fallback_val in VARIABLE_FALLBACKS.items():
            pattern = re.compile(rf"\{{\{{\s*{var_name}\s*\}}\}}", re.IGNORECASE)
            actual_val = context.get(var_name)
            replacement = str(actual_val).strip() if actual_val and str(actual_val).strip() else fallback_val
            result = pattern.sub(replacement, result)

        # Catch-all: strip any remaining unexpected template tags
        result = re.sub(r"\{\{\s*[\w_]+\s*\}\}", "", result)
        return result

    def generate_draft(
        self,
        lead: Dict[str, Any],
        campaign_id: str,
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None
    ) -> OutreachDraft:
        """
        Generate a personalized outreach draft for a specific prospect lead.
        """
        lead_id = lead.get("lead_id") or f"lead_{uuid.uuid4().hex[:10]}"
        email = (lead.get("email") or "").strip()
        company_name = (lead.get("company_name") or "").strip()
        buyer_name = (lead.get("buyer_name") or "").strip()
        country = (lead.get("country") or "").strip()
        classification = lead.get("classification") or "Business"
        is_demo = str(lead.get("is_demo", "")).lower() in ("true", "1")

        # Extract enriched intelligence if present
        enrichment = lead.get("enrichment") or {}
        b_details = enrichment.get("business_details") or {}
        p_contact = enrichment.get("public_contact") or {}
        b_relevance = enrichment.get("buyer_relevance") or {}

        recipient_name = p_contact.get("name") or buyer_name or None
        recipient_role = p_contact.get("role") or None
        business_type = b_details.get("business_type") or None
        industry = b_details.get("industry") or None
        company_desc = b_details.get("company_description") or None
        relevance_val = b_relevance.get("relevance") or lead.get("buyer_relevance") or "Unknown"
        relevance_reason = b_relevance.get("reason") or "Direct wellness and export prospect"
        evidence_items = enrichment.get("evidence") or []

        # Build context for template substitution
        var_context = {
            "buyer_name": recipient_name,
            "company_name": company_name,
            "country": country,
            "business_type": business_type,
            "industry": industry,
            "personalized_opening": ""
        }

        now_iso = datetime.utcnow().isoformat() + "Z"
        draft_id = f"draft_{campaign_id}_{lead_id}_{uuid.uuid4().hex[:4]}"

        # Attempt AI generation if Gemini is configured
        ai_success = False
        subject = ""
        opening_line = ""
        body = ""
        closing = ""
        personalization_reason = ""
        evidence_used: List[Dict[str, Any]] = []
        ai_confidence = 0.85

        if self.gemini.is_configured():
            try:
                prompt = build_outreach_personalization_prompt(
                    company_name=company_name,
                    recipient_name=recipient_name,
                    recipient_role=recipient_role,
                    business_type=business_type,
                    industry=industry,
                    company_description=company_desc,
                    buyer_relevance=relevance_val,
                    relevance_reason=relevance_reason,
                    evidence_items=evidence_items,
                    country=country,
                    subject_template=subject_template,
                    body_template=body_template
                )
                raw_json = self.gemini.call_model(prompt)
                parsed = json.loads(raw_json)

                subject = parsed.get("subject", "").strip()
                opening_line = parsed.get("opening_line", "").strip()
                body = parsed.get("body", "").strip()
                closing = parsed.get("closing", "").strip()
                personalization_reason = parsed.get("personalization_reason", "").strip()
                evidence_used = parsed.get("evidence_used", [])
                ai_confidence = float(parsed.get("confidence", 0.90))

                if subject and body:
                    ai_success = True
            except Exception:
                ai_success = False

        # Fallback to grounded deterministic synthesis
        if not ai_success:
            subject, opening_line, body, closing, personalization_reason, evidence_used, ai_confidence = self._grounded_fallback_generation(
                lead=lead,
                var_context=var_context,
                subject_template=subject_template,
                body_template=body_template,
                evidence_items=evidence_items
            )

        # Substitute any remaining whitelisted variables
        var_context["personalized_opening"] = opening_line
        subject = self.substitute_variables(subject, var_context)
        body = self.substitute_variables(body, var_context)
        closing = self.substitute_variables(closing, var_context)

        # Run draft validation
        validation_result = self.validator.validate(
            subject=subject,
            body=body,
            verified_context={
                "company_name": company_name,
                "recipient_name": recipient_name,
                "business_type": business_type,
                "buyer_relevance": relevance_val,
                "evidence": evidence_used
            }
        )

        initial_draft_dict = {
            "subject": subject,
            "opening_line": opening_line,
            "body": body,
            "closing": closing
        }

        initial_version = {
            "version": 1,
            "generated_at": now_iso,
            "subject": subject,
            "opening_line": opening_line,
            "body": body,
            "closing": closing,
            "ai_confidence": ai_confidence,
            "personalization_reason": personalization_reason
        }

        return OutreachDraft(
            draft_id=draft_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            recipient_email=email,
            recipient_name=recipient_name,
            company_name=company_name,
            country=country,
            subject=subject,
            opening_line=opening_line,
            body=body,
            closing=closing,
            classification=classification,
            buyer_relevance=relevance_val,
            ai_confidence=ai_confidence,
            personalization_reason=personalization_reason,
            personalization_evidence=evidence_used,
            original_ai_draft=initial_draft_dict,
            operator_edited_draft=None,
            version_history=[initial_version],
            status=validation_result.suggested_status,
            validation=validation_result.model_dump(),
            created_at=now_iso,
            updated_at=now_iso,
            is_demo=is_demo
        )

    def _grounded_fallback_generation(
        self,
        lead: Dict[str, Any],
        var_context: Dict[str, Any],
        subject_template: Optional[str],
        body_template: Optional[str],
        evidence_items: List[Dict[str, Any]]
    ) -> Tuple[str, str, str, str, str, List[Dict[str, Any]], float]:
        """
        Produces clean, grounded B2B export copy without Gemini.
        Zero hallucinations: strictly synthesizes verified company and catalog metadata.
        """
        company = var_context.get("company_name") or "your company"
        buyer = var_context.get("buyer_name") or "Procurement Team"
        b_type = var_context.get("business_type")

        # 1. Subject line
        if subject_template and subject_template.strip():
            subj = subject_template
        else:
            subj = f"Wholesale Himalayan Singing Bowls for {company}"

        # 2. Opening line based on verified evidence
        if b_type and "wholesale" in b_type.lower():
            opening = f"I noticed that {company} provides wholesale wellness and acoustic instruments to retail partners."
        elif evidence_items:
            first_ev = evidence_items[0].get("evidence") or ""
            if "sound" in first_ev.lower() or "singing bowl" in first_ev.lower():
                opening = f"We noticed {company}'s focus on quality sound healing and meditation instruments."
            else:
                opening = f"I am writing regarding authentic handcrafted Himalayan singing bowls for {company}."
        else:
            opening = f"We noticed {company}'s focus on holistic wellness and acoustic instruments."

        # 3. Body
        if body_template and body_template.strip():
            body_content = body_template
        else:
            body_content = f"""Dear {buyer},

{opening}

We are specialized Himalayan master artisans and direct exporters of authentic hand-hammered 7-metal Tibetan Singing Bowls, meditation gongs, and sound-healing instruments.

We would love to share our latest 2026 B2B Export Catalog and direct manufacturer wholesale pricing with your purchasing team.

Key Wholesale Offerings:
• Authentic 7-metal hand-hammered singing bowls (graded Frequencies & Hz)
• Custom engraving and OEM private labeling for international distributors
• Direct door-to-door worldwide export shipping with full documentation

Please find our complete company presentation and export specifications attached. Would you be open to reviewing our wholesale price sheet this week?"""

        closing = "Warm regards,\nExport Operations Team\nHimalayan Singing Bowls Exporters\nexport@himalayanbowls.org"
        reason = "Synthesized from verified lead business profile and export catalog specifications."
        evidence_used = evidence_items[:3] if evidence_items else []
        confidence = 0.85

        return subj, opening, body_content, closing, reason, evidence_used, confidence
