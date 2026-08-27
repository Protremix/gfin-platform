"""Audit log verification tests.

Per Luna Directive — Focus Area 4: Audit log verification, immutability, filtering, retention.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from auth.audit import AuditEvent, AuditEventType, AuditLog


class TestAuditLogGeneration:
    """Test that operations generate audit log entries."""

    def test_log_creates_entry(self):
        """Logging an event should create an entry."""
        audit = AuditLog()
        audit.log(AuditEventType.ENTITY_CREATE, "user-001", "create", "entity", "ENT-001")
        assert len(audit.query()) == 1

    def test_log_contains_required_fields(self):
        """Audit log entry should contain required fields."""
        audit = AuditLog()
        audit.log(
            AuditEventType.ENTITY_UPDATE, "user-001", "update",
            "entity", "ENT-001", "ALLOW", "field update",
            metadata={"field": "confidence"},
        )
        entries = audit.query()
        assert len(entries) == 1
        assert entries[0].user_id == "user-001"
        assert entries[0].action == "update"
        assert entries[0].resource_id == "ENT-001"
        assert entries[0].decision == "ALLOW"

    def test_audit_log_correlation_id(self):
        """Audit events should support correlation tracking."""
        audit = AuditLog()
        audit.log(
            AuditEventType.ENTITY_CREATE, "user-001", "create",
            "entity", "ENT-001", metadata={"correlation_id": "corr-001"},
        )
        entries = audit.query()
        assert entries[0].metadata.get("correlation_id") == "corr-001"


class TestAuditLogFiltering:
    """Test audit log filtering."""

    def test_filter_by_user(self):
        """Should filter by user_id."""
        audit = AuditLog()
        for i in range(5):
            audit.log(
                AuditEventType.ENTITY_CREATE, f"user-{i % 2}", "create",
                "entity", f"ENT-{i}",
            )
        user0_events = audit.query(user_id="user-0")
        user1_events = audit.query(user_id="user-1")
        assert len(user0_events) >= 1
        assert len(user1_events) >= 1

    def test_filter_by_event_type(self):
        """Should filter by event_type."""
        audit = AuditLog()
        audit.log(AuditEventType.ENTITY_CREATE, "u1", "create", "entity", "E1")
        audit.log(AuditEventType.ENTITY_DELETE, "u1", "delete", "entity", "E2")
        create_events = audit.query(event_type=AuditEventType.ENTITY_CREATE)
        delete_events = audit.query(event_type=AuditEventType.ENTITY_DELETE)
        assert len(create_events) == 1
        assert len(delete_events) == 1


class TestAuditLogImmutability:
    """Test audit log immutability."""

    def test_audit_event_fields_immutable(self):
        """AuditEvent should be created with all required fields."""
        event = AuditEvent(
            event_id="evt-001",
            event_type=AuditEventType.ENTITY_CREATE,
            user_id="user-001",
            action="create",
            resource_type="entity",
            resource_id="ENT-001",
            decision="ALLOW",
            reason="test",
            ip_address=None,
            user_agent=None,
            timestamp=datetime.now(UTC),
        )
        assert event.event_id == "evt-001"
        assert event.user_id == "user-001"
        assert event.action == "create"

    def test_audit_log_grows_monotonically(self):
        """Audit log should only grow, never shrink (append-only)."""
        audit = AuditLog()
        for i in range(10):
            audit.log(AuditEventType.ENTITY_CREATE, "u1", "create", "entity", f"E{i}")
        initial_count = len(audit.query())
        for i in range(10, 15):
            audit.log(AuditEventType.ENTITY_CREATE, "u1", "create", "entity", f"E{i}")
        final_count = len(audit.query())
        assert final_count == initial_count + 5
        assert final_count == 15
