# GFIN Input Validation — Sanitization and Injection Prevention
#
# Per Constitution Article XXVII and Master Spec §45:
# "Treat all external content as untrusted."
# Protect against: XSS, SQL injection, NoSQL injection, prompt injection,
# path traversal, command injection, and malformed input.
#
# This module provides validation and sanitization utilities for all
# user-submitted and external content.

from __future__ import annotations

import html
import re
from typing import Any

import structlog

logger = structlog.get_logger("gfin.validation")

# Maximum input sizes (Layer A development defaults)
MAX_STRING_LENGTH = 10_000
MAX_TEXT_LENGTH = 50_000
MAX_PHONE_LENGTH = 30
MAX_EMAIL_LENGTH = 320
MAX_URL_LENGTH = 2_048
MAX_DOMAIN_LENGTH = 253

# Dangerous patterns to detect
SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|alter|create|exec)\b.*\b(from|into|table|database)\b)",
    r"(--\s|\/\*|\*\/|;.*--)",
    r"(\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b)",
    r"('\s*or\s*'?1'?\s*=\s*'?1|'\s*or\s*1\s*=\s*1)",
    r"(\bwaitfor\s+delay\b|\bsleep\s*\()",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c",
]

PROMPT_INJECTION_PATTERNS = [
    r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions)",
    r"(disregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts))",
    r"(you\s+are\s+(now|actually)\s+(a|an)\s+)",
    r"(act\s+as\s+(if|a)\s+)",
    r"(system\s*:\s*|assistant\s*:\s*|user\s*:\s*)",
]

COMPILED_SQL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
COMPILED_PATH_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
COMPILED_PROMPT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]


class ValidationError(Exception):
    """Input validation error."""

    def __init__(self, field: str, reason: str, value: str = ""):
        self.field = field
        self.reason = reason
        self.value = value[:100]  # Never log full input
        super().__init__(f"Validation error on '{field}': {reason}")


class ValidationResult:
    """Result of input validation."""

    def __init__(
        self, is_valid: bool, sanitized_value: Any = None, warnings: list[str] | None = None
    ):
        self.is_valid = is_valid
        self.sanitized_value = sanitized_value
        self.warnings = warnings or []


def validate_string(
    value: str, max_length: int = MAX_STRING_LENGTH, field_name: str = "input"
) -> ValidationResult:
    """Validate and sanitize a string input."""
    if not isinstance(value, str):
        raise ValidationError(field_name, "Expected string", str(type(value)))

    if len(value) > max_length:
        raise ValidationError(field_name, f"Exceeds max length {max_length}", str(len(value)))

    # Check for SQL injection patterns
    for pattern in COMPILED_SQL_PATTERNS:
        if pattern.search(value):
            logger.warning("sql_injection_detected", field=field_name)
            raise ValidationError(field_name, "Potential SQL injection detected")

    # Check for path traversal
    for pattern in COMPILED_PATH_PATTERNS:
        if pattern.search(value):
            logger.warning("path_traversal_detected", field=field_name)
            raise ValidationError(field_name, "Path traversal detected")

    # HTML-escape the value to prevent XSS
    sanitized = html.escape(value, quote=True)

    return ValidationResult(is_valid=True, sanitized_value=sanitized)


def validate_phone(phone: str, field_name: str = "phone") -> ValidationResult:
    """Validate a phone number."""
    if not phone:
        raise ValidationError(field_name, "Phone number is required")

    if len(phone) > MAX_PHONE_LENGTH:
        raise ValidationError(field_name, f"Phone exceeds {MAX_PHONE_LENGTH} chars")

    # Allow +, digits, spaces, dashes, parens
    if not re.match(r"^[\+]?[\d\s\-\(\)]+$", phone):
        raise ValidationError(field_name, "Invalid phone format")

    # Normalize: extract digits and leading +
    normalized = re.sub(r"[\s\-\(\)]", "", phone)
    return ValidationResult(is_valid=True, sanitized_value=normalized)


def validate_email(email: str, field_name: str = "email") -> ValidationResult:
    """Validate an email address."""
    if not email:
        raise ValidationError(field_name, "Email is required")

    if len(email) > MAX_EMAIL_LENGTH:
        raise ValidationError(field_name, f"Email exceeds {MAX_EMAIL_LENGTH} chars")

    # Basic email pattern
    if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        raise ValidationError(field_name, "Invalid email format")

    # Check for SQL injection
    for pattern in COMPILED_SQL_PATTERNS:
        if pattern.search(email):
            raise ValidationError(field_name, "Potential injection in email")

    return ValidationResult(is_valid=True, sanitized_value=email.lower().strip())


def validate_url(url: str, field_name: str = "url") -> ValidationResult:
    """Validate a URL."""
    if not url:
        raise ValidationError(field_name, "URL is required")

    if len(url) > MAX_URL_LENGTH:
        raise ValidationError(field_name, f"URL exceeds {MAX_URL_LENGTH} chars")

    # Must start with http(s)://
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValidationError(field_name, "URL must start with http:// or https://")

    # Check for path traversal
    for pattern in COMPILED_PATH_PATTERNS:
        if pattern.search(url):
            raise ValidationError(field_name, "Path traversal in URL")

    # Check for SQL injection
    for pattern in COMPILED_SQL_PATTERNS:
        if pattern.search(url):
            raise ValidationError(field_name, "Potential injection in URL")

    return ValidationResult(is_valid=True, sanitized_value=url.strip())


def validate_domain(domain: str, field_name: str = "domain") -> ValidationResult:
    """Validate a domain name."""
    if not domain:
        raise ValidationError(field_name, "Domain is required")

    if len(domain) > MAX_DOMAIN_LENGTH:
        raise ValidationError(field_name, f"Domain exceeds {MAX_DOMAIN_LENGTH} chars")

    # Valid domain pattern
    if not re.match(
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)+$",
        domain,
    ):
        raise ValidationError(field_name, "Invalid domain format")

    return ValidationResult(is_valid=True, sanitized_value=domain.lower().strip())


def detect_prompt_injection(text: str) -> list[str]:
    """Detect potential prompt injection patterns in text.

    Returns list of detected patterns (empty = clean).
    Used when passing external content to AI models.
    """
    detections = []
    for pattern in COMPILED_PROMPT_PATTERNS:
        match = pattern.search(text)
        if match:
            detections.append(match.group(0))
            logger.warning(
                "prompt_injection_detected",
                pattern=match.group(0)[:50],
            )
    return detections


def sanitize_for_ai(text: str) -> str:
    """Sanitize text before passing to AI model.

    Escapes HTML and wraps content to clearly mark it as data.
    """
    escaped = html.escape(text, quote=True)
    return f"[USER_DATA_START]\n{escaped}\n[USER_DATA_END]"
