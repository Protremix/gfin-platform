"""Tests for Global Matching — Module 25.

Tests cover:
- GlobalEntityIndex: register, lookup, remove, stats, get_entity
- GlobalMatchEngine: match, match_batch, notify_connector, notifications
- MatchPolicy: is_permitted, filter_match_data, filter_entity
- MatchResult: fields, policy_filtered
- MatchNotification: status transitions (PENDING → SENT → ACKNOWLEDGED)
- Integration: full match pipeline from registration to notification
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from services.global_matching import (
    NOT_PERMITTED_FIELDS,
    PERMITTED_FIELDS,
    GlobalEntityIndex,
    GlobalMatchEngine,
    IndexedEntity,
    MatchConfidence,
    MatchEntry,
    MatchPolicy,
    MatchResult,
    NotificationStatus,
)

# ─── Fixtures ───


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def index():
    return GlobalEntityIndex()


@pytest.fixture
def engine(mock_event_bus, mock_audit):
    return GlobalMatchEngine(event_bus=mock_event_bus, audit_logger=mock_audit)


@pytest.fixture
def populated_engine(engine):
    """Engine with entities from multiple jurisdictions."""
    entities = [
        IndexedEntity(
            entity_id="ENT-LV-001",
            entity_type="domain",
            entity_value="fraudster.com",
            jurisdiction="LV",
            organization="Latvian Police",
            confidence=MatchConfidence.HIGH.value,
            first_seen=datetime(2026, 1, 1, tzinfo=UTC),
            last_seen=datetime(2026, 8, 1, tzinfo=UTC),
            suspect_names=["John Doe"],
            case_files=["CASE-LV-001"],
            investigation_notes="Active investigation",
        ),
        IndexedEntity(
            entity_id="ENT-DE-001",
            entity_type="domain",
            entity_value="fraudster.com",
            jurisdiction="DE",
            organization="BKA",
            confidence=MatchConfidence.MEDIUM.value,
            first_seen=datetime(2026, 2, 1, tzinfo=UTC),
            last_seen=datetime(2026, 7, 1, tzinfo=UTC),
            suspect_names=["Jane Smith"],
            case_files=["CASE-DE-001"],
        ),
        IndexedEntity(
            entity_id="ENT-FR-001",
            entity_type="ip",
            entity_value="1.2.3.4",
            jurisdiction="FR",
            organization="French Police",
            confidence=MatchConfidence.HIGH.value,
        ),
        IndexedEntity(
            entity_id="ENT-LV-002",
            entity_type="ip",
            entity_value="1.2.3.4",
            jurisdiction="LV",
            organization="Latvian Police",
            confidence=MatchConfidence.LOW.value,
        ),
    ]
    for e in entities:
        engine.index.register_entity(e)
    return engine


# ─── GlobalEntityIndex Tests ───


class TestGlobalEntityIndex:
    def test_register_entity(self, index):
        entity = IndexedEntity(
            entity_id="E1", entity_type="domain", entity_value="test.com", jurisdiction="LV"
        )
        index.register_entity(entity)
        assert index.count == 1

    def test_register_same_jurisdiction_updates(self, index):
        entity1 = IndexedEntity(
            entity_id="E1",
            entity_type="domain",
            entity_value="test.com",
            jurisdiction="LV",
            confidence="LOW",
        )
        entity2 = IndexedEntity(
            entity_id="E1",
            entity_type="domain",
            entity_value="test.com",
            jurisdiction="LV",
            confidence="HIGH",
        )
        index.register_entity(entity1)
        index.register_entity(entity2)
        assert index.count == 1
        assert index.get_entity("E1").confidence == "HIGH"

    def test_register_different_jurisdictions(self, index):
        e1 = IndexedEntity(
            entity_id="E1", entity_type="domain", entity_value="test.com", jurisdiction="LV"
        )
        e2 = IndexedEntity(
            entity_id="E2", entity_type="domain", entity_value="test.com", jurisdiction="DE"
        )
        index.register_entity(e1)
        index.register_entity(e2)
        assert index.count == 2
        entries = index.lookup("domain", "test.com")
        assert len(entries) == 2

    def test_lookup(self, index):
        e = IndexedEntity(
            entity_id="E1", entity_type="domain", entity_value="test.com", jurisdiction="LV"
        )
        index.register_entity(e)
        results = index.lookup("domain", "test.com")
        assert len(results) == 1
        assert results[0].entity_id == "E1"

    def test_lookup_nonexistent(self, index):
        results = index.lookup("domain", "nonexistent.com")
        assert len(results) == 0

    def test_get_entity(self, index):
        e = IndexedEntity(
            entity_id="E1", entity_type="domain", entity_value="test.com", jurisdiction="LV"
        )
        index.register_entity(e)
        assert index.get_entity("E1") is not None
        assert index.get_entity("E1").jurisdiction == "LV"

    def test_get_entity_nonexistent(self, index):
        assert index.get_entity("nonexistent") is None

    def test_remove_entity(self, index):
        e = IndexedEntity(
            entity_id="E1", entity_type="domain", entity_value="test.com", jurisdiction="LV"
        )
        index.register_entity(e)
        assert index.remove_entity("E1") is True
        assert index.count == 0

    def test_remove_nonexistent(self, index):
        assert index.remove_entity("nonexistent") is False

    def test_stats(self, index):
        index.register_entity(
            IndexedEntity(
                entity_id="E1", entity_type="domain", entity_value="a.com", jurisdiction="LV"
            )
        )
        index.register_entity(
            IndexedEntity(
                entity_id="E2", entity_type="ip", entity_value="1.2.3.4", jurisdiction="DE"
            )
        )
        index.register_entity(
            IndexedEntity(
                entity_id="E3", entity_type="domain", entity_value="b.com", jurisdiction="LV"
            )
        )
        stats = index.stats
        assert stats["total_entities"] == 3
        assert stats["by_type"]["domain"] == 2
        assert stats["by_type"]["ip"] == 1
        assert stats["by_jurisdiction"]["LV"] == 2
        assert stats["by_jurisdiction"]["DE"] == 1


# ─── MatchPolicy Tests ───


class TestMatchPolicy:
    def test_is_permitted(self):
        assert MatchPolicy.is_permitted("entity_id") is True
        assert MatchPolicy.is_permitted("jurisdiction") is True
        assert MatchPolicy.is_permitted("confidence") is True
        assert MatchPolicy.is_permitted("first_seen") is True

    def test_is_not_permitted(self):
        assert MatchPolicy.is_permitted("suspect_names") is False
        assert MatchPolicy.is_permitted("case_files") is False
        assert MatchPolicy.is_permitted("investigation_notes") is False
        assert MatchPolicy.is_permitted("raw_reports") is False
        assert MatchPolicy.is_permitted("citizen_personal_info") is False

    def test_is_not_permitted_method(self):
        assert MatchPolicy.is_not_permitted("suspect_names") is True
        assert MatchPolicy.is_not_permitted("entity_id") is False

    def test_filter_match_data(self):
        data = {
            "entity_id": "E1",
            "jurisdiction": "LV",
            "suspect_names": ["John"],
            "case_files": ["CASE-001"],
            "confidence": "HIGH",
        }
        filtered = MatchPolicy.filter_match_data(data)
        assert "entity_id" in filtered
        assert "jurisdiction" in filtered
        assert "confidence" in filtered
        assert "suspect_names" not in filtered
        assert "case_files" not in filtered

    def test_filter_entity(self):
        entity = IndexedEntity(
            entity_id="E1",
            entity_type="domain",
            entity_value="test.com",
            jurisdiction="LV",
            suspect_names=["John Doe"],
            case_files=["CASE-001"],
            investigation_notes="Secret notes",
        )
        safe = MatchPolicy.filter_entity(entity)
        assert safe["entity_id"] == "E1"
        assert safe["jurisdiction"] == "LV"
        assert "suspect_names" not in safe
        assert "case_files" not in safe
        assert "investigation_notes" not in safe

    def test_permitted_fields_frozen(self):
        assert isinstance(PERMITTED_FIELDS, frozenset)
        assert isinstance(NOT_PERMITTED_FIELDS, frozenset)


# ─── GlobalMatchEngine Tests ───


class TestGlobalMatchEngine:
    def test_match_no_results(self, engine):
        result = engine.match("domain", "clean.com", "LV")
        assert result.matched is False
        assert len(result.matches) == 0
        assert result.policy_filtered is True

    def test_match_with_results(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        assert result.matched is True
        # Should only show DE match (LV is requesting jurisdiction)
        assert len(result.matches) == 1
        assert result.matches[0].jurisdiction == "DE"

    def test_match_excludes_own_jurisdiction(self, populated_engine):
        result = populated_engine.match("ip", "1.2.3.4", "LV")
        # Should only show FR match, not LV
        assert result.matched is True
        assert len(result.matches) == 1
        assert result.matches[0].jurisdiction == "FR"

    def test_match_returns_match_id(self, engine):
        result = engine.match("domain", "test.com", "LV")
        assert result.match_id.startswith("GMATCH-")

    def test_match_policy_filtered(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        assert result.policy_filtered is True
        # Match entries should not contain suspect names or case files
        for m in result.matches:
            assert not hasattr(m, "suspect_names")
            assert not hasattr(m, "case_files")

    def test_match_event_published(self, populated_engine, mock_event_bus):
        populated_engine.match("domain", "fraudster.com", "LV")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "match.global" in topics

    def test_match_no_event_when_no_match(self, engine, mock_event_bus):
        engine.match("domain", "clean.com", "LV")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "match.global" not in topics

    def test_match_audit_logged(self, engine, mock_audit):
        engine.match("domain", "test.com", "LV")
        mock_audit.log.assert_called_once()

    def test_match_batch(self, populated_engine):
        entities = [
            {"entity_type": "domain", "entity_value": "fraudster.com"},
            {"entity_type": "ip", "entity_value": "1.2.3.4"},
            {"entity_type": "domain", "entity_value": "clean.com"},
        ]
        results = populated_engine.match_batch(entities, "LV")
        assert len(results) == 3
        assert results[0].matched is True
        assert results[1].matched is True
        assert results[2].matched is False

    def test_match_increments_counter(self, engine):
        engine.match("domain", "a.com", "LV")
        engine.match("domain", "b.com", "LV")
        assert engine.match_count == 2

    def test_audit_entries(self, engine):
        engine.match("domain", "test.com", "LV")
        log = engine.get_audit_log()
        assert len(log) == 1
        assert log[0].entity_type == "domain"
        assert log[0].entity_value == "test.com"


# ─── MatchNotification Tests ───


class TestMatchNotification:
    def test_create_notification(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        notif = populated_engine.notify_connector("ORG-001", result)
        assert notif.id.startswith("GNOTIF-")
        assert notif.status == NotificationStatus.PENDING.value
        assert notif.org_id == "ORG-001"

    def test_send_notification(self, populated_engine, mock_event_bus):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        notif = populated_engine.notify_connector("ORG-001", result)
        assert populated_engine.send_notification(notif.id) is True
        assert notif.status == NotificationStatus.SENT.value
        assert notif.sent_at is not None
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "match.notification_sent" in topics

    def test_acknowledge_notification(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        notif = populated_engine.notify_connector("ORG-001", result)
        populated_engine.send_notification(notif.id)
        assert populated_engine.acknowledge_notification(notif.id) is True
        assert notif.status == NotificationStatus.ACKNOWLEDGED.value
        assert notif.acknowledged_at is not None

    def test_send_nonexistent_notification(self, engine):
        assert engine.send_notification("nonexistent") is False

    def test_acknowledge_nonexistent_notification(self, engine):
        assert engine.acknowledge_notification("nonexistent") is False

    def test_acknowledge_unsent_notification(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        notif = populated_engine.notify_connector("ORG-001", result)
        # Can't acknowledge without sending first
        assert populated_engine.acknowledge_notification(notif.id) is False

    def test_notification_count(self, populated_engine):
        result = populated_engine.match("domain", "fraudster.com", "LV")
        populated_engine.notify_connector("ORG-001", result)
        populated_engine.notify_connector("ORG-002", result)
        assert populated_engine.notification_count == 2


# ─── MatchResult Tests ───


class TestMatchResult:
    def test_no_match(self):
        result = MatchResult(
            query_entity_type="domain",
            query_entity_value="clean.com",
            requesting_jurisdiction="LV",
            matched=False,
        )
        assert result.matched is False
        assert len(result.matches) == 0
        assert result.policy_filtered is True

    def test_with_matches(self):
        entry = MatchEntry(
            entity_id="ENT-001",
            jurisdiction="DE",
            confidence=MatchConfidence.HIGH.value,
        )
        result = MatchResult(
            query_entity_type="domain",
            query_entity_value="fraudster.com",
            requesting_jurisdiction="LV",
            matched=True,
            matches=[entry],
        )
        assert result.matched is True
        assert len(result.matches) == 1
        assert result.matches[0].jurisdiction == "DE"


# ─── Integration Tests ───


class TestIntegrationGlobalMatching:
    def test_full_match_pipeline(self, mock_event_bus, mock_audit):
        """Full pipeline: register → match → filter → notify → send → acknowledge."""
        engine = GlobalMatchEngine(event_bus=mock_event_bus, audit_logger=mock_audit)

        # Register entities from multiple jurisdictions
        engine.index.register_entity(
            IndexedEntity(
                entity_id="ENT-DE-001",
                entity_type="domain",
                entity_value="phishing.com",
                jurisdiction="DE",
                organization="BKA",
                confidence=MatchConfidence.HIGH.value,
                first_seen=datetime(2026, 1, 1, tzinfo=UTC),
                suspect_names=["Hans Mueller"],
                case_files=["CASE-DE-001"],
            )
        )
        engine.index.register_entity(
            IndexedEntity(
                entity_id="ENT-FR-001",
                entity_type="domain",
                entity_value="phishing.com",
                jurisdiction="FR",
                organization="DGSI",
                confidence=MatchConfidence.MEDIUM.value,
                first_seen=datetime(2026, 3, 1, tzinfo=UTC),
            )
        )

        # Match from LV jurisdiction
        result = engine.match("domain", "phishing.com", "LV")
        assert result.matched is True
        assert len(result.matches) == 2
        jurisdictions = {m.jurisdiction for m in result.matches}
        assert jurisdictions == {"DE", "FR"}

        # Verify policy filtering — no suspect names or case files in results
        for m in result.matches:
            assert not hasattr(m, "suspect_names")
            assert not hasattr(m, "case_files")

        # Create notification for DE match
        notif = engine.notify_connector("ORG-LV-001", result)
        assert notif.status == NotificationStatus.PENDING.value

        # Send notification
        assert engine.send_notification(notif.id) is True
        assert notif.status == NotificationStatus.SENT.value

        # Acknowledge
        assert engine.acknowledge_notification(notif.id) is True
        assert notif.status == NotificationStatus.ACKNOWLEDGED.value

        # Audit trail
        log = engine.get_audit_log()
        assert len(log) == 1
        assert log[0].match_count == 2

    def test_no_self_match(self, mock_event_bus):
        """An entity should not match against its own jurisdiction."""
        engine = GlobalMatchEngine(event_bus=mock_event_bus)
        engine.index.register_entity(
            IndexedEntity(
                entity_id="ENT-LV-001",
                entity_type="domain",
                entity_value="fraud.com",
                jurisdiction="LV",
            )
        )
        result = engine.match("domain", "fraud.com", "LV")
        assert result.matched is False
        assert len(result.matches) == 0

    def test_batch_match_mixed_results(self, mock_event_bus):
        """Batch match with some hits and some misses."""
        engine = GlobalMatchEngine(event_bus=mock_event_bus)
        engine.index.register_entity(
            IndexedEntity(
                entity_id="E1", entity_type="domain", entity_value="fraud.com", jurisdiction="DE"
            )
        )
        engine.index.register_entity(
            IndexedEntity(
                entity_id="E2", entity_type="ip", entity_value="5.6.7.8", jurisdiction="FR"
            )
        )

        results = engine.match_batch(
            [
                {"entity_type": "domain", "entity_value": "fraud.com"},
                {"entity_type": "domain", "entity_value": "clean.com"},
                {"entity_type": "ip", "entity_value": "5.6.7.8"},
            ],
            requesting_jurisdiction="LV",
        )
        assert results[0].matched is True
        assert results[1].matched is False
        assert results[2].matched is True
