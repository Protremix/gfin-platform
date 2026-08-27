"""GFIN Alert Engine — Module 18.

Alert routing, notification delivery, escalation policies, templates, and digest.
Takes alerts from Module 17 (Continuous Monitoring) and handles the full delivery pipeline.

Layer A: In-memory mock delivery (logs, queues)
Layer B: Real email/SMS/webhook delivery via SendGrid/Twilio/Slack (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# Re-use alert models from Module 17
from services.continuous_monitoring import (
    AlertPriority,
    AlertType,
    MonitoringAlert,
)

# ─── Enums ───


class DeliveryChannel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"
    IN_APP = "IN_APP"
    SLACK = "SLACK"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class AlertLifecycle(StrEnum):
    CREATED = "CREATED"
    ROUTED = "ROUTED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    DIGESTED = "DIGESTED"


# ─── Default routing rules ───

DEFAULT_PRIORITY_ROUTING: dict[str, list[str]] = {
    AlertPriority.URGENT.value: [
        DeliveryChannel.EMAIL.value,
        DeliveryChannel.SMS.value,
        DeliveryChannel.WEBHOOK.value,
        DeliveryChannel.IN_APP.value,
    ],
    AlertPriority.HIGH.value: [
        DeliveryChannel.EMAIL.value,
        DeliveryChannel.IN_APP.value,
    ],
    AlertPriority.MEDIUM.value: [
        DeliveryChannel.IN_APP.value,
    ],
    AlertPriority.LOW.value: [],  # Digest only
}

DIGEST_PRIORITY_THRESHOLD: list[str] = [
    AlertPriority.LOW.value,
    AlertPriority.MEDIUM.value,
]


# ─── Models ───


class RoutingRule(BaseModel):
    """Custom routing rule for alerts."""

    id: str
    name: str = ""
    alert_type: str | None = None
    priority: str | None = None
    target_type: str | None = None
    channels: list[str] = Field(default_factory=list)
    immediate: bool = True


class NotificationRecord(BaseModel):
    """A record of a notification delivery attempt."""

    id: str
    alert_id: str
    channel: str
    recipient: str
    subject: str = ""
    body: str = ""
    status: str = DeliveryStatus.PENDING.value
    sent_at: datetime | None = None
    error: str | None = None


class EscalationLevel(BaseModel):
    """A single escalation tier."""

    level: int
    name: str
    delay_minutes: int
    contacts: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class EscalationState(BaseModel):
    """Tracks escalation state for an alert."""

    alert_id: str
    current_level: int = 0
    escalated_at: datetime | None = None
    last_checked: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AlertDigestEntry(BaseModel):
    """An entry in an alert digest."""

    alert_id: str
    target_type: str
    target_id: str
    alert_type: str
    priority: str
    description: str
    created_at: datetime


class DigestSummary(BaseModel):
    """A generated digest of alerts."""

    id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_alerts: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_target: dict[str, list[str]] = Field(default_factory=dict)
    summary_text: str = ""
    entries: list[AlertDigestEntry] = Field(default_factory=list)


class AlertStatistics(BaseModel):
    """Statistics about alerts."""

    total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    acknowledged: int = 0
    unacknowledged: int = 0
    escalated: int = 0


# ─── Alert Templates ───


class AlertTemplate:
    """Renders notification messages for alerts."""

    TEMPLATES: dict[str, dict[str, str]] = {
        AlertType.RISK_ESCALATION.value: {
            "subject": "🚨 RISK ESCALATION — {target_type} {target_id}",
            "body": (
                "Risk level escalated for {target_type} {target_id}.\n"
                "New risk: {new_risk}\n"
                "Previous risk: {old_risk}\n"
                "Priority: {priority}\n"
                "Changes detected: {change_count}\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
        AlertType.NEW_REPORT.value: {
            "subject": "📋 NEW REPORT — {target_type} {target_id}",
            "body": (
                "{report_count} new report(s) filed for {target_type} {target_id}.\n"
                "Priority: {priority}\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
        AlertType.INFRASTRUCTURE_CHANGE.value: {
            "subject": "🔧 INFRASTRUCTURE CHANGE — {target_type} {target_id}",
            "body": (
                "Infrastructure change detected for {target_type} {target_id}.\n"
                "Priority: {priority}\n"
                "Changes: {change_descriptions}\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
        AlertType.CAMPAIGN_UPDATE.value: {
            "subject": "🎯 CAMPAIGN UPDATE — {target_type} {target_id}",
            "body": (
                "Campaign {target_id} has been updated.\n"
                "Priority: {priority}\n"
                "Changes: {change_count} change(s)\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
        AlertType.ACTIVITY_SPIKE.value: {
            "subject": "📈 ACTIVITY SPIKE — {target_type} {target_id}",
            "body": (
                "Activity spike detected for {target_type} {target_id}.\n"
                "New reports: {report_count}\n"
                "Priority: {priority}\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
        AlertType.STATUS_CHANGE.value: {
            "subject": "⚠️ STATUS CHANGE — {target_type} {target_id}",
            "body": (
                "Status changed for {target_type} {target_id}.\n"
                "New status: {new_status}\n"
                "Previous status: {old_status}\n"
                "Priority: {priority}\n"
                "Alert ID: {alert_id}\n"
                "Time: {timestamp}"
            ),
        },
    }

    DEFAULT_TEMPLATE: dict[str, str] = {
        "subject": "GFIN Alert — {alert_type} for {target_type} {target_id}",
        "body": (
            "Alert type: {alert_type}\n"
            "Target: {target_type} {target_id}\n"
            "Priority: {priority}\n"
            "Changes: {change_count}\n"
            "Alert ID: {alert_id}\n"
            "Time: {timestamp}"
        ),
    }

    @classmethod
    def render(cls, alert: MonitoringAlert) -> dict[str, str]:
        """Render notification subject and body for an alert."""
        template = cls.TEMPLATES.get(alert.alert_type, cls.DEFAULT_TEMPLATE)

        # Extract change values
        changes = alert.changes
        change_count = len(changes)
        change_descriptions = "; ".join(c.description for c in changes) if changes else "N/A"

        # Extract specific values from changes
        new_risk = next(
            (c.new_value for c in changes if c.change_type == "RISK_LEVEL_CHANGED"),
            "UNKNOWN",
        )
        old_risk = next(
            (c.old_value for c in changes if c.change_type == "RISK_LEVEL_CHANGED"),
            "UNKNOWN",
        )
        report_count = next(
            (c.new_value for c in changes if c.change_type in ("NEW_REPORTS", "ACTIVITY_SPIKE")),
            0,
        )
        new_status = next(
            (c.new_value for c in changes if c.change_type == "STATUS_CHANGED"),
            "UNKNOWN",
        )
        old_status = next(
            (c.old_value for c in changes if c.change_type == "STATUS_CHANGED"),
            "UNKNOWN",
        )

        variables: dict[str, Any] = {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "target_type": alert.target_type,
            "target_id": alert.target_id,
            "priority": alert.priority,
            "change_count": change_count,
            "change_descriptions": change_descriptions,
            "new_risk": new_risk,
            "old_risk": old_risk,
            "report_count": report_count,
            "new_status": new_status,
            "old_status": old_status,
            "timestamp": alert.created_at.isoformat(),
        }

        subject = template["subject"].format(**variables)
        body = template["body"].format(**variables)

        return {"subject": subject, "body": body}


# ─── Alert Router ───


class AlertRouter:
    """Routes alerts to delivery channels based on priority and type."""

    def __init__(self) -> None:
        self._custom_rules: list[RoutingRule] = []

    def route(self, alert: MonitoringAlert) -> list[str]:
        """Determine delivery channels for an alert."""
        # Check custom rules first
        for rule in self._custom_rules:
            if self._matches_rule(alert, rule):
                if rule.immediate:
                    return rule.channels
                return []  # Rule says digest only

        # Default routing by priority
        return DEFAULT_PRIORITY_ROUTING.get(alert.priority, [DeliveryChannel.IN_APP.value])

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a custom routing rule."""
        self._custom_rules.append(rule)

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a custom routing rule."""
        before = len(self._custom_rules)
        self._custom_rules = [r for r in self._custom_rules if r.id != rule_id]
        return len(self._custom_rules) < before

    def is_digest(self, alert: MonitoringAlert) -> bool:
        """Check if an alert should go to digest queue."""
        return alert.priority in DIGEST_PRIORITY_THRESHOLD

    def _matches_rule(self, alert: MonitoringAlert, rule: RoutingRule) -> bool:
        """Check if a routing rule matches an alert."""
        if rule.alert_type and alert.alert_type != rule.alert_type:
            return False
        if rule.priority and alert.priority != rule.priority:
            return False
        return not (rule.target_type and alert.target_type != rule.target_type)


# ─── Notification Service ───


class NotificationService:
    """Delivers notifications via channels (mock in Layer A)."""

    def __init__(self) -> None:
        self._delivery_log: list[NotificationRecord] = []
        self._counter = 0

    def send(
        self,
        alert_id: str,
        channel: str,
        recipient: str,
        subject: str = "",
        body: str = "",
    ) -> NotificationRecord:
        """Send a notification via a channel (mock delivery)."""
        self._counter += 1
        record = NotificationRecord(
            id=f"NOTIF-{self._counter:06d}",
            alert_id=alert_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status=DeliveryStatus.SENT.value,
            sent_at=datetime.now(UTC),
        )
        self._delivery_log.append(record)
        return record

    def get_delivery_log(
        self,
        alert_id: str | None = None,
        channel: str | None = None,
    ) -> list[NotificationRecord]:
        """Retrieve delivery log, optionally filtered."""
        result = list(self._delivery_log)
        if alert_id:
            result = [r for r in result if r.alert_id == alert_id]
        if channel:
            result = [r for r in result if r.channel == channel]
        return result

    def mark_delivered(self, notification_id: str) -> NotificationRecord | None:
        """Mark a notification as delivered."""
        for r in self._delivery_log:
            if r.id == notification_id:
                r.status = DeliveryStatus.DELIVERED.value
                return r
        return None


# ─── Escalation Policy ───


class EscalationPolicy:
    """Time-based escalation for unacknowledged alerts."""

    DEFAULT_LEVELS: list[EscalationLevel] = [
        EscalationLevel(
            level=0,
            name="Original Recipients",
            delay_minutes=0,
            contacts=["analyst"],
            channels=[DeliveryChannel.IN_APP.value],
        ),
        EscalationLevel(
            level=1,
            name="Team Lead",
            delay_minutes=15,
            contacts=["team_lead"],
            channels=[DeliveryChannel.EMAIL.value, DeliveryChannel.IN_APP.value],
        ),
        EscalationLevel(
            level=2,
            name="Department Head",
            delay_minutes=60,
            contacts=["dept_head"],
            channels=[DeliveryChannel.EMAIL.value, DeliveryChannel.SMS.value],
        ),
        EscalationLevel(
            level=3,
            name="Security Operations Center",
            delay_minutes=240,
            contacts=["soc"],
            channels=[
                DeliveryChannel.EMAIL.value,
                DeliveryChannel.SMS.value,
                DeliveryChannel.SLACK.value,
            ],
        ),
    ]

    def __init__(self, levels: list[EscalationLevel] | None = None) -> None:
        self._levels = levels or self.DEFAULT_LEVELS
        self._escalation_states: dict[str, EscalationState] = {}

    def register_alert(self, alert: MonitoringAlert) -> EscalationState:
        """Register an alert for escalation tracking."""
        state = EscalationState(
            alert_id=alert.id,
            current_level=0,
        )
        self._escalation_states[alert.id] = state
        return state

    def check_escalation(
        self,
        alert: MonitoringAlert,
        now: datetime | None = None,
    ) -> EscalationLevel | None:
        """Check if an alert needs escalation. Returns new level if escalation needed."""
        if now is None:
            now = datetime.now(UTC)

        state = self._escalation_states.get(alert.id)
        if state is None:
            state = self.register_alert(alert)

        if alert.acknowledged or state.current_level < 0:
            return None

        elapsed = now - alert.created_at
        elapsed_minutes = elapsed.total_seconds() / 60

        # Find highest level whose delay has passed
        target_level = state.current_level
        for level in self._levels:
            if level.level > state.current_level and elapsed_minutes >= level.delay_minutes:
                target_level = level.level

        if target_level > state.current_level:
            new_level = (
                self._levels[target_level] if target_level < len(self._levels) else self._levels[-1]
            )
            state.current_level = target_level
            state.escalated_at = now
            return new_level

        return None

    def get_current_level(self, alert_id: str) -> EscalationLevel | None:
        """Get the current escalation level for an alert."""
        state = self._escalation_states.get(alert_id)
        if state is None:
            return None
        if state.current_level < len(self._levels):
            return self._levels[state.current_level]
        return self._levels[-1]

    def get_state(self, alert_id: str) -> EscalationState | None:
        return self._escalation_states.get(alert_id)

    def acknowledge(self, alert_id: str) -> None:
        """Mark alert as acknowledged, stopping escalation."""
        state = self._escalation_states.get(alert_id)
        if state:
            state.current_level = -1  # No further escalation


# ─── Alert Digest ───


class AlertDigest:
    """Collects low-priority alerts into a periodic digest."""

    def __init__(self) -> None:
        self._queue: list[MonitoringAlert] = []
        self._counter = 0

    def add(self, alert: MonitoringAlert) -> None:
        """Add an alert to the digest queue."""
        self._queue.append(alert)

    def generate_digest(self) -> DigestSummary:
        """Generate a digest summary of queued alerts."""
        self._counter += 1
        digest_id = f"DIGEST-{self._counter:06d}"

        by_type: dict[str, int] = {}
        by_target: dict[str, list[str]] = {}
        entries: list[AlertDigestEntry] = []

        for alert in self._queue:
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1

            target_key = f"{alert.target_type}:{alert.target_id}"
            if target_key not in by_target:
                by_target[target_key] = []
            by_target[target_key].append(alert.id)

            entries.append(
                AlertDigestEntry(
                    alert_id=alert.id,
                    target_type=alert.target_type,
                    target_id=alert.target_id,
                    alert_type=alert.alert_type,
                    priority=alert.priority,
                    description=alert.description,
                    created_at=alert.created_at,
                )
            )

        summary_lines = [f"GFIN Alert Digest — {len(self._queue)} alert(s)"]
        for alert_type, count in sorted(by_type.items()):
            summary_lines.append(f"  {alert_type}: {count}")
        for target_key, alert_ids in sorted(by_target.items()):
            summary_lines.append(f"  {target_key}: {len(alert_ids)} alert(s)")
        summary_text = "\n".join(summary_lines)

        digest = DigestSummary(
            id=digest_id,
            total_alerts=len(self._queue),
            by_type=by_type,
            by_target=by_target,
            summary_text=summary_text,
            entries=entries,
        )

        return digest

    def clear(self) -> int:
        """Clear the digest queue. Returns number cleared."""
        count = len(self._queue)
        self._queue.clear()
        return count

    @property
    def pending_count(self) -> int:
        return len(self._queue)


# ─── Alert Manager ───


class AlertManager:
    """Orchestrates the full alert pipeline: route → template → send → digest."""

    def __init__(
        self,
        router: AlertRouter | None = None,
        notifier: NotificationService | None = None,
        escalation: EscalationPolicy | None = None,
        digest: AlertDigest | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._router = router or AlertRouter()
        self._notifier = notifier or NotificationService()
        self._escalation = escalation or EscalationPolicy()
        self._digest = digest or AlertDigest()
        self._event_bus = event_bus
        self._audit = audit_logger
        self._all_alerts: list[MonitoringAlert] = []

    def process_alert(self, alert: MonitoringAlert) -> dict[str, Any]:
        """Process an alert through the full pipeline."""
        self._all_alerts.append(alert)
        self._escalation.register_alert(alert)

        # Route
        channels = self._router.route(alert)

        # Template
        rendered = AlertTemplate.render(alert)

        # Send to each channel
        deliveries: list[NotificationRecord] = []
        if channels:
            for channel in channels:
                recipient = self._get_recipient(channel)
                record = self._notifier.send(
                    alert_id=alert.id,
                    channel=channel,
                    recipient=recipient,
                    subject=rendered["subject"],
                    body=rendered["body"],
                )
                deliveries.append(record)
        else:
            # No immediate channels → digest
            self._digest.add(alert)

        # If alert is digest-priority but also sent immediate, add to digest for email summary
        if self._router.is_digest(alert) and channels:
            self._digest.add(alert)

        # Publish event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="alert.routed",
                    event={
                        "alert_id": alert.id,
                        "channels": channels,
                        "priority": alert.priority,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        # Audit
        if self._audit:
            self._audit.log(
                user_id="system",
                action="alert_processed",
                resource_type="alert",
                resource_id=alert.id,
                details={
                    "channels": channels,
                    "priority": alert.priority,
                    "deliveries": len(deliveries),
                },
            )

        return {
            "alert_id": alert.id,
            "channels": channels,
            "deliveries": deliveries,
            "digest_queued": self._router.is_digest(alert),
        }

    def check_escalations(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Check all alerts for escalation needs."""
        results: list[dict[str, Any]] = []
        if now is None:
            now = datetime.now(UTC)

        for alert in self._all_alerts:
            if alert.acknowledged:
                continue

            level = self._escalation.check_escalation(alert, now=now)
            if level:
                # Escalate: send to escalation channels
                rendered = AlertTemplate.render(alert)
                deliveries: list[NotificationRecord] = []
                for channel in level.channels:
                    for contact in level.contacts:
                        record = self._notifier.send(
                            alert_id=alert.id,
                            channel=channel,
                            recipient=contact,
                            subject=f"[ESCALATION L{level.level}] {rendered['subject']}",
                            body=rendered["body"],
                        )
                        deliveries.append(record)

                # Publish escalation event
                if self._event_bus:
                    with contextlib.suppress(Exception):
                        self._event_bus.publish(
                            topic="alert.escalated",
                            event={
                                "alert_id": alert.id,
                                "level": level.level,
                                "level_name": level.name,
                                "timestamp": now.isoformat(),
                            },
                        )

                results.append(
                    {
                        "alert_id": alert.id,
                        "escalated_to_level": level.level,
                        "level_name": level.name,
                        "deliveries": deliveries,
                    }
                )

        return results

    def get_statistics(self) -> AlertStatistics:
        """Get alert statistics."""
        stats = AlertStatistics(total=len(self._all_alerts))

        for alert in self._all_alerts:
            stats.by_type[alert.alert_type] = stats.by_type.get(alert.alert_type, 0) + 1
            stats.by_priority[alert.priority] = stats.by_priority.get(alert.priority, 0) + 1

            if alert.acknowledged:
                stats.acknowledged += 1
                stats.by_status[AlertLifecycle.ACKNOWLEDGED.value] = (
                    stats.by_status.get(AlertLifecycle.ACKNOWLEDGED.value, 0) + 1
                )
            else:
                stats.unacknowledged += 1
                stats.by_status[AlertLifecycle.ROUTED.value] = (
                    stats.by_status.get(AlertLifecycle.ROUTED.value, 0) + 1
                )

            state = self._escalation.get_state(alert.id)
            if state and state.current_level > 0:
                stats.escalated += 1

        return stats

    def get_digest(self) -> DigestSummary:
        """Generate and clear the alert digest."""
        digest = self._digest.generate_digest()
        self._digest.clear()
        return digest

    def get_delivery_log(self, alert_id: str | None = None) -> list[NotificationRecord]:
        return self._notifier.get_delivery_log(alert_id=alert_id)

    def _get_recipient(self, channel: str) -> str:
        """Get default recipient for a channel (Layer A: mock)."""
        recipients = {
            DeliveryChannel.EMAIL.value: "analyst@gfin.local",
            DeliveryChannel.SMS.value: "+0000000000",
            DeliveryChannel.WEBHOOK.value: "https://hooks.gfin.local/alert",
            DeliveryChannel.IN_APP.value: "dashboard",
            DeliveryChannel.SLACK.value: "#gfin-alerts",
        }
        return recipients.get(channel, "unknown")

    @property
    def all_alerts(self) -> list[MonitoringAlert]:
        return list(self._all_alerts)
