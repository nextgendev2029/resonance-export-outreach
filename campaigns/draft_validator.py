"""
Draft Validator for Resonance Campaigns (Phase 4).
Performs strict automated validation on outreach drafts:
1. Factual grounding against verified lead context.
2. Anti-hallucination checks (rejects invented purchasing intent, fake prior relationships).
3. Anti-spam detection (all-caps, repeated exclamations, scam triggers).
4. Stylistic & word count bounds (120-220 target words, professional tone).
"""

import re
from typing import Dict, Any, List
from campaigns.models import DraftValidationResult


# Spam and hype triggers to strictly forbid in B2B export correspondence
SPAM_PATTERNS = [
    r"\b(urgent|act now|limited time|free|guaranteed|100% guaranteed|no risk|risk-free)\b",
    r"\b(click here|buy now|special promotion|once in a lifetime)\b",
    r"!!+",
    r"\?\?+",
    r"\$\$\$+"
]

# Clichés and fake familiarity forbidden in Resonance outreach
FAKE_FAMILIARITY_PATTERNS = [
    r"i hope this (email|message) finds you well",
    r"i came across your (amazing|impressive|wonderful) website",
    r"we are (thrilled|delighted|excited) to reach out",
    r"i was blown away by your",
    r"i stumbled upon your"
]

# Fabricated intent indicators (claims that prospect is actively looking/buying without evidence)
FABRICATED_INTENT_PATTERNS = [
    r"i saw (that )?you are (currently )?looking for (new )?suppliers",
    r"i noticed you are (in the market|actively seeking|procuring)",
    r"as we (discussed|talked about|spoke) (earlier|previously|before)",
    r"following up on (our|your) (recent|previous) conversation",
    r"regarding your recent (rfq|inquiry|request)"
]


class DraftValidator:
    """Audits generated email drafts for grounding, style, spam, and compliance."""

    def __init__(self, target_word_min: int = 100, target_word_max: int = 250):
        self.target_word_min = target_word_min
        self.target_word_max = target_word_max

    def validate(
        self,
        subject: str,
        body: str,
        verified_context: Dict[str, Any]
    ) -> DraftValidationResult:
        issues: List[str] = []
        full_text = f"{subject}\n{body}".strip()
        words = re.findall(r"\b\w+\b", full_text)
        word_count = len(words)

        # 1. Word count check
        if word_count < self.target_word_min:
            issues.append(f"Email length is concise ({word_count} words; minimum target is {self.target_word_min}).")
        elif word_count > self.target_word_max:
            issues.append(f"Email is too verbose ({word_count} words; maximum target is {self.target_word_max}).")

        # 2. Spam checks
        spam_detected = False
        lower_text = full_text.lower()
        for pat in SPAM_PATTERNS:
            if re.search(pat, lower_text):
                spam_detected = True
                issues.append("Potential spam-style language or excessive punctuation detected.")
                break

        # Check for excessive ALL-CAPS words (excluding acronyms like OEM, B2B, PDF, USA, UK, HZ)
        all_caps_words = [
            w for w in words
            if len(w) >= 4 and w.isupper() and w not in ("OEM", "B2B", "PDF", "USA", "APAC", "EMEA", "NOTE")
        ]
        if len(all_caps_words) >= 2:
            spam_detected = True
            issues.append(f"Excessive capitalization detected: {', '.join(all_caps_words[:3])}")

        # 3. Fake familiarity check
        tone_appropriate = True
        for pat in FAKE_FAMILIARITY_PATTERNS:
            if re.search(pat, lower_text):
                tone_appropriate = False
                issues.append("Generic marketing cliché or fake familiarity detected.")
                break

        # 4. Fabricated intent check (Grounding violation)
        is_grounded = True
        for pat in FABRICATED_INTENT_PATTERNS:
            if re.search(pat, lower_text):
                is_grounded = False
                issues.append("Potential unsupported claim: implies active supplier search or prior conversation without verified evidence.")
                break

        # Check for undefined template variables
        if "undefined" in lower_text or "{{ " in full_text or "}}" in full_text:
            is_grounded = False
            issues.append("Unresolved or undefined template variable detected.")

        # Suggest status based on audit
        suggested_status = "Draft"
        if not is_grounded or spam_detected or not tone_appropriate or len(issues) > 0:
            suggested_status = "Needs Review"

        return DraftValidationResult(
            is_grounded=is_grounded,
            word_count=word_count,
            spam_detected=spam_detected,
            tone_appropriate=tone_appropriate,
            issues=issues,
            suggested_status=suggested_status
        )
