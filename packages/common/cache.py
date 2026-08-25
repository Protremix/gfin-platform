# GFIN Cache Service Abstraction Interface
#
# Layer A (current): MemoryCache — in-memory dict
# Layer B (target):  RedisCache — Redis-compatible (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any


class CacheService(ABC):
    """Abstract cache service interface.

    All application code caches through this interface.
    The specific adapter (in-memory, Redis) is selected by configuration.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value by key. Returns None if not found or expired."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set a value with optional TTL in seconds."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached values."""
        ...


class MemoryCache(CacheService):
    """Development adapter — in-memory cache.

    NOT for production. No persistence, no distributed cache, no eviction policy.
    Production uses Redis adapter (REQUIRES EXTERNAL INFRASTRUCTURE).

    TTL is supported but only checked on access (lazy expiration).
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, datetime | None]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and datetime.now(UTC) > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        _, expires_at = entry
        if expires_at is not None and datetime.now(UTC) > expires_at:
            del self._store[key]
            return False
        return True

    async def clear(self) -> None:
        self._store.clear()
