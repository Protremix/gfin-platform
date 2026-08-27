"""Idempotency and deduplication tests.

Per Luna Directive — Focus Area 2: Verify idempotency, deduplication,
dead-letter handling, backpressure, and recovery semantics.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.cache import MemoryCache
from common.database import InMemoryEntityRepository
from common.event_bus import Event, InMemoryEventBus, RetryPolicy
from schemas.entities import create_entity


class TestEventBusIdempotency:
    """Test event bus idempotent publishing."""

    def test_same_event_id_published_twice_both_recorded(self):
        """Publishing same event_id twice should record both in history."""
        bus = InMemoryEventBus()
        event_id = str(uuid4())

        async def run():
            event = Event(
                event_id=event_id,
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"id": "DUP"},
                version=1,
            )
            await bus.publish(event)
            await bus.publish(event)
            return bus.get_event_history()

        history = asyncio.run(run())
        assert len(history) == 2

    def test_subscriber_receives_both_duplicates(self):
        """Subscriber should receive duplicate events."""
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


class TestEntityDedup:
    """Test entity deduplication."""

    def test_same_normalized_value_different_ids(self):
        """Entities with same normalized_value should both be stored (Layer A: no dedup)."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e1 = create_entity("EMAIL", email="same@test.com")
            await repo.create(e1)
            e2 = create_entity("EMAIL", email="same@test.com")
            await repo.create(e2)
            return await repo.count()

        count = asyncio.run(run())
        assert count == 2  # Both stored, no dedup in Layer A

    def test_find_by_normalized_value(self):
        """Finding by normalized_value should return matching entity."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e = create_entity("EMAIL", email="findme@test.com")
            await repo.create(e)
            return await repo.find_by_normalized_value("EMAIL", "findme@test.com")

        result = asyncio.run(run())
        assert result is not None


class TestCacheDedup:
    """Test cache set overwrite (dedup)."""

    def test_cache_set_same_key_twice_overwrites(self):
        """Setting the same key twice should overwrite the value."""
        cache = MemoryCache()

        async def run():
            await cache.set("key", "value1")
            await cache.set("key", "value2")
            return await cache.get("key")

        result = asyncio.run(run())
        assert result == "value2"

    def test_cache_exists_after_overwrite(self):
        """Key should exist after overwrite."""
        cache = MemoryCache()

        async def run():
            await cache.set("key", "v1")
            await cache.set("key", "v2")
            return await cache.exists("key")

        result = asyncio.run(run())
        assert result is True


class TestDLQReplay:
    """Test DLQ replay after fix."""

    def test_dlq_entry_exists_after_failure(self):
        """Failed event should appear in DLQ."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, base_delay_ms=0))

        async def run():
            async def failing_handler(event: Event) -> None:
                raise RuntimeError("Failure")

            await bus.subscribe("Test", failing_handler)
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)
            return await bus.get_dlq_entries()

        dlq = asyncio.run(run())
        assert len(dlq) == 1

    def test_dlq_replay_with_fixed_handler(self):
        """Replaying DLQ entry with a fixed handler should succeed."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, base_delay_ms=0))
        handler_should_fail = True
        consumed_after_replay = False

        async def run():
            nonlocal handler_should_fail, consumed_after_replay

            async def handler(event: Event) -> None:
                nonlocal consumed_after_replay
                if handler_should_fail:
                    raise RuntimeError("Failure")
                consumed_after_replay = True

            await bus.subscribe("Test", handler)
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            await bus.publish(event)

            dlq = await bus.get_dlq_entries()
            assert len(dlq) == 1

            # Fix the handler
            handler_should_fail = False

            # Replay
            replayed = await bus.replay_dlq_entry(dlq[0].dlq_id)
            return replayed, consumed_after_replay

        replayed, consumed = asyncio.run(run())
        assert replayed is True
        assert consumed is True


class TestBackpressure:
    """Test backpressure simulation."""

    def test_1000_events_rapid_publish_no_crash(self):
        """Publishing 1000 events rapidly should not crash."""
        bus = InMemoryEventBus()

        async def run():
            for i in range(1000):
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="Test",
                    source="test",
                    payload={"seq": i},
                    version=1,
                )
                await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 1000

    def test_rapid_publish_to_slow_handler(self):
        """Rapid publishing to a slow handler should not lose events."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, base_delay_ms=0))
        received: list[str] = []

        async def run():
            async def slow_handler(event: Event) -> None:
                await asyncio.sleep(0.001)  # 1ms delay
                received.append(event.event_id)

            await bus.subscribe("Test", slow_handler)
            for i in range(100):
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="Test",
                    source="test",
                    payload={"seq": i},
                    version=1,
                )
                await bus.publish(event)
            return len(received)

        count = asyncio.run(run())
        # Each publish dispatches and waits for handler, so all should be received
        assert count == 100

    def test_rapid_entity_creation_backpressure(self):
        """Rapid entity creation should handle backpressure."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(5000):
                e = create_entity("EMAIL", email=f"bp{i}@test.com")
                await repo.create(e)
            return await repo.count()

        count = asyncio.run(run())
        assert count == 5000
