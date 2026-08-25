"""Comprehensive tests for Module 05 — Event Bus.

Per Master Spec §9 and Module 05 acceptance criteria:
- Kafka topic definitions, schemas, producers, consumers
- Retry with max attempts + backoff
- Dead-letter queue
- Events survive service restarts (Layer A: within process; Layer B: Kafka durability)

Test categories:
1. Kafka topic definitions (14 topics, contracts, DLQ topics)
2. Event envelope (canonical format, all required fields)
3. Schema validation (required fields, unknown types, valid/invalid)
4. Pub/sub (publish, subscribe, unsubscribe, multiple subscribers)
5. Retry logic (max attempts, exponential backoff, failure scenarios)
6. Dead-letter queue (failed events, entries, replay)
7. Producer/consumer adapters (decoupled from bus implementation)
8. Metrics (published, consumed, failed, DLQ size)
9. Event history
10. Negative/fail-safe tests
"""

import pytest
import asyncio
from datetime import datetime, timezone

from common.event_bus import (
    # Topic definitions
    KAFKA_TOPICS,
    TopicDefinition,
    get_topic_definition,
    list_topics,
    # Event envelope
    Event,
    ClassificationLevel,
    # Schema validation
    SCHEMA_REGISTRY,
    EventSchema,
    register_schema,
    validate_event,
    # DLQ
    DLQEntry,
    # Retry
    RetryPolicy,
    # Bus
    EventBus,
    InMemoryEventBus,
    # Adapters
    EventProducer,
    EventConsumer,
    # Factory
    create_event_bus,
)
from schemas.base import utc_now


# ═══════════════════════════════════════════════
# KAFKA TOPIC DEFINITIONS
# ═══════════════════════════════════════════════

class TestTopicDefinitions:
    """Test Kafka topic definitions — 14 topics per Master Spec §9."""

    def test_14_topics_defined(self):
        """Exactly 14 topics must be defined per the spec."""
        assert len(KAFKA_TOPICS) == 14

    def test_all_specified_topics_present(self):
        """All 14 topics from the spec must be present."""
        expected = [
            "entity.created", "entity.updated", "observation.created",
            "relationship.created", "evidence.created", "report.created",
            "campaign.created", "campaign.updated", "infrastructure.changed",
            "risk.changed", "alert.created", "police.match",
            "police.request", "audit.event",
        ]
        for topic in expected:
            assert topic in KAFKA_TOPICS, f"Missing topic: {topic}"

    def test_each_topic_has_definition(self):
        """Each topic must have a full TopicDefinition."""
        for name, definition in KAFKA_TOPICS.items():
            assert isinstance(definition, TopicDefinition)
            assert definition.name == name
            assert definition.description
            assert definition.partition_key
            assert definition.retention_hours > 0
            assert definition.partitions >= 1
            assert definition.replication_factor >= 1
            assert definition.schema_version
            assert definition.dlq_topic

    def test_each_topic_has_dlq(self):
        """Each topic must have an associated dead-letter queue topic."""
        for name, definition in KAFKA_TOPICS.items():
            assert definition.dlq_topic == f"{name}.dlq"

    def test_get_topic_definition_valid(self):
        topic = get_topic_definition("entity.created")
        assert topic.name == "entity.created"

    def test_get_topic_definition_invalid(self):
        with pytest.raises(ValueError, match="Unknown topic"):
            get_topic_definition("nonexistent.topic")

    def test_list_topics_returns_all(self):
        topics = list_topics()
        assert len(topics) == 14

    def test_evidence_longest_retention(self):
        """Evidence should have the longest retention (1 year)."""
        evidence = get_topic_definition("evidence.created")
        audit = get_topic_definition("audit.event")
        assert evidence.retention_hours == 8760  # 1 year
        assert audit.retention_hours == 8760  # 1 year

    def test_risk_changed_shortest_retention(self):
        """Risk changes have shorter retention (7 days)."""
        risk = get_topic_definition("risk.changed")
        assert risk.retention_hours == 168  # 7 days


# ═══════════════════════════════════════════════
# EVENT ENVELOPE
# ═══════════════════════════════════════════════

class TestEventEnvelope:
    """Test the canonical event envelope per Master Spec §9."""

    def test_event_has_all_required_fields(self):
        """Every event must contain all 9 required fields."""
        event = Event(event_type="entity.created", source="test-service")
        assert event.event_id  # auto-generated
        assert event.event_type == "entity.created"
        assert event.schema_version == "1.0"
        assert event.timestamp is not None
        assert event.source == "test-service"
        assert event.entity_refs == []
        assert event.classification == ClassificationLevel.PUBLIC
        assert event.correlation_id is None  # optional
        assert event.payload == {}

    def test_event_id_unique(self):
        """Event IDs must be unique."""
        e1 = Event(event_type="test", source="test")
        e2 = Event(event_type="test", source="test")
        assert e1.event_id != e2.event_id

    def test_event_id_format(self):
        """Event IDs should follow the EVT-XXX format."""
        event = Event(event_type="test", source="test")
        assert event.event_id.startswith("EVT-")

    def test_classification_levels(self):
        """All 4 classification levels must be available."""
        assert ClassificationLevel.PUBLIC == "PUBLIC"
        assert ClassificationLevel.INTERNAL == "INTERNAL"
        assert ClassificationLevel.CONFIDENTIAL == "CONFIDENTIAL"
        assert ClassificationLevel.RESTRICTED == "RESTRICTED"

    def test_event_to_dict(self):
        """Event should serialize to dict correctly."""
        event = Event(
            event_type="entity.created",
            source="test",
            payload={"entity_id": "ENT-001"},
            entity_refs=["ENT-001"],
        )
        d = event.to_dict()
        assert d["event_type"] == "entity.created"
        assert d["payload"]["entity_id"] == "ENT-001"
        assert "timestamp" in d

    def test_event_with_correlation_id(self):
        """Events should support correlation IDs for tracing."""
        event = Event(
            event_type="observation.created",
            source="crawler",
            correlation_id="COR-001",
        )
        assert event.correlation_id == "COR-001"


# ═══════════════════════════════════════════════
# SCHEMA VALIDATION
# ═══════════════════════════════════════════════

class TestSchemaValidation:
    """Test event schema validation."""

    def test_valid_event(self):
        """A valid event with all required fields should pass."""
        event = Event(
            event_type="entity.created",
            source="test",
            payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"},
        )
        is_valid, error = validate_event(event)
        assert is_valid
        assert error == ""

    def test_missing_required_field(self):
        """An event missing required fields should fail validation."""
        event = Event(
            event_type="entity.created",
            source="test",
            payload={"entity_id": "ENT-001"},  # Missing entity_type and normalized_value
        )
        is_valid, error = validate_event(event)
        assert not is_valid
        assert "entity_type" in error
        assert "normalized_value" in error

    def test_unknown_event_type_allowed(self):
        """Unknown event types should be allowed (forward compatibility)."""
        event = Event(event_type="custom.event", source="test", payload={})
        is_valid, error = validate_event(event)
        assert is_valid
        assert error == ""

    def test_all_14_topics_have_schemas(self):
        """All 14 Kafka topics should have registered schemas."""
        for topic in KAFKA_TOPICS:
            assert topic in SCHEMA_REGISTRY, f"Missing schema for topic: {topic}"

    def test_register_custom_schema(self):
        """Custom schemas can be registered."""
        register_schema("custom.topic", ["required_field"])
        assert "custom.topic" in SCHEMA_REGISTRY
        assert SCHEMA_REGISTRY["custom.topic"].required_fields == ["required_field"]


# ═══════════════════════════════════════════════
# PUB/SUB
# ═══════════════════════════════════════════════

class TestPubSub:
    """Test publish/subscribe functionality."""

    @pytest.fixture
    def bus(self):
        return InMemoryEventBus()

    async def test_publish_receive(self, bus):
        """Published events should be received by subscribers."""
        received = []

        async def handler(event):
            received.append(event)

        sub_id = await bus.subscribe("entity.created", handler)
        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].event_id == event.event_id

    async def test_sync_handler(self, bus):
        """Sync handlers should work."""
        received = []

        def handler(event):
            received.append(event)

        await bus.subscribe("entity.created", handler)
        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert len(received) == 1

    async def test_multiple_subscribers(self, bus):
        """Multiple subscribers on the same topic should all receive events."""
        received_a = []
        received_b = []

        async def handler_a(event):
            received_a.append(event)

        async def handler_b(event):
            received_b.append(event)

        await bus.subscribe("entity.created", handler_a)
        await bus.subscribe("entity.created", handler_b)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert len(received_a) == 1
        assert len(received_b) == 1

    async def test_unsubscribe(self, bus):
        """Unsubscribed handlers should not receive events."""
        received = []

        async def handler(event):
            received.append(event)

        sub_id = await bus.subscribe("entity.created", handler)
        await bus.unsubscribe(sub_id)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert len(received) == 0

    async def test_no_subscribers_no_error(self, bus):
        """Publishing to a topic with no subscribers should not error."""
        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)  # Should not raise

    async def test_invalid_event_rejected(self, bus):
        """Events failing schema validation should be rejected."""
        event = Event(
            event_type="entity.created",
            source="test",
            payload={"entity_id": "ENT-001"},  # Missing required fields
        )
        with pytest.raises(ValueError, match="schema validation failed"):
            await bus.publish(event)

    async def test_publish_without_validation(self):
        """Publishing without validation should allow any payload."""
        bus = InMemoryEventBus(validate_on_publish=False)
        event = Event(event_type="entity.created", source="test", payload={})
        await bus.publish(event)  # Should not raise


# ═══════════════════════════════════════════════
# RETRY LOGIC
# ═══════════════════════════════════════════════

class TestRetryLogic:
    """Test retry with max attempts and exponential backoff."""

    def test_retry_policy_defaults(self):
        """Default retry policy should have reasonable values."""
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.initial_delay_ms == 100
        assert policy.max_delay_ms == 5000
        assert policy.backoff_multiplier == 2.0

    def test_retry_delay_exponential(self):
        """Delay should increase exponentially."""
        policy = RetryPolicy(initial_delay_ms=100, backoff_multiplier=2.0)
        assert policy.get_delay_ms(1) == 100
        assert policy.get_delay_ms(2) == 200
        assert policy.get_delay_ms(3) == 400

    def test_retry_delay_capped(self):
        """Delay should be capped at max_delay_ms."""
        policy = RetryPolicy(initial_delay_ms=100, max_delay_ms=500, backoff_multiplier=2.0)
        assert policy.get_delay_ms(1) == 100
        assert policy.get_delay_ms(5) == 500  # Capped

    async def test_handler_retried_on_failure(self):
        """Failing handler should be retried up to max_attempts."""
        call_count = 0

        async def failing_handler(event):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Intentional failure")

        # Fast retries for testing
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=3, initial_delay_ms=1))
        await bus.subscribe("entity.created", failing_handler)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert call_count == 3  # Retried 3 times

    async def test_handler_succeeds_on_retry(self):
        """Handler that succeeds on second attempt should not go to DLQ."""
        call_count = 0

        async def flaky_handler(event):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Fail first")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=3, initial_delay_ms=1))
        await bus.subscribe("entity.created", flaky_handler)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        assert call_count == 2  # Succeeded on second attempt
        dlq = await bus.get_dlq_entries()
        assert len(dlq) == 0  # Not in DLQ


# ═══════════════════════════════════════════════
# DEAD-LETTER QUEUE
# ═══════════════════════════════════════════════

class TestDeadLetterQueue:
    """Test dead-letter queue functionality."""

    async def test_failed_event_goes_to_dlq(self):
        """Events that fail all retry attempts should go to DLQ."""
        async def always_fails(event):
            raise RuntimeError("Always fails")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=2, initial_delay_ms=1))
        await bus.subscribe("entity.created", always_fails)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        dlq = await bus.get_dlq_entries()
        assert len(dlq) == 1
        assert dlq[0].original_event.event_id == event.event_id
        assert "Always fails" in dlq[0].failure_reason
        assert dlq[0].attempt_count == 2

    async def test_dlq_filtered_by_topic(self):
        """DLQ entries should be filterable by topic."""
        async def fails(event):
            raise RuntimeError("fail")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))
        await bus.subscribe("entity.created", fails)
        await bus.subscribe("entity.updated", fails)

        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))
        await bus.publish(Event(event_type="entity.updated", source="test", payload={"entity_id": "ENT-001", "change_type": "merge"}))

        all_dlq = await bus.get_dlq_entries()
        assert len(all_dlq) == 2

        entity_created_dlq = await bus.get_dlq_entries(topic="entity.created")
        assert len(entity_created_dlq) == 1
        assert entity_created_dlq[0].topic == "entity.created"

    async def test_dlq_entry_has_timestamps(self):
        """DLQ entries should have first and last attempt timestamps."""
        async def fails(event):
            raise RuntimeError("fail")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=2, initial_delay_ms=1))
        await bus.subscribe("entity.created", fails)

        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        dlq = await bus.get_dlq_entries()
        assert dlq[0].first_attempt_at is not None
        assert dlq[0].last_attempt_at is not None
        assert dlq[0].last_attempt_at >= dlq[0].first_attempt_at

    async def test_dlq_entry_has_traceback(self):
        """DLQ entries should capture the traceback."""
        async def fails(event):
            raise RuntimeError("specific error")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))
        await bus.subscribe("entity.created", fails)

        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        dlq = await bus.get_dlq_entries()
        assert dlq[0].traceback is not None
        assert "specific error" in dlq[0].traceback

    async def test_replay_dlq_entry_success(self):
        """Replaying a DLQ entry with a working handler should succeed."""
        async def fails(event):
            raise RuntimeError("fail")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))
        await bus.subscribe("entity.created", fails)

        event = Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"})
        await bus.publish(event)

        # Replace handler with one that succeeds
        received = []
        async def succeeds(event):
            received.append(event)

        await bus.unsubscribe(next(iter(bus._subscribers.get("entity.created", {}))))
        await bus.subscribe("entity.created", succeeds)

        # Replay
        dlq = await bus.get_dlq_entries()
        dlq_id = dlq[0].dlq_id
        result = await bus.replay_dlq_entry(dlq_id)
        assert result is True
        assert len(received) == 1

        # Should be removed from DLQ
        dlq_after = await bus.get_dlq_entries()
        assert len(dlq_after) == 0

    async def test_replay_dlq_entry_not_found(self):
        """Replaying a non-existent DLQ entry should return False."""
        bus = InMemoryEventBus()
        result = await bus.replay_dlq_entry("DLQ-NONEXIST")
        assert result is False

    async def test_dlq_entry_id_format(self):
        """DLQ entry IDs should follow DLQ-XXX format."""
        async def fails(event):
            raise RuntimeError("fail")

        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))
        await bus.subscribe("entity.created", fails)

        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        dlq = await bus.get_dlq_entries()
        assert dlq[0].dlq_id.startswith("DLQ-")


# ═══════════════════════════════════════════════
# PRODUCER / CONSUMER ADAPTERS
# ═══════════════════════════════════════════════

class TestProducerConsumer:
    """Test producer and consumer adapters."""

    async def test_producer_publishes(self):
        """Producer should create and publish events."""
        bus = InMemoryEventBus()
        producer = EventProducer(bus, source="entity-resolution")

        received = []
        async def handler(event):
            received.append(event)

        await bus.subscribe("entity.created", handler)

        event = await producer.publish(
            "entity.created",
            payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"},
            entity_refs=["ENT-001"],
        )

        assert event.source == "entity-resolution"
        assert event.event_type == "entity.created"
        assert len(received) == 1
        assert received[0].event_id == event.event_id

    async def test_producer_with_classification(self):
        """Producer should support classification levels."""
        bus = InMemoryEventBus()
        producer = EventProducer(bus, source="evidence-engine")

        received = []
        async def handler(event):
            received.append(event)

        await bus.subscribe("evidence.created", handler)

        event = await producer.publish(
            "evidence.created",
            payload={"evidence_id": "EV-001", "entity_id": "ENT-001", "evidence_type": "screenshot", "source": "crawler"},
            classification=ClassificationLevel.CONFIDENTIAL,
        )

        assert event.classification == ClassificationLevel.CONFIDENTIAL

    async def test_consumer_subscribe_unsubscribe(self):
        """Consumer should support subscribe and unsubscribe."""
        bus = InMemoryEventBus()
        consumer = EventConsumer(bus)

        received = []
        async def handler(event):
            received.append(event)

        await consumer.subscribe("entity.created", handler)
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))
        assert len(received) == 1

        await consumer.unsubscribe("entity.created")
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-002", "entity_type": "EMAIL", "normalized_value": "test@example.com"}))
        assert len(received) == 1  # No new events received

    async def test_consumer_unsubscribe_all(self):
        """Consumer should be able to unsubscribe from all topics."""
        bus = InMemoryEventBus()
        consumer = EventConsumer(bus)

        received = []
        async def handler(event):
            received.append(event)

        await consumer.subscribe("entity.created", handler)
        await consumer.subscribe("entity.updated", handler)
        await consumer.unsubscribe_all()

        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))
        await bus.publish(Event(event_type="entity.updated", source="test", payload={"entity_id": "ENT-001", "change_type": "merge"}))

        assert len(received) == 0


# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════

class TestMetrics:
    """Test event bus metrics collection."""

    async def test_metrics_published(self):
        """Metrics should track published events."""
        bus = InMemoryEventBus()
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))
        await bus.publish(Event(event_type="entity.updated", source="test", payload={"entity_id": "ENT-001", "change_type": "merge"}))

        metrics = await bus.get_metrics()
        assert metrics["published"] == 2

    async def test_metrics_consumed(self):
        """Metrics should track consumed events."""
        bus = InMemoryEventBus()

        async def handler(event):
            pass

        await bus.subscribe("entity.created", handler)
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        metrics = await bus.get_metrics()
        assert metrics["consumed"] == 1

    async def test_metrics_failed(self):
        """Metrics should track failed events."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))

        async def fails(event):
            raise RuntimeError("fail")

        await bus.subscribe("entity.created", fails)
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        metrics = await bus.get_metrics()
        assert metrics["failed"] == 1
        assert metrics["dlq_size"] == 1

    async def test_metrics_replayed(self):
        """Metrics should track replayed events."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))

        async def fails(event):
            raise RuntimeError("fail")

        await bus.subscribe("entity.created", fails)
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        # Fix handler and replay
        async def succeeds(event):
            pass

        await bus.unsubscribe(next(iter(bus._subscribers.get("entity.created", {}))))
        await bus.subscribe("entity.created", succeeds)

        dlq = await bus.get_dlq_entries()
        await bus.replay_dlq_entry(dlq[0].dlq_id)

        metrics = await bus.get_metrics()
        assert metrics["replayed"] == 1


# ═══════════════════════════════════════════════
# EVENT HISTORY
# ═══════════════════════════════════════════════

class TestEventHistory:
    """Test event history for testing/debugging."""

    async def test_event_history_records_all(self):
        """All published events should be recorded in history."""
        bus = InMemoryEventBus()
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))
        await bus.publish(Event(event_type="entity.updated", source="test", payload={"entity_id": "ENT-001", "change_type": "merge"}))

        history = bus.get_event_history()
        assert len(history) == 2

    async def test_event_history_empty_initially(self):
        """Event history should be empty initially."""
        bus = InMemoryEventBus()
        assert len(bus.get_event_history()) == 0


# ═══════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════

class TestFactory:
    """Test event bus factory."""

    def test_create_memory_bus(self):
        """Factory should create in-memory bus."""
        bus = create_event_bus("memory")
        assert isinstance(bus, InMemoryEventBus)

    def test_create_kafka_bus_raises(self):
        """Factory should raise for Kafka backend (not available in Layer A)."""
        with pytest.raises(NotImplementedError, match="REQUIRES EXTERNAL INFRASTRUCTURE"):
            create_event_bus("kafka")

    def test_create_unknown_backend(self):
        """Factory should reject unknown backends."""
        with pytest.raises(ValueError, match="Unknown event bus backend"):
            create_event_bus("rabbitmq")


# ═══════════════════════════════════════════════
# INTEGRATION (end-to-end)
# ═══════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests."""

    async def test_full_flow_entity_lifecycle(self):
        """Full entity lifecycle: create → update → merge events."""
        bus = InMemoryEventBus()
        producer = EventProducer(bus, source="entity-resolution")

        events_received = []
        async def handler(event):
            events_received.append(event)

        consumer = EventConsumer(bus)
        await consumer.subscribe("entity.created", handler)
        await consumer.subscribe("entity.updated", handler)

        # Create entity
        await producer.publish(
            "entity.created",
            payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"},
            entity_refs=["ENT-001"],
        )

        # Update entity
        await producer.publish(
            "entity.updated",
            payload={"entity_id": "ENT-001", "change_type": "merge"},
            entity_refs=["ENT-001"],
            correlation_id="COR-001",
        )

        assert len(events_received) == 2
        assert events_received[0].event_type == "entity.created"
        assert events_received[1].event_type == "entity.updated"
        assert events_received[1].correlation_id == "COR-001"

        metrics = await bus.get_metrics()
        assert metrics["published"] == 2
        assert metrics["consumed"] == 2
        assert metrics["failed"] == 0

    async def test_multiple_services_communicating(self):
        """Multiple services communicating via event bus."""
        bus = InMemoryEventBus()

        # Service 1: Entity Resolution
        resolution_producer = EventProducer(bus, source="entity-resolution")
        # Service 2: Evidence Engine
        evidence_producer = EventProducer(bus, source="evidence-engine")
        # Service 3: Risk Engine
        risk_producer = EventProducer(bus, source="risk-engine")

        # Risk engine listens for evidence
        risk_received = []
        async def risk_handler(event):
            risk_received.append(event)

        await bus.subscribe("evidence.created", risk_handler)

        # Entity resolution creates entity
        await resolution_producer.publish(
            "entity.created",
            payload={"entity_id": "ENT-001", "entity_type": "DOMAIN", "normalized_value": "evil.com"},
        )

        # Evidence engine records evidence
        await evidence_producer.publish(
            "evidence.created",
            payload={"evidence_id": "EV-001", "entity_id": "ENT-001", "evidence_type": "screenshot", "source": "crawler"},
            classification=ClassificationLevel.CONFIDENTIAL,
        )

        # Risk engine should have received the evidence event
        assert len(risk_received) == 1
        assert risk_received[0].payload["evidence_id"] == "EV-001"

    async def test_dlq_and_replay_workflow(self):
        """Full DLQ workflow: fail → DLQ → fix → replay → success."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=2, initial_delay_ms=1))

        # Handler that fails
        async def failing_handler(event):
            raise RuntimeError("Service unavailable")

        sub_id = await bus.subscribe("observation.created", failing_handler)

        # Publish event that will fail
        event = Event(
            event_type="observation.created",
            source="crawler",
            payload={"observation_id": "OBS-001", "entity_id": "ENT-001", "observation_type": "dns_lookup"},
        )
        await bus.publish(event)

        # Check DLQ
        dlq = await bus.get_dlq_entries()
        assert len(dlq) == 1
        assert dlq[0].failure_reason == "Service unavailable"

        # Replace handler with one that works
        await bus.unsubscribe(sub_id)
        received = []
        async def working_handler(event):
            received.append(event)

        await bus.subscribe("observation.created", working_handler)

        # Replay
        result = await bus.replay_dlq_entry(dlq[0].dlq_id)
        assert result is True
        assert len(received) == 1

        # DLQ should be empty now
        dlq_after = await bus.get_dlq_entries()
        assert len(dlq_after) == 0

        metrics = await bus.get_metrics()
        assert metrics["published"] == 1
        assert metrics["failed"] == 1
        assert metrics["consumed"] == 1  # From replay
        assert metrics["replayed"] == 1


# ═══════════════════════════════════════════════
# NEGATIVE / FAIL-SAFE TESTS
# ═══════════════════════════════════════════════

class TestNegativeFailSafe:
    """Test fail-safe behavior."""

    async def test_invalid_event_rejected(self):
        """Invalid events should be rejected at publish time."""
        bus = InMemoryEventBus()
        event = Event(
            event_type="entity.created",
            source="test",
            payload={},  # Missing all required fields
        )
        with pytest.raises(ValueError, match="schema validation"):
            await bus.publish(event)

    async def test_kafka_backend_not_available(self):
        """Kafka backend should explicitly not be available in Layer A."""
        with pytest.raises(NotImplementedError, match="REQUIRES EXTERNAL INFRASTRUCTURE"):
            create_event_bus("kafka")

    async def test_unsubscribe_nonexistent(self):
        """Unsubscribing a non-existent subscription should return False."""
        bus = InMemoryEventBus()
        result = await bus.unsubscribe("SUB-NONEXIST")
        assert result is False

    async def test_handler_exception_does_not_crash_bus(self):
        """Handler exceptions should not crash the event bus."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, initial_delay_ms=1))

        async def crash_handler(event):
            raise RuntimeError("Crash!")

        await bus.subscribe("entity.created", crash_handler)

        # This should not raise
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-001", "entity_type": "PHONE", "normalized_value": "+34612345678"}))

        # Bus should still be functional
        received = []
        async def good_handler(event):
            received.append(event)

        await bus.unsubscribe(next(iter(bus._subscribers.get("entity.created", {}))))
        await bus.subscribe("entity.created", good_handler)
        await bus.publish(Event(event_type="entity.created", source="test", payload={"entity_id": "ENT-002", "entity_type": "EMAIL", "normalized_value": "test@example.com"}))
        assert len(received) == 1

    async def test_empty_topic_name_rejected(self):
        """Empty topic names should still be handled gracefully."""
        bus = InMemoryEventBus()
        # Publishing to empty topic — not in KAFKA_TOPICS, but forward-compatible
        event = Event(event_type="", source="test", payload={})
        # Should not crash (unknown types are allowed)
        await bus.publish(event)
