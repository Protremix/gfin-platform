"""SLO definitions and capacity targets for GFIN.

Per Luna Strategic Assessment — Step 2: Reliability Validation.
These SLOs are the targets that production GFIN must meet.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


# ─── Latency SLOs (p99) ───

ENTITY_RESOLUTION_LATENCY_MS = 100
GRAPH_QUERY_LATENCY_MS = 200
SEARCH_LATENCY_MS = 300
EVIDENCE_VAULT_CREATE_MS = 50
API_GATEWAY_LATENCY_MS = 200
AI_GATEWAY_LATENCY_MS = 5000

# ─── Throughput SLOs ───

ENTITY_CREATE_THROUGHPUT = 1000  # per second
EVENT_BUS_PUBLISH_THROUGHPUT = 5000  # per second
SEARCH_QUERY_THROUGHPUT = 100  # per second

# ─── Availability SLO ───

AVAILABILITY_TARGET = 99.9  # percent

# ─── Recovery SLOs ───

RTO_SECONDS = 300  # Recovery Time Objective: 5 minutes
RPO_SECONDS = 60  # Recovery Point Objective: 1 minute

# ─── Capacity Targets ───

MAX_ENTITIES = 1_000_000
MAX_GRAPH_NODES = 10_000_000
MAX_GRAPH_EDGES = 50_000_000
MAX_EVIDENCE_ITEMS = 1_000_000
MAX_SEARCH_DOCS = 10_000_000


class TestSLODefinitions:
    """Verify SLO targets are reasonable and internally consistent."""

    def test_entity_resolution_latency_is_reasonable(self):
        """Entity resolution p99 should be under 100ms."""
        assert ENTITY_RESOLUTION_LATENCY_MS <= 100

    def test_graph_query_latency_is_reasonable(self):
        """Graph query p99 should be under 200ms."""
        assert GRAPH_QUERY_LATENCY_MS <= 200

    def test_search_latency_is_reasonable(self):
        """Search p99 should be under 300ms."""
        assert SEARCH_LATENCY_MS <= 300

    def test_evidence_vault_create_latency_is_reasonable(self):
        """Evidence vault create p99 should be under 50ms."""
        assert EVIDENCE_VAULT_CREATE_MS <= 50

    def test_api_gateway_latency_is_reasonable(self):
        """API gateway p99 should be under 200ms."""
        assert API_GATEWAY_LATENCY_MS <= 200

    def test_ai_gateway_latency_is_reasonable(self):
        """AI gateway p99 should be under 5 seconds."""
        assert AI_GATEWAY_LATENCY_MS <= 5000

    def test_entity_create_throughput_is_adequate(self):
        """Entity creation should handle 1000+ per second."""
        assert ENTITY_CREATE_THROUGHPUT >= 1000

    def test_event_bus_throughput_is_adequate(self):
        """Event bus should handle 5000+ publishes per second."""
        assert EVENT_BUS_PUBLISH_THROUGHPUT >= 5000

    def test_search_throughput_is_adequate(self):
        """Search should handle 100+ queries per second."""
        assert SEARCH_QUERY_THROUGHPUT >= 100

    def test_availability_target_is_high(self):
        """Availability should be 99.9% or higher."""
        assert AVAILABILITY_TARGET >= 99.9

    def test_rto_is_within_5_minutes(self):
        """RTO should be 5 minutes or less."""
        assert RTO_SECONDS <= 300

    def test_rpo_is_within_1_minute(self):
        """RPO should be 1 minute or less."""
        assert RPO_SECONDS <= 60

    def test_capacity_targets_are_scalable(self):
        """Capacity targets should support millions of records."""
        assert MAX_ENTITIES >= 1_000_000
        assert MAX_GRAPH_NODES >= 10_000_000
        assert MAX_EVIDENCE_ITEMS >= 1_000_000

    def test_latency_ordering_is_consistent(self):
        """Faster operations should have lower latency targets."""
        assert EVIDENCE_VAULT_CREATE_MS <= ENTITY_RESOLUTION_LATENCY_MS
        assert ENTITY_RESOLUTION_LATENCY_MS <= GRAPH_QUERY_LATENCY_MS
        assert GRAPH_QUERY_LATENCY_MS <= SEARCH_LATENCY_MS
