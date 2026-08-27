"""GFIN Production — Module 40.

Production readiness assessment, deployment checklists, infrastructure
requirements, and go-live criteria. Per Directive §11: production
infrastructure is Layer B, never claimed as deployed.

Layer A: In-memory readiness assessment
Layer B: Real infrastructure deployment (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReadinessLevel(StrEnum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"
    LIVE = "LIVE"


class CheckCategory(StrEnum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    SECURITY = "SECURITY"
    MONITORING = "MONITORING"
    DATA = "DATA"
    NETWORKING = "NETWORKING"
    COMPLIANCE = "COMPLIANCE"
    OPERATIONS = "OPERATIONS"


class ReadinessCheck(BaseModel):
    """A production readiness check."""

    id: str
    category: str
    description: str
    required: bool = True
    verified: bool = False
    notes: str = ""
    verified_at: datetime | None = None

    def verify(self, notes: str = "") -> None:
        self.verified = True
        self.verified_at = datetime.now(UTC)
        if notes:
            self.notes = notes


class ProductionChecklist(BaseModel):
    """Production deployment checklist."""

    id: str
    name: str
    checks: list[ReadinessCheck] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.checks if c.verified)

    @property
    def required_unverified(self) -> int:
        return sum(1 for c in self.checks if c.required and not c.verified)

    @property
    def readiness_level(self) -> str:
        if self.required_unverified > 0:
            return ReadinessLevel.NOT_READY.value
        if self.verified_count < self.total_checks:
            return ReadinessLevel.PARTIALLY_READY.value
        return ReadinessLevel.READY.value


class InfrastructureRequirement(BaseModel):
    """An infrastructure requirement for production."""

    id: str
    component: str
    requirement: str
    status: str = "REQUIRES_EXTERNAL_INFRASTRUCTURE"
    notes: str = ""
    provisioned: bool = False


class ProductionService:
    """Service for production readiness assessment.

    Per Directive §11: production infrastructure is Layer B.
    """

    def __init__(self) -> None:
        self._checklists: dict[str, ProductionChecklist] = {}
        self._requirements: dict[str, InfrastructureRequirement] = {}
        self._checklist_counter = 0
        self._req_counter = 0
        self._init_default_checklist()
        self._init_default_requirements()

    def _init_default_checklist(self) -> None:
        """Initialize default production readiness checklist."""
        checks = [
            (CheckCategory.INFRASTRUCTURE.value, "Kubernetes cluster provisioned"),
            (CheckCategory.INFRASTRUCTURE.value, "PostgreSQL cluster configured"),
            (CheckCategory.INFRASTRUCTURE.value, "Redis cluster configured"),
            (CheckCategory.INFRASTRUCTURE.value, "Kafka cluster configured"),
            (CheckCategory.INFRASTRUCTURE.value, "OpenSearch cluster configured"),
            (CheckCategory.INFRASTRUCTURE.value, "S3 storage configured"),
            (CheckCategory.SECURITY.value, "OIDC/OAuth2 provider configured"),
            (CheckCategory.SECURITY.value, "TLS certificates installed"),
            (CheckCategory.SECURITY.value, "Secrets management configured"),
            (CheckCategory.SECURITY.value, "Network policies enforced"),
            (CheckCategory.MONITORING.value, "Prometheus configured"),
            (CheckCategory.MONITORING.value, "Grafana dashboards deployed"),
            (CheckCategory.MONITORING.value, "Alerting rules configured"),
            (CheckCategory.MONITORING.value, "OpenTelemetry collectors deployed"),
            (CheckCategory.DATA.value, "Database migrations applied"),
            (CheckCategory.DATA.value, "Backup schedules configured"),
            (CheckCategory.DATA.value, "Data retention policies enforced"),
            (CheckCategory.NETWORKING.value, "Load balancer configured"),
            (CheckCategory.NETWORKING.value, "DNS records configured"),
            (CheckCategory.NETWORKING.value, "CDN configured (if applicable)"),
            (CheckCategory.COMPLIANCE.value, "Security audit completed"),
            (CheckCategory.COMPLIANCE.value, "Privacy impact assessment done"),
            (CheckCategory.COMPLIANCE.value, "Legal review completed"),
            (CheckCategory.OPERATIONS.value, "Runbooks documented"),
            (CheckCategory.OPERATIONS.value, "On-call rotation configured"),
            (CheckCategory.OPERATIONS.value, "Incident response plan ready"),
            (CheckCategory.OPERATIONS.value, "Disaster recovery tested"),
        ]

        self._checklist_counter += 1
        checklist = ProductionChecklist(
            id=f"PC-{self._checklist_counter:06d}",
            name="GFIN Production Readiness Checklist",
        )

        for i, (category, desc) in enumerate(checks):
            check = ReadinessCheck(
                id=f"RC-{i + 1:04d}",
                category=category,
                description=desc,
            )
            checklist.checks.append(check)

        self._checklists[checklist.id] = checklist

    def _init_default_requirements(self) -> None:
        """Initialize default infrastructure requirements."""
        reqs = [
            ("compute", "Kubernetes cluster with autoscaling"),
            ("database", "PostgreSQL with replication"),
            ("cache", "Redis cluster with failover"),
            ("message_queue", "Kafka cluster with 3+ brokers"),
            ("search", "OpenSearch cluster"),
            ("storage", "S3-compatible object storage"),
            ("secrets", "HashiCorp Vault or cloud KMS"),
            ("monitoring", "Prometheus + Grafana stack"),
            ("tracing", "OpenTelemetry collectors"),
            ("cdn", "Content delivery network"),
            ("dns", "DNS with health checks"),
            ("lb", "Load balancer with SSL termination"),
        ]
        for component, req in reqs:
            self._req_counter += 1
            ir = InfrastructureRequirement(
                id=f"IR-{self._req_counter:04d}",
                component=component,
                requirement=req,
            )
            self._requirements[ir.id] = ir

    def get_checklist(self, checklist_id: str | None = None) -> ProductionChecklist | None:
        if checklist_id is None:
            # Return the first (default) checklist
            return next(iter(self._checklists.values())) if self._checklists else None
        return self._checklists.get(checklist_id)

    def list_checklists(self) -> list[ProductionChecklist]:
        return list(self._checklists.values())

    def verify_check(self, checklist_id: str, check_id: str, notes: str = "") -> bool:
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return False
        for check in checklist.checks:
            if check.id == check_id:
                check.verify(notes)
                return True
        return False

    def get_readiness_level(self, checklist_id: str | None = None) -> str:
        checklist = self.get_checklist(checklist_id)
        if checklist is None:
            return ReadinessLevel.NOT_READY.value
        return checklist.readiness_level

    def get_readiness_summary(self, checklist_id: str | None = None) -> dict[str, Any]:
        checklist = self.get_checklist(checklist_id)
        if checklist is None:
            return {}
        by_category: dict[str, dict[str, int]] = {}
        for check in checklist.checks:
            cat = check.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "verified": 0}
            by_category[cat]["total"] += 1
            if check.verified:
                by_category[cat]["verified"] += 1
        return {
            "readiness_level": checklist.readiness_level,
            "total_checks": checklist.total_checks,
            "verified": checklist.verified_count,
            "required_unverified": checklist.required_unverified,
            "by_category": by_category,
        }

    def list_requirements(self, provisioned: bool | None = None) -> list[InfrastructureRequirement]:
        reqs = list(self._requirements.values())
        if provisioned is not None:
            reqs = [r for r in reqs if r.provisioned == provisioned]
        return reqs

    def provision_requirement(self, req_id: str, notes: str = "") -> bool:
        req = self._requirements.get(req_id)
        if req is None:
            return False
        req.provisioned = True
        req.notes = notes
        return True

    def get_requirements_summary(self) -> dict[str, Any]:
        reqs = list(self._requirements.values())
        return {
            "total": len(reqs),
            "provisioned": sum(1 for r in reqs if r.provisioned),
            "pending": sum(1 for r in reqs if not r.provisioned),
        }

    def is_production_ready(self) -> bool:
        """Check if ALL required checks are verified AND all requirements provisioned."""
        checklist = self.get_checklist()
        if checklist is None:
            return False
        if checklist.required_unverified > 0:
            return False
        unprovisioned = [r for r in self._requirements.values() if not r.provisioned]
        return len(unprovisioned) == 0

    def mark_go_live(self) -> str:
        """Attempt to mark the system as LIVE. Returns status message."""
        if not self.is_production_ready():
            cl = self.get_checklist()
            unverified = cl.required_unverified if cl else 0
            unprovisioned = sum(1 for r in self._requirements.values() if not r.provisioned)
            return f"NOT READY: {unverified} required checks unverified, {unprovisioned} infrastructure requirements unprovisioned"
        return "READY FOR GO-LIVE: All required checks verified and infrastructure provisioned"

    @property
    def checklist_count(self) -> int:
        return len(self._checklists)

    @property
    def requirement_count(self) -> int:
        return len(self._requirements)
