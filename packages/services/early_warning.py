"""GFIN Global Early Warning — Module 31.

Proactive detection and alerting based on the Continuous Intelligence loop
per Directive §13: DISCOVER → CORRELATE → MONITOR → CHANGE DETECT →
REANALYZE → ALERT → DISCOVER AGAIN.

Layer A: In-memory rule-based detection
Layer B: Real-time Kafka stream processing, ML anomaly detection (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class WarningLevel(str, Enum):
    INFO = "INFO"
    WATCH = "WATCH"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class WarningRuleType(str, Enum):
    ENTITY_VELOCITY = "ENTITY_VELOCITY"
    CAMPAIGN_ESCALATION = "CAMPAIGN_ESCALATION"
    INFRASTRUCTURE_CHANGE = "INFRASTRUCTURE_CHANGE"
    NEW_CORRELATION = "NEW_CORRELATION"
    JURISDICTION_SPREAD = "JURISDICTION_SPREAD"


# Level ordering for comparison
LEVEL_ORDER: dict[str, int] = {
    WarningLevel.INFO.value: 1,
    WarningLevel.WATCH.value: 2,
    WarningLevel.WARNING.value: 3,
    WarningLevel.CRITICAL.value: 4,
}


# ─── Models ───


class WarningRule(BaseModel):
    """A configurable rule for early warning detection."""

    id: str
    name: str
    rule_type: str
    level: str = WarningLevel.WATCH.value
    threshold: int = 1
    description: str = ""
    enabled: bool = True
    scope: str = "global"  # global, jurisdiction, campaign


class WarningEvent(BaseModel):
    """A detected early warning event."""

    id: str
    rule_id: str
    rule_name: str
    level: str
    rule_type: str
    detected_data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: datetime | None = None

    def acknowledge(self, operator: str) -> None:
        self.acknowledged = True
        self.acknowledged_by = operator
        self.acknowledged_at = datetime.now(UTC)

    @property
    def level_priority(self) -> int:
        return LEVEL_ORDER.get(self.level, 0)


class WarningNotification(BaseModel):
    """A notification dispatched for a warning."""

    id: str
    event_id: str
    level: str
    message: str
    recipients: list[str] = Field(default_factory=list)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MonitoredEntity(BaseModel):
    """An entity being monitored for changes."""

    entity_id: str
    entity_type: str
    entity_value: str = ""
    jurisdiction: str = ""
    first_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_checked: datetime = Field(default_factory=lambda: datetime.now(UTC))
    check_count: int = 0
    changes_detected: int = 0

    def check(self) -> None:
        self.last_checked = datetime.now(UTC)
        self.check_count += 1

    def mark_changed(self) -> None:
        self.changes_detected += 1
        self.last_checked = datetime.now(UTC)


# ─── Early Warning Engine ───


class EarlyWarningEngine:
    """Engine for proactive detection of emerging threats.

    Per Directive §13: Continuous Intelligence loop.
    """

    def __init__(self, event_bus: Any | None = None) -> None:
        self._rules: dict[str, WarningRule] = {}
        self._events: list[WarningEvent] = []
        self._notifications: list[WarningNotification] = []
        self._monitored: dict[str, MonitoredEntity] = {}
        self._rule_counter = 0
        self._event_counter = 0
        self._notif_counter = 0
        self._event_bus = event_bus

    def add_rule(
        self,
        name: str,
        rule_type: str,
        level: str = WarningLevel.WATCH.value,
        threshold: int = 1,
        description: str = "",
        scope: str = "global",
    ) -> WarningRule:
        """Add a new warning rule."""
        self._rule_counter += 1
        rule = WarningRule(
            id=f"WR-{self._rule_counter:06d}",
            name=name,
            rule_type=rule_type,
            level=level,
            threshold=threshold,
            description=description,
            scope=scope,
        )
        self._rules[rule.id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a warning rule."""
        return self._rules.pop(rule_id, None) is not None

    def get_rule(self, rule_id: str) -> WarningRule | None:
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> list[WarningRule]:
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def enable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def monitor_entity(
        self, entity_id: str, entity_type: str, entity_value: str = "", jurisdiction: str = ""
    ) -> MonitoredEntity:
        """Register an entity for monitoring."""
        if entity_id in self._monitored:
            return self._monitored[entity_id]
        entity = MonitoredEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_value=entity_value,
            jurisdiction=jurisdiction,
        )
        self._monitored[entity_id] = entity
        return entity

    def get_monitored(self, entity_id: str) -> MonitoredEntity | None:
        return self._monitored.get(entity_id)

    def trigger_warning(
        self,
        rule_id: str,
        detected_data: dict[str, Any] | None = None,
        message: str = "",
    ) -> WarningEvent | None:
        """Manually trigger a warning for a rule. Returns the event or None if rule not found/disabled."""
        rule = self._rules.get(rule_id)
        if rule is None or not rule.enabled:
            return None

        self._event_counter += 1
        event = WarningEvent(
            id=f"WE-{self._event_counter:06d}",
            rule_id=rule.id,
            rule_name=rule.name,
            level=rule.level,
            rule_type=rule.type if hasattr(rule, "type") else rule.rule_type,
            detected_data=detected_data or {},
            message=message or f"Warning triggered by rule: {rule.name}",
        )
        self._events.append(event)

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="early_warning.triggered",
                    event={
                        "event_id": event.id,
                        "rule_id": rule.id,
                        "level": event.level,
                        "timestamp": event.timestamp.isoformat(),
                    },
                )

        # Auto-dispatch notification for WARNING and CRITICAL
        if LEVEL_ORDER.get(event.level, 0) >= LEVEL_ORDER[WarningLevel.WARNING.value]:
            self._dispatch_notification(event)

        return event

    def evaluate_rules(self, data: dict[str, Any]) -> list[WarningEvent]:
        """Evaluate all enabled rules against the provided data."""
        events: list[WarningEvent] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Check if data meets the threshold for this rule type
            metric_key = f"{rule.rule_type.lower()}_count"
            value = data.get(metric_key, 0)

            if isinstance(value, int | float) and value >= rule.threshold:
                event = self.trigger_warning(
                    rule.id,
                    detected_data={metric_key: value, "threshold": rule.threshold},
                    message=f"{rule.name}: {metric_key}={value} >= threshold={rule.threshold}",
                )
                if event:
                    events.append(event)

        return events

    def _dispatch_notification(self, event: WarningEvent) -> WarningNotification:
        """Dispatch a notification for a warning event."""
        self._notif_counter += 1
        notif = WarningNotification(
            id=f"WN-{self._notif_counter:06d}",
            event_id=event.id,
            level=event.level,
            message=event.message,
            recipients=["system"],
        )
        self._notifications.append(notif)
        return notif

    def acknowledge_event(self, event_id: str, operator: str) -> bool:
        """Acknowledge a warning event."""
        for event in self._events:
            if event.id == event_id:
                event.acknowledge(operator)
                return True
        return False

    def get_events(
        self,
        level: str | None = None,
        rule_id: str | None = None,
        unacknowledged_only: bool = False,
    ) -> list[WarningEvent]:
        """Get warning events with optional filters."""
        events = list(self._events)
        if level:
            events = [e for e in events if e.level == level]
        if rule_id:
            events = [e for e in events if e.rule_id == rule_id]
        if unacknowledged_only:
            events = [e for e in events if not e.acknowledged]
        return events

    def get_notifications(self) -> list[WarningNotification]:
        return list(self._notifications)

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def notification_count(self) -> int:
        return len(self._notifications)

    @property
    def monitored_count(self) -> int:
        return len(self._monitored)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
