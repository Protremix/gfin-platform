"""Tests for Police Console — Module 27."""

from datetime import UTC, datetime, timedelta

import pytest

from services.cross_border_requests import (
    CrossBorderRequestEngine,
    RequestAuthorizer,
    RequestRouter,
)
from services.global_matching import GlobalMatchEngine, IndexedEntity, MatchConfidence
from services.police_console import (
    ROLE_PERMISSIONS,
    ConsoleAction,
    ConsoleAuditLogger,
    ConsoleRole,
    ConsoleSession,
    InvestigationWorkspace,
    PoliceConsoleService,
    WorkspaceStatus,
)

# ─── Fixtures ───


@pytest.fixture
def match_engine():
    eng = GlobalMatchEngine()
    eng.index.register_entity(
        IndexedEntity(
            entity_id="ENT-DE-001",
            entity_type="domain",
            entity_value="fraudster.com",
            jurisdiction="DE",
            organization="BKA",
            confidence=MatchConfidence.HIGH.value,
            first_seen=datetime(2026, 1, 1, tzinfo=UTC),
            suspect_names=["Hans Mueller"],
        )
    )
    eng.index.register_entity(
        IndexedEntity(
            entity_id="ENT-LV-001",
            entity_type="domain",
            entity_value="fraudster.com",
            jurisdiction="LV",
            organization="Latvian Police",
            confidence=MatchConfidence.MEDIUM.value,
        )
    )
    return eng


@pytest.fixture
def cbr_engine():
    auth = RequestAuthorizer()
    auth.register_org("ORG-LV", {"DE", "FR"})
    router = RequestRouter()
    router.register_jurisdiction("DE", "ORG-DE")
    return CrossBorderRequestEngine(authorizer=auth, router=router)


@pytest.fixture
def service(match_engine, cbr_engine):
    return PoliceConsoleService(match_engine=match_engine, cbr_engine=cbr_engine)


@pytest.fixture
def officer_session(service):
    return service.create_session(
        operator_id="OP-001",
        operator_name="Det. Smith",
        org_id="ORG-LV",
        jurisdiction="LV",
        role=ConsoleRole.OFFICER.value,
    )


@pytest.fixture
def admin_session(service):
    return service.create_session(
        operator_id="OP-002",
        operator_name="Admin Jones",
        org_id="ORG-LV",
        jurisdiction="LV",
        role=ConsoleRole.ADMIN.value,
    )


@pytest.fixture
def service_with_alerts(service):
    service.set_alert_store(
        [
            {"id": "ALT-001", "jurisdiction": "LV", "priority": "HIGH"},
            {"id": "ALT-002", "jurisdiction": "LV", "priority": "MEDIUM"},
            {"id": "ALT-003", "jurisdiction": "DE", "priority": "LOW"},
        ]
    )
    return service


# ─── ConsoleSession Tests ───


class TestConsoleSession:
    def test_creation(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
        )
        assert s.role == ConsoleRole.OFFICER.value
        assert s.active is True

    def test_has_permission_officer(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
            role=ConsoleRole.OFFICER.value,
        )
        assert s.has_permission(ConsoleAction.SEARCH_ENTITY.value) is True
        assert s.has_permission(ConsoleAction.VIEW_AUDIT_TRAIL.value) is False

    def test_has_permission_admin(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
            role=ConsoleRole.ADMIN.value,
        )
        assert s.has_permission(ConsoleAction.VIEW_AUDIT_TRAIL.value) is True
        assert s.has_permission(ConsoleAction.SEARCH_ENTITY.value) is True

    def test_is_expired(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert s.is_expired() is True

    def test_not_expired(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert s.is_expired() is False

    def test_no_expiry_not_expired(self):
        s = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
        )
        assert s.is_expired() is False


# ─── Role Permissions Tests ───


class TestRolePermissions:
    def test_officer_cannot_view_audit(self):
        assert (
            ConsoleAction.VIEW_AUDIT_TRAIL.value not in ROLE_PERMISSIONS[ConsoleRole.OFFICER.value]
        )

    def test_supervisor_can_view_audit(self):
        assert (
            ConsoleAction.VIEW_AUDIT_TRAIL.value in ROLE_PERMISSIONS[ConsoleRole.SUPERVISOR.value]
        )

    def test_admin_has_all(self):
        assert len(ROLE_PERMISSIONS[ConsoleRole.ADMIN.value]) == len(list(ConsoleAction))


# ─── ConsoleAuditLogger Tests ───


class TestConsoleAuditLogger:
    def test_log(self):
        logger = ConsoleAuditLogger()
        session = ConsoleSession(
            session_id="S1",
            operator_id="OP1",
            operator_name="Smith",
            org_id="ORG-LV",
            jurisdiction="LV",
        )
        entry = logger.log(session, ConsoleAction.SEARCH_ENTITY.value, {"count": 1})
        assert entry.id.startswith("CA-")
        assert entry.operator_name == "Smith"
        assert logger.count == 1

    def test_get_entries_by_session(self):
        logger = ConsoleAuditLogger()
        s1 = ConsoleSession(
            session_id="S1", operator_id="OP1", operator_name="A", org_id="O", jurisdiction="LV"
        )
        s2 = ConsoleSession(
            session_id="S2", operator_id="OP2", operator_name="B", org_id="O", jurisdiction="LV"
        )
        logger.log(s1, ConsoleAction.SEARCH_ENTITY.value)
        logger.log(s2, ConsoleAction.VIEW_ENTITY.value)
        assert len(logger.get_entries(session_id="S1")) == 1
        assert len(logger.get_entries(session_id="S2")) == 1

    def test_get_entries_by_operator(self):
        logger = ConsoleAuditLogger()
        s = ConsoleSession(
            session_id="S1", operator_id="OP1", operator_name="A", org_id="O", jurisdiction="LV"
        )
        logger.log(s, ConsoleAction.SEARCH_ENTITY.value)
        logger.log(s, ConsoleAction.VIEW_ENTITY.value)
        assert len(logger.get_entries(operator_id="OP1")) == 2


# ─── PoliceConsoleService Tests ───


class TestPoliceConsoleService:
    def test_create_session(self, service):
        s = service.create_session("OP1", "Smith", "ORG-LV", "LV")
        assert s.session_id.startswith("CS-")
        assert service.session_count == 1

    def test_get_session(self, service, officer_session):
        assert service.get_session(officer_session.session_id) is not None
        assert service.get_session("nonexistent") is None

    def test_search_entity(self, service, officer_session):
        results = service.search_entity(officer_session.session_id, "domain", "fraudster.com")
        assert len(results) == 2
        jurisdictions = {r.jurisdiction for r in results}
        assert jurisdictions == {"DE", "LV"}

    def test_search_entity_no_results(self, service, officer_session):
        results = service.search_entity(officer_session.session_id, "domain", "clean.com")
        assert len(results) == 0

    def test_search_entity_session_not_found(self, service):
        with pytest.raises(ValueError, match="Session not found"):
            service.search_entity("nonexistent", "domain", "test.com")

    def test_view_entity(self, service, officer_session):
        data = service.view_entity(officer_session.session_id, "ENT-DE-001")
        assert data is not None
        assert data["entity_id"] == "ENT-DE-001"
        assert "suspect_names" not in data

    def test_view_entity_not_found(self, service, officer_session):
        assert service.view_entity(officer_session.session_id, "nonexistent") is None

    def test_view_entity_policy_filtered(self, service, officer_session):
        data = service.view_entity(officer_session.session_id, "ENT-DE-001")
        assert "entity_id" in data
        assert "jurisdiction" in data
        assert "suspect_names" not in data
        assert "case_files" not in data

    def test_submit_observation(self, service, officer_session):
        obs = service.submit_observation(
            officer_session.session_id, "domain", "suspicious.com", "Looks like phishing"
        )
        assert obs.id.startswith("OBS-")
        assert obs.observation_text == "Looks like phishing"
        assert service.observation_count == 1

    def test_view_alerts(self, service_with_alerts, officer_session):
        alerts = service_with_alerts.view_alerts(officer_session.session_id)
        assert len(alerts) == 2  # Only LV alerts
        assert all(a["jurisdiction"] == "LV" for a in alerts)

    def test_view_alerts_different_jurisdiction(self, service_with_alerts):
        s = service_with_alerts.create_session("OP-DE", "Mueller", "ORG-DE", "DE")
        alerts = service_with_alerts.view_alerts(s.session_id)
        assert len(alerts) == 1
        assert alerts[0]["jurisdiction"] == "DE"

    def test_create_cross_border_request(self, service, officer_session):
        req_id = service.create_cross_border_request(
            officer_session.session_id,
            target_jurisdiction="DE",
            entity_id="ENT-DE-001",
            entity_type="domain",
            legal_basis="EU Directive 2016/680",
            purpose="Fraud investigation",
            entity_value="fraudster.com",
        )
        assert req_id.startswith("CBR-")

    def test_view_cross_border_requests(self, service, officer_session):
        service.create_cross_border_request(
            officer_session.session_id,
            target_jurisdiction="DE",
            entity_id="ENT-DE-001",
            entity_type="domain",
            legal_basis="EU Directive",
            purpose="Investigation",
        )
        requests = service.view_cross_border_requests(officer_session.session_id)
        assert len(requests) == 1
        assert requests[0]["requesting_org"] == "ORG-LV"

    def test_create_workspace(self, service, officer_session):
        ws = service.create_workspace(officer_session.session_id, "Phishing Investigation Q3")
        assert ws.id.startswith("WS-")
        assert ws.name == "Phishing Investigation Q3"
        assert ws.status == WorkspaceStatus.OPEN.value
        assert service.workspace_count == 1

    def test_add_entity_to_workspace(self, service, officer_session):
        ws = service.create_workspace(officer_session.session_id, "Investigation")
        assert service.add_entity_to_workspace(officer_session.session_id, ws.id, "ENT-001") is True
        assert "ENT-001" in service.get_workspace(ws.id).entity_ids

    def test_add_note_to_workspace(self, service, officer_session):
        ws = service.create_workspace(officer_session.session_id, "Investigation")
        assert service.add_workspace_note(officer_session.session_id, ws.id, "Test note") is True
        assert len(service.get_workspace(ws.id).notes) == 1
        assert service.get_workspace(ws.id).notes[0]["text"] == "Test note"

    def test_add_entity_to_nonexistent_workspace(self, service, officer_session):
        assert (
            service.add_entity_to_workspace(officer_session.session_id, "WS-999", "ENT-001")
            is False
        )

    def test_view_audit_trail_admin(self, service, admin_session, officer_session):
        # Officer does some actions
        service.search_entity(officer_session.session_id, "domain", "fraudster.com")
        service.submit_observation(officer_session.session_id, "domain", "test.com", "Test")

        # Admin views audit trail
        entries = service.view_audit_trail(admin_session.session_id)
        assert len(entries) >= 2

    def test_view_audit_trail_officer_denied(self, service, officer_session):
        with pytest.raises(PermissionError):
            service.view_audit_trail(officer_session.session_id)

    def test_expired_session_denied(self, service):
        s = service.create_session("OP1", "Smith", "ORG-LV", "LV")
        s.expires_at = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(PermissionError, match="expired"):
            service.search_entity(s.session_id, "domain", "test.com")

    def test_audit_logged_on_search(self, service, officer_session):
        service.search_entity(officer_session.session_id, "domain", "fraudster.com")
        entries = service.audit.get_entries(session_id=officer_session.session_id)
        assert len(entries) == 1
        assert entries[0].action == ConsoleAction.SEARCH_ENTITY.value

    def test_audit_logged_on_submit(self, service, officer_session):
        service.submit_observation(officer_session.session_id, "domain", "test.com", "Test")
        entries = service.audit.get_entries(session_id=officer_session.session_id)
        assert len(entries) == 1
        assert entries[0].action == ConsoleAction.SUBMIT_OBSERVATION.value


# ─── InvestigationWorkspace Tests ───


class TestInvestigationWorkspace:
    def test_add_entity(self):
        ws = InvestigationWorkspace(
            id="WS-001", name="Test", operator_id="OP1", org_id="O", jurisdiction="LV"
        )
        ws.add_entity("ENT-001")
        ws.add_entity("ENT-002")
        ws.add_entity("ENT-001")  # Deduplicate
        assert len(ws.entity_ids) == 2
        assert ws.updated_at is not None

    def test_add_note(self):
        ws = InvestigationWorkspace(
            id="WS-001", name="Test", operator_id="OP1", org_id="O", jurisdiction="LV"
        )
        ws.add_note("Important finding", "Detective Smith")
        assert len(ws.notes) == 1
        assert ws.notes[0]["text"] == "Important finding"
        assert ws.notes[0]["author"] == "Detective Smith"

    def test_set_status(self):
        ws = InvestigationWorkspace(
            id="WS-001", name="Test", operator_id="OP1", org_id="O", jurisdiction="LV"
        )
        ws.set_status(WorkspaceStatus.IN_PROGRESS.value)
        assert ws.status == WorkspaceStatus.IN_PROGRESS.value
        assert ws.updated_at is not None


# ─── Integration Tests ───


class TestIntegrationConsole:
    def test_full_investigation_workflow(self, service, officer_session):
        """Full workflow: search → view → submit obs → create CBR → create workspace."""
        # Search
        results = service.search_entity(officer_session.session_id, "domain", "fraudster.com")
        assert len(results) >= 1

        # View entity
        entity = service.view_entity(officer_session.session_id, results[0].entity_id)
        assert entity is not None

        # Submit observation
        obs = service.submit_observation(
            officer_session.session_id, "domain", "fraudster.com", "Confirmed phishing"
        )
        assert obs.id.startswith("OBS-")

        # Create workspace
        ws = service.create_workspace(officer_session.session_id, "Phishing Investigation")
        service.add_entity_to_workspace(officer_session.session_id, ws.id, results[0].entity_id)
        service.add_workspace_note(officer_session.session_id, ws.id, "Starting investigation")

        # Create cross-border request
        req_id = service.create_cross_border_request(
            officer_session.session_id,
            target_jurisdiction="DE",
            entity_id=results[0].entity_id,
            entity_type="domain",
            legal_basis="EU Directive 2016/680 Art. 10",
            purpose="Cross-border fraud investigation",
            entity_value="fraudster.com",
        )
        assert req_id.startswith("CBR-")

        # View requests
        requests = service.view_cross_border_requests(officer_session.session_id)
        assert len(requests) >= 1

        # Verify full audit trail
        entries = service.audit.get_entries(session_id=officer_session.session_id)
        actions = [e.action for e in entries]
        assert ConsoleAction.SEARCH_ENTITY.value in actions
        assert ConsoleAction.VIEW_ENTITY.value in actions
        assert ConsoleAction.SUBMIT_OBSERVATION.value in actions
        assert ConsoleAction.MANAGE_INVESTIGATION.value in actions
        assert ConsoleAction.CREATE_CBR.value in actions
        assert ConsoleAction.VIEW_CBR.value in actions
