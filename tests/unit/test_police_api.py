"""Tests for Police API — Module 23.

Tests cover:
- PoliceAuth: authenticate, authorize, session expiry, revocation, ABAC
- PoliceAPI: all 8 endpoints (match, observation, entity_intel, campaign_intel, monitor, alerts, request, request_status)
- PoliceAuditLog: log, query, immutability
- PoliceRateLimiter: check, record, reset, enforce
- CrossBorderRequest: status workflow, transitions
- Integration: full API pipeline from auth to response
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from services.police_api import (
    AccessLevel,
    CampaignIntel,
    CrossBorderRequest,
    EndpointName,
    EntityIntel,
    MatchResult,
    ObservationRecord,
    PoliceAPI,
    PoliceAuditLog,
    PoliceAuth,
    PoliceOrganization,
    PoliceRateLimiter,
    PoliceRole,
    RequestStatus,
)

# ─── Fixtures ───


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def org_officer():
    return PoliceOrganization(
        org_id="ORG-001",
        name="Latvian Police",
        jurisdiction="LV",
        api_key="key-officer-001",
        access_level=AccessLevel.MATCH_ONLY.value,
    )


@pytest.fixture
def org_supervisor():
    return PoliceOrganization(
        org_id="ORG-002",
        name="EUROPOL",
        jurisdiction="EU",
        api_key="key-supervisor-001",
        access_level=AccessLevel.FULL_ACCESS.value,
    )


@pytest.fixture
def auth(org_officer, org_supervisor):
    a = PoliceAuth()
    a.register_organization(org_officer)
    a.register_organization(org_supervisor)
    return a


@pytest.fixture
def api(mock_event_bus, org_officer, org_supervisor):
    a = PoliceAuth()
    a.register_organization(org_officer)
    a.register_organization(org_supervisor)
    return PoliceAPI(auth=a, event_bus=mock_event_bus)


@pytest.fixture
def officer_session(auth):
    return auth.authenticate(
        "key-officer-001", officer_name="Officer Smith", role=PoliceRole.POLICE_OFFICER.value
    )


@pytest.fixture
def supervisor_session(auth):
    return auth.authenticate(
        "key-supervisor-001",
        officer_name="Supervisor Jones",
        role=PoliceRole.POLICE_SUPERVISOR.value,
    )


# ─── PoliceAuth Tests ───


class TestPoliceAuth:
    def test_authenticate_success(self, auth):
        session = auth.authenticate("key-officer-001", "Officer Smith")
        assert session is not None
        assert session.org_id == "ORG-001"
        assert session.officer_name == "Officer Smith"
        assert session.is_valid()

    def test_authenticate_invalid_key(self, auth):
        session = auth.authenticate("invalid-key")
        assert session is None

    def test_authorize_officer_can_match(self, auth):
        session = auth.authenticate("key-officer-001", role=PoliceRole.POLICE_OFFICER.value)
        assert auth.authorize(session, EndpointName.MATCH.value) is True

    def test_authorize_officer_cannot_request(self, auth):
        session = auth.authenticate("key-officer-001", role=PoliceRole.POLICE_OFFICER.value)
        assert auth.authorize(session, EndpointName.REQUEST.value) is False

    def test_authorize_supervisor_can_request(self, auth):
        session = auth.authenticate("key-supervisor-001", role=PoliceRole.POLICE_SUPERVISOR.value)
        assert auth.authorize(session, EndpointName.REQUEST.value) is True

    def test_authorize_admin_can_access_all(self, auth):
        session = auth.authenticate("key-officer-001", role=PoliceRole.POLICE_ADMIN.value)
        for endpoint in EndpointName:
            assert auth.authorize(session, endpoint.value) is True

    def test_session_expiry(self, auth):
        session = auth.authenticate("key-officer-001")
        # Force expiry
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        assert session.is_expired() is True
        assert session.is_valid() is False
        assert auth.authorize(session, EndpointName.MATCH.value) is False

    def test_revoke_session(self, auth):
        session = auth.authenticate("key-officer-001")
        assert auth.revoke_session(session.session_id) is True
        assert session.active is False
        assert session.is_valid() is False

    def test_revoke_nonexistent(self, auth):
        assert auth.revoke_session("nonexistent") is False

    def test_get_organization(self, auth):
        org = auth.get_organization("ORG-001")
        assert org is not None
        assert org.name == "Latvian Police"

    def test_get_organization_not_found(self, auth):
        assert auth.get_organization("nonexistent") is None


# ─── PoliceAuditLog Tests ───


class TestPoliceAuditLog:
    def test_log_entry(self, officer_session):
        log = PoliceAuditLog()
        entry = log.log(officer_session, EndpointName.MATCH.value, {"entity": "test"}, "ok")
        assert entry.id.startswith("PAUDIT-")
        assert entry.org_id == "ORG-001"
        assert entry.endpoint == EndpointName.MATCH.value

    def test_log_count(self, officer_session):
        log = PoliceAuditLog()
        log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        log.log(officer_session, EndpointName.OBSERVATION.value, {}, "ok")
        assert log.count == 2

    def test_query_by_org(self, officer_session, supervisor_session):
        log = PoliceAuditLog()
        log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        log.log(supervisor_session, EndpointName.MATCH.value, {}, "ok")
        results = log.query(org_id="ORG-001")
        assert len(results) == 1
        assert results[0].org_id == "ORG-001"

    def test_query_by_endpoint(self, officer_session):
        log = PoliceAuditLog()
        log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        log.log(officer_session, EndpointName.OBSERVATION.value, {}, "ok")
        results = log.query(endpoint=EndpointName.MATCH.value)
        assert len(results) == 1
        assert results[0].endpoint == EndpointName.MATCH.value

    def test_query_by_time_range(self, officer_session):
        log = PoliceAuditLog()
        log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        results = log.query(start=datetime.now(UTC) - timedelta(hours=1))
        assert len(results) == 1
        results = log.query(start=datetime.now(UTC) + timedelta(hours=1))
        assert len(results) == 0

    def test_immutability_delete(self, officer_session):
        log = PoliceAuditLog()
        entry = log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        assert log.delete_entry(entry.id) is False
        assert log.count == 1  # Still there

    def test_immutability_modify(self, officer_session):
        log = PoliceAuditLog()
        entry = log.log(officer_session, EndpointName.MATCH.value, {}, "ok")
        assert log.modify_entry(entry.id, success=False) is False
        # Entry unchanged
        results = log.query(org_id="ORG-001")
        assert results[0].success is True


# ─── PoliceRateLimiter Tests ───


class TestPoliceRateLimiter:
    def test_check_limit_within(self, org_officer):
        limiter = PoliceRateLimiter()
        assert limiter.check_limit(org_officer, EndpointName.MATCH.value) is True

    def test_record_use(self, org_officer):
        limiter = PoliceRateLimiter()
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        assert limiter.get_usage(org_officer.org_id, EndpointName.MATCH.value) == 1

    def test_check_limit_exceeded(self, org_officer):
        limiter = PoliceRateLimiter()
        # Set a very low limit for testing
        org_officer.rate_limits[EndpointName.MATCH.value] = 2
        assert limiter.check_limit(org_officer, EndpointName.MATCH.value) is True
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        assert limiter.check_limit(org_officer, EndpointName.MATCH.value) is False

    def test_reset_org(self, org_officer):
        limiter = PoliceRateLimiter()
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        limiter.reset(org_officer.org_id)
        assert limiter.get_usage(org_officer.org_id, EndpointName.MATCH.value) == 0

    def test_reset_all(self, org_officer):
        limiter = PoliceRateLimiter()
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        limiter.reset()
        assert limiter.get_usage(org_officer.org_id, EndpointName.MATCH.value) == 0

    def test_per_endpoint_independent(self, org_officer):
        limiter = PoliceRateLimiter()
        limiter.record_use(org_officer.org_id, EndpointName.MATCH.value)
        # Different endpoint should not be affected
        assert limiter.get_usage(org_officer.org_id, EndpointName.OBSERVATION.value) == 0


# ─── CrossBorderRequest Tests ───


class TestCrossBorderRequest:
    def test_initial_status(self):
        req = CrossBorderRequest(
            id="CBR-001",
            requesting_org="ORG-001",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="ENT-001",
            entity_type="domain",
        )
        assert req.status == RequestStatus.PENDING.value

    def test_transition_pending_to_review(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        assert req.transition(RequestStatus.REVIEW.value) is True
        assert req.status == RequestStatus.REVIEW.value

    def test_transition_pending_to_denied(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        assert req.transition(RequestStatus.DENIED.value, reviewer="admin") is True
        assert req.status == RequestStatus.DENIED.value
        assert req.reviewed_by == "admin"

    def test_transition_review_to_approved(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        req.transition(RequestStatus.REVIEW.value)
        assert req.transition(RequestStatus.APPROVED.value, reviewer="supervisor") is True
        assert req.status == RequestStatus.APPROVED.value

    def test_transition_approved_to_executed(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        req.transition(RequestStatus.REVIEW.value)
        req.transition(RequestStatus.APPROVED.value, reviewer="supervisor")
        assert req.transition(RequestStatus.EXECUTED.value) is True
        assert req.executed_at is not None

    def test_transition_executed_to_closed(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        req.transition(RequestStatus.REVIEW.value)
        req.transition(RequestStatus.APPROVED.value, reviewer="supervisor")
        req.transition(RequestStatus.EXECUTED.value)
        assert req.transition(RequestStatus.CLOSED.value) is True

    def test_invalid_transition(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        # Can't go from PENDING to EXECUTED directly
        assert req.transition(RequestStatus.EXECUTED.value) is False

    def test_closed_is_terminal(self):
        req = CrossBorderRequest(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        req.transition(RequestStatus.DENIED.value, reviewer="admin")
        req.transition(RequestStatus.CLOSED.value)
        # No transitions from CLOSED
        assert req.transition(RequestStatus.PENDING.value) is False
        assert req.transition(RequestStatus.APPROVED.value) is False


# ─── PoliceAPI Endpoint Tests ───


class TestPoliceAPI:
    def test_match_entity(self, api, officer_session):
        result = api.match_entity(officer_session, "domain", "fraudster.com")
        assert isinstance(result, MatchResult)
        assert result.entity_type == "domain"
        assert result.entity_value == "fraudster.com"
        assert result.match_id.startswith("MATCH-")

    def test_match_entity_event_published(self, api, mock_event_bus, officer_session):
        api.match_entity(officer_session, "domain", "fraudster.com")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "police.match" in topics

    def test_match_entity_unauthorized(self, api):
        # Create a session with expired token
        auth = api.auth
        session = auth.authenticate("key-officer-001")
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(PermissionError):
            api.match_entity(session, "domain", "test.com")

    def test_submit_observation(self, api, officer_session):
        result = api.submit_observation(
            officer_session, "domain", "fraudster.com", "Known phishing domain"
        )
        assert isinstance(result, ObservationRecord)
        assert result.entity_value == "fraudster.com"
        assert result.observation_text == "Known phishing domain"
        assert result.id.startswith("OBS-")

    def test_submit_observation_audit_logged(self, api, officer_session):
        api.submit_observation(officer_session, "domain", "fraudster.com", "test")
        log = api.audit_log.query(endpoint=EndpointName.OBSERVATION.value)
        assert len(log) == 1

    def test_get_entity_intel(self, api, officer_session):
        result = api.get_entity_intel(officer_session, "ENT-001")
        assert isinstance(result, EntityIntel)
        assert result.entity_id == "ENT-001"

    def test_get_campaign_intel(self, api, officer_session):
        result = api.get_campaign_intel(officer_session, "CAMP-001")
        assert isinstance(result, CampaignIntel)
        assert result.campaign_id == "CAMP-001"

    def test_subscribe_monitor(self, api, officer_session):
        result = api.subscribe_monitor(officer_session, "ENT-001")
        assert result["status"] == "subscribed"
        assert "ENT-001" in api.subscriptions.get("ORG-001", [])

    def test_subscribe_monitor_idempotent(self, api, officer_session):
        api.subscribe_monitor(officer_session, "ENT-001")
        api.subscribe_monitor(officer_session, "ENT-001")
        assert api.subscriptions["ORG-001"].count("ENT-001") == 1

    def test_get_alerts(self, api, officer_session):
        result = api.get_alerts(officer_session)
        assert isinstance(result, list)

    def test_create_cross_border_request(self, api, supervisor_session):
        result = api.create_cross_border_request(
            supervisor_session,
            target_jurisdiction="DE",
            entity_id="ENT-001",
            entity_type="domain",
            request_reason="Investigation into phishing campaign",
        )
        assert isinstance(result, CrossBorderRequest)
        assert result.status == RequestStatus.PENDING.value
        assert result.target_jurisdiction == "DE"

    def test_create_cross_border_request_event_published(
        self, api, mock_event_bus, supervisor_session
    ):
        api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "police.cross_border_request" in topics

    def test_create_cross_border_request_officer_denied(self, api, officer_session):
        with pytest.raises(PermissionError):
            api.create_cross_border_request(officer_session, "DE", "ENT-001", "domain", "test")

    def test_get_request_status(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        result = api.get_request_status(supervisor_session, req.id)
        assert result is not None
        assert result.id == req.id

    def test_get_request_status_not_found(self, api, supervisor_session):
        result = api.get_request_status(supervisor_session, "nonexistent")
        assert result is None

    def test_review_request_approve(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        reviewed = api.review_cross_border_request(req.id, approved=True, reviewer="admin")
        assert reviewed.status == RequestStatus.APPROVED.value
        assert reviewed.reviewed_by == "admin"

    def test_review_request_deny(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        reviewed = api.review_cross_border_request(
            req.id, approved=False, reviewer="admin", denial_reason="Insufficient legal basis"
        )
        assert reviewed.status == RequestStatus.DENIED.value
        assert reviewed.denial_reason == "Insufficient legal basis"

    def test_execute_request(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        api.review_cross_border_request(req.id, approved=True, reviewer="admin")
        executed = api.execute_cross_border_request(req.id)
        assert executed.status == RequestStatus.EXECUTED.value
        assert executed.response_data is not None

    def test_execute_request_not_approved(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        result = api.execute_cross_border_request(req.id)
        assert result is None  # Can't execute without approval

    def test_close_request(self, api, supervisor_session):
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        api.review_cross_border_request(req.id, approved=True, reviewer="admin")
        api.execute_cross_border_request(req.id)
        closed = api.close_cross_border_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value

    def test_rate_limiting_enforced(self, api):
        # Create org with very low limit
        org = PoliceOrganization(
            org_id="ORG-LIMIT",
            name="Test",
            jurisdiction="LV",
            api_key="key-limit",
        )
        org.rate_limits[EndpointName.MATCH.value] = 3
        api.auth.register_organization(org)
        session = api.auth.authenticate("key-limit", role=PoliceRole.POLICE_OFFICER.value)

        # First 3 should work
        api.match_entity(session, "domain", "a.com")
        api.match_entity(session, "domain", "b.com")
        api.match_entity(session, "domain", "c.com")

        # 4th should fail
        with pytest.raises(PermissionError, match="Rate limit"):
            api.match_entity(session, "domain", "d.com")

    def test_all_api_calls_audited(self, api, officer_session):
        api.match_entity(officer_session, "domain", "test.com")
        api.submit_observation(officer_session, "domain", "test.com", "test")
        api.get_entity_intel(officer_session, "ENT-001")
        api.get_campaign_intel(officer_session, "CAMP-001")
        api.subscribe_monitor(officer_session, "ENT-001")
        api.get_alerts(officer_session)

        log = api.audit_log
        assert log.count == 6

    def test_invalid_api_key(self, api):
        session = api.auth.authenticate("invalid-key")
        assert session is None


# ─── Integration Tests ───


class TestIntegrationPoliceAPI:
    def test_full_investigation_pipeline(self, api, supervisor_session):
        """Full pipeline: match → entity intel → campaign intel → cross-border request."""
        # 1. Match entity
        match = api.match_entity(supervisor_session, "domain", "fraudster.com")
        assert match.match_id

        # 2. Get entity intel
        intel = api.get_entity_intel(supervisor_session, match.entity_id)
        assert intel.entity_id

        # 3. Get campaign intel
        camp = api.get_campaign_intel(supervisor_session, "CAMP-001")
        assert camp.campaign_id

        # 4. Subscribe to monitoring
        sub = api.subscribe_monitor(supervisor_session, match.entity_id)
        assert sub["status"] == "subscribed"

        # 5. Create cross-border request
        req = api.create_cross_border_request(
            supervisor_session,
            target_jurisdiction="DE",
            entity_id=match.entity_id,
            entity_type="domain",
            request_reason="Cross-border fraud investigation",
        )
        assert req.status == RequestStatus.PENDING.value

        # 6. Review and approve
        reviewed = api.review_cross_border_request(req.id, approved=True, reviewer="commissioner")
        assert reviewed.status == RequestStatus.APPROVED.value

        # 7. Execute
        executed = api.execute_cross_border_request(req.id)
        assert executed.status == RequestStatus.EXECUTED.value

        # 8. Close
        closed = api.close_cross_border_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value

        # 9. Check audit trail
        assert api.audit_log.count >= 5

    def test_cross_border_denial_pipeline(self, api, supervisor_session):
        """Cross-border request denied."""
        req = api.create_cross_border_request(supervisor_session, "DE", "ENT-001", "domain", "test")
        denied = api.review_cross_border_request(
            req.id, approved=False, reviewer="admin", denial_reason="No legal basis"
        )
        assert denied.status == RequestStatus.DENIED.value
        assert denied.denial_reason == "No legal basis"

        # Closed after denial
        closed = api.close_cross_border_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value

    def test_observations_stored(self, api, officer_session):
        """Multiple observations are stored and retrievable."""
        api.submit_observation(officer_session, "domain", "a.com", "Phishing")
        api.submit_observation(officer_session, "domain", "b.com", "Malware")
        api.submit_observation(officer_session, "ip", "1.2.3.4", "C2 server")
        assert len(api.observations) == 3
