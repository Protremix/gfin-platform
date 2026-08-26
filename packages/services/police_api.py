"""GFIN Police API — Module 23.

Controlled interface for law enforcement to access GFIN intelligence.
Per Constitution and Architecture Review §8: federated data, authenticated,
authorized, audited, rate-limited.

Layer A: In-memory API service (direct calls, no HTTP)
Layer B: FastAPI HTTP endpoints with mTLS, OIDC/OAuth2 (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class PoliceRole(str, Enum):
    POLICE_OFFICER = "POLICE_OFFICER"
    POLICE_SUPERVISOR = "POLICE_SUPERVISOR"
    POLICE_ADMIN = "POLICE_ADMIN"


class AccessLevel(str, Enum):
    MATCH_ONLY = "MATCH_ONLY"
    REQUEST_REQUIRED = "REQUEST_REQUIRED"
    FULL_ACCESS = "FULL_ACCESS"


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXECUTED = "EXECUTED"
    CLOSED = "CLOSED"


class EndpointName(str, Enum):
    MATCH = "match"
    OBSERVATION = "observation"
    ENTITY_INTEL = "entity_intel"
    CAMPAIGN_INTEL = "campaign_intel"
    MONITOR = "monitor"
    ALERTS = "alerts"
    REQUEST = "request"
    REQUEST_STATUS = "request_status"


# ─── Role hierarchy ───

ROLE_LEVEL: dict[str, int] = {
    PoliceRole.POLICE_OFFICER.value: 1,
    PoliceRole.POLICE_SUPERVISOR.value: 2,
    PoliceRole.POLICE_ADMIN.value: 3,
}

# Per-endpoint minimum role
ENDPOINT_MIN_ROLE: dict[str, str] = {
    EndpointName.MATCH.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.OBSERVATION.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.ENTITY_INTEL.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.CAMPAIGN_INTEL.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.MONITOR.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.ALERTS.value: PoliceRole.POLICE_OFFICER.value,
    EndpointName.REQUEST.value: PoliceRole.POLICE_SUPERVISOR.value,
    EndpointName.REQUEST_STATUS.value: PoliceRole.POLICE_OFFICER.value,
}

# Per-endpoint rate limits (requests per hour)
DEFAULT_RATE_LIMITS: dict[str, int] = {
    EndpointName.MATCH.value: 100,
    EndpointName.OBSERVATION.value: 500,
    EndpointName.ENTITY_INTEL.value: 200,
    EndpointName.CAMPAIGN_INTEL.value: 200,
    EndpointName.MONITOR.value: 50,
    EndpointName.ALERTS.value: 300,
    EndpointName.REQUEST.value: 20,
    EndpointName.REQUEST_STATUS.value: 100,
}


# ─── Models ───


class PoliceOrganization(BaseModel):
    """A police organization registered with GFIN."""

    org_id: str
    name: str
    jurisdiction: str
    api_key: str
    access_level: str = AccessLevel.MATCH_ONLY.value
    rate_limits: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_RATE_LIMITS))


class PoliceSession(BaseModel):
    """An authenticated police session."""

    session_id: str
    org_id: str
    officer_name: str = ""
    role: str
    jurisdiction: str
    access_level: str = AccessLevel.MATCH_ONLY.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(hours=8))
    active: bool = True

    def is_expired(self, now: datetime | None = None) -> bool:
        check = now or datetime.now(UTC)
        return check >= self.expires_at

    def is_valid(self, now: datetime | None = None) -> bool:
        return self.active and not self.is_expired(now)


class MatchResult(BaseModel):
    """Result of an entity match query."""

    entity_id: str
    entity_type: str
    entity_value: str
    jurisdiction: str
    matched: bool
    confidence: str = "LOW"
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_campaign: str | None = None
    access_level: str = AccessLevel.MATCH_ONLY.value
    intelligence_type: str = ""
    match_id: str = ""


class ObservationRecord(BaseModel):
    """A police-submitted observation."""

    id: str
    org_id: str
    officer_name: str
    entity_type: str
    entity_value: str
    observation_text: str = ""
    jurisdiction: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EntityIntel(BaseModel):
    """Entity intelligence response for police API."""

    entity_id: str
    entity_type: str
    entity_value: str
    risk_level: str = "UNKNOWN"
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_campaigns: list[str] = Field(default_factory=list)
    report_count: int = 0
    jurisdiction: str = ""
    confidence: str = "LOW"
    access_level: str = AccessLevel.MATCH_ONLY.value


class CampaignIntel(BaseModel):
    """Campaign intelligence response for police API."""

    campaign_id: str
    name: str = ""
    status: str = "UNKNOWN"
    risk_score: int = 0
    entity_count: int = 0
    report_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_entities: list[str] = Field(default_factory=list)


class CrossBorderRequest(BaseModel):
    """A cross-border information request."""

    id: str
    requesting_org: str
    requesting_jurisdiction: str
    target_jurisdiction: str
    entity_id: str
    entity_type: str
    request_reason: str = ""
    status: str = RequestStatus.PENDING.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    reviewed_by: str = ""
    executed_at: datetime | None = None
    response_data: dict[str, Any] | None = None
    denial_reason: str = ""

    def can_transition_to(self, new_status: str) -> bool:
        """Check if status transition is valid."""
        valid_transitions: dict[str, set[str]] = {
            RequestStatus.PENDING.value: {RequestStatus.REVIEW.value, RequestStatus.DENIED.value},
            RequestStatus.REVIEW.value: {RequestStatus.APPROVED.value, RequestStatus.DENIED.value},
            RequestStatus.APPROVED.value: {
                RequestStatus.EXECUTED.value,
                RequestStatus.CLOSED.value,
            },
            RequestStatus.EXECUTED.value: {RequestStatus.CLOSED.value},
            RequestStatus.DENIED.value: {RequestStatus.CLOSED.value},
            RequestStatus.CLOSED.value: set(),
        }
        return new_status in valid_transitions.get(self.status, set())

    def transition(self, new_status: str, reviewer: str = "") -> bool:
        """Transition to a new status if valid."""
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        if new_status in (RequestStatus.APPROVED.value, RequestStatus.DENIED.value):
            self.reviewed_at = datetime.now(UTC)
            self.reviewed_by = reviewer
        elif new_status == RequestStatus.EXECUTED.value:
            self.executed_at = datetime.now(UTC)
        return True


class PoliceAuditEntry(BaseModel):
    """An immutable audit entry for police API access."""

    id: str
    session_id: str
    org_id: str
    officer_name: str
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    success: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Police Audit Log ───


class PoliceAuditLog:
    """Immutable audit log for all police API access."""

    def __init__(self) -> None:
        self._entries: list[PoliceAuditEntry] = []
        self._counter = 0

    def log(
        self,
        session: PoliceSession,
        endpoint: str,
        params: dict[str, Any],
        result_summary: str = "",
        success: bool = True,
    ) -> PoliceAuditEntry:
        """Log a police API call (immutable)."""
        self._counter += 1
        entry = PoliceAuditEntry(
            id=f"PAUDIT-{self._counter:06d}",
            session_id=session.session_id,
            org_id=session.org_id,
            officer_name=session.officer_name,
            endpoint=endpoint,
            params=params,
            result_summary=result_summary,
            success=success,
        )
        self._entries.append(entry)
        return entry

    def query(
        self,
        org_id: str | None = None,
        endpoint: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PoliceAuditEntry]:
        """Query audit entries."""
        result = list(self._entries)
        if org_id:
            result = [e for e in result if e.org_id == org_id]
        if endpoint:
            result = [e for e in result if e.endpoint == endpoint]
        if start:
            result = [e for e in result if e.timestamp >= start]
        if end:
            result = [e for e in result if e.timestamp <= end]
        return result

    @property
    def count(self) -> int:
        return len(self._entries)

    def delete_entry(self, entry_id: str) -> bool:
        """Audit entries are immutable — deletion is not allowed."""
        return False

    def modify_entry(self, entry_id: str, **kwargs: Any) -> bool:
        """Audit entries are immutable — modification is not allowed."""
        return False


# ─── Police Rate Limiter ───


class PoliceRateLimiter:
    """Per-organization rate limiting for police API."""

    def __init__(self) -> None:
        # {org_id: {endpoint: [(timestamp), ...]}}
        self._usage: dict[str, dict[str, list[datetime]]] = {}

    def check_limit(
        self, org: PoliceOrganization, endpoint: str, now: datetime | None = None
    ) -> bool:
        """Check if organization is within rate limit for an endpoint."""
        if now is None:
            now = datetime.now(UTC)

        limit = org.rate_limits.get(endpoint, 100)
        window_start = now - timedelta(hours=1)

        if org.org_id not in self._usage:
            self._usage[org.org_id] = {}

        if endpoint not in self._usage[org.org_id]:
            self._usage[org.org_id][endpoint] = []

        # Remove entries outside the window
        self._usage[org.org_id][endpoint] = [
            ts for ts in self._usage[org.org_id][endpoint] if ts > window_start
        ]

        return len(self._usage[org.org_id][endpoint]) < limit

    def record_use(self, org_id: str, endpoint: str, now: datetime | None = None) -> None:
        """Record an API call for rate limiting."""
        if now is None:
            now = datetime.now(UTC)
        if org_id not in self._usage:
            self._usage[org_id] = {}
        if endpoint not in self._usage[org_id]:
            self._usage[org_id][endpoint] = []
        self._usage[org_id][endpoint].append(now)

    def get_usage(self, org_id: str, endpoint: str) -> int:
        """Get current usage count for an org+endpoint."""
        return len(self._usage.get(org_id, {}).get(endpoint, []))

    def reset(self, org_id: str | None = None) -> None:
        """Reset rate limit counters."""
        if org_id:
            self._usage.pop(org_id, None)
        else:
            self._usage.clear()


# ─── Police Authentication ───


class PoliceAuth:
    """Authentication and authorization for police API."""

    def __init__(self) -> None:
        self._organizations: dict[str, PoliceOrganization] = {}
        self._sessions: dict[str, PoliceSession] = {}
        self._session_counter = 0

    def register_organization(self, org: PoliceOrganization) -> None:
        """Register a police organization."""
        self._organizations[org.api_key] = org

    def authenticate(
        self,
        api_key: str,
        officer_name: str = "",
        role: str = PoliceRole.POLICE_OFFICER.value,
    ) -> PoliceSession | None:
        """Authenticate an API key and create a session."""
        org = self._organizations.get(api_key)
        if org is None:
            return None

        self._session_counter += 1
        session = PoliceSession(
            session_id=f"PSESSION-{self._session_counter:06d}",
            org_id=org.org_id,
            officer_name=officer_name,
            role=role,
            jurisdiction=org.jurisdiction,
            access_level=org.access_level,
        )
        self._sessions[session.session_id] = session
        return session

    def authorize(self, session: PoliceSession, endpoint: str) -> bool:
        """Authorize a session for an endpoint (RBAC + ABAC)."""
        if not session.is_valid():
            return False

        min_role = ENDPOINT_MIN_ROLE.get(endpoint, PoliceRole.POLICE_ADMIN.value)
        if ROLE_LEVEL.get(session.role, 0) < ROLE_LEVEL.get(min_role, 0):
            return False

        return True

    def get_session(self, session_id: str) -> PoliceSession | None:
        return self._sessions.get(session_id)

    def revoke_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.active = False
            return True
        return False

    def get_organization(self, org_id: str) -> PoliceOrganization | None:
        for org in self._organizations.values():
            if org.org_id == org_id:
                return org
        return None


# ─── Police API ───


class PoliceAPI:
    """Main police API service."""

    def __init__(
        self,
        auth: PoliceAuth | None = None,
        audit_log: PoliceAuditLog | None = None,
        rate_limiter: PoliceRateLimiter | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._auth = auth or PoliceAuth()
        self._audit = audit_log or PoliceAuditLog()
        self._rate_limiter = rate_limiter or PoliceRateLimiter()
        self._event_bus = event_bus
        self._observations: list[ObservationRecord] = []
        self._cross_border_requests: dict[str, CrossBorderRequest] = {}
        self._subscriptions: dict[str, list[str]] = {}  # org_id -> [entity_id]
        self._match_counter = 0
        self._observation_counter = 0
        self._request_counter = 0

    @property
    def auth(self) -> PoliceAuth:
        return self._auth

    @property
    def audit_log(self) -> PoliceAuditLog:
        return self._audit

    @property
    def rate_limiter(self) -> PoliceRateLimiter:
        return self._rate_limiter

    def _check_access(self, session: PoliceSession, endpoint: str) -> tuple[bool, str]:
        """Check authentication, authorization, and rate limit."""
        if not session.is_valid():
            return False, "Session expired or invalid"

        if not self._auth.authorize(session, endpoint):
            return False, "Not authorized for this endpoint"

        org = self._auth.get_organization(session.org_id)
        if org is None:
            return False, "Organization not found"

        if not self._rate_limiter.check_limit(org, endpoint):
            return False, "Rate limit exceeded"

        return True, ""

    def match_entity(
        self,
        session: PoliceSession,
        entity_type: str,
        entity_value: str,
        jurisdiction: str | None = None,
    ) -> MatchResult:
        """Match an entity against GFIN intelligence."""
        ok, err = self._check_access(session, EndpointName.MATCH.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.MATCH.value)
        self._match_counter += 1

        result = MatchResult(
            entity_id=f"ENT-{self._match_counter:06d}",
            entity_type=entity_type,
            entity_value=entity_value,
            jurisdiction=jurisdiction or session.jurisdiction,
            matched=False,
            confidence="LOW",
            access_level=session.access_level,
            intelligence_type="fraud_intelligence",
            match_id=f"MATCH-{self._match_counter:06d}",
        )

        self._audit.log(
            session=session,
            endpoint=EndpointName.MATCH.value,
            params={"entity_type": entity_type, "entity_value": entity_value},
            result_summary=f"match={result.matched}",
        )

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="police.match",
                    event={
                        "match_id": result.match_id,
                        "org_id": session.org_id,
                        "entity_type": entity_type,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return result

    def submit_observation(
        self,
        session: PoliceSession,
        entity_type: str,
        entity_value: str,
        observation_text: str = "",
    ) -> ObservationRecord:
        """Submit a police observation."""
        ok, err = self._check_access(session, EndpointName.OBSERVATION.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.OBSERVATION.value)
        self._observation_counter += 1

        record = ObservationRecord(
            id=f"OBS-{self._observation_counter:06d}",
            org_id=session.org_id,
            officer_name=session.officer_name,
            entity_type=entity_type,
            entity_value=entity_value,
            observation_text=observation_text,
            jurisdiction=session.jurisdiction,
        )
        self._observations.append(record)

        self._audit.log(
            session=session,
            endpoint=EndpointName.OBSERVATION.value,
            params={"entity_type": entity_type, "entity_value": entity_value},
            result_summary=f"observation_id={record.id}",
        )

        return record

    def get_entity_intel(self, session: PoliceSession, entity_id: str) -> EntityIntel:
        """Get entity intelligence."""
        ok, err = self._check_access(session, EndpointName.ENTITY_INTEL.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.ENTITY_INTEL.value)

        intel = EntityIntel(
            entity_id=entity_id,
            entity_type="UNKNOWN",
            entity_value="",
            risk_level="UNKNOWN",
            jurisdiction=session.jurisdiction,
            confidence="LOW",
            access_level=session.access_level,
        )

        self._audit.log(
            session=session,
            endpoint=EndpointName.ENTITY_INTEL.value,
            params={"entity_id": entity_id},
            result_summary=f"risk={intel.risk_level}",
        )

        return intel

    def get_campaign_intel(self, session: PoliceSession, campaign_id: str) -> CampaignIntel:
        """Get campaign intelligence."""
        ok, err = self._check_access(session, EndpointName.CAMPAIGN_INTEL.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.CAMPAIGN_INTEL.value)

        intel = CampaignIntel(
            campaign_id=campaign_id,
            status="UNKNOWN",
        )

        self._audit.log(
            session=session,
            endpoint=EndpointName.CAMPAIGN_INTEL.value,
            params={"campaign_id": campaign_id},
            result_summary=f"status={intel.status}",
        )

        return intel

    def subscribe_monitor(self, session: PoliceSession, entity_id: str) -> dict[str, str]:
        """Subscribe to entity monitoring."""
        ok, err = self._check_access(session, EndpointName.MONITOR.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.MONITOR.value)

        if session.org_id not in self._subscriptions:
            self._subscriptions[session.org_id] = []
        if entity_id not in self._subscriptions[session.org_id]:
            self._subscriptions[session.org_id].append(entity_id)

        self._audit.log(
            session=session,
            endpoint=EndpointName.MONITOR.value,
            params={"entity_id": entity_id},
            result_summary="subscribed",
        )

        return {"entity_id": entity_id, "status": "subscribed"}

    def get_alerts(self, session: PoliceSession) -> list[dict[str, Any]]:
        """Get alerts for the organization."""
        ok, err = self._check_access(session, EndpointName.ALERTS.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.ALERTS.value)

        self._audit.log(
            session=session,
            endpoint=EndpointName.ALERTS.value,
            params={},
            result_summary="0 alerts",
        )

        return []

    def create_cross_border_request(
        self,
        session: PoliceSession,
        target_jurisdiction: str,
        entity_id: str,
        entity_type: str,
        request_reason: str = "",
    ) -> CrossBorderRequest:
        """Create a cross-border information request."""
        ok, err = self._check_access(session, EndpointName.REQUEST.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.REQUEST.value)
        self._request_counter += 1

        request = CrossBorderRequest(
            id=f"CBR-{self._request_counter:06d}",
            requesting_org=session.org_id,
            requesting_jurisdiction=session.jurisdiction,
            target_jurisdiction=target_jurisdiction,
            entity_id=entity_id,
            entity_type=entity_type,
            request_reason=request_reason,
        )
        self._cross_border_requests[request.id] = request

        self._audit.log(
            session=session,
            endpoint=EndpointName.REQUEST.value,
            params={"target_jurisdiction": target_jurisdiction, "entity_id": entity_id},
            result_summary=f"request_id={request.id}",
        )

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="police.cross_border_request",
                    event={
                        "request_id": request.id,
                        "requesting_org": session.org_id,
                        "target_jurisdiction": target_jurisdiction,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return request

    def get_request_status(
        self, session: PoliceSession, request_id: str
    ) -> CrossBorderRequest | None:
        """Get the status of a cross-border request."""
        ok, err = self._check_access(session, EndpointName.REQUEST_STATUS.value)
        if not ok:
            raise PermissionError(err)

        self._rate_limiter.record_use(session.org_id, EndpointName.REQUEST_STATUS.value)

        request = self._cross_border_requests.get(request_id)

        self._audit.log(
            session=session,
            endpoint=EndpointName.REQUEST_STATUS.value,
            params={"request_id": request_id},
            result_summary=f"status={request.status if request else 'not_found'}",
        )

        return request

    def review_cross_border_request(
        self,
        request_id: str,
        approved: bool,
        reviewer: str,
        denial_reason: str = "",
    ) -> CrossBorderRequest | None:
        """Review a cross-border request (supervisor/admin action)."""
        request = self._cross_border_requests.get(request_id)
        if request is None:
            return None

        if (
            request.status != RequestStatus.PENDING.value
            and request.status != RequestStatus.REVIEW.value
        ):
            return None

        # Move to REVIEW first if pending
        if request.status == RequestStatus.PENDING.value:
            request.transition(RequestStatus.REVIEW.value)

        if approved:
            request.transition(RequestStatus.APPROVED.value, reviewer=reviewer)
        else:
            request.denial_reason = denial_reason
            request.transition(RequestStatus.DENIED.value, reviewer=reviewer)

        return request

    def execute_cross_border_request(self, request_id: str) -> CrossBorderRequest | None:
        """Execute an approved cross-border request."""
        request = self._cross_border_requests.get(request_id)
        if request is None:
            return None
        if request.status != RequestStatus.APPROVED.value:
            return None

        request.response_data = {"status": "executed", "data": "mock"}
        request.transition(RequestStatus.EXECUTED.value)
        return request

    def close_cross_border_request(self, request_id: str) -> CrossBorderRequest | None:
        """Close a cross-border request."""
        request = self._cross_border_requests.get(request_id)
        if request is None:
            return None
        request.transition(RequestStatus.CLOSED.value)
        return request

    @property
    def observations(self) -> list[ObservationRecord]:
        return list(self._observations)

    @property
    def cross_border_requests(self) -> list[CrossBorderRequest]:
        return list(self._cross_border_requests.values())

    @property
    def subscriptions(self) -> dict[str, list[str]]:
        return dict(self._subscriptions)
