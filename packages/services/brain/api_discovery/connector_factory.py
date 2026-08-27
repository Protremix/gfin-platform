"""GFIN Connector Factory — creates secure connectors for registered providers."""
from __future__ import annotations
from typing import Any, Optional, Protocol
from datetime import datetime, timezone
import hashlib
import logging

from packages.sources.registry import SourceRecord

logger = logging.getLogger(__name__)


class ConnectorInterface(Protocol):
    """Interface for all source connectors."""
    def fetch(self, params: dict[str, Any]) -> dict[str, Any]: ...


class ConnectorFactory:
    """Creates secure connectors for registered providers.

    Pipeline:
        Source Adapter Interface -> Authentication -> Policy Enforcement ->
        Rate Limiter -> Provider API -> Response Validator -> Normalizer ->
        Evidence Builder -> Graph Updater -> Audit

    The Brain never receives raw provider credentials.
    """

    def __init__(self):
        self._connectors: dict[str, ConnectorInterface] = {}
        self._call_log: list[dict[str, Any]] = []

    def register_connector(self, source_id: str, connector: ConnectorInterface) -> None:
        """Register a connector for a source."""
        self._connectors[source_id] = connector
        logger.info(f"Connector registered for source: {source_id}")

    def get_connector(self, source_id: str) -> Optional[ConnectorInterface]:
        """Get the connector for a source."""
        return self._connectors.get(source_id)

    def execute(
        self,
        source: SourceRecord,
        params: dict[str, Any],
        credentials: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a connector call through the full pipeline.

        Credentials are passed separately and never logged or stored.
        """
        connector = self._connectors.get(source.source_id)
        if not connector:
            return {
                "status": "CONNECTOR_NOT_IMPLEMENTED",
                "source_id": source.source_id,
                "error": f"No connector for source {source.source_id}",
            }

        try:
            # Execute through connector (auth, rate limit, API call, validation, normalization)
            raw_result = connector.fetch(params)

            # Build evidence record
            evidence = self._build_evidence(source, raw_result, params)

            # Audit (credentials never included)
            self._call_log.append({
                "source_id": source.source_id,
                "provider": source.provider,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "params_hash": hashlib.sha256(str(params).encode()).hexdigest()[:16],
                "result_hash": hashlib.sha256(str(raw_result).encode()).hexdigest()[:16],
                "success": True,
            })

            return {
                "status": "SUCCESS",
                "source_id": source.source_id,
                "provider": source.provider,
                "data": raw_result,
                "evidence": evidence,
            }
        except Exception as e:
            self._call_log.append({
                "source_id": source.source_id,
                "provider": source.provider,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": False,
                "error": str(e),
            })
            return {
                "status": "PROVIDER_ERROR",
                "source_id": source.source_id,
                "error": str(e),
            }

    def _build_evidence(
        self,
        source: SourceRecord,
        result: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Build evidence record from API response."""
        return {
            "provider": source.provider,
            "endpoint": source.base_url,
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "request_params_hash": hashlib.sha256(str(params).encode()).hexdigest()[:16],
            "response_hash": hashlib.sha256(str(result).encode()).hexdigest()[:16],
            "source_id": source.source_id,
            "processing_version": "1.0.0",
            "evidence_type": "api_response",
        }

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get the connector call audit log (no credentials)."""
        return list(self._call_log)
