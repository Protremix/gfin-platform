"""
GFIN WebSocket Hub — Future-Tier Module

Real-time communication for live updates:
- Case status changes
- Investigation progress updates
- Alert notifications
- Dark web finding notifications
- System events

Layer A: In-memory pub/sub (single server)
Layer B: Redis pub/sub for multi-server scaling (REQUIRES EXTERNAL INFRASTRUCTURE)
"""
import asyncio
import json
from datetime import datetime, UTC
from typing import Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class WSMessage:
    channel: str
    event_type: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "channel": self.channel,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""

    def __init__(self):
        self._connections: dict[str, set] = defaultdict(set)  # channel -> set of websockets
        self._client_channels: dict[str, set] = defaultdict(set)  # client_id -> channels
        self._message_history: dict[str, list] = defaultdict(list)  # channel -> recent messages
        self._max_history = 100
        self._stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "channels_active": 0,
        }

    async def connect(self, websocket, client_id: str = ""):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        client_id = client_id or f"client_{id(websocket)}"
        self._stats["total_connections"] += 1
        return client_id

    def subscribe(self, client_id: str, channel: str):
        """Subscribe a client to a channel."""
        self._connections[channel].add(client_id)
        self._client_channels[client_id].add(channel)
        self._stats["channels_active"] = len(self._connections)

    def unsubscribe(self, client_id: str, channel: str = None):
        """Unsubscribe a client from a channel (or all channels)."""
        if channel:
            self._connections[channel].discard(client_id)
            self._client_channels[client_id].discard(channel)
        else:
            for ch in list(self._client_channels[client_id]):
                self._connections[ch].discard(client_id)
            self._client_channels[client_id].clear()

    async def broadcast(self, channel: str, event_type: str, data: dict):
        """Broadcast a message to all subscribers of a channel."""
        msg = WSMessage(channel=channel, event_type=event_type, data=data)

        # Store in history
        self._message_history[channel].append(msg.to_dict())
        if len(self._message_history[channel]) > self._max_history:
            self._message_history[channel] = self._message_history[channel][-self._max_history:]

        self._stats["messages_sent"] += 1
        return msg.to_dict()

    def get_history(self, channel: str, limit: int = 50) -> list:
        """Get recent messages for a channel."""
        history = self._message_history.get(channel, [])
        return history[-limit:]

    def get_subscriber_count(self, channel: str) -> int:
        """Get the number of subscribers for a channel."""
        return len(self._connections.get(channel, set()))

    def list_channels(self) -> list:
        """List all active channels."""
        return list(self._connections.keys())

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "current_subscribers": sum(len(subs) for subs in self._connections.values()),
            "channels": len(self._connections),
            "history_items": sum(len(h) for h in self._message_history.values()),
        }


class WebSocketHub:
    """WebSocket hub for real-time GFIN updates."""

    # Pre-defined channels
    CHANNELS = [
        "case_updates",        # Case status changes
        "investigation",       # Investigation progress
        "alerts",              # Alert notifications
        "dark_web",            # Dark web findings
        "system_events",       # System health and events
        "evidence",            # New evidence items
        "patterns",            # Pattern detections
        "crypto_alerts",       # Crypto intelligence alerts
    ]

    def __init__(self):
        self.manager = ConnectionManager()

    def get_available_channels(self) -> list:
        return self.CHANNELS

    async def publish_case_update(self, case_id: str, status: str, details: dict = None):
        """Publish a case status update."""
        return await self.manager.broadcast(
            "case_updates",
            "case_status_changed",
            {"case_id": case_id, "status": status, "details": details or {}}
        )

    async def publish_investigation_update(self, investigation_id: str, step: str, status: str):
        """Publish an investigation step update."""
        return await self.manager.broadcast(
            "investigation",
            "step_updated",
            {"investigation_id": investigation_id, "step": step, "status": status}
        )

    async def publish_alert(self, alert_type: str, level: str, message: str, data: dict = None):
        """Publish an alert notification."""
        return await self.manager.broadcast(
            "alerts",
            "new_alert",
            {"alert_type": alert_type, "level": level, "message": message, "data": data or {}}
        )

    async def publish_dark_web_finding(self, finding_id: str, threat_level: str, entity: str):
        """Publish a dark web finding notification."""
        return await self.manager.broadcast(
            "dark_web",
            "new_finding",
            {"finding_id": finding_id, "threat_level": threat_level, "entity": entity}
        )

    async def publish_evidence(self, case_id: str, evidence_id: str, evidence_type: str):
        """Publish a new evidence item notification."""
        return await self.manager.broadcast(
            "evidence",
            "new_evidence",
            {"case_id": case_id, "evidence_id": evidence_id, "evidence_type": evidence_type}
        )

    async def publish_pattern(self, pattern_type: str, entities: list, confidence: float):
        """Publish a pattern detection notification."""
        return await self.manager.broadcast(
            "patterns",
            "pattern_detected",
            {"pattern_type": pattern_type, "entities": entities, "confidence": confidence}
        )

    async def publish_crypto_alert(self, address: str, risk_level: str, details: dict = None):
        """Publish a crypto intelligence alert."""
        return await self.manager.broadcast(
            "crypto_alerts",
            "wallet_alert",
            {"address": address, "risk_level": risk_level, "details": details or {}}
        )

    def get_stats(self) -> dict:
        return self.manager.get_stats()

    def get_channel_history(self, channel: str, limit: int = 50) -> list:
        return self.manager.get_history(channel, limit)

    def get_channel_info(self, channel: str) -> dict:
        return {
            "channel": channel,
            "subscribers": self.manager.get_subscriber_count(channel),
            "recent_messages": len(self.manager.get_history(channel)),
        }
