# GFIN Auth Middleware — FastAPI dependency injection

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.identity import AuthContext, Base44IdentityProvider, IdentityProvider
from schemas.enums import DataClassification, UserRole

# Default identity provider — production would inject OIDC provider
_identity_provider: IdentityProvider = Base44IdentityProvider()

security_scheme = HTTPBearer(auto_error=False)


def get_identity_provider() -> IdentityProvider:
    """Get the configured identity provider."""
    return _identity_provider


def set_identity_provider(provider: IdentityProvider) -> None:
    """Override the identity provider (for testing)."""
    global _identity_provider
    _identity_provider = provider


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthContext:
    """FastAPI dependency: extract and validate auth context from token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    provider = get_identity_provider()
    context = await provider.authenticate(credentials.credentials)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return context


async def require_role(*roles: UserRole):
    """FastAPI dependency factory: require one of the specified roles."""

    async def _check(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if context.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {context.role} not authorized. Required: {', '.join(r.value for r in roles)}",
            )
        return context

    return _check


async def require_classification_access(
    classification: DataClassification,
    context: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """FastAPI dependency: require access to a data classification level."""
    if not context.can_access(classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to {classification} data requires elevated permissions",
        )
    return context


class AuthMiddleware:
    """Authentication middleware container for app setup."""

    def __init__(self, provider: IdentityProvider | None = None) -> None:
        if provider is not None:
            set_identity_provider(provider)
