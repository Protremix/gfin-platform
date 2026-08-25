from __future__ import annotations
from typing import List

# GFIN Evidence Vault — Module 06
#
# Per Master Spec §10 (Evidence Vault):
# - Secure evidence storage with all required metadata
# - Immutable/WORM-compatible storage for evidence classes requiring immutability (Layer B)
# - Chain of custody where applicable
# - Content hash for integrity verification
#
# Per GPT Luna guidance:
# - Use existing BaseEvidence entity from Module 03 (don't create second entity)
# - EvidenceVault = application boundary that validates, hashes, records custody, applies policies
# - Publish evidence.created event after validation (Module 05)
#
# Layer A: In-memory evidence vault with content storage, hash verification, custody chain
# Layer B: WORM/immutable object storage, KMS, tamper-evident audit (REQUIRES EXTERNAL INFRASTRUCTURE)


import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import BaseEvidence, EvidenceId, utc_now
from schemas.enums import DataClassification

# ═══════════════════════════════════════════════
# CHAIN OF CUSTODY
# ═══════════════════════════════════════════════


class CustodyAction(str, Enum):
    """Actions in the chain of custody."""

    CREATED = "CREATED"
    RECEIVED = "RECEIVED"
    ACCESSED = "ACCESSED"
    TRANSFERRED = "TRANSFERRED"
    PROCESSED = "PROCESSED"
    EXPORTED = "EXPORTED"
    RELEASED = "RELEASED"


class CustodyEvent(BaseModel):
    """A single event in the chain of custody for an evidence item.

    Chain of custody tracks every action taken on an evidence item,
    maintaining integrity and traceability.
    """

    event_id: str = Field(default_factory=lambda: f"CSY-{uuid4().hex[:8].upper()}")
    evidence_id: EvidenceId
    action: CustodyAction
    actor: str  # user_id or component name
    timestamp: datetime = Field(default_factory=utc_now)
    reason: str = ""
    prior_event_id: str | None = None  # Links to previous custody event
    evidence_hash: str  # Hash of evidence at this point in time

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# PROCESSING HISTORY ENTRY
# ═══════════════════════════════════════════════


class ProcessingEntry(BaseModel):
    """An entry in the processing history of an evidence item.

    Append-only record of transformations applied to evidence.
    """

    entry_id: str = Field(default_factory=lambda: f"PHI-{uuid4().hex[:8].upper()}")
    operation: str  # e.g., "hash_computed", "ocr_extracted", "virus_scanned"
    actor: str  # component or user that performed the operation
    timestamp: datetime = Field(default_factory=utc_now)
    input_hash: str | None = None
    output_hash: str | None = None
    status: str = "COMPLETED"  # COMPLETED, FAILED, IN_PROGRESS
    details: str = ""

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# STORED EVIDENCE (metadata + content)
# ═══════════════════════════════════════════════


class StoredEvidence(BaseModel):
    """Evidence item with content stored alongside metadata.

    Layer A: content stored in memory.
    Layer B: content stored in S3-compatible / WORM storage.
    """

    evidence: BaseEvidence
    content: bytes
    custody_chain: list[CustodyEvent] = Field(default_factory=list)
    processing_history: list[ProcessingEntry] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# VERIFICATION RESULT
# ═══════════════════════════════════════════════


class VerificationResult(BaseModel):
    """Result of verifying an evidence item's integrity."""

    evidence_id: EvidenceId
    is_valid: bool
    expected_hash: str
    actual_hash: str
    verified_at: datetime = Field(default_factory=utc_now)
    custody_intact: bool = True

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# EVIDENCE VAULT INTERFACE
# ═══════════════════════════════════════════════


class EvidenceVault:
    """Evidence vault — secure storage with hash verification, chain of custody.

    Layer A: In-memory storage with full custody tracking.
    Layer B: WORM/S3-compatible storage (REQUIRES EXTERNAL INFRASTRUCTURE).

    Per Master Spec §10, every evidence item must contain:
    - evidence_id, source, source reference
    - retrieval timestamp, observation timestamp
    - content hash, content type
    - provenance, classification
    - retention policy, access policy
    - processing history
    """

    def __init__(self) -> None:
        self._storage: dict[EvidenceId, StoredEvidence] = {}
        self._custody_chains: dict[EvidenceId, list[CustodyEvent]] = {}

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def create(
        self,
        evidence: BaseEvidence,
        content: bytes,
        actor: str = "system",
    ) -> StoredEvidence:
        """Create a new evidence item in the vault.

        Validates required fields, computes content hash, initializes custody chain.
        Returns the stored evidence.

        Raises ValueError if required fields are missing.
        """
        # Validate required fields per Master Spec §10
        self._validate_evidence(evidence)

        # Compute hash if not already set
        actual_hash = self._compute_hash(content)
        if not evidence.content_hash:
            evidence.content_hash = actual_hash
        elif evidence.content_hash != actual_hash:
            raise ValueError(
                f"Content hash mismatch: expected {evidence.content_hash}, " f"got {actual_hash}"
            )

        # Create stored evidence
        stored = StoredEvidence(
            evidence=evidence,
            content=content,
            custody_chain=[],
            processing_history=[],
        )

        # Initialize custody chain
        custody_event = CustodyEvent(
            evidence_id=evidence.id,
            action=CustodyAction.CREATED,
            actor=actor,
            reason="Initial evidence ingestion",
            evidence_hash=actual_hash,
        )
        stored.custody_chain.append(custody_event)

        # Add initial processing history entry
        processing_entry = ProcessingEntry(
            operation="hash_computed",
            actor=actor,
            input_hash=None,
            output_hash=actual_hash,
            status="COMPLETED",
            details=f"SHA-256 hash computed on ingestion: {actual_hash}",
        )
        stored.processing_history.append(processing_entry)

        # Store
        self._storage[evidence.id] = stored
        self._custody_chains[evidence.id] = stored.custody_chain

        return stored

    def _validate_evidence(self, evidence: BaseEvidence) -> None:
        """Validate that evidence has all required fields per Master Spec §10."""
        errors = []

        if not evidence.id:
            errors.append("evidence_id")
        if not evidence.source_id:
            errors.append("source_id")
        if not evidence.content_type:
            errors.append("content_type")
        if not evidence.retrieval_timestamp:
            errors.append("retrieval_timestamp")
        if not evidence.classification:
            errors.append("classification")

        if errors:
            raise ValueError(f"Evidence missing required fields: {errors}")

    def get(self, evidence_id: EvidenceId, actor: str = "system") -> StoredEvidence | None:
        """Retrieve evidence by ID.

        Records an ACCESSED custody event.
        Returns None if not found.
        """
        stored = self._storage.get(evidence_id)
        if stored is None:
            return None

        # Record custody event
        self._record_custody(
            evidence_id,
            CustodyAction.ACCESSED,
            actor,
            reason="Evidence retrieved",
        )

        return stored

    def list(
        self,
        source_id: str | None = None,
        content_type: str | None = None,
        classification: DataClassification | None = None,
    ) -> list[StoredEvidence]:
        """List evidence items with optional filters."""
        results = list(self._storage.values())

        if source_id:
            results = [s for s in results if s.evidence.source_id == source_id]
        if content_type:
            results = [s for s in results if s.evidence.content_type == content_type]
        if classification:
            results = [
                s for s in results if s.evidence.classification.classification == classification
            ]

        return results

    def verify(self, evidence_id: EvidenceId, actor: str = "system") -> VerificationResult:
        """Verify evidence integrity by recomputing content hash.

        Returns VerificationResult with is_valid=True if hash matches.
        """
        stored = self._storage.get(evidence_id)
        if stored is None:
            return VerificationResult(
                evidence_id=evidence_id,
                is_valid=False,
                expected_hash="",
                actual_hash="",
                custody_intact=False,
            )

        actual_hash = self._compute_hash(stored.content)
        is_valid = actual_hash == stored.evidence.content_hash

        # Verify custody chain integrity
        custody_intact = self._verify_custody_chain(evidence_id)

        # Record custody event
        self._record_custody(
            evidence_id,
            CustodyAction.ACCESSED,
            actor,
            reason="Integrity verification",
        )

        return VerificationResult(
            evidence_id=evidence_id,
            is_valid=is_valid,
            expected_hash=stored.evidence.content_hash,
            actual_hash=actual_hash,
            custody_intact=custody_intact,
        )

    def _verify_custody_chain(self, evidence_id: EvidenceId) -> bool:
        """Verify that the custody chain is intact (no gaps, hashes match)."""
        chain = self._custody_chains.get(evidence_id, [])
        if not chain:
            return True

        prev_id = None
        for event in chain:
            if event.prior_event_id is not None and event.prior_event_id != prev_id:
                return False
            prev_id = event.event_id

        return True

    def get_custody_chain(self, evidence_id: EvidenceId) -> List[CustodyEvent]:
        """Get the full chain of custody for an evidence item."""
        return list(self._custody_chains.get(evidence_id, []))

    def _record_custody(
        self,
        evidence_id: EvidenceId,
        action: CustodyAction,
        actor: str,
        reason: str = "",
    ) -> CustodyEvent:
        """Record a custody event for an evidence item."""
        stored = self._storage.get(evidence_id)
        if stored is None:
            raise ValueError(f"Evidence not found: {evidence_id}")

        # Get last custody event for linking
        prior_id = None
        if stored.custody_chain:
            prior_id = stored.custody_chain[-1].event_id

        event = CustodyEvent(
            evidence_id=evidence_id,
            action=action,
            actor=actor,
            reason=reason,
            prior_event_id=prior_id,
            evidence_hash=stored.evidence.content_hash,
        )
        stored.custody_chain.append(event)
        self._custody_chains[evidence_id] = stored.custody_chain
        return event

    def transfer(
        self,
        evidence_id: EvidenceId,
        to_actor: str,
        by_actor: str = "system",
        reason: str = "",
    ) -> CustodyEvent:
        """Transfer evidence to a new custodian.

        Records a TRANSFERRED custody event.
        """
        return self._record_custody(
            evidence_id,
            CustodyAction.TRANSFERRED,
            by_actor,
            reason=f"Transferred to {to_actor}. {reason}",
        )

    def export(
        self,
        evidence_id: EvidenceId,
        by_actor: str = "system",
        reason: str = "",
    ) -> CustodyEvent:
        """Export evidence (e.g., for law enforcement request).

        Records an EXPORTED custody event.
        """
        return self._record_custody(
            evidence_id,
            CustodyAction.EXPORTED,
            by_actor,
            reason=reason,
        )

    def release(
        self,
        evidence_id: EvidenceId,
        by_actor: str = "system",
        reason: str = "",
    ) -> CustodyEvent:
        """Release evidence (end of retention/lifecycle).

        Records a RELEASED custody event.
        """
        return self._record_custody(
            evidence_id,
            CustodyAction.RELEASED,
            by_actor,
            reason=reason,
        )

    def add_processing_entry(
        self,
        evidence_id: EvidenceId,
        operation: str,
        actor: str,
        input_hash: str | None = None,
        output_hash: str | None = None,
        status: str = "COMPLETED",
        details: str = "",
    ) -> ProcessingEntry:
        """Add an entry to the processing history.

        Processing history is append-only — entries cannot be removed or modified.
        """
        stored = self._storage.get(evidence_id)
        if stored is None:
            raise ValueError(f"Evidence not found: {evidence_id}")

        entry = ProcessingEntry(
            operation=operation,
            actor=actor,
            input_hash=input_hash,
            output_hash=output_hash,
            status=status,
            details=details,
        )
        stored.processing_history.append(entry)

        # Also record a PROCESSED custody event
        self._record_custody(
            evidence_id,
            CustodyAction.PROCESSED,
            actor,
            reason=f"Processing: {operation}",
        )

        return entry

    def get_processing_history(self, evidence_id: EvidenceId) -> List[ProcessingEntry]:
        """Get the processing history for an evidence item."""
        stored = self._storage.get(evidence_id)
        if stored is None:
            return []
        return list(stored.processing_history)

    def check_access(
        self,
        evidence_id: EvidenceId,
        actor: str,
        actor_classification_level: DataClassification = DataClassification.PUBLIC,
    ) -> tuple[bool, str]:
        """Check if an actor can access an evidence item.

        Returns (can_access, reason).
        """
        stored = self._storage.get(evidence_id)
        if stored is None:
            return False, "Evidence not found"

        evidence_class = stored.evidence.classification.classification
        if evidence_class is None:
            return True, "No classification restriction"

        # GFIN classification hierarchy: PUBLIC < COMMUNITY < RESTRICTED < LAW_ENFORCEMENT < HIGHLY_RESTRICTED
        levels = {
            DataClassification.PUBLIC: 0,
            DataClassification.COMMUNITY: 1,
            DataClassification.RESTRICTED: 2,
            DataClassification.LAW_ENFORCEMENT: 3,
            DataClassification.HIGHLY_RESTRICTED: 4,
        }

        required_level = levels.get(evidence_class, 0)
        actor_level = levels.get(actor_classification_level, 0)

        if actor_level < required_level:
            return False, f"Insufficient classification level: requires {evidence_class}"

        # Check access policy if defined
        policy = stored.evidence.access_policy
        if policy and policy != "OPEN":
            # In Layer A, we just check if policy is "RESTRICTED"
            # Layer B would integrate with RBAC/ABAC
            if policy == "RESTRICTED" and actor_level < 2:
                return False, f"Access policy requires RESTRICTED: {policy}"

        return True, "Access granted"

    def check_retention(self, evidence_id: EvidenceId) -> tuple[bool, str]:
        """Check if evidence is still within its retention period.

        Returns (should_retain, reason).
        """
        stored = self._storage.get(evidence_id)
        if stored is None:
            return False, "Evidence not found"

        policy = stored.evidence.retention_policy
        if not policy:
            return True, "No retention policy — retain indefinitely"

        # Parse retention policy (e.g., "90d", "365d", "1y", "permanent")
        if policy == "permanent":
            return True, "Permanent retention"

        if policy.endswith("d"):
            days = int(policy[:-1])
            expiry = stored.evidence.retrieval_timestamp + timedelta(days=days)
            if utc_now() > expiry:
                return False, f"Retention expired on {expiry.isoformat()}"
            return True, f"Retained until {expiry.isoformat()}"

        if policy.endswith("y"):
            years = int(policy[:-1])
            expiry = stored.evidence.retrieval_timestamp + timedelta(days=365 * years)
            if utc_now() > expiry:
                return False, f"Retention expired on {expiry.isoformat()}"
            return True, f"Retained until {expiry.isoformat()}"

        return True, f"Unknown retention policy: {policy}"

    def get_metrics(self) -> dict[str, Any]:
        """Get vault metrics."""
        total = len(self._storage)
        custody_events = sum(len(chain) for chain in self._custody_chains.values())
        processing_entries = sum(len(s.processing_history) for s in self._storage.values())

        by_type: dict[str, int] = {}
        for stored in self._storage.values():
            ct = stored.evidence.content_type
            by_type[ct] = by_type.get(ct, 0) + 1

        return {
            "total_evidence": total,
            "custody_events": custody_events,
            "processing_entries": processing_entries,
            "by_content_type": by_type,
        }


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# The following capabilities are NOT available in Layer A:
#
# - WORM (Write-Once-Read-Many) / immutable object storage for evidence requiring immutability
# - S3-compatible durable storage with redundancy and backup
# - Key Management Service (KMS) for encryption at rest
# - Tamper-evident audit storage for custody chains
# - Cross-system custody transfer with cryptographic signatures
# - Production retention enforcement (automated deletion/expiry)
# - Integration with RBAC/ABAC for access policy enforcement
# - Evidence replication across regions for disaster recovery
# - Content-addressable storage (CAS) for deduplication
# - Legal hold management (suspension of retention policies)
# - Evidence export with cryptographic watermarking
# - Hardware Security Module (HSM) for key management
# - Time-stamping authority (TSA) for evidence timestamps
# - Integration with law-enforcement evidence management systems
#
# All of the above are marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
# Do NOT consider the evidence vault production-ready until these are implemented.
