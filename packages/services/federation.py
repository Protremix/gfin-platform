"""GFIN Federation — Module 32.

Federation protocol for national GFIN nodes. Per Architecture Review §6:
event-driven, each node controls its data, global platform stores only
permitted metadata.

Layer A: In-memory node network and message routing
Layer B: Kafka federation streaming, mTLS, cross-DC replication (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class NodeStatus(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"


class MessageType(StrEnum):
    MATCH = "MATCH"
    ALERT = "ALERT"
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    SYNC = "SYNC"
    DISCOVERY = "DISCOVERY"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


# ─── Models ───


class FederationNode(BaseModel):
    """A national GFIN node."""

    node_id: str
    jurisdiction: str
    organization: str
    endpoint: str = ""
    status: str = NodeStatus.OFFLINE.value
    capabilities: list[str] = Field(default_factory=list)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime | None = None

    def go_online(self) -> None:
        self.status = NodeStatus.ONLINE.value
        self.last_heartbeat = datetime.now(UTC)

    def go_offline(self) -> None:
        self.status = NodeStatus.OFFLINE.value

    def go_degraded(self) -> None:
        self.status = NodeStatus.DEGRADED.value
        self.last_heartbeat = datetime.now(UTC)

    def heartbeat(self) -> None:
        self.last_heartbeat = datetime.now(UTC)

    @property
    def is_online(self) -> bool:
        return self.status == NodeStatus.ONLINE.value


class FederationMessage(BaseModel):
    """A message between federation nodes."""

    id: str
    msg_type: str
    source_jurisdiction: str
    target_jurisdiction: str
    source_node_id: str = ""
    target_node_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    delivery_status: str = DeliveryStatus.PENDING.value
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivered_at: datetime | None = None
    acknowledged_at: datetime | None = None

    def mark_delivered(self) -> None:
        self.delivery_status = DeliveryStatus.DELIVERED.value
        self.delivered_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.delivery_status = DeliveryStatus.FAILED.value

    def mark_rejected(self) -> None:
        self.delivery_status = DeliveryStatus.REJECTED.value

    def acknowledge(self) -> None:
        self.acknowledged_at = datetime.now(UTC)


class FederationAuditEntry(BaseModel):
    """Audit entry for a federation operation."""

    id: str
    operation: str
    node_id: str = ""
    message_id: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Federation Network ───


class FederationNetwork:
    """Manages the federation of GFIN nodes.

    Per Architecture Review §6.4: each national node controls its data.
    The network handles node registration, discovery, and messaging.
    """

    def __init__(self, audit_logger: Any | None = None) -> None:
        self._nodes: dict[str, FederationNode] = {}  # node_id → node
        self._jurisdiction_map: dict[str, str] = {}  # jurisdiction → node_id
        self._messages: dict[str, FederationMessage] = {}
        self._audit_entries: list[FederationAuditEntry] = []
        self._node_counter = 0
        self._msg_counter = 0
        self._audit_counter = 0
        self._audit_logger = audit_logger

    def register_node(
        self,
        jurisdiction: str,
        organization: str,
        endpoint: str = "",
        capabilities: list[str] | None = None,
    ) -> FederationNode:
        """Register a new federation node."""
        self._node_counter += 1
        node = FederationNode(
            node_id=f"NODE-{self._node_counter:06d}",
            jurisdiction=jurisdiction,
            organization=organization,
            endpoint=endpoint,
            capabilities=capabilities or [],
        )
        self._nodes[node.node_id] = node
        self._jurisdiction_map[jurisdiction] = node.node_id
        self._log_audit(
            "register_node", node_id=node.node_id, details={"jurisdiction": jurisdiction}
        )
        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the federation."""
        node = self._nodes.pop(node_id, None)
        if node is None:
            return False
        self._jurisdiction_map.pop(node.jurisdiction, None)
        self._log_audit("remove_node", node_id=node_id)
        return True

    def get_node(self, node_id: str) -> FederationNode | None:
        return self._nodes.get(node_id)

    def get_node_by_jurisdiction(self, jurisdiction: str) -> FederationNode | None:
        node_id = self._jurisdiction_map.get(jurisdiction)
        if node_id is None:
            return None
        return self._nodes.get(node_id)

    def list_nodes(self, status: str | None = None) -> list[FederationNode]:
        nodes = list(self._nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def set_node_status(self, node_id: str, status: str) -> bool:
        """Set a node's status."""
        node = self._nodes.get(node_id)
        if node is None:
            return False
        if status == NodeStatus.ONLINE.value:
            node.go_online()
        elif status == NodeStatus.OFFLINE.value:
            node.go_offline()
        elif status == NodeStatus.DEGRADED.value:
            node.go_degraded()
        else:
            return False
        self._log_audit("set_status", node_id=node_id, details={"status": status})
        return True

    def send_heartbeat(self, node_id: str) -> bool:
        """Send a heartbeat from a node."""
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.heartbeat()
        return True

    def send_message(
        self,
        msg_type: str,
        source_jurisdiction: str,
        target_jurisdiction: str,
        payload: dict[str, Any] | None = None,
    ) -> FederationMessage:
        """Send a message between nodes."""
        self._msg_counter += 1
        source_node = self.get_node_by_jurisdiction(source_jurisdiction)
        target_node = self.get_node_by_jurisdiction(target_jurisdiction)

        msg = FederationMessage(
            id=f"FMSG-{self._msg_counter:06d}",
            msg_type=msg_type,
            source_jurisdiction=source_jurisdiction,
            target_jurisdiction=target_jurisdiction,
            source_node_id=source_node.node_id if source_node else "",
            target_node_id=target_node.node_id if target_node else "",
            payload=payload or {},
        )

        # Delivery logic
        if target_node is None:
            msg.mark_rejected()
        elif target_node.status == NodeStatus.OFFLINE.value:
            msg.mark_failed()
        else:
            msg.mark_delivered()

        self._messages[msg.id] = msg
        self._log_audit(
            "send_message",
            message_id=msg.id,
            details={
                "type": msg_type,
                "source": source_jurisdiction,
                "target": target_jurisdiction,
                "delivery": msg.delivery_status,
            },
        )

        return msg

    def get_message(self, msg_id: str) -> FederationMessage | None:
        return self._messages.get(msg_id)

    def acknowledge_message(self, msg_id: str) -> bool:
        """Acknowledge receipt of a message."""
        msg = self._messages.get(msg_id)
        if msg is None or msg.delivery_status != DeliveryStatus.DELIVERED.value:
            return False
        msg.acknowledge()
        self._log_audit("ack_message", message_id=msg_id)
        return True

    def get_messages(
        self,
        target_jurisdiction: str | None = None,
        msg_type: str | None = None,
    ) -> list[FederationMessage]:
        """Get messages with optional filters."""
        msgs = list(self._messages.values())
        if target_jurisdiction:
            msgs = [m for m in msgs if m.target_jurisdiction == target_jurisdiction]
        if msg_type:
            msgs = [m for m in msgs if m.msg_type == msg_type]
        return msgs

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def get_topology(self) -> list[dict[str, Any]]:
        """Get the network topology."""
        return [
            {
                "node_id": n.node_id,
                "jurisdiction": n.jurisdiction,
                "organization": n.organization,
                "status": n.status,
                "capabilities": n.capabilities,
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            }
            for n in self._nodes.values()
        ]

    def _log_audit(
        self,
        operation: str,
        node_id: str = "",
        message_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit_counter += 1
        entry = FederationAuditEntry(
            id=f"FAUDIT-{self._audit_counter:06d}",
            operation=operation,
            node_id=node_id,
            message_id=message_id,
            details=details or {},
        )
        self._audit_entries.append(entry)

        if self._audit_logger:
            with contextlib.suppress(Exception):
                self._audit_logger.log(
                    user_id="system",
                    action=f"federation.{operation}",
                    resource_type="federation",
                    resource_id=node_id or message_id,
                    details=details or {},
                )

    def get_audit_log(self) -> list[FederationAuditEntry]:
        return list(self._audit_entries)
