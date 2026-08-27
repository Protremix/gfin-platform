"""Unit tests for GFIN Go/No-Go Gate definitions, evaluation, and JSON serialization."""

import json

from production.go_no_go_gates import (
    GateStatus,
    GoNoGoGate,
    GoNoGoGateEvaluator,
    OverallStatus,
    evaluate_all,
    evaluate_gate,
    get_all_gates,
    get_gate,
    serialize_gates_to_json,
)

EXPECTED_GATES = [
    "infrastructure_ready",
    "secrets_configured",
    "tls_valid",
    "network_policies_enforced",
    "rbac_configured",
    "monitoring_active",
    "backup_configured",
    "dr_drill_passed",
    "security_scan_passed",
    "legal_signed",
    "load_test_passed",
    "data_migration_verified",
]


def test_gate_definitions_exist():
    """Verify that all 12 required go/no-go gates exist in the gate registry."""
    gates = get_all_gates()
    assert len(gates) == 12
    for gate_name in EXPECTED_GATES:
        assert gate_name in gates


def test_gate_attributes():
    """Verify each gate contains non-empty name, description, passing criteria, and status."""
    gates = get_all_gates()
    for name, gate in gates.items():
        assert isinstance(gate, GoNoGoGate)
        assert gate.name == name
        assert isinstance(gate.description, str) and len(gate.description) > 0
        assert isinstance(gate.passing_criteria, str) and len(gate.passing_criteria) > 0
        assert hasattr(gate, "status")


def test_evaluate_all_returns_blocked():
    """Verify evaluate_all() returns BLOCKED when external infrastructure is missing."""
    overall = evaluate_all()
    assert overall == OverallStatus.BLOCKED
    assert overall == "BLOCKED"


def test_individual_gate_evaluation_returns_not_ready():
    """Verify evaluating individual infrastructure gates returns NOT_READY."""
    for gate_name in EXPECTED_GATES:
        status = evaluate_gate(gate_name)
        assert status == GateStatus.NOT_READY
        assert status == "NOT_READY"


def test_gate_json_serialization():
    """Verify serialization of gates to JSON format."""
    json_str = serialize_gates_to_json()
    assert isinstance(json_str, str)

    data = json.loads(json_str)
    assert "overall_status" in data
    assert data["overall_status"] == "BLOCKED"
    assert "gates" in data
    assert len(data["gates"]) == 12

    for gate_name in EXPECTED_GATES:
        assert gate_name in data["gates"]
        gate_data = data["gates"][gate_name]
        assert "name" in gate_data
        assert "description" in gate_data
        assert "passing_criteria" in gate_data
        assert "status" in gate_data
        assert gate_data["status"] in ["NOT_READY", "PASSED", "FAILED", "BLOCKED"]


def test_custom_evaluator():
    """Verify custom evaluator instance behavior and gate modification."""
    evaluator = GoNoGoGateEvaluator()
    assert evaluator.evaluate_all() == OverallStatus.BLOCKED

    # Test individual gate getter
    gate = get_gate("infrastructure_ready")
    assert gate.name == "infrastructure_ready"
    assert gate.to_dict()["status"] == "NOT_READY"
