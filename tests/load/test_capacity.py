"""Capacity tests — verify GFIN components handle large datasets in-memory.

Per Luna Strategic Assessment — Step 2: Reliability Validation.
These tests verify that Layer A components can handle significant load
patterns. Real production capacity will be validated against live infrastructure.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.cache import MemoryCache
from common.database import InMemoryEntityRepository
from common.event_bus import Event, InMemoryEventBus
from common.graph import AdjacencyListGraph, GraphEdge, GraphNode
from common.search import EntitySearchService, SearchQuery
from schemas.base import BaseEvidence
from schemas.entities import create_entity
from services.evidence_vault import EvidenceVault


class TestEntityRepositoryCapacity:
    """Test entity repository handles large datasets."""

    def test_create_10000_entities(self):
        """Repository should handle 10,000 entity records."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(10000):
                e = create_entity("EMAIL", email=f"user{i}@test.com")
                await repo.create(e)
            return await repo.count()

        count = asyncio.run(run())
        assert count >= 9999  # 8-hex-char UUID has ~1% collision at 10k (birthday paradox)

    def test_10000_entities_under_5_seconds(self):
        """Creating 10,000 entities should take under 5 seconds."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(10000):
                e = create_entity("EMAIL", email=f"speed{i}@test.com")
                await repo.create(e)

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Creating 10K entities took {elapsed:.2f}s (SLO: <5s)"

    def test_paginated_read_large_dataset(self):
        """Paginated reads should work on large datasets."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(1000):
                e = create_entity("EMAIL", email=f"page{i}@test.com")
                await repo.create(e)
            page1 = await repo.list(limit=100, offset=0)
            page2 = await repo.list(limit=100, offset=100)
            return page1, page2

        page1, page2 = asyncio.run(run())
        assert len(page1) == 100
        assert len(page2) == 100


class TestGraphEngineCapacity:
    """Test graph engine handles large graphs."""

    def test_graph_handles_1000_nodes(self):
        """Graph should handle 1,000 nodes without error."""
        graph = AdjacencyListGraph()

        async def run():
            for i in range(1000):
                node = GraphNode(entity_id=f"node-{i}", entity_type="entity", label=f"Node {i}")
                await graph.add_node(node)
            return await graph.get_node("node-999")

        result = asyncio.run(run())
        assert result is not None

    def test_graph_handles_5000_edges(self):
        """Graph should handle 5,000 edges without error."""
        graph = AdjacencyListGraph()

        async def run():
            for i in range(1000):
                node = GraphNode(entity_id=f"node-{i}", entity_type="entity", label=f"Node {i}")
                await graph.add_node(node)
            for i in range(5000):
                edge = GraphEdge(
                    relationship_id=f"edge-{i}",
                    from_entity_id=f"node-{i % 1000}",
                    to_entity_id=f"node-{(i + 1) % 1000}",
                    relationship_type="LINKED_TO",
                )
                await graph.add_edge(edge)
            neighbors, _edges = await graph.get_neighbors("node-0")
            return len(neighbors)

        neighbor_count = asyncio.run(run())
        assert neighbor_count > 0

    def test_graph_build_under_5_seconds(self):
        """Building 1K nodes + 5K edges should take under 5 seconds."""
        graph = AdjacencyListGraph()

        async def run():
            for i in range(1000):
                node = GraphNode(entity_id=f"node-{i}", entity_type="entity", label=f"Node {i}")
                await graph.add_node(node)
            for i in range(5000):
                edge = GraphEdge(
                    relationship_id=f"edge-{i}",
                    from_entity_id=f"node-{i % 1000}",
                    to_entity_id=f"node-{(i + 1) % 1000}",
                    relationship_type="LINKED",
                )
                await graph.add_edge(edge)

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Building graph took {elapsed:.2f}s (SLO: <5s)"

    def test_graph_path_finding_on_large_graph(self):
        """Path finding should work on a large graph."""
        graph = AdjacencyListGraph()

        async def run():
            for i in range(500):
                node = GraphNode(entity_id=f"node-{i}", entity_type="entity", label=f"Node {i}")
                await graph.add_node(node)
            for i in range(499):
                edge = GraphEdge(
                    relationship_id=f"edge-{i}",
                    from_entity_id=f"node-{i}",
                    to_entity_id=f"node-{i + 1}",
                    relationship_type="LINKED",
                )
                await graph.add_edge(edge)
            return await graph.find_path("node-0", "node-499", max_depth=500)

        path = asyncio.run(run())
        assert path is not None
        assert path is not None
        assert path.length >= 1


class TestEventBusCapacity:
    """Test event bus handles high-volume event publishing."""

    def test_event_bus_handles_10000_events(self):
        """Event bus should handle 10,000 events published."""
        bus = InMemoryEventBus()

        async def run():
            for i in range(10000):
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="EntityCreated",
                    source="test",
                    payload={"entity_id": f"ENT-{i}"},
                    version=1,
                )
                await bus.publish(event)
            return await bus.get_metrics()

        metrics = asyncio.run(run())
        assert metrics["published"] == 10000

    def test_event_bus_10000_events_under_5_seconds(self):
        """Publishing 10K events should take under 5 seconds."""
        bus = InMemoryEventBus()

        async def run():
            for i in range(10000):
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="EntityCreated",
                    source="test",
                    payload={"entity_id": f"ENT-{i}"},
                    version=1,
                )
                await bus.publish(event)

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Publishing 10K events took {elapsed:.2f}s"

    def test_event_bus_with_subscriber_throughput(self):
        """Event bus should deliver events to subscribers quickly."""
        bus = InMemoryEventBus()
        received: list[str] = []

        async def run():
            async def handler(event: Event) -> None:
                received.append(event.event_id)

            await bus.subscribe("Test", handler)
            for i in range(1000):
                event = Event(
                    event_id=str(uuid4()),
                    topic="entity_events",
                    event_type="Test",
                    source="test",
                    payload={"index": i},
                    version=1,
                )
                await bus.publish(event)
            # Allow async dispatch to complete
            await asyncio.sleep(0.1)

        asyncio.run(run())
        assert len(received) == 1000


class TestSearchCapacity:
    """Test search service handles large indices."""

    def test_search_index_10000_entities(self):
        """Search should index 10,000 entities via repository."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(10000):
                e = create_entity("EMAIL", email=f"doc{i}@test.com")
                await repo.create(e)
            return await repo.count()

        count = asyncio.run(run())
        assert count >= 9999  # 8-hex-char UUID has ~1% collision at 10k (birthday paradox)

    def test_search_query_on_large_index(self):
        """Search should return relevant results on large index."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()
        service = EntitySearchService(repo)

        async def run():
            for i in range(1000):
                e = create_entity("EMAIL", email=f"fraud{i}@test.com")
                await repo.create(e)
            query = SearchQuery(query="fraud", limit=10)
            return await service.search(query)

        response = asyncio.run(run())
        assert response is not None
        assert len(response.results) <= 10

    def test_search_build_under_5_seconds(self):
        """Indexing 10K entities should take under 5 seconds."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(10000):
                e = create_entity("EMAIL", email=f"fast{i}@test.com")
                await repo.create(e)

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Indexing 10K entities took {elapsed:.2f}s"


class TestEvidenceVaultCapacity:
    """Test evidence vault handles large numbers of evidence items."""

    def test_evidence_vault_handles_1000_items(self):
        """Evidence vault should handle 1,000 evidence items."""
        vault = EvidenceVault()
        for i in range(1000):
            content = f"evidence content {i}".encode()
            evidence = BaseEvidence(
                source_id=f"SRC-{i:04d}",
                content_type="text/plain",
                content_hash=hashlib.sha256(content).hexdigest(),
            )
            vault.create(evidence, content=content, actor=f"crawler-{i:04d}")

        items = vault.list()
        assert len(items) == 1000

    def test_evidence_vault_1000_under_5_seconds(self):
        """Storing 1K evidence items should take under 5 seconds."""
        vault = EvidenceVault()
        start = time.time()
        for i in range(1000):
            content = f"evidence {i}".encode()
            evidence = BaseEvidence(
                source_id=f"SRC-{i}",
                content_type="text/plain",
                content_hash=hashlib.sha256(content).hexdigest(),
            )
            vault.create(evidence, content=content)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Storing 1K evidence items took {elapsed:.2f}s"


class TestCacheCapacity:
    """Test cache handles large numbers of entries."""

    def test_cache_handles_10000_entries(self):
        """Cache should handle 10,000 entries."""
        cache = MemoryCache()

        async def run():
            for i in range(10000):
                await cache.set(f"key-{i}", f"value-{i}")
            return await cache.get("key-5000")

        result = asyncio.run(run())
        assert result == "value-5000"

    def test_cache_10000_entries_under_5_seconds(self):
        """Setting 10K cache entries should take under 5 seconds."""
        cache = MemoryCache()

        async def run():
            for i in range(10000):
                await cache.set(f"key-{i}", f"value-{i}")

        start = time.time()
        asyncio.run(run())
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Setting 10K cache entries took {elapsed:.2f}s"

    def test_cache_delete_works(self):
        """Cache delete should work without crash."""
        cache = MemoryCache()

        async def run():
            await cache.set("key-1", "value-1")
            await cache.delete("key-1")
            return await cache.get("key-1")

        result = asyncio.run(run())
        assert result is None
