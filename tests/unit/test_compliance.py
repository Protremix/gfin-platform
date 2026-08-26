"""Tests for Compliance — Module 33."""

from datetime import UTC, datetime, timedelta

import pytest

from services.compliance import (
    CLASSIFICATION_LEVEL,
    ROLE_CLEARANCE,
    AccessorRole,
    ComplianceCheck,
    ComplianceService,
    ComplianceViolation,
    DataClassification,
)


@pytest.fixture
def service():
    return ComplianceService()


# ─── Classification Tests ───


class TestDataClassification:
    def test_hierarchy(self):
        assert (
            CLASSIFICATION_LEVEL[DataClassification.PUBLIC.value]
            < CLASSIFICATION_LEVEL[DataClassification.COMMUNITY.value]
        )
        assert (
            CLASSIFICATION_LEVEL[DataClassification.COMMUNITY.value]
            < CLASSIFICATION_LEVEL[DataClassification.LAW_ENFORCEMENT.value]
        )
        assert (
            CLASSIFICATION_LEVEL[DataClassification.LAW_ENFORCEMENT.value]
            < CLASSIFICATION_LEVEL[DataClassification.RESTRICTED.value]
        )
        assert (
            CLASSIFICATION_LEVEL[DataClassification.RESTRICTED.value]
            < CLASSIFICATION_LEVEL[DataClassification.HIGHLY_RESTRICTED.value]
        )

    def test_role_clearance(self):
        assert (
            ROLE_CLEARANCE[AccessorRole.PUBLIC.value]
            < ROLE_CLEARANCE[AccessorRole.POLICE_OFFICER.value]
        )
        assert (
            ROLE_CLEARANCE[AccessorRole.POLICE_OFFICER.value]
            < ROLE_CLEARANCE[AccessorRole.POLICE_SUPERVISOR.value]
        )
        assert (
            ROLE_CLEARANCE[AccessorRole.POLICE_SUPERVISOR.value]
            < ROLE_CLEARANCE[AccessorRole.SYSTEM_ADMIN.value]
        )


# ─── ComplianceCheck Tests ───


class TestComplianceCheck:
    def test_creation(self):
        check = ComplianceCheck(
            id="CC-001",
            accessor_role=AccessorRole.POLICE_OFFICER.value,
            data_classification=DataClassification.LAW_ENFORCEMENT.value,
            allowed=True,
        )
        assert check.allowed is True
        assert check.reason == ""


# ─── ComplianceViolation Tests ───


class TestComplianceViolation:
    def test_creation(self):
        v = ComplianceViolation(
            id="CV-001",
            accessor_role=AccessorRole.PUBLIC.value,
            data_classification=DataClassification.RESTRICTED.value,
            violation_type="UNAUTHORIZED_ACCESS",
        )
        assert v.resolved is False
        assert v.resolved_at is None

    def test_resolve(self):
        v = ComplianceViolation(
            id="CV-001",
            accessor_role=AccessorRole.PUBLIC.value,
            data_classification=DataClassification.RESTRICTED.value,
            violation_type="UNAUTHORIZED_ACCESS",
        )
        v.resolve()
        assert v.resolved is True
        assert v.resolved_at is not None


# ─── ComplianceService Tests ───


class TestComplianceService:
    def test_check_access_allowed(self, service):
        check = service.check_access(
            AccessorRole.POLICE_OFFICER.value, DataClassification.LAW_ENFORCEMENT.value
        )
        assert check.allowed is True

    def test_check_access_denied(self, service):
        check = service.check_access(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        assert check.allowed is False
        assert "clearance" in check.reason

    def test_check_access_officer_cannot_access_restricted(self, service):
        check = service.check_access(
            AccessorRole.POLICE_OFFICER.value, DataClassification.RESTRICTED.value
        )
        assert check.allowed is False

    def test_check_access_admin_can_access_all(self, service):
        for cls in DataClassification:
            check = service.check_access(AccessorRole.SYSTEM_ADMIN.value, cls.value)
            assert check.allowed is True

    def test_check_access_citizen_can_access_public(self, service):
        check = service.check_access(AccessorRole.CITIZEN.value, DataClassification.PUBLIC.value)
        assert check.allowed is True

    def test_check_access_citizen_cannot_access_le(self, service):
        check = service.check_access(
            AccessorRole.CITIZEN.value, DataClassification.LAW_ENFORCEMENT.value
        )
        assert check.allowed is False

    def test_violation_recorded_on_denial(self, service):
        service.check_access(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        assert service.violation_count == 1
        assert service.unresolved_violation_count == 1

    def test_no_violation_on_allowed(self, service):
        service.check_access(
            AccessorRole.POLICE_ADMIN.value, DataClassification.LAW_ENFORCEMENT.value
        )
        assert service.violation_count == 0

    def test_filter_data_public_fields(self, service):
        data = {"entity_id": "ENT-001", "entity_type": "domain", "public_note": "test"}
        result = service.filter_data(data, AccessorRole.PUBLIC.value)
        assert "entity_id" in result
        assert "public_note" in result

    def test_filter_data_restricted_fields(self, service):
        data = {"entity_id": "ENT-001", "suspect_name": "John Doe", "case_file": "CASE-001"}
        field_cls = {
            "suspect_name": DataClassification.RESTRICTED.value,
            "case_file": DataClassification.HIGHLY_RESTRICTED.value,
        }
        result = service.filter_data(data, AccessorRole.POLICE_OFFICER.value, field_cls)
        assert "entity_id" in result
        assert "suspect_name" not in result
        assert "case_file" not in result

    def test_filter_data_admin_sees_all(self, service):
        data = {"entity_id": "ENT-001", "suspect_name": "John Doe"}
        field_cls = {"suspect_name": DataClassification.HIGHLY_RESTRICTED.value}
        result = service.filter_data(data, AccessorRole.SYSTEM_ADMIN.value, field_cls)
        assert "suspect_name" in result

    def test_filter_data_officer_sees_le(self, service):
        data = {"entity_id": "ENT-001", "police_match": True}
        field_cls = {"police_match": DataClassification.LAW_ENFORCEMENT.value}
        result = service.filter_data(data, AccessorRole.POLICE_OFFICER.value, field_cls)
        assert "police_match" in result

    def test_get_retention_policy(self, service):
        policy = service.get_retention_policy(DataClassification.PUBLIC.value)
        assert policy is not None
        assert policy.retention_days == 3650

    def test_set_retention_policy(self, service):
        service.set_retention_policy("CUSTOM", 100, "Custom policy")
        policy = service.get_retention_policy("CUSTOM")
        assert policy is not None
        assert policy.retention_days == 100

    def test_check_retention_expired(self, service):
        old_date = datetime.now(UTC) - timedelta(days=4000)
        assert service.check_retention(DataClassification.PUBLIC.value, old_date) is True

    def test_check_retention_not_expired(self, service):
        recent_date = datetime.now(UTC) - timedelta(days=30)
        assert service.check_retention(DataClassification.PUBLIC.value, recent_date) is False

    def test_check_retention_no_policy(self, service):
        recent_date = datetime.now(UTC)
        assert service.check_retention("NONEXISTENT", recent_date) is False

    def test_default_policies_exist(self, service):
        for cls in DataClassification:
            assert service.get_retention_policy(cls.value) is not None

    def test_record_violation(self, service):
        v = service.record_violation(
            AccessorRole.CITIZEN.value,
            DataClassification.RESTRICTED.value,
            violation_type="UNAUTHORIZED_ACCESS",
            details="Citizen tried to access restricted data",
        )
        assert v.id.startswith("CV-")
        assert service.violation_count == 1

    def test_get_violations_unresolved(self, service):
        service.record_violation(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        service.record_violation(AccessorRole.CITIZEN.value, DataClassification.RESTRICTED.value)
        unresolved = service.get_violations(resolved=False)
        assert len(unresolved) == 2

    def test_resolve_violation(self, service):
        v = service.record_violation(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        assert service.resolve_violation(v.id) is True
        assert v.resolved is True
        assert service.unresolved_violation_count == 0

    def test_resolve_nonexistent(self, service):
        assert service.resolve_violation("nonexistent") is False

    def test_get_violations_by_role(self, service):
        service.record_violation(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        service.record_violation(AccessorRole.CITIZEN.value, DataClassification.RESTRICTED.value)
        service.record_violation(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        public_violations = service.get_violations(accessor_role=AccessorRole.PUBLIC.value)
        assert len(public_violations) == 2

    def test_get_checks(self, service):
        service.check_access(AccessorRole.POLICE_OFFICER.value, DataClassification.PUBLIC.value)
        service.check_access(AccessorRole.PUBLIC.value, DataClassification.RESTRICTED.value)
        assert service.check_count == 2

    def test_check_count(self, service):
        service.check_access(AccessorRole.POLICE_OFFICER.value, DataClassification.PUBLIC.value)
        assert service.check_count == 1
