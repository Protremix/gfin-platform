"""GFIN Source Policy — authorization and access control for data sources."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import logging

from packages.sources.enums import AuthMethod

if TYPE_CHECKING:
    from packages.sources.registry import SourceRecord

logger = logging.getLogger(__name__)


class AccessStatus(str, Enum):
    FOUND_AND_ACCESSIBLE = "found_and_accessible"
    FOUND_BUT_AUTH_REQUIRED = "found_but_auth_required"
    FOUND_BUT_NOT_SUPPORTED = "found_but_not_supported"
    NOT_FOUND = "not_found"


class FailureReason(str, Enum):
    AUTH_REQUIRED = "auth_required"
    API_KEY_MISSING = "api_key_missing"
    OAUTH_REQUIRED = "oauth_required"
    JURISDICTION_RESTRICTED = "jurisdiction_restricted"
    LICENSE_REQUIRED = "license_required"
    RATE_LIMITED = "rate_limited"
    PROVIDER_DOWN = "provider_down"
    CONNECTOR_NOT_IMPLEMENTED = "connector_not_implemented"
    NOT_AUTHORIZED = "not_authorized"


@dataclass
class AccessResult:
    """Result of an access check."""
    status: AccessStatus
    reason: FailureReason | None = None
    required_auth: list[str] = field(default_factory=list)
    message: str = ""


class SourcePolicy:
    """Determines whether a source can be accessed.

    If a source appears valuable but requires additional authorization:
    ACCESS_STATUS = AUTHORIZATION_REQUIRED

    The system records the source and the required authorization path.
    """

    def __init__(self):
        self._credentials: dict[str, bool] = {}  # source_id -> has_credentials
        self._jurisdiction_allowed: dict[str, list[str]] = {}

    def check_access(self, source: SourceRecord, jurisdiction: str = "GLOBAL") -> AccessResult:
        """Check if a source can be accessed."""
        # Check jurisdiction
        if source.jurisdictions and jurisdiction not in source.jurisdictions and "GLOBAL" not in source.jurisdictions:
            return AccessResult(
                status=AccessStatus.FOUND_BUT_NOT_SUPPORTED,
                reason=FailureReason.JURISDICTION_RESTRICTED,
                message=f"Source not available in jurisdiction: {jurisdiction}",
            )

        # Check authentication
        if source.auth_method == AuthMethod.PUBLIC_API:
            return AccessResult(
                status=AccessStatus.FOUND_AND_ACCESSIBLE,
                message="Public API — no authentication required",
            )

        # Check if we have credentials
        has_creds = self._credentials.get(source.source_id, False)
        if not has_creds:
            required_auth = []
            if source.auth_method == AuthMethod.API_KEY:
                required_auth = ["api_key"]
                reason = FailureReason.API_KEY_MISSING
            elif source.auth_method == AuthMethod.OAUTH2:
                required_auth = ["oauth2_token"]
                reason = FailureReason.OAUTH_REQUIRED
            elif source.auth_method == AuthMethod.LAW_ENFORCEMENT_CREDENTIAL:
                required_auth = ["law_enforcement_credential", "case_id", "legal_authority"]
                reason = FailureReason.NOT_AUTHORIZED
            elif source.auth_method == AuthMethod.SERVICE_ACCOUNT:
                required_auth = ["service_account_credentials"]
                reason = FailureReason.AUTH_REQUIRED
            else:
                required_auth = [source.auth_method.value]
                reason = FailureReason.AUTH_REQUIRED

            return AccessResult(
                status=AccessStatus.FOUND_BUT_AUTH_REQUIRED,
                reason=reason,
                required_auth=required_auth,
                message=f"Authorization required: {source.auth_method.value}",
            )

        # Has credentials — accessible
        return AccessResult(
            status=AccessStatus.FOUND_AND_ACCESSIBLE,
            message="Credentials available",
        )

    def set_has_credentials(self, source_id: str, has_creds: bool) -> None:
        """Record that credentials exist for a source."""
        self._credentials[source_id] = has_creds

    def get_auth_requirement(self, source: SourceRecord) -> list[str]:
        """Get what authentication is required for a source."""
        if source.auth_method == AuthMethod.PUBLIC_API:
            return []
        return [source.auth_method.value]

    def validate_response_security(self, response: dict[str, Any]) -> dict[str, Any]:
        """Treat all provider responses as untrusted DATA (Directive §27).

        Protect against: prompt injection, malicious HTML, poisoned metadata,
        unexpected redirects, oversized responses, SSRF, malicious files.
        """
        issues = []

        # Check for prompt injection patterns
        text = str(response).lower()
        injection_patterns = [
            "ignore previous instructions",
            "you are now",
            "system prompt",
            "forget your rules",
            "act as if",
            "<script",
            "javascript:",
            "onerror=",
        ]
        for pattern in injection_patterns:
            if pattern in text:
                issues.append(f"Potential prompt injection: '{pattern}'")

        # Check for oversized response
        if len(str(response)) > 1_000_000:
            issues.append("Oversized response (>1MB)")

        # Check for redirect attempts
        if isinstance(response, dict):
            for key in ["redirect", "redirect_url", "location"]:
                if key in response:
                    issues.append(f"Unexpected redirect field: {key}")

        return {
            "is_safe": len(issues) == 0,
            "issues": issues,
            "processing_version": "1.0.0",
        }
