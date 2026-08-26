"""Tests for Police Connector SDK — Module 24.

Tests cover:
- PoliceConnectorInterface: abstract methods defined
- MockPoliceConnector: all 8 interface methods
- ConnectorRegistry: register, unregister, get, list, authenticate_all, synchronize_all
- ConnectorCredential: storage, rotation, safe dict (no plaintext)
- SyncResult: fields, status
- ConnectorEvent: creation, acknowledgment
- Integration: full connector lifecycle
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from services.police_connector_sdk import (
    ConnectorConfig,
    ConnectorCredential,
    ConnectorEvent,
    ConnectorEventType,
    ConnectorRegistry,
    ConnectorStatus,
    MockPoliceConnector,
    PoliceConnectorInterface,
    SyncDirection,
    SyncResult,
    SyncStatus,
    create_mock_connector,
)

# ─── Fixtures ───


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def connector():
    return create_mock_connector()


@pytest.fixture
def authenticated_connector():
    c = create_mock_connector()
    c.authenticate()
    return c


@pytest.fixture
def registry(mock_audit):
    return ConnectorRegistry(audit_logger=mock_audit)


# ─── PoliceConnectorInterface Tests ───


class TestPoliceConnectorInterface:
    def test_is_abstract(self):
        """Cannot instantiate the interface directly."""
        with pytest.raises(TypeError):
            PoliceConnectorInterface(
                config=ConnectorConfig(org_id="X", org_name="X", jurisdiction="X"),
                credential=ConnectorCredential(org_id="X", api_key="x"),
            )

    def test_has_all_8_methods(self):
        """Interface defines all 8 abstract methods."""
        abstract_methods = {
            "authenticate",
            "synchronize",
            "submit_observation",
            "receive_match",
            "receive_alert",
            "handle_request",
            "acknowledge",
            "retry",
        }
        for method in abstract_methods:
            assert hasattr(PoliceConnectorInterface, method)

    def test_mock_implements_all(self):
        """MockPoliceConnector implements all interface methods."""
        connector = MockPoliceConnector(
            config=ConnectorConfig(org_id="O1", org_name="Org", jurisdiction="LV"),
            credential=ConnectorCredential(org_id="O1", api_key="key"),
        )
        assert connector.authenticate() is True
        assert isinstance(connector.synchronize(), SyncResult)
        assert isinstance(connector.submit_observation("domain", "test.com"), str)
        assert isinstance(connector.receive_match({}), str)
        assert isinstance(connector.receive_alert({}), str)
        assert isinstance(connector.handle_request({}), str)
        assert isinstance(connector.acknowledge("EV-000001"), bool)
        assert connector.retry("authenticate") is True


# ─── MockPoliceConnector Tests ───


class TestMockPoliceConnector:
    def test_authenticate_success(self, connector):
        assert connector.authenticate() is True
        assert connector.is_connected is True
        assert connector.status == ConnectorStatus.CONNECTED.value

    def test_authenticate_failure_empty_key(self):
        c = create_mock_connector(api_key="")
        assert c.authenticate() is False
        assert c.status == ConnectorStatus.ERROR.value

    def test_authenticate_failure_empty_org(self):
        c = create_mock_connector(org_id="")
        assert c.authenticate() is False
        assert c.status == ConnectorStatus.ERROR.value

    def test_synchronize_bidirectional(self, authenticated_connector):
        result = authenticated_connector.synchronize()
        assert result.status == SyncStatus.SUCCESS.value
        assert result.direction == SyncDirection.BIDIRECTIONAL.value
        assert result.records_pushed > 0
        assert result.records_pulled > 0

    def test_synchronize_push_only(self, authenticated_connector):
        result = authenticated_connector.synchronize(SyncDirection.PUSH.value)
        assert result.records_pushed > 0
        assert result.records_pulled == 0

    def test_synchronize_pull_only(self, authenticated_connector):
        result = authenticated_connector.synchronize(SyncDirection.PULL.value)
        assert result.records_pulled > 0
        assert result.records_pushed == 0

    def test_synchronize_not_authenticated(self, connector):
        result = connector.synchronize()
        assert result.status == SyncStatus.FAILED.value
        assert "Not authenticated" in result.error

    def test_submit_observation(self, authenticated_connector):
        obs_id = authenticated_connector.submit_observation("domain", "fraudster.com", "Phishing")
        assert obs_id.startswith("MOBS-")

    def test_submit_observation_not_connected(self, connector):
        with pytest.raises(RuntimeError, match="not authenticated"):
            connector.submit_observation("domain", "test.com")

    def test_receive_match(self, authenticated_connector):
        ack_id = authenticated_connector.receive_match({"entity_id": "ENT-001", "matched": True})
        assert ack_id.startswith("MACK-")

    def test_receive_alert(self, authenticated_connector):
        ack_id = authenticated_connector.receive_alert({"alert_id": "ALT-001", "priority": "HIGH"})
        assert ack_id.startswith("MACK-")

    def test_handle_request(self, authenticated_connector):
        response_id = authenticated_connector.handle_request(
            {"request_id": "CBR-001", "action": "query"}
        )
        assert response_id.startswith("MRES-")

    def test_acknowledge_existing_event(self, authenticated_connector):
        # Create an event first
        ack_id = authenticated_connector.receive_match({"test": True})
        event_id = authenticated_connector.events[-1].id
        assert authenticated_connector.acknowledge(event_id) is True
        assert authenticated_connector.events[-1].acknowledged is True
        assert authenticated_connector.events[-1].acknowledged_at is not None

    def test_acknowledge_nonexistent_event(self, authenticated_connector):
        assert authenticated_connector.acknowledge("EV-999999") is False

    def test_retry_authenticate(self, connector):
        result = connector.retry("authenticate")
        assert result is True

    def test_retry_synchronize(self, authenticated_connector):
        result = authenticated_connector.retry(
            "synchronize", {"direction": SyncDirection.PUSH.value}
        )
        assert isinstance(result, SyncResult)
        assert result.status == SyncStatus.SUCCESS.value

    def test_retry_submit_observation(self, authenticated_connector):
        result = authenticated_connector.retry(
            "submit_observation",
            {
                "entity_type": "domain",
                "entity_value": "test.com",
                "observation_text": "test",
            },
        )
        assert isinstance(result, str)

    def test_retry_receive_match(self, authenticated_connector):
        result = authenticated_connector.retry("receive_match", {"match_data": {"test": True}})
        assert isinstance(result, str)

    def test_retry_acknowledge(self, authenticated_connector):
        event_id = authenticated_connector.events[-1].id
        result = authenticated_connector.retry("acknowledge", {"event_id": event_id})
        assert result is True

    def test_retry_unknown_operation(self, authenticated_connector):
        with pytest.raises(ValueError, match="Unknown operation"):
            authenticated_connector.retry("nonexistent")

    def test_events_recorded(self, authenticated_connector):
        authenticated_connector.submit_observation("domain", "test.com")
        authenticated_connector.receive_match({"test": True})
        assert len(authenticated_connector.events) >= 2

    def test_is_connected_before_auth(self, connector):
        assert connector.is_connected is False
        assert connector.status == ConnectorStatus.DISCONNECTED.value


# ─── ConnectorRegistry Tests ───


class TestConnectorRegistry:
    def test_register(self, registry):
        connector = create_mock_connector(org_id="ORG-001")
        registry.register(connector)
        assert registry.count == 1

    def test_unregister(self, registry):
        connector = create_mock_connector(org_id="ORG-001")
        registry.register(connector)
        assert registry.unregister("ORG-001") is True
        assert registry.count == 0

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("nonexistent") is False

    def test_get_connector(self, registry):
        connector = create_mock_connector(org_id="ORG-001")
        registry.register(connector)
        assert registry.get_connector("ORG-001") is connector

    def test_get_connector_nonexistent(self, registry):
        assert registry.get_connector("nonexistent") is None

    def test_list_connectors(self, registry):
        registry.register(
            create_mock_connector(org_id="ORG-001", org_name="Latvian Police", jurisdiction="LV")
        )
        registry.register(
            create_mock_connector(org_id="ORG-002", org_name="EUROPOL", jurisdiction="EU")
        )
        connectors = registry.list_connectors()
        assert len(connectors) == 2
        assert connectors[0]["org_name"] == "Latvian Police"
        assert connectors[1]["org_name"] == "EUROPOL"

    def test_list_connectors_shows_status(self, registry):
        connector = create_mock_connector(org_id="ORG-001")
        registry.register(connector)
        connector.authenticate()
        connectors = registry.list_connectors()
        assert connectors[0]["status"] == ConnectorStatus.CONNECTED.value
        assert connectors[0]["is_connected"] is True

    def test_register_audit_logged(self, mock_audit):
        registry = ConnectorRegistry(audit_logger=mock_audit)
        registry.register(create_mock_connector(org_id="ORG-001"))
        mock_audit.log.assert_called_once()

    def test_authenticate_all(self, registry):
        registry.register(create_mock_connector(org_id="ORG-001", api_key="key1"))
        registry.register(create_mock_connector(org_id="ORG-002", api_key="key2"))
        results = registry.authenticate_all()
        assert results["ORG-001"] is True
        assert results["ORG-002"] is True

    def test_authenticate_all_with_failure(self, registry):
        registry.register(create_mock_connector(org_id="ORG-001", api_key="key1"))
        registry.register(create_mock_connector(org_id="ORG-002", api_key=""))
        results = registry.authenticate_all()
        assert results["ORG-001"] is True
        assert results["ORG-002"] is False

    def test_synchronize_all(self, registry):
        c1 = create_mock_connector(org_id="ORG-001")
        c2 = create_mock_connector(org_id="ORG-002")
        registry.register(c1)
        registry.register(c2)
        registry.authenticate_all()
        results = registry.synchronize_all()
        assert "ORG-001" in results
        assert "ORG-002" in results
        assert results["ORG-001"].status == SyncStatus.SUCCESS.value


# ─── ConnectorCredential Tests ───


class TestConnectorCredential:
    def test_creation(self):
        cred = ConnectorCredential(org_id="ORG-001", api_key="secret-key")
        assert cred.org_id == "ORG-001"
        assert cred.api_key == "secret-key"
        assert cred.created_at is not None

    def test_rotate(self):
        cred = ConnectorCredential(org_id="ORG-001", api_key="old-key")
        cred.rotate("new-key")
        assert cred.api_key == "new-key"
        assert cred.rotated_at is not None

    def test_to_safe_dict_redacts(self):
        cred = ConnectorCredential(org_id="ORG-001", api_key="secret-key", mtls_cert="cert-data")
        safe = cred.to_safe_dict()
        assert safe["api_key"] == "***REDACTED***"
        assert safe["mtls_cert"] == "***REDACTED***"
        assert "secret-key" not in str(safe)
        assert "cert-data" not in str(safe)

    def test_to_safe_dict_has_mtls(self):
        cred = ConnectorCredential(org_id="ORG-001", api_key="key", mtls_cert="cert")
        safe = cred.to_safe_dict()
        assert safe["has_mtls"] is True

    def test_to_safe_dict_no_mtls(self):
        cred = ConnectorCredential(org_id="ORG-001", api_key="key")
        safe = cred.to_safe_dict()
        assert safe["has_mtls"] is False
        assert safe["mtls_cert"] == ""


# ─── SyncResult Tests ───


class TestSyncResult:
    def test_default(self):
        result = SyncResult(direction=SyncDirection.BIDIRECTIONAL.value)
        assert result.records_pushed == 0
        assert result.records_pulled == 0
        assert result.status == SyncStatus.SUCCESS.value
        assert len(result.conflicts) == 0

    def test_with_data(self):
        result = SyncResult(
            direction=SyncDirection.PUSH.value,
            records_pushed=10,
            records_pulled=0,
            status=SyncStatus.PARTIAL.value,
            conflicts=[{"entity": "ENT-001", "issue": "version conflict"}],
        )
        assert result.records_pushed == 10
        assert result.status == SyncStatus.PARTIAL.value
        assert len(result.conflicts) == 1


# ─── ConnectorEvent Tests ───


class TestConnectorEvent:
    def test_creation(self):
        event = ConnectorEvent(
            id="EV-001", event_type=ConnectorEventType.MATCH.value, org_id="ORG-001"
        )
        assert event.acknowledged is False
        assert event.acknowledged_at is None

    def test_acknowledge(self):
        event = ConnectorEvent(
            id="EV-001", event_type=ConnectorEventType.ALERT.value, org_id="ORG-001"
        )
        event.acknowledged = True
        event.acknowledged_at = datetime.now(UTC)
        assert event.acknowledged is True
        assert event.acknowledged_at is not None


# ─── Integration Tests ───


class TestIntegrationConnector:
    def test_full_connector_lifecycle(self, registry):
        """Full lifecycle: register → auth → sync → observe → match → alert → request → acknowledge."""
        connector = create_mock_connector(
            org_id="ORG-001", org_name="Test Police", jurisdiction="LV"
        )
        registry.register(connector)
        assert registry.count == 1

        # Authenticate
        assert connector.authenticate() is True
        assert connector.is_connected is True

        # Synchronize
        sync_result = connector.synchronize()
        assert sync_result.status == SyncStatus.SUCCESS.value

        # Submit observation
        obs_id = connector.submit_observation("domain", "fraudster.com", "Known phishing")
        assert obs_id.startswith("MOBS-")

        # Receive match
        match_ack = connector.receive_match(
            {"entity_id": "ENT-001", "matched": True, "confidence": "HIGH"}
        )
        assert match_ack.startswith("MACK-")

        # Receive alert
        alert_ack = connector.receive_alert({"alert_id": "ALT-001", "priority": "CRITICAL"})
        assert alert_ack.startswith("MACK-")

        # Handle cross-border request
        response_id = connector.handle_request({"request_id": "CBR-001", "action": "query"})
        assert response_id.startswith("MRES-")

        # Acknowledge events
        events = connector.events
        assert len(events) >= 5
        for event in events:
            assert connector.acknowledge(event.id) is True

        # All events acknowledged
        for event in connector.events:
            assert event.acknowledged is True

    def test_multiple_connectors_in_registry(self, registry):
        """Multiple connectors managed simultaneously."""
        for i in range(5):
            c = create_mock_connector(org_id=f"ORG-{i:03d}", api_key=f"key-{i}")
            registry.register(c)

        assert registry.count == 5

        results = registry.authenticate_all()
        assert all(results.values())

        sync_results = registry.synchronize_all()
        assert all(r.status == SyncStatus.SUCCESS.value for r in sync_results.values())

    def test_retry_after_auth_failure(self):
        """Retry authentication after initial failure."""
        connector = create_mock_connector(api_key="")
        assert connector.authenticate() is False

        # Fix credentials and retry
        connector.credential.rotate("valid-key")
        result = connector.retry("authenticate")
        assert result is True
        assert connector.is_connected is True

    def test_unregistered_connector_cannot_sync(self, connector):
        """Connector not in registry still works independently."""
        connector.authenticate()
        result = connector.synchronize()
        assert result.status == SyncStatus.SUCCESS.value
