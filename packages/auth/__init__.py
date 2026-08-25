# GFIN Auth — Package Exports

from auth.audit import AuditEvent, AuditEventType, AuditLog
from auth.middleware import (
    AuthMiddleware,
    get_auth_context,
    get_identity_provider,
    require_classification_access,
    require_role,
    set_identity_provider,
)
from auth.rate_limit import RateLimiter
from auth.rbac import (
    AccessDecision,
    AccessRequest,
    AuthorizationEngine,
    Decision,
    Permission,
    ROLE_PERMISSIONS,
)
from auth.validation import (
    ValidationError,
    ValidationResult,
    detect_prompt_injection,
    sanitize_for_ai,
    validate_domain,
    validate_email,
    validate_phone,
    validate_string,
    validate_url,
)

__all__ = [
    "AccessDecision",
    "AccessRequest",
    "AuditEvent",
    "AuditEventType",
    "AuditLog",
    "AuthMiddleware",
    "AuthorizationEngine",
    "Decision",
    "Permission",
    "RateLimiter",
    "ROLE_PERMISSIONS",
    "ValidationError",
    "ValidationResult",
    "detect_prompt_injection",
    "get_auth_context",
    "get_identity_provider",
    "require_classification_access",
    "require_role",
    "sanitize_for_ai",
    "set_identity_provider",
    "validate_domain",
    "validate_email",
    "validate_phone",
    "validate_string",
    "validate_url",
]
