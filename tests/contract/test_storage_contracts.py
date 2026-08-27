"""Contract tests for storage (entity repository) operations.

Per Luna Directive — Focus Area 1: Contract tests for CRUD operations
on all entity types and migration test fixtures.
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

import pytest

from common.database import InMemoryEntityRepository
from schemas.entities import create_entity
from schemas.versions import check_backward_compatibility, get_schema, migrate_entity


class TestStorageCRUDContracts:
    """Test CRUD operations on entity repository."""

    def test_create_and_read_entity(self):
        """Created entity should be retrievable by ID."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e = create_entity("EMAIL", email="test@example.com")
            await repo.create(e)
            return await repo.get(e.id)

        result = asyncio.run(run())
        assert result is not None

    def test_update_entity(self):
        """Updating an entity should modify its data."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e = create_entity("PHONE", e164="+1234567890")
            await repo.create(e)
            updated = await repo.update(e.id, {"confidence": 0.95})
            return updated

        result = asyncio.run(run())
        assert result is not None
        assert result.confidence == 0.95

    def test_delete_entity(self):
        """Deleted entity should not be retrievable."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e = create_entity("DOMAIN", domain="example.com")
            await repo.create(e)
            deleted = await repo.delete(e.id)
            after = await repo.get(e.id)
            return deleted, after

        deleted, after = asyncio.run(run())
        assert deleted is True
        assert after is None

    def test_list_with_pagination(self):
        """List should support pagination via offset."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(50):
                e = create_entity("EMAIL", email=f"user{i}@test.com")
                await repo.create(e)
            page1 = await repo.list(limit=10, offset=0)
            page2 = await repo.list(limit=10, offset=10)
            return page1, page2

        page1, page2 = asyncio.run(run())
        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].id != page2[0].id

    def test_count_all_entities(self):
        """Count should return total number of entities."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            for i in range(100):
                e = create_entity("PHONE", e164=f"+15550{i:04d}")
                await repo.create(e)
            return await repo.count()

        count = asyncio.run(run())
        assert count == 100


class TestStorageEntityTypes:
    """Test CRUD with different entity types."""

    @pytest.mark.parametrize("entity_type,kwargs", [
        ("EMAIL", {"email": "test@test.com"}),
        ("PHONE", {"e164": "+1234567890"}),
        ("DOMAIN", {"domain": "example.com"}),
    ])
    def test_create_different_entity_types(self, entity_type, kwargs):
        """Repository should handle different entity types."""
        repo: InMemoryEntityRepository = InMemoryEntityRepository()

        async def run():
            e = create_entity(entity_type, **kwargs)
            await repo.create(e)
            return await repo.get(e.id)

        result = asyncio.run(run())
        assert result is not None


class TestSchemaMigrationContracts:
    """Test schema migration from v1.0 to v1.1."""

    def test_entity_schema_v1_exists(self):
        """Entity schema v1.0 should exist."""
        schema = get_schema("entity", "1.0")
        assert schema is not None
        assert schema.version == "1.0"

    def test_entity_schema_v1_1_exists(self):
        """Entity schema v1.1 should exist."""
        schema = get_schema("entity", "1.1")
        assert schema is not None
        assert schema.version == "1.1"

    def test_v1_to_v1_1_backward_compatible(self):
        """v1.0 to v1.1 should be backward compatible."""
        is_compatible, issues = check_backward_compatibility("entity", "1.0", "1.1")
        assert is_compatible, f"Expected compatibility: {issues}"

    def test_migration_adds_new_optional_fields(self):
        """Migration should add new optional fields with None defaults."""
        data_v1 = {
            "id": "ENT-001",
            "entity_type": "EMAIL",
            "normalized_value": "test@example.com",
            "confidence": 0.9,
        }
        result = migrate_entity(data_v1, "1.0", "1.1")
        assert result.success
        assert "classification" in result.added_fields
        assert "organization_id" in result.added_fields

    def test_migration_preserves_existing_fields(self):
        """Migration should preserve existing fields."""
        data_v1 = {
            "id": "ENT-001",
            "entity_type": "EMAIL",
            "normalized_value": "test@example.com",
            "confidence": 0.9,
        }
        result = migrate_entity(data_v1, "1.0", "1.1")
        assert "id" in result.migrated_fields
        assert "entity_type" in result.migrated_fields
        assert "normalized_value" in result.migrated_fields
        assert "confidence" in result.migrated_fields

    def test_migration_fails_on_missing_required(self):
        """Migration should fail if required fields are missing."""
        data_v1 = {
            "entity_type": "EMAIL",
            # Missing id and normalized_value
        }
        result = migrate_entity(data_v1, "1.0", "1.1")
        assert not result.success
        assert len(result.errors) > 0

    def test_migration_with_unknown_version(self):
        """Migration with unknown version should fail."""
        data = {"id": "ENT-001"}
        result = migrate_entity(data, "0.0", "99.0")
        assert not result.success
