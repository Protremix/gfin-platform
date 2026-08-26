"""GFIN Compliance — Module 33.

Data classification enforcement, privacy controls, retention policies, and
audit compliance. Per Privacy Model: 5 classification levels govern access
and sharing.

Layer A: In-memory compliance checks and filtering
Layer B: Legal framework integration, automated enforcement (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    COMMUNITY = "COMMUNITY"
    LAW_ENFORCEMENT = "LAW_ENFORCEMENT"
    RESTRICTED = "RESTRICTED"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


class AccessorRole(str, Enum):
    PUBLIC = "PUBLIC"
    CITIZEN = "CITIZEN"
    POLICE_OFFICER = "POLICE_OFFICER"
    POLICE_SUPERVISOR = "POLICE_SUPERVISOR"
    POLICE_ADMIN = "POLICE_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


# Classification hierarchy: higher number = more restricted
CLASSIFICATION_LEVEL: dict[str, int] = {
    DataClassification.PUBLIC.value: 1,
    DataClassification.COMMUNITY.value: 2,
    DataClassification.LAW_ENFORCEMENT.value: 3,
    DataClassification.RESTRICTED.value: 4,
    DataClassification.HIGHLY_RESTRICTED.value: 5,
}

# Role clearance level
ROLE_CLEARANCE: dict[str, int] = {
    AccessorRole.PUBLIC.value: 1,
    AccessorRole.CITIZEN.value: 2,
    AccessorRole.POLICE_OFFICER.value: 3,
    AccessorRole.POLICE_SUPERVISOR.value: 4,
    AccessorRole.POLICE_ADMIN.value: 5,
    AccessorRole.SYSTEM_ADMIN.value: 5,
}


# ─── Models ───


class RetentionPolicy(BaseModel):
    """Data retention policy by classification."""

    classification: str
    retention_days: int
    description: str = ""
    auto_delete: bool = False


class ComplianceCheck(BaseModel):
    """Result of a compliance access check."""

    id: str
    accessor_role: str
    data_classification: str
    allowed: bool
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ComplianceViolation(BaseModel):
    """A recorded compliance violation."""

    id: str
    accessor_role: str
    accessor_id: str = ""
    data_classification: str
    resource_type: str = ""
    resource_id: str = ""
    violation_type: str = ""
    details: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False
    resolved_at: datetime | None = None

    def resolve(self) -> None:
        self.resolved = True
        self.resolved_at = datetime.now(UTC)


# ─── Compliance Service ───


class ComplianceService:
    """Service for compliance checks, privacy filtering, and retention.

    Per Privacy Model: data classification governs access and sharing.
    """

    def __init__(self) -> None:
        self._retention_policies: dict[str, RetentionPolicy] = {}
        self._checks: list[ComplianceCheck] = []
        self._violations: list[ComplianceViolation] = []
        self._check_counter = 0
        self._violation_counter = 0
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        """Initialize default retention policies."""
        defaults = [
            (DataClassification.PUBLIC.value, 3650, "Public data retained indefinitely (10 years)"),
            (DataClassification.COMMUNITY.value, 1825, "Community data retained 5 years"),
            (
                DataClassification.LAW_ENFORCEMENT.value,
                2555,
                "Law enforcement data retained 7 years",
            ),
            (DataClassification.RESTRICTED.value, 1095, "Restricted data retained 3 years"),
            (
                DataClassification.HIGHLY_RESTRICTED.value,
                365,
                "Highly restricted data retained 1 year",
            ),
        ]
        for cls, days, desc in defaults:
            self._retention_policies[cls] = RetentionPolicy(
                classification=cls,
                retention_days=days,
                description=desc,
                auto_delete=True,
            )

    def check_access(self, accessor_role: str, data_classification: str) -> ComplianceCheck:
        """Check if an accessor role can access data of a given classification."""
        self._check_counter += 1
        clearance = ROLE_CLEARANCE.get(accessor_role, 0)
        required = CLASSIFICATION_LEVEL.get(data_classification, 5)
        allowed = clearance >= required

        check = ComplianceCheck(
            id=f"CC-{self._check_counter:06d}",
            accessor_role=accessor_role,
            data_classification=data_classification,
            allowed=allowed,
            reason=""
            if allowed
            else f"Role {accessor_role} clearance {clearance} < required {required}",
        )
        self._checks.append(check)

        if not allowed:
            self.record_violation(
                accessor_role=accessor_role,
                data_classification=data_classification,
                violation_type="UNAUTHORIZED_ACCESS",
                details=f"Role {accessor_role} attempted to access {data_classification} data",
            )

        return check

    def record_violation(
        self,
        accessor_role: str,
        data_classification: str,
        violation_type: str = "",
        accessor_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        details: str = "",
    ) -> ComplianceViolation:
        """Record a compliance violation."""
        self._violation_counter += 1
        violation = ComplianceViolation(
            id=f"CV-{self._violation_counter:06d}",
            accessor_role=accessor_role,
            accessor_id=accessor_id,
            data_classification=data_classification,
            resource_type=resource_type,
            resource_id=resource_id,
            violation_type=violation_type,
            details=details,
        )
        self._violations.append(violation)
        return violation

    def filter_data(
        self,
        data: dict[str, Any],
        accessor_role: str,
        field_classifications: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Filter data based on accessor's clearance level.

        field_classifications maps field names to their data classification.
        Fields not in the map are assumed PUBLIC.
        """
        if field_classifications is None:
            field_classifications = {}

        clearance = ROLE_CLEARANCE.get(accessor_role, 0)
        filtered: dict[str, Any] = {}

        for field, value in data.items():
            cls = field_classifications.get(field, DataClassification.PUBLIC.value)
            required = CLASSIFICATION_LEVEL.get(cls, 1)
            if clearance >= required:
                filtered[field] = value

        return filtered

    def get_retention_policy(self, classification: str) -> RetentionPolicy | None:
        return self._retention_policies.get(classification)

    def set_retention_policy(
        self,
        classification: str,
        retention_days: int,
        description: str = "",
        auto_delete: bool = False,
    ) -> RetentionPolicy:
        policy = RetentionPolicy(
            classification=classification,
            retention_days=retention_days,
            description=description,
            auto_delete=auto_delete,
        )
        self._retention_policies[classification] = policy
        return policy

    def check_retention(self, classification: str, created_date: datetime) -> bool:
        """Check if data has exceeded its retention period. Returns True if expired."""
        policy = self._retention_policies.get(classification)
        if policy is None:
            return False
        age_days = (datetime.now(UTC) - created_date).days
        return age_days > policy.retention_days

    def get_violations(
        self,
        resolved: bool | None = None,
        accessor_role: str | None = None,
    ) -> list[ComplianceViolation]:
        """Get compliance violations with optional filters."""
        result = list(self._violations)
        if resolved is not None:
            result = [v for v in result if v.resolved == resolved]
        if accessor_role:
            result = [v for v in result if v.accessor_role == accessor_role]
        return result

    def resolve_violation(self, violation_id: str) -> bool:
        """Resolve a compliance violation."""
        for v in self._violations:
            if v.id == violation_id:
                v.resolve()
                return True
        return False

    def get_checks(self) -> list[ComplianceCheck]:
        return list(self._checks)

    @property
    def check_count(self) -> int:
        return len(self._checks)

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    @property
    def unresolved_violation_count(self) -> int:
        return len([v for v in self._violations if not v.resolved])
