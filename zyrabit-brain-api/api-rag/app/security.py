# security.py - Centralized PII sanitization for Zyrabit API

"""Provides a single function `sanitize_pii` that redacts sensitive information.

Supported patterns:
- Email addresses (replaced with "████████")
- Credit‑card numbers (13‑16 digits, allowing spaces or dashes) replaced with "[CREDIT_CARD]"
- Monetary amounts prefixed with $ (e.g., $1,234.56) replaced with "[AMOUNT]"

The function returns a tuple `(clean_text, redacted)` where `redacted` is a boolean indicating
whether any replacement occurred.
"""

import re
from typing import Tuple

# Pre‑compiled regex patterns for performance
_EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+")
_CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_AMOUNT_REGEX = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?")


def sanitize_pii(text: str) -> Tuple[str, bool]:
    """Redact PII in *text*.

    Returns:
        (clean_text, redacted)
        - *clean_text*: the sanitized string.
        - *redacted*: ``True`` if any substitution was performed.
    """
    original = text
    # Apply replacements
    text = _EMAIL_REGEX.sub("████████", text)
    text = _CREDIT_CARD_REGEX.sub("[CREDIT_CARD]", text)
    text = _AMOUNT_REGEX.sub("[AMOUNT]", text)
    redacted = text != original
    return text, redacted

# Export name for convenient import
__all__ = ["sanitize_pii"]
