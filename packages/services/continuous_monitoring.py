"""GFIN Continuous Monitoring — Module 17.

Implements the Continuous Intelligence loop: monitor entities and campaigns for
changes, trigger re-analysis, and generate alerts when risk thresholds are crossed.

Layer A: In-memory services with synthetic fixtures
Layer B: Kafka-streamed change events + Redis + WebSocket push (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ─── Enums ───


class WatchType(StrEnum):
    NEW_OBSERVATION = "NEW_OBSERVATION"
    RISK_LEVEL_CHANGED = "RISK_LEVEL_CHANGED"
    NEW_REPORTS = "NEW_REPORTS"
    INFRASTRUCTURE_CHANGED = "INFRASTRUCTURE_CHANGED"
    CAMPAIGN_LINKED = "CAMPAIGN_LINKED"
    NEW_ENTITIES = "NEW_ENTITIES"
    SEVERITY_CHANGED = "SEVERITY_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ACTIVITY_SPIKE = "ACTIVITY_SPIKE"
    ALL = "ALL"


class ChangeType(StrEnum):
    NEW_OBSERVATION = "NEW_OBSERVATION"
    RISK_LEVEL_CHANGED = "RISK_LEVEL_CHANGED"
    NEW_REPORTS = "NEW_REPORTS"
    INFRASTRUCTURE_CHANGED = "INFRASTRUCTURE_CHANGED"
    CAMPAIGN_LINKED = "CAMPAIGN_LINKED"
    NEW_ENTITIES = "NEW_ENTITIES"
    SEVERITY_CHANGED = "SEVERITY_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ACTIVITY_SPIKE = "ACTIVITY_SPIKE"


class AlertType(StrEnum):
    RISK_ESCALATION = "RISK_ESCALATION"
    NEW_REPORT = "NEW_REPORT"
    INFRASTRUCTURE_CHANGE = "INFRASTRUCTURE_CHANGE"
    CAMPAIGN_UPDATE = "CAMPAIGN_UPDATE"
    ACTIVITY_SPIKE = "ACTIVITY_SPIKE"
    STATUS_CHANGE = "STATUS_CHANGE"


class AlertPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ─── Alert priority mapping ───

CHANGE_PRIORITY_MAP: dict[str, str] = {
    ChangeType.RISK_LEVEL_CHANGED.value: AlertPriority.HIGH.value,
    ChangeType.NEW_REPORTS.value: AlertPriority.MEDIUM.value,
    ChangeType.INFRASTRUCTURE_CHANGED.value: AlertPriority.MEDIUM.value,
    ChangeType.CAMPAIGN_LINKED.value: AlertPriority.HIGH.value,
    ChangeType.SEVERITY_CHANGED.value: AlertPriority.HIGH.value,
    ChangeType.STATUS_CHANGED.value: AlertPriority.URGENT.value,
    ChangeType.ACTIVITY_SPIKE.value: AlertPriority.URGENT.value,
    ChangeType.NEW_OBSERVATION.value: AlertPriority.LOW.value,
    ChangeType.NEW_ENTITIES.value: AlertPriority.MEDIUM.value,
}


# ─── Models ───


class MonitoringSubscription(BaseModel):
    """A subscription to monitor an entity or campaign."""

    id: str
    subscriber_id: str
    target_type: str  # "entity" or "campaign"
    target_id: str
    watch_types: list[str] = Field(default_factory=lambda: [WatchType.ALL.value])
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_checked: datetime | None = None

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        if v not in ("entity", "campaign"):
            raise ValueError("target_type must be 'entity' or 'campaign'")
        return v


class EntitySnapshot(BaseModel):
    """A snapshot of an entity's state at a point in time."""

    entity_id: str
    risk_level: str = "UNKNOWN"
    report_count: int = 0
    observation_count: int = 0
    infrastructure_hash: str = ""
    campaign_ids: list[str] = Field(default_factory=list)
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CampaignSnapshot(BaseModel):
    """A snapshot of a campaign's state at a point in time."""

    campaign_id: str
    status: str = "DRAFT"
    severity: str = "LOW"
    entity_count: int = 0
    report_count: int = 0
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DetectedChange(BaseModel):
    """A detected change in an entity or campaign."""

    change_type: str
    target_type: str  # "entity" or "campaign"
    target_id: str
    old_value: Any = None
    new_value: Any = None
    description: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MonitoringAlert(BaseModel):
    """An alert generated from monitoring."""

    id: str
    subscription_id: str
    target_type: str
    target_id: str
    alert_type: str
    priority: str = AlertPriority.LOW.value
    changes: list[DetectedChange] = Field(default_factory=list)
    description: str = ""
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Subscription Service ───


class SubscriptionService:
    """Manages monitoring subscriptions."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, MonitoringSubscription] = {}

    def subscribe(
        self,
        subscriber_id: str,
        target_type: str,
        target_id: str,
        watch_types: list[str] | None = None,
    ) -> MonitoringSubscription:
        """Create a monitoring subscription."""
        sub_id = f"SUB-{target_type[:3].upper()}-{target_id}-{subscriber_id}"
        # Deduplicate
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id].active = True
            return self._subscriptions[sub_id]

        sub = MonitoringSubscription(
            id=sub_id,
            subscriber_id=subscriber_id,
            target_type=target_type,
            target_id=target_id,
            watch_types=watch_types or [WatchType.ALL.value],
        )
        self._subscriptions[sub_id] = sub
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        """Deactivate a subscription."""
        sub = self._subscriptions.get(subscription_id)
        if sub:
            sub.active = False
            return True
        return False

    def get_subscription(self, subscription_id: str) -> MonitoringSubscription | None:
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(
        self,
        subscriber_id: str | None = None,
        target_id: str | None = None,
        active_only: bool = True,
    ) -> list[MonitoringSubscription]:
        """List subscriptions, optionally filtered."""
        result = list(self._subscriptions.values())
        if active_only:
            result = [s for s in result if s.active]
        if subscriber_id:
            result = [s for s in result if s.subscriber_id == subscriber_id]
        if target_id:
            result = [s for s in result if s.target_id == target_id]
        return result


# ─── Change Detector ───


class ChangeDetector:
    """Detects changes in entities and campaigns by comparing snapshots."""

    def __init__(
        self,
        report_store: dict[str, Any] | None = None,
        entity_store: dict[str, Any] | None = None,
        campaign_store: dict[str, Any] | None = None,
    ) -> None:
        self._reports = report_store if report_store is not None else {}
        self._entities = entity_store if entity_store is not None else {}
        self._campaigns = campaign_store if campaign_store is not None else {}

    def capture_entity_snapshot(self, entity_id: str) -> EntitySnapshot:
        """Capture a snapshot of an entity's current state."""
        entity = self._entities.get(entity_id)
        if not entity:
            return EntitySnapshot(entity_id=entity_id)

        # Count reports for this entity
        report_count = 0
        for r in self._reports.values():
            if entity_id in getattr(r, "related_entity_ids", []):
                report_count += 1

        # Infrastructure hash (simple hash of metadata)
        metadata = getattr(entity, "metadata", {})
        infra_parts = []
        if isinstance(metadata, dict):
            for key in sorted(metadata.keys()):
                infra_parts.append(f"{key}:{metadata[key]}")
        infra_hash = "|".join(infra_parts)

        # Find campaigns linked to this entity
        campaign_ids = []
        for cid, camp in self._campaigns.items():
            if entity_id in getattr(camp, "related_entity_ids", []):
                campaign_ids.append(cid)

        return EntitySnapshot(
            entity_id=entity_id,
            risk_level=getattr(entity, "confidence", "UNKNOWN"),
            report_count=report_count,
            observation_count=0,  # Layer A: no observation store
            infrastructure_hash=infra_hash,
            campaign_ids=campaign_ids,
        )

    def capture_campaign_snapshot(self, campaign_id: str) -> CampaignSnapshot:
        """Capture a snapshot of a campaign's current state."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return CampaignSnapshot(campaign_id=campaign_id)

        report_count = 0
        for r in self._reports.values():
            if set(getattr(r, "related_entity_ids", [])) & set(
                getattr(campaign, "related_entity_ids", [])
            ):
                report_count += 1

        return CampaignSnapshot(
            campaign_id=campaign_id,
            status=getattr(campaign, "campaign_status", "DRAFT"),
            severity=getattr(campaign, "severity", "LOW"),
            entity_count=getattr(campaign, "entity_count", 0),
            report_count=report_count,
        )

    def detect_entity_changes(
        self,
        entity_id: str,
        old_snapshot: EntitySnapshot,
        new_snapshot: EntitySnapshot | None = None,
    ) -> list[DetectedChange]:
        """Detect changes in an entity by comparing snapshots."""
        if new_snapshot is None:
            new_snapshot = self.capture_entity_snapshot(entity_id)

        changes: list[DetectedChange] = []

        # Risk level changed
        if old_snapshot.risk_level != new_snapshot.risk_level:
            changes.append(
                DetectedChange(
                    change_type=ChangeType.RISK_LEVEL_CHANGED.value,
                    target_type="entity",
                    target_id=entity_id,
                    old_value=old_snapshot.risk_level,
                    new_value=new_snapshot.risk_level,
                    description=f"Risk level changed from {old_snapshot.risk_level} to {new_snapshot.risk_level}",
                )
            )

        # New reports
        if new_snapshot.report_count > old_snapshot.report_count:
            diff = new_snapshot.report_count - old_snapshot.report_count
            changes.append(
                DetectedChange(
                    change_type=ChangeType.NEW_REPORTS.value,
                    target_type="entity",
                    target_id=entity_id,
                    old_value=old_snapshot.report_count,
                    new_value=new_snapshot.report_count,
                    description=f"{diff} new report(s) filed",
                )
            )

        # Infrastructure changed
        if old_snapshot.infrastructure_hash != new_snapshot.infrastructure_hash:
            changes.append(
                DetectedChange(
                    change_type=ChangeType.INFRASTRUCTURE_CHANGED.value,
                    target_type="entity",
                    target_id=entity_id,
                    old_value=old_snapshot.infrastructure_hash[:50],
                    new_value=new_snapshot.infrastructure_hash[:50],
                    description="Entity infrastructure changed",
                )
            )

        # New campaign linked
        old_camps = set(old_snapshot.campaign_ids)
        new_camps = set(new_snapshot.campaign_ids)
        new_links = new_camps - old_camps
        if new_links:
            changes.append(
                DetectedChange(
                    change_type=ChangeType.CAMPAIGN_LINKED.value,
                    target_type="entity",
                    target_id=entity_id,
                    old_value=list(old_camps),
                    new_value=list(new_links),
                    description=f"Entity linked to {len(new_links)} new campaign(s)",
                )
            )

        return changes

    def detect_campaign_changes(
        self,
        campaign_id: str,
        old_snapshot: CampaignSnapshot,
        new_snapshot: CampaignSnapshot | None = None,
    ) -> list[DetectedChange]:
        """Detect changes in a campaign by comparing snapshots."""
        if new_snapshot is None:
            new_snapshot = self.capture_campaign_snapshot(campaign_id)

        changes: list[DetectedChange] = []

        # Status changed
        if old_snapshot.status != new_snapshot.status:
            changes.append(
                DetectedChange(
                    change_type=ChangeType.STATUS_CHANGED.value,
                    target_type="campaign",
                    target_id=campaign_id,
                    old_value=old_snapshot.status,
                    new_value=new_snapshot.status,
                    description=f"Campaign status changed from {old_snapshot.status} to {new_snapshot.status}",
                )
            )

        # Severity changed
        if old_snapshot.severity != new_snapshot.severity:
            changes.append(
                DetectedChange(
                    change_type=ChangeType.SEVERITY_CHANGED.value,
                    target_type="campaign",
                    target_id=campaign_id,
                    old_value=old_snapshot.severity,
                    new_value=new_snapshot.severity,
                    description=f"Campaign severity changed from {old_snapshot.severity} to {new_snapshot.severity}",
                )
            )

        # New entities
        if new_snapshot.entity_count > old_snapshot.entity_count:
            diff = new_snapshot.entity_count - old_snapshot.entity_count
            changes.append(
                DetectedChange(
                    change_type=ChangeType.NEW_ENTITIES.value,
                    target_type="campaign",
                    target_id=campaign_id,
                    old_value=old_snapshot.entity_count,
                    new_value=new_snapshot.entity_count,
                    description=f"{diff} new entity/entities added to campaign",
                )
            )

        # Activity spike: 5+ new reports
        if new_snapshot.report_count > old_snapshot.report_count + 4:
            diff = new_snapshot.report_count - old_snapshot.report_count
            changes.append(
                DetectedChange(
                    change_type=ChangeType.ACTIVITY_SPIKE.value,
                    target_type="campaign",
                    target_id=campaign_id,
                    old_value=old_snapshot.report_count,
                    new_value=new_snapshot.report_count,
                    description=f"Activity spike: {diff} new reports since last check",
                )
            )

        return changes


# ─── Alert Engine ───


class AlertEngine:
    """Generates alerts from detected changes."""

    def __init__(
        self,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._audit = audit_logger
        self._alerts: dict[str, MonitoringAlert] = {}
        self._alert_counter = 0

    def evaluate_changes(
        self,
        subscription_id: str,
        target_type: str,
        target_id: str,
        changes: list[DetectedChange],
    ) -> MonitoringAlert | None:
        """Evaluate detected changes and generate an alert if warranted."""
        if not changes:
            return None

        # Determine highest priority change
        max_priority = AlertPriority.LOW.value
        priority_order = {
            AlertPriority.LOW.value: 0,
            AlertPriority.MEDIUM.value: 1,
            AlertPriority.HIGH.value: 2,
            AlertPriority.URGENT.value: 3,
        }
        for change in changes:
            change_priority = CHANGE_PRIORITY_MAP.get(change.change_type, AlertPriority.LOW.value)
            if priority_order.get(change_priority, 0) > priority_order.get(max_priority, 0):
                max_priority = change_priority

        # Map changes to alert type
        alert_type = self._determine_alert_type(changes)

        self._alert_counter += 1
        alert = MonitoringAlert(
            id=f"ALT-{self._alert_counter:06d}",
            subscription_id=subscription_id,
            target_type=target_type,
            target_id=target_id,
            alert_type=alert_type,
            priority=max_priority,
            changes=changes,
            description=f"{len(changes)} change(s) detected for {target_type} {target_id}",
        )
        self._alerts[alert.id] = alert

        # Audit
        if self._audit:
            self._audit.log(
                user_id="system",
                action="alert_created",
                resource_type=target_type,
                resource_id=target_id,
                details={
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "priority": alert.priority,
                    "change_count": len(changes),
                },
            )

        # Event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="alert.created",
                    event={
                        "alert_id": alert.id,
                        "target_type": target_type,
                        "target_id": target_id,
                        "alert_type": alert.alert_type,
                        "priority": alert.priority,
                        "change_count": len(changes),
                        "timestamp": alert.created_at.isoformat(),
                    },
                )

        return alert

    def get_alerts(
        self,
        target_id: str | None = None,
        target_type: str | None = None,
        unacknowledged_only: bool = False,
    ) -> list[MonitoringAlert]:
        """Retrieve alerts, optionally filtered."""
        result = list(self._alerts.values())
        if target_id:
            result = [a for a in result if a.target_id == target_id]
        if target_type:
            result = [a for a in result if a.target_type == target_type]
        if unacknowledged_only:
            result = [a for a in result if not a.acknowledged]
        return result

    def acknowledge_alert(self, alert_id: str, user_id: str = "admin") -> MonitoringAlert | None:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        alert.acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.now(UTC)

        if self._audit:
            self._audit.log(
                user_id=user_id,
                action="alert_acknowledged",
                resource_type="alert",
                resource_id=alert_id,
                details={},
            )

        return alert

    def _determine_alert_type(self, changes: list[DetectedChange]) -> str:
        """Determine the alert type from changes."""
        change_types = {c.change_type for c in changes}

        if ChangeType.RISK_LEVEL_CHANGED.value in change_types:
            return AlertType.RISK_ESCALATION.value
        if ChangeType.STATUS_CHANGED.value in change_types:
            return AlertType.STATUS_CHANGE.value
        if ChangeType.ACTIVITY_SPIKE.value in change_types:
            return AlertType.ACTIVITY_SPIKE.value
        if ChangeType.INFRASTRUCTURE_CHANGED.value in change_types:
            return AlertType.INFRASTRUCTURE_CHANGE.value
        if ChangeType.NEW_REPORTS.value in change_types:
            return AlertType.NEW_REPORT.value
        if {ChangeType.NEW_ENTITIES.value, ChangeType.SEVERITY_CHANGED.value} & change_types:
            return AlertType.CAMPAIGN_UPDATE.value
        if ChangeType.CAMPAIGN_LINKED.value in change_types:
            return AlertType.CAMPAIGN_UPDATE.value
        return AlertType.NEW_REPORT.value


# ─── Monitoring Engine ───


class MonitoringEngine:
    """Orchestrates the continuous monitoring loop."""

    def __init__(
        self,
        subscription_service: SubscriptionService | None = None,
        change_detector: ChangeDetector | None = None,
        alert_engine: AlertEngine | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._subscriptions = subscription_service or SubscriptionService()
        self._detector = change_detector or ChangeDetector()
        self._alerts = alert_engine or AlertEngine(event_bus=event_bus, audit_logger=audit_logger)
        self._event_bus = event_bus
        self._audit = audit_logger
        self._snapshots: dict[str, EntitySnapshot | CampaignSnapshot] = {}
        self._check_count = 0
        self._last_check_at: datetime | None = None

    def run_check(self) -> list[MonitoringAlert]:
        """Run a monitoring check on all active subscriptions."""
        self._check_count += 1
        self._last_check_at = datetime.now(UTC)
        alerts: list[MonitoringAlert] = []

        active_subs = self._subscriptions.list_subscriptions(active_only=True)

        for sub in active_subs:
            alert = self._evaluate_subscription(sub)
            if alert:
                alerts.append(alert)

            # Update last checked
            sub.last_checked = datetime.now(UTC)

        return alerts

    def _evaluate_subscription(self, sub: MonitoringSubscription) -> MonitoringAlert | None:
        """Evaluate a single subscription for changes."""
        snapshot_key = f"{sub.target_type}:{sub.target_id}"

        if sub.target_type == "entity":
            new_snapshot: EntitySnapshot | CampaignSnapshot = (
                self._detector.capture_entity_snapshot(sub.target_id)
            )
        else:
            new_snapshot = self._detector.capture_campaign_snapshot(sub.target_id)

        old_snapshot = self._snapshots.get(snapshot_key)
        self._snapshots[snapshot_key] = new_snapshot

        if old_snapshot is None:
            # First check — no baseline, just store snapshot
            return None

        # Detect changes
        if sub.target_type == "entity":
            assert isinstance(new_snapshot, EntitySnapshot)
            assert isinstance(old_snapshot, EntitySnapshot)
            changes = self._detector.detect_entity_changes(
                sub.target_id,
                old_snapshot,
                new_snapshot,
            )
        else:
            assert isinstance(new_snapshot, CampaignSnapshot)
            assert isinstance(old_snapshot, CampaignSnapshot)
            changes = self._detector.detect_campaign_changes(
                sub.target_id,
                old_snapshot,
                new_snapshot,
            )

        # Filter by watch_types
        if WatchType.ALL.value not in sub.watch_types:
            changes = [c for c in changes if c.change_type in sub.watch_types]

        if not changes:
            return None

        # Generate alert
        return self._alerts.evaluate_changes(
            subscription_id=sub.id,
            target_type=sub.target_type,
            target_id=sub.target_id,
            changes=changes,
        )

    def get_status(self, target_type: str, target_id: str) -> dict[str, Any]:
        """Get monitoring status for a target."""
        snapshot_key = f"{target_type}:{target_id}"
        snapshot = self._snapshots.get(snapshot_key)
        alerts = self._alerts.get_alerts(target_id=target_id, target_type=target_type)
        unack = [a for a in alerts if not a.acknowledged]

        return {
            "target_type": target_type,
            "target_id": target_id,
            "has_snapshot": snapshot is not None,
            "total_alerts": len(alerts),
            "unacknowledged_alerts": len(unack),
            "last_checked": max(
                (
                    s.last_checked
                    for s in self._subscriptions.list_subscriptions(
                        target_id=target_id, active_only=False
                    )
                ),
                default=None,
            ),
        }

    @property
    def check_count(self) -> int:
        return self._check_count

    @property
    def last_check_at(self) -> datetime | None:
        return self._last_check_at
