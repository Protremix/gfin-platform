"""GFIN Police Connector SDK — Module 24.

Standardized interface for police organizations to connect national systems
to GFIN. Per Architecture Review §8.3: authenticate, synchronize, submit
observation, receive match/alert, handle request, acknowledge, retry.

Layer A: Abstract interface + mock implementation (in-memory)
Layer B: Real connectors with mTLS, credential vault (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class SyncDirection(StrEnum):
    PUSH = "PUSH"
    PULL = "PULL"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class SyncStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ConnectorStatus(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class ConnectorEventType(StrEnum):
    MATCH = "MATCH"
    ALERT = "ALERT"
    REQUEST = "REQUEST"
    SYNC = "SYNC"
    OBSERVATION = "OBSERVATION"


# ─── Models ───


class ConnectorCredential(BaseModel):
    """Credentials for a police connector (HIGHLY_RESTRICTED classification)."""

    org_id: str
    api_key: str
    mtls_cert: str = ""  # Layer B: certificate for mTLS
    mtls_key: str = ""  # Layer B: private key for mTLS
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    rotated_at: datetime | None = None

    def rotate(self, new_api_key: str) -> None:
        """Rotate the API key."""
        self.api_key = new_api_key
        self.rotated_at = datetime.now(UTC)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a dict with credentials redacted (for logging)."""
        return {
            "org_id": self.org_id,
            "api_key": "***REDACTED***",
            "mtls_cert": "***REDACTED***" if self.mtls_cert else "",
            "has_mtls": bool(self.mtls_cert),
            "created_at": self.created_at.isoformat(),
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
        }


class ConnectorConfig(BaseModel):
    """Configuration for a police connector."""

    org_id: str
    org_name: str
    jurisdiction: str
    endpoint: str = "https://api.gfin.local/v1/police"
    sync_interval: int = 300  # seconds
    max_retries: int = 3
    timeout: int = 30  # seconds


class SyncResult(BaseModel):
    """Result of a synchronization operation."""

    direction: str
    records_pushed: int = 0
    records_pulled: int = 0
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    status: str = SyncStatus.SUCCESS.value
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error: str = ""


class ConnectorEvent(BaseModel):
    """An event received by or sent to a connector."""

    id: str
    event_type: str
    org_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


# ─── Police Connector Interface (ABC) ───


class PoliceConnectorInterface(ABC):
    """Abstract interface for police connectors.

    Implement per country/organization. Per Architecture Review §8.3.
    """

    def __init__(self, config: ConnectorConfig, credential: ConnectorCredential) -> None:
        self.config = config
        self.credential = credential
        self.status: str = ConnectorStatus.DISCONNECTED.value
        self._events: list[ConnectorEvent] = []
        self._event_counter = 0
        self._obs_counter = 0
        self._ack_counter = 0

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with GFIN using credentials."""
        ...

    @abstractmethod
    def synchronize(self, direction: str = SyncDirection.BIDIRECTIONAL.value) -> SyncResult:
        """Synchronize data with GFIN."""
        ...

    @abstractmethod
    def submit_observation(
        self,
        entity_type: str,
        entity_value: str,
        observation_text: str = "",
    ) -> str:
        """Submit an observation to GFIN. Returns observation ID."""
        ...

    @abstractmethod
    def receive_match(self, match_data: dict[str, Any]) -> str:
        """Receive a match notification from GFIN. Returns acknowledgment ID."""
        ...

    @abstractmethod
    def receive_alert(self, alert_data: dict[str, Any]) -> str:
        """Receive an alert from GFIN. Returns acknowledgment ID."""
        ...

    @abstractmethod
    def handle_request(self, request_data: dict[str, Any]) -> str:
        """Handle a cross-border request. Returns response ID."""
        ...

    @abstractmethod
    def acknowledge(self, event_id: str) -> bool:
        """Acknowledge receipt of an event."""
        ...

    @abstractmethod
    def retry(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        """Retry a failed operation."""
        ...

    def _create_event(self, event_type: str, data: dict[str, Any]) -> ConnectorEvent:
        """Create and store an event."""
        self._event_counter += 1
        event = ConnectorEvent(
            id=f"EV-{self._event_counter:06d}",
            event_type=event_type,
            org_id=self.config.org_id,
            data=data,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> list[ConnectorEvent]:
        return list(self._events)

    @property
    def is_connected(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED.value


# ─── Mock Police Connector (Reference Implementation) ───


class MockPoliceConnector(PoliceConnectorInterface):
    """Mock implementation for development and testing.

    Uses in-memory test data. Simulates national system behavior.
    For development/testing only (per Architecture Review §8.3).
    """

    def authenticate(self) -> bool:
        """Authenticate with mock credentials."""
        self.status = ConnectorStatus.CONNECTING.value

        # Simulate authentication
        if self.credential.api_key and self.credential.org_id:
            self.status = ConnectorStatus.CONNECTED.value
            self._create_event(
                ConnectorEventType.SYNC.value, {"action": "authenticate", "result": "success"}
            )
            return True

        self.status = ConnectorStatus.ERROR.value
        return False

    def synchronize(self, direction: str = SyncDirection.BIDIRECTIONAL.value) -> SyncResult:
        """Synchronize with mock data."""
        if not self.is_connected:
            return SyncResult(
                direction=direction,
                status=SyncStatus.FAILED.value,
                error="Not authenticated",
            )

        result = SyncResult(
            direction=direction,
            records_pushed=5
            if direction in (SyncDirection.PUSH.value, SyncDirection.BIDIRECTIONAL.value)
            else 0,
            records_pulled=3
            if direction in (SyncDirection.PULL.value, SyncDirection.BIDIRECTIONAL.value)
            else 0,
            status=SyncStatus.SUCCESS.value,
        )

        self._create_event(
            ConnectorEventType.SYNC.value,
            {
                "direction": direction,
                "pushed": result.records_pushed,
                "pulled": result.records_pulled,
            },
        )

        return result

    def submit_observation(
        self,
        entity_type: str,
        entity_value: str,
        observation_text: str = "",
    ) -> str:
        """Submit a mock observation."""
        if not self.is_connected:
            raise RuntimeError("Connector not authenticated")

        self._obs_counter += 1
        obs_id = f"MOBS-{self._obs_counter:06d}"

        self._create_event(
            ConnectorEventType.OBSERVATION.value,
            {
                "observation_id": obs_id,
                "entity_type": entity_type,
                "entity_value": entity_value,
                "text": observation_text,
            },
        )

        return obs_id

    def receive_match(self, match_data: dict[str, Any]) -> str:
        """Receive a mock match notification."""
        self._ack_counter += 1
        ack_id = f"MACK-{self._ack_counter:06d}"

        self._create_event(
            ConnectorEventType.MATCH.value,
            {
                "ack_id": ack_id,
                "match_data": match_data,
            },
        )

        return ack_id

    def receive_alert(self, alert_data: dict[str, Any]) -> str:
        """Receive a mock alert."""
        self._ack_counter += 1
        ack_id = f"MACK-{self._ack_counter:06d}"

        self._create_event(
            ConnectorEventType.ALERT.value,
            {
                "ack_id": ack_id,
                "alert_data": alert_data,
            },
        )

        return ack_id

    def handle_request(self, request_data: dict[str, Any]) -> str:
        """Handle a mock cross-border request."""
        self._ack_counter += 1
        response_id = f"MRES-{self._ack_counter:06d}"

        self._create_event(
            ConnectorEventType.REQUEST.value,
            {
                "response_id": response_id,
                "request_data": request_data,
                "response": "mock_response",
            },
        )

        return response_id

    def acknowledge(self, event_id: str) -> bool:
        """Acknowledge receipt of an event."""
        for event in self._events:
            if event.id == event_id:
                event.acknowledged = True
                event.acknowledged_at = datetime.now(UTC)
                return True
        return False

    def retry(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        """Retry a failed operation."""
        params = params or {}

        if operation == "authenticate":
            return self.authenticate()
        elif operation == "synchronize":
            return self.synchronize(params.get("direction", SyncDirection.BIDIRECTIONAL.value))
        elif operation == "submit_observation":
            return self.submit_observation(
                params.get("entity_type", ""),
                params.get("entity_value", ""),
                params.get("observation_text", ""),
            )
        elif operation == "receive_match":
            return self.receive_match(params.get("match_data", {}))
        elif operation == "receive_alert":
            return self.receive_alert(params.get("alert_data", {}))
        elif operation == "handle_request":
            return self.handle_request(params.get("request_data", {}))
        elif operation == "acknowledge":
            return self.acknowledge(params.get("event_id", ""))
        else:
            raise ValueError(f"Unknown operation: {operation}")


# ─── Connector Registry ───


class ConnectorRegistry:
    """Registry for managing police connectors."""

    def __init__(self, audit_logger: Any | None = None) -> None:
        self._connectors: dict[str, PoliceConnectorInterface] = {}
        self._audit = audit_logger

    def register(self, connector: PoliceConnectorInterface) -> None:
        """Register a connector."""
        org_id = connector.config.org_id
        self._connectors[org_id] = connector

        if self._audit:
            with contextlib.suppress(Exception):
                self._audit.log(
                    user_id="system",
                    action="connector_registered",
                    resource_type="connector",
                    resource_id=org_id,
                    details=connector.credential.to_safe_dict(),
                )

    def unregister(self, org_id: str) -> bool:
        """Unregister a connector."""
        return self._connectors.pop(org_id, None) is not None

    def get_connector(self, org_id: str) -> PoliceConnectorInterface | None:
        """Get a connector by org ID."""
        return self._connectors.get(org_id)

    def list_connectors(self) -> list[dict[str, Any]]:
        """List all registered connectors."""
        return [
            {
                "org_id": c.config.org_id,
                "org_name": c.config.org_name,
                "jurisdiction": c.config.jurisdiction,
                "status": c.status,
                "is_connected": c.is_connected,
            }
            for c in self._connectors.values()
        ]

    @property
    def count(self) -> int:
        return len(self._connectors)

    def authenticate_all(self) -> dict[str, bool]:
        """Authenticate all registered connectors."""
        results: dict[str, bool] = {}
        for org_id, connector in self._connectors.items():
            results[org_id] = connector.authenticate()
        return results

    def synchronize_all(
        self, direction: str = SyncDirection.BIDIRECTIONAL.value
    ) -> dict[str, SyncResult]:
        """Synchronize all registered connectors."""
        results: dict[str, SyncResult] = {}
        for org_id, connector in self._connectors.items():
            results[org_id] = connector.synchronize(direction)
        return results


# ─── Factory ───


def create_mock_connector(
    org_id: str = "ORG-MOCK",
    org_name: str = "Mock Police Organization",
    jurisdiction: str = "MOCK",
    api_key: str = "mock-api-key",
) -> MockPoliceConnector:
    """Create a mock connector for testing."""
    config = ConnectorConfig(
        org_id=org_id,
        org_name=org_name,
        jurisdiction=jurisdiction,
    )
    credential = ConnectorCredential(
        org_id=org_id,
        api_key=api_key,
    )
    return MockPoliceConnector(config=config, credential=credential)
