"""Regression benchmark tests for GFIN Layer A operations.

Per Luna Directive — Module 39: Scaling & Optimization.
Records p50/p95/p99 latency and asserts against performance budgets.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from auth.audit import AuditEventType, AuditLog
from common.cache import MemoryCache
from common.database import InMemoryEntityRepository
from common.event_bus import Event, InMemoryEventBus
from common.graph import AdjacencyListGraph, GraphEdge, GraphNode
from common.search import EntitySearchService, SearchQuery
from schemas.base import BaseEvidence
from schemas.entities import create_entity
from services.evidence_vault import EvidenceVault


# ---------------------------------------------------------------------------
# Entity operations
# ---------------------------------------------------------------------------
class TestEntityBenchmarks:
    """Entity CRUD + resolution timing."""

    def test_entity_create_benchmark(self):
        """Entity create: p50 < 10ms."""
        repo = InMemoryEntityRepository()

        async def run():
            timings = []
            for i in range(1000):
                start = time.perf_counter()
                await repo.create(create_entity("EMAIL", email=f"bench{i}@test.com"))
                timings.append((time.perf_counter() - start) * 1000)
            return timings

        timings = asyncio.run(run())
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        p50 = timings[len(timings) // 2]
        assert p99 < 50, f"Entity create p99={p99:.2f}ms exceeds 50ms budget"
        assert p50 < 10, f"Entity create p50={p50:.2f}ms exceeds 10ms"

    def test_entity_read_benchmark(self):
        """Entity read: p99 < 20ms."""
        repo = InMemoryEntityRepository()

        async def run():
            ids = []
            for i in range(1000):
                e = await repo.create(create_entity("PHONE", phone=f"+15550{i:06d}"))
                ids.append(e.id)
            timings = []
            for eid in ids:
                start = time.perf_counter()
                await repo.get(eid)
                timings.append((time.perf_counter() - start) * 1000)
            return timings

        timings = asyncio.run(run())
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 20, f"Entity read p99={p99:.2f}ms exceeds 20ms budget"

    def test_entity_bulk_create_capacity(self):
        """Bulk create 10,000 entities in < 5s."""
        repo = InMemoryEntityRepository()

        async def run():
            start = time.perf_counter()
            for i in range(10_000):
                await repo.create(create_entity("EMAIL", email=f"bulk{i}@bench.com"))
            return time.perf_counter() - start

        elapsed = asyncio.run(run())
        assert elapsed < 5.0, f"Bulk create 10k took {elapsed:.2f}s, budget 5s"


# ---------------------------------------------------------------------------
# Graph operations
# ---------------------------------------------------------------------------
class TestGraphBenchmarks:
    """Graph query timing at scale."""

    def test_graph_one_hop_benchmark(self):
        """1-hop query: p99 < 100ms at 1000 nodes."""
        graph = AdjacencyListGraph()

        async def setup():
            for i in range(1000):
                await graph.add_node(GraphNode(entity_id=f"node-{i}", entity_type="EMAIL", label=f"node-{i}", properties={}))
            for i in range(999):
                await graph.add_edge(GraphEdge(
                    relationship_id=f"e-{i}", from_entity_id=f"node-{i}",
                    to_entity_id=f"node-{i+1}", relationship_type="LINKED_TO",
                    confidence="1.0", source_id="bench", timestamp=None, properties={},
                ))

        asyncio.run(setup())

        async def run():
            timings = []
            for i in range(500):
                start = time.perf_counter()
                await graph.get_neighbors(f"node-{i}")
                timings.append((time.perf_counter() - start) * 1000)
            return timings

        timings = asyncio.run(run())
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 100, f"1-hop p99={p99:.2f}ms exceeds 100ms budget"

    def test_graph_large_capacity(self):
        """Graph with 5000 nodes + 25000 edges, query < 500ms."""
        graph = AdjacencyListGraph()

        async def setup():
            for i in range(5000):
                await graph.add_node(GraphNode(entity_id=f"n-{i}", entity_type="DOMAIN", label=f"n-{i}", properties={}))
            for i in range(5000):
                for j in range(5):
                    target = (i + j + 1) % 5000
                    await graph.add_edge(GraphEdge(
                        relationship_id=f"e-{i}-{j}", from_entity_id=f"n-{i}",
                        to_entity_id=f"n-{target}", relationship_type="RESOLVES_TO",
                        confidence="1.0", source_id="bench", timestamp=None, properties={},
                    ))

        asyncio.run(setup())

        async def run():
            start = time.perf_counter()
            result = await graph.get_neighbors("n-0")
            return (time.perf_counter() - start) * 1000, result

        elapsed, result = asyncio.run(run())
        assert elapsed < 500, f"Large graph query took {elapsed:.2f}ms, budget 500ms"
        assert len(result[0]) >= 1


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------
class TestEventBusBenchmarks:
    """Event bus throughput + latency."""

    def test_event_publish_benchmark(self):
        """Event publish: p99 < 20ms."""
        bus = InMemoryEventBus()
        timings = []
        for i in range(10_000):
            event = Event(topic="entity_events", event_type="ENTITY_CREATED", source="bench", payload={"id": i})
            start = time.perf_counter()
            bus.publish(event)
            timings.append((time.perf_counter() - start) * 1000)
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 20, f"Event publish p99={p99:.2f}ms exceeds 20ms budget"

    def test_event_bus_throughput_capacity(self):
        """100,000 events in < 30s."""
        bus = InMemoryEventBus()
        start = time.perf_counter()
        for i in range(100_000):
            event = Event(topic="entity_events", event_type="ENTITY_CREATED", source="bench-cap", payload={"id": i})
            bus.publish(event)
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0, f"100k events took {elapsed:.2f}s, budget 30s"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class TestCacheBenchmarks:
    """Cache hit/miss/eviction timing."""

    def test_cache_get_benchmark(self):
        """Cache get: p99 < 5ms."""
        cache = MemoryCache()
        for i in range(10_000):
            cache.set(f"key-{i}", f"value-{i}")
        timings = []
        for i in range(10_000):
            start = time.perf_counter()
            cache.get(f"key-{i}")
            timings.append((time.perf_counter() - start) * 1000)
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 5, f"Cache get p99={p99:.2f}ms exceeds 5ms budget"


# ---------------------------------------------------------------------------
# Evidence vault
# ---------------------------------------------------------------------------
class TestEvidenceBenchmarks:
    """Evidence vault operations timing."""

    def test_evidence_create_benchmark(self):
        """Evidence create: p99 < 100ms."""
        vault = EvidenceVault()
        timings = []
        for i in range(1000):
            content = f"evidence-content-{i}".encode()
            evidence = BaseEvidence(
                source_id="bench",
                content_type="text/plain",
                content_hash=hashlib.sha256(content).hexdigest(),
            )
            start = time.perf_counter()
            vault.create(evidence, content=content)
            timings.append((time.perf_counter() - start) * 1000)
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 100, f"Evidence create p99={p99:.2f}ms exceeds 100ms budget"

    def test_evidence_bulk_capacity(self):
        """5,000 evidence items in < 10s."""
        vault = EvidenceVault()
        start = time.perf_counter()
        for i in range(5000):
            content = f"bulk-evidence-{i}".encode()
            evidence = BaseEvidence(
                source_id="bulk-bench",
                content_type="text/plain",
                content_hash=hashlib.sha256(content).hexdigest(),
            )
            vault.create(evidence, content=content)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Bulk evidence 5k took {elapsed:.2f}s, budget 10s"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
class TestSearchBenchmarks:
    """Search query performance."""

    def test_search_benchmark(self):
        """Search query: p99 < 500ms at 10k docs."""
        repo = InMemoryEntityRepository()

        async def setup():
            for i in range(10_000):
                await repo.create(create_entity("EMAIL", email=f"search{i}@test.com"))

        asyncio.run(setup())
        service = EntitySearchService(repo)

        async def run_search():
            timings = []
            for i in range(500):
                q = SearchQuery(query=f"search{i}@test.com", limit=10)
                start = time.perf_counter()
                await service.search(q)
                timings.append((time.perf_counter() - start) * 1000)
            return timings

        timings = asyncio.run(run_search())
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 500, f"Search p99={p99:.2f}ms exceeds 500ms budget (Layer A)"

    def test_search_bulk_index_capacity(self):
        """Index 10,000 documents, search < 1s."""
        repo = InMemoryEntityRepository()

        async def setup():
            for i in range(10_000):
                await repo.create(create_entity("DOMAIN", domain=f"domain{i}.com"))

        asyncio.run(setup())
        service = EntitySearchService(repo)

        async def run():
            start = time.perf_counter()
            await service.search(SearchQuery(query="domain", limit=100))
            return (time.perf_counter() - start) * 1000

        elapsed = asyncio.run(run())
        assert elapsed < 1000, f"Search 10k docs took {elapsed:.2f}ms, budget 1000ms"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
class TestAuditLogBenchmarks:
    """Audit log append + query timing."""

    def test_audit_append_benchmark(self):
        """Audit log append: p99 < 20ms."""
        audit = AuditLog()
        timings = []
        for i in range(10_000):
            start = time.perf_counter()
            audit.log(AuditEventType.ENTITY_CREATE, "bench-user", "create", "entity", f"E{i}")
            timings.append((time.perf_counter() - start) * 1000)
        timings.sort()
        p99 = timings[int(len(timings) * 0.99)]
        assert p99 < 20, f"Audit append p99={p99:.2f}ms exceeds 20ms budget"

    def test_audit_query_capacity(self):
        """Query 10,000 audit entries in < 500ms."""
        audit = AuditLog()
        for i in range(10_000):
            audit.log(AuditEventType.ENTITY_CREATE, f"user-{i % 10}", "create", "entity", f"E{i}")
        start = time.perf_counter()
        results = audit.query(user_id="user-0")
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 500, f"Audit query 10k took {elapsed:.2f}ms, budget 500ms"
        assert len(results) >= 1
