# GFIN Database Abstraction Interface
#
# Layer A (current): InMemoryEntityRepository — development/MVP
# Layer B (target):  PostgresEntityRepository — PostgreSQL + SQLAlchemy (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# The application NEVER talks to a specific database directly.
# It talks to EntityRepository. The adapter is selected by configuration.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from schemas.base import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class EntityRepository(ABC, Generic[T]):
    """Abstract repository interface for entity persistence.

    All application code uses this interface.
    The specific adapter (in-memory, Base44, PostgreSQL) is selected by configuration.
    """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity record."""
        ...

    @abstractmethod
    async def get(self, entity_id: str) -> T | None:
        """Get an entity by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> T | None:
        """Update an entity. Returns updated entity or None if not found."""
        ...

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """List entities with optional filters."""
        ...

    @abstractmethod
    async def find_by_normalized_value(self, entity_type: str, normalized_value: str) -> T | None:
        """Find an entity by its normalized value (for deduplication)."""
        ...

    @abstractmethod
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching filters."""
        ...


class InMemoryEntityRepository(EntityRepository[T]):
    """Development adapter — in-memory storage.

    NOT for production. No persistence. Data is lost on restart.
    Production uses PostgreSQL adapter (REQUIRES EXTERNAL INFRASTRUCTURE).
    """

    def __init__(self) -> None:
        self._store: dict[str, T] = {}
        self._by_type_value: dict[tuple[str, str], str] = {}

    async def create(self, entity: T) -> T:
        self._store[entity.id] = entity
        self._by_type_value[(entity.entity_type, entity.normalized_value)] = entity.id
        return entity

    async def get(self, entity_id: str) -> T | None:
        return self._store.get(entity_id)

    async def update(self, entity_id: str, data: dict[str, Any]) -> T | None:
        entity = self._store.get(entity_id)
        if entity is None:
            return None
        updated = entity.model_copy(update=data)
        self._store[entity_id] = updated
        return updated

    async def delete(self, entity_id: str) -> bool:
        entity = self._store.pop(entity_id, None)
        if entity is not None:
            self._by_type_value.pop((entity.entity_type, entity.normalized_value), None)
            return True
        return False

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        results = list(self._store.values())
        if filters:
            results = [
                e for e in results if all(getattr(e, k, None) == v for k, v in filters.items())
            ]
        return results[offset : offset + limit]

    async def find_by_normalized_value(self, entity_type: str, normalized_value: str) -> T | None:
        entity_id = self._by_type_value.get((entity_type, normalized_value))
        if entity_id is None:
            return None
        return self._store.get(entity_id)

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        if not filters:
            return len(self._store)
        return len(
            [
                e
                for e in self._store.values()
                if all(getattr(e, k, None) == v for k, v in filters.items())
            ]
        )
