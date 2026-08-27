"""GFIN Source Registry — central registry for all authorized data sources."""
from __future__ import annotations
from typing import Any, Optional
from datetime import datetime, timezone
import logging

from packages.sources.enums import AuthMethod

logger = logging.getLogger(__name__)


class SourceRecord:
    """A registered data source (API, feed, provider).

    No unregistered external source may be used by the Brain.
    """

    def __init__(
        self,
        source_id: str,
        provider: str,
        connector: str,
        base_url: str,
        auth_method: AuthMethod = AuthMethod.PUBLIC_API,
        data_categories: list[str] | None = None,
        jurisdictions: list[str] | None = None,
        allowed_data: list[str] | None = None,
        classification: str = "PUBLIC",
        required_permissions: list[str] | None = None,
        legal_basis: str = "",
        rate_limit: int = 60,
        audit_policy: str = "full",
        enabled: bool = True,
        version: str = "1.0.0",
        reliability: str = "MEDIUM",
        last_verified: datetime | None = None,
    ):
        self.source_id = source_id
        self.provider = provider
        self.connector = connector
        self.base_url = base_url
        self.auth_method = auth_method
        self.data_categories = data_categories or []
        self.jurisdictions = jurisdictions or []
        self.allowed_data = allowed_data or []
        self.classification = classification
        self.required_permissions = required_permissions or []
        self.legal_basis = legal_basis
        self.rate_limit = rate_limit
        self.audit_policy = audit_policy
        self.enabled = enabled
        self.version = version
        self.reliability = reliability
        self.last_verified = last_verified or datetime.now(timezone.utc)


class SourceRegistry:
    """Central registry for all authorized data sources.

    No unregistered external source may be used by the Brain.
    """

    def __init__(self):
        self._sources: dict[str, SourceRecord] = {}

    def register(self, source: SourceRecord) -> None:
        """Register a new source."""
        if source.source_id in self._sources:
            raise ValueError(f"Source already registered: {source.source_id}")
        self._sources[source.source_id] = source
        logger.info(f"Source registered: {source.source_id} ({source.provider})")

    def unregister(self, source_id: str) -> None:
        """Remove a source."""
        self._sources.pop(source_id, None)

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        """Get a source by ID."""
        return self._sources.get(source_id)

    def list_sources(self, enabled_only: bool = True) -> list[SourceRecord]:
        """List all registered sources."""
        sources = list(self._sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sources

    def search_by_data_type(self, data_type: str) -> list[SourceRecord]:
        """Search for sources that provide a specific data type."""
        results = []
        for source in self._sources.values():
            if not source.enabled:
                continue
            if data_type in source.data_categories:
                results.append(source)
            if data_type in source.allowed_data:
                results.append(source)
        return results

    def search_by_jurisdiction(self, jurisdiction: str) -> list[SourceRecord]:
        """Search for sources available in a jurisdiction."""
        results = []
        for source in self._sources.values():
            if not source.enabled:
                continue
            if jurisdiction in source.jurisdictions or "GLOBAL" in source.jurisdictions:
                results.append(source)
        return results

    def update_source(self, source_id: str, **kwargs: Any) -> bool:
        """Update a source's attributes."""
        source = self._sources.get(source_id)
        if not source:
            return False
        for key, value in kwargs.items():
            if hasattr(source, key):
                setattr(source, key, value)
        return True

    def is_registered(self, source_id: str) -> bool:
        """Check if a source is registered."""
        return source_id in self._sources and self._sources[source_id].enabled

    def get_all_for_brain(self) -> list[dict[str, Any]]:
        """Get all source definitions for the Brain (no credentials)."""
        result = []
        for source in self._sources.values():
            if source.enabled:
                result.append({
                    "source_id": source.source_id,
                    "provider": source.provider,
                    "data_categories": source.data_categories,
                    "jurisdictions": source.jurisdictions,
                    "auth_method": source.auth_method.value,
                    "classification": source.classification,
                    "legal_basis": source.legal_basis,
                    "reliability": source.reliability,
                })
        return result
