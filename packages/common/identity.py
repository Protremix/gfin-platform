# GFIN Identity Provider Abstraction Interface
#
# Layer A (current): Base44IdentityProvider — uses Base44 auth
# Layer B (target):  OIDCIdentityProvider — OIDC/OAuth2 with MFA (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# Per Constitution Article XXVII (Security Supremacy) and Master Spec §45:
# Mandatory: Zero Trust, MFA, OIDC/OAuth2, RBAC, ABAC, least privilege.

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from schemas.enums import DataClassification, UserRole


class AuthContext(BaseModel):
    """Authenticated user context with permissions."""

    user_id: str
    email: str | None = None
    role: UserRole = UserRole.CITIZEN
    organization_id: str | None = None
    jurisdiction: str | None = None
    permissions: list[str] = Field(default_factory=list)
    token_id: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def can_access(self, classification: DataClassification) -> bool:
        """Check if user can access data with given classification."""
        classification_order = {
            DataClassification.PUBLIC: 0,
            DataClassification.COMMUNITY: 1,
            DataClassification.RESTRICTED: 2,
            DataClassification.LAW_ENFORCEMENT: 3,
            DataClassification.HIGHLY_RESTRICTED: 4,
        }
        user_level = {
            UserRole.CITIZEN: 1,
            UserRole.INVESTIGATOR: 3,
            UserRole.ANALYST: 2,
            UserRole.ADMINISTRATOR: 4,
        }
        return classification_order.get(classification, 4) <= user_level.get(self.role, 0)


class IdentityProvider(ABC):
    """Abstract identity provider interface.

    All application code authenticates through this interface.
    The specific adapter (Base44, OIDC/OAuth2) is selected by configuration.
    """

    @abstractmethod
    async def authenticate(self, token: str) -> AuthContext | None:
        """Validate a token and return auth context. Returns None if invalid."""
        ...

    @abstractmethod
    async def authorize(
        self, context: AuthContext, action: str, resource_type: str, resource_classification: DataClassification
    ) -> bool:
        """Check if user is authorized to perform an action on a resource."""
        ...

    @abstractmethod
    async def create_token(self, user_id: str, role: UserRole, organization_id: str | None = None) -> str:
        """Create a new authentication token."""
        ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        ...

    @abstractmethod
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get user details."""
        ...


class Base44IdentityProvider(IdentityProvider):
    """Development adapter — uses Base44 authentication.

    MVP implementation. Production uses OIDC/OAuth2 provider
    with MFA (REQUIRES EXTERNAL INFRASTRUCTURE).
    """

    def __init__(self) -> None:
        self._tokens: dict[str, AuthContext] = {}
        self._users: dict[str, dict[str, Any]] = {}

    async def authenticate(self, token: str) -> AuthContext | None:
        context = self._tokens.get(token)
        if context is None:
            return None
        if context.expires_at and datetime.now(timezone.utc) > context.expires_at:
            del self._tokens[token]
            return None
        return context

    async def authorize(
        self,
        context: AuthContext,
        action: str,
        resource_type: str,
        resource_classification: DataClassification,
    ) -> bool:
        if not context.can_access(resource_classification):
            return False
        if action in ("create", "read", "update", "delete"):
            if context.role == UserRole.CITIZEN and action in ("update", "delete"):
                return False
        return True

    async def create_token(self, user_id: str, role: UserRole, organization_id: str | None = None) -> str:
        from uuid import uuid4

        token = f"tkn-{uuid4().hex}"
        context = AuthContext(
            user_id=user_id,
            role=role,
            organization_id=organization_id,
            token_id=token,
        )
        self._tokens[token] = context
        return token

    async def revoke_token(self, token: str) -> bool:
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._users.get(user_id)
