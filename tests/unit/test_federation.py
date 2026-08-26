"""Tests for Federation — Module 32."""

from unittest.mock import MagicMock

import pytest

from services.federation import (
    DeliveryStatus,
    FederationNetwork,
    FederationNode,
    MessageType,
    NodeStatus,
)


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def network(mock_audit):
    return FederationNetwork(audit_logger=mock_audit)


@pytest.fixture
def populated_network(network):
    network.register_node("LV", "Latvian Police", capabilities=["match", "alert"])
    network.register_node("DE", "BKA", capabilities=["match", "alert", "request"])
    network.register_node("FR", "DGSI", capabilities=["match"])
    # Set all online
    for n in network.list_nodes():
        network.set_node_status(n.node_id, NodeStatus.ONLINE.value)
    return network


# ─── FederationNode Tests ───


class TestFederationNode:
    def test_creation(self):
        node = FederationNode(node_id="N1", jurisdiction="LV", organization="Latvian Police")
        assert node.status == NodeStatus.OFFLINE.value
        assert node.is_online is False

    def test_go_online(self):
        node = FederationNode(node_id="N1", jurisdiction="LV", organization="Org")
        node.go_online()
        assert node.is_online is True
        assert node.last_heartbeat is not None

    def test_go_offline(self):
        node = FederationNode(node_id="N1", jurisdiction="LV", organization="Org")
        node.go_online()
        node.go_offline()
        assert node.is_online is False

    def test_go_degraded(self):
        node = FederationNode(node_id="N1", jurisdiction="LV", organization="Org")
        node.go_online()
        node.go_degraded()
        assert node.status == NodeStatus.DEGRADED.value

    def test_heartbeat(self):
        node = FederationNode(node_id="N1", jurisdiction="LV", organization="Org")
        node.go_online()
        old_hb = node.last_heartbeat
        node.heartbeat()
        assert node.last_heartbeat is not old_hb


# ─── FederationNetwork Tests ───


class TestFederationNetwork:
    def test_register_node(self, network):
        node = network.register_node("LV", "Latvian Police")
        assert node.node_id.startswith("NODE-")
        assert network.node_count == 1

    def test_remove_node(self, network):
        node = network.register_node("LV", "Org")
        assert network.remove_node(node.node_id) is True
        assert network.node_count == 0

    def test_remove_nonexistent(self, network):
        assert network.remove_node("nonexistent") is False

    def test_get_node(self, network):
        node = network.register_node("LV", "Org")
        assert network.get_node(node.node_id) is not None
        assert network.get_node("nonexistent") is None

    def test_get_node_by_jurisdiction(self, network):
        network.register_node("LV", "Org")
        assert network.get_node_by_jurisdiction("LV") is not None
        assert network.get_node_by_jurisdiction("DE") is None

    def test_list_nodes(self, populated_network):
        nodes = populated_network.list_nodes()
        assert len(nodes) == 3

    def test_list_nodes_filtered(self, populated_network):
        # Set one offline
        nodes = populated_network.list_nodes()
        populated_network.set_node_status(nodes[0].node_id, NodeStatus.OFFLINE.value)
        online = populated_network.list_nodes(status=NodeStatus.ONLINE.value)
        assert len(online) == 2

    def test_set_node_status(self, network):
        node = network.register_node("LV", "Org")
        assert network.set_node_status(node.node_id, NodeStatus.ONLINE.value) is True
        assert node.is_online is True
        assert network.set_node_status(node.node_id, NodeStatus.OFFLINE.value) is True
        assert node.is_online is False

    def test_set_invalid_status(self, network):
        node = network.register_node("LV", "Org")
        assert network.set_node_status(node.node_id, "INVALID") is False

    def test_send_heartbeat(self, network):
        node = network.register_node("LV", "Org")
        node.go_online()
        old_hb = node.last_heartbeat
        assert network.send_heartbeat(node.node_id) is True
        assert node.last_heartbeat is not old_hb

    def test_send_heartbeat_nonexistent(self, network):
        assert network.send_heartbeat("nonexistent") is False


# ─── Messaging Tests ───


class TestFederationMessaging:
    def test_send_message_delivered(self, populated_network):
        msg = populated_network.send_message(
            MessageType.MATCH.value, "LV", "DE", {"entity_id": "ENT-001"}
        )
        assert msg.delivery_status == DeliveryStatus.DELIVERED.value
        assert msg.delivered_at is not None

    def test_send_message_target_offline(self, populated_network):
        de_node = populated_network.get_node_by_jurisdiction("DE")
        populated_network.set_node_status(de_node.node_id, NodeStatus.OFFLINE.value)
        msg = populated_network.send_message(MessageType.ALERT.value, "LV", "DE")
        assert msg.delivery_status == DeliveryStatus.FAILED.value

    def test_send_message_no_target_node(self, populated_network):
        msg = populated_network.send_message(MessageType.REQUEST.value, "LV", "IT")
        assert msg.delivery_status == DeliveryStatus.REJECTED.value

    def test_acknowledge_message(self, populated_network):
        msg = populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        assert populated_network.acknowledge_message(msg.id) is True
        assert msg.acknowledged_at is not None

    def test_acknowledge_non_delivered(self, populated_network):
        msg = populated_network.send_message(MessageType.REQUEST.value, "LV", "IT")
        assert msg.delivery_status == DeliveryStatus.REJECTED.value
        assert populated_network.acknowledge_message(msg.id) is False

    def test_acknowledge_nonexistent(self, network):
        assert network.acknowledge_message("nonexistent") is False

    def test_get_message(self, populated_network):
        msg = populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        assert populated_network.get_message(msg.id) is not None
        assert populated_network.get_message("nonexistent") is None

    def test_get_messages_filtered(self, populated_network):
        populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        populated_network.send_message(MessageType.ALERT.value, "LV", "FR")
        populated_network.send_message(MessageType.MATCH.value, "DE", "LV")
        de_messages = populated_network.get_messages(target_jurisdiction="DE")
        assert len(de_messages) == 1
        match_messages = populated_network.get_messages(msg_type=MessageType.MATCH.value)
        assert len(match_messages) == 2

    def test_message_count(self, populated_network):
        populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        assert populated_network.message_count == 1


# ─── Topology Tests ───


class TestTopology:
    def test_get_topology(self, populated_network):
        topo = populated_network.get_topology()
        assert len(topo) == 3
        assert topo[0]["jurisdiction"] == "LV"
        assert topo[1]["jurisdiction"] == "DE"

    def test_topology_has_status(self, populated_network):
        topo = populated_network.get_topology()
        assert topo[0]["status"] == NodeStatus.ONLINE.value

    def test_topology_has_capabilities(self, populated_network):
        topo = populated_network.get_topology()
        assert "match" in topo[0]["capabilities"]


# ─── Audit Tests ───


class TestFederationAudit:
    def test_audit_logged_on_register(self, mock_audit):
        net = FederationNetwork(audit_logger=mock_audit)
        net.register_node("LV", "Org")
        mock_audit.log.assert_called_once()

    def test_audit_entries_tracked(self, network):
        network.register_node("LV", "Org")
        log = network.get_audit_log()
        assert len(log) == 1
        assert log[0].operation == "register_node"

    def test_audit_on_message(self, populated_network):
        populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        log = populated_network.get_audit_log()
        assert any(e.operation == "send_message" for e in log)

    def test_audit_on_acknowledge(self, populated_network):
        msg = populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        populated_network.acknowledge_message(msg.id)
        log = populated_network.get_audit_log()
        assert any(e.operation == "ack_message" for e in log)


# ─── Integration Tests ───


class TestIntegrationFederation:
    def test_full_federation_flow(self, network):
        """Full flow: register nodes → go online → send messages → acknowledge."""
        lv = network.register_node("LV", "Latvian Police", capabilities=["match"])
        de = network.register_node("DE", "BKA", capabilities=["match", "request"])
        fr = network.register_node("FR", "DGSI", capabilities=["match"])

        network.set_node_status(lv.node_id, NodeStatus.ONLINE.value)
        network.set_node_status(de.node_id, NodeStatus.ONLINE.value)
        network.set_node_status(fr.node_id, NodeStatus.ONLINE.value)

        # LV sends match to DE
        msg = network.send_message(MessageType.MATCH.value, "LV", "DE", {"entity_id": "ENT-001"})
        assert msg.delivery_status == DeliveryStatus.DELIVERED.value
        assert network.acknowledge_message(msg.id) is True

        # DE sends request to FR
        msg2 = network.send_message(MessageType.REQUEST.value, "DE", "FR")
        assert msg2.delivery_status == DeliveryStatus.DELIVERED.value

        # Verify topology
        topo = network.get_topology()
        assert len(topo) == 3
        assert all(t["status"] == NodeStatus.ONLINE.value for t in topo)

        # Verify audit trail
        log = network.get_audit_log()
        assert len(log) >= 5

    def test_degraded_node_receives_messages(self, populated_network):
        """Degraded nodes can still receive messages (only offline rejects)."""
        de_node = populated_network.get_node_by_jurisdiction("DE")
        populated_network.set_node_status(de_node.node_id, NodeStatus.DEGRADED.value)
        msg = populated_network.send_message(MessageType.MATCH.value, "LV", "DE")
        assert msg.delivery_status == DeliveryStatus.DELIVERED.value
