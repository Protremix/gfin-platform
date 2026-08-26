"""Tests for Cross-Border Requests — Module 26.

Tests cover:
- RequestValidator: valid/invalid requests, missing fields
- RequestAuthorizer: authorized/denied, unregistered org, jurisdiction permissions
- RequestRouter: routing success/failure, jurisdiction mapping
- CrossBorderRequestEngine: full workflow (create → validate → authorize → route → review → decide → close)
- Status transitions: valid/invalid transitions
- Decision types: approve (with policy filtering), partial (with reason), deny (with reason)
- RequestAuditTrail: completeness, per-request retrieval
- Integration: full pipeline from request to response
"""

from unittest.mock import MagicMock

import pytest

from services.cross_border_requests import (
    CrossBorderRequestEngine,
    CrossBorderRequestRecord,
    RequestAuthorizer,
    RequestDecision,
    RequestRouter,
    RequestStatus,
    RequestValidator,
    UrgencyLevel,
)

# ─── Fixtures ───


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def authorizer():
    a = RequestAuthorizer()
    a.register_org("ORG-LV", {"DE", "FR", "ES"})
    a.register_org("ORG-DE", {"*"})
    return a


@pytest.fixture
def router():
    r = RequestRouter()
    r.register_jurisdiction("DE", "ORG-DE")
    r.register_jurisdiction("FR", "ORG-FR")
    r.register_jurisdiction("ES", "ORG-ES")
    return r


@pytest.fixture
def engine(mock_event_bus, authorizer, router):
    return CrossBorderRequestEngine(
        authorizer=authorizer,
        router=router,
        event_bus=mock_event_bus,
    )


@pytest.fixture
def valid_params():
    return {
        "requesting_org": "ORG-LV",
        "requesting_jurisdiction": "LV",
        "target_jurisdiction": "DE",
        "entity_id": "ENT-001",
        "entity_type": "domain",
        "investigator_name": "Detective Smith",
        "legal_basis": "EU Directive 2016/680 Art. 10",
        "purpose": "Fraud investigation - phishing campaign",
        "case_reference": "CASE-LV-2026-001",
        "entity_value": "fraudster.com",
        "requested_information": "Entity intelligence, first/last seen, related campaigns",
    }


# ─── RequestValidator Tests ───


class TestRequestValidator:
    def test_valid_request(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            investigator_name="Smith",
            legal_basis="EU Directive",
            purpose="Investigation",
            entity_id="ENT-001",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_legal_basis(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            investigator_name="Smith",
            legal_basis="",
            purpose="Investigation",
            entity_id="ENT-001",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert "Legal basis is required" in result.errors

    def test_missing_purpose(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            investigator_name="Smith",
            legal_basis="EU Directive",
            purpose="",
            entity_id="ENT-001",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert "Purpose is required" in result.errors

    def test_missing_investigator(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            investigator_name="",
            legal_basis="EU Directive",
            purpose="Investigation",
            entity_id="ENT-001",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert "Investigator name is required" in result.errors

    def test_same_jurisdiction(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="LV",
            investigator_name="Smith",
            legal_basis="EU Directive",
            purpose="Investigation",
            entity_id="ENT-001",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert "Target jurisdiction must differ" in result.errors[0]

    def test_missing_entity(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            investigator_name="Smith",
            legal_basis="EU Directive",
            purpose="Investigation",
            entity_id="",
            entity_type="domain",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert "Entity ID is required" in result.errors

    def test_multiple_errors(self):
        req = CrossBorderRequestRecord(
            id="CBR-001",
            requesting_org="",
            requesting_jurisdiction="LV",
            target_jurisdiction="LV",
            investigator_name="",
            legal_basis="",
            purpose="",
            entity_id="",
            entity_type="",
        )
        result = RequestValidator.validate(req)
        assert result.valid is False
        assert len(result.errors) >= 6


# ─── RequestAuthorizer Tests ───


class TestRequestAuthorizer:
    def test_authorized(self, authorizer):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        result = authorizer.authorize(req)
        assert result.authorized is True

    def test_unregistered_org(self, authorizer):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-UNKNOWN",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        result = authorizer.authorize(req)
        assert result.authorized is False
        assert "not registered" in result.reason

    def test_jurisdiction_not_permitted(self, authorizer):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="IT",
            entity_id="E1",
            entity_type="domain",
        )
        result = authorizer.authorize(req)
        assert result.authorized is False
        assert "not permitted" in result.reason

    def test_wildcard_permission(self, authorizer):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-DE",
            requesting_jurisdiction="DE",
            target_jurisdiction="FR",
            entity_id="E1",
            entity_type="domain",
        )
        result = authorizer.authorize(req)
        assert result.authorized is True


# ─── RequestRouter Tests ───


class TestRequestRouter:
    def test_route_success(self, router):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        result = router.route(req)
        assert result.routed is True
        assert result.destination_jurisdiction == "DE"
        assert result.destination_org == "ORG-DE"

    def test_route_no_org_for_jurisdiction(self, router):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="IT",
            entity_id="E1",
            entity_type="domain",
        )
        result = router.route(req)
        assert result.routed is False
        assert "No organization" in result.reason


# ─── CrossBorderRequestRecord Tests ───


class TestCrossBorderRequestRecord:
    def test_initial_status(self):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        assert req.status == RequestStatus.SUBMITTED.value
        assert req.decision == RequestDecision.NONE.value

    def test_valid_transitions(self):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        assert req.transition(RequestStatus.VALIDATED.value) is True
        assert req.validated_at is not None
        assert req.transition(RequestStatus.AUTHORIZED.value) is True
        assert req.transition(RequestStatus.ROUTED.value) is True
        assert req.transition(RequestStatus.REVIEWING.value) is True
        assert req.transition(RequestStatus.DECIDED.value) is True
        assert req.transition(RequestStatus.CLOSED.value) is True

    def test_invalid_transition(self):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        # Can't skip to REVIEWING
        assert req.transition(RequestStatus.REVIEWING.value) is False
        assert req.status == RequestStatus.SUBMITTED.value

    def test_rejected_transition(self):
        req = CrossBorderRequestRecord(
            id="R1",
            requesting_org="O1",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="E1",
            entity_type="domain",
        )
        assert req.transition(RequestStatus.REJECTED.value) is True
        assert req.status == RequestStatus.REJECTED.value
        assert req.transition(RequestStatus.CLOSED.value) is True


# ─── CrossBorderRequestEngine Tests ───


class TestCrossBorderRequestEngine:
    def test_create_request(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        assert req.id.startswith("CBR-")
        assert req.status == RequestStatus.SUBMITTED.value
        assert req.legal_basis == valid_params["legal_basis"]

    def test_validate_success(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        result = engine.validate_request(req.id)
        assert result.valid is True
        assert engine.get_request(req.id).status == RequestStatus.VALIDATED.value

    def test_validate_failure(self, engine, valid_params):
        params = {**valid_params, "legal_basis": ""}
        req = engine.create_request(**params)
        result = engine.validate_request(req.id)
        assert result.valid is False
        assert engine.get_request(req.id).status == RequestStatus.REJECTED.value

    def test_authorize_success(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        result = engine.authorize_request(req.id)
        assert result.authorized is True
        assert engine.get_request(req.id).status == RequestStatus.AUTHORIZED.value

    def test_authorize_unregistered(self, engine, valid_params):
        params = {**valid_params, "requesting_org": "ORG-UNKNOWN"}
        req = engine.create_request(**params)
        engine.validate_request(req.id)
        result = engine.authorize_request(req.id)
        assert result.authorized is False
        assert engine.get_request(req.id).status == RequestStatus.REJECTED.value

    def test_route_success(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        result = engine.route_request(req.id)
        assert result.routed is True
        assert engine.get_request(req.id).status == RequestStatus.ROUTED.value

    def test_start_review(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        assert engine.start_review(req.id, "Reviewer Mueller") is True
        assert engine.get_request(req.id).status == RequestStatus.REVIEWING.value
        assert engine.get_request(req.id).reviewer == "Reviewer Mueller"

    def test_start_review_wrong_state(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        assert engine.start_review(req.id, "Reviewer") is False

    def test_decision_approve(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        result = engine.make_decision(
            req.id,
            RequestDecision.APPROVED.value,
            "Reviewer",
            response_data={"entity_id": "E1", "jurisdiction": "DE", "suspect_names": ["Hidden"]},
        )
        assert result is not None
        assert result.decision == RequestDecision.APPROVED.value
        # Policy filtered — suspect_names should NOT be in response
        assert "suspect_names" not in engine.get_request(req.id).response_data
        assert "entity_id" in engine.get_request(req.id).response_data

    def test_decision_partial(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        result = engine.make_decision(
            req.id,
            RequestDecision.PARTIAL.value,
            "Reviewer",
            response_data={"entity_id": "E1", "jurisdiction": "DE"},
            partial_reason="Only partial data available",
        )
        assert result.decision == RequestDecision.PARTIAL.value
        assert engine.get_request(req.id).partial_reason == "Only partial data available"

    def test_decision_deny(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        result = engine.make_decision(
            req.id,
            RequestDecision.DENIED.value,
            "Reviewer",
            denial_reason="Insufficient legal basis for this request",
        )
        assert result.decision == RequestDecision.DENIED.value
        assert (
            engine.get_request(req.id).denial_reason == "Insufficient legal basis for this request"
        )

    def test_decision_wrong_state(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        result = engine.make_decision(req.id, RequestDecision.APPROVED.value, "R")
        assert result is None

    def test_close_request(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        engine.make_decision(req.id, RequestDecision.APPROVED.value, "Reviewer")
        closed = engine.close_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value

    def test_close_wrong_state(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        result = engine.close_request(req.id)
        assert result is None

    def test_route_event_published(self, engine, mock_event_bus, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "cross_border.routed" in topics

    def test_review_event_published(self, engine, mock_event_bus, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "cross_border.review_started" in topics

    def test_decision_event_published(self, engine, mock_event_bus, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        engine.make_decision(req.id, RequestDecision.APPROVED.value, "Reviewer")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "cross_border.decided" in topics

    def test_audit_trail_completeness(self, engine, valid_params):
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        engine.make_decision(req.id, RequestDecision.APPROVED.value, "Reviewer")
        engine.close_request(req.id)

        trail = engine.get_audit_trail(req.id)
        stages = [e.stage for e in trail]
        assert "SUBMITTED" in stages
        assert "VALIDATE" in stages
        assert "AUTHORIZE" in stages
        assert "ROUTE" in stages
        assert "REVIEW" in stages
        assert "DECISION" in stages
        assert "CLOSE" in stages
        assert len(trail) >= 7

    def test_urgency_levels(self, engine, valid_params):
        for urgency in [
            UrgencyLevel.ROUTINE.value,
            UrgencyLevel.PRIORITY.value,
            UrgencyLevel.EMERGENCY.value,
        ]:
            params = {**valid_params, "urgency": urgency}
            req = engine.create_request(**params)
            assert req.urgency == urgency

    def test_get_request_nonexistent(self, engine):
        assert engine.get_request("nonexistent") is None

    def test_get_audit_trail_empty(self, engine):
        assert engine.get_audit_trail("nonexistent") == []


# ─── Integration Tests ───


class TestIntegrationCrossBorder:
    def test_full_workflow_approve(self, engine, valid_params):
        """Full approved workflow: submit → validate → authorize → route → review → approve → close."""
        req = engine.create_request(**valid_params)
        assert engine.validate_request(req.id).valid is True
        assert engine.authorize_request(req.id).authorized is True
        assert engine.route_request(req.id).routed is True
        assert engine.start_review(req.id, "Reviewer Mueller") is True

        decision = engine.make_decision(
            req.id,
            RequestDecision.APPROVED.value,
            "Reviewer Mueller",
            response_data={
                "entity_id": "ENT-001",
                "jurisdiction": "DE",
                "first_seen": "2026-01-01",
            },
        )
        assert decision.decision == RequestDecision.APPROVED.value

        closed = engine.close_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value
        assert closed.decision == RequestDecision.APPROVED.value

        # Verify timestamps for each stage
        assert closed.submitted_at is not None
        assert closed.validated_at is not None
        assert closed.authorized_at is not None
        assert closed.routed_at is not None
        assert closed.review_started_at is not None
        assert closed.decided_at is not None
        assert closed.closed_at is not None

        # Verify audit trail
        trail = engine.get_audit_trail(req.id)
        assert len(trail) >= 7

    def test_full_workflow_deny(self, engine, valid_params):
        """Full denied workflow."""
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")

        decision = engine.make_decision(
            req.id,
            RequestDecision.DENIED.value,
            "Reviewer",
            denial_reason="No legal basis for this entity type",
        )
        assert decision.decision == RequestDecision.DENIED.value

        closed = engine.close_request(req.id)
        assert closed.decision == RequestDecision.DENIED.value
        assert closed.denial_reason == "No legal basis for this entity type"

    def test_full_workflow_partial(self, engine, valid_params):
        """Full partial approval workflow."""
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")

        decision = engine.make_decision(
            req.id,
            RequestDecision.PARTIAL.value,
            "Reviewer",
            response_data={"entity_id": "ENT-001", "jurisdiction": "DE"},
            partial_reason="Only entity registration data available, no case details",
        )
        assert decision.decision == RequestDecision.PARTIAL.value

        closed = engine.close_request(req.id)
        assert closed.decision == RequestDecision.PARTIAL.value
        assert "entity registration" in closed.partial_reason.lower()

    def test_workflow_rejected_at_validation(self, engine, valid_params):
        """Request rejected at validation stage."""
        params = {**valid_params, "legal_basis": ""}
        req = engine.create_request(**params)
        result = engine.validate_request(req.id)
        assert result.valid is False
        assert engine.get_request(req.id).status == RequestStatus.REJECTED.value

        # Can still close
        closed = engine.close_request(req.id)
        assert closed.status == RequestStatus.CLOSED.value

    def test_process_full_workflow_helper(self, engine, valid_params):
        """Test the convenience method that runs the full workflow."""
        req = engine.process_full_workflow(
            **valid_params,
            reviewer="Reviewer Mueller",
            decision=RequestDecision.APPROVED.value,
            response_data={"entity_id": "ENT-001", "jurisdiction": "DE"},
        )
        assert req is not None
        assert req.status == RequestStatus.CLOSED.value
        assert req.decision == RequestDecision.APPROVED.value

    def test_policy_filtering_on_response(self, engine, valid_params):
        """Response data is policy-filtered — suspect names don't cross the boundary."""
        req = engine.create_request(**valid_params)
        engine.validate_request(req.id)
        engine.authorize_request(req.id)
        engine.route_request(req.id)
        engine.start_review(req.id, "Reviewer")
        engine.make_decision(
            req.id,
            RequestDecision.APPROVED.value,
            "Reviewer",
            response_data={
                "entity_id": "ENT-001",
                "entity_type": "domain",
                "jurisdiction": "DE",
                "suspect_names": ["Hans Mueller", "Jane Smith"],
                "case_files": ["CASE-DE-001"],
                "investigation_notes": "Active investigation",
                "first_seen": "2026-01-01",
            },
        )
        response = engine.get_request(req.id).response_data
        assert "entity_id" in response
        assert "jurisdiction" in response
        assert "first_seen" in response
        assert "suspect_names" not in response
        assert "case_files" not in response
        assert "investigation_notes" not in response
