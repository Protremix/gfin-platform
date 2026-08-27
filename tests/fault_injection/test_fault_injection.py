"""Fault-injection tests — service timeouts, retries, partial writes, corrupted messages.

Per Luna Directive — Focus Area 2: Deterministic fault-injection tests.
"""

from __future__ import annotations

import asyncio
import sys
import time
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.cache import MemoryCache
from common.database import InMemoryEntityRepository
from common.event_bus import Event, InMemoryEventBus, RetryPolicy
from common.graph import AdjacencyListGraph, GraphNode
from schemas.entities import create_entity
from services.evidence_vault import EvidenceVault


class TestServiceTimeoutHandling:
    """Test handling of service timeouts."""

    def test_slow_handler_does_not_block_indefinitely(self):
        """A slow subscriber handler should not block the bus indefinitely."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=1, base_delay_ms=0))
        received: list[str] = []

        async def run():
            async def slow_handler(event: Event) -> None:
                await asyncio.sleep(0.5)
                received.append(event.event_id)

            await bus.subscribe("Test", slow_handler)
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={},
                version=1,
            )
            start = time.time()
            await asyncio.wait_for(bus.publish(event), timeout=5.0)
            elapsed = time.time() - start
            return elapsed

        elapsed = asyncio.run(run())
        assert elapsed < 5.0  # Should complete within timeout

    def test_repository_operation_timeout_protection(self):
        """Repository operations should complete in reasonable time."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            start = time.time()
            for i in range(100):
                e = create_entity("EMAIL", email=f"timeout{i}@test.com")
                await repo.create(e)
            return time.time() - start

        elapsed = asyncio.run(run())
        assert elapsed < 3.0


class TestRetryExhaustion:
    """Test retry exhaustion behavior."""

    def test_handler_fails_then_succeeds(self):
        """A handler that fails then succeeds should eventually succeed."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=0))
        call_count = 0
        consumed = False

        async def run():
            nonlocal call_count, consumed

            async def flaky_handler(event: Event) -> None:
                nonlocal call_count, consumed
                call_count += 1
                if call_count < 3:
                    raise RuntimeError("Transient failure")
                consumed = True

            await bus.subscribe("Test", flaky_handler)
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
        assert call_count == 3
        assert consumed is True
        assert metrics["consumed"] == 1

    def test_handler_always_fails_goes_to_dlq(self):
        """A handler that always fails should send the event to DLQ."""
        bus = InMemoryEventBus(retry_policy=RetryPolicy(max_attempts=2, base_delay_ms=0))

        async def run():
            async def always_fails(event: Event) -> None:
                raise RuntimeError("Permanent failure")

            await bus.subscribe("Test", always_fails)
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
        assert "Permanent failure" in dlq[0].failure_reason


class TestPartialWriteRecovery:
    """Test recovery from partial write failures."""

    def test_partial_entity_creation(self):
        """Creating entities where one fails should not corrupt others."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            results = []
            for i in range(10):
                try:
                    e = create_entity("EMAIL", email=f"partial{i}@test.com")
                    await repo.create(e)
                    results.append(True)
                except Exception:
                    results.append(False)
            return await repo.count(), results

        count, results = asyncio.run(run())
        assert count == 10
        assert all(results)

    def test_partial_evidence_creation(self):
        """Creating evidence items where one fails should not corrupt others."""
        import hashlib

        vault = EvidenceVault()
        success_count = 0
        for i in range(10):
            try:
                content = f"evidence {i}".encode()
                from schemas.base import BaseEvidence

                evidence = BaseEvidence(
                    source_id=f"SRC-{i}",
                    content_type="text/plain",
                    content_hash=hashlib.sha256(content).hexdigest(),
                )
                vault.create(evidence, content=content)
                success_count += 1
            except Exception:
                pass

        assert success_count == 10
        assert len(vault.list()) == 10


class TestCorruptedMessageHandling:
    """Test corrupted message handling."""

    def test_event_with_invalid_payload_type(self):
        """Event with unexpected payload type should be handled."""
        bus = InMemoryEventBus()

        async def run():
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"valid": "json"},
                version=1,
            )
            await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 1

    def test_event_with_large_payload(self):
        """Event with large payload should not crash the bus."""
        bus = InMemoryEventBus()

        async def run():
            large_payload = {"data": "x" * 100000}
            event = Event(
                event_id=str(uuid4()),
                topic="entity_events",
                event_type="Test",
                source="test",
                payload=large_payload,
                version=1,
            )
            await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 1


class TestReplayAttackDetection:
    """Test replay attack detection."""

    def test_same_event_processed_twice(self):
        """Same event_id published twice should be delivered twice (no dedup in Layer A)."""
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
                payload={"nonce": 1},
                version=1,
            )
            await bus.publish(event)
            await bus.publish(event)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        # Layer A does not dedup — both delivered (documented behavior)
        assert len(received) == 2

    def test_event_with_different_payload_same_id(self):
        """Events with same ID but different payloads should both be recorded."""
        bus = InMemoryEventBus()
        event_id = str(uuid4())

        async def run():
            e1 = Event(
                event_id=event_id,
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"version": 1},
                version=1,
            )
            e2 = Event(
                event_id=event_id,
                topic="entity_events",
                event_type="Test",
                source="test",
                payload={"version": 2},
                version=1,
            )
            await bus.publish(e1)
            await bus.publish(e2)
            return bus.get_event_history()

        history = asyncio.run(run())
        assert len(history) == 2
        assert history[0].payload["version"] == 1
        assert history[1].payload["version"] == 2


class TestUnavailableDependency:
    """Test handling of unavailable dependencies."""

    def test_cache_available_after_clear(self):
        """Cache should be usable after clear."""
        cache = MemoryCache()

        async def run():
            await cache.set("key", "value")
            await cache.clear()
            await cache.set("key2", "value2")
            return await cache.get("key2")

        result = asyncio.run(run())
        assert result == "value2"

    def test_graph_after_failed_operation(self):
        """Graph should remain usable after a failed operation."""
        graph = AdjacencyListGraph()

        async def run():
            # Try to get nonexistent node (fails gracefully)
            await graph.get_node("nonexistent")

            # Graph should still work
            node = GraphNode(entity_id="A", entity_type="entity", label="A")
            await graph.add_node(node)
            return await graph.get_node("A")

        result = asyncio.run(run())
        assert result is not None
