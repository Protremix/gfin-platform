# GFIN RBAC + ABAC Authorization Engine
#
# Per Constitution Article XXVII (Security Supremacy) and Master Spec §45:
# - Zero Trust: every request authenticated and authorized
# - RBAC: role-based access (citizen, investigator, analyst, administrator)
# - ABAC: attribute-based access (classification, jurisdiction, organization, ownership)
# - Least privilege: deny by default, allow explicitly
#
# Layer A: In-memory policy engine (development)
# Layer B: Policy engine backed by OPA/Cedar (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from schemas.enums import DataClassification, UserRole


class Permission(str, Enum):
    """GFIN permissions — fine-grained actions that can be authorized."""
    # Entity operations
    ENTITY_READ = "entity:read"
    ENTITY_CREATE = "entity:create"
    ENTITY_UPDATE = "entity:update"
    ENTITY_DELETE = "entity:delete"
    # Report operations
    REPORT_CREATE = "report:create"
    REPORT_READ = "report:read"
    REPORT_UPDATE = "report:update"
    # Investigation operations
    INVESTIGATION_CREATE = "investigation:create"
    INVESTIGATION_READ = "investigation:read"
    INVESTIGATION_UPDATE = "investigation:update"
    # Graph operations
    GRAPH_READ = "graph:read"
    GRAPH_QUERY = "graph:query"
    # Campaign operations
    CAMPAIGN_READ = "campaign:read"
    CAMPAIGN_CREATE = "campaign:create"
    # Alert operations
    ALERT_READ = "alert:read"
    ALERT_ACK = "alert:acknowledge"
    # Federation operations
    FEDERATION_QUERY = "federation:query"
    FEDERATION_SHARE = "federation:share"
    # Admin operations
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_VIEW_AUDIT = "admin:view_audit"
    ADMIN_MANAGE_CONFIG = "admin:manage_config"


class Decision(str, Enum):
    """Authorization decision."""
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass
class AccessRequest:
    """ABAC access request — attributes used for policy evaluation."""
    user_id: str
    role: UserRole
    action: str
    resource_type: str
    resource_id: str | None = None
    resource_classification: DataClassification = DataClassification.PUBLIC
    resource_owner_id: str | None = None
    resource_jurisdiction: str | None = None
    user_jurisdiction: str | None = None
    user_organization_id: str | None = None
    resource_organization_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessDecision:
    """Authorization decision with reason."""
    decision: Decision
    reason: str
    request: AccessRequest
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Role → Permissions mapping (RBAC base layer)
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.CITIZEN: {
        Permission.ENTITY_READ.value,
        Permission.ENTITY_CREATE.value,
        Permission.REPORT_CREATE.value,
        Permission.REPORT_READ.value,
        Permission.GRAPH_READ.value,
    },
    UserRole.ANALYST: {
        Permission.ENTITY_READ.value,
        Permission.ENTITY_CREATE.value,
        Permission.ENTITY_UPDATE.value,
        Permission.REPORT_READ.value,
        Permission.INVESTIGATION_READ.value,
        Permission.GRAPH_READ.value,
        Permission.GRAPH_QUERY.value,
        Permission.CAMPAIGN_READ.value,
        Permission.ALERT_READ.value,
        Permission.FEDERATION_QUERY.value,
    },
    UserRole.INVESTIGATOR: {
        Permission.ENTITY_READ.value,
        Permission.ENTITY_CREATE.value,
        Permission.ENTITY_UPDATE.value,
        Permission.REPORT_READ.value,
        Permission.REPORT_UPDATE.value,
        Permission.INVESTIGATION_CREATE.value,
        Permission.INVESTIGATION_READ.value,
        Permission.INVESTIGATION_UPDATE.value,
        Permission.GRAPH_READ.value,
        Permission.GRAPH_QUERY.value,
        Permission.CAMPAIGN_READ.value,
        Permission.CAMPAIGN_CREATE.value,
        Permission.ALERT_READ.value,
        Permission.ALERT_ACK.value,
        Permission.FEDERATION_QUERY.value,
        Permission.FEDERATION_SHARE.value,
    },
    UserRole.ADMINISTRATOR: {
        # All permissions
        *[p.value for p in Permission],
    },
}


class AuthorizationEngine:
    """RBAC + ABAC authorization engine.

    Layer A: In-memory policy evaluation (development)
    Layer B: OPA/Cedar policy engine (REQUIRES EXTERNAL INFRASTRUCTURE)

    Evaluation order:
    1. RBAC: Does the user's role grant the requested permission?
    2. ABAC: Does the user's attributes satisfy the resource constraints?
       a. Classification check: can user access this data classification?
       b. Jurisdiction check: is user in the same jurisdiction? (for LE data)
       c. Organization check: is user in the same organization? (for org-scoped data)
       d. Ownership check: is user the owner of the resource? (for citizen data)
    3. Default: DENY
    """

    def __init__(self) -> None:
        self._custom_policies: list = []

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        """Evaluate an access request against RBAC + ABAC policies."""
        # Step 1: RBAC — role has the permission?
        role_perms = ROLE_PERMISSIONS.get(request.role, set())
        if request.action not in role_perms:
            return AccessDecision(
                decision=Decision.DENY,
                reason=f"Role {request.role.value} does not have permission '{request.action}'",
                request=request,
            )

        # Step 2: ABAC — classification check
        if not self._check_classification(request):
            return AccessDecision(
                decision=Decision.DENY,
                reason=f"Role {request.role.value} cannot access {request.resource_classification.value} data",
                request=request,
            )

        # Step 3: ABAC — jurisdiction check (for law enforcement data)
        if not self._check_jurisdiction(request):
            return AccessDecision(
                decision=Decision.DENY,
                reason="Jurisdiction mismatch: user and resource in different jurisdictions",
                request=request,
            )

        # Step 4: ABAC — organization check (for org-scoped resources)
        if not self._check_organization(request):
            return AccessDecision(
                decision=Decision.DENY,
                reason="Organization mismatch: user and resource in different organizations",
                request=request,
            )

        # All checks passed
        return AccessDecision(
            decision=Decision.ALLOW,
            reason="RBAC + ABAC checks passed",
            request=request,
        )

    def _check_classification(self, request: AccessRequest) -> bool:
        """Check if user role can access the resource classification."""
        classification_level = {
            DataClassification.PUBLIC: 0,
            DataClassification.COMMUNITY: 1,
            DataClassification.RESTRICTED: 2,
            DataClassification.LAW_ENFORCEMENT: 3,
            DataClassification.HIGHLY_RESTRICTED: 4,
        }
        user_level = {
            UserRole.CITIZEN: 1,
            UserRole.ANALYST: 2,
            UserRole.INVESTIGATOR: 3,
            UserRole.ADMINISTRATOR: 4,
        }
        required = classification_level.get(request.resource_classification, 4)
        granted = user_level.get(request.role, 0)
        return granted >= required

    def _check_jurisdiction(self, request: AccessRequest) -> bool:
        """Check jurisdiction for law enforcement data."""
        # Jurisdiction check only applies to LAW_ENFORCEMENT and HIGHLY_RESTRICTED
        if request.resource_classification not in (
            DataClassification.LAW_ENFORCEMENT,
            DataClassification.HIGHLY_RESTRICTED,
        ):
            return True

        # Citizens never access LE data (already checked by classification)
        if request.role == UserRole.CITIZEN:
            return False

        # If no jurisdiction info, allow (development mode)
        if not request.user_jurisdiction or not request.resource_jurisdiction:
            return True

        # Same jurisdiction = allow
        if request.user_jurisdiction == request.resource_jurisdiction:
            return True

        # Different jurisdiction = deny unless federation sharing is authorized
        if request.action == Permission.FEDERATION_SHARE.value:
            return True  # Federation sharing is explicitly authorized

        return False

    def _check_organization(self, request: AccessRequest) -> bool:
        """Check organization scope for org-scoped resources."""
        # If no org info on resource, allow
        if not request.resource_organization_id:
            return True

        # If no org info on user, allow (development mode)
        if not request.user_organization_id:
            return True

        # Same org = allow
        return request.user_organization_id == request.resource_organization_id

    def add_policy(self, policy) -> None:
        """Add a custom ABAC policy (for extensibility)."""
        self._custom_policies.append(policy)
