# Tests for GFIN Temporal Intelligence Service
# Per Advanced Intelligence Superset Directive v1.0 §5-6

import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

from services.temporal_intelligence import (
    ConfidenceLevel,
    TemporalEvent,
    TemporalEventType,
    TemporalIntelligenceService,
)


@pytest.fixture
def service():
    return TemporalIntelligenceService()


@pytest.fixture
def base_time():
    return datetime(2026, 1, 10, 12, 0, 0)


@pytest.fixture
def domain_entity():
    return ("DOMAIN:scam-example.invalid", "DOMAIN")


@pytest.fixture
def ip_entity():
    return ("IP:192.0.2.1", "IP")


# ═══════════════════════════════════════════════
# EVENT RECORDING TESTS
# ═══════════════════════════════════════════════


class TestEventRecording:
    def test_record_event(self, service, domain_entity):
        entity_id, entity_type = domain_entity
        event = TemporalEvent(
            event_type=TemporalEventType.ENTITY_CREATED,
            entity_id=entity_id,
            entity_type=entity_type,
            source="test_source",
            description="Domain created",
        )
        result = service.record_event(event)
        assert result.event_id == event.event_id
        assert result.event_type == "ENTITY_CREATED"
        assert len(service._events) == 1

    def test_record_entity_observation(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        event = service.record_entity_observation(
            entity_id=entity_id,
            entity_type=entity_type,
            source="dns_resolver",
            observed_at=base_time,
            attributes={"registrar": "example-registrar", "tld": "invalid"},
        )
        assert event.event_type == "ENTITY_OBSERVED"
        assert event.observed_at == base_time
        assert event.source == "dns_resolver"
        assert len(service._events) == 1

    def test_first_seen_tracking(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        # Record observations at different times
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time + timedelta(days=5))
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time)
        service.record_entity_observation(entity_id, entity_type, "src3", observed_at=base_time + timedelta(days=10))

        first = service.get_first_seen(entity_id)
        assert first == base_time

    def test_last_seen_tracking(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time)
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=10))
        service.record_entity_observation(entity_id, entity_type, "src3", observed_at=base_time + timedelta(days=5))

        last = service.get_last_seen(entity_id)
        assert last == base_time + timedelta(days=10)

    def test_event_has_provenance(self, service, domain_entity):
        entity_id, entity_type = domain_entity
        event = service.record_entity_observation(
            entity_id=entity_id,
            entity_type=entity_type,
            source="cert_transparency",
            evidence_id="EV-001",
        )
        assert event.source == "cert_transparency"
        assert event.evidence_id == "EV-001"

    def test_event_content_hash(self, service, domain_entity):
        entity_id, entity_type = domain_entity
        event = service.record_entity_observation(entity_id, entity_type, "test")
        h = event.to_hash()
        assert len(h) == 64  # SHA-256 hex
        assert event.to_hash() == h  # Deterministic


# ═══════════════════════════════════════════════
# RELATIONSHIP / TEMPORAL EDGE TESTS
# ═══════════════════════════════════════════════


class TestTemporalEdges:
    def test_record_relationship(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity
        edge = service.record_relationship(
            source_entity_id=dom_id,
            source_entity_type=dom_type,
            target_entity_id=ip_id,
            target_entity_type=ip_type,
            relationship_type="RESOLVES_TO",
            source="dns_resolver",
            valid_from=base_time,
        )
        assert edge.relationship_type == "RESOLVES_TO"
        assert edge.is_active
        assert edge.valid_from == base_time
        assert edge.valid_to is None

    def test_edge_was_active_at(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity
        edge = service.record_relationship(
            dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns",
            valid_from=base_time,
            valid_to=base_time + timedelta(days=30),
        )
        assert edge.was_active_at(base_time + timedelta(days=10))
        assert not edge.was_active_at(base_time - timedelta(days=1))
        assert not edge.was_active_at(base_time + timedelta(days=31))

    def test_end_relationship_preserves_history(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        # Create edge
        service.record_relationship(dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time)

        # End it
        ended = service.end_relationship(dom_id, ip_id, "RESOLVES_TO", ended_at=base_time + timedelta(days=30))
        assert ended is not None
        assert not ended.is_active
        assert ended.valid_to == base_time + timedelta(days=30)

        # Edge still in storage
        assert len(service._edges) == 1
        assert not service._edges[0].is_active

    def test_replacing_relationship_ends_previous(self, service, domain_entity, base_time):
        dom_id, dom_type = domain_entity
        ip1_id, ip1_type = "IP:192.0.2.1", "IP"
        ip2_id, ip2_type = "IP:192.0.2.2", "IP"

        # Domain resolves to IP1
        edge1 = service.record_relationship(dom_id, dom_type, ip1_id, ip1_type, "RESOLVES_TO", "dns", valid_from=base_time)
        assert edge1.is_active

        # Domain resolves to IP2 — should end edge1
        edge2 = service.record_relationship(dom_id, dom_type, ip2_id, ip2_type, "RESOLVES_TO", "dns", valid_from=base_time + timedelta(days=15))
        assert edge2.is_active
        assert not edge1.is_active  # edge1 ended
        assert edge1.valid_to == base_time + timedelta(days=15)

        # Both edges preserved
        assert len(service._edges) == 2

    def test_relationship_event_created(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity
        service.record_relationship(
            dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time
        )
        rel_events = [e for e in service._events if e.event_type == "RELATIONSHIP_CREATED"]
        assert len(rel_events) == 1
        assert rel_events[0].related_entity_id == ip_id
        assert rel_events[0].relationship_type == "RESOLVES_TO"

    def test_end_relationship_creates_event(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity
        service.record_relationship(dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time)
        service.end_relationship(dom_id, ip_id, "RESOLVES_TO", ended_at=base_time + timedelta(days=30))

        end_events = [e for e in service._events if e.event_type == "RELATIONSHIP_ENDED"]
        assert len(end_events) == 1


# ═══════════════════════════════════════════════
# TEMPORAL QUERY TESTS
# ═══════════════════════════════════════════════


class TestTemporalQueries:
    def test_get_entity_timeline(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time)
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=5))
        service.record_entity_observation(entity_id, entity_type, "src3", observed_at=base_time + timedelta(days=10))

        timeline = service.get_entity_timeline(entity_id)
        assert timeline.query_type == "timeline"
        assert len(timeline.events) == 3
        # Events sorted by time
        assert timeline.events[0].observed_at == base_time
        assert timeline.events[2].observed_at == base_time + timedelta(days=10)

    def test_timeline_with_time_filter(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time)
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=5))
        service.record_entity_observation(entity_id, entity_type, "src3", observed_at=base_time + timedelta(days=10))

        timeline = service.get_entity_timeline(
            entity_id,
            start_time=base_time + timedelta(days=3),
            end_time=base_time + timedelta(days=7),
        )
        assert len(timeline.events) == 1
        assert timeline.events[0].observed_at == base_time + timedelta(days=5)

    def test_get_state_at_time(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        service.record_relationship(dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time)
        service.record_relationship(dom_id, dom_type, "IP:192.0.2.2", "IP", "RESOLVES_TO", "dns",
                                     valid_from=base_time + timedelta(days=30))

        # At day 10, only first edge should be active
        state = service.get_state_at_time(dom_id, base_time + timedelta(days=10))
        assert len(state.edges) == 1
        assert state.edges[0].target_entity_id == ip_id

        # At day 40, only second edge should be active
        state = service.get_state_at_time(dom_id, base_time + timedelta(days=40))
        assert len(state.edges) == 1
        assert state.edges[0].target_entity_id == "IP:192.0.2.2"

    def test_get_changes_between(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time,
                                           attributes={"ip": "192.0.2.1", "registrar": "GoDaddy"})
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=10),
                                           attributes={"ip": "192.0.2.2", "registrar": "GoDaddy"})
        service.record_entity_observation(entity_id, entity_type, "src3", observed_at=base_time + timedelta(days=20),
                                           attributes={"ip": "192.0.2.2", "registrar": "Namecheap"})

        changes = service.get_changes_between(entity_id, base_time, base_time + timedelta(days=25))
        assert len(changes.changes) >= 2  # IP change + registrar change
        ip_changes = [c for c in changes.changes if c.field == "ip"]
        assert len(ip_changes) == 1
        assert ip_changes[0].old_value == "192.0.2.1"
        assert ip_changes[0].new_value == "192.0.2.2"

    def test_get_new_entities(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        service.record_entity_observation(dom_id, dom_type, "src", observed_at=base_time)
        service.record_entity_observation(ip_id, ip_type, "src", observed_at=base_time + timedelta(days=10))

        new = service.get_new_entities(after=base_time + timedelta(days=5))
        assert ip_id in new
        assert dom_id not in new  # First seen before the cutoff

    def test_get_new_entities_by_type(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        service.record_entity_observation(dom_id, dom_type, "src", observed_at=base_time)
        service.record_entity_observation(ip_id, ip_type, "src", observed_at=base_time + timedelta(days=10))

        new_domains = service.get_new_entities(entity_type="DOMAIN", after=base_time - timedelta(days=1))
        assert dom_id in new_domains
        assert ip_id not in new_domains

    def test_get_disappeared_entities(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        # Only observe before the cutoff, so entity has disappeared by cutoff time
        service.record_entity_observation(entity_id, entity_type, "src", observed_at=base_time)
        service.record_entity_observation(entity_id, entity_type, "src", observed_at=base_time + timedelta(days=2))

        disappeared = service.get_disappeared_entities(before=base_time + timedelta(days=3))
        assert entity_id in disappeared  # Last seen (base_time+2) before cutoff (base_time+3)

    def test_infrastructure_changes(self, service, domain_entity, base_time):
        entity_id, entity_type = domain_entity
        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time,
                                           attributes={"ip": "192.0.2.1", "asn": "AS12345"})
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=10),
                                           attributes={"ip": "192.0.2.2", "asn": "AS12345"})

        infra_changes = service.get_infrastructure_changes(entity_id, base_time, base_time + timedelta(days=15))
        assert len(infra_changes) == 1
        assert infra_changes[0].field == "ip"


# ═══════════════════════════════════════════════
# EXPLAINABILITY TESTS
# ═══════════════════════════════════════════════


class TestExplainability:
    def test_explain_entity(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        service.record_entity_observation(dom_id, dom_type, "dns", observed_at=base_time)
        service.record_relationship(dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time)
        service.record_relationship(dom_id, dom_type, "IP:192.0.2.2", "IP", "RESOLVES_TO", "dns",
                                     valid_from=base_time + timedelta(days=30))

        explanation = service.explain_entity(dom_id)
        assert "entity_id" in explanation
        assert explanation["entity_id"] == dom_id
        assert explanation["first_seen"] is not None
        assert explanation["last_seen"] is not None
        assert explanation["total_events"] >= 3
        assert explanation["active_relationships"] >= 1
        assert "historical_relationships" in explanation
        assert "explanation" in explanation

    def test_explain_entity_not_found(self, service):
        explanation = service.explain_entity("UNKNOWN:does-not-exist")
        assert explanation["first_seen"] is None
        assert explanation["last_seen"] is None
        assert explanation["total_events"] == 0


# ═══════════════════════════════════════════════
# HISTORY PRESERVATION TESTS
# ═══════════════════════════════════════════════


class TestHistoryPreservation:
    def test_history_not_overwritten(self, service, domain_entity, base_time):
        """Critical: temporal history must NEVER be overwritten."""
        entity_id, entity_type = domain_entity

        service.record_entity_observation(entity_id, entity_type, "src1", observed_at=base_time,
                                           attributes={"ip": "192.0.2.1"})
        service.record_entity_observation(entity_id, entity_type, "src2", observed_at=base_time + timedelta(days=10),
                                           attributes={"ip": "192.0.2.2"})

        history = service._history[entity_id]
        assert len(history) == 2
        assert history[0].attributes["ip"] == "192.0.2.1"  # Original preserved
        assert history[1].attributes["ip"] == "192.0.2.2"

    def test_multiple_relationship_versions_preserved(self, service, domain_entity, base_time):
        """When a domain resolves to different IPs over time, all versions are kept."""
        dom_id, dom_type = domain_entity

        for i in range(5):
            ip_id = f"IP:10.0.0.{i}"
            service.record_relationship(
                dom_id, dom_type, ip_id, "IP", "RESOLVES_TO", "dns",
                valid_from=base_time + timedelta(days=i * 10),
            )

        # All 5 edges preserved
        assert len(service._edges) == 5
        # Only the last one is active
        active = [e for e in service._edges if e.is_active]
        assert len(active) == 1
        assert active[0].target_entity_id == "IP:10.0.0.4"

    def test_edge_metadata_preserved(self, service, domain_entity, base_time):
        dom_id, dom_type = domain_entity
        edge = service.record_relationship(
            dom_id, dom_type, "IP:192.0.2.1", "IP", "RESOLVES_TO", "dns",
            valid_from=base_time,
            confidence=ConfidenceLevel.HIGH,
            evidence_id="EV-001",
        )
        assert edge.confidence == "HIGH"
        assert edge.evidence_id == "EV-001"


# ═══════════════════════════════════════════════
# STATS TESTS
# ═══════════════════════════════════════════════


class TestStats:
    def test_stats(self, service, domain_entity, ip_entity, base_time):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity

        service.record_entity_observation(dom_id, dom_type, "src", observed_at=base_time)
        service.record_entity_observation(ip_id, ip_type, "src", observed_at=base_time)
        service.record_relationship(dom_id, dom_type, ip_id, ip_type, "RESOLVES_TO", "dns", valid_from=base_time)

        stats = service.stats()
        assert stats["total_events"] >= 3  # 2 observations + 1 relationship
        assert stats["total_edges"] == 1
        assert stats["active_edges"] == 1
        assert stats["tracked_entities"] == 2
        assert stats["history_entries"] == 2


# ═══════════════════════════════════════════════
# PROVENANCE TESTS
# ═══════════════════════════════════════════════


class TestProvenance:
    def test_every_event_has_source(self, service, domain_entity):
        entity_id, entity_type = domain_entity
        event = service.record_entity_observation(entity_id, entity_type, "cert_transparency")
        assert event.source == "cert_transparency"
        assert event.source != ""

    def test_every_edge_has_source(self, service, domain_entity, ip_entity):
        dom_id, dom_type = domain_entity
        ip_id, ip_type = ip_entity
        edge = service.record_relationship(dom_id, dom_type, ip_id, ip_type, "HOSTS", "rdap")
        assert edge.source == "rdap"

    def test_confidence_levels(self, service, domain_entity):
        entity_id, entity_type = domain_entity
        for level in ConfidenceLevel:
            event = service.record_entity_observation(
                entity_id, entity_type, f"src_{level}",
                confidence=level,
            )
            assert event.confidence == level.value
