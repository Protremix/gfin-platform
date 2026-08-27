"""Comprehensive tests for Module 06 — Evidence Vault.

Per Master Spec §10 (Evidence Vault):
- Every evidence item contains: evidence_id, source, source reference, retrieval timestamp,
  observation timestamp, content hash, content type, provenance, classification,
  retention policy, access policy, processing history
- Immutable/WORM-compatible storage for evidence requiring immutability (Layer B)
- Maintain chain of custody where applicable

Test categories:
1. Evidence creation (required fields, hash computation, validation)
2. Content hash verification (integrity checking)
3. Chain of custody (CREATED, ACCESSED, TRANSFERRED, PROCESSED, EXPORTED, RELEASED)
4. Processing history (append-only, entries)
5. Access control (classification levels, access policy)
6. Retention policy (time-based expiry, permanent)
7. Listing and filtering
8. Metrics
9. Integration with event bus
10. Negative/fail-safe tests
"""

from datetime import timedelta

import pytest

from schemas.base import BaseEvidence, Classification, Provenance, utc_now
from schemas.enums import Confidence, DataClassification
from services.evidence_vault import (
    CustodyAction,
    EvidenceVault,
)

# ─── Fixtures ───


@pytest.fixture
def vault():
    return EvidenceVault()


@pytest.fixture
def sample_evidence():
    return BaseEvidence(
        source_id="SRC-001",
        source_reference="https://example.com/evidence/1",
        retrieval_timestamp=utc_now(),
        observation_timestamp=utc_now(),
        content_hash="",  # Will be computed
        content_type="screenshot",
        provenance=Provenance(
            source_id="SRC-001",
            source_type="web_crawler",
            acquisition_method="automated",
            confidence=Confidence.MEDIUM,
        ),
        classification=Classification(
            classification=DataClassification.RESTRICTED,
            retention_policy="90d",
            access_policy="RESTRICTED",
        ),
        retention_policy="90d",
        access_policy="RESTRICTED",
    )


@pytest.fixture
def sample_content():
    return b"Fake screenshot content for testing"


# ═══════════════════════════════════════════════
# EVIDENCE CREATION
# ═══════════════════════════════════════════════


class TestEvidenceCreation:
    """Test evidence creation and ingestion."""

    def test_create_evidence(self, vault, sample_evidence, sample_content):
        """Creating evidence should compute hash and store."""
        stored = vault.create(sample_evidence, sample_content, actor="investigator1")

        assert stored.evidence.id.startswith("EVD-")
        assert stored.evidence.content_hash  # Hash computed
        assert len(stored.evidence.content_hash) == 64  # SHA-256 hex
        assert stored.content == sample_content

    def test_create_initializes_custody_chain(self, vault, sample_evidence, sample_content):
        """Creating evidence should initialize the custody chain with CREATED event."""
        stored = vault.create(sample_evidence, sample_content, actor="investigator1")

        assert len(stored.custody_chain) == 1
        assert stored.custody_chain[0].action == CustodyAction.CREATED
        assert stored.custody_chain[0].actor == "investigator1"
        assert stored.custody_chain[0].evidence_hash == stored.evidence.content_hash

    def test_create_initializes_processing_history(self, vault, sample_evidence, sample_content):
        """Creating evidence should add hash_computed to processing history."""
        stored = vault.create(sample_evidence, sample_content, actor="investigator1")

        assert len(stored.processing_history) == 1
        assert stored.processing_history[0].operation == "hash_computed"
        assert stored.processing_history[0].output_hash == stored.evidence.content_hash

    def test_create_with_preset_hash(self, vault, sample_content):
        """Creating evidence with a preset hash should verify it matches."""
        import hashlib

        expected_hash = hashlib.sha256(sample_content).hexdigest()
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash=expected_hash,
        )
        stored = vault.create(evidence, sample_content, actor="test")
        assert stored.evidence.content_hash == expected_hash

    def test_create_with_mismatched_hash(self, vault, sample_content):
        """Creating evidence with a wrong preset hash should fail."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="wrong_hash_value",
        )
        with pytest.raises(ValueError, match="Content hash mismatch"):
            vault.create(evidence, sample_content)

    def test_create_missing_required_fields(self, vault, sample_content):
        """Creating evidence without required fields should fail."""
        evidence = BaseEvidence(
            source_id="",  # Missing
            content_type="",  # Missing
            content_hash="",
        )
        with pytest.raises(ValueError, match="missing required fields"):
            vault.create(evidence, sample_content)

    def test_evidence_id_unique(self, vault, sample_evidence, sample_content):
        """Each evidence item should have a unique ID."""
        e1 = BaseEvidence(source_id="SRC-001", content_type="image", content_hash="")
        e2 = BaseEvidence(source_id="SRC-001", content_type="image", content_hash="")
        s1 = vault.create(e1, sample_content)
        s2 = vault.create(e2, sample_content)
        assert s1.evidence.id != s2.evidence.id


# ═══════════════════════════════════════════════
# CONTENT HASH VERIFICATION
# ═══════════════════════════════════════════════


class TestHashVerification:
    """Test content hash verification for integrity."""

    def test_verify_valid_evidence(self, vault, sample_evidence, sample_content):
        """Verifying unmodified evidence should return valid."""
        stored = vault.create(sample_evidence, sample_content)
        result = vault.verify(stored.evidence.id)

        assert result.is_valid is True
        assert result.expected_hash == result.actual_hash
        assert result.custody_intact is True

    def test_verify_tampered_evidence(self, vault, sample_evidence, sample_content):
        """Verifying tampered evidence should return invalid."""
        stored = vault.create(sample_evidence, sample_content)

        # Tamper with content
        stored.content = b"TAMPERED CONTENT"

        result = vault.verify(stored.evidence.id)
        assert result.is_valid is False
        assert result.expected_hash != result.actual_hash

    def test_verify_nonexistent_evidence(self, vault):
        """Verifying nonexistent evidence should return invalid."""
        result = vault.verify("EVD-NONEXIST")
        assert result.is_valid is False
        assert result.custody_intact is False

    def test_verify_records_custody_event(self, vault, sample_evidence, sample_content):
        """Verifying should record an ACCESSED custody event."""
        stored = vault.create(sample_evidence, sample_content)
        initial_chain_len = len(stored.custody_chain)

        vault.verify(stored.evidence.id)

        chain = vault.get_custody_chain(stored.evidence.id)
        assert len(chain) > initial_chain_len
        # Last event should be ACCESSED (from verify, not from create)
        accessed_events = [e for e in chain if e.action == CustodyAction.ACCESSED]
        assert len(accessed_events) >= 1  # From verify

    def test_hash_is_sha256(self, vault, sample_evidence, sample_content):
        """Content hash should be SHA-256 (64 hex chars)."""
        stored = vault.create(sample_evidence, sample_content)
        assert len(stored.evidence.content_hash) == 64
        # Verify it's hex
        int(stored.evidence.content_hash, 16)


# ═══════════════════════════════════════════════
# CHAIN OF CUSTODY
# ═══════════════════════════════════════════════


class TestChainOfCustody:
    """Test chain of custody tracking."""

    def test_custody_chain_starts_with_created(self, vault, sample_evidence, sample_content):
        """Custody chain should start with a CREATED event."""
        stored = vault.create(sample_evidence, sample_content, actor="admin")
        chain = vault.get_custody_chain(stored.evidence.id)

        assert len(chain) == 1
        assert chain[0].action == CustodyAction.CREATED
        assert chain[0].actor == "admin"

    def test_custody_event_has_hash(self, vault, sample_evidence, sample_content):
        """Each custody event should record the evidence hash."""
        stored = vault.create(sample_evidence, sample_content)
        chain = vault.get_custody_chain(stored.evidence.id)

        for event in chain:
            assert event.evidence_hash == stored.evidence.content_hash

    def test_custody_events_linked(self, vault, sample_evidence, sample_content):
        """Custody events should be linked via prior_event_id."""
        stored = vault.create(sample_evidence, sample_content)
        vault.transfer(stored.evidence.id, "investigator2", by_actor="supervisor")
        vault.export(stored.evidence.id, by_actor="supervisor", reason="court order")

        chain = vault.get_custody_chain(stored.evidence.id)
        assert len(chain) >= 3

        # Each event (except first) should link to previous
        for i in range(1, len(chain)):
            assert chain[i].prior_event_id == chain[i - 1].event_id

    def test_transfer_custody(self, vault, sample_evidence, sample_content):
        """Transferring evidence should record a TRANSFERRED event."""
        stored = vault.create(sample_evidence, sample_content)
        event = vault.transfer(
            stored.evidence.id, "new_custodian", by_actor="admin", reason="Reassignment"
        )

        assert event.action == CustodyAction.TRANSFERRED
        assert "new_custodian" in event.reason

    def test_export_custody(self, vault, sample_evidence, sample_content):
        """Exporting evidence should record an EXPORTED event."""
        stored = vault.create(sample_evidence, sample_content)
        event = vault.export(stored.evidence.id, by_actor="admin", reason="LE request")

        assert event.action == CustodyAction.EXPORTED

    def test_release_custody(self, vault, sample_evidence, sample_content):
        """Releasing evidence should record a RELEASED event."""
        stored = vault.create(sample_evidence, sample_content)
        event = vault.release(stored.evidence.id, by_actor="admin", reason="Case closed")

        assert event.action == CustodyAction.RELEASED

    def test_custody_chain_intact(self, vault, sample_evidence, sample_content):
        """Custody chain verification should pass for unbroken chain."""
        stored = vault.create(sample_evidence, sample_content)
        vault.transfer(stored.evidence.id, "new", by_actor="admin")
        vault.export(stored.evidence.id, by_actor="admin")

        result = vault.verify(stored.evidence.id)
        assert result.custody_intact is True

    def test_get_custody_chain_nonexistent(self, vault):
        """Getting custody chain for nonexistent evidence should return empty."""
        chain = vault.get_custody_chain("EVD-NONEXIST")
        assert chain == []

    def test_all_custody_actions_available(self):
        """All 7 custody actions should be available."""
        assert CustodyAction.CREATED == "CREATED"
        assert CustodyAction.RECEIVED == "RECEIVED"
        assert CustodyAction.ACCESSED == "ACCESSED"
        assert CustodyAction.TRANSFERRED == "TRANSFERRED"
        assert CustodyAction.PROCESSED == "PROCESSED"
        assert CustodyAction.EXPORTED == "EXPORTED"
        assert CustodyAction.RELEASED == "RELEASED"


# ═══════════════════════════════════════════════
# PROCESSING HISTORY
# ═══════════════════════════════════════════════


class TestProcessingHistory:
    """Test append-only processing history."""

    def test_initial_processing_entry(self, vault, sample_evidence, sample_content):
        """Evidence creation should add a hash_computed processing entry."""
        stored = vault.create(sample_evidence, sample_content)
        history = vault.get_processing_history(stored.evidence.id)

        assert len(history) == 1
        assert history[0].operation == "hash_computed"

    def test_add_processing_entry(self, vault, sample_evidence, sample_content):
        """Adding a processing entry should append to history."""
        stored = vault.create(sample_evidence, sample_content)
        vault.add_processing_entry(
            stored.evidence.id,
            operation="virus_scan",
            actor="security_scanner",
            status="COMPLETED",
            details="No threats found",
        )

        history = vault.get_processing_history(stored.evidence.id)
        assert len(history) == 2
        assert history[1].operation == "virus_scan"

    def test_processing_entry_has_id(self, vault, sample_evidence, sample_content):
        """Processing entries should have unique IDs."""
        stored = vault.create(sample_evidence, sample_content)
        vault.add_processing_entry(stored.evidence.id, operation="ocr", actor="ocr_engine")
        history = vault.get_processing_history(stored.evidence.id)

        assert history[1].entry_id.startswith("PHI-")
        assert history[0].entry_id != history[1].entry_id

    def test_processing_entry_records_custody(self, vault, sample_evidence, sample_content):
        """Adding a processing entry should also record a PROCESSED custody event."""
        stored = vault.create(sample_evidence, sample_content)
        vault.add_processing_entry(stored.evidence.id, operation="ocr", actor="ocr_engine")

        chain = vault.get_custody_chain(stored.evidence.id)
        processed_events = [e for e in chain if e.action == CustodyAction.PROCESSED]
        assert len(processed_events) >= 1

    def test_processing_history_nonexistent(self, vault):
        """Getting processing history for nonexistent evidence should return empty."""
        assert vault.get_processing_history("EVD-NONEXIST") == []


# ═══════════════════════════════════════════════
# ACCESS CONTROL
# ═══════════════════════════════════════════════


class TestAccessControl:
    """Test access control based on classification levels."""

    def test_public_accessible_by_all(self, vault):
        """PUBLIC evidence should be accessible by everyone."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            classification=Classification(classification=DataClassification.PUBLIC),
        )
        stored = vault.create(evidence, b"content")

        can_access, _reason = vault.check_access(
            stored.evidence.id, "user1", DataClassification.PUBLIC
        )
        assert can_access

    def test_restricted_requires_higher_level(self, vault):
        """RESTRICTED evidence should not be accessible by PUBLIC users."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            classification=Classification(classification=DataClassification.RESTRICTED),
        )
        stored = vault.create(evidence, b"content")

        can_access, reason = vault.check_access(
            stored.evidence.id, "user1", DataClassification.PUBLIC
        )
        assert not can_access
        assert "Insufficient classification" in reason

    def test_restricted_accessible_by_restricted(self, vault):
        """RESTRICTED evidence should be accessible by RESTRICTED users."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            classification=Classification(classification=DataClassification.RESTRICTED),
        )
        stored = vault.create(evidence, b"content")

        can_access, _reason = vault.check_access(
            stored.evidence.id, "user1", DataClassification.RESTRICTED
        )
        assert can_access

    def test_law_enforcement_requires_le(self, vault):
        """LAW_ENFORCEMENT evidence should require LE clearance."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            classification=Classification(classification=DataClassification.LAW_ENFORCEMENT),
        )
        stored = vault.create(evidence, b"content")

        can_access, _ = vault.check_access(
            stored.evidence.id, "user1", DataClassification.RESTRICTED
        )
        assert not can_access

        can_access, _ = vault.check_access(
            stored.evidence.id, "user1", DataClassification.LAW_ENFORCEMENT
        )
        assert can_access

    def test_access_policy_restricted(self, vault):
        """Access policy=RESTRICTED should block non-RESTRICTED users."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            classification=Classification(classification=DataClassification.RESTRICTED),
            access_policy="RESTRICTED",
        )
        stored = vault.create(evidence, b"content")

        # COMMUNITY user with RESTRICTED classification — should still pass classification
        # but access_policy=RESTRICTED should block if level < 2
        can_access, _ = vault.check_access(
            stored.evidence.id, "user1", DataClassification.COMMUNITY
        )
        assert not can_access

    def test_access_nonexistent_evidence(self, vault):
        """Checking access for nonexistent evidence should fail."""
        can_access, reason = vault.check_access("EVD-NONEXIST", "user1")
        assert not can_access
        assert "not found" in reason.lower()


# ═══════════════════════════════════════════════
# RETENTION POLICY
# ═══════════════════════════════════════════════


class TestRetentionPolicy:
    """Test retention policy checking."""

    def test_no_retention_policy(self, vault):
        """No retention policy should mean retain indefinitely."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
        )
        stored = vault.create(evidence, b"content")

        should_retain, reason = vault.check_retention(stored.evidence.id)
        assert should_retain
        assert "indefinitely" in reason.lower()

    def test_permanent_retention(self, vault):
        """Permanent retention should always retain."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            retention_policy="permanent",
        )
        stored = vault.create(evidence, b"content")

        should_retain, reason = vault.check_retention(stored.evidence.id)
        assert should_retain
        assert "Permanent" in reason

    def test_active_retention(self, vault):
        """Active retention (90d) should retain within period."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            retention_policy="90d",
        )
        stored = vault.create(evidence, b"content")

        should_retain, reason = vault.check_retention(stored.evidence.id)
        assert should_retain
        assert "Retained until" in reason

    def test_expired_retention(self, vault):
        """Expired retention should not retain."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            retention_policy="1d",
            retrieval_timestamp=utc_now() - timedelta(days=10),  # 10 days ago
        )
        stored = vault.create(evidence, b"content")

        should_retain, reason = vault.check_retention(stored.evidence.id)
        assert not should_retain
        assert "expired" in reason.lower()

    def test_yearly_retention(self, vault):
        """Yearly retention (1y) should parse correctly."""
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="document",
            content_hash="",
            retention_policy="1y",
        )
        stored = vault.create(evidence, b"content")

        should_retain, _reason = vault.check_retention(stored.evidence.id)
        assert should_retain

    def test_retention_nonexistent(self, vault):
        """Checking retention for nonexistent evidence should fail."""
        should_retain, _reason = vault.check_retention("EVD-NONEXIST")
        assert not should_retain


# ═══════════════════════════════════════════════
# LISTING AND FILTERING
# ═══════════════════════════════════════════════


class TestListing:
    """Test evidence listing and filtering."""

    def test_list_all(self, vault):
        """Should list all evidence."""
        vault.create(
            BaseEvidence(source_id="SRC-001", content_type="image", content_hash=""), b"img1"
        )
        vault.create(
            BaseEvidence(source_id="SRC-002", content_type="document", content_hash=""), b"doc1"
        )

        results = vault.list()
        assert len(results) == 2

    def test_filter_by_source(self, vault):
        """Should filter by source_id."""
        vault.create(
            BaseEvidence(source_id="SRC-001", content_type="image", content_hash=""), b"img1"
        )
        vault.create(
            BaseEvidence(source_id="SRC-002", content_type="image", content_hash=""), b"img2"
        )

        results = vault.list(source_id="SRC-001")
        assert len(results) == 1
        assert results[0].evidence.source_id == "SRC-001"

    def test_filter_by_content_type(self, vault):
        """Should filter by content type."""
        vault.create(
            BaseEvidence(source_id="SRC-001", content_type="image", content_hash=""), b"img1"
        )
        vault.create(
            BaseEvidence(source_id="SRC-001", content_type="document", content_hash=""), b"doc1"
        )

        results = vault.list(content_type="image")
        assert len(results) == 1
        assert results[0].evidence.content_type == "image"

    def test_filter_by_classification(self, vault):
        """Should filter by classification."""
        vault.create(
            BaseEvidence(
                source_id="SRC-001",
                content_type="image",
                content_hash="",
                classification=Classification(classification=DataClassification.PUBLIC),
            ),
            b"img1",
        )
        vault.create(
            BaseEvidence(
                source_id="SRC-001",
                content_type="image",
                content_hash="",
                classification=Classification(classification=DataClassification.RESTRICTED),
            ),
            b"img2",
        )

        results = vault.list(classification=DataClassification.PUBLIC)
        assert len(results) == 1

    def test_empty_list(self, vault):
        """Empty vault should return empty list."""
        assert vault.list() == []


# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════


class TestMetrics:
    """Test vault metrics."""

    def test_metrics_empty(self, vault):
        """Empty vault should have zero metrics."""
        metrics = vault.get_metrics()
        assert metrics["total_evidence"] == 0
        assert metrics["custody_events"] == 0
        assert metrics["processing_entries"] == 0

    def test_metrics_after_creation(self, vault, sample_evidence, sample_content):
        """Metrics should reflect created evidence."""
        vault.create(sample_evidence, sample_content)
        metrics = vault.get_metrics()

        assert metrics["total_evidence"] == 1
        assert metrics["custody_events"] == 1
        assert metrics["processing_entries"] == 1

    def test_metrics_by_content_type(self, vault):
        """Metrics should count by content type."""
        vault.create(BaseEvidence(source_id="S1", content_type="image", content_hash=""), b"img1")
        vault.create(BaseEvidence(source_id="S1", content_type="image", content_hash=""), b"img2")
        vault.create(
            BaseEvidence(source_id="S1", content_type="document", content_hash=""), b"doc1"
        )

        metrics = vault.get_metrics()
        assert metrics["by_content_type"]["image"] == 2
        assert metrics["by_content_type"]["document"] == 1


# ═══════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════


class TestIntegration:
    """Integration tests for end-to-end workflows."""

    def test_full_evidence_lifecycle(self, vault, sample_evidence, sample_content):
        """Full lifecycle: create → verify → process → transfer → export → release."""
        # Create
        stored = vault.create(sample_evidence, sample_content, actor="investigator")
        eid = stored.evidence.id

        # Verify integrity
        result = vault.verify(eid, actor="investigator")
        assert result.is_valid

        # Add processing
        vault.add_processing_entry(
            eid, operation="ocr_extracted", actor="ocr_engine", details="Text extracted"
        )

        # Transfer custody
        vault.transfer(eid, "detective_2", by_actor="supervisor", reason="Case reassignment")

        # Export for court
        vault.export(eid, by_actor="court_liaison", reason="Court order #12345")

        # Release (case closed)
        vault.release(eid, by_actor="supervisor", reason="Case closed")

        # Verify chain
        chain = vault.get_custody_chain(eid)
        assert len(chain) >= 5  # CREATED + ACCESSED + PROCESSED + TRANSFERRED + EXPORTED + RELEASED

        actions = [e.action for e in chain]
        assert CustodyAction.CREATED in actions
        assert CustodyAction.TRANSFERRED in actions
        assert CustodyAction.EXPORTED in actions
        assert CustodyAction.RELEASED in actions

        # Final integrity check
        final_result = vault.verify(eid)
        assert final_result.is_valid
        assert final_result.custody_intact

    def test_tamper_detection_workflow(self, vault, sample_evidence, sample_content):
        """Tampered evidence should be detected on verification."""
        stored = vault.create(sample_evidence, sample_content)

        # Initial verification passes
        result = vault.verify(stored.evidence.id)
        assert result.is_valid

        # Tamper
        stored.content = b"TAMPERED"

        # Verification fails
        result = vault.verify(stored.evidence.id)
        assert not result.is_valid
        assert result.expected_hash != result.actual_hash

    def test_multiple_evidence_items(self, vault):
        """Vault should handle multiple evidence items independently."""
        for i in range(5):
            evidence = BaseEvidence(
                source_id=f"SRC-{i:03d}",
                content_type="screenshot",
                content_hash="",
                classification=Classification(
                    classification=DataClassification.PUBLIC
                    if i % 2 == 0
                    else DataClassification.RESTRICTED
                ),
            )
            vault.create(evidence, f"content-{i}".encode())

        assert vault.get_metrics()["total_evidence"] == 5

        # Each should verify independently
        for stored in vault.list():
            result = vault.verify(stored.evidence.id)
            assert result.is_valid


# ═══════════════════════════════════════════════
# NEGATIVE / FAIL-SAFE TESTS
# ═══════════════════════════════════════════════


class TestNegativeFailSafe:
    """Test fail-safe behavior."""

    def test_get_nonexistent_evidence(self, vault):
        """Getting nonexistent evidence should return None."""
        assert vault.get("EVD-NONEXIST") is None

    def test_transfer_nonexistent(self, vault):
        """Transferring nonexistent evidence should fail."""
        with pytest.raises(ValueError, match="not found"):
            vault.transfer("EVD-NONEXIST", "new_actor")

    def test_export_nonexistent(self, vault):
        """Exporting nonexistent evidence should fail."""
        with pytest.raises(ValueError, match="not found"):
            vault.export("EVD-NONEXIST")

    def test_add_processing_nonexistent(self, vault):
        """Adding processing entry for nonexistent evidence should fail."""
        with pytest.raises(ValueError, match="not found"):
            vault.add_processing_entry("EVD-NONEXIST", operation="test", actor="test")

    def test_empty_content_allowed(self, vault):
        """Empty content should be allowed (metadata-only evidence)."""
        evidence = BaseEvidence(source_id="SRC-001", content_type="metadata", content_hash="")
        stored = vault.create(evidence, b"")
        assert stored.evidence.content_hash  # Even empty content has a hash

    def test_hash_collision_resistance(self, vault):
        """Different content should produce different hashes."""
        e1 = BaseEvidence(source_id="SRC-001", content_type="text", content_hash="")
        e2 = BaseEvidence(source_id="SRC-001", content_type="text", content_hash="")

        s1 = vault.create(e1, b"content_a")
        s2 = vault.create(e2, b"content_b")

        assert s1.evidence.content_hash != s2.evidence.content_hash
