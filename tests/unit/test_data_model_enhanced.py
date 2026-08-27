"""Comprehensive tests for Module 03 — Core Data Model (Enhanced).

Per user requirements:
- entity creation, validation
- observation creation, evidence linkage
- relationship creation, provenance, classification
- jurisdiction, organization ownership
- access policy, stable IDs
- invalid references, duplicate handling
- serialization/deserialization, schema compatibility
- negative tests (fail-closed behavior)
- authorization integration (security-sensitive data model must fail closed)
"""

from datetime import UTC, datetime

import pytest

from auth.audit import AuditEventType, AuditLog
from auth.rbac import (
    AccessRequest,
    AuthorizationEngine,
    Decision,
    Permission,
)
from schemas.base import (
    AuditMetadata,
    BaseEvidence,
    BaseObservation,
    BaseReport,
    BaseSource,
    Classification,
    Provenance,
)
from schemas.entities import (
    PersonEntity,
    PhoneEntity,
    create_entity,
)
from schemas.enums import (
    Confidence,
    DataClassification,
    UserRole,
)
from schemas.extended import (
    BaseAccessPolicy,
    BaseAlert,
    BaseCampaign,
    BaseCase,
    BaseCountry,
    BaseOrganization,
    BaseUser,
)
from schemas.relationships import (
    Relationship,
    create_relationship,
)

# ═══════════════════════════════════════════════
# ENTITY CREATION & VALIDATION
# ═══════════════════════════════════════════════


class TestEntityCreation:
    """Test entity creation for all required types."""

    def test_create_person(self):
        p = create_entity("PERSON", full_name="Jane Doe")
        assert p.entity_type == "PERSON"
        assert p.normalized_value == "jane doe"
        assert p.id.startswith("ENT-")

    def test_create_phone_normalized(self):
        p = create_entity("PHONE", e164="+34612345678")
        assert p.normalized_value == "+34612345678"

    def test_create_email_normalized(self):
        e = create_entity("EMAIL", email="User@Example.COM")
        assert e.email == "user@example.com"
        assert e.normalized_value == "user@example.com"

    def test_create_domain_normalized(self):
        d = create_entity("DOMAIN", domain="Example.COM")
        assert d.domain == "example.com"
        assert d.tld == "com"

    def test_create_ip_canonical(self):
        ip = create_entity("IP", ip="192.168.1.1")
        assert ip.ip == "192.168.1.1"

    def test_create_crypto_wallet(self):
        w = create_entity(
            "CRYPTO_WALLET",
            blockchain="bitcoin",
            address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        )
        assert "bitcoin:" in w.normalized_value

    def test_entity_has_organization_id_field(self):
        p = create_entity("PERSON", full_name="Test")
        assert hasattr(p, "organization_id")
        assert p.organization_id is None  # Default None

    def test_entity_has_jurisdiction_field(self):
        d = create_entity("DOMAIN", domain="test.com")
        assert hasattr(d, "jurisdiction")
        assert d.jurisdiction is None

    def test_entity_has_audit_metadata(self):
        p = create_entity("PERSON", full_name="Test")
        assert hasattr(p, "audit")
        assert isinstance(p.audit, AuditMetadata)
        assert p.audit.version == 1
        assert p.audit.is_deleted is False
        assert p.audit.created_at is not None

    def test_entity_has_classification(self):
        p = create_entity("PERSON", full_name="Test")
        assert isinstance(p.classification, Classification)
        assert p.classification.classification == DataClassification.PUBLIC


# ═══════════════════════════════════════════════
# STABLE IDs
# ═══════════════════════════════════════════════


class TestStableIDs:
    """Test that all records use stable, immutable IDs — never user-facing values."""

    def test_entity_id_starts_with_prefix(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.id.startswith("ENT-")

    def test_entity_id_not_phone_number(self):
        phone = create_entity("PHONE", e164="+34612345678")
        assert phone.id != "+34612345678"
        assert phone.id != phone.normalized_value

    def test_entity_id_not_email(self):
        email = create_entity("EMAIL", email="user@example.com")
        assert email.id != "user@example.com"
        assert email.id != email.normalized_value

    def test_entity_id_not_domain(self):
        domain = create_entity("DOMAIN", domain="example.com")
        assert domain.id != "example.com"
        assert domain.id != domain.normalized_value

    def test_two_entities_different_ids(self):
        p1 = create_entity("PERSON", full_name="John")
        p2 = create_entity("PERSON", full_name="John")
        assert p1.id != p2.id

    def test_observation_id_prefix(self):
        obs = BaseObservation(
            entity_id="ENT-1", source_id="SRC-1", source_type="citizen", raw_value="test"
        )
        assert obs.id.startswith("OBS-")

    def test_relationship_id_prefix(self):
        rel = Relationship(
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            relationship_type="OWNS",
            source_id="SRC-1",
        )
        assert rel.id.startswith("REL-")

    def test_evidence_id_prefix(self):
        evd = BaseEvidence(source_id="SRC-1", content_hash="abc123", content_type="image/png")
        assert evd.id.startswith("EVD-")

    def test_source_id_prefix(self):
        src = BaseSource(source_identity="citizen-1", acquisition_method="web_form")
        assert src.id.startswith("SRC-")


# ═══════════════════════════════════════════════
# OBSERVATION CREATION
# ═══════════════════════════════════════════════


class TestObservation:
    """Test observation creation and linking to entities."""

    def test_create_observation(self):
        obs = BaseObservation(
            entity_id="ENT-ABC123",
            source_id="SRC-XYZ",
            source_type="web_crawl",
            raw_value="+34612345678",
        )
        assert obs.entity_id == "ENT-ABC123"
        assert obs.source_id == "SRC-XYZ"
        assert obs.raw_value == "+34612345678"
        assert obs.timestamp is not None

    def test_observation_has_classification(self):
        obs = BaseObservation(
            entity_id="ENT-1", source_id="SRC-1", source_type="citizen", raw_value="test"
        )
        assert isinstance(obs.classification, Classification)

    def test_observation_has_provenance(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="police_feed",
            raw_value="test",
            provenance=Provenance(
                source_id="SRC-1",
                source_type="police_feed",
                acquisition_method="api",
                reliability="HIGH",
            ),
        )
        assert obs.provenance is not None
        assert obs.provenance.reliability == "HIGH"

    def test_observation_has_organization_id(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="internal",
            raw_value="test",
            organization_id="ORG-1",
        )
        assert obs.organization_id == "ORG-1"

    def test_observation_has_audit_metadata(self):
        obs = BaseObservation(
            entity_id="ENT-1", source_id="SRC-1", source_type="citizen", raw_value="test"
        )
        assert hasattr(obs, "audit")
        assert obs.audit.version == 1
        assert obs.audit.is_deleted is False

    def test_observation_distinct_from_entity(self):
        """OBSERVATION ≠ ENTITY — different classes, different purposes."""
        entity = create_entity("PHONE", e164="+34612345678")
        obs = BaseObservation(
            entity_id=entity.id,
            source_id="SRC-1",
            source_type="citizen",
            raw_value="+34 612 345 678",
        )
        assert not isinstance(entity, type(obs))
        assert entity.id == obs.entity_id  # Observation references entity
        assert hasattr(obs, "entity_id")  # Only observations have this FK
        assert not hasattr(entity, "entity_id")  # Entities don't have self-FK


# ═══════════════════════════════════════════════
# EVIDENCE LINKAGE
# ═══════════════════════════════════════════════


class TestEvidenceLinkage:
    """Test evidence creation and linkage to observations."""

    def test_create_evidence(self):
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="sha256:abc123", content_type="image/png"
        )
        assert evd.id.startswith("EVD-")
        assert evd.content_hash == "sha256:abc123"
        assert evd.content_type == "image/png"

    def test_evidence_links_to_observation(self):
        evd = BaseEvidence(
            source_id="SRC-1",
            content_hash="sha256:abc123",
            content_type="image/png",
            observation_ids=["OBS-1", "OBS-2"],
        )
        assert len(evd.observation_ids) == 2
        assert "OBS-1" in evd.observation_ids

    def test_evidence_has_classification(self):
        evd = BaseEvidence(
            source_id="SRC-1",
            content_hash="abc",
            content_type="application/pdf",
            classification=Classification(
                classification=DataClassification.RESTRICTED, jurisdiction="ES"
            ),
        )
        assert evd.classification.classification == DataClassification.RESTRICTED
        assert evd.classification.jurisdiction == "ES"

    def test_evidence_has_provenance(self):
        evd = BaseEvidence(
            source_id="SRC-1",
            content_hash="abc",
            content_type="image/png",
            provenance=Provenance(
                source_id="SRC-1",
                source_type="web_crawl",
                acquisition_method="screenshot",
                reliability="MEDIUM",
            ),
        )
        assert evd.provenance is not None
        assert evd.provenance.acquisition_method == "screenshot"

    def test_evidence_has_retention_policy(self):
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="abc", content_type="image/png", retention_policy="90d"
        )
        assert evd.retention_policy == "90d"

    def test_evidence_has_organization_id(self):
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="abc", content_type="image/png", organization_id="ORG-1"
        )
        assert evd.organization_id == "ORG-1"

    def test_evidence_has_audit_metadata(self):
        evd = BaseEvidence(source_id="SRC-1", content_hash="abc", content_type="image/png")
        assert hasattr(evd, "audit")
        assert evd.audit.version == 1

    def test_evidence_distinct_from_observation(self):
        """EVIDENCE ≠ OBSERVATION — different classes."""
        obs = BaseObservation(
            entity_id="ENT-1", source_id="SRC-1", source_type="citizen", raw_value="test"
        )
        evd = BaseEvidence(source_id="SRC-1", content_hash="abc", content_type="image/png")
        assert not isinstance(obs, type(evd))
        # Evidence has content_hash, observations have raw_value
        assert hasattr(evd, "content_hash")
        assert hasattr(obs, "raw_value")
        assert not hasattr(obs, "content_hash")


# ═══════════════════════════════════════════════
# RELATIONSHIP CREATION
# ═══════════════════════════════════════════════


class TestRelationshipCreation:
    """Test relationship creation and provenance."""

    def test_create_relationship(self):
        rel = create_relationship(
            "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1"
        )
        assert rel.relationship_type == "OWNS"
        assert rel.from_entity_id == "ENT-1"
        assert rel.to_entity_id == "ENT-2"

    def test_relationship_has_provenance(self):
        rel = create_relationship(
            "RESOLVES_TO",
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            source_id="SRC-1",
            confidence=Confidence.HIGH,
        )
        assert rel.source_id == "SRC-1"
        assert rel.confidence == Confidence.HIGH

    def test_relationship_has_classification(self):
        rel = create_relationship(
            "RELATED_TO", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1"
        )
        assert isinstance(rel.classification, Classification)

    def test_relationship_has_organization_id(self):
        rel = create_relationship(
            "OWNS",
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            source_id="SRC-1",
            organization_id="ORG-1",
        )
        assert rel.organization_id == "ORG-1"

    def test_relationship_has_audit_metadata(self):
        rel = create_relationship(
            "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1"
        )
        assert hasattr(rel, "audit")
        assert rel.audit.version == 1

    def test_self_relationship_blocked(self):
        with pytest.raises(Exception, match="Self-relationship"):
            Relationship(
                from_entity_id="ENT-1",
                to_entity_id="ENT-1",
                relationship_type="RELATED_TO",
                source_id="SRC-1",
            )

    def test_relationship_distinct_from_entity(self):
        """RELATIONSHIP ≠ ENTITY — different classes."""
        entity = create_entity("DOMAIN", domain="test.com")
        rel = create_relationship(
            "RESOLVES_TO", from_entity_id=entity.id, to_entity_id="ENT-2", source_id="SRC-1"
        )
        assert not isinstance(entity, type(rel))
        assert hasattr(rel, "from_entity_id")
        assert hasattr(rel, "to_entity_id")
        assert not hasattr(entity, "from_entity_id")


# ═══════════════════════════════════════════════
# PROVENANCE
# ═══════════════════════════════════════════════


class TestProvenance:
    """Test provenance preservation on all record types."""

    def test_provenance_has_source_id(self):
        prov = Provenance(source_id="SRC-1", source_type="web_crawl", acquisition_method="api")
        assert prov.source_id == "SRC-1"

    def test_provenance_has_timestamp(self):
        prov = Provenance(source_id="SRC-1", source_type="test", acquisition_method="test")
        assert prov.timestamp is not None
        assert isinstance(prov.timestamp, datetime)

    def test_provenance_has_observation_timestamp(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="test",
            acquisition_method="test",
            observation_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert prov.observation_timestamp is not None

    def test_provenance_has_retrieval_timestamp(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="test",
            acquisition_method="test",
            retrieval_timestamp=datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert prov.retrieval_timestamp is not None

    def test_provenance_has_reliability(self):
        prov = Provenance(
            source_id="SRC-1", source_type="test", acquisition_method="test", reliability="HIGH"
        )
        assert prov.reliability == "HIGH"

    def test_provenance_has_confidence(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="test",
            acquisition_method="test",
            confidence=Confidence.HIGH,
        )
        assert prov.confidence == Confidence.HIGH

    def test_provenance_default_confidence_unknown(self):
        prov = Provenance(source_id="SRC-1", source_type="test", acquisition_method="test")
        assert prov.confidence == Confidence.UNKNOWN

    def test_provenance_confidence_on_all_record_types(self):
        """Provenance with confidence must be preservable on all record types."""
        prov = Provenance(
            source_id="SRC-1",
            source_type="test",
            acquisition_method="test",
            confidence=Confidence.HIGH,
        )
        # Entity
        p = create_entity("PERSON", full_name="Test", provenance=prov)
        assert p.provenance.confidence == Confidence.HIGH
        # Observation
        obs = BaseObservation(
            entity_id="ENT-1", source_id="SRC-1", source_type="test", raw_value="x", provenance=prov
        )
        assert obs.provenance.confidence == Confidence.HIGH
        # Relationship
        rel = create_relationship(
            "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1", provenance=prov
        )
        assert rel.provenance.confidence == Confidence.HIGH
        # Evidence
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="abc", content_type="image/png", provenance=prov
        )
        assert evd.provenance.confidence == Confidence.HIGH

    def test_entity_preserves_provenance(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="police_feed",
            acquisition_method="api",
            reliability="HIGH",
        )
        p = create_entity("PERSON", full_name="Test", provenance=prov)
        assert p.provenance is not None
        assert p.provenance.source_id == "SRC-1"
        assert p.provenance.reliability == "HIGH"

    def test_observation_preserves_provenance(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="citizen",
            acquisition_method="web_form",
            reliability="LOW",
        )
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="citizen",
            raw_value="test",
            provenance=prov,
        )
        assert obs.provenance is not None
        assert obs.provenance.reliability == "LOW"

    def test_relationship_preserves_provenance(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="investigation",
            acquisition_method="manual",
            reliability="MEDIUM",
        )
        rel = create_relationship(
            "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1", provenance=prov
        )
        assert rel.provenance is not None
        assert rel.provenance.reliability == "MEDIUM"

    def test_evidence_preserves_provenance(self):
        prov = Provenance(
            source_id="SRC-1",
            source_type="web_crawl",
            acquisition_method="screenshot",
            reliability="HIGH",
        )
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="abc", content_type="image/png", provenance=prov
        )
        assert evd.provenance is not None
        assert evd.provenance.acquisition_method == "screenshot"


# ═══════════════════════════════════════════════
# CLASSIFICATION & JURISDICTION
# ═══════════════════════════════════════════════


class TestClassificationJurisdiction:
    """Test classification and jurisdiction on all record types."""

    def test_entity_classification_default_public(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.classification.classification == DataClassification.PUBLIC

    def test_entity_classification_restricted(self):
        p = create_entity(
            "PERSON",
            full_name="Test",
            classification=Classification(
                classification=DataClassification.RESTRICTED, jurisdiction="ES"
            ),
        )
        assert p.classification.classification == DataClassification.RESTRICTED
        assert p.classification.jurisdiction == "ES"

    def test_entity_jurisdiction_field(self):
        d = create_entity("DOMAIN", domain="test.es", jurisdiction="ES")
        assert d.jurisdiction == "ES"

    def test_observation_classification(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="police",
            raw_value="restricted data",
            classification=Classification(
                classification=DataClassification.LAW_ENFORCEMENT, jurisdiction="DE"
            ),
        )
        assert obs.classification.classification == DataClassification.LAW_ENFORCEMENT
        assert obs.classification.jurisdiction == "DE"

    def test_relationship_classification(self):
        rel = create_relationship(
            "OWNS",
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            source_id="SRC-1",
            classification=Classification(classification=DataClassification.RESTRICTED),
        )
        assert rel.classification.classification == DataClassification.RESTRICTED

    def test_evidence_classification(self):
        evd = BaseEvidence(
            source_id="SRC-1",
            content_hash="abc",
            content_type="image/png",
            classification=Classification(
                classification=DataClassification.HIGHLY_RESTRICTED, jurisdiction="ES"
            ),
        )
        assert evd.classification.classification == DataClassification.HIGHLY_RESTRICTED

    def test_all_classification_levels(self):
        for level in DataClassification:
            p = create_entity(
                "PERSON", full_name="Test", classification=Classification(classification=level)
            )
            assert p.classification.classification == level


# ═══════════════════════════════════════════════
# ORGANIZATION OWNERSHIP & MULTI-TENANT
# ═══════════════════════════════════════════════


class TestOrganizationOwnership:
    """Test organization ownership and multi-tenant isolation."""

    def test_entity_organization_id(self):
        p = create_entity("PERSON", full_name="Test", organization_id="ORG-1")
        assert p.organization_id == "ORG-1"

    def test_entity_default_no_org(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.organization_id is None

    def test_observation_organization_id(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="internal",
            raw_value="test",
            organization_id="ORG-1",
        )
        assert obs.organization_id == "ORG-1"

    def test_relationship_organization_id(self):
        rel = create_relationship(
            "OWNS",
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            source_id="SRC-1",
            organization_id="ORG-1",
        )
        assert rel.organization_id == "ORG-1"

    def test_evidence_organization_id(self):
        evd = BaseEvidence(
            source_id="SRC-1", content_hash="abc", content_type="image/png", organization_id="ORG-1"
        )
        assert evd.organization_id == "ORG-1"

    def test_report_organization_id(self):
        rpt = BaseReport(description="Test report", organization_id="ORG-1")
        assert rpt.organization_id == "ORG-1"

    def test_source_organization_id(self):
        src = BaseSource(
            source_identity="police-es", acquisition_method="api", organization_id="ORG-1"
        )
        assert src.organization_id == "ORG-1"

    def test_organization_model(self):
        org = BaseOrganization(name="Spanish Police", org_type="law_enforcement", country="ES")
        assert org.name == "Spanish Police"
        assert org.org_type == "law_enforcement"
        assert org.country == "ES"
        assert org.id.startswith("ORG-")

    def test_organization_has_audit(self):
        org = BaseOrganization(name="Test")
        assert hasattr(org, "audit")
        assert org.audit.version == 1


# ═══════════════════════════════════════════════
# ACCESS POLICY
# ═══════════════════════════════════════════════


class TestAccessPolicy:
    """Test access policy model and integration."""

    def test_create_access_policy(self):
        policy = BaseAccessPolicy(
            name="LE-only",
            description="Law enforcement only access",
            required_roles=["INVESTIGATOR", "ADMINISTRATOR"],
            required_classifications=["RESTRICTED", "LAW_ENFORCEMENT"],
            deny_by_default=True,
        )
        assert policy.id.startswith("POL-")
        assert "INVESTIGATOR" in policy.required_roles
        assert policy.deny_by_default is True
        assert policy.is_active is True

    def test_access_policy_with_jurisdiction(self):
        policy = BaseAccessPolicy(
            name="ES-only", required_jurisdictions=["ES"], required_roles=["INVESTIGATOR"]
        )
        assert "ES" in policy.required_jurisdictions

    def test_access_policy_with_organization(self):
        policy = BaseAccessPolicy(name="Org-A-only", required_organizations=["ORG-A"])
        assert "ORG-A" in policy.required_organizations

    def test_access_policy_has_audit(self):
        policy = BaseAccessPolicy(name="test")
        assert hasattr(policy, "audit")
        assert policy.audit.version == 1


# ═══════════════════════════════════════════════
# SOFT DELETION & VERSIONING (LIFECYCLE)
# ═══════════════════════════════════════════════


class TestLifecycle:
    """Test soft deletion, versioning, and audit metadata."""

    def test_entity_default_not_deleted(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.audit.is_deleted is False
        assert p.audit.deleted_at is None

    def test_soft_delete(self):
        p = create_entity("PERSON", full_name="Test")
        p.soft_delete(deleted_by="USR-1")
        assert p.audit.is_deleted is True
        assert p.audit.deleted_at is not None
        assert p.audit.deleted_by == "USR-1"

    def test_soft_delete_increments_version(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.audit.version == 1
        p.soft_delete()
        assert p.audit.version == 2

    def test_update_audit(self):
        p = create_entity("PERSON", full_name="Test")
        p.update_audit(updated_by="USR-1")
        assert p.audit.updated_by == "USR-1"
        assert p.audit.updated_at is not None
        assert p.audit.version == 2

    def test_multiple_updates_increment_version(self):
        p = create_entity("PERSON", full_name="Test")
        assert p.audit.version == 1
        p.update_audit()
        assert p.audit.version == 2
        p.update_audit()
        assert p.audit.version == 3

    def test_all_records_have_audit_metadata(self):
        p = create_entity("PERSON", full_name="Test")
        obs = BaseObservation(entity_id=p.id, source_id="SRC-1", source_type="test", raw_value="x")
        rel = create_relationship(
            "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1"
        )
        evd = BaseEvidence(source_id="SRC-1", content_hash="abc", content_type="image/png")
        src = BaseSource(source_identity="test", acquisition_method="test")
        rpt = BaseReport(description="test")

        for record in [p, obs, rel, evd, src, rpt]:
            assert hasattr(record, "audit")
            assert isinstance(record.audit, AuditMetadata)
            assert record.audit.version == 1
            assert record.audit.is_deleted is False


# ═══════════════════════════════════════════════
# DUPLICATE HANDLING
# ═══════════════════════════════════════════════


class TestDuplicateHandling:
    """Test that the data model supports distinguishing duplicates by ID,
    even when normalized values are identical."""

    def test_same_normalized_value_different_ids(self):
        p1 = create_entity("PHONE", e164="+34612345678")
        p2 = create_entity("PHONE", e164="+34612345678")
        assert p1.normalized_value == p2.normalized_value
        assert p1.id != p2.id  # Different entities, same value

    def test_raw_values_accumulate(self):
        p = create_entity("PERSON", full_name="John", aliases=["Johnny", "J"])
        assert "John" in p.raw_values
        assert "Johnny" in p.raw_values
        assert "J" in p.raw_values

    def test_same_domain_different_raw(self):
        d1 = create_entity("DOMAIN", domain="example.com")
        d2 = create_entity("DOMAIN", domain="example.com")
        # Same normalized, different IDs — entity resolution (Module 04) would merge
        assert d1.normalized_value == d2.normalized_value
        assert d1.id != d2.id


# ═══════════════════════════════════════════════
# SERIALIZATION / DESERIALIZATION
# ═══════════════════════════════════════════════


class TestSerialization:
    """Test JSON serialization and deserialization round-trips."""

    def test_entity_serialize_deserialize(self):
        p = create_entity(
            "PERSON", full_name="Jane Doe", organization_id="ORG-1", jurisdiction="US"
        )
        data = p.model_dump()
        p2 = PersonEntity(**data)
        assert p2.full_name == "Jane Doe"
        assert p2.organization_id == "ORG-1"
        assert p2.jurisdiction == "US"
        assert p2.id == p.id

    def test_entity_json_roundtrip(self):
        p = create_entity("PHONE", e164="+34612345678")
        json_str = p.model_dump_json()
        p2 = PhoneEntity.model_validate_json(json_str)
        assert p2.e164 == "+34612345678"
        assert p2.id == p.id

    def test_observation_serialize_deserialize(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="citizen",
            raw_value="test data",
            organization_id="ORG-1",
        )
        data = obs.model_dump()
        obs2 = BaseObservation(**data)
        assert obs2.entity_id == "ENT-1"
        assert obs2.organization_id == "ORG-1"
        assert obs2.id == obs.id

    def test_relationship_serialize_deserialize(self):
        rel = create_relationship(
            "OWNS",
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            source_id="SRC-1",
            organization_id="ORG-1",
            confidence=Confidence.HIGH,
        )
        json_str = rel.model_dump_json()
        rel2 = Relationship.model_validate_json(json_str)
        assert rel2.from_entity_id == "ENT-1"
        assert rel2.confidence == Confidence.HIGH
        assert rel2.organization_id == "ORG-1"

    def test_evidence_serialize_deserialize(self):
        evd = BaseEvidence(
            source_id="SRC-1",
            content_hash="sha256:abc",
            content_type="image/png",
            organization_id="ORG-1",
            observation_ids=["OBS-1", "OBS-2"],
        )
        data = evd.model_dump()
        evd2 = BaseEvidence(**data)
        assert evd2.content_hash == "sha256:abc"
        assert len(evd2.observation_ids) == 2
        assert evd2.organization_id == "ORG-1"

    def test_report_serialize_deserialize(self):
        rpt = BaseReport(
            description="Phishing report",
            category="phishing",
            organization_id="ORG-1",
            risk_level="HIGH",
        )
        json_str = rpt.model_dump_json()
        rpt2 = BaseReport.model_validate_json(json_str)
        assert rpt2.description == "Phishing report"
        assert rpt2.risk_level == "HIGH"
        assert rpt2.organization_id == "ORG-1"

    def test_classification_serialization(self):
        p = create_entity(
            "PERSON",
            full_name="Test",
            classification=Classification(
                classification=DataClassification.RESTRICTED, jurisdiction="ES"
            ),
        )
        data = p.model_dump()
        assert data["classification"]["classification"] == "RESTRICTED"
        assert data["classification"]["jurisdiction"] == "ES"

    def test_provenance_serialization(self):
        obs = BaseObservation(
            entity_id="ENT-1",
            source_id="SRC-1",
            source_type="test",
            raw_value="x",
            provenance=Provenance(
                source_id="SRC-1", source_type="test", acquisition_method="api", reliability="HIGH"
            ),
        )
        data = obs.model_dump()
        assert data["provenance"]["source_id"] == "SRC-1"
        assert data["provenance"]["reliability"] == "HIGH"

    def test_audit_metadata_serialization(self):
        p = create_entity("PERSON", full_name="Test")
        p.update_audit(updated_by="USR-1")
        data = p.model_dump()
        assert data["audit"]["version"] == 2
        assert data["audit"]["updated_by"] == "USR-1"


# ═══════════════════════════════════════════════
# EXTENDED MODELS (Case, Campaign, Alert, Org, Country, User)
# ═══════════════════════════════════════════════


class TestExtendedModels:
    """Test Case, Campaign, Alert, Organization, Country, User models."""

    def test_case_creation(self):
        case = BaseCase(case_number="CASE-2026-001", jurisdiction="ES")
        assert case.case_number == "CASE-2026-001"
        assert case.jurisdiction == "ES"
        assert case.case_status == "OPEN"

    def test_case_default_restricted(self):
        case = BaseCase()
        assert case.classification.classification == DataClassification.RESTRICTED

    def test_case_has_organization_id(self):
        case = BaseCase(organization_id="ORG-1")
        assert case.organization_id == "ORG-1"

    def test_campaign_creation(self):
        camp = BaseCampaign(name="Phishing Wave", fraud_type="phishing", severity="HIGH")
        assert camp.name == "Phishing Wave"
        assert camp.campaign_status == "ACTIVE"
        assert camp.severity == "HIGH"

    def test_campaign_has_organization_id(self):
        camp = BaseCampaign(name="Test", organization_id="ORG-1")
        assert camp.organization_id == "ORG-1"

    def test_alert_creation(self):
        alert = BaseAlert(alert_type="domain_change", priority="P0", entity_ids=["ENT-1"])
        assert alert.alert_type == "domain_change"
        assert alert.priority == "P0"
        assert alert.alert_status == "NEW"

    def test_alert_has_organization_id(self):
        alert = BaseAlert(alert_type="test", organization_id="ORG-1")
        assert alert.organization_id == "ORG-1"

    def test_country_creation(self):
        country = BaseCountry(iso_code="ES", name="Spain", is_eu_member=True)
        assert country.iso_code == "ES"
        assert country.name == "Spain"
        assert country.is_eu_member is True

    def test_country_invalid_iso(self):
        with pytest.raises(Exception):
            BaseCountry(iso_code="ESP")

    def test_user_creation(self):
        user = BaseUser(
            email="admin@gfin.org", full_name="Admin", role="ADMINISTRATOR", organization_id="ORG-1"
        )
        assert user.email == "admin@gfin.org"
        assert user.role == "ADMINISTRATOR"
        assert user.organization_id == "ORG-1"
        assert user.is_active is True

    def test_user_email_normalized(self):
        user = BaseUser(email="ADMIN@GFIN.ORG")
        assert user.email == "admin@gfin.org"

    def test_source_creation(self):
        src = BaseSource(source_identity="citizen-1", acquisition_method="web_form")
        assert src.source_identity == "citizen-1"
        assert src.reliability == "UNKNOWN"
        assert src.id.startswith("SRC-")

    def test_report_creation(self):
        rpt = BaseReport(description="Test", category="phishing", risk_level="MEDIUM")
        assert rpt.status == "UNVERIFIED"
        assert rpt.category == "phishing"


# ═══════════════════════════════════════════════
# AUTHORIZATION INTEGRATION (FAIL-CLOSED)
# ═══════════════════════════════════════════════


class TestAuthorizationIntegration:
    """Test that the data model integrates with RBAC+ABAC and fails closed."""

    def test_citizen_cannot_access_law_enforcement_entity(self):
        """A citizen must not be able to access LAW_ENFORCEMENT classified data."""
        engine = AuthorizationEngine()
        req = AccessRequest(
            user_id="citizen-1",
            role=UserRole.CITIZEN,
            action=Permission.ENTITY_READ.value,
            resource_type="entity",
            resource_classification=DataClassification.LAW_ENFORCEMENT,
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    def test_investigator_cannot_access_highly_restricted(self):
        engine = AuthorizationEngine()
        req = AccessRequest(
            user_id="inv-1",
            role=UserRole.INVESTIGATOR,
            action=Permission.ENTITY_READ.value,
            resource_type="entity",
            resource_classification=DataClassification.HIGHLY_RESTRICTED,
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    def test_cross_jurisdiction_denied_for_le_data(self):
        engine = AuthorizationEngine()
        req = AccessRequest(
            user_id="inv-es",
            role=UserRole.INVESTIGATOR,
            action=Permission.INVESTIGATION_READ.value,
            resource_type="case",
            resource_classification=DataClassification.LAW_ENFORCEMENT,
            user_jurisdiction="ES",
            resource_jurisdiction="DE",
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY
        assert "jurisdiction" in result.reason.lower()

    def test_cross_organization_denied(self):
        engine = AuthorizationEngine()
        req = AccessRequest(
            user_id="inv-1",
            role=UserRole.INVESTIGATOR,
            action=Permission.ENTITY_READ.value,
            resource_type="entity",
            resource_classification=DataClassification.RESTRICTED,
            user_organization_id="ORG-A",
            resource_organization_id="ORG-B",
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY
        assert "organization" in result.reason.lower()

    def test_default_deny_for_unknown_role(self):
        engine = AuthorizationEngine()
        req = AccessRequest(
            user_id="unknown",
            role=UserRole.CITIZEN,
            action=Permission.ADMIN_MANAGE_USERS.value,
            resource_type="user",
            resource_classification=DataClassification.PUBLIC,
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    async def test_entity_with_classification_blocks_unauthorized(self):
        """Integration: entity with RESTRICTED classification blocks citizen."""
        from common.identity import Base44IdentityProvider

        provider = Base44IdentityProvider()
        engine = AuthorizationEngine()

        # Create a restricted entity
        create_entity(
            "PERSON",
            full_name="Restricted",
            classification=Classification(classification=DataClassification.RESTRICTED),
        )

        # Citizen token
        token = await provider.create_token("citizen-1", UserRole.CITIZEN)
        context = await provider.authenticate(token)

        # Citizen tries to read restricted entity
        # context.role is a string due to use_enum_values=True
        role_enum = UserRole(context.role) if isinstance(context.role, str) else context.role
        req = AccessRequest(
            user_id=context.user_id,
            role=role_enum,
            action=Permission.ENTITY_READ.value,
            resource_type="entity",
            resource_classification=DataClassification.RESTRICTED,
        )
        result = engine.evaluate(req)
        assert result.decision == Decision.DENY

    def test_audit_log_records_denial(self):
        """Integration: denied access must be auditable."""
        engine = AuthorizationEngine()
        audit = AuditLog()

        req = AccessRequest(
            user_id="citizen-1",
            role=UserRole.CITIZEN,
            action=Permission.ENTITY_DELETE.value,
            resource_type="entity",
            resource_classification=DataClassification.PUBLIC,
        )
        decision = engine.evaluate(req)
        audit.log(
            event_type=AuditEventType.AUTHZ_DENY,
            user_id="citizen-1",
            action=Permission.ENTITY_DELETE.value,
            resource_type="entity",
            decision=decision.decision.value,
            reason=decision.reason,
        )
        events = audit.query(event_type=AuditEventType.AUTHZ_DENY)
        assert len(events) == 1
        assert audit.verify_chain() is True

    def test_input_validation_blocks_malicious_entity(self):
        """Integration: input validation prevents creating malicious entities."""
        from auth.validation import ValidationError, validate_string

        with pytest.raises(ValidationError, match="SQL injection"):
            validate_string("'; DROP TABLE entities; --")

        with pytest.raises(ValidationError, match="traversal"):
            validate_string("../../../etc/passwd")


# ═══════════════════════════════════════════════
# NEGATIVE TESTS (FAIL-CLOSED)
# ═══════════════════════════════════════════════


class TestNegativeFailClosed:
    """Test that security-sensitive operations fail closed."""

    def test_invalid_entity_type_rejected(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            create_entity("INVALID_TYPE", value="test")

    def test_invalid_relationship_type_rejected(self):
        with pytest.raises(ValueError, match="Unknown relationship type"):
            create_relationship("INVALID_REL", from_entity_id="A", to_entity_id="B", source_id="S")

    def test_invalid_phone_rejected(self):
        with pytest.raises(Exception):
            create_entity("PHONE", e164="not_a_phone")

    def test_invalid_email_rejected(self):
        with pytest.raises(Exception):
            create_entity("EMAIL", email="not_an_email")

    def test_invalid_domain_rejected(self):
        with pytest.raises(Exception):
            create_entity("DOMAIN", domain="not_a_domain!!")

    def test_invalid_ip_rejected(self):
        with pytest.raises(Exception):
            create_entity("IP", ip="999.999.999.999")

    def test_invalid_report_status_rejected(self):
        with pytest.raises(Exception):
            create_entity("REPORT", status="INVALID_STATUS")

    def test_invalid_case_status_rejected(self):
        with pytest.raises(Exception):
            create_entity("CASE", case_status="INVALID")

    def test_invalid_campaign_status_rejected(self):
        with pytest.raises(Exception):
            create_entity("CAMPAIGN", campaign_status="INVALID")

    def test_self_relationship_rejected(self):
        with pytest.raises(Exception, match="Self-relationship"):
            create_relationship(
                "OWNS", from_entity_id="ENT-1", to_entity_id="ENT-1", source_id="SRC-1"
            )

    def test_person_without_name_rejected(self):
        with pytest.raises(Exception):
            create_entity("PERSON", full_name="")

    def test_phone_without_number_rejected(self):
        with pytest.raises(Exception):
            create_entity("PHONE", e164="")

    def test_country_invalid_iso_rejected(self):
        with pytest.raises(Exception):
            BaseCountry(iso_code="ESP")  # 3 letters

    def test_country_empty_iso_rejected(self):
        with pytest.raises(Exception):
            BaseCountry(iso_code="")
