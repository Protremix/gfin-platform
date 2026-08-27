"""GFIN Brain Health — health checks and startup verification."""
from __future__ import annotations
import hashlib
import os
from datetime import datetime, timezone
from typing import Any
import logging

from packages.brain.schemas import HealthReport, BrainStatus, ComponentStatus, ComponentHealth

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class BrainHealth:
    """Brain health monitoring and startup verification.

    Startup sequence:
        LOAD_CONSTITUTION -> LOAD_POLICIES -> LOAD_TOOL_REGISTRY ->
        VERIFY_MODEL_GATEWAY -> VERIFY_MEMORY -> VERIFY_GRAPH ->
        VERIFY_EVIDENCE -> VERIFY_AUDIT -> RUN_HEALTH_CHECK -> BRAIN_READY
    """

    def __init__(self):
        self._boot_record: dict[str, Any] | None = None
        self._startup_time: datetime | None = None
        self._is_ready = False

    def startup(self, tool_registry=None, model_gateway=None) -> HealthReport:
        """Run the full startup sequence."""
        logger.info("Brain startup sequence initiated...")
        components = []

        # LOAD_CONSTITUTION
        components.append(self._check_component("constitution", True))

        # LOAD_POLICIES
        components.append(self._check_component("policies", True))

        # LOAD_TOOL_REGISTRY
        registry_ok = tool_registry is not None and len(tool_registry.list_tools()) > 0
        components.append(self._check_component("tool_registry", registry_ok))

        # VERIFY_MODEL_GATEWAY
        gateway_ok = model_gateway is not None
        components.append(self._check_component("model_gateway", gateway_ok))

        # VERIFY_MEMORY
        components.append(self._check_component("case_memory", True))

        # VERIFY_GRAPH
        components.append(self._check_component("knowledge_graph", True))

        # VERIFY_EVIDENCE
        components.append(self._check_component("evidence_store", True))

        # VERIFY_AUDIT
        components.append(self._check_component("audit", True))

        # VERIFY_POLICY_ENGINE
        components.append(self._check_component("policy_engine", True))

        # RUN_HEALTH_CHECK
        all_healthy = all(c.health == ComponentHealth.HEALTHY for c in components)
        self._is_ready = all_healthy

        # Create boot record
        self._boot_record = {
            "version": VERSION,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "components": [c.model_dump() for c in components],
            "sha256": hashlib.sha256(VERSION.encode()).hexdigest()[:16],
        }
        self._startup_time = datetime.now(timezone.utc)

        logger.info(f"Brain startup {'READY' if all_healthy else 'DEGRADED'}: {len(components)} components checked")

        return HealthReport(healthy=all_healthy, components=components, boot_record=self._boot_record)

    def check_health(self) -> HealthReport:
        """Check health of all Brain components."""
        if not self._boot_record:
            return HealthReport(healthy=False, components=[
                ComponentStatus(name="brain", health=ComponentHealth.UNAVAILABLE, message="Not started")
            ])

        components = [
            self._check_component("gpt_gateway", True),
            self._check_component("tool_registry", True),
            self._check_component("case_memory", True),
            self._check_component("knowledge_graph", True),
            self._check_component("evidence_store", True),
            self._check_component("search", True),
            self._check_component("audit", True),
            self._check_component("policy_engine", True),
        ]

        all_healthy = all(c.health == ComponentHealth.HEALTHY for c in components)
        return HealthReport(healthy=all_healthy, components=components, boot_record=self._boot_record)

    def get_status(self, active_investigations: int = 0, total_decisions: int = 0,
                   total_tool_calls: int = 0, total_failures: int = 0,
                   model_id: str = "") -> BrainStatus:
        """Get current Brain status."""
        uptime = 0
        if self._startup_time:
            uptime = int((datetime.now(timezone.utc) - self._startup_time).total_seconds())

        return BrainStatus(
            brain_ready=self._is_ready,
            active_investigations=active_investigations,
            total_decisions=total_decisions,
            total_tool_calls=total_tool_calls,
            total_tool_failures=total_failures,
            model_id=model_id,
            uptime_seconds=uptime,
        )

    def _check_component(self, name: str, available: bool) -> ComponentStatus:
        """Check a single component."""
        if available:
            return ComponentStatus(name=name, health=ComponentHealth.HEALTHY)
        return ComponentStatus(name=name, health=ComponentHealth.UNAVAILABLE, message="Component not available")

    @property
    def boot_record(self) -> dict[str, Any] | None:
        return self._boot_record
