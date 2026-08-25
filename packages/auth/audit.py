# GFIN Audit Log — Immutable Security Event Logging
#
# Per Constitution Article XXVII and Master Spec §45:
# "Important actions must be auditable. Every tool call is authenticated,
#  authorized, logged, and attributable. Immutable audit trails are
#  maintained for security-critical operations."
#
# Layer A: In-memory + file-based audit log (development)
# Layer B: Append-only audit log with cryptographic integrity (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger("gfin.audit")


class AuditEventType(str, Enum):
    """Types of auditable security events."""

    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_CREATED = "auth.token_created"
    AUTH_TOKEN_REVOKED = "auth.token_revoked"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"
    AUTH_FAILED = "auth.failed"
    AUTHZ_ALLOW = "authz.allow"
    AUTHZ_DENY = "authz.deny"
    ENTITY_CREATE = "entity.create"
    ENTITY_UPDATE = "entity.update"
    ENTITY_DELETE = "entity.delete"
    REPORT_CREATE = "report.create"
    INVESTIGATION_CREATE = "investigation.create"
    INVESTIGATION_UPDATE = "investigation.update"
    FEDERATION_QUERY = "federation.query"
    FEDERATION_SHARE = "federation.share"
    ADMIN_USER_MANAGE = "admin.user_manage"
    ADMIN_CONFIG_CHANGE = "admin.config_change"
    SECURITY_RATE_LIMIT = "security.rate_limit"
    SECURITY_INPUT_REJECTED = "security.input_rejected"


@dataclass
class AuditEvent:
    """A single auditable event."""

    event_id: str
    event_type: AuditEventType
    user_id: str
    action: str
    resource_type: str
    resource_id: str | None
    decision: str  # ALLOW, DENY, N/A
    reason: str
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    hash: str = ""

    def compute_hash(self, prev_hash: str = "") -> str:
        """Compute SHA-256 hash of this event, chained to previous event."""
        self.prev_hash = prev_hash
        content = json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type.value,
                "user_id": self.user_id,
                "action": self.action,
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
                "decision": self.decision,
                "reason": self.reason,
                "timestamp": self.timestamp.isoformat(),
                "prev_hash": self.prev_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


class AuditLog:
    """Immutable, chain-of-hash audit log.

    Layer A: In-memory + optional file persistence (development)
    Layer B: Append-only store with cryptographic signatures (REQUIRES EXTERNAL INFRASTRUCTURE)
    """

    def __init__(self, persist_to_file: str | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._persist_path = persist_to_file
        self._chain_hash: str = ""

    def log(
        self,
        event_type: AuditEventType,
        user_id: str,
        action: str,
        resource_type: str = "",
        resource_id: str | None = None,
        decision: str = "N/A",
        reason: str = "",
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Record an audit event."""
        from uuid import uuid4

        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(UTC),
            metadata=metadata or {},
        )
        event.hash = event.compute_hash(self._chain_hash)
        self._chain_hash = event.hash
        self._events.append(event)

        logger.info(
            "audit_event",
            event_type=event_type.value,
            user_id=user_id,
            action=action,
            decision=decision,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if self._persist_path:
            self._persist(event)

        return event

    def query(
        self,
        user_id: str | None = None,
        event_type: AuditEventType | None = None,
        resource_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with filters."""
        results = self._events
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def verify_chain(self) -> bool:
        """Verify the integrity of the audit chain."""
        prev_hash = ""
        for event in self._events:
            expected_hash = event.compute_hash(prev_hash)
            if event.hash != expected_hash:
                return False
            prev_hash = event.hash
        return True

    def count(self) -> int:
        """Total number of audit events."""
        return len(self._events)

    def _persist(self, event: AuditEvent) -> None:
        """Append event to file (development mode)."""
        try:
            assert self._persist_path is not None
            with open(self._persist_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "event_id": event.event_id,
                            "event_type": event.event_type.value,
                            "user_id": event.user_id,
                            "action": event.action,
                            "resource_type": event.resource_type,
                            "resource_id": event.resource_id,
                            "decision": event.decision,
                            "reason": event.reason,
                            "timestamp": event.timestamp.isoformat(),
                            "hash": event.hash,
                            "prev_hash": event.prev_hash,
                        }
                    )
                    + "\n"
                )
        except Exception as e:
            logger.error("audit_persist_failed", error=str(e)[:100])
