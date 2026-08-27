"""GFIN Police Console — Module 27.

Backend service for the Police Console app. Provides entity search,
investigation workspace, alert viewing, observation submission, and
cross-border request management for police operators.

Per Architecture Review §2: Police Console is one of three GFIN apps.

Layer A: In-memory service layer
Layer B: FastAPI REST + WebSocket + OIDC auth (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from services.cross_border_requests import (
    CrossBorderRequestEngine,
    UrgencyLevel,
)
from services.global_matching import GlobalMatchEngine, MatchPolicy

# ─── Enums ───


class ConsoleRole(StrEnum):
    OFFICER = "OFFICER"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class ConsoleAction(StrEnum):
    SEARCH_ENTITY = "search_entity"
    VIEW_ENTITY = "view_entity"
    SUBMIT_OBSERVATION = "submit_observation"
    VIEW_ALERTS = "view_alerts"
    VIEW_CAMPAIGN = "view_campaign"
    CREATE_CBR = "create_cross_border_request"
    VIEW_CBR = "view_cross_border_requests"
    MANAGE_INVESTIGATION = "manage_investigation"
    VIEW_AUDIT_TRAIL = "view_audit_trail"


class WorkspaceStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


# ─── Role permissions ───

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ConsoleRole.OFFICER.value: {
        ConsoleAction.SEARCH_ENTITY.value,
        ConsoleAction.VIEW_ENTITY.value,
        ConsoleAction.SUBMIT_OBSERVATION.value,
        ConsoleAction.VIEW_ALERTS.value,
        ConsoleAction.VIEW_CAMPAIGN.value,
        ConsoleAction.CREATE_CBR.value,
        ConsoleAction.VIEW_CBR.value,
        ConsoleAction.MANAGE_INVESTIGATION.value,
    },
    ConsoleRole.SUPERVISOR.value: {
        ConsoleAction.SEARCH_ENTITY.value,
        ConsoleAction.VIEW_ENTITY.value,
        ConsoleAction.SUBMIT_OBSERVATION.value,
        ConsoleAction.VIEW_ALERTS.value,
        ConsoleAction.VIEW_CAMPAIGN.value,
        ConsoleAction.CREATE_CBR.value,
        ConsoleAction.VIEW_CBR.value,
        ConsoleAction.MANAGE_INVESTIGATION.value,
        ConsoleAction.VIEW_AUDIT_TRAIL.value,
    },
    ConsoleRole.ADMIN.value: {a.value for a in ConsoleAction},
}


# ─── Models ───


class ConsoleSession(BaseModel):
    """A police console operator session."""

    session_id: str
    operator_id: str
    operator_name: str
    org_id: str
    jurisdiction: str
    role: str = ConsoleRole.OFFICER.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    active: bool = True

    def has_permission(self, action: str) -> bool:
        return action in ROLE_PERMISSIONS.get(self.role, set())

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


class ConsoleAuditEntry(BaseModel):
    """Audit entry for a console action."""

    id: str
    session_id: str
    operator_id: str
    operator_name: str
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InvestigationWorkspace(BaseModel):
    """A workspace for an ongoing investigation."""

    id: str
    name: str
    operator_id: str
    org_id: str
    jurisdiction: str
    entity_ids: list[str] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)
    status: str = WorkspaceStatus.OPEN.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    def add_entity(self, entity_id: str) -> None:
        if entity_id not in self.entity_ids:
            self.entity_ids.append(entity_id)
            self.updated_at = datetime.now(UTC)

    def add_note(self, note_text: str, author: str = "") -> None:
        self.notes.append(
            {
                "text": note_text,
                "author": author,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        self.updated_at = datetime.now(UTC)

    def set_status(self, status: str) -> None:
        self.status = status
        self.updated_at = datetime.now(UTC)


class SearchResult(BaseModel):
    """A search result from the console."""

    entity_id: str
    entity_type: str
    entity_value: str
    jurisdiction: str
    confidence: str = "LOW"
    first_seen: str | None = None
    last_seen: str | None = None
    related_campaign: str | None = None


class ObservationSubmission(BaseModel):
    """An observation submitted through the console."""

    id: str
    operator_id: str
    org_id: str
    entity_type: str
    entity_value: str
    observation_text: str = ""
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Console Audit Logger ───


class ConsoleAuditLogger:
    """Audit logger for console actions."""

    def __init__(self) -> None:
        self._entries: list[ConsoleAuditEntry] = []
        self._counter = 0

    def log(
        self,
        session: ConsoleSession,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> ConsoleAuditEntry:
        self._counter += 1
        entry = ConsoleAuditEntry(
            id=f"CA-{self._counter:06d}",
            session_id=session.session_id,
            operator_id=session.operator_id,
            operator_name=session.operator_name,
            action=action,
            details=details or {},
        )
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        session_id: str | None = None,
        operator_id: str | None = None,
    ) -> list[ConsoleAuditEntry]:
        result = list(self._entries)
        if session_id:
            result = [e for e in result if e.session_id == session_id]
        if operator_id:
            result = [e for e in result if e.operator_id == operator_id]
        return result

    @property
    def count(self) -> int:
        return len(self._entries)


# ─── Police Console Service ───


class PoliceConsoleService:
    """Main service for the Police Console.

    Provides entity search, investigation workspace, alerts, observations,
    and cross-border request management for police operators.
    """

    def __init__(
        self,
        match_engine: GlobalMatchEngine | None = None,
        cbr_engine: CrossBorderRequestEngine | None = None,
        audit_logger: ConsoleAuditLogger | None = None,
        alert_store: Any | None = None,
    ) -> None:
        self._match_engine = match_engine or GlobalMatchEngine()
        self._cbr_engine = cbr_engine or CrossBorderRequestEngine()
        self._audit = audit_logger or ConsoleAuditLogger()
        self._alert_store = alert_store or []
        self._sessions: dict[str, ConsoleSession] = {}
        self._workspaces: dict[str, InvestigationWorkspace] = {}
        self._observations: list[ObservationSubmission] = []
        self._session_counter = 0
        self._workspace_counter = 0
        self._observation_counter = 0

    @property
    def audit(self) -> ConsoleAuditLogger:
        return self._audit

    @property
    def cbr_engine(self) -> CrossBorderRequestEngine:
        return self._cbr_engine

    @property
    def match_engine(self) -> GlobalMatchEngine:
        return self._match_engine

    def create_session(
        self,
        operator_id: str,
        operator_name: str,
        org_id: str,
        jurisdiction: str,
        role: str = ConsoleRole.OFFICER.value,
    ) -> ConsoleSession:
        """Create a new console session."""
        self._session_counter += 1
        session = ConsoleSession(
            session_id=f"CS-{self._session_counter:06d}",
            operator_id=operator_id,
            operator_name=operator_name,
            org_id=org_id,
            jurisdiction=jurisdiction,
            role=role,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> ConsoleSession | None:
        return self._sessions.get(session_id)

    def _check_permission(self, session: ConsoleSession, action: str) -> None:
        if not session.has_permission(action):
            raise PermissionError(f"Role {session.role} cannot perform {action}")
        if session.is_expired():
            raise PermissionError("Session expired")

    def search_entity(
        self,
        session_id: str,
        entity_type: str,
        entity_value: str,
    ) -> list[SearchResult]:
        """Search for entities in the global index."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.SEARCH_ENTITY.value)

        entries = self._match_engine.index.lookup(entity_type, entity_value)

        results = [
            SearchResult(
                entity_id=e.entity_id,
                entity_type=e.entity_type,
                entity_value=e.entity_value,
                jurisdiction=e.jurisdiction,
                confidence=e.confidence,
                first_seen=e.first_seen.isoformat() if e.first_seen else None,
                last_seen=e.last_seen.isoformat() if e.last_seen else None,
                related_campaign=e.related_campaign,
            )
            for e in entries
        ]

        self._audit.log(
            session,
            ConsoleAction.SEARCH_ENTITY.value,
            {
                "entity_type": entity_type,
                "entity_value": entity_value,
                "result_count": len(results),
            },
        )

        return results

    def view_entity(self, session_id: str, entity_id: str) -> dict[str, Any] | None:
        """View entity details (policy-filtered)."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.VIEW_ENTITY.value)

        entity = self._match_engine.index.get_entity(entity_id)
        if entity is None:
            return None

        safe_data = MatchPolicy.filter_entity(entity)

        self._audit.log(
            session,
            ConsoleAction.VIEW_ENTITY.value,
            {
                "entity_id": entity_id,
            },
        )

        return safe_data

    def submit_observation(
        self,
        session_id: str,
        entity_type: str,
        entity_value: str,
        observation_text: str = "",
    ) -> ObservationSubmission:
        """Submit an observation about an entity."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.SUBMIT_OBSERVATION.value)

        self._observation_counter += 1
        obs = ObservationSubmission(
            id=f"OBS-{self._observation_counter:06d}",
            operator_id=session.operator_id,
            org_id=session.org_id,
            entity_type=entity_type,
            entity_value=entity_value,
            observation_text=observation_text,
        )
        self._observations.append(obs)

        self._audit.log(
            session,
            ConsoleAction.SUBMIT_OBSERVATION.value,
            {
                "observation_id": obs.id,
                "entity_type": entity_type,
                "entity_value": entity_value,
            },
        )

        return obs

    def view_alerts(self, session_id: str) -> list[dict[str, Any]]:
        """View alerts for the operator's jurisdiction."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.VIEW_ALERTS.value)

        alerts = [a for a in self._alert_store if a.get("jurisdiction") == session.jurisdiction]

        self._audit.log(
            session,
            ConsoleAction.VIEW_ALERTS.value,
            {
                "alert_count": len(alerts),
            },
        )

        return alerts

    def set_alert_store(self, alerts: list[dict[str, Any]]) -> None:
        """Set the alert store (for testing)."""
        self._alert_store = alerts

    def create_cross_border_request(
        self,
        session_id: str,
        target_jurisdiction: str,
        entity_id: str,
        entity_type: str,
        legal_basis: str,
        purpose: str,
        investigator_name: str = "",
        case_reference: str = "",
        entity_value: str = "",
        requested_information: str = "",
        urgency: str = UrgencyLevel.ROUTINE.value,
    ) -> str:
        """Create a cross-border request. Returns request ID."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.CREATE_CBR.value)

        request = self._cbr_engine.create_request(
            requesting_org=session.org_id,
            requesting_jurisdiction=session.jurisdiction,
            target_jurisdiction=target_jurisdiction,
            entity_id=entity_id,
            entity_type=entity_type,
            investigator_name=investigator_name or session.operator_name,
            legal_basis=legal_basis,
            purpose=purpose,
            case_reference=case_reference,
            entity_value=entity_value,
            requested_information=requested_information,
            urgency=urgency,
        )

        self._audit.log(
            session,
            ConsoleAction.CREATE_CBR.value,
            {
                "request_id": request.id,
                "target_jurisdiction": target_jurisdiction,
            },
        )

        return request.id

    def view_cross_border_requests(self, session_id: str) -> list[dict[str, Any]]:
        """View cross-border requests involving the operator's org."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.VIEW_CBR.value)

        requests = [
            {
                "id": r.id,
                "requesting_org": r.requesting_org,
                "target_jurisdiction": r.target_jurisdiction,
                "status": r.status,
                "decision": r.decision,
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "urgency": r.urgency,
                "submitted_at": r.submitted_at.isoformat(),
            }
            for r in self._cbr_engine.requests
            if r.requesting_org == session.org_id
        ]

        self._audit.log(
            session,
            ConsoleAction.VIEW_CBR.value,
            {
                "request_count": len(requests),
            },
        )

        return requests

    def create_workspace(
        self,
        session_id: str,
        name: str,
    ) -> InvestigationWorkspace:
        """Create a new investigation workspace."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.MANAGE_INVESTIGATION.value)

        self._workspace_counter += 1
        workspace = InvestigationWorkspace(
            id=f"WS-{self._workspace_counter:06d}",
            name=name,
            operator_id=session.operator_id,
            org_id=session.org_id,
            jurisdiction=session.jurisdiction,
        )
        self._workspaces[workspace.id] = workspace

        self._audit.log(
            session,
            ConsoleAction.MANAGE_INVESTIGATION.value,
            {
                "action": "create_workspace",
                "workspace_id": workspace.id,
            },
        )

        return workspace

    def get_workspace(self, workspace_id: str) -> InvestigationWorkspace | None:
        return self._workspaces.get(workspace_id)

    def add_entity_to_workspace(self, session_id: str, workspace_id: str, entity_id: str) -> bool:
        """Add an entity to an investigation workspace."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.MANAGE_INVESTIGATION.value)

        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False

        ws.add_entity(entity_id)
        self._audit.log(
            session,
            ConsoleAction.MANAGE_INVESTIGATION.value,
            {
                "action": "add_entity",
                "workspace_id": workspace_id,
                "entity_id": entity_id,
            },
        )
        return True

    def add_workspace_note(self, session_id: str, workspace_id: str, note_text: str) -> bool:
        """Add a note to an investigation workspace."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.MANAGE_INVESTIGATION.value)

        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False

        ws.add_note(note_text, session.operator_name)
        self._audit.log(
            session,
            ConsoleAction.MANAGE_INVESTIGATION.value,
            {
                "action": "add_note",
                "workspace_id": workspace_id,
            },
        )
        return True

    def view_audit_trail(
        self,
        session_id: str,
        filter_session_id: str | None = None,
    ) -> list[ConsoleAuditEntry]:
        """View the audit trail (supervisor/admin only)."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        self._check_permission(session, ConsoleAction.VIEW_AUDIT_TRAIL.value)

        entries = self._audit.get_entries(session_id=filter_session_id)
        return entries

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def workspace_count(self) -> int:
        return len(self._workspaces)

    @property
    def observation_count(self) -> int:
        return len(self._observations)
