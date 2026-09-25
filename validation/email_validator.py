"""
Email Validation Module for Resonance.
Categorizes email addresses into VALID, REVIEW, MISSING, and INVALID.
Ensures questionable or missing emails are retained for review rather than silently discarded.
"""

import re
from typing import Tuple

# RFC 5322 compliant email regex pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Known placeholder or test domains
PLACEHOLDER_DOMAINS = {
    "example.com", "example.org", "test.com", "sample.com",
    "domain.com", "yourcompany.com", "email.com", "mail.com", "unknown.com"
}

# Disposable / temporary webmail domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "throwawaymail.com", "trashmail.com"
}

DISALLOWED_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff",
    ".js", ".css", ".mp4", ".mp3", ".pdf", ".zip", ".tar", ".gz"
)


class EmailValidator:
    @staticmethod
    def validate(email: str) -> Tuple[bool, str, str]:
        """
        Validate an email address.
        Returns:
            (is_acceptable: bool, status: str, reason: str)
            status is strictly one of: 'Valid', 'Review', 'Missing', 'Invalid'.
        """
        if email is None or not isinstance(email, str) or not email.strip():
            return False, "Missing", "No email address extracted; record retained for review"

        email = email.strip()

        # Check basic length constraints
        if len(email) < 5 or len(email) > 254:
            return False, "Invalid", "Overall email length out of bounds"

        # Check for image or asset extension accidentally parsed
        email_lower = email.lower()
        for ext in DISALLOWED_EXTENSIONS:
            if email_lower.endswith(ext):
                return False, "Invalid", f"Contains file extension {ext}"

        # Must contain exactly one @ symbol
        parts = email.split("@")
        if len(parts) != 2:
            return False, "Invalid", "Must contain exactly one '@' symbol"

        local_part, domain_part = parts

        if not local_part or not domain_part:
            return False, "Invalid", "Local part or domain part is missing"

        if len(domain_part) > 50:
            return False, "Invalid", "Domain part exceeds 50 characters"

        # Domain must contain a dot
        if "." not in domain_part:
            return False, "Invalid", "Domain missing TLD dot"

        # Check regex syntax
        if not EMAIL_REGEX.match(email):
            return False, "Invalid", "Regex syntax check failed"

        # Check placeholder domains
        if domain_part.lower() in PLACEHOLDER_DOMAINS:
            return False, "Review", f"Common placeholder domain '{domain_part}'"

        # Check disposable domains
        if domain_part.lower() in DISPOSABLE_DOMAINS:
            return False, "Review", f"Disposable email provider '{domain_part}'"

        # Check generic contact addresses (valid, but flagged as generic for review)
        generic_prefixes = ("info@", "contact@", "support@", "admin@", "sales@", "hello@", "office@", "inquiry@")
        if any(email_lower.startswith(prefix) for prefix in generic_prefixes):
            return True, "Valid", "Generic business department address"

        return True, "Valid", "Passed RFC syntax and domain checks"


def validate_email(email: str) -> Tuple[bool, str, str]:
    """Convenience helper function."""
    return EmailValidator.validate(email)
