"""GFIN Go/No-Go Production Gates.

This module defines the 12 critical quality, infrastructure, legal, and security gates
required for GFIN production deployment sign-off.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any


class GateStatus(StrEnum):
    NOT_READY = "NOT_READY"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class OverallStatus(StrEnum):
    GO = "GO"
    NO_GO = "NO_GO"
    BLOCKED = "BLOCKED"


@dataclass
class GoNoGoGate:
    """Represents a single production go/no-go gate definition and evaluation state."""

    name: str
    description: str
    passing_criteria: str
    check_function: Callable[[], bool] | None = None
    status: GateStatus = GateStatus.NOT_READY

    def evaluate(self) -> GateStatus:
        """Evaluate the check function associated with this gate.

        Returns NOT_READY if external infrastructure is absent or check fails.
        """
        if self.check_function is None:
            self.status = GateStatus.NOT_READY
            return self.status

        try:
            passed = self.check_function()
            if passed:
                self.status = GateStatus.PASSED
            else:
                self.status = GateStatus.NOT_READY
        except Exception:
            self.status = GateStatus.FAILED

        return self.status

    def to_dict(self) -> dict[str, Any]:
        """Convert gate to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "passing_criteria": self.passing_criteria,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
        }


# Dummy check function for non-deployed external infrastructure
def _check_external_infra() -> bool:
    """Check function returning False since no external infrastructure is deployed."""
    return False

def _check_legal_compliance() -> bool:
    """Check if legal compliance engineering controls are all verified."""
    try:
        from governance.legal_compliance import is_legal_gate_passable
        passable, _ = is_legal_gate_passable()
        return passable
    except Exception:
        return False



def build_default_gates() -> dict[str, GoNoGoGate]:
    """Instantiate and return all 12 GFIN Go/No-Go gate definitions."""
    return {
        "infrastructure_ready": GoNoGoGate(
            name="infrastructure_ready",
            description="All 8 infrastructure components deployed and healthy",
            passing_criteria="Kubernetes, Vault, Kafka, PostgreSQL, Neo4j, OpenSearch, Redis, and S3 reporting healthy",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "secrets_configured": GoNoGoGate(
            name="secrets_configured",
            description="All secrets in Vault and accessible",
            passing_criteria="Vault unsealed with PKI, database dynamic engine, and app secrets accessible",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "tls_valid": GoNoGoGate(
            name="tls_valid",
            description="All certificates valid and not expiring",
            passing_criteria="TLS certs valid for >= 30 days across all public and internal endpoints",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "network_policies_enforced": GoNoGoGate(
            name="network_policies_enforced",
            description="Network isolation active",
            passing_criteria="NetworkPolicies blocking non-whitelisted inter-pod communication active in k8s",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "rbac_configured": GoNoGoGate(
            name="rbac_configured",
            description="All roles and permissions set up",
            passing_criteria="Kubernetes RBAC and application RBAC matrices verified and enforced",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "monitoring_active": GoNoGoGate(
            name="monitoring_active",
            description="Prometheus scraping all services, Grafana dashboards loaded",
            passing_criteria="Prometheus targets reporting 100% UP and Grafana dashboards responding",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "backup_configured": GoNoGoGate(
            name="backup_configured",
            description="Backup jobs scheduled and tested",
            passing_criteria="PostgreSQL WAL archiving, Neo4j dumps, and OpenSearch snapshots active in S3",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "dr_drill_passed": GoNoGoGate(
            name="dr_drill_passed",
            description="Disaster recovery drill completed successfully",
            passing_criteria="RTO < 1 hour and RPO < 5 minutes verified during simulated cluster failover",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "security_scan_passed": GoNoGoGate(
            name="security_scan_passed",
            description="SAST/DAST/dependency scan completed with no critical findings",
            passing_criteria="Zero Critical or High severity vulnerabilities in code, containers, or packages",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "legal_signed": GoNoGoGate(
            name="legal_signed",
            description="DPA, MLAT, and bilateral agreements signed",
            passing_criteria="Data Processing Agreement and cross-border intelligence agreements executed",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "load_test_passed": GoNoGoGate(
            name="load_test_passed",
            description="Production load test meets SLOs",
            passing_criteria="Sustained 5,000 req/sec with p99 latency < 200ms and 0% error rate",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
        "data_migration_verified": GoNoGoGate(
            name="data_migration_verified",
            description="Data migration from Layer A to Layer B verified",
            passing_criteria="100% record parity and checksum verification between memory state and DB",
            check_function=_check_external_infra,
            status=GateStatus.NOT_READY,
        ),
    }


class GoNoGoGateEvaluator:
    """Evaluates set of Go/No-Go gates and tracks execution state."""

    def __init__(self, gates: dict[str, GoNoGoGate] | None = None) -> None:
        self.gates = gates or build_default_gates()

    def evaluate_gate(self, name: str) -> GateStatus:
        """Evaluate a single gate by name."""
        if name not in self.gates:
            raise KeyError(f"Gate '{name}' not found")
        return self.gates[name].evaluate()

    def evaluate_all(self) -> OverallStatus:
        """Evaluate all 12 gates and determine overall status.

        Returns BLOCKED if any gate is NOT_READY, FAILED, or BLOCKED.
        """
        all_passed = True
        for gate in self.gates.values():
            status = gate.evaluate()
            if status != GateStatus.PASSED:
                all_passed = False

        if not all_passed:
            return OverallStatus.BLOCKED

        return OverallStatus.GO

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluator state and all gates to dictionary."""
        return {
            "overall_status": self.evaluate_all().value,
            "gates": {name: gate.to_dict() for name, gate in self.gates.items()},
        }

    def to_json(self) -> str:
        """Serialize evaluator status to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Global instance and module-level helper functions
_default_evaluator = GoNoGoGateEvaluator()


def get_all_gates() -> dict[str, GoNoGoGate]:
    """Get dictionary of all 12 default gate instances."""
    return _default_evaluator.gates


def get_gate(name: str) -> GoNoGoGate:
    """Get a single gate by name."""
    return _default_evaluator.gates[name]


def evaluate_gate(name: str) -> GateStatus:
    """Evaluate a single gate by name."""
    return _default_evaluator.evaluate_gate(name)


def evaluate_all() -> OverallStatus:
    """Evaluate all gates and return overall status (BLOCKED if infrastructure missing)."""
    return _default_evaluator.evaluate_all()


def serialize_gates_to_json() -> str:
    """Serialize all gate definitions and statuses to JSON string."""
    return _default_evaluator.to_json()
