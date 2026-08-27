# GFIN Temporal Intelligence Service
#
# Per Advanced Intelligence Superset Directive v1.0 §5-6:
# - Event timeline
# - Entity history
# - Relationship history
# - Temporal graph edges
# - Before/after comparisons
# - First-seen / last-seen
# - Change events
# - Temporal query engine
#
# Layer A: In-memory temporal store with query engine
# Layer B: Time-series database / temporal graph backend (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import utc_now

# ═══════════════════════════════════════════════
# TEMPORAL EVENT TYPES
# ═══════════════════════════════════════════════


class TemporalEventType(StrEnum):
    """Types of temporal events tracked by GFIN."""

    ENTITY_CREATED = "ENTITY_CREATED"
    ENTITY_OBSERVED = "ENTITY_OBSERVED"
    ENTITY_CHANGED = "ENTITY_CHANGED"
    ENTITY_DISAPPEARED = "ENTITY_DISAPPEARED"
    RELATIONSHIP_CREATED = "RELATIONSHIP_CREATED"
    RELATIONSHIP_CHANGED = "RELATIONSHIP_CHANGED"
    RELATIONSHIP_ENDED = "RELATIONSHIP_ENDED"
    INFRASTRUCTURE_CHANGED = "INFRASTRUCTURE_CHANGED"
    FIRST_SEEN = "FIRST_SEEN"
    LAST_SEEN = "LAST_SEEN"
    CASE_EVENT = "CASE_EVENT"
    ALERT = "ALERT"
    INVESTIGATOR_ACTION = "INVESTIGATOR_ACTION"


class ChangeType(StrEnum):
    """How a value changed."""

    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    REPLACED = "REPLACED"


class ConfidenceLevel(StrEnum):
    """Confidence in a temporal observation."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ═══════════════════════════════════════════════
# TEMPORAL EVENT
# ═══════════════════════════════════════════════


class TemporalEvent(BaseModel):
    """A single temporal event — something that happened at a point in time.

    Every event has provenance: source, actor, timestamp, evidence.
    Events are immutable once created.
    """

    event_id: str = Field(default_factory=lambda: f"TEV-{uuid4().hex[:8].upper()}")
    event_type: TemporalEventType
    entity_id: str  # The entity this event is about
    entity_type: str  # DOMAIN, IP, EMAIL, etc.
    timestamp: datetime = Field(default_factory=utc_now)
    observed_at: datetime = Field(default_factory=utc_now)  # When the event was actually observed
    source: str  # Provenance: which source reported this
    actor: str = ""  # Who/what caused this event
    description: str = ""
    change_type: ChangeType | None = None
    old_value: str | None = None
    new_value: str | None = None
    related_entity_id: str | None = None  # For relationship events
    related_entity_type: str | None = None
    relationship_type: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_id: str | None = None  # Link to evidence vault
    classification: str = "PUBLIC"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def to_hash(self) -> str:
        """Content hash for integrity verification."""
        content = f"{self.event_id}:{self.event_type}:{self.entity_id}:{self.timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()


# ═══════════════════════════════════════════════
# ENTITY HISTORY
# ═══════════════════════════════════════════════


class EntityHistoryEntry(BaseModel):
    """A snapshot of an entity's state at a point in time."""

    entry_id: str = Field(default_factory=lambda: f"EHI-{uuid4().hex[:8].upper()}")
    entity_id: str
    entity_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    source: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    relationships: list[dict[str, str]] = Field(default_factory=list)  # [{type, target_id, target_type}]
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_id: str | None = None

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# TEMPORAL EDGE (time-stamped relationship)
# ═══════════════════════════════════════════════


class TemporalEdge(BaseModel):
    """A relationship between two entities with a time dimension.

    Unlike a static graph edge, a temporal edge has:
    - valid_from: when the relationship started
    - valid_to: when it ended (None = still active)
    - Multiple versions preserved (not overwritten)
    """

    edge_id: str = Field(default_factory=lambda: f"TED-{uuid4().hex[:8].upper()}")
    source_entity_id: str
    source_entity_type: str
    target_entity_id: str
    target_entity_type: str
    relationship_type: str  # RESOLVES_TO, HOSTS, USES, etc.
    valid_from: datetime = Field(default_factory=utc_now)
    valid_to: datetime | None = None  # None = currently active
    source: str  # Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    @property
    def is_active(self) -> bool:
        return self.valid_to is None

    def was_active_at(self, timestamp: datetime) -> bool:
        """Check if this edge was active at a specific time."""
        if timestamp < self.valid_from:
            return False
        return not (self.valid_to is not None and timestamp > self.valid_to)


# ═══════════════════════════════════════════════
# CHANGE DETECTION RESULT
# ═══════════════════════════════════════════════


class TemporalChange(BaseModel):
    """A detected change between two points in time."""

    change_id: str = Field(default_factory=lambda: f"TCH-{uuid4().hex[:8].upper()}")
    entity_id: str
    entity_type: str
    change_type: ChangeType
    field: str  # What changed
    old_value: str | None = None
    new_value: str | None = None
    first_timestamp: datetime = Field(default_factory=utc_now)
    second_timestamp: datetime = Field(default_factory=utc_now)
    source_first: str = ""
    source_second: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    description: str = ""
    evidence_id: str | None = None

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# TEMPORAL QUERY RESULT
# ═══════════════════════════════════════════════


class TemporalQueryResult(BaseModel):
    """Result of a temporal query."""

    query_type: str  # "state_at", "changes_between", "first_seen", "last_seen", "timeline"
    entity_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    events: list[TemporalEvent] = Field(default_factory=list)
    edges: list[TemporalEdge] = Field(default_factory=list)
    changes: list[TemporalChange] = Field(default_factory=list)
    history_entries: list[EntityHistoryEntry] = Field(default_factory=list)
    summary: str = ""

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# TEMPORAL INTELLIGENCE SERVICE
# ═══════════════════════════════════════════════


class TemporalIntelligenceService:
    """Service for tracking and querying temporal intelligence.

    Layer A: In-memory storage with full query capabilities.
    Layer B: Time-series database backend (REQUIRES EXTERNAL INFRASTRUCTURE).

    Key principle: NEVER overwrite historical state.
    Every change creates a new temporal event and/or edge version.
    """

    def __init__(self) -> None:
        self._events: list[TemporalEvent] = []
        self._edges: list[TemporalEdge] = []
        self._history: dict[str, list[EntityHistoryEntry]] = defaultdict(list)
        self._first_seen: dict[str, datetime] = {}
        self._last_seen: dict[str, datetime] = {}

    # ─── Event Recording ───

    def record_event(self, event: TemporalEvent) -> TemporalEvent:
        """Record a temporal event. Events are immutable once stored."""
        self._events.append(event)

        # Track first/last seen
        key = f"{event.entity_type}:{event.entity_id}"
        if key not in self._first_seen or event.observed_at < self._first_seen[key]:
            self._first_seen[key] = event.observed_at
        if key not in self._last_seen or event.observed_at > self._last_seen[key]:
            self._last_seen[key] = event.observed_at

        return event

    def record_entity_observation(
        self,
        entity_id: str,
        entity_type: str,
        source: str,
        observed_at: datetime | None = None,
        attributes: dict[str, Any] | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        evidence_id: str | None = None,
    ) -> TemporalEvent:
        """Record that an entity was observed (seen) at a specific time."""
        ts = observed_at or utc_now()
        event = TemporalEvent(
            event_type=TemporalEventType.ENTITY_OBSERVED,
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=ts,
            observed_at=ts,
            source=source,
            description=f"Entity {entity_id} observed by {source}",
            confidence=confidence,
            evidence_id=evidence_id,
            metadata=attributes or {},
        )
        self.record_event(event)

        # Also record in history
        self._add_history_entry(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=ts,
            source=source,
            attributes=attributes or {},
            confidence=confidence,
            evidence_id=evidence_id,
        )

        return event

    def record_relationship(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
        relationship_type: str,
        source: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        evidence_id: str | None = None,
    ) -> TemporalEdge:
        """Record a temporal relationship edge.

        If a previous edge of the same type existed, it is ended (valid_to set)
        but NOT deleted — preserving history.
        """
        vf = valid_from or utc_now()

        # End any existing active edges of the same type from the same source
        # This preserves history (old edges kept with valid_to set) while
        # ensuring only one active edge of each type per source at a time
        for edge in self._edges:
            if (
                edge.source_entity_id == source_entity_id
                and edge.relationship_type == relationship_type
                and edge.is_active
            ):
                edge.valid_to = vf

        # Create new edge
        edge = TemporalEdge(
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            target_entity_id=target_entity_id,
            target_entity_type=target_entity_type,
            relationship_type=relationship_type,
            valid_from=vf,
            valid_to=valid_to,
            source=source,
            confidence=confidence,
            evidence_id=evidence_id,
        )
        self._edges.append(edge)

        # Record the relationship event
        event = TemporalEvent(
            event_type=TemporalEventType.RELATIONSHIP_CREATED,
            entity_id=source_entity_id,
            entity_type=source_entity_type,
            timestamp=vf,
            observed_at=vf,
            source=source,
            description=f"{source_entity_type} {source_entity_id} -> {relationship_type} -> {target_entity_type} {target_entity_id}",
            related_entity_id=target_entity_id,
            related_entity_type=target_entity_type,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence_id=evidence_id,
        )
        self.record_event(event)

        return edge

    def end_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        ended_at: datetime | None = None,
        source: str = "system",
        reason: str = "",
    ) -> TemporalEdge | None:
        """End an active relationship (set valid_to). Does not delete it."""
        ts = ended_at or utc_now()
        for edge in self._edges:
            if (
                edge.source_entity_id == source_entity_id
                and edge.target_entity_id == target_entity_id
                and edge.relationship_type == relationship_type
                and edge.is_active
            ):
                edge.valid_to = ts
                self.record_event(
                    TemporalEvent(
                        event_type=TemporalEventType.RELATIONSHIP_ENDED,
                        entity_id=source_entity_id,
                        entity_type=edge.source_entity_type,
                        timestamp=ts,
                        observed_at=ts,
                        source=source,
                        description=f"Relationship {relationship_type} ended: {reason}",
                        related_entity_id=target_entity_id,
                        related_entity_type=edge.target_entity_type,
                        relationship_type=relationship_type,
                    )
                )
                return edge
        return None

    # ─── History ───

    def _add_history_entry(
        self,
        entity_id: str,
        entity_type: str,
        timestamp: datetime,
        source: str,
        attributes: dict[str, Any],
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        evidence_id: str | None = None,
    ) -> EntityHistoryEntry:
        entry = EntityHistoryEntry(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=timestamp,
            source=source,
            attributes=attributes,
            confidence=confidence,
            evidence_id=evidence_id,
        )
        self._history[entity_id].append(entry)
        return entry

    # ─── Temporal Queries ───

    def get_entity_timeline(
        self,
        entity_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> TemporalQueryResult:
        """Get the complete timeline for an entity."""
        events = [
            e for e in self._events
            if e.entity_id == entity_id
            and (start_time is None or e.observed_at >= start_time)
            and (end_time is None or e.observed_at <= end_time)
        ]
        events.sort(key=lambda e: e.observed_at)

        edges = [
            ed for ed in self._edges
            if (ed.source_entity_id == entity_id or ed.target_entity_id == entity_id)
        ]

        return TemporalQueryResult(
            query_type="timeline",
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            events=events,
            edges=edges,
            history_entries=self._history.get(entity_id, []),
            summary=f"Timeline for {entity_id}: {len(events)} events, {len(edges)} edges",
        )

    def get_state_at_time(
        self,
        entity_id: str,
        timestamp: datetime,
    ) -> TemporalQueryResult:
        """What was the state of an entity at a specific time?

    Returns all active relationships and known attributes at that point.
    """
        active_edges = [
            ed for ed in self._edges
            if (ed.source_entity_id == entity_id or ed.target_entity_id == entity_id)
            and ed.was_active_at(timestamp)
        ]

        history_at_time = [
            h for h in self._history.get(entity_id, [])
            if h.timestamp <= timestamp
        ]
        history_at_time.sort(key=lambda h: h.timestamp)

        return TemporalQueryResult(
            query_type="state_at",
            entity_id=entity_id,
            start_time=timestamp,
            end_time=timestamp,
            edges=active_edges,
            history_entries=history_at_time,
            summary=f"State of {entity_id} at {timestamp.isoformat()}: {len(active_edges)} active edges",
        )

    def get_changes_between(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TemporalQueryResult:
        """What changed for an entity between two points in time?"""
        events = [
            e for e in self._events
            if e.entity_id == entity_id
            and start_time <= e.observed_at <= end_time
            and e.event_type in (
                TemporalEventType.ENTITY_CHANGED,
                TemporalEventType.RELATIONSHIP_CREATED,
                TemporalEventType.RELATIONSHIP_CHANGED,
                TemporalEventType.RELATIONSHIP_ENDED,
                TemporalEventType.ENTITY_DISAPPEARED,
                TemporalEventType.INFRASTRUCTURE_CHANGED,
            )
        ]
        events.sort(key=lambda e: e.observed_at)

        # Detect attribute changes from history
        changes: list[TemporalChange] = []
        history = self._history.get(entity_id, [])
        history_in_range = [h for h in history if start_time <= h.timestamp <= end_time]
        history_in_range.sort(key=lambda h: h.timestamp)

        for i in range(1, len(history_in_range)):
            prev = history_in_range[i - 1]
            curr = history_in_range[i]
            all_keys = set(prev.attributes.keys()) | set(curr.attributes.keys())
            for key in all_keys:
                old_val = prev.attributes.get(key)
                new_val = curr.attributes.get(key)
                if old_val != new_val:
                    changes.append(
                        TemporalChange(
                            entity_id=entity_id,
                            entity_type=curr.entity_type,
                            change_type=ChangeType.MODIFIED if old_val and new_val else (ChangeType.ADDED if new_val else ChangeType.REMOVED),
                            field=key,
                            old_value=str(old_val) if old_val else None,
                            new_value=str(new_val) if new_val else None,
                            first_timestamp=prev.timestamp,
                            second_timestamp=curr.timestamp,
                            source_first=prev.source,
                            source_second=curr.source,
                            description=f"Field '{key}' changed from '{old_val}' to '{new_val}'",
                        )
                    )

        return TemporalQueryResult(
            query_type="changes_between",
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            events=events,
            changes=changes,
            summary=f"Changes for {entity_id} between {start_time.isoformat()} and {end_time.isoformat()}: {len(changes)} attribute changes, {len(events)} events",
        )

    def get_first_seen(self, entity_id: str) -> datetime | None:
        """When was an entity first seen?"""
        key_pattern = f":{entity_id}"
        for key, ts in self._first_seen.items():
            if key.endswith(key_pattern):
                return ts
        # Fallback: search events
        entity_events = [e for e in self._events if e.entity_id == entity_id]
        if entity_events:
            return min(e.observed_at for e in entity_events)
        return None

    def get_last_seen(self, entity_id: str) -> datetime | None:
        """When was an entity last seen?"""
        key_pattern = f":{entity_id}"
        for key, ts in self._last_seen.items():
            if key.endswith(key_pattern):
                return ts
        # Fallback: search events
        entity_events = [e for e in self._events if e.entity_id == entity_id]
        if entity_events:
            return max(e.observed_at for e in entity_events)
        return None

    def get_new_entities(
        self,
        entity_type: str | None = None,
        after: datetime | None = None,
    ) -> list[str]:
        """What entities appeared for the first time after a given date?"""
        if after is None:
            after = datetime(1970, 1, 1)
        result = []
        for key, ts in self._first_seen.items():
            if ts >= after:
                if entity_type is None or key.startswith(f"{entity_type}:"):
                    entity_id = key.split(":", 1)[1]
                    result.append(entity_id)
        return result

    def get_disappeared_entities(
        self,
        entity_type: str | None = None,
        before: datetime | None = None,
    ) -> list[str]:
        """What entities disappeared (last seen before a given date)?"""
        if before is None:
            before = utc_now()
        result = []
        for key, ts in self._last_seen.items():
            if ts < before:
                # Check if there's no newer observation
                if entity_type is None or key.startswith(f"{entity_type}:"):
                    entity_id = key.split(":", 1)[1]
                    result.append(entity_id)
        return result

    def get_infrastructure_changes(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[TemporalChange]:
        """Detect infrastructure changes for an entity between two times."""
        result = self.get_changes_between(entity_id, start_time, end_time)
        infra_fields = {"ip", "asn", "nameserver", "hosting", "tls_cert", "server"}
        return [c for c in result.changes if c.field.lower() in infra_fields]

    # ─── Explainability ───

    def explain_entity(self, entity_id: str) -> dict[str, Any]:
        """Provide explainable temporal context for an entity."""
        first = self.get_first_seen(entity_id)
        last = self.get_last_seen(entity_id)
        timeline = self.get_entity_timeline(entity_id)

        active_edges = [e for e in timeline.edges if e.is_active]
        ended_edges = [e for e in timeline.edges if not e.is_active]

        return {
            "entity_id": entity_id,
            "first_seen": first.isoformat() if first else None,
            "last_seen": last.isoformat() if last else None,
            "total_events": len(timeline.events),
            "active_relationships": len(active_edges),
            "historical_relationships": len(ended_edges),
            "timeline_summary": [
                {
                    "timestamp": e.observed_at.isoformat(),
                    "type": e.event_type,
                    "description": e.description,
                    "source": e.source,
                    "confidence": e.confidence,
                }
                for e in timeline.events[-10:]  # Last 10 events
            ],
            "explanation": f"Entity {entity_id} was first observed at {first.isoformat() if first else 'unknown'} "
            f"and last seen at {last.isoformat() if last else 'unknown'}. "
            f"It has {len(active_edges)} active and {len(ended_edges)} historical relationships.",
        }

    # ─── Stats ───

    def stats(self) -> dict[str, Any]:
        """Service statistics."""
        return {
            "total_events": len(self._events),
            "total_edges": len(self._edges),
            "active_edges": sum(1 for e in self._edges if e.is_active),
            "ended_edges": sum(1 for e in self._edges if not e.is_active),
            "tracked_entities": len(self._first_seen),
            "history_entries": sum(len(v) for v in self._history.values()),
        }
