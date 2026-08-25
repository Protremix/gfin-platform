# GFIN Base Schema Types
#
# Per Master Spec §5, §7, §45:
# - Entity ≠ Observation ≠ Evidence ≠ Relationship (mandatory distinction)
# - All records carry: provenance, classification, confidence, stable IDs
# - Multi-tenant: organization_id, jurisdiction
# - Lifecycle: versioning, soft deletion, retention awareness
# - Audit metadata: created_by, updated_at, access policy

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.enums import Confidence, DataClassification, EntityType


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(UTC)


# ─── Type Aliases ───

EntityId = str
ObservationId = str
RelationshipId = str
EvidenceId = str
SourceId = str
ReportId = str
Timestamp = datetime


class Classification(BaseModel):
    """Data classification metadata for any sensitive object.

    Per Constitution Article XX: 5 classification levels.
    Per Master Spec §45: classification-aware access control.
    """

    classification: DataClassification = DataClassification.PUBLIC
    owner: str | None = None
    jurisdiction: str | None = None
    access_policy: str | None = None
    retention_policy: str | None = None
    legal_basis: str | None = None


class Provenance(BaseModel):
    """Provenance for any observation, evidence, or claim.

    Per Master Spec §8: every record must preserve source, timestamp,
    observation time, retrieval time, provenance, confidence, classification.
    """

    source_id: SourceId
    source_type: str
    acquisition_method: str
    timestamp: Timestamp = Field(default_factory=utc_now)
    observation_timestamp: Timestamp | None = None
    retrieval_timestamp: Timestamp | None = None
    reliability: str = "UNKNOWN"
    confidence: Confidence = Confidence.UNKNOWN
    reference: str | None = None
    terms_classification: str | None = None


class AuditMetadata(BaseModel):
    """Audit metadata for tracking record lifecycle.

    Per Master Spec §45: immutable audit trails for security-critical operations.
    """

    created_by: str | None = None  # user_id of creator
    created_at: Timestamp = Field(default_factory=utc_now)
    updated_by: str | None = None
    updated_at: Timestamp | None = None
    version: int = 1  # Optimistic concurrency version
    is_deleted: bool = False  # Soft deletion
    deleted_at: Timestamp | None = None
    deleted_by: str | None = None


class BaseEntity(BaseModel):
    """Base model for all GFIN entities.

    Per Master Spec §7: An entity is a normalized, resolved object.
    An observation is a single sighting of it. This distinction is mandatory.

    ENTITY → something being tracked (a phone, a domain, a person)
    OBSERVATION → something observed about an entity (a sighting from a source)
    EVIDENCE → material supporting an observation/claim (a screenshot, a log)
    RELATIONSHIP → a connection between entities (person owns phone)
    SOURCE → where the information originated (a citizen, a police feed)

    Stable IDs: UUID-based, never use mutable user-facing values (phone, email) as PK.
    Multi-tenant: organization_id for org isolation.
    Lifecycle: soft deletion, versioning, audit metadata.
    """

    id: EntityId = Field(default_factory=lambda: f"ENT-{uuid4().hex[:8].upper()}")
    entity_type: EntityType
    normalized_value: str = ""
    raw_values: list[str] = Field(default_factory=list)
    classification: Classification = Field(default_factory=Classification)
    provenance: Provenance | None = None
    first_seen: Timestamp = Field(default_factory=utc_now)
    last_seen: Timestamp = Field(default_factory=utc_now)
    confidence: Confidence = Confidence.UNKNOWN

    # Multi-tenant / jurisdiction
    organization_id: str | None = None  # Owning organization for isolation
    jurisdiction: str | None = None  # ISO 3166-1 alpha-2 for jurisdiction scoping

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def soft_delete(self, deleted_by: str | None = None) -> None:
        """Mark entity as soft-deleted. Does not remove from storage."""
        self.audit.is_deleted = True
        self.audit.deleted_at = utc_now()
        self.audit.deleted_by = deleted_by
        self.audit.version += 1

    def update_audit(self, updated_by: str | None = None) -> None:
        """Update audit metadata on modification."""
        self.audit.updated_by = updated_by
        self.audit.updated_at = utc_now()
        self.audit.version += 1


class BaseObservation(BaseModel):
    """A single observation of an entity from a specific source.

    OBSERVATION ≠ ENTITY. An observation is a single sighting.
    Multiple observations of the same entity from different sources
    contribute to entity resolution and confidence scoring.
    """

    id: ObservationId = Field(default_factory=lambda: f"OBS-{uuid4().hex[:8].upper()}")
    entity_id: EntityId  # FK → BaseEntity.id (reference integrity)
    source_id: SourceId  # FK → BaseSource.id (reference integrity)
    source_type: str
    country: str | None = None
    timestamp: Timestamp = Field(default_factory=utc_now)
    raw_value: str
    classification: Classification = Field(default_factory=Classification)
    provenance: Provenance | None = None

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseRelationship(BaseModel):
    """A typed, provenance-bearing connection between two entities.

    RELATIONSHIP ≠ ENTITY. A relationship connects two entities.
    It has its own provenance, classification, and confidence.
    Self-relationships are not allowed.
    """

    id: RelationshipId = Field(default_factory=lambda: f"REL-{uuid4().hex[:8].upper()}")
    from_entity_id: EntityId  # FK → BaseEntity.id
    to_entity_id: EntityId  # FK → BaseEntity.id
    relationship_type: str
    source_id: SourceId  # FK → BaseSource.id
    timestamp: Timestamp = Field(default_factory=utc_now)
    observation_period_start: Timestamp | None = None
    observation_period_end: Timestamp | None = None
    confidence: Confidence = Confidence.UNKNOWN
    provenance: Provenance | None = None
    classification: Classification = Field(default_factory=Classification)
    access_policy: str | None = None

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseEvidence(BaseModel):
    """Stored, verifiable artifact supporting a claim or observation.

    EVIDENCE ≠ OBSERVATION. Evidence is material (a screenshot, a log file).
    It supports observations and claims. It has content hash for integrity.
    """

    id: EvidenceId = Field(default_factory=lambda: f"EVD-{uuid4().hex[:8].upper()}")
    source_id: SourceId  # FK → BaseSource.id
    source_reference: str | None = None
    retrieval_timestamp: Timestamp = Field(default_factory=utc_now)
    observation_timestamp: Timestamp | None = None
    content_hash: str
    content_type: str
    provenance: Provenance | None = None
    classification: Classification = Field(default_factory=Classification)
    retention_policy: str | None = None
    access_policy: str | None = None

    # Link to observation(s) this evidence supports
    observation_ids: list[str] = Field(default_factory=list)  # FK → BaseObservation.id

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    processing_history: list[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


class BaseSource(BaseModel):
    """Registered external data source per Source Policy.

    SOURCE ≠ ENTITY. A source is where information originated.
    Every observation, evidence, and relationship must reference a source.
    """

    id: SourceId = Field(default_factory=lambda: f"SRC-{uuid4().hex[:8].upper()}")
    source_identity: str
    acquisition_method: str
    terms_classification: str | None = None
    reliability: str = "UNKNOWN"
    registered_at: Timestamp = Field(default_factory=utc_now)
    last_reviewed: Timestamp | None = None
    data_classification: DataClassification = DataClassification.PUBLIC
    retention_policy: str | None = None
    access_policy: str | None = None

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    model_config = {"use_enum_values": True}


class BaseReport(BaseModel):
    """A user/organization-submitted fraud report.

    REPORT ≠ ENTITY. A report is a submission by a citizen or organization.
    It references entities but is not itself an entity.
    Citizen reports are allegations until corroborated (Constitution Article XVII).
    """

    id: ReportId = Field(default_factory=lambda: f"RPT-{uuid4().hex[:8].upper()}")
    status: str = "UNVERIFIED"  # ReportStatus enum value
    category: str = ""
    description: str = ""
    reporter_id: str | None = None  # user_id of reporter
    reporter_organization_id: str | None = None
    country: str | None = None  # ISO 3166-1 alpha-2
    language: str | None = None
    risk_level: str = "UNKNOWN"
    related_entity_ids: list[str] = Field(default_factory=list)  # FK → BaseEntity.id
    related_evidence_ids: list[str] = Field(default_factory=list)  # FK → BaseEvidence.id
    classification: Classification = Field(default_factory=Classification)

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}
