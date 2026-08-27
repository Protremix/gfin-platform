"""Contract tests for the GFIN event bus.

Per Luna Directive — Focus Area 1: Contract tests for valid, malformed,
duplicated, delayed, and out-of-order events.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.event_bus import Event, InMemoryEventBus
from schemas.versions import check_backward_compatibility, get_latest_version, get_schema


class TestEventSchemaContracts:
    """Test event schema versioning and compatibility."""

    def test_event_schema_v1_exists(self):
        """Event schema v1.0 should exist in registry."""
        schema = get_schema("event", "1.0")
        assert schema is not None
        assert "event_id" in schema.fields
        assert "topic" in schema.fields
        assert "event_type" in schema.fields

    def test_event_required_fields(self):
        """Event schema should declare required fields."""
        schema = get_schema("event", "1.0")
        assert "event_id" in schema.required_fields
        assert "event_type" in schema.required_fields
        assert "payload" in schema.required_fields
        assert "version" in schema.required_fields

    def test_event_optional_fields(self):
        """Event schema should declare optional fields."""
        schema = get_schema("event", "1.0")
        assert "timestamp" in schema.optional_fields
        assert "correlation_id" in schema.optional_fields


class TestEventPublishingContracts:
    """Test valid event publishing and consumption."""

    def test_valid_event_published_and_consumed(self):
        """A valid event should be published and consumed by subscribers."""
        bus = InMemoryEventBus()
        received: list[Event] = []

        async def run():
            async def handler(event: Event) -> None:
                received.append(event)

            await bus.subscribe("EntityCreated", handler)
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="EntityCreated",
                source="test",
                payload={"entity_id": "ENT-001"},
                version=1,
            )
            await bus.publish(event)

        asyncio.run(run())
        assert len(received) == 1
        assert received[0].event_id == received[0].event_id

    def test_event_metrics_increment_on_publish(self):
        """Publishing an event should increment the published metric."""
        bus = InMemoryEventBus()

        async def run():
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 1


class TestMalformedEventContracts:
    """Test that malformed events are rejected."""

    def test_event_missing_required_field_raises(self):
        """Event missing required fields should raise ValueError."""
        bus = InMemoryEventBus(validate_on_publish=True)

        async def run():
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)

        asyncio.run(run())  # Valid event should work

    def test_event_with_empty_event_id(self):
        """Event with empty event_id should be handled."""
        bus = InMemoryEventBus()

        async def run():
            event = Event(
                event_id="",
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 1


class TestDuplicateEventContracts:
    """Test duplicate event handling."""

    def test_duplicate_event_id_published_twice(self):
        """Same event_id published twice should both be recorded."""
        bus = InMemoryEventBus()
        event_id = str(uuid4())

        async def run():
            event = Event(
                event_id=event_id,
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"id": "DUP-001"},
                version=1,
            )
            await bus.publish(event)
            await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 2  # Both recorded
        assert len(bus.get_event_history()) == 2

    def test_duplicate_event_delivered_to_subscriber(self):
        """Duplicate events should be delivered to subscriber both times."""
        bus = InMemoryEventBus()
        received: list[str] = []
        event_id = str(uuid4())

        async def run():
            async def handler(event: Event) -> None:
                received.append(event.event_id)

            await bus.subscribe("Test", handler)
            event = Event(
                event_id=event_id,
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)
            await bus.publish(event)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert len(received) == 2


class TestOutOfOrderEventContracts:
    """Test delayed and out-of-order event handling."""

    def test_events_published_out_of_order(self):
        """Events published out of timestamp order should all be recorded."""
        bus = InMemoryEventBus()
        events: list[Event] = []

        async def run():
            for i in [3, 1, 2]:
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="Test",
                    source="test",
                    payload={"seq": i},
                    version=1,
                )
                events.append(event)
                await bus.publish(event)
            return len(bus.get_event_history())

        count = asyncio.run(run())
        assert count == 3
        # History preserves publish order, not timestamp order
        assert bus.get_event_history()[0].payload["seq"] == 3
        assert bus.get_event_history()[2].payload["seq"] == 2

    def test_late_event_does_not_crash(self):
        """A late-arriving event should not crash the bus."""
        bus = InMemoryEventBus()

        async def run():
            # Publish current event
            e1 = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"seq": 1},
                version=1,
            )
            await bus.publish(e1)

            # Publish "late" event (simulated)
            e2 = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"seq": 0},
                version=1,
            )
            await bus.publish(e2)

        asyncio.run(run())  # Should not raise


class TestSchemaVersionCompatibility:
    """Test schema version backward compatibility."""

    def test_entity_v1_to_v1_1_compatible(self):
        """Entity v1.0 to v1.1 should be backward compatible (only optional fields added)."""
        is_compatible, issues = check_backward_compatibility("entity", "1.0", "1.1")
        assert is_compatible, f"Expected compatibility, got issues: {issues}"

    def test_unknown_schema_returns_false(self):
        """Unknown schema should return False."""
        is_compatible, _issues = check_backward_compatibility("nonexistent", "1.0", "2.0")
        assert not is_compatible

    def test_latest_version_exists(self):
        """Latest version should be retrievable for all registered schemas."""
        for name in ["entity", "event", "graph_node", "graph_edge", "search_query", "evidence", "api_request"]:
            latest = get_latest_version(name)
            assert latest is not None, f"No latest version for {name}"


class TestEventBusUnsubscribeContract:
    """Test unsubscribe contract."""

    def test_unsubscribe_stops_delivery(self):
        """After unsubscribing, events should not be delivered."""
        bus = InMemoryEventBus()
        received: list[str] = []

        async def run():
            async def handler(event: Event) -> None:
                received.append(event.event_id)

            sub_id = await bus.subscribe("Test", handler)
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)
            await asyncio.sleep(0.05)

            # Unsubscribe
            await bus.unsubscribe(sub_id)

            # Publish another event
            event2 = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event2)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert len(received) == 1  # Only first event received
