"""Tests for Continuous Monitoring — Module 17.

Tests cover:
- SubscriptionService: subscribe, unsubscribe, list, deduplication
- ChangeDetector: entity changes (risk, reports, infra, campaign), campaign changes
- AlertEngine: evaluate changes, alert types, priorities, acknowledge
- MonitoringEngine: run_check, evaluate, get_status
- Integration: full monitoring loop
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from schemas.base import AuditMetadata, BaseEntity, BaseReport, Classification
from schemas.entities import CampaignEntity
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel
from services.continuous_monitoring import (
    AlertEngine,
    AlertPriority,
    AlertType,
    CampaignSnapshot,
    ChangeDetector,
    ChangeType,
    DetectedChange,
    EntitySnapshot,
    MonitoringEngine,
    SubscriptionService,
    WatchType,
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


@pytest.fixture
def entity_store():
    return {
        "ENT-001": BaseEntity(
            id="ENT-001",
            entity_type=EntityType.URL,
            value="https://scam.test",
            normalized_value="https://scam.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
            metadata={"ip_addresses": ["1.2.3.4"]},
        ),
    }


@pytest.fixture
def report_store(now):
    return {
        "RPT-001": BaseReport(
            id="RPT-001",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Report 1.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        ),
    }


@pytest.fixture
def campaign_store():
    return {
        "CAMP-001": CampaignEntity(
            id="CAMP-001",
            name="Test Campaign",
            campaign_status="ACTIVE",
            severity=RiskLevel.MEDIUM.value,
            fraud_type="phishing",
            related_entity_ids=["ENT-001"],
            entity_count=1,
        ),
    }


# ─── Subscription Service Tests ───


class TestSubscriptionService:
    def test_subscribe_entity(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "entity", "ENT-001")
        assert sub.subscriber_id == "user-001"
        assert sub.target_type == "entity"
        assert sub.target_id == "ENT-001"
        assert sub.active is True

    def test_subscribe_campaign(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "campaign", "CAMP-001")
        assert sub.target_type == "campaign"

    def test_subscribe_with_watch_types(self):
        svc = SubscriptionService()
        sub = svc.subscribe(
            "user-001",
            "entity",
            "ENT-001",
            watch_types=[WatchType.RISK_LEVEL_CHANGED.value, WatchType.NEW_REPORTS.value],
        )
        assert len(sub.watch_types) == 2

    def test_subscribe_default_all(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "entity", "ENT-001")
        assert WatchType.ALL.value in sub.watch_types

    def test_subscribe_invalid_target_type(self):
        svc = SubscriptionService()
        with pytest.raises(ValueError, match="target_type"):
            svc.subscribe("user-001", "invalid", "ENT-001")

    def test_subscribe_dedup(self):
        svc = SubscriptionService()
        sub1 = svc.subscribe("user-001", "entity", "ENT-001")
        sub2 = svc.subscribe("user-001", "entity", "ENT-001")
        assert sub1.id == sub2.id

    def test_unsubscribe(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "entity", "ENT-001")
        assert svc.unsubscribe(sub.id) is True
        assert sub.active is False

    def test_unsubscribe_nonexistent(self):
        svc = SubscriptionService()
        assert svc.unsubscribe("NONEXISTENT") is False

    def test_get_subscription(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "entity", "ENT-001")
        assert svc.get_subscription(sub.id) is not None

    def test_list_subscriptions(self):
        svc = SubscriptionService()
        svc.subscribe("user-001", "entity", "ENT-001")
        svc.subscribe("user-002", "entity", "ENT-002")
        subs = svc.list_subscriptions()
        assert len(subs) == 2

    def test_list_by_subscriber(self):
        svc = SubscriptionService()
        svc.subscribe("user-001", "entity", "ENT-001")
        svc.subscribe("user-002", "entity", "ENT-002")
        subs = svc.list_subscriptions(subscriber_id="user-001")
        assert len(subs) == 1
        assert subs[0].subscriber_id == "user-001"

    def test_list_by_target(self):
        svc = SubscriptionService()
        svc.subscribe("user-001", "entity", "ENT-001")
        svc.subscribe("user-002", "entity", "ENT-002")
        subs = svc.list_subscriptions(target_id="ENT-001")
        assert len(subs) == 1
        assert subs[0].target_id == "ENT-001"

    def test_list_inactive(self):
        svc = SubscriptionService()
        sub = svc.subscribe("user-001", "entity", "ENT-001")
        svc.unsubscribe(sub.id)
        active = svc.list_subscriptions(active_only=True)
        inactive = svc.list_subscriptions(active_only=False)
        assert len(active) == 0
        assert len(inactive) == 1


# ─── Change Detector Tests ───


class TestChangeDetector:
    def test_capture_entity_snapshot(self, entity_store, report_store, campaign_store):
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        snapshot = detector.capture_entity_snapshot("ENT-001")
        assert snapshot.entity_id == "ENT-001"
        assert snapshot.report_count == 1
        assert "CAMP-001" in snapshot.campaign_ids

    def test_capture_nonexistent_entity(self):
        detector = ChangeDetector()
        snapshot = detector.capture_entity_snapshot("NONEXISTENT")
        assert snapshot.entity_id == "NONEXISTENT"
        assert snapshot.report_count == 0

    def test_capture_campaign_snapshot(self, report_store, campaign_store):
        detector = ChangeDetector(report_store=report_store, campaign_store=campaign_store)
        snapshot = detector.capture_campaign_snapshot("CAMP-001")
        assert snapshot.campaign_id == "CAMP-001"
        assert snapshot.status == "ACTIVE"
        assert snapshot.report_count == 1

    def test_detect_entity_risk_change(self):
        detector = ChangeDetector()
        old = EntitySnapshot(entity_id="ENT-001", risk_level="LOW")
        new = EntitySnapshot(entity_id="ENT-001", risk_level="HIGH")
        changes = detector.detect_entity_changes("ENT-001", old, new)
        risk_changes = [c for c in changes if c.change_type == ChangeType.RISK_LEVEL_CHANGED.value]
        assert len(risk_changes) == 1
        assert risk_changes[0].old_value == "LOW"
        assert risk_changes[0].new_value == "HIGH"

    def test_detect_entity_new_reports(self):
        detector = ChangeDetector()
        old = EntitySnapshot(entity_id="ENT-001", report_count=2)
        new = EntitySnapshot(entity_id="ENT-001", report_count=5)
        changes = detector.detect_entity_changes("ENT-001", old, new)
        report_changes = [c for c in changes if c.change_type == ChangeType.NEW_REPORTS.value]
        assert len(report_changes) == 1
        assert "3 new report" in report_changes[0].description

    def test_detect_entity_infra_change(self):
        detector = ChangeDetector()
        old = EntitySnapshot(entity_id="ENT-001", infrastructure_hash="ip:1.2.3.4")
        new = EntitySnapshot(entity_id="ENT-001", infrastructure_hash="ip:5.6.7.8")
        changes = detector.detect_entity_changes("ENT-001", old, new)
        infra_changes = [
            c for c in changes if c.change_type == ChangeType.INFRASTRUCTURE_CHANGED.value
        ]
        assert len(infra_changes) == 1

    def test_detect_entity_campaign_linked(self):
        detector = ChangeDetector()
        old = EntitySnapshot(entity_id="ENT-001", campaign_ids=[])
        new = EntitySnapshot(entity_id="ENT-001", campaign_ids=["CAMP-001"])
        changes = detector.detect_entity_changes("ENT-001", old, new)
        camp_changes = [c for c in changes if c.change_type == ChangeType.CAMPAIGN_LINKED.value]
        assert len(camp_changes) == 1

    def test_detect_no_changes(self):
        detector = ChangeDetector()
        old = EntitySnapshot(entity_id="ENT-001", risk_level="LOW", report_count=5)
        new = EntitySnapshot(entity_id="ENT-001", risk_level="LOW", report_count=5)
        changes = detector.detect_entity_changes("ENT-001", old, new)
        assert len(changes) == 0

    def test_detect_campaign_status_change(self):
        detector = ChangeDetector()
        old = CampaignSnapshot(campaign_id="CAMP-001", status="ACTIVE")
        new = CampaignSnapshot(campaign_id="CAMP-001", status="DISMANTLED")
        changes = detector.detect_campaign_changes("CAMP-001", old, new)
        status_changes = [c for c in changes if c.change_type == ChangeType.STATUS_CHANGED.value]
        assert len(status_changes) == 1

    def test_detect_campaign_severity_change(self):
        detector = ChangeDetector()
        old = CampaignSnapshot(campaign_id="CAMP-001", severity="LOW")
        new = CampaignSnapshot(campaign_id="CAMP-001", severity="HIGH")
        changes = detector.detect_campaign_changes("CAMP-001", old, new)
        sev_changes = [c for c in changes if c.change_type == ChangeType.SEVERITY_CHANGED.value]
        assert len(sev_changes) == 1

    def test_detect_campaign_new_entities(self):
        detector = ChangeDetector()
        old = CampaignSnapshot(campaign_id="CAMP-001", entity_count=2)
        new = CampaignSnapshot(campaign_id="CAMP-001", entity_count=5)
        changes = detector.detect_campaign_changes("CAMP-001", old, new)
        entity_changes = [c for c in changes if c.change_type == ChangeType.NEW_ENTITIES.value]
        assert len(entity_changes) == 1

    def test_detect_campaign_activity_spike(self):
        detector = ChangeDetector()
        old = CampaignSnapshot(campaign_id="CAMP-001", report_count=3)
        new = CampaignSnapshot(campaign_id="CAMP-001", report_count=10)
        changes = detector.detect_campaign_changes("CAMP-001", old, new)
        spike_changes = [c for c in changes if c.change_type == ChangeType.ACTIVITY_SPIKE.value]
        assert len(spike_changes) == 1

    def test_detect_campaign_no_changes(self):
        detector = ChangeDetector()
        old = CampaignSnapshot(campaign_id="CAMP-001", status="ACTIVE", severity="LOW")
        new = CampaignSnapshot(campaign_id="CAMP-001", status="ACTIVE", severity="LOW")
        changes = detector.detect_campaign_changes("CAMP-001", old, new)
        assert len(changes) == 0


# ─── Alert Engine Tests ───


class TestAlertEngine:
    def test_evaluate_risk_escalation(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.RISK_LEVEL_CHANGED.value,
                target_type="entity",
                target_id="ENT-001",
                old_value="LOW",
                new_value="HIGH",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        assert alert is not None
        assert alert.alert_type == AlertType.RISK_ESCALATION.value
        assert alert.priority == AlertPriority.HIGH.value

    def test_evaluate_new_report(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        assert alert is not None
        assert alert.alert_type == AlertType.NEW_REPORT.value
        assert alert.priority == AlertPriority.MEDIUM.value

    def test_evaluate_infra_change(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.INFRASTRUCTURE_CHANGED.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        assert alert is not None
        assert alert.alert_type == AlertType.INFRASTRUCTURE_CHANGE.value

    def test_evaluate_status_change(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.STATUS_CHANGED.value,
                target_type="campaign",
                target_id="CAMP-001",
                old_value="ACTIVE",
                new_value="DISMANTLED",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "campaign", "CAMP-001", changes)
        assert alert is not None
        assert alert.alert_type == AlertType.STATUS_CHANGE.value
        assert alert.priority == AlertPriority.URGENT.value

    def test_evaluate_activity_spike(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.ACTIVITY_SPIKE.value,
                target_type="campaign",
                target_id="CAMP-001",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "campaign", "CAMP-001", changes)
        assert alert is not None
        assert alert.priority == AlertPriority.URGENT.value

    def test_evaluate_no_changes(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", [])
        assert alert is None

    def test_evaluate_multi_change_takes_highest_priority(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            ),
            DetectedChange(
                change_type=ChangeType.STATUS_CHANGED.value,
                target_type="entity",
                target_id="ENT-001",
            ),
        ]
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        # STATUS_CHANGED is URGENT, higher than NEW_REPORTS MEDIUM
        assert alert.priority == AlertPriority.URGENT.value

    def test_event_published(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        mock_event_bus.publish.assert_called_once()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "alert.created"

    def test_audit_logged(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        mock_audit.log.assert_called_once()

    def test_get_alerts_by_target(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        alerts = engine.get_alerts(target_id="ENT-001")
        assert len(alerts) == 1
        alerts_other = engine.get_alerts(target_id="ENT-999")
        assert len(alerts_other) == 0

    def test_get_unacknowledged(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        unack = engine.get_alerts(unacknowledged_only=True)
        assert len(unack) == 1
        engine.acknowledge_alert(unack[0].id)
        unack_after = engine.get_alerts(unacknowledged_only=True)
        assert len(unack_after) == 0

    def test_acknowledge_alert(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        changes = [
            DetectedChange(
                change_type=ChangeType.NEW_REPORTS.value,
                target_type="entity",
                target_id="ENT-001",
            )
        ]
        alert = engine.evaluate_changes("SUB-001", "entity", "ENT-001", changes)
        acknowledged = engine.acknowledge_alert(alert.id, user_id="admin-001")
        assert acknowledged.acknowledged is True
        assert acknowledged.acknowledged_by == "admin-001"
        assert acknowledged.acknowledged_at is not None

    def test_acknowledge_nonexistent(self, mock_event_bus, mock_audit):
        engine = AlertEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        assert engine.acknowledge_alert("NONEXISTENT") is None


# ─── Monitoring Engine Tests ───


class TestMonitoringEngine:
    def test_run_check_no_subscriptions(self, mock_event_bus, mock_audit):
        engine = MonitoringEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        alerts = engine.run_check()
        assert len(alerts) == 0
        assert engine.check_count == 1

    def test_run_check_first_check_no_alert(
        self, mock_event_bus, mock_audit, entity_store, report_store, campaign_store
    ):
        """First check should just store baseline, no alert."""
        sub_svc = SubscriptionService()
        sub_svc.subscribe("user-001", "entity", "ENT-001")
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        engine = MonitoringEngine(
            subscription_service=sub_svc,
            change_detector=detector,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        alerts = engine.run_check()
        assert len(alerts) == 0  # First check = baseline

    def test_run_check_detects_change(
        self, mock_event_bus, mock_audit, entity_store, report_store, campaign_store
    ):
        """Second check should detect changes and create alert."""
        sub_svc = SubscriptionService()
        sub_svc.subscribe("user-001", "entity", "ENT-001")
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        engine = MonitoringEngine(
            subscription_service=sub_svc,
            change_detector=detector,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )

        # First check — baseline
        engine.run_check()

        # Add a new report
        report_store["RPT-002"] = BaseReport(
            id="RPT-002",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="New report.",
            reporter_id="citizen-002",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=datetime.now(UTC)),
        )

        # Second check — should detect new report
        alerts = engine.run_check()
        assert len(alerts) >= 1
        assert alerts[0].alert_type == AlertType.NEW_REPORT.value

    def test_run_check_campaign_change(
        self, mock_event_bus, mock_audit, entity_store, report_store, campaign_store
    ):
        sub_svc = SubscriptionService()
        sub_svc.subscribe("user-001", "campaign", "CAMP-001")
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        engine = MonitoringEngine(
            subscription_service=sub_svc,
            change_detector=detector,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )

        # First check — baseline
        engine.run_check()

        # Change campaign status
        campaign_store["CAMP-001"].campaign_status = "DORMANT"

        # Second check
        alerts = engine.run_check()
        assert len(alerts) >= 1
        assert alerts[0].alert_type == AlertType.STATUS_CHANGE.value

    def test_get_status(
        self, mock_event_bus, mock_audit, entity_store, report_store, campaign_store
    ):
        sub_svc = SubscriptionService()
        sub_svc.subscribe("user-001", "entity", "ENT-001")
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        engine = MonitoringEngine(
            subscription_service=sub_svc,
            change_detector=detector,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        engine.run_check()
        status = engine.get_status("entity", "ENT-001")
        assert status["target_id"] == "ENT-001"
        assert status["has_snapshot"] is True
        assert status["total_alerts"] == 0

    def test_watch_type_filter(
        self, mock_event_bus, mock_audit, entity_store, report_store, campaign_store
    ):
        """Only watch for risk level changes, ignore new reports."""
        sub_svc = SubscriptionService()
        sub_svc.subscribe(
            "user-001", "entity", "ENT-001", watch_types=[WatchType.RISK_LEVEL_CHANGED.value]
        )
        detector = ChangeDetector(
            report_store=report_store,
            entity_store=entity_store,
            campaign_store=campaign_store,
        )
        engine = MonitoringEngine(
            subscription_service=sub_svc,
            change_detector=detector,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )

        # First check
        engine.run_check()

        # Add report (should not trigger alert — only watching risk changes)
        report_store["RPT-002"] = BaseReport(
            id="RPT-002",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="New.",
            reporter_id="citizen-002",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=datetime.now(UTC)),
        )

        alerts = engine.run_check()
        # No alert because we're only watching RISK_LEVEL_CHANGED
        assert len(alerts) == 0

    def test_last_check_at(self, mock_event_bus, mock_audit):
        engine = MonitoringEngine(event_bus=mock_event_bus, audit_logger=mock_audit)
        assert engine.last_check_at is None
        engine.run_check()
        assert engine.last_check_at is not None
