"""PII redaction and input sanitization utilities.

Per Luna Directive — Focus Area 2: Redaction and sanitization logic.
"""

from __future__ import annotations

import re

# PII patterns
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b")
SSN_RE = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")

# Dangerous input patterns
SQL_INJECTION_RE = re.compile(
    r"(?i)(\b(union|select|insert|update|delete|drop|create|alter|exec|script)\b.*\b(from|into|table|database|where)\b)",
    re.IGNORECASE,
)
XSS_RE = re.compile(r"<[^>]*script[^>]*>|<[^>]*on\w+\s*=", re.IGNORECASE)
PATH_TRAVERSAL_RE = re.compile(r"\.\./|\.\.\\|/etc/passwd|/etc/shadow|c:\\windows", re.IGNORECASE)
NULL_BYTE_RE = re.compile(r"\x00")


def redact_pii(text: str) -> str:
    """Redact PII (emails, phones, SSNs, credit cards) from text."""
    text = EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    text = PHONE_RE.sub("[PHONE_REDACTED]", text)
    text = SSN_RE.sub("[SSN_REDACTED]", text)
    text = CREDIT_CARD_RE.sub("[CARD_REDACTED]", text)
    return text


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    # Remove null bytes
    text = NULL_BYTE_RE.sub("", text)
    # Escape HTML/XML special chars
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    # Remove path traversal patterns
    text = PATH_TRAVERSAL_RE.sub("", text)
    return text


def detect_injection(text: str) -> list[str]:
    """Detect potential injection attempts in input.

    Returns list of detected attack types.
    """
    threats: list[str] = []
    if SQL_INJECTION_RE.search(text):
        threats.append("SQL_INJECTION")
    if XSS_RE.search(text):
        threats.append("XSS")
    if PATH_TRAVERSAL_RE.search(text):
        threats.append("PATH_TRAVERSAL")
    if NULL_BYTE_RE.search(text):
        threats.append("NULL_BYTE")
    return threats


def validate_phone_format(phone: str) -> bool:
    """Validate phone number format (E.164 or common formats)."""
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)
    return bool(re.match(r"^\+?\d{7,15}$", cleaned))


def validate_email_format(email: str) -> bool:
    """Validate email format."""
    return bool(EMAIL_RE.match(email))


def validate_domain_format(domain: str) -> bool:
    """Validate domain name format."""
    return bool(re.match(r"^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$", domain))


def validate_url_format(url: str) -> bool:
    """Validate URL format."""
    return bool(re.match(r"^https?://[^\s]+$", url, re.IGNORECASE))


def validate_crypto_address(address: str, chain: str = "bitcoin") -> bool:
    """Validate cryptocurrency address format."""
    if chain == "bitcoin":
        return bool(re.match(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", address))
    elif chain == "ethereum":
        return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))
    return len(address) > 10
