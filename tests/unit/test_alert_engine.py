"""Tests for Alert Engine — Module 18.

Tests cover:
- AlertRouter: priority-based routing, custom rules, digest detection
- NotificationService: delivery, logging, channels, mark delivered
- EscalationPolicy: levels, time-based escalation, acknowledge
- AlertTemplate: rendering, all alert types, variables
- AlertDigest: add, generate, clear, grouping
- AlertManager: process_alert, check_escalations, statistics, digest
- Integration: full alert pipeline
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from services.alert_engine import (
    AlertDigest,
    AlertManager,
    AlertRouter,
    AlertTemplate,
    DeliveryChannel,
    DeliveryStatus,
    EscalationLevel,
    EscalationPolicy,
    NotificationService,
    RoutingRule,
)
from services.continuous_monitoring import (
    AlertPriority,
    AlertType,
    DetectedChange,
    MonitoringAlert,
)

# ─── Fixtures ───


@pytest.fixture
def now():
    return datetime.now(UTC)


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def mock_audit():
    return MagicMock()


def make_alert(
    alert_type: str = AlertType.NEW_REPORT.value,
    priority: str = AlertPriority.MEDIUM.value,
    target_type: str = "entity",
    target_id: str = "ENT-001",
    acknowledged: bool = False,
    created_at: datetime | None = None,
    changes: list[DetectedChange] | None = None,
) -> MonitoringAlert:
    """Create a test alert."""
    if changes is None:
        changes = [
            DetectedChange(
                change_type="NEW_REPORTS",
                target_type=target_type,
                target_id=target_id,
                old_value=2,
                new_value=5,
                description="3 new reports",
            )
        ]
    return MonitoringAlert(
        id=f"ALT-TEST-{hash((alert_type, priority, target_id)) & 0xFFFFFF:06X}",
        subscription_id="SUB-001",
        target_type=target_type,
        target_id=target_id,
        alert_type=alert_type,
        priority=priority,
        changes=changes,
        description=f"Test alert for {target_id}",
        acknowledged=acknowledged,
        created_at=created_at or datetime.now(UTC),
    )


# ─── AlertRouter Tests ───


class TestAlertRouter:
    def test_route_urgent(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.URGENT.value)
        channels = router.route(alert)
        assert DeliveryChannel.EMAIL.value in channels
        assert DeliveryChannel.SMS.value in channels
        assert DeliveryChannel.WEBHOOK.value in channels
        assert DeliveryChannel.IN_APP.value in channels

    def test_route_high(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.HIGH.value)
        channels = router.route(alert)
        assert DeliveryChannel.EMAIL.value in channels
        assert DeliveryChannel.IN_APP.value in channels
        assert DeliveryChannel.SMS.value not in channels

    def test_route_medium(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.MEDIUM.value)
        channels = router.route(alert)
        assert DeliveryChannel.IN_APP.value in channels
        assert DeliveryChannel.EMAIL.value not in channels

    def test_route_low_digest_only(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.LOW.value)
        channels = router.route(alert)
        assert channels == []

    def test_is_digest_low(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.LOW.value)
        assert router.is_digest(alert) is True

    def test_is_digest_medium(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.MEDIUM.value)
        assert router.is_digest(alert) is True

    def test_is_digest_high(self):
        router = AlertRouter()
        alert = make_alert(priority=AlertPriority.HIGH.value)
        assert router.is_digest(alert) is False

    def test_custom_routing_rule(self):
        router = AlertRouter()
        rule = RoutingRule(
            id="RULE-001",
            name="Custom rule",
            alert_type=AlertType.RISK_ESCALATION.value,
            channels=[DeliveryChannel.SLACK.value],
        )
        router.add_routing_rule(rule)
        alert = make_alert(
            alert_type=AlertType.RISK_ESCALATION.value,
            priority=AlertPriority.HIGH.value,
        )
        channels = router.route(alert)
        assert channels == [DeliveryChannel.SLACK.value]

    def test_custom_rule_no_match(self):
        router = AlertRouter()
        rule = RoutingRule(
            id="RULE-001",
            alert_type=AlertType.RISK_ESCALATION.value,
            channels=[DeliveryChannel.SLACK.value],
        )
        router.add_routing_rule(rule)
        alert = make_alert(alert_type=AlertType.NEW_REPORT.value)
        channels = router.route(alert)
        # Should fall through to default routing
        assert DeliveryChannel.SLACK.value not in channels

    def test_custom_rule_digest_only(self):
        router = AlertRouter()
        rule = RoutingRule(
            id="RULE-001",
            priority=AlertPriority.HIGH.value,
            channels=[],
            immediate=False,
        )
        router.add_routing_rule(rule)
        alert = make_alert(priority=AlertPriority.HIGH.value)
        channels = router.route(alert)
        assert channels == []

    def test_remove_routing_rule(self):
        router = AlertRouter()
        rule = RoutingRule(id="RULE-001", channels=[DeliveryChannel.SLACK.value])
        router.add_routing_rule(rule)
        assert router.remove_routing_rule("RULE-001") is True
        assert router.remove_routing_rule("RULE-001") is False


# ─── NotificationService Tests ───


class TestNotificationService:
    def test_send_email(self):
        svc = NotificationService()
        record = svc.send(
            "ALT-001", DeliveryChannel.EMAIL.value, "user@test.com", "Subject", "Body"
        )
        assert record.alert_id == "ALT-001"
        assert record.channel == DeliveryChannel.EMAIL.value
        assert record.status == DeliveryStatus.SENT.value
        assert record.sent_at is not None

    def test_send_sms(self):
        svc = NotificationService()
        record = svc.send(
            "ALT-001", DeliveryChannel.SMS.value, "+1234567890", "SMS Subject", "SMS Body"
        )
        assert record.channel == DeliveryChannel.SMS.value

    def test_send_webhook(self):
        svc = NotificationService()
        record = svc.send(
            "ALT-001", DeliveryChannel.WEBHOOK.value, "https://hook.test", "Webhook", "Body"
        )
        assert record.channel == DeliveryChannel.WEBHOOK.value

    def test_get_delivery_log_all(self):
        svc = NotificationService()
        svc.send("ALT-001", DeliveryChannel.EMAIL.value, "user@test.com", "S1", "B1")
        svc.send("ALT-002", DeliveryChannel.SMS.value, "+1234", "S2", "B2")
        log = svc.get_delivery_log()
        assert len(log) == 2

    def test_get_delivery_log_by_alert(self):
        svc = NotificationService()
        svc.send("ALT-001", DeliveryChannel.EMAIL.value, "user@test.com", "S1", "B1")
        svc.send("ALT-002", DeliveryChannel.SMS.value, "+1234", "S2", "B2")
        log = svc.get_delivery_log(alert_id="ALT-001")
        assert len(log) == 1
        assert log[0].alert_id == "ALT-001"

    def test_get_delivery_log_by_channel(self):
        svc = NotificationService()
        svc.send("ALT-001", DeliveryChannel.EMAIL.value, "u@t.com", "S1", "B1")
        svc.send("ALT-002", DeliveryChannel.SMS.value, "+1234", "S2", "B2")
        log = svc.get_delivery_log(channel=DeliveryChannel.EMAIL.value)
        assert len(log) == 1
        assert log[0].channel == DeliveryChannel.EMAIL.value

    def test_mark_delivered(self):
        svc = NotificationService()
        record = svc.send("ALT-001", DeliveryChannel.EMAIL.value, "u@t.com", "S", "B")
        delivered = svc.mark_delivered(record.id)
        assert delivered.status == DeliveryStatus.DELIVERED.value

    def test_mark_delivered_nonexistent(self):
        svc = NotificationService()
        assert svc.mark_delivered("NONEXISTENT") is None


# ─── EscalationPolicy Tests ───


class TestEscalationPolicy:
    def test_register_alert(self, now):
        policy = EscalationPolicy()
        alert = make_alert(created_at=now)
        state = policy.register_alert(alert)
        assert state.alert_id == alert.id
        assert state.current_level == 0

    def test_no_escalation_initially(self, now):
        policy = EscalationPolicy()
        alert = make_alert(created_at=now)
        policy.register_alert(alert)
        level = policy.check_escalation(alert, now=now)
        assert level is None

    def test_escalate_to_level_1(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=20)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        level = policy.check_escalation(alert)
        assert level is not None
        assert level.level == 1

    def test_escalate_to_level_2(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=70)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        level = policy.check_escalation(alert)
        assert level is not None
        assert level.level >= 2

    def test_escalate_to_level_3(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=300)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        level = policy.check_escalation(alert)
        assert level is not None
        assert level.level == 3

    def test_no_escalation_if_acknowledged(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=300)
        alert = make_alert(created_at=created, acknowledged=True)
        policy.register_alert(alert)
        level = policy.check_escalation(alert)
        assert level is None

    def test_acknowledge_stops_escalation(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=20)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        # First check escalates
        level1 = policy.check_escalation(alert)
        assert level1 is not None
        # Acknowledge
        policy.acknowledge(alert.id)
        # Check again — no escalation
        level2 = policy.check_escalation(alert)
        assert level2 is None

    def test_get_current_level(self, now):
        policy = EscalationPolicy()
        alert = make_alert(created_at=now)
        policy.register_alert(alert)
        level = policy.get_current_level(alert.id)
        assert level is not None
        assert level.level == 0

    def test_custom_escalation_levels(self):
        custom_levels = [
            EscalationLevel(
                level=0, name="L0", delay_minutes=0, contacts=["a"], channels=["IN_APP"]
            ),
            EscalationLevel(
                level=1, name="L1", delay_minutes=5, contacts=["b"], channels=["EMAIL"]
            ),
        ]
        policy = EscalationPolicy(levels=custom_levels)
        created = datetime.now(UTC) - timedelta(minutes=10)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        level = policy.check_escalation(alert)
        assert level is not None
        assert level.name == "L1"

    def test_escalation_state_updated(self):
        policy = EscalationPolicy()
        created = datetime.now(UTC) - timedelta(minutes=20)
        alert = make_alert(created_at=created)
        policy.register_alert(alert)
        policy.check_escalation(alert)
        state = policy.get_state(alert.id)
        assert state.current_level == 1
        assert state.escalated_at is not None


# ─── AlertTemplate Tests ───


class TestAlertTemplate:
    def test_render_risk_escalation(self):
        alert = make_alert(
            alert_type=AlertType.RISK_ESCALATION.value,
            changes=[
                DetectedChange(
                    change_type="RISK_LEVEL_CHANGED",
                    target_type="entity",
                    target_id="ENT-001",
                    old_value="LOW",
                    new_value="HIGH",
                    description="Risk changed",
                )
            ],
        )
        rendered = AlertTemplate.render(alert)
        assert "RISK ESCALATION" in rendered["subject"]
        assert "HIGH" in rendered["body"]
        assert "LOW" in rendered["body"]

    def test_render_new_report(self):
        alert = make_alert(
            alert_type=AlertType.NEW_REPORT.value,
            changes=[
                DetectedChange(
                    change_type="NEW_REPORTS",
                    target_type="entity",
                    target_id="ENT-001",
                    old_value=2,
                    new_value=5,
                    description="3 new reports",
                )
            ],
        )
        rendered = AlertTemplate.render(alert)
        assert "NEW REPORT" in rendered["subject"]
        assert "5" in rendered["body"]

    def test_render_infrastructure_change(self):
        alert = make_alert(
            alert_type=AlertType.INFRASTRUCTURE_CHANGE.value,
            changes=[
                DetectedChange(
                    change_type="INFRASTRUCTURE_CHANGED",
                    target_type="entity",
                    target_id="ENT-001",
                    description="Infra changed",
                )
            ],
        )
        rendered = AlertTemplate.render(alert)
        assert "INFRASTRUCTURE CHANGE" in rendered["subject"]

    def test_render_campaign_update(self):
        alert = make_alert(
            alert_type=AlertType.CAMPAIGN_UPDATE.value,
            target_type="campaign",
        )
        rendered = AlertTemplate.render(alert)
        assert "CAMPAIGN UPDATE" in rendered["subject"]

    def test_render_activity_spike(self):
        alert = make_alert(
            alert_type=AlertType.ACTIVITY_SPIKE.value,
            changes=[
                DetectedChange(
                    change_type="ACTIVITY_SPIKE",
                    target_type="campaign",
                    target_id="CAMP-001",
                    old_value=3,
                    new_value=10,
                    description="Spike",
                )
            ],
        )
        rendered = AlertTemplate.render(alert)
        assert "ACTIVITY SPIKE" in rendered["subject"]
        assert "10" in rendered["body"]

    def test_render_status_change(self):
        alert = make_alert(
            alert_type=AlertType.STATUS_CHANGE.value,
            changes=[
                DetectedChange(
                    change_type="STATUS_CHANGED",
                    target_type="campaign",
                    target_id="CAMP-001",
                    old_value="ACTIVE",
                    new_value="DORMANT",
                    description="Status changed",
                )
            ],
        )
        rendered = AlertTemplate.render(alert)
        assert "STATUS CHANGE" in rendered["subject"]
        assert "DORMANT" in rendered["body"]
        assert "ACTIVE" in rendered["body"]

    def test_render_default_template(self):
        alert = make_alert(alert_type="UNKNOWN_TYPE")
        rendered = AlertTemplate.render(alert)
        assert "UNKNOWN_TYPE" in rendered["subject"]

    def test_render_contains_alert_id(self):
        alert = make_alert()
        rendered = AlertTemplate.render(alert)
        assert alert.id in rendered["body"]

    def test_render_contains_timestamp(self):
        alert = make_alert()
        rendered = AlertTemplate.render(alert)
        assert alert.created_at.isoformat() in rendered["body"]


# ─── AlertDigest Tests ───


class TestAlertDigest:
    def test_add_alert(self):
        digest = AlertDigest()
        alert = make_alert(priority=AlertPriority.LOW.value)
        digest.add(alert)
        assert digest.pending_count == 1

    def test_add_multiple(self):
        digest = AlertDigest()
        digest.add(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-001"))
        digest.add(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-002"))
        assert digest.pending_count == 2

    def test_generate_digest(self):
        digest = AlertDigest()
        digest.add(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-001"))
        digest.add(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-002"))
        summary = digest.generate_digest()
        assert summary.total_alerts == 2
        assert len(summary.entries) == 2
        assert summary.id.startswith("DIGEST-")

    def test_generate_digest_grouped_by_type(self):
        digest = AlertDigest()
        digest.add(
            make_alert(alert_type=AlertType.NEW_REPORT.value, priority=AlertPriority.LOW.value)
        )
        digest.add(
            make_alert(alert_type=AlertType.NEW_REPORT.value, priority=AlertPriority.LOW.value)
        )
        digest.add(
            make_alert(alert_type=AlertType.RISK_ESCALATION.value, priority=AlertPriority.LOW.value)
        )
        summary = digest.generate_digest()
        assert summary.by_type.get(AlertType.NEW_REPORT.value) == 2
        assert summary.by_type.get(AlertType.RISK_ESCALATION.value) == 1

    def test_generate_digest_grouped_by_target(self):
        digest = AlertDigest()
        digest.add(make_alert(target_id="ENT-001", priority=AlertPriority.LOW.value))
        digest.add(make_alert(target_id="ENT-001", priority=AlertPriority.LOW.value))
        digest.add(make_alert(target_id="ENT-002", priority=AlertPriority.LOW.value))
        summary = digest.generate_digest()
        assert len(summary.by_target["entity:ENT-001"]) == 2
        assert len(summary.by_target["entity:ENT-002"]) == 1

    def test_digest_summary_text(self):
        digest = AlertDigest()
        digest.add(make_alert(priority=AlertPriority.LOW.value))
        summary = digest.generate_digest()
        assert "GFIN Alert Digest" in summary.summary_text
        assert "1 alert" in summary.summary_text

    def test_clear_digest(self):
        digest = AlertDigest()
        digest.add(make_alert(priority=AlertPriority.LOW.value))
        digest.add(make_alert(priority=AlertPriority.LOW.value))
        cleared = digest.clear()
        assert cleared == 2
        assert digest.pending_count == 0

    def test_empty_digest(self):
        digest = AlertDigest()
        summary = digest.generate_digest()
        assert summary.total_alerts == 0


# ─── AlertManager Tests ───


class TestAlertManager:
    def test_process_urgent_alert(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(priority=AlertPriority.URGENT.value)
        result = mgr.process_alert(alert)
        assert result["alert_id"] == alert.id
        assert len(result["deliveries"]) >= 3  # email + sms + webhook + in_app
        assert DeliveryChannel.EMAIL.value in result["channels"]

    def test_process_low_alert_to_digest(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(priority=AlertPriority.LOW.value)
        result = mgr.process_alert(alert)
        assert result["channels"] == []
        assert result["digest_queued"] is True

    def test_process_medium_alert(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(priority=AlertPriority.MEDIUM.value)
        result = mgr.process_alert(alert)
        assert DeliveryChannel.IN_APP.value in result["channels"]
        assert result["digest_queued"] is True  # Medium is digest-eligible

    def test_event_published_on_route(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert()
        mgr.process_alert(alert)
        mock_event_bus.publish.assert_called()
        topics = [call.kwargs["topic"] for call in mock_event_bus.publish.call_args_list]
        assert "alert.routed" in topics

    def test_audit_logged_on_process(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert()
        mgr.process_alert(alert)
        mock_audit.log.assert_called_once()

    def test_check_escalations_none_needed(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(created_at=datetime.now(UTC))
        mgr.process_alert(alert)
        results = mgr.check_escalations()
        assert len(results) == 0

    def test_check_escalations_triggered(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            priority=AlertPriority.URGENT.value,
            created_at=datetime.now(UTC) - timedelta(minutes=20),
        )
        mgr.process_alert(alert)
        results = mgr.check_escalations()
        assert len(results) >= 1
        assert results[0]["escalated_to_level"] >= 1

    def test_check_escalations_event_published(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            priority=AlertPriority.URGENT.value,
            created_at=datetime.now(UTC) - timedelta(minutes=20),
        )
        mgr.process_alert(alert)
        mgr.check_escalations()
        topics = [call.kwargs["topic"] for call in mock_event_bus.publish.call_args_list]
        assert "alert.escalated" in topics

    def test_check_escalations_skips_acknowledged(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            acknowledged=True,
            created_at=datetime.now(UTC) - timedelta(minutes=300),
        )
        mgr.process_alert(alert)
        results = mgr.check_escalations()
        assert len(results) == 0

    def test_get_statistics(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        mgr.process_alert(
            make_alert(
                priority=AlertPriority.HIGH.value, alert_type=AlertType.RISK_ESCALATION.value
            )
        )
        mgr.process_alert(
            make_alert(priority=AlertPriority.MEDIUM.value, alert_type=AlertType.NEW_REPORT.value)
        )
        mgr.process_alert(
            make_alert(priority=AlertPriority.LOW.value, alert_type=AlertType.NEW_REPORT.value)
        )
        stats = mgr.get_statistics()
        assert stats.total == 3
        assert stats.by_priority[AlertPriority.HIGH.value] == 1
        assert stats.by_priority[AlertPriority.MEDIUM.value] == 1
        assert stats.by_priority[AlertPriority.LOW.value] == 1
        assert stats.unacknowledged == 3
        assert stats.acknowledged == 0

    def test_get_statistics_with_escalated(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            priority=AlertPriority.URGENT.value,
            created_at=datetime.now(UTC) - timedelta(minutes=20),
        )
        mgr.process_alert(alert)
        mgr.check_escalations()
        stats = mgr.get_statistics()
        assert stats.escalated >= 1

    def test_get_digest(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        mgr.process_alert(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-001"))
        mgr.process_alert(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-002"))
        digest = mgr.get_digest()
        assert digest.total_alerts == 2
        # Digest should be cleared after get
        digest2 = mgr.get_digest()
        assert digest2.total_alerts == 0

    def test_get_delivery_log(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(priority=AlertPriority.URGENT.value)
        mgr.process_alert(alert)
        log = mgr.get_delivery_log(alert_id=alert.id)
        assert len(log) >= 3  # urgent = email + sms + webhook + in_app

    def test_all_alerts_tracked(self, mock_event_bus, mock_audit):
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        mgr.process_alert(make_alert())
        mgr.process_alert(make_alert(alert_type=AlertType.RISK_ESCALATION.value))
        assert len(mgr.all_alerts) == 2


# ─── Integration Tests ───


class TestIntegrationAlertEngine:
    def test_full_pipeline_urgent(self, mock_event_bus, mock_audit):
        """Full pipeline: create → route → template → send → register escalation."""
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            alert_type=AlertType.RISK_ESCALATION.value,
            priority=AlertPriority.URGENT.value,
            changes=[
                DetectedChange(
                    change_type="RISK_LEVEL_CHANGED",
                    target_type="entity",
                    target_id="ENT-001",
                    old_value="LOW",
                    new_value="CRITICAL",
                    description="Risk escalated to CRITICAL",
                )
            ],
        )
        result = mgr.process_alert(alert)
        assert len(result["deliveries"]) >= 3
        assert mock_event_bus.publish.called

    def test_full_pipeline_escalation_flow(self, mock_event_bus, mock_audit):
        """Alert → no acknowledgement → escalation after time."""
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            priority=AlertPriority.HIGH.value,
            created_at=datetime.now(UTC) - timedelta(minutes=65),
        )
        mgr.process_alert(alert)

        # Check escalations — should escalate to level 2
        escalations = mgr.check_escalations()
        assert len(escalations) == 1
        assert escalations[0]["escalated_to_level"] >= 2

        # Verify escalation delivery
        log = mgr.get_delivery_log(alert_id=alert.id)
        # Original delivery + escalation deliveries
        assert len(log) >= 3

    def test_full_pipeline_digest_flow(self, mock_event_bus, mock_audit):
        """Low priority alerts go to digest, not immediate delivery."""
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        mgr.process_alert(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-001"))
        mgr.process_alert(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-002"))
        mgr.process_alert(make_alert(priority=AlertPriority.LOW.value, target_id="ENT-001"))

        # No immediate deliveries for low priority
        log = mgr.get_delivery_log()
        assert len(log) == 0

        # Digest should have 3 alerts
        digest = mgr.get_digest()
        assert digest.total_alerts == 3
        assert "entity:ENT-001" in digest.by_target

    def test_full_pipeline_acknowledged_no_escalation(self, mock_event_bus, mock_audit):
        """Acknowledged alert should not escalate."""
        mgr = AlertManager(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = make_alert(
            priority=AlertPriority.URGENT.value,
            acknowledged=True,
            created_at=datetime.now(UTC) - timedelta(minutes=300),
        )
        mgr.process_alert(alert)
        escalations = mgr.check_escalations()
        assert len(escalations) == 0
