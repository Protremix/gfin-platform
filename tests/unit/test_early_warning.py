"""Tests for Global Early Warning — Module 31."""

from unittest.mock import MagicMock

import pytest

from services.early_warning import (
    LEVEL_ORDER,
    EarlyWarningEngine,
    MonitoredEntity,
    WarningEvent,
    WarningLevel,
    WarningRule,
    WarningRuleType,
)


@pytest.fixture
def mock_event_bus():
    return MagicMock()


@pytest.fixture
def engine(mock_event_bus):
    return EarlyWarningEngine(event_bus=mock_event_bus)


@pytest.fixture
def rule_engine(engine):
    engine.add_rule(
        "High Entity Velocity",
        WarningRuleType.ENTITY_VELOCITY.value,
        WarningLevel.WATCH.value,
        threshold=10,
    )
    engine.add_rule(
        "Campaign Escalation",
        WarningRuleType.CAMPAIGN_ESCALATION.value,
        WarningLevel.WARNING.value,
        threshold=3,
    )
    engine.add_rule(
        "Critical Infrastructure Change",
        WarningRuleType.INFRASTRUCTURE_CHANGE.value,
        WarningLevel.CRITICAL.value,
        threshold=1,
    )
    return engine


# ─── WarningLevel Tests ───


class TestWarningLevel:
    def test_level_ordering(self):
        assert LEVEL_ORDER[WarningLevel.INFO.value] < LEVEL_ORDER[WarningLevel.WATCH.value]
        assert LEVEL_ORDER[WarningLevel.WATCH.value] < LEVEL_ORDER[WarningLevel.WARNING.value]
        assert LEVEL_ORDER[WarningLevel.WARNING.value] < LEVEL_ORDER[WarningLevel.CRITICAL.value]


# ─── WarningRule Tests ───


class TestWarningRule:
    def test_creation(self):
        rule = WarningRule(id="R1", name="Test", rule_type=WarningRuleType.ENTITY_VELOCITY.value)
        assert rule.enabled is True
        assert rule.level == WarningLevel.WATCH.value
        assert rule.threshold == 1

    def test_disabled(self):
        rule = WarningRule(
            id="R1", name="Test", rule_type=WarningRuleType.ENTITY_VELOCITY.value, enabled=False
        )
        assert rule.enabled is False


# ─── WarningEvent Tests ───


class TestWarningEvent:
    def test_creation(self):
        event = WarningEvent(
            id="E1",
            rule_id="R1",
            rule_name="Test",
            level=WarningLevel.WARNING.value,
            rule_type="ENTITY_VELOCITY",
        )
        assert event.acknowledged is False
        assert event.level_priority == LEVEL_ORDER[WarningLevel.WARNING.value]

    def test_acknowledge(self):
        event = WarningEvent(
            id="E1",
            rule_id="R1",
            rule_name="Test",
            level=WarningLevel.WARNING.value,
            rule_type="ENTITY_VELOCITY",
        )
        event.acknowledge("Operator Smith")
        assert event.acknowledged is True
        assert event.acknowledged_by == "Operator Smith"
        assert event.acknowledged_at is not None


# ─── EarlyWarningEngine Tests ───


class TestEarlyWarningEngine:
    def test_add_rule(self, engine):
        rule = engine.add_rule("Test Rule", WarningRuleType.ENTITY_VELOCITY.value)
        assert rule.id.startswith("WR-")
        assert engine.rule_count == 1

    def test_remove_rule(self, engine):
        rule = engine.add_rule("Test", WarningRuleType.ENTITY_VELOCITY.value)
        assert engine.remove_rule(rule.id) is True
        assert engine.rule_count == 0

    def test_remove_nonexistent_rule(self, engine):
        assert engine.remove_rule("nonexistent") is False

    def test_get_rule(self, engine):
        rule = engine.add_rule("Test", WarningRuleType.ENTITY_VELOCITY.value)
        assert engine.get_rule(rule.id) is not None
        assert engine.get_rule("nonexistent") is None

    def test_list_rules(self, engine):
        engine.add_rule("A", WarningRuleType.ENTITY_VELOCITY.value)
        engine.add_rule("B", WarningRuleType.CAMPAIGN_ESCALATION.value)
        assert len(engine.list_rules()) == 2
        assert len(engine.list_rules(enabled_only=True)) == 2

    def test_enable_disable_rule(self, engine):
        rule = engine.add_rule("Test", WarningRuleType.ENTITY_VELOCITY.value)
        assert engine.disable_rule(rule.id) is True
        assert engine.get_rule(rule.id).enabled is False
        assert engine.enable_rule(rule.id) is True
        assert engine.get_rule(rule.id).enabled is True

    def test_trigger_warning(self, rule_engine):
        rule = rule_engine.list_rules()[0]
        event = rule_engine.trigger_warning(rule.id, {"count": 15}, "High velocity detected")
        assert event is not None
        assert event.level == WarningLevel.WATCH.value
        assert rule_engine.event_count == 1

    def test_trigger_warning_disabled_rule(self, rule_engine):
        rule = rule_engine.list_rules()[0]
        rule_engine.disable_rule(rule.id)
        event = rule_engine.trigger_warning(rule.id)
        assert event is None

    def test_trigger_warning_nonexistent_rule(self, engine):
        assert engine.trigger_warning("nonexistent") is None

    def test_evaluate_rules_meets_threshold(self, rule_engine):
        events = rule_engine.evaluate_rules({"entity_velocity_count": 15})
        assert len(events) >= 1
        assert any(e.rule_type == WarningRuleType.ENTITY_VELOCITY.value for e in events)

    def test_evaluate_rules_below_threshold(self, rule_engine):
        events = rule_engine.evaluate_rules({"entity_velocity_count": 5})
        assert len(events) == 0

    def test_evaluate_rules_multiple_triggers(self, rule_engine):
        events = rule_engine.evaluate_rules(
            {
                "entity_velocity_count": 20,
                "campaign_escalation_count": 5,
                "infrastructure_change_count": 2,
            }
        )
        assert len(events) == 3

    def test_notification_dispatched_for_warning(self, rule_engine):
        rule = next(r for r in rule_engine.list_rules() if r.level == WarningLevel.WARNING.value)
        rule_engine.trigger_warning(rule.id)
        assert rule_engine.notification_count == 1

    def test_notification_dispatched_for_critical(self, rule_engine):
        rule = next(r for r in rule_engine.list_rules() if r.level == WarningLevel.CRITICAL.value)
        rule_engine.trigger_warning(rule.id)
        assert rule_engine.notification_count == 1

    def test_notification_not_dispatched_for_info(self, engine):
        rule = engine.add_rule(
            "Info Rule", WarningRuleType.ENTITY_VELOCITY.value, level=WarningLevel.INFO.value
        )
        engine.trigger_warning(rule.id)
        assert engine.notification_count == 0

    def test_notification_not_dispatched_for_watch(self, engine):
        rule = engine.add_rule(
            "Watch Rule", WarningRuleType.ENTITY_VELOCITY.value, level=WarningLevel.WATCH.value
        )
        engine.trigger_warning(rule.id)
        assert engine.notification_count == 0

    def test_event_bus_publish(self, rule_engine, mock_event_bus):
        rule = rule_engine.list_rules()[0]
        rule_engine.trigger_warning(rule.id)
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "early_warning.triggered" in topics

    def test_acknowledge_event(self, rule_engine):
        rule = rule_engine.list_rules()[0]
        event = rule_engine.trigger_warning(rule.id)
        assert rule_engine.acknowledge_event(event.id, "Admin") is True
        assert event.acknowledged is True

    def test_acknowledge_nonexistent(self, engine):
        assert engine.acknowledge_event("nonexistent", "Admin") is False

    def test_get_events_filtered_by_level(self, rule_engine):
        rule_engine.trigger_warning(rule_engine.list_rules()[0].id)
        rule_engine.trigger_warning(rule_engine.list_rules()[1].id)
        watch_events = rule_engine.get_events(level=WarningLevel.WATCH.value)
        warning_events = rule_engine.get_events(level=WarningLevel.WARNING.value)
        assert len(watch_events) == 1
        assert len(warning_events) == 1

    def test_get_events_unacknowledged(self, rule_engine):
        rule = rule_engine.list_rules()[0]
        event = rule_engine.trigger_warning(rule.id)
        assert len(rule_engine.get_events(unacknowledged_only=True)) == 1
        rule_engine.acknowledge_event(event.id, "Admin")
        assert len(rule_engine.get_events(unacknowledged_only=True)) == 0

    def test_get_events_by_rule_id(self, rule_engine):
        rule = rule_engine.list_rules()[0]
        rule_engine.trigger_warning(rule.id)
        events = rule_engine.get_events(rule_id=rule.id)
        assert len(events) == 1

    def test_get_notifications(self, rule_engine):
        rule = next(r for r in rule_engine.list_rules() if r.level == WarningLevel.CRITICAL.value)
        rule_engine.trigger_warning(rule.id)
        notifs = rule_engine.get_notifications()
        assert len(notifs) == 1
        assert notifs[0].level == WarningLevel.CRITICAL.value


# ─── MonitoredEntity Tests ───


class TestMonitoredEntity:
    def test_creation(self):
        e = MonitoredEntity(entity_id="ENT-001", entity_type="domain")
        assert e.check_count == 0
        assert e.changes_detected == 0

    def test_check(self):
        e = MonitoredEntity(entity_id="ENT-001", entity_type="domain")
        e.check()
        assert e.check_count == 1

    def test_mark_changed(self):
        e = MonitoredEntity(entity_id="ENT-001", entity_type="domain")
        e.mark_changed()
        assert e.changes_detected == 1


class TestMonitoring:
    def test_monitor_entity(self, engine):
        e = engine.monitor_entity("ENT-001", "domain", "fraudster.com", "LV")
        assert e.entity_id == "ENT-001"
        assert engine.monitored_count == 1

    def test_monitor_entity_dedup(self, engine):
        engine.monitor_entity("ENT-001", "domain")
        engine.monitor_entity("ENT-001", "domain")
        assert engine.monitored_count == 1

    def test_get_monitored(self, engine):
        engine.monitor_entity("ENT-001", "domain")
        assert engine.get_monitored("ENT-001") is not None
        assert engine.get_monitored("nonexistent") is None
