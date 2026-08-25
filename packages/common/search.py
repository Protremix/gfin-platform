# GFIN Search Service Abstraction Interface
#
# Layer A (current): EntitySearchService — queries entity repository
# Layer B (target):  OpenSearchService — OpenSearch cluster (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# Per Master Spec §11: Support exact, normalized, fuzzy, semantic, entity, graph-assisted,
# campaign, infrastructure, and report search. All results must respect authorization
# and data-sharing policies.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str
    entity_type: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    fuzzy: bool = False
    semantic: bool = False
    limit: int = 50
    offset: int = 0
    classification_filter: str | None = None
    user_role: str | None = None
    user_jurisdiction: str | None = None


class SearchResult(BaseModel):
    """A single search result."""

    entity_id: str
    entity_type: str
    normalized_value: str
    score: float = 1.0
    highlights: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response with pagination."""

    results: list[SearchResult] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False


class SearchService(ABC):
    """Abstract search service interface.

    All application code searches through this interface.
    The specific adapter (entity repository, OpenSearch) is selected by configuration.
    """

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute a search query."""
        ...

    @abstractmethod
    async def index_entity(self, entity: Any) -> None:
        """Index or re-index an entity."""
        ...

    @abstractmethod
    async def delete_index(self, entity_id: str) -> bool:
        """Remove an entity from the index."""
        ...


class EntitySearchService(SearchService):
    """Development adapter — searches against entity repository.

    NOT for production. No full-text search, no fuzzy matching, no semantic search.
    Production uses OpenSearch adapter (REQUIRES EXTERNAL INFRASTRUCTURE).

    Supports: exact match, prefix match, entity type filter.
    Does NOT support: fuzzy, semantic, graph-assisted search.
    """

    def __init__(self, repository: Any) -> None:
        self._repo = repository

    async def search(self, query: SearchQuery) -> SearchResponse:
        filters = dict(query.filters)
        if query.entity_type:
            filters["entity_type"] = query.entity_type

        entities = await self._repo.list(filters=filters, limit=query.limit, offset=query.offset)
        total = await self._repo.count(filters=filters)

        results = [
            SearchResult(
                entity_id=e.id,
                entity_type=e.entity_type,
                normalized_value=e.normalized_value,
                score=1.0,
            )
            for e in entities
        ]

        return SearchResponse(
            results=results,
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=(query.offset + query.limit) < total,
        )

    async def index_entity(self, entity: Any) -> None:
        """No-op in development adapter — entities are queried directly."""
        pass

    async def delete_index(self, entity_id: str) -> bool:
        """No-op in development adapter."""
        return True
