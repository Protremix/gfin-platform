# GFIN Event Bus — Module 05
#
# Per Master Spec §9 and Module 05:
# - Kafka topic definitions (14 topics), schemas, producers, consumers
# - Retry with max attempts + backoff
# - Dead-letter queue
#
# Layer A: InMemoryEventBus with full pub/sub, retry, DLQ, schema validation
# Layer B: KafkaEventBus — REQUIRES EXTERNAL INFRASTRUCTURE
#
# Acceptance: Events survive service restarts and are processed reliably.
# (Layer A: events survive within process; Layer B: Kafka durability)
#
# GPT Luna guidance:
# - Canonical event envelope (event ID, type, schema version, timestamp, producer, correlation ID, payload)
# - Schema validation at publish/consume time
# - Producer/consumer adapters decoupled from Kafka
# - Retry with max attempts + backoff
# - In-memory DLQ (event, failure reason, attempt count, timestamps)
# - Define 14 Kafka topics as version-controlled interfaces now

from __future__ import annotations

import asyncio
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import utc_now

# ═══════════════════════════════════════════════
# KAFKA TOPIC DEFINITIONS (14 topics from Master Spec §9)
# ═══════════════════════════════════════════════


class TopicDefinition(BaseModel):
    """Version-controlled Kafka topic definition.

    These are interface contracts — defined now, provisioned in Layer B.
    """

    name: str
    description: str
    partition_key: str  # Field used for partitioning
    retention_hours: int = 168  # 7 days default
    partitions: int = 3
    replication_factor: int = 3
    schema_version: str = "1.0"
    dlq_topic: str  # Associated dead-letter queue topic


KAFKA_TOPICS: dict[str, TopicDefinition] = {
    "entity.created": TopicDefinition(
        name="entity.created",
        description="New entity created in the system (person, phone, domain, etc.)",
        partition_key="entity_type",
        retention_hours=168,
        partitions=6,
        replication_factor=3,
        dlq_topic="entity.created.dlq",
    ),
    "entity.updated": TopicDefinition(
        name="entity.updated",
        description="Entity updated (merge, split, metadata change)",
        partition_key="entity_id",
        retention_hours=168,
        partitions=6,
        replication_factor=3,
        dlq_topic="entity.updated.dlq",
    ),
    "observation.created": TopicDefinition(
        name="observation.created",
        description="New observation recorded about an entity",
        partition_key="entity_id",
        retention_hours=336,  # 14 days
        partitions=6,
        replication_factor=3,
        dlq_topic="observation.created.dlq",
    ),
    "relationship.created": TopicDefinition(
        name="relationship.created",
        description="New relationship established between entities",
        partition_key="source_entity_id",
        retention_hours=336,
        partitions=3,
        replication_factor=3,
        dlq_topic="relationship.created.dlq",
    ),
    "evidence.created": TopicDefinition(
        name="evidence.created",
        description="New evidence artifact recorded",
        partition_key="entity_id",
        retention_hours=8760,  # 1 year — evidence is long-lived
        partitions=6,
        replication_factor=3,
        dlq_topic="evidence.created.dlq",
    ),
    "report.created": TopicDefinition(
        name="report.created",
        description="New fraud report submitted by citizen or police",
        partition_key="report_id",
        retention_hours=2160,  # 90 days
        partitions=6,
        replication_factor=3,
        dlq_topic="report.created.dlq",
    ),
    "campaign.created": TopicDefinition(
        name="campaign.created",
        description="New fraud campaign identified",
        partition_key="campaign_id",
        retention_hours=2160,
        partitions=3,
        replication_factor=3,
        dlq_topic="campaign.created.dlq",
    ),
    "campaign.updated": TopicDefinition(
        name="campaign.updated",
        description="Campaign status update (new entities, risk change, etc.)",
        partition_key="campaign_id",
        retention_hours=2160,
        partitions=3,
        replication_factor=3,
        dlq_topic="campaign.updated.dlq",
    ),
    "infrastructure.changed": TopicDefinition(
        name="infrastructure.changed",
        description="Infrastructure change detected (DNS, SSL cert, IP, domain)",
        partition_key="entity_id",
        retention_hours=336,
        partitions=3,
        replication_factor=3,
        dlq_topic="infrastructure.changed.dlq",
    ),
    "risk.changed": TopicDefinition(
        name="risk.changed",
        description="Risk score change for an entity",
        partition_key="entity_id",
        retention_hours=168,
        partitions=3,
        replication_factor=3,
        dlq_topic="risk.changed.dlq",
    ),
    "alert.created": TopicDefinition(
        name="alert.created",
        description="Global Early Warning alert triggered",
        partition_key="alert_id",
        retention_hours=2160,
        partitions=3,
        replication_factor=3,
        dlq_topic="alert.created.dlq",
    ),
    "police.match": TopicDefinition(
        name="police.match",
        description="Entity matched against police federated data",
        partition_key="entity_id",
        retention_hours=4380,  # 6 months
        partitions=3,
        replication_factor=3,
        dlq_topic="police.match.dlq",
    ),
    "police.request": TopicDefinition(
        name="police.request",
        description="Request sent to police federation (data, verification, etc.)",
        partition_key="request_id",
        retention_hours=4380,
        partitions=3,
        replication_factor=3,
        dlq_topic="police.request.dlq",
    ),
    "audit.event": TopicDefinition(
        name="audit.event",
        description="Audit trail event (user action, system action, security event)",
        partition_key="actor_id",
        retention_hours=8760,  # 1 year
        partitions=3,
        replication_factor=3,
        dlq_topic="audit.event.dlq",
    ),
}


def get_topic_definition(name: str) -> TopicDefinition:
    """Get a Kafka topic definition by name."""
    if name not in KAFKA_TOPICS:
        raise ValueError(f"Unknown topic: {name}. Valid topics: {list(KAFKA_TOPICS.keys())}")
    return KAFKA_TOPICS[name]


def list_topics() -> list[str]:
    """List all defined Kafka topic names."""
    return list(KAFKA_TOPICS.keys())


# ═══════════════════════════════════════════════
# EVENT ENVELOPE (canonical, per Master Spec §9)
# ═══════════════════════════════════════════════


class ClassificationLevel(str, Enum):
    """Classification level for event data."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class Event(BaseModel):
    """Canonical event envelope — per Master Spec §9.

    Every event must contain:
    - event_id: unique identifier
    - event_type: Kafka topic name
    - schema_version: versioned schema for backward compatibility
    - timestamp: UTC timestamp
    - source: producing service/module
    - entity_refs: referenced entity IDs
    - classification: data classification level
    - correlation_id: for tracing event chains
    - payload: event-specific data
    """

    event_id: str = Field(default_factory=lambda: f"EVT-{uuid4().hex[:12].upper()}")
    event_type: str
    schema_version: str = "1.0"
    timestamp: datetime = Field(default_factory=utc_now)
    source: str  # Producing service (e.g., "entity-resolution", "evidence-engine")
    entity_refs: list[str] = Field(default_factory=list)
    classification: ClassificationLevel = ClassificationLevel.PUBLIC
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dict for transmission."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "entity_refs": self.entity_refs,
            "classification": self.classification,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


# ═══════════════════════════════════════════════
# EVENT SCHEMA VALIDATION
# ═══════════════════════════════════════════════


class EventSchema(BaseModel):
    """Versioned schema definition for an event type."""

    event_type: str
    schema_version: str = "1.0"
    required_fields: list[str]
    optional_fields: list[str] = Field(default_factory=list)


# Schema registry — defines what fields are expected per event type
SCHEMA_REGISTRY: dict[str, EventSchema] = {}


def register_schema(
    event_type: str, required_fields: list[str], optional_fields: list[str] | None = None
) -> None:
    """Register an event schema for validation."""
    SCHEMA_REGISTRY[event_type] = EventSchema(
        event_type=event_type,
        required_fields=required_fields,
        optional_fields=optional_fields or [],
    )


# Pre-register schemas for all 14 topics
register_schema("entity.created", ["entity_id", "entity_type", "normalized_value"])
register_schema("entity.updated", ["entity_id", "change_type"], ["old_value", "new_value"])
register_schema("observation.created", ["observation_id", "entity_id", "observation_type"])
register_schema(
    "relationship.created",
    ["relationship_id", "source_entity_id", "target_entity_id", "relationship_type"],
)
register_schema("evidence.created", ["evidence_id", "entity_id", "evidence_type", "source"])
register_schema("report.created", ["report_id", "reporter_id", "report_type"])
register_schema("campaign.created", ["campaign_id", "campaign_name"])
register_schema("campaign.updated", ["campaign_id", "update_type"])
register_schema("infrastructure.changed", ["entity_id", "change_type", "old_value", "new_value"])
register_schema("risk.changed", ["entity_id", "old_risk_score", "new_risk_score"])
register_schema("alert.created", ["alert_id", "alert_type", "entity_refs"])
register_schema("police.match", ["entity_id", "match_id", "match_confidence"])
register_schema("police.request", ["request_id", "request_type", "entity_id"])
register_schema("audit.event", ["actor_id", "action", "resource"])


def validate_event(event: Event) -> tuple[bool, str]:
    """Validate an event against its registered schema.

    Returns (is_valid, error_message).
    """
    if event.event_type not in SCHEMA_REGISTRY:
        # Unknown event type — allow but log (forward compatibility)
        return True, ""

    schema = SCHEMA_REGISTRY[event.event_type]
    missing = [f for f in schema.required_fields if f not in event.payload]
    if missing:
        return False, f"Missing required fields: {missing}"

    return True, ""


# ═══════════════════════════════════════════════
# DEAD-LETTER QUEUE ENTRY
# ═══════════════════════════════════════════════


class DLQEntry(BaseModel):
    """Dead-letter queue entry for failed events."""

    dlq_id: str = Field(default_factory=lambda: f"DLQ-{uuid4().hex[:12].upper()}")
    original_event: Event
    failure_reason: str
    attempt_count: int
    first_attempt_at: datetime
    last_attempt_at: datetime
    topic: str
    handler_id: str | None = None
    traceback: str | None = None

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# RETRY POLICY
# ═══════════════════════════════════════════════


class RetryPolicy(BaseModel):
    """Retry policy for event processing."""

    max_attempts: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    backoff_multiplier: float = 2.0

    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for a given attempt number (1-indexed)."""
        delay = self.initial_delay_ms * (self.backoff_multiplier ** (attempt - 1))
        return min(int(delay), self.max_delay_ms)


# ═══════════════════════════════════════════════
# EVENT BUS INTERFACE
# ═══════════════════════════════════════════════

# Handler can be sync or async
EventHandler = Callable[[Event], None | Awaitable[None]]


class EventBus(ABC):
    """Abstract event bus interface.

    All application code publishes and subscribes through this interface.
    The specific adapter (in-memory, Kafka) is selected by configuration.
    """

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event to the bus."""
        ...

    @abstractmethod
    async def subscribe(self, topic: str, handler: EventHandler) -> str:
        """Subscribe to a topic. Returns a subscription ID."""
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe by subscription ID."""
        ...

    @abstractmethod
    async def get_dlq_entries(self, topic: str | None = None) -> list[DLQEntry]:
        """Get dead-letter queue entries, optionally filtered by topic."""
        ...

    @abstractmethod
    async def replay_dlq_entry(self, dlq_id: str) -> bool:
        """Replay a dead-letter queue entry. Returns True if successful."""
        ...

    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """Get event bus metrics (published, consumed, failed, DLQ size)."""
        ...


# ═══════════════════════════════════════════════
# IN-MEMORY EVENT BUS (Layer A)
# ═══════════════════════════════════════════════


class InMemoryEventBus(EventBus):
    """Layer A: In-memory event bus with full pub/sub, retry, and DLQ.

    NOT for production. No persistence across restarts.
    Production uses KafkaEventBus (REQUIRES EXTERNAL INFRASTRUCTURE).

    Features:
    - Topic-based pub/sub
    - Schema validation at publish time
    - Retry with exponential backoff
    - Dead-letter queue for failed events
    - Metrics collection
    - Event history (for testing/replay within process)
    """

    def __init__(
        self, retry_policy: RetryPolicy | None = None, validate_on_publish: bool = True
    ) -> None:
        self._subscribers: dict[str, dict[str, EventHandler]] = defaultdict(dict)
        self._dlq: list[DLQEntry] = []
        self._retry_policy = retry_policy or RetryPolicy()
        self._validate_on_publish = validate_on_publish
        self._next_sub_id = 0
        self._event_history: list[Event] = []

        # Metrics
        self._metrics = {
            "published": 0,
            "consumed": 0,
            "failed": 0,
            "dlq_size": 0,
            "replayed": 0,
        }

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of its topic.

        Validates schema if validation is enabled.
        Dispatches to all handlers with retry logic.
        Failed handlers send the event to the DLQ after max attempts.
        """
        # Validate schema
        if self._validate_on_publish:
            is_valid, error = validate_event(event)
            if not is_valid:
                raise ValueError(f"Event schema validation failed: {error}")

        # Record event
        self._event_history.append(event)
        self._metrics["published"] += 1

        # Get subscribers for this topic
        handlers = self._subscribers.get(event.event_type, {})
        if not handlers:
            return

        # Dispatch to each handler with retry
        for sub_id, handler in list(handlers.items()):
            await self._dispatch_with_retry(event, handler, sub_id)

    async def _dispatch_with_retry(self, event: Event, handler: EventHandler, sub_id: str) -> None:
        """Dispatch event to handler with retry logic.

        On failure, retries up to max_attempts with exponential backoff.
        If all attempts fail, sends to DLQ.
        """
        last_error = ""
        last_traceback = None
        first_attempt_at = utc_now()

        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                # Success
                self._metrics["consumed"] += 1
                return
            except Exception as e:
                last_error = str(e)
                last_traceback = traceback.format_exc()
                if attempt < self._retry_policy.max_attempts:
                    # Wait before retry (exponential backoff)
                    delay_ms = self._retry_policy.get_delay_ms(attempt)
                    await asyncio.sleep(delay_ms / 1000.0)

        # All attempts failed — send to DLQ
        self._metrics["failed"] += 1
        dlq_entry = DLQEntry(
            original_event=event,
            failure_reason=last_error,
            attempt_count=self._retry_policy.max_attempts,
            first_attempt_at=first_attempt_at,
            last_attempt_at=utc_now(),
            topic=event.event_type,
            handler_id=sub_id,
            traceback=last_traceback,
        )
        self._dlq.append(dlq_entry)
        self._metrics["dlq_size"] = len(self._dlq)

    async def subscribe(self, topic: str, handler: EventHandler) -> str:
        """Subscribe to a topic. Returns a subscription ID."""
        if topic not in KAFKA_TOPICS and topic not in self._subscribers:
            # Allow custom topics but warn (for testing)
            pass
        self._next_sub_id += 1
        sub_id = f"SUB-{self._next_sub_id:04d}"
        self._subscribers[topic][sub_id] = handler
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe by subscription ID."""
        for topic_handlers in self._subscribers.values():
            if subscription_id in topic_handlers:
                del topic_handlers[subscription_id]
                return True
        return False

    async def get_dlq_entries(self, topic: str | None = None) -> list[DLQEntry]:
        """Get dead-letter queue entries, optionally filtered by topic."""
        if topic is None:
            return list(self._dlq)
        return [e for e in self._dlq if e.topic == topic]

    async def replay_dlq_entry(self, dlq_id: str) -> bool:
        """Replay a dead-letter queue entry.

        Re-dispatches the original event to all subscribers.
        Returns True if successful, False if DLQ entry not found or replay failed.
        """
        entry = None
        for e in self._dlq:
            if e.dlq_id == dlq_id:
                entry = e
                break

        if entry is None:
            return False

        # Re-dispatch the original event
        handlers = self._subscribers.get(entry.topic, {})
        success = True
        for handler in handlers.values():
            try:
                result = handler(entry.original_event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                success = False
                break

        if success:
            # Remove from DLQ on successful replay
            self._dlq.remove(entry)
            self._metrics["replayed"] += 1
            self._metrics["consumed"] += 1
            self._metrics["dlq_size"] = len(self._dlq)

        return success

    async def get_metrics(self) -> dict[str, Any]:
        """Get event bus metrics."""
        return {**self._metrics, "dlq_size": len(self._dlq)}

    def get_event_history(self) -> list[Event]:
        """Get all published events (for testing/debugging)."""
        return list(self._event_history)


# ═══════════════════════════════════════════════
# PRODUCER ADAPTER
# ═══════════════════════════════════════════════


class EventProducer:
    """Producer adapter — decouples application code from the event bus.

    Application services use this to publish events without knowing
    whether the underlying bus is in-memory or Kafka.
    """

    def __init__(self, bus: EventBus, source: str) -> None:
        self._bus = bus
        self._source = source

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        entity_refs: list[str] | None = None,
        classification: ClassificationLevel = ClassificationLevel.PUBLIC,
        correlation_id: str | None = None,
    ) -> Event:
        """Publish an event to the bus.

        Creates the event envelope and publishes it.
        Returns the created event.
        """
        event = Event(
            event_type=event_type,
            source=self._source,
            payload=payload,
            entity_refs=entity_refs or [],
            classification=classification,
            correlation_id=correlation_id,
        )
        await self._bus.publish(event)
        return event


# ═══════════════════════════════════════════════
# CONSUMER ADAPTER
# ═══════════════════════════════════════════════


class EventConsumer:
    """Consumer adapter — decouples application code from the event bus.

    Application services use this to subscribe to topics without knowing
    whether the underlying bus is in-memory or Kafka.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._subscriptions: dict[str, str] = {}  # topic → subscription_id

    async def subscribe(self, topic: str, handler: EventHandler) -> str:
        """Subscribe to a topic. Returns subscription ID."""
        sub_id = await self._bus.subscribe(topic, handler)
        self._subscriptions[topic] = sub_id
        return sub_id

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic."""
        sub_id = self._subscriptions.pop(topic, None)
        if sub_id is None:
            return False
        return await self._bus.unsubscribe(sub_id)

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all topics."""
        for topic in list(self._subscriptions.keys()):
            await self.unsubscribe(topic)


# ═══════════════════════════════════════════════
# EVENT BUS FACTORY
# ═══════════════════════════════════════════════


def create_event_bus(backend: str = "memory", **kwargs) -> EventBus:
    """Factory for creating an event bus by backend type.

    backends:
    - "memory": InMemoryEventBus (Layer A, default)
    - "kafka": KafkaEventBus (Layer B, REQUIRES EXTERNAL INFRASTRUCTURE)
    """
    if backend == "memory":
        return InMemoryEventBus(**kwargs)
    elif backend == "kafka":
        raise NotImplementedError(
            "KafkaEventBus requires external infrastructure (Kafka brokers). "
            "Use 'memory' backend for development. "
            "REQUIRES EXTERNAL INFRASTRUCTURE."
        )
    else:
        raise ValueError(f"Unknown event bus backend: {backend}")


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# The following capabilities are NOT available in Layer A:
#
# - Apache Kafka brokers (topic creation, partitioning, replication)
# - Durable event persistence across service restarts
# - Consumer groups with partition assignment and rebalancing
# - Kafka-backed dead-letter topics with offset management
# - Event replay from Kafka offsets (not just in-memory DLQ)
# - Exactly-once delivery semantics
# - Kafka Connect for source/sink connectors
# - Kafka Streams for event processing pipelines
# - Schema Registry integration (Confluent or equivalent)
# - Cross-service event distribution (in-memory bus is process-local only)
# - Production monitoring (Kafka metrics, consumer lag, throughput)
# - TLS/SSL encryption for event transmission
# - ACL-based topic access control
#
# All of the above are marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
# Do NOT consider the event bus production-ready until these are implemented.
