"""
Centralized prompt templates for Resonance AI Lead Intelligence.
Mandates zero hallucination, factual grounding in provided evidence, and strict JSON schemas.
"""

import json
from typing import Dict, Any, List, Optional


SYSTEM_INTELLIGENCE_INSTRUCTION = """You are an expert B2B sales intelligence analyst for a Himalayan Singing Bowls manufacturing and direct export enterprise.
Your role is to analyze verified, public business information to understand prospective buyers.

CRITICAL RULES - DO NOT DEVIATE:
1. NEVER INVENT OR HALLUCINATE: If a piece of information (such as name, phone, address, job title, or business type) is not explicitly present in the provided source text, output null or 'Unknown'.
2. DO NOT GUESS INTENT: Base your relevance assessments solely on concrete keywords and statements in the text.
3. CONCISE EVIDENCE: For every conclusion, cite a brief, factual quotation or excerpt from the provided text as evidence.
4. STRICT JSON: Respond ONLY with a valid JSON object matching the requested schema. Do not enclose in markdown blocks other than clean json.
"""


def build_classification_prompt(contacts: List[Dict[str, Any]]) -> str:
    """
    Build prompt to classify contacts into Business, Individual, or Unclassified.
    """
    schema_spec = {
        "contacts": [
            {
                "email": "string (matching input)",
                "classification": "Business | Individual | Unclassified",
                "confidence": "number between 0.0 and 1.0",
                "reason": "concise explanation grounded in text",
                "evidence": [
                    {
                        "field": "classification",
                        "evidence": "concise factual quote from input",
                        "confidence": "number between 0.0 and 1.0"
                    }
                ]
            }
        ]
    }

    contacts_json = json.dumps(contacts, indent=2)

    return f"""{SYSTEM_INTELLIGENCE_INSTRUCTION}

TASK: Classify the following contacts into:
- 'Business': Wholesale distributors, acoustic/musical instrument importers, sound therapy academies, yoga/meditation studios, retail boutiques, or commercial wellness centers.
- 'Individual': Private collectors, solo meditation enthusiasts, students, or retail consumers.
- 'Unclassified': Use this when the evidence is ambiguous, missing, or contradictory. Do NOT force uncertain records into Business or Individual.

Output schema:
{json.dumps(schema_spec, indent=2)}

Contacts to classify:
{contacts_json}
"""


def build_enrichment_prompt(
    company_name: str,
    website: str,
    page_texts: Dict[str, str],
    email: Optional[str] = None
) -> str:
    """
    Build prompt to extract factual business capabilities, public contact details,
    and buyer relevance from shallow-crawled website pages.
    """
    # Truncate page texts if very large to respect model token limits
    formatted_pages = []
    for url, text in page_texts.items():
        excerpt = text[:2500].strip()
        formatted_pages.append(f"--- PAGE URL: {url} ---\n{excerpt}")

    combined_text = "\n\n".join(formatted_pages) if formatted_pages else "No website content available."

    schema_spec = {
        "classification": {
            "classification": "Business | Individual | Unclassified",
            "confidence": 0.9,
            "reason": "string",
            "evidence": [{"field": "classification", "evidence": "quote", "confidence": 0.9}]
        },
        "buyer_relevance": {
            "relevance": "High | Medium | Low | Unknown",
            "confidence": 0.85,
            "reason": "string",
            "evidence": [{"field": "buyer_relevance", "evidence": "quote", "confidence": 0.85}]
        },
        "business_details": {
            "company_name": "string or null",
            "business_type": "string or null (e.g., Wholesale Distributor, Retail Store, Yoga Studio, Sound Academy)",
            "industry": "string or null (e.g., Wellness & Sound Healing, Musical Instruments)",
            "company_description": "concise 1-2 sentence description or null",
            "wholesale_available": "boolean or null",
            "confidence": 0.8
        },
        "public_contact": {
            "name": "string or null",
            "role": "Owner | Founder | Director | Procurement | Purchasing | Buyer | Sales | Wholesale | Operations | General Contact | Unknown",
            "phone": "string or null",
            "email": "string or null",
            "address": "string or null",
            "city": "string or null",
            "country": "string or null",
            "confidence": 0.8
        },
        "evidence": [
            {
                "url": "string (URL where evidence was found)",
                "field": "string (field name)",
                "evidence": "concise factual quote from the page",
                "confidence": 0.85
            }
        ]
    }

    return f"""{SYSTEM_INTELLIGENCE_INSTRUCTION}

TARGET PRODUCT CONTEXT:
We manufacture and export hand-hammered Himalayan Tibetan Singing Bowls, meditation gongs, and sound therapy instruments.
Evaluate buyer relevance as:
- 'High': The business explicitly deals in singing bowls, sound therapy/healing, acoustic healing instruments, meditation supplies, or wholesale wellness equipment.
- 'Medium': The business operates in broader yoga, meditation, spiritual goods, musical instruments, or holistic lifestyle retail, but does not explicitly feature singing bowls.
- 'Low': The business is in an unrelated sector with minimal fit (e.g. general tech, logistics, food).
- 'Unknown': Insufficient evidence to judge relevance.

RULES FOR CONTACT DETAILS:
- Only extract public business contact info found directly in the text.
- If no individual person's name is listed, output "name": null and "role": "Unknown".
- If no phone number is found, output "phone": null.
- If no address is found, output "address": null.

COMPANY TO ENRICH:
Company: {company_name or 'Unknown'}
Website: {website or 'None'}
Email: {email or 'None'}

SOURCE WEBPAGES CONTENT:
{combined_text}

OUTPUT STRICT JSON MATCHING THIS SCHEMA:
{json.dumps(schema_spec, indent=2)}
"""


def build_outreach_personalization_prompt(
    company_name: str,
    recipient_name: Optional[str],
    recipient_role: Optional[str],
    business_type: Optional[str],
    industry: Optional[str],
    company_description: Optional[str],
    buyer_relevance: str,
    relevance_reason: str,
    evidence_items: List[Dict[str, Any]],
    country: Optional[str],
    subject_template: Optional[str] = None,
    body_template: Optional[str] = None,
    target_word_min: int = 120,
    target_word_max: int = 220
) -> str:
    """
    Build prompt to generate a grounded, highly professional B2B outreach email draft
    referencing only verified evidence.
    """
    schema_spec = {
        "subject": "Wholesale Singing Bowls for Your Product Range",
        "opening_line": "I noticed that [Company] offers wholesale sound therapy instruments to holistic retailers...",
        "body": "Complete email body including opening line, export value proposition, presentation reference, and clear low-friction next step (120-220 words).",
        "closing": "Warm regards,\nExport Operations Team\nHimalayan Singing Bowls Exporters",
        "personalization_reason": "Based on the company's verified wholesale wellness instrument catalog.",
        "evidence_used": [
            {
                "field": "wholesale_available",
                "url": "https://example.com/wholesale",
                "quote": "Direct quote from source text"
            }
        ],
        "confidence": 0.92
    }

    evidence_summary = []
    for ev in evidence_items[:5]:
        field = ev.get("field", "general")
        quote = ev.get("evidence", ev.get("quote", ""))
        url = ev.get("url", "")
        if quote:
            evidence_summary.append(f"- [{field}] {quote} (Source: {url})")

    evidence_text = "\n".join(evidence_summary) if evidence_summary else "No specific quotes available; rely only on verified business metadata."

    return f"""{SYSTEM_INTELLIGENCE_INSTRUCTION}

You are a senior B2B international export manager representing Himalayan artisan exporters of handcrafted 7-metal Tibetan Singing Bowls, meditation gongs, and sound-healing instruments.

TASK:
Compose a tailored, professional B2B cold outreach email to the prospect below.

VERIFIED PROSPECT CONTEXT (FACTS ONLY):
- Company: {company_name or 'the business'}
- Recipient Name: {recipient_name or 'Procurement / Purchasing Team'}
- Recipient Role: {recipient_role or 'Purchasing / Category Manager'}
- Business Type: {business_type or 'Wellness / Musical Instruments Business'}
- Industry: {industry or 'Holistic Wellness & Sound Healing'}
- Description: {company_description or 'Specialist retailer or distributor'}
- Buyer Relevance: {buyer_relevance} ({relevance_reason})
- Country: {country or 'International'}

VERIFIED SOURCE EVIDENCE QUOTES:
{evidence_text}

REFERENCE TEMPLATES (USE AS GUIDELINES IF HELPFUL):
Subject Template: {subject_template or 'Handcrafted Himalayan Singing Bowls - B2B Wholesale Catalog'}
Body Guidelines: {body_template or 'Introduce our authentic 7-metal singing bowls, mention attached PDF presentation, offer wholesale price list.'}

CRITICAL ANTI-HALLUCINATION & STYLE RULES:
1. NO FABRICATED INTENT: Never say "I saw you are looking for new singing bowl suppliers" or claim they have an active requirement unless source evidence explicitly states it.
2. NO FAKE FAMILIARITY: Do NOT use "I hope this email finds you well" or "I came across your amazing website" or "We are thrilled to reach out".
3. NO SPAM PHRASES: Do NOT use all-caps, multiple exclamation marks, fake urgency ("LIMITED TIME", "ACT NOW"), or fake discounts.
4. SPECIFIC GROUNDING: Use verified facts (e.g. their wholesale model, wellness acoustic focus) to create a respectful, natural opening.
5. CONCISE & COMMERCIAL: Total email length MUST be between {target_word_min} and {target_word_max} words.
6. ATTACHMENT REFERENCE: Reference the attached company presentation and export catalog (`company_presentation.pdf`).
7. NEXT STEP: Provide a clear, low-pressure commercial inquiry (e.g. asking if they are open to reviewing the wholesale export catalog/price sheet).

OUTPUT STRICT JSON MATCHING THIS SCHEMA:
{json.dumps(schema_spec, indent=2)}
"""


def build_draft_validation_prompt(
    draft_subject: str,
    draft_body: str,
    verified_context: Dict[str, Any]
) -> str:
    """
    Build prompt to audit an outreach draft for factual grounding, spam language, and tone.
    """
    schema_spec = {
        "is_grounded": True,
        "word_count": 150,
        "spam_detected": False,
        "tone_appropriate": True,
        "issues": ["List of any detected unsupported claims or stylistic violations"],
        "confidence": 0.95
    }

    return f"""{SYSTEM_INTELLIGENCE_INSTRUCTION}

TASK:
Audit the following B2B email draft against verified prospect context.

EMAIL DRAFT:
Subject: {draft_subject}
Body:
{draft_body}

VERIFIED CONTEXT:
{json.dumps(verified_context, indent=2)}

VALIDATION CHECKS:
1. Is every factual claim supported by the verified context?
2. Did the draft invent current supplier issues, active orders, or budgets?
3. Did it claim a previous conversation or relationship that did not exist?
4. Is it free from spam triggers, excessive punctuation, and hype?
5. Is the tone professional and commercially respectful?

OUTPUT STRICT JSON MATCHING THIS SCHEMA:
{json.dumps(schema_spec, indent=2)}
"""

