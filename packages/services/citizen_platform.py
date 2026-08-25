"""GFIN Citizen Platform — Module 13.

Per Master Spec: Citizen-facing interface for entity checking, fraud reporting,
and alert subscriptions.

Key principles:
- Citizen reports are ALLEGATIONS until corroborated (Constitution Article XVII)
- Citizens see PUBLIC data only — never restricted or law-enforcement data
- Rate limited: 60 req/min (Module 02)
- Anonymous reporting supported
- All citizen actions audit-logged

Layer A: In-memory services with synthetic fixtures
Layer B: PostgreSQL + Redis + notification gateways (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from schemas.base import BaseReport
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel

# ─── Models ───


class CitizenCheckRequest(BaseModel):
    """A citizen's request to check an entity for fraud signals."""

    entity_type: str  # EntityType value
    value: str
    country: str | None = None  # ISO 3166-1 alpha-2

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        valid = {e.value for e in EntityType}
        if v not in valid:
            raise ValueError(f"entity_type must be one of {valid}")
        return v


class CitizenCheckResponse(BaseModel):
    """Response to a citizen entity check.

    Only PUBLIC data is returned. No restricted or law-enforcement data.
    """

    entity_type: str
    value: str
    normalized_value: str
    found: bool = False
    risk_level: str = RiskLevel.UNKNOWN.value
    report_count: int = 0
    corroborated_count: int = 0
    evidence_count: int = 0
    related_entities_summary: list[dict[str, str]] = Field(default_factory=list)
    message: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    disclaimer: str = (
        "Results are based on community-reported data. Reports are allegations until corroborated."
    )


class CitizenReportRequest(BaseModel):
    """A citizen's fraud report submission."""

    category: str
    description: str
    entity_type: str
    entity_value: str
    country: str | None = None
    language: str | None = None
    reporter_id: str | None = None  # None = anonymous
    reporter_organization_id: str | None = None
    risk_level: str = RiskLevel.UNKNOWN.value

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("category is required")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("description is required")
        if len(v) > 5000:
            raise ValueError("description must be 5000 characters or less")
        return v.strip()

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        valid = {e.value for e in EntityType}
        if v not in valid:
            raise ValueError(f"entity_type must be one of {valid}")
        return v


class CitizenReportResponse(BaseModel):
    """Response after a citizen submits a report."""

    report_id: str
    status: str = ReportStatus.UNVERIFIED.value
    message: str = "Report submitted. It will be reviewed by our team."
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportStatusUpdate(BaseModel):
    """Update a report's status (admin/analyst only)."""

    report_id: str
    new_status: str

    @field_validator("new_status")
    @classmethod
    def validate_new_status(cls, v: str) -> str:
        valid = {s.value for s in ReportStatus}
        if v not in valid:
            raise ValueError(f"new_status must be one of {valid}")
        return v


class AlertSubscription(BaseModel):
    """A citizen's subscription to alerts for an entity."""

    id: str = Field(default_factory=lambda: f"ALT-{uuid4().hex[:8].upper()}")
    entity_type: str
    entity_value: str
    normalized_value: str
    subscriber_id: str  # user_id or anonymous token
    channel: str = "email"  # email, sms (placeholder)
    channel_address: str  # email address or phone
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notified_count: int = 0
    last_notified_at: datetime | None = None


class AlertNotification(BaseModel):
    """A notification sent to a subscriber."""

    id: str = Field(default_factory=lambda: f"NTF-{uuid4().hex[:8].upper()}")
    subscription_id: str
    entity_type: str
    entity_value: str
    message: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── State Machine ───

VALID_TRANSITIONS: dict[str, set[str]] = {
    ReportStatus.UNVERIFIED.value: {
        ReportStatus.UNDER_REVIEW.value,
        ReportStatus.CORROBORATED.value,
        ReportStatus.DISPUTED.value,
        ReportStatus.FALSE_POSITIVE.value,
    },
    ReportStatus.UNDER_REVIEW.value: {
        ReportStatus.CORROBORATED.value,
        ReportStatus.DISPUTED.value,
        ReportStatus.FALSE_POSITIVE.value,
        ReportStatus.VERIFIED.value,
    },
    ReportStatus.CORROBORATED.value: {
        ReportStatus.DISPUTED.value,
        ReportStatus.VERIFIED.value,
        ReportStatus.OFFICIALLY_ESTABLISHED.value,
    },
    ReportStatus.DISPUTED.value: {
        ReportStatus.CORROBORATED.value,
        ReportStatus.FALSE_POSITIVE.value,
    },
    ReportStatus.VERIFIED.value: {
        ReportStatus.OFFICIALLY_ESTABLISHED.value,
    },
    ReportStatus.FALSE_POSITIVE.value: set(),  # terminal
    ReportStatus.OFFICIALLY_ESTABLISHED.value: set(),  # terminal
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid."""
    if from_status == to_status:
        return True  # no-op
    allowed = VALID_TRANSITIONS.get(from_status, set())
    return to_status in allowed


# ─── Citizen Check Service ───


class CitizenCheckService:
    """Service for citizens to check entities for fraud signals.

    Citizens see PUBLIC data only. No restricted or law-enforcement data.
    """

    def __init__(
        self,
        entity_store: dict[str, Any] | None = None,
        report_store: dict[str, BaseReport] | None = None,
        rate_limiter: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._entities = entity_store or {}
        self._reports = report_store or {}
        self._rate_limiter = rate_limiter
        self._audit = audit_logger

    def check_entity(
        self,
        request: CitizenCheckRequest,
        user_id: str | None = None,
        user_role: str = "citizen",
    ) -> CitizenCheckResponse:
        """Check an entity for known fraud signals.

        Returns PUBLIC data only. Citizens never see restricted data.
        """
        # Rate limit check
        if self._rate_limiter:
            allowed, _ = self._rate_limiter.allow(user_id or "anonymous", "citizen_check")
            if not allowed:
                raise PermissionError("Rate limit exceeded. Please try again later.")

        # Audit
        if self._audit:
            self._audit.log(
                user_id=user_id or "anonymous",
                action="citizen_check",
                resource_type="entity",
                resource_id=f"{request.entity_type}:{request.value}",
            )

        # Normalize the query value (simple normalization for now)
        normalized = self._normalize_value(request.entity_type, request.value)

        # Search for matching entities
        matches = self._find_entities(request.entity_type, normalized)

        if not matches:
            return CitizenCheckResponse(
                entity_type=request.entity_type,
                value=request.value,
                normalized_value=normalized,
                found=False,
                message="No known fraud signals found for this entity.",
            )

        # Filter entities by classification — citizens see PUBLIC only
        visible_entities = []
        for entity in matches:
            entity_class = getattr(getattr(entity, "classification", None), "classification", None)
            if hasattr(entity_class, "value"):
                entity_class = entity_class.value  # type: ignore[union-attr]

            # Citizens never see restricted/LE data
            if user_role == "citizen" and entity_class in (
                DataClassification.RESTRICTED.value,
                DataClassification.LAW_ENFORCEMENT.value,
                DataClassification.HIGHLY_RESTRICTED.value,
            ):
                continue
            visible_entities.append(entity)

        if not visible_entities:
            return CitizenCheckResponse(
                entity_type=request.entity_type,
                value=request.value,
                normalized_value=normalized,
                found=False,
                message="No known fraud signals found for this entity.",
            )

        # Count reports that reference these entities
        report_count = 0
        corroborated_count = 0
        evidence_count = 0
        related: list[dict[str, str]] = []

        visible_ids = {getattr(e, "id", None) for e in visible_entities}

        for report in self._reports.values():
            report_entity_ids = getattr(report, "related_entity_ids", [])
            if any(eid in visible_ids for eid in report_entity_ids):
                report_count += 1
                status = getattr(report, "status", ReportStatus.UNVERIFIED.value)
                if status in (
                    ReportStatus.CORROBORATED.value,
                    ReportStatus.VERIFIED.value,
                    ReportStatus.OFFICIALLY_ESTABLISHED.value,
                ):
                    corroborated_count += 1
                evidence_count += len(getattr(report, "related_evidence_ids", []))

        for entity in visible_entities:
            related.append(
                {
                    "entity_type": str(getattr(entity, "entity_type", request.entity_type)),
                    "value": str(getattr(entity, "value", normalized)),
                    "relationship": "matched",
                }
            )

        # Determine risk level
        risk = self._assess_risk(report_count, corroborated_count, evidence_count)

        return CitizenCheckResponse(
            entity_type=request.entity_type,
            value=request.value,
            normalized_value=normalized,
            found=True,
            risk_level=risk,
            report_count=report_count,
            corroborated_count=corroborated_count,
            evidence_count=evidence_count,
            related_entities_summary=related[:10],  # max 10
            message=self._risk_message(risk, report_count, corroborated_count),
        )

    def _normalize_value(self, entity_type: str, value: str) -> str:
        """Simple normalization — delegates to Module 04 normalizers in production."""
        return value.strip().lower()

    def _find_entities(self, entity_type: str, normalized_value: str) -> list[Any]:
        """Find entities matching the query. In production, uses search platform."""
        results = []
        for entity in self._entities.values():
            etype = getattr(entity, "entity_type", None)
            if etype is None:
                continue
            if hasattr(etype, "value"):
                etype = etype.value
            if etype != entity_type:
                continue
            norm = getattr(entity, "normalized_value", None) or getattr(entity, "value", "")
            if norm and norm.strip().lower() == normalized_value:
                results.append(entity)
        return results

    def _assess_risk(self, report_count: int, corroborated_count: int, evidence_count: int) -> str:
        """Assess risk level based on signals."""
        if corroborated_count >= 3 or evidence_count >= 10:
            return RiskLevel.CRITICAL.value
        if corroborated_count >= 1 or evidence_count >= 5:
            return RiskLevel.HIGH.value
        if report_count >= 3 or evidence_count >= 2:
            return RiskLevel.MEDIUM.value
        if report_count >= 1 or evidence_count >= 1:
            return RiskLevel.LOW.value
        return RiskLevel.UNKNOWN.value

    def _risk_message(self, risk: str, report_count: int, corroborated: int) -> str:
        """Human-readable risk message."""
        if risk == RiskLevel.UNKNOWN.value:
            return "No known fraud signals found for this entity."
        if risk == RiskLevel.LOW.value:
            return f"{report_count} report(s) found. No corroboration yet."
        if risk == RiskLevel.MEDIUM.value:
            return f"{report_count} report(s) found with {corroborated} corroborated."
        if risk == RiskLevel.HIGH.value:
            return (
                f"Strong indicators of fraud: {report_count} reports, {corroborated} corroborated."
            )
        if risk == RiskLevel.CRITICAL.value:
            return f"Critical risk: {report_count} reports, {corroborated} corroborated, strong evidence."
        return "No known fraud signals found for this entity."


# ─── Citizen Report Service ───


class CitizenReportService:
    """Service for citizens to submit and track fraud reports.

    Reports always start as UNVERIFIED. Citizens can only see their own reports.
    """

    def __init__(
        self,
        entity_store: dict[str, Any] | None = None,
        event_bus: Any | None = None,
        rate_limiter: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._entities = entity_store or {}
        self._reports: dict[str, BaseReport] = {}
        self._event_bus = event_bus
        self._rate_limiter = rate_limiter
        self._audit = audit_logger

    def submit_report(
        self,
        request: CitizenReportRequest,
        user_id: str | None = None,
    ) -> CitizenReportResponse:
        """Submit a new fraud report. Always starts as UNVERIFIED."""
        # Rate limit
        if self._rate_limiter:
            allowed, _ = self._rate_limiter.allow(user_id or "anonymous", "citizen_report")
            if not allowed:
                raise PermissionError("Rate limit exceeded. Please try again later.")

        # Validate entity exists (if entity store provided)
        if self._entities:
            normalized = request.entity_value.strip().lower()
            found = self._find_entity(request.entity_type, normalized)
            if not found:
                # Allow report even if entity not yet known — it may be new
                pass

        # Create report
        report = BaseReport(
            status=ReportStatus.UNVERIFIED.value,  # ALWAYS UNVERIFIED
            category=request.category,
            description=request.description,
            reporter_id=request.reporter_id or user_id,
            reporter_organization_id=request.reporter_organization_id,
            country=request.country,
            language=request.language,
            risk_level=request.risk_level,
            classification=self._default_classification(),
        )

        # Store
        self._reports[report.id] = report

        # Audit
        if self._audit:
            self._audit.log(
                user_id=user_id or "anonymous",
                action="citizen_report_submit",
                resource_type="report",
                resource_id=report.id,
            )

        # Publish event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="citizen.report.submitted",
                    event={
                        "report_id": report.id,
                        "category": report.category,
                        "entity_type": request.entity_type,
                        "entity_value": request.entity_value,
                        "reporter_id": report.reporter_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return CitizenReportResponse(
            report_id=report.id,
            status=ReportStatus.UNVERIFIED.value,
        )

    def get_report(
        self,
        report_id: str,
        user_id: str | None = None,
        user_role: str = "citizen",
    ) -> BaseReport | None:
        """Get a report by ID. Citizens can only see their own reports."""
        report = self._reports.get(report_id)
        if not report:
            return None

        # Authorization: citizens can only see their own reports
        if user_role == "citizen" and report.reporter_id != user_id:
            raise PermissionError("You can only view your own reports.")

        # Audit
        if self._audit:
            self._audit.log(
                user_id=user_id or "anonymous",
                action="citizen_report_view",
                resource_type="report",
                resource_id=report_id,
            )

        return report

    def list_reports(
        self,
        user_id: str | None = None,
        user_role: str = "citizen",
        limit: int = 50,
        offset: int = 0,
    ) -> list[BaseReport]:
        """List reports. Citizens see only their own. Admins/analysts see all."""
        # Rate limit
        if self._rate_limiter:
            allowed, _ = self._rate_limiter.allow(user_id or "anonymous", "citizen_list_reports")
            if not allowed:
                raise PermissionError("Rate limit exceeded.")

        if user_role == "citizen":
            reports = [r for r in self._reports.values() if r.reporter_id == user_id]
        else:
            reports = list(self._reports.values())

        # Paginate
        reports = reports[offset : offset + min(limit, 50)]

        # Audit
        if self._audit:
            self._audit.log(
                user_id=user_id or "anonymous",
                action="citizen_report_list",
                resource_type="report",
                resource_id=f"count:{len(reports)}",
            )

        return reports

    def update_status(
        self,
        update: ReportStatusUpdate,
        user_id: str | None = None,
        user_role: str = "admin",
    ) -> BaseReport:
        """Update a report's status. Admin/analyst only."""
        if user_role not in ("admin", "analyst", "investigator"):
            raise PermissionError("Only authorized personnel can update report status.")

        report = self._reports.get(update.report_id)
        if not report:
            raise ValueError(f"Report {update.report_id} not found.")

        # Validate transition
        if not can_transition(report.status, update.new_status):
            raise ValueError(f"Invalid status transition: {report.status} → {update.new_status}")

        old_status = report.status
        report.status = update.new_status

        # Audit
        if self._audit:
            self._audit.log(
                user_id=user_id or "system",
                action="report_status_update",
                resource_type="report",
                resource_id=update.report_id,
                details={"old_status": old_status, "new_status": update.new_status},
            )

        # Publish event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="citizen.report.status_changed",
                    event={
                        "report_id": report.id,
                        "old_status": old_status,
                        "new_status": update.new_status,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return report

    def _find_entity(self, entity_type: str, normalized: str) -> Any | None:
        """Find an entity in the store."""
        for entity in self._entities.values():
            etype = getattr(entity, "entity_type", None)
            if etype is None:
                continue
            if hasattr(etype, "value"):
                etype = etype.value
            if etype != entity_type:
                continue
            norm = getattr(entity, "normalized_value", None) or getattr(entity, "value", "")
            if norm and norm.strip().lower() == normalized:
                return entity
        return None

    def _default_classification(self) -> Any:
        """Default classification for citizen reports: COMMUNITY."""
        from schemas.base import Classification

        return Classification(classification=DataClassification.COMMUNITY)


# ─── Citizen Alert Service ───


class CitizenAlertService:
    """Service for citizens to subscribe to and receive alerts.

    Alerts fire when new reports match subscribed entities.
    Layer A: in-memory. Layer B: Redis + notification gateways.
    """

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        rate_limiter: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._subscriptions: dict[str, AlertSubscription] = {}
        self._notifications: list[AlertNotification] = []
        self._reports = report_store or {}
        self._rate_limiter = rate_limiter
        self._audit = audit_logger

    def subscribe(
        self,
        entity_type: str,
        entity_value: str,
        subscriber_id: str,
        channel: str = "email",
        channel_address: str = "",
    ) -> AlertSubscription:
        """Subscribe to alerts for an entity."""
        if self._rate_limiter:
            allowed, _ = self._rate_limiter.allow(subscriber_id, "citizen_subscribe")
            if not allowed:
                raise PermissionError("Rate limit exceeded.")

        if not channel_address:
            raise ValueError("channel_address is required")

        normalized = entity_value.strip().lower()

        sub = AlertSubscription(
            entity_type=entity_type,
            entity_value=entity_value,
            normalized_value=normalized,
            subscriber_id=subscriber_id,
            channel=channel,
            channel_address=channel_address,
        )
        self._subscriptions[sub.id] = sub

        if self._audit:
            self._audit.log(
                user_id=subscriber_id,
                action="alert_subscribe",
                resource_type="entity",
                resource_id=f"{entity_type}:{entity_value}",
            )

        return sub

    def unsubscribe(self, subscription_id: str, subscriber_id: str) -> bool:
        """Unsubscribe from alerts."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            return False

        if sub.subscriber_id != subscriber_id:
            raise PermissionError("You can only unsubscribe your own subscriptions.")

        sub.active = False
        del self._subscriptions[subscription_id]

        if self._audit:
            self._audit.log(
                user_id=subscriber_id,
                action="alert_unsubscribe",
                resource_type="subscription",
                resource_id=subscription_id,
            )

        return True

    def list_subscriptions(self, subscriber_id: str) -> list[AlertSubscription]:
        """List a citizen's active subscriptions."""
        return [s for s in self._subscriptions.values() if s.subscriber_id == subscriber_id]

    def notify_on_new_report(
        self,
        entity_type: str,
        entity_value: str,
        report_id: str,
        risk_level: str = "UNKNOWN",
    ) -> list[AlertNotification]:
        """Notify all subscribers when a new report matches their entity."""
        normalized = entity_value.strip().lower()
        notifications: list[AlertNotification] = []

        for sub in self._subscriptions.values():
            if not sub.active:
                continue
            if sub.entity_type != entity_type:
                continue
            if sub.normalized_value != normalized:
                continue

            # Create notification (no restricted data in message)
            notif = AlertNotification(
                subscription_id=sub.id,
                entity_type=entity_type,
                entity_value=entity_value,
                message=f"A new fraud report has been submitted for {entity_type}: {entity_value}. Risk level: {risk_level}.",
            )
            self._notifications.append(notif)
            notifications.append(notif)

            sub.notified_count += 1
            sub.last_notified_at = datetime.now(UTC)

        return notifications

    def get_notifications(self, subscriber_id: str) -> list[AlertNotification]:
        """Get all notifications for a subscriber."""
        sub_ids = {s.id for s in self._subscriptions.values() if s.subscriber_id == subscriber_id}
        return [n for n in self._notifications if n.subscription_id in sub_ids]
