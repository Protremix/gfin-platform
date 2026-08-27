"""GFIN Global Matching — Module 25.

Global Match Engine in the Global Control Plane. Checks entities against
the Global Entity Index for international/cross-border matches. Returns only
permitted intelligence metadata (no case details, suspect names, etc.).

Per Terminology: "Global Match = entity observed elsewhere, NOT guilt."
Per Architecture Review §6.1: Match Engine sits above Federation Boundary.

Layer A: In-memory index and matching
Layer B: Distributed OpenSearch, Kafka streaming, ML fuzzy matching (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class MatchConfidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"


# ─── Permitted fields at federation boundary ───

PERMITTED_FIELDS: frozenset[str] = frozenset(
    {
        "entity_id",
        "entity_type",
        "entity_value",
        "jurisdiction",
        "confidence",
        "first_seen",
        "last_seen",
        "related_campaign",
        "intelligence_type",
        "access_level",
    }
)

NOT_PERMITTED_FIELDS: frozenset[str] = frozenset(
    {
        "suspect_names",
        "case_files",
        "investigation_notes",
        "raw_reports",
        "citizen_personal_info",
        "evidence_content",
        "police_internal_data",
    }
)


# ─── Models ───


class IndexedEntity(BaseModel):
    """An entity in the global index."""

    entity_id: str
    entity_type: str
    entity_value: str
    jurisdiction: str
    organization: str = ""
    confidence: str = MatchConfidence.LOW.value
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_campaign: str | None = None
    intelligence_type: str = "fraud_intelligence"
    access_level: str = "MATCH_ONLY"
    # Fields that do NOT cross the boundary:
    suspect_names: list[str] = Field(default_factory=list)
    case_files: list[str] = Field(default_factory=list)
    investigation_notes: str = ""
    raw_reports: list[str] = Field(default_factory=list)
    citizen_personal_info: dict[str, Any] = Field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return only permitted fields (for crossing federation boundary)."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "jurisdiction": self.jurisdiction,
            "confidence": self.confidence,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "related_campaign": self.related_campaign,
            "intelligence_type": self.intelligence_type,
            "access_level": self.access_level,
        }


class MatchEntry(BaseModel):
    """A single match entry for an entity in another jurisdiction."""

    entity_id: str
    jurisdiction: str
    organization: str = ""
    confidence: str = MatchConfidence.LOW.value
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_campaign: str | None = None
    intelligence_type: str = "fraud_intelligence"


class MatchResult(BaseModel):
    """Result of a global match query."""

    query_entity_type: str
    query_entity_value: str
    requesting_jurisdiction: str
    matched: bool
    matches: list[MatchEntry] = Field(default_factory=list)
    policy_filtered: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    match_id: str = ""


class MatchNotification(BaseModel):
    """A match notification sent to a police connector."""

    id: str
    org_id: str
    entity_id: str
    match_data: dict[str, Any] = Field(default_factory=dict)
    status: str = NotificationStatus.PENDING.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None

    def mark_sent(self) -> None:
        self.status = NotificationStatus.SENT.value
        self.sent_at = datetime.now(UTC)

    def mark_acknowledged(self) -> None:
        self.status = NotificationStatus.ACKNOWLEDGED.value
        self.acknowledged_at = datetime.now(UTC)


class MatchAuditEntry(BaseModel):
    """Audit entry for a match query."""

    id: str
    requesting_jurisdiction: str
    entity_type: str
    entity_value: str
    match_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Match Policy ───


class MatchPolicy:
    """Policy for what data is permitted to cross the federation boundary.

    Per Architecture Review §8.4 and Terminology:
    - Only permitted intelligence metadata crosses
    - No case files, suspect names, investigation notes, raw reports
    """

    @staticmethod
    def is_permitted(field_name: str) -> bool:
        """Check if a field is permitted to cross the boundary."""
        return field_name in PERMITTED_FIELDS

    @staticmethod
    def is_not_permitted(field_name: str) -> bool:
        """Check if a field is explicitly not permitted."""
        return field_name in NOT_PERMITTED_FIELDS

    @staticmethod
    def filter_match_data(data: dict[str, Any]) -> dict[str, Any]:
        """Filter a dict to only include permitted fields."""
        return {k: v for k, v in data.items() if k in PERMITTED_FIELDS}

    @staticmethod
    def filter_entity(entity: IndexedEntity) -> dict[str, Any]:
        """Filter an entity to only permitted fields (for crossing boundary)."""
        return entity.to_safe_dict()


# ─── Global Entity Index ───


class GlobalEntityIndex:
    """In-memory global index of entities across jurisdictions.

    Layer A: In-memory with dict-based lookup
    Layer B: Distributed OpenSearch/Elasticsearch cluster
    """

    def __init__(self) -> None:
        # {entity_type: {entity_value: [IndexedEntity, ...]}}
        self._index: dict[str, dict[str, list[IndexedEntity]]] = {}
        # {entity_id: IndexedEntity}
        self._by_id: dict[str, IndexedEntity] = {}
        self._counter = 0

    def register_entity(self, entity: IndexedEntity) -> str:
        """Register or update an entity in the global index."""
        if entity.entity_id not in self._by_id:
            self._counter += 1

        self._by_id[entity.entity_id] = entity

        if entity.entity_type not in self._index:
            self._index[entity.entity_type] = {}
        if entity.entity_value not in self._index[entity.entity_type]:
            self._index[entity.entity_type][entity.entity_value] = []

        # Check if already registered for this jurisdiction
        existing = self._index[entity.entity_type][entity.entity_value]
        for i, e in enumerate(existing):
            if e.jurisdiction == entity.jurisdiction:
                existing[i] = entity
                return entity.entity_id
        existing.append(entity)
        return entity.entity_id

    def lookup(self, entity_type: str, entity_value: str) -> list[IndexedEntity]:
        """Look up all entries for an entity across jurisdictions."""
        return list(self._index.get(entity_type, {}).get(entity_value, []))

    def get_entity(self, entity_id: str) -> IndexedEntity | None:
        """Get an entity by ID."""
        return self._by_id.get(entity_id)

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the index."""
        entity = self._by_id.pop(entity_id, None)
        if entity is None:
            return False

        entries = self._index.get(entity.entity_type, {}).get(entity.entity_value, [])
        self._index[entity.entity_type][entity.entity_value] = [
            e for e in entries if e.entity_id != entity_id
        ]
        return True

    @property
    def stats(self) -> dict[str, Any]:
        """Index statistics."""
        total = len(self._by_id)
        by_type: dict[str, int] = {}
        by_jurisdiction: dict[str, int] = {}
        for entity in self._by_id.values():
            by_type[entity.entity_type] = by_type.get(entity.entity_type, 0) + 1
            by_jurisdiction[entity.jurisdiction] = by_jurisdiction.get(entity.jurisdiction, 0) + 1
        return {
            "total_entities": total,
            "by_type": by_type,
            "by_jurisdiction": by_jurisdiction,
        }

    @property
    def count(self) -> int:
        return len(self._by_id)


# ─── Global Match Engine ───


class GlobalMatchEngine:
    """Global Match Engine — matches entities across jurisdictions.

    Per Architecture Review §6.1: sits in Global Control Plane above
    Federation Boundary. Returns only permitted intelligence metadata.
    """

    def __init__(
        self,
        index: GlobalEntityIndex | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._index = index or GlobalEntityIndex()
        self._event_bus = event_bus
        self._audit = audit_logger
        self._policy = MatchPolicy()
        self._notifications: dict[str, MatchNotification] = {}
        self._notification_counter = 0
        self._match_counter = 0
        self._audit_entries: list[MatchAuditEntry] = []
        self._audit_counter = 0

    @property
    def index(self) -> GlobalEntityIndex:
        return self._index

    def match(
        self,
        entity_type: str,
        entity_value: str,
        requesting_jurisdiction: str,
    ) -> MatchResult:
        """Match an entity against the global index.

        Returns matches from OTHER jurisdictions (not the requesting one).
        Per Match ≠ Guilt: results are "observed elsewhere", not criminal identity.
        """
        self._match_counter += 1
        match_id = f"GMATCH-{self._match_counter:06d}"

        all_entries = self._index.lookup(entity_type, entity_value)

        # Filter out same-jurisdiction matches
        cross_border_entries = [e for e in all_entries if e.jurisdiction != requesting_jurisdiction]

        # Apply policy filter
        matches = [
            MatchEntry(
                entity_id=e.entity_id,
                jurisdiction=e.jurisdiction,
                organization=e.organization,
                confidence=e.confidence,
                first_seen=e.first_seen,
                last_seen=e.last_seen,
                related_campaign=e.related_campaign,
                intelligence_type=e.intelligence_type,
            )
            for e in cross_border_entries
        ]

        result = MatchResult(
            query_entity_type=entity_type,
            query_entity_value=entity_value,
            requesting_jurisdiction=requesting_jurisdiction,
            matched=len(matches) > 0,
            matches=matches,
            policy_filtered=True,
            match_id=match_id,
        )

        # Audit log
        self._audit_counter += 1
        self._audit_entries.append(
            MatchAuditEntry(
                id=f"GAUDIT-{self._audit_counter:06d}",
                requesting_jurisdiction=requesting_jurisdiction,
                entity_type=entity_type,
                entity_value=entity_value,
                match_count=len(matches),
            )
        )

        if self._audit:
            with contextlib.suppress(Exception):
                self._audit.log(
                    user_id="system",
                    action="global_match",
                    resource_type="entity",
                    resource_id=entity_value,
                    details={
                        "match_id": match_id,
                        "matches": len(matches),
                        "requesting_jurisdiction": requesting_jurisdiction,
                    },
                )

        if self._event_bus and result.matched:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="match.global",
                    event={
                        "match_id": match_id,
                        "entity_type": entity_type,
                        "entity_value": entity_value,
                        "match_count": len(matches),
                        "requesting_jurisdiction": requesting_jurisdiction,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return result

    def match_batch(
        self,
        entities: list[dict[str, str]],
        requesting_jurisdiction: str,
    ) -> list[MatchResult]:
        """Match a batch of entities."""
        return [
            self.match(
                entity_type=e["entity_type"],
                entity_value=e["entity_value"],
                requesting_jurisdiction=requesting_jurisdiction,
            )
            for e in entities
        ]

    def notify_connector(
        self,
        org_id: str,
        match: MatchResult,
    ) -> MatchNotification:
        """Create a match notification for a police connector."""
        self._notification_counter += 1
        notification = MatchNotification(
            id=f"GNOTIF-{self._notification_counter:06d}",
            org_id=org_id,
            entity_id=match.matches[0].entity_id if match.matches else "",
            match_data={
                "match_id": match.match_id,
                "matches": [m.model_dump() for m in match.matches],
                "policy_filtered": True,
            },
        )
        self._notifications[notification.id] = notification
        return notification

    def send_notification(self, notification_id: str) -> bool:
        """Mark a notification as sent."""
        n = self._notifications.get(notification_id)
        if n and n.status == NotificationStatus.PENDING.value:
            n.mark_sent()

            if self._event_bus:
                with contextlib.suppress(Exception):
                    self._event_bus.publish(
                        topic="match.notification_sent",
                        event={
                            "notification_id": notification_id,
                            "org_id": n.org_id,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
            return True
        return False

    def acknowledge_notification(self, notification_id: str) -> bool:
        """Acknowledge a sent notification."""
        n = self._notifications.get(notification_id)
        if n and n.status == NotificationStatus.SENT.value:
            n.mark_acknowledged()
            return True
        return False

    def get_audit_log(self) -> list[MatchAuditEntry]:
        """Get match audit entries."""
        return list(self._audit_entries)

    @property
    def notification_count(self) -> int:
        return len(self._notifications)

    @property
    def match_count(self) -> int:
        return self._match_counter
