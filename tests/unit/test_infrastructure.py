"""Tests for GFIN infrastructure abstraction interfaces (development adapters)."""

import pytest

from common.cache import MemoryCache
from common.database import InMemoryEntityRepository
from common.event_bus import Event, InMemoryEventBus
from common.graph import AdjacencyListGraph, GraphEdge, GraphNode
from common.identity import Base44IdentityProvider
from common.model_gateway import (
    BaseModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    TaskType,
)
from common.storage import LocalObjectStorage
from schemas.base import BaseEntity
from schemas.enums import DataClassification, EntityType, UserRole

# ─── Database (EntityRepository) ───


class TestInMemoryEntityRepository:
    """Test the development adapter for entity persistence."""

    @pytest.fixture
    def repo(self):
        return InMemoryEntityRepository[BaseEntity]()

    @pytest.fixture
    def sample_entity(self):
        return BaseEntity(
            entity_type=EntityType.PHONE,
            normalized_value="+34612345678",
            raw_values=["+34 612 345 678"],
        )

    async def test_create_and_get(self, repo, sample_entity):
        created = await repo.create(sample_entity)
        assert created.id == sample_entity.id
        retrieved = await repo.get(sample_entity.id)
        assert retrieved is not None
        assert retrieved.normalized_value == "+34612345678"

    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("ENT-DOESNOTEXIST")
        assert result is None

    async def test_update(self, repo, sample_entity):
        await repo.create(sample_entity)
        updated = await repo.update(sample_entity.id, {"confidence": "HIGH"})
        assert updated is not None
        assert updated.confidence == "HIGH"

    async def test_update_nonexistent_returns_none(self, repo):
        result = await repo.update("ENT-NOPE", {"confidence": "HIGH"})
        assert result is None

    async def test_delete(self, repo, sample_entity):
        await repo.create(sample_entity)
        result = await repo.delete(sample_entity.id)
        assert result is True
        assert await repo.get(sample_entity.id) is None

    async def test_delete_nonexistent_returns_false(self, repo):
        result = await repo.delete("ENT-NOPE")
        assert result is False

    async def test_list_with_filters(self, repo):
        for i in range(5):
            await repo.create(
                BaseEntity(
                    entity_type=EntityType.PHONE,
                    normalized_value=f"+34612345{i}",
                )
            )
        results = await repo.list(filters={"entity_type": "PHONE"}, limit=10)
        assert len(results) == 5

    async def test_list_pagination(self, repo):
        for i in range(10):
            await repo.create(
                BaseEntity(
                    entity_type=EntityType.EMAIL,
                    normalized_value=f"test{i}@example.com",
                )
            )
        page1 = await repo.list(limit=5, offset=0)
        page2 = await repo.list(limit=5, offset=5)
        assert len(page1) == 5
        assert len(page2) == 5

    async def test_find_by_normalized_value(self, repo, sample_entity):
        await repo.create(sample_entity)
        found = await repo.find_by_normalized_value("PHONE", "+34612345678")
        assert found is not None
        assert found.id == sample_entity.id

    async def test_find_by_normalized_value_not_found(self, repo):
        found = await repo.find_by_normalized_value("PHONE", "+999999999")
        assert found is None

    async def test_count(self, repo):
        for i in range(3):
            await repo.create(
                BaseEntity(
                    entity_type=EntityType.DOMAIN,
                    normalized_value=f"site{i}.com",
                )
            )
        assert await repo.count() == 3


# ─── Event Bus ───


class TestInMemoryEventBus:
    """Test the development adapter for event publishing/subscribing."""

    @pytest.fixture
    def bus(self):
        return InMemoryEventBus()

    async def test_publish_and_subscribe(self, bus):
        received: list[Event] = []
        await bus.subscribe("entity.created", lambda e: received.append(e))

        event = Event(
            event_type="entity.created",
            source="test",
            payload={
                "entity_id": "ENT-001",
                "entity_type": "PHONE",
                "normalized_value": "+34612345678",
            },
        )
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].event_type == "entity.created"

    async def test_unsubscribe(self, bus):
        received: list[Event] = []
        sub_id = await bus.subscribe("entity.created", lambda e: received.append(e))
        await bus.unsubscribe(sub_id)

        await bus.publish(
            Event(
                event_type="entity.created",
                source="test",
                payload={
                    "entity_id": "ENT-001",
                    "entity_type": "PHONE",
                    "normalized_value": "+34612345678",
                },
            )
        )
        assert len(received) == 0

    async def test_multiple_subscribers(self, bus):
        received_a: list[Event] = []
        received_b: list[Event] = []

        await bus.subscribe("observation.created", lambda e: received_a.append(e))
        await bus.subscribe("observation.created", lambda e: received_b.append(e))

        await bus.publish(
            Event(
                event_type="observation.created",
                source="test",
                payload={
                    "observation_id": "OBS-001",
                    "entity_id": "ENT-001",
                    "observation_type": "dns_lookup",
                },
            )
        )

        assert len(received_a) == 1
        assert len(received_b) == 1

    async def test_event_has_required_fields(self):
        """Per Master Spec §9: Every event must contain required fields."""
        event = Event(
            event_type="entity.created",
            source="crawler",
            entity_refs=["ENT-001"],
            classification="PUBLIC",
            correlation_id="REQ-001",
        )
        assert event.event_id is not None
        assert event.event_type == "entity.created"
        assert event.schema_version == "1.0"
        assert event.timestamp is not None
        assert event.source == "crawler"
        assert len(event.entity_refs) == 1


# ─── Graph Store ───


class TestAdjacencyListGraph:
    """Test the development adapter for graph operations."""

    @pytest.fixture
    def graph(self):
        return AdjacencyListGraph()

    async def test_add_and_get_node(self, graph):
        node = GraphNode(entity_id="ENT-001", entity_type="PHONE", label="+34612345678")
        await graph.add_node(node)
        result = await graph.get_node("ENT-001")
        assert result is not None
        assert result.label == "+34612345678"

    async def test_get_nonexistent_node(self, graph):
        result = await graph.get_node("ENT-NOPE")
        assert result is None

    async def test_add_edge_and_get_neighbors(self, graph):
        await graph.add_node(GraphNode(entity_id="ENT-001", entity_type="PHONE", label="A"))
        await graph.add_node(GraphNode(entity_id="ENT-002", entity_type="DOMAIN", label="B"))
        await graph.add_edge(
            GraphEdge(
                relationship_id="REL-001",
                from_entity_id="ENT-001",
                to_entity_id="ENT-002",
                relationship_type="RESOLVES_TO",
            )
        )
        nodes, edges = await graph.get_neighbors("ENT-001")
        assert len(nodes) == 1
        assert nodes[0].entity_id == "ENT-002"
        assert len(edges) == 1

    async def test_find_path(self, graph):
        for i in range(4):
            await graph.add_node(
                GraphNode(entity_id=f"ENT-{i}", entity_type="DOMAIN", label=f"d{i}.com")
            )
        for i in range(3):
            await graph.add_edge(
                GraphEdge(
                    relationship_id=f"REL-{i}",
                    from_entity_id=f"ENT-{i}",
                    to_entity_id=f"ENT-{i + 1}",
                    relationship_type="REDIRECTS_TO",
                )
            )
        path = await graph.find_path("ENT-0", "ENT-3")
        assert path is not None
        assert path.length == 3

    async def test_find_path_not_found(self, graph):
        await graph.add_node(GraphNode(entity_id="ENT-A", entity_type="IP", label="A"))
        await graph.add_node(GraphNode(entity_id="ENT-B", entity_type="IP", label="B"))
        path = await graph.find_path("ENT-A", "ENT-B")
        assert path is None

    async def test_remove_node(self, graph):
        await graph.add_node(GraphNode(entity_id="ENT-001", entity_type="PHONE", label="A"))
        result = await graph.remove_node("ENT-001")
        assert result is True
        assert await graph.get_node("ENT-001") is None

    async def test_remove_edge(self, graph):
        await graph.add_node(GraphNode(entity_id="ENT-001", entity_type="IP", label="A"))
        await graph.add_node(GraphNode(entity_id="ENT-002", entity_type="IP", label="B"))
        await graph.add_edge(
            GraphEdge(
                relationship_id="REL-001",
                from_entity_id="ENT-001",
                to_entity_id="ENT-002",
                relationship_type="HOSTED_ON",
            )
        )
        result = await graph.remove_edge("REL-001")
        assert result is True


# ─── Cache ───


class TestMemoryCache:
    """Test the development adapter for caching."""

    @pytest.fixture
    def cache(self):
        return MemoryCache()

    async def test_set_and_get(self, cache):
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

    async def test_get_nonexistent(self, cache):
        assert await cache.get("nonexistent") is None

    async def test_ttl_expiration(self, cache):
        await cache.set("key1", "value1", ttl_seconds=0)
        # TTL of 0 means it expires immediately
        import asyncio

        await asyncio.sleep(0.01)
        assert await cache.get("key1") is None

    async def test_delete(self, cache):
        await cache.set("key1", "value1")
        assert await cache.delete("key1") is True
        assert await cache.get("key1") is None

    async def test_delete_nonexistent(self, cache):
        assert await cache.delete("nonexistent") is False

    async def test_exists(self, cache):
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True
        assert await cache.exists("key2") is False

    async def test_clear(self, cache):
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None


# ─── Storage ───


class TestLocalObjectStorage:
    """Test the development adapter for object storage."""

    @pytest.fixture
    def storage(self, tmp_path):
        return LocalObjectStorage(base_path=str(tmp_path))

    async def test_store_and_retrieve(self, storage):
        data = b"test evidence content"
        obj = await storage.store("evidence/test.txt", data)
        assert obj.content_hash is not None
        assert obj.size == len(data)

        retrieved = await storage.retrieve("evidence/test.txt")
        assert retrieved == data

    async def test_retrieve_nonexistent(self, storage):
        assert await storage.retrieve("nonexistent") is None

    async def test_delete(self, storage):
        await storage.store("test.txt", b"data")
        assert await storage.delete("test.txt") is True
        assert await storage.retrieve("test.txt") is None

    async def test_exists(self, storage):
        await storage.store("test.txt", b"data")
        assert await storage.exists("test.txt") is True
        assert await storage.exists("nonexistent") is False

    async def test_content_hash_is_sha256(self, storage):
        import hashlib

        data = b"hash test"
        obj = await storage.store("hash.txt", data)
        expected = hashlib.sha256(data).hexdigest()
        assert obj.content_hash == expected


# ─── Identity ───


class TestBase44IdentityProvider:
    """Test the development adapter for authentication."""

    @pytest.fixture
    def provider(self):
        return Base44IdentityProvider()

    async def test_create_and_authenticate_token(self, provider):
        token = await provider.create_token("user-001", UserRole.INVESTIGATOR)
        context = await provider.authenticate(token)
        assert context is not None
        assert context.user_id == "user-001"
        assert context.role == UserRole.INVESTIGATOR

    async def test_authenticate_invalid_token(self, provider):
        result = await provider.authenticate("invalid-token")
        assert result is None

    async def test_revoke_token(self, provider):
        token = await provider.create_token("user-001", UserRole.CITIZEN)
        result = await provider.revoke_token(token)
        assert result is True
        assert await provider.authenticate(token) is None

    async def test_authorize_citizen_cannot_access_restricted(self, provider):
        token = await provider.create_token("user-001", UserRole.CITIZEN)
        context = await provider.authenticate(token)
        assert context is not None
        result = await provider.authorize(context, "read", "entity", DataClassification.RESTRICTED)
        assert result is False

    async def test_authorize_investigator_can_access_restricted(self, provider):
        token = await provider.create_token("user-001", UserRole.INVESTIGATOR)
        context = await provider.authenticate(token)
        assert context is not None
        result = await provider.authorize(context, "read", "entity", DataClassification.RESTRICTED)
        assert result is True

    async def test_authorize_citizen_can_access_public(self, provider):
        token = await provider.create_token("user-001", UserRole.CITIZEN)
        context = await provider.authenticate(token)
        assert context is not None
        result = await provider.authorize(context, "read", "entity", DataClassification.PUBLIC)
        assert result is True


# ─── Model Gateway ───


class TestBaseModelGateway:
    """Test the model gateway routing logic."""

    @pytest.fixture
    def gateway(self):
        class MockGateway(BaseModelGateway):
            async def _call_provider(self, provider, request, operation):
                return ModelResponse(
                    content=f"mock-{operation}",
                    provider=provider.value,
                    model="mock-model",
                    task_type=request.task_type.value,
                )

            async def embed(self, text):
                return [0.1] * 128

        return MockGateway()

    async def test_routes_restricted_to_local(self, gateway):
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="Analyze this evidence",
            classification_filter="HIGHLY_RESTRICTED",
        )
        response = await gateway.generate(request)
        assert response.provider == "local"

    async def test_routes_public_to_primary(self, gateway):
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="Summarize this",
            classification_filter="PUBLIC",
        )
        response = await gateway.generate(request)
        assert response.provider == "openai"

    async def test_embeddings_always_local(self, gateway):
        """Embeddings should always use local model for latency and privacy."""
        request = ModelRequest(
            task_type=TaskType.EMBEDDING,
            prompt="test",
            classification_filter="PUBLIC",
        )
        response = await gateway.generate(request)
        assert response.provider == "local"

    async def test_fallback_on_error(self, gateway):
        class FailingGateway(BaseModelGateway):
            def __init__(self):
                super().__init__(
                    primary_provider=ModelProvider.OPENAI,
                    fallback_provider=ModelProvider.LOCAL,
                )

            async def _call_provider(self, provider, request, operation):
                if provider == ModelProvider.OPENAI:
                    raise RuntimeError("OpenAI unavailable")
                return ModelResponse(
                    content="fallback",
                    provider="local",
                    model="local-model",
                    task_type=request.task_type.value,
                )

        failing = FailingGateway()
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="test",
            classification_filter="PUBLIC",
        )
        response = await failing.generate(request)
        assert response.content == "fallback"
        assert response.provider == "local"

    async def test_health_check(self, gateway):
        health = await gateway.health_check()
        assert isinstance(health, dict)
