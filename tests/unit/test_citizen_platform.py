"""Tests for Citizen Platform — Module 13.

Tests cover:
- CitizenCheckService: check, risk assessment, authorization, no results
- CitizenReportService: submit, track, status transitions, anonymous, validation
- CitizenAlertService: subscribe, unsubscribe, notify, no-leak
- Integration: end-to-end flow, rate limiting, authorization boundaries
"""

from unittest.mock import MagicMock

import pytest

from schemas.base import BaseEntity, BaseReport, Classification
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel
from services.citizen_platform import (
    VALID_TRANSITIONS,
    CitizenAlertService,
    CitizenCheckRequest,
    CitizenCheckService,
    CitizenReportRequest,
    CitizenReportService,
    ReportStatusUpdate,
    can_transition,
)

# ─── Fixtures ───


@pytest.fixture
def sample_entity():
    """A phone entity with fraud signals."""
    return BaseEntity(
        id="ENT-PHONE-001",
        entity_type=EntityType.PHONE,
        value="TEST-PHONE-001",
        normalized_value="test-phone-001",
        classification=Classification(classification=DataClassification.PUBLIC.value),
    )


@pytest.fixture
def restricted_entity():
    """A restricted entity that citizens should NOT see."""
    return BaseEntity(
        id="ENT-PHONE-002",
        entity_type=EntityType.PHONE,
        value="RESTRICTED-PHONE-001",
        normalized_value="restricted-phone-001",
        classification=Classification(classification=DataClassification.RESTRICTED.value),
    )


@pytest.fixture
def corroborated_report():
    return BaseReport(
        id="RPT-001",
        status=ReportStatus.CORROBORATED.value,
        category="phishing",
        description="Test phishing report",
        reporter_id="user-001",
        related_entity_ids=["ENT-PHONE-001"],
        related_evidence_ids=["EV-001", "EV-002", "EV-003"],
    )


@pytest.fixture
def unverified_report():
    return BaseReport(
        id="RPT-002",
        status=ReportStatus.UNVERIFIED.value,
        category="investment_fraud",
        description="Test investment fraud",
        reporter_id="user-002",
        related_entity_ids=["ENT-PHONE-001"],
    )


@pytest.fixture
def entity_store(sample_entity, restricted_entity):
    return {
        sample_entity.id: sample_entity,
        restricted_entity.id: restricted_entity,
    }


@pytest.fixture
def report_store(corroborated_report, unverified_report):
    return {
        "RPT-001": corroborated_report,
        "RPT-002": unverified_report,
    }


@pytest.fixture
def mock_rate_limiter():
    rl = MagicMock()
    rl.allow.return_value = (True, "ok")
    return rl


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def check_service(entity_store, report_store, mock_rate_limiter, mock_audit):
    return CitizenCheckService(
        entity_store=entity_store,
        report_store=report_store,
        rate_limiter=mock_rate_limiter,
        audit_logger=mock_audit,
    )


@pytest.fixture
def report_service(mock_event_bus, mock_rate_limiter, mock_audit):
    return CitizenReportService(
        entity_store={},
        event_bus=mock_event_bus,
        rate_limiter=mock_rate_limiter,
        audit_logger=mock_audit,
    )


@pytest.fixture
def alert_service(report_store, mock_rate_limiter, mock_audit):
    return CitizenAlertService(
        report_store=report_store,
        rate_limiter=mock_rate_limiter,
        audit_logger=mock_audit,
    )


# ─── State Machine Tests ───


class TestStateMachine:
    def test_valid_transition(self):
        assert can_transition(ReportStatus.UNVERIFIED.value, ReportStatus.UNDER_REVIEW.value)

    def test_invalid_transition(self):
        assert not can_transition(ReportStatus.UNVERIFIED.value, ReportStatus.VERIFIED.value)

    def test_same_status_is_noop(self):
        assert can_transition(ReportStatus.UNVERIFIED.value, ReportStatus.UNVERIFIED.value)

    def test_terminal_states_have_no_transitions(self):
        assert VALID_TRANSITIONS[ReportStatus.FALSE_POSITIVE.value] == set()
        assert VALID_TRANSITIONS[ReportStatus.OFFICIALLY_ESTABLISHED.value] == set()

    def test_verified_to_officially_established(self):
        assert can_transition(
            ReportStatus.VERIFIED.value, ReportStatus.OFFICIALLY_ESTABLISHED.value
        )

    def test_under_review_to_verified(self):
        assert can_transition(ReportStatus.UNDER_REVIEW.value, ReportStatus.VERIFIED.value)

    def test_corroborated_to_disputed(self):
        assert can_transition(ReportStatus.CORROBORATED.value, ReportStatus.DISPUTED.value)


# ─── Citizen Check Service Tests ───


class TestCitizenCheckService:
    def test_check_found_entity(self, check_service, sample_entity):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        response = check_service.check_entity(request, user_id="citizen-001")
        assert response.found is True
        assert response.entity_type == EntityType.PHONE.value
        assert response.report_count >= 0

    def test_check_not_found(self, check_service):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="UNKNOWN-PHONE-999",
        )
        response = check_service.check_entity(request)
        assert response.found is False
        assert response.risk_level == RiskLevel.UNKNOWN.value
        assert "No known fraud signals" in response.message

    def test_check_normalizes_value(self, check_service):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="  TEST-PHONE-001  ",
        )
        response = check_service.check_entity(request)
        assert response.normalized_value == "test-phone-001"

    def test_check_has_disclaimer(self, check_service):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        response = check_service.check_entity(request)
        assert "allegations" in response.disclaimer.lower()

    def test_citizen_cannot_see_restricted(self, check_service, restricted_entity):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="RESTRICTED-PHONE-001",
        )
        response = check_service.check_entity(request, user_role="citizen")
        # Should not find it because it's restricted
        assert response.found is False

    def test_admin_can_see_restricted(self, check_service):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="RESTRICTED-PHONE-001",
        )
        response = check_service.check_entity(request, user_role="admin")
        assert response.found is True

    def test_rate_limit_exceeded(self, entity_store, report_store):
        rl = MagicMock()
        rl.allow.return_value = (False, "rate limited")
        service = CitizenCheckService(
            entity_store=entity_store,
            report_store=report_store,
            rate_limiter=rl,
        )
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        with pytest.raises(PermissionError, match="Rate limit"):
            service.check_entity(request, user_id="citizen-001")

    def test_audit_logged(self, check_service, mock_audit):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        check_service.check_entity(request, user_id="citizen-001")
        mock_audit.log.assert_called_once()

    def test_risk_assessment_low(self, check_service):
        """Two reports (1 corroborated), 3 evidence → should be HIGH or above."""
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        response = check_service.check_entity(request)
        # 2 reports, 1 corroborated, 3 evidence → HIGH
        assert response.report_count == 2
        assert response.corroborated_count == 1
        assert response.evidence_count == 3
        assert response.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)

    def test_related_entities_summary_limited(self, check_service):
        """Related entities summary should be limited to 10 items."""
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        response = check_service.check_entity(request)
        assert len(response.related_entities_summary) <= 10

    def test_invalid_entity_type(self):
        with pytest.raises(ValueError, match="entity_type"):
            CitizenCheckRequest(entity_type="INVALID", value="test")

    def test_empty_value(self, check_service):
        request = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="",
        )
        response = check_service.check_entity(request)
        assert response.found is False


# ─── Citizen Report Service Tests ───


class TestCitizenReportService:
    def test_submit_report(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="I received a suspicious call from this number.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")
        assert response.report_id
        assert response.status == ReportStatus.UNVERIFIED.value

    def test_report_always_starts_unverified(self, report_service):
        request = CitizenReportRequest(
            category="investment_fraud",
            description="They asked for crypto.",
            entity_type=EntityType.URL.value,
            entity_value="https://suspicious.test",
            risk_level=RiskLevel.CRITICAL.value,  # even if citizen says critical
        )
        response = report_service.submit_report(request)
        assert response.status == ReportStatus.UNVERIFIED.value

    def test_anonymous_report(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Suspicious email.",
            entity_type=EntityType.EMAIL.value,
            entity_value="test@test.com",
            reporter_id=None,
        )
        response = report_service.submit_report(request)
        assert response.status == ReportStatus.UNVERIFIED.value
        # Should be retrievable
        report = report_service.get_report(response.report_id, user_role="admin")
        assert report is not None
        assert report.reporter_id is None

    def test_get_own_report(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Test report.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")
        report = report_service.get_report(response.report_id, user_id="citizen-001")
        assert report is not None
        assert report.id == response.report_id

    def test_cannot_view_others_report(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Test report.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")
        with pytest.raises(PermissionError, match="own reports"):
            report_service.get_report(response.report_id, user_id="citizen-002")

    def test_list_own_reports(self, report_service):
        for i in range(3):
            request = CitizenReportRequest(
                category="phishing",
                description=f"Report {i}.",
                entity_type=EntityType.PHONE.value,
                entity_value=f"TEST-PHONE-{i:03d}",
            )
            report_service.submit_report(request, user_id="citizen-001")

        # Submit one as a different user
        other_request = CitizenReportRequest(
            category="phishing",
            description="Other user report.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-999",
        )
        report_service.submit_report(other_request, user_id="citizen-002")

        reports = report_service.list_reports(user_id="citizen-001")
        assert len(reports) == 3

    def test_list_reports_pagination(self, report_service):
        for i in range(10):
            request = CitizenReportRequest(
                category="phishing",
                description=f"Report {i}.",
                entity_type=EntityType.PHONE.value,
                entity_value=f"TEST-PHONE-{i:03d}",
            )
            report_service.submit_report(request, user_id="citizen-001")

        page1 = report_service.list_reports(user_id="citizen-001", limit=5, offset=0)
        page2 = report_service.list_reports(user_id="citizen-001", limit=5, offset=5)
        assert len(page1) == 5
        assert len(page2) == 5

    def test_list_reports_max_50(self, report_service):
        for i in range(60):
            request = CitizenReportRequest(
                category="phishing",
                description=f"Report {i}.",
                entity_type=EntityType.PHONE.value,
                entity_value=f"TEST-PHONE-{i:03d}",
            )
            report_service.submit_report(request, user_id="citizen-001")

        reports = report_service.list_reports(user_id="citizen-001", limit=100)
        assert len(reports) <= 50

    def test_update_status_valid_transition(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")

        update = ReportStatusUpdate(
            report_id=response.report_id,
            new_status=ReportStatus.UNDER_REVIEW.value,
        )
        updated = report_service.update_status(update, user_role="admin")
        assert updated.status == ReportStatus.UNDER_REVIEW.value

    def test_update_status_invalid_transition(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")

        update = ReportStatusUpdate(
            report_id=response.report_id,
            new_status=ReportStatus.VERIFIED.value,  # can't go UNVERIFIED → VERIFIED
        )
        with pytest.raises(ValueError, match="Invalid status transition"):
            report_service.update_status(update, user_role="admin")

    def test_update_status_citizen_denied(self, report_service):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")

        update = ReportStatusUpdate(
            report_id=response.report_id,
            new_status=ReportStatus.UNDER_REVIEW.value,
        )
        with pytest.raises(PermissionError, match="authorized personnel"):
            report_service.update_status(update, user_role="citizen")

    def test_update_nonexistent_report(self, report_service):
        update = ReportStatusUpdate(
            report_id="NONEXISTENT",
            new_status=ReportStatus.UNDER_REVIEW.value,
        )
        with pytest.raises(ValueError, match="not found"):
            report_service.update_status(update, user_role="admin")

    def test_event_published_on_submit(self, report_service, mock_event_bus):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        report_service.submit_report(request, user_id="citizen-001")
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args.kwargs.get("topic") == "citizen.report.submitted"

    def test_event_published_on_status_change(self, report_service, mock_event_bus):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        response = report_service.submit_report(request, user_id="citizen-001")

        update = ReportStatusUpdate(
            report_id=response.report_id,
            new_status=ReportStatus.UNDER_REVIEW.value,
        )
        report_service.update_status(update, user_role="admin")
        # Should have 2 publish calls: submit + status change
        assert mock_event_bus.publish.call_count == 2

    def test_empty_category_rejected(self):
        with pytest.raises(ValueError, match="category"):
            CitizenReportRequest(
                category="",
                description="Test.",
                entity_type=EntityType.PHONE.value,
                entity_value="TEST-PHONE-001",
            )

    def test_empty_description_rejected(self):
        with pytest.raises(ValueError, match="description"):
            CitizenReportRequest(
                category="phishing",
                description="",
                entity_type=EntityType.PHONE.value,
                entity_value="TEST-PHONE-001",
            )

    def test_long_description_rejected(self):
        with pytest.raises(ValueError, match="5000"):
            CitizenReportRequest(
                category="phishing",
                description="x" * 5001,
                entity_type=EntityType.PHONE.value,
                entity_value="TEST-PHONE-001",
            )

    def test_rate_limit_on_submit(self, mock_event_bus):
        rl = MagicMock()
        rl.allow.return_value = (False, "rate limited")
        service = CitizenReportService(event_bus=mock_event_bus, rate_limiter=rl)
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        with pytest.raises(PermissionError, match="Rate limit"):
            service.submit_report(request)

    def test_audit_logged_on_submit(self, report_service, mock_audit):
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        report_service.submit_report(request, user_id="citizen-001")
        mock_audit.log.assert_called()

    def test_admin_can_list_all_reports(self, report_service):
        for i in range(3):
            request = CitizenReportRequest(
                category="phishing",
                description=f"Report {i}.",
                entity_type=EntityType.PHONE.value,
                entity_value=f"TEST-PHONE-{i:03d}",
            )
            report_service.submit_report(request, user_id=f"citizen-{i:03d}")

        reports = report_service.list_reports(user_id="admin-001", user_role="admin")
        assert len(reports) == 3


# ─── Citizen Alert Service Tests ───


class TestCitizenAlertService:
    def test_subscribe(self, alert_service):
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel="email",
            channel_address="citizen@test.com",
        )
        assert sub.id
        assert sub.active is True
        assert sub.subscriber_id == "citizen-001"

    def test_subscribe_requires_address(self, alert_service):
        with pytest.raises(ValueError, match="channel_address"):
            alert_service.subscribe(
                entity_type=EntityType.PHONE.value,
                entity_value="TEST-PHONE-001",
                subscriber_id="citizen-001",
                channel_address="",
            )

    def test_unsubscribe(self, alert_service):
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        result = alert_service.unsubscribe(sub.id, "citizen-001")
        assert result is True
        assert sub.id not in alert_service._subscriptions

    def test_unsubscribe_others_denied(self, alert_service):
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        with pytest.raises(PermissionError, match="own subscriptions"):
            alert_service.unsubscribe(sub.id, "citizen-002")

    def test_unsubscribe_nonexistent(self, alert_service):
        result = alert_service.unsubscribe("NONEXISTENT", "citizen-001")
        assert result is False

    def test_list_subscriptions(self, alert_service):
        for i in range(3):
            alert_service.subscribe(
                entity_type=EntityType.PHONE.value,
                entity_value=f"TEST-PHONE-{i:03d}",
                subscriber_id="citizen-001",
                channel_address="citizen@test.com",
            )
        # Another user
        alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-999",
            subscriber_id="citizen-002",
            channel_address="other@test.com",
        )

        subs = alert_service.list_subscriptions("citizen-001")
        assert len(subs) == 3

    def test_notify_on_new_report(self, alert_service):
        alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        notifications = alert_service.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            report_id="RPT-NEW-001",
            risk_level=RiskLevel.HIGH.value,
        )
        assert len(notifications) == 1
        assert "TEST-PHONE-001" in notifications[0].message
        assert "HIGH" in notifications[0].message

    def test_notify_no_match(self, alert_service):
        alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        notifications = alert_service.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="DIFFERENT-PHONE",
            report_id="RPT-NEW-001",
        )
        assert len(notifications) == 0

    def test_notify_different_entity_type(self, alert_service):
        alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        notifications = alert_service.notify_on_new_report(
            entity_type=EntityType.EMAIL.value,
            entity_value="TEST-PHONE-001",
            report_id="RPT-NEW-001",
        )
        assert len(notifications) == 0

    def test_notify_increments_count(self, alert_service):
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        alert_service.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            report_id="RPT-001",
        )
        assert sub.notified_count == 1
        assert sub.last_notified_at is not None

    def test_get_notifications(self, alert_service):
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        alert_service.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            report_id="RPT-001",
        )
        notifs = alert_service.get_notifications("citizen-001")
        assert len(notifs) == 1
        assert notifs[0].subscription_id == sub.id

    def test_notification_no_restricted_data(self, alert_service):
        """Alert messages should not contain restricted data."""
        sub = alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        notifs = alert_service.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            report_id="RPT-001",
            risk_level=RiskLevel.HIGH.value,
        )
        # Message should contain entity info but no case/LE data
        msg = notifs[0].message
        assert "RESTRICTED" not in msg
        assert "LAW_ENFORCEMENT" not in msg

    def test_rate_limit_on_subscribe(self):
        rl = MagicMock()
        rl.allow.return_value = (False, "rate limited")
        service = CitizenAlertService(rate_limiter=rl)
        with pytest.raises(PermissionError, match="Rate limit"):
            service.subscribe(
                entity_type=EntityType.PHONE.value,
                entity_value="TEST-PHONE-001",
                subscriber_id="citizen-001",
                channel_address="citizen@test.com",
            )

    def test_audit_on_subscribe(self, alert_service, mock_audit):
        alert_service.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )
        mock_audit.log.assert_called_once()


# ─── Integration Tests ───


class TestIntegration:
    def test_full_flow_check_report_alert(
        self, entity_store, report_store, mock_event_bus, mock_rate_limiter, mock_audit
    ):
        """End-to-end: citizen checks entity → submits report → gets alert."""
        # Setup services
        check_svc = CitizenCheckService(
            entity_store=entity_store,
            report_store=report_store,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        report_svc = CitizenReportService(
            entity_store=entity_store,
            event_bus=mock_event_bus,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        alert_svc = CitizenAlertService(
            report_store={},
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )

        # 1. Citizen checks entity
        check_req = CitizenCheckRequest(
            entity_type=EntityType.PHONE.value,
            value="TEST-PHONE-001",
        )
        check_resp = check_svc.check_entity(check_req, user_id="citizen-001")
        assert check_resp.found is True

        # 2. Citizen subscribes to alerts for this entity
        sub = alert_svc.subscribe(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            subscriber_id="citizen-001",
            channel_address="citizen@test.com",
        )

        # 3. Citizen submits a report
        report_req = CitizenReportRequest(
            category="phishing",
            description="This number called me with a phishing attempt.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        report_resp = report_svc.submit_report(report_req, user_id="citizen-001")
        assert report_resp.status == ReportStatus.UNVERIFIED.value

        # 4. Simulate alert trigger
        notifs = alert_svc.notify_on_new_report(
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
            report_id=report_resp.report_id,
        )
        assert len(notifs) == 1

        # 5. Citizen tracks their report
        report = report_svc.get_report(report_resp.report_id, user_id="citizen-001")
        assert report is not None
        assert report.status == ReportStatus.UNVERIFIED.value

    def test_authorization_boundary(self, mock_event_bus, mock_rate_limiter, mock_audit):
        """Citizen vs analyst vs admin boundaries."""
        report_svc = CitizenReportService(
            event_bus=mock_event_bus,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )

        # Citizen submits report
        request = CitizenReportRequest(
            category="phishing",
            description="Test.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        resp = report_svc.submit_report(request, user_id="citizen-001")

        # Another citizen cannot see it
        with pytest.raises(PermissionError):
            report_svc.get_report(resp.report_id, user_id="citizen-002")

        # Admin can see it
        report = report_svc.get_report(resp.report_id, user_id="admin-001", user_role="admin")
        assert report is not None

        # Admin can update status
        update = ReportStatusUpdate(
            report_id=resp.report_id,
            new_status=ReportStatus.UNDER_REVIEW.value,
        )
        updated = report_svc.update_status(update, user_role="admin")
        assert updated.status == ReportStatus.UNDER_REVIEW.value

        # Analyst can also update
        update2 = ReportStatusUpdate(
            report_id=resp.report_id,
            new_status=ReportStatus.CORROBORATED.value,
        )
        updated2 = report_svc.update_status(update2, user_role="analyst")
        assert updated2.status == ReportStatus.CORROBORATED.value

        # Citizen still cannot update
        with pytest.raises(PermissionError):
            report_svc.update_status(
                ReportStatusUpdate(
                    report_id=resp.report_id,
                    new_status=ReportStatus.UNDER_REVIEW.value,
                ),
                user_role="citizen",
            )

    def test_status_lifecycle(self, report_service):
        """Full report lifecycle: UNVERIFIED → UNDER_REVIEW → CORROBORATED → VERIFIED → OFFICIALLY_ESTABLISHED."""
        request = CitizenReportRequest(
            category="phishing",
            description="Test lifecycle.",
            entity_type=EntityType.PHONE.value,
            entity_value="TEST-PHONE-001",
        )
        resp = report_service.submit_report(request, user_id="citizen-001")

        # UNVERIFIED → UNDER_REVIEW
        r = report_service.update_status(
            ReportStatusUpdate(
                report_id=resp.report_id, new_status=ReportStatus.UNDER_REVIEW.value
            ),
            user_role="admin",
        )
        assert r.status == ReportStatus.UNDER_REVIEW.value

        # UNDER_REVIEW → CORROBORATED
        r = report_service.update_status(
            ReportStatusUpdate(
                report_id=resp.report_id, new_status=ReportStatus.CORROBORATED.value
            ),
            user_role="admin",
        )
        assert r.status == ReportStatus.CORROBORATED.value

        # CORROBORATED → VERIFIED
        r = report_service.update_status(
            ReportStatusUpdate(report_id=resp.report_id, new_status=ReportStatus.VERIFIED.value),
            user_role="admin",
        )
        assert r.status == ReportStatus.VERIFIED.value

        # VERIFIED → OFFICIALLY_ESTABLISHED
        r = report_service.update_status(
            ReportStatusUpdate(
                report_id=resp.report_id, new_status=ReportStatus.OFFICIALLY_ESTABLISHED.value
            ),
            user_role="admin",
        )
        assert r.status == ReportStatus.OFFICIALLY_ESTABLISHED.value

        # OFFICIALLY_ESTABLISHED is terminal — no further transitions
        with pytest.raises(ValueError, match="Invalid status transition"):
            report_service.update_status(
                ReportStatusUpdate(
                    report_id=resp.report_id, new_status=ReportStatus.DISPUTED.value
                ),
                user_role="admin",
            )
