"""Tests for GFIN core schemas (enums, base types)."""

import pytest

from schemas.base import BaseEntity, BaseObservation, BaseRelationship, BaseSource
from schemas.enums import (
    Confidence,
    DataClassification,
    EntityType,
    RelationshipType,
    ReportStatus,
    RiskLevel,
    UserRole,
)


class TestEnums:
    """Verify all enums have the expected values."""

    def test_data_classification_has_5_levels(self):
        assert len(DataClassification) == 5
        assert DataClassification.PUBLIC.value == "PUBLIC"
        assert DataClassification.HIGHLY_RESTRICTED.value == "HIGHLY_RESTRICTED"

    def test_entity_type_has_expected_types(self):
        assert EntityType.PHONE.value == "PHONE"
        assert EntityType.DOMAIN.value == "DOMAIN"
        assert EntityType.CRYPTO_WALLET.value == "CRYPTO_WALLET"
        assert EntityType.CAMPAIGN.value == "CAMPAIGN"

    def test_relationship_type_has_expected_types(self):
        assert RelationshipType.RESOLVES_TO.value == "RESOLVES_TO"
        assert RelationshipType.PART_OF_CAMPAIGN.value == "PART_OF_CAMPAIGN"
        assert RelationshipType.SIMILAR_TO.value == "SIMILAR_TO"

    def test_report_status_has_expected_states(self):
        assert ReportStatus.UNVERIFIED.value == "UNVERIFIED"
        assert ReportStatus.OFFICIALLY_ESTABLISHED.value == "OFFICIALLY_ESTABLISHED"

    def test_risk_level_has_expected_levels(self):
        assert RiskLevel.UNKNOWN.value == "UNKNOWN"
        assert RiskLevel.CRITICAL.value == "CRITICAL"

    def test_user_role_has_expected_roles(self):
        assert UserRole.CITIZEN.value == "CITIZEN"
        assert UserRole.INVESTIGATOR.value == "INVESTIGATOR"
        assert UserRole.ADMINISTRATOR.value == "ADMINISTRATOR"


class TestBaseEntity:
    """Test base entity model."""

    def test_entity_has_auto_generated_id(self):
        entity = BaseEntity(
            entity_type=EntityType.PHONE,
            normalized_value="+34612345678",
        )
        assert entity.id.startswith("ENT-")
        assert len(entity.id) == 12  # ENT- + 8 hex chars

    def test_entity_preserves_raw_values(self):
        entity = BaseEntity(
            entity_type=EntityType.PHONE,
            normalized_value="+34612345678",
            raw_values=["+34 612 345 678", "0034 612 345 678"],
        )
        assert len(entity.raw_values) == 2
        assert "+34 612 345 678" in entity.raw_values

    def test_entity_has_default_classification_public(self):
        entity = BaseEntity(
            entity_type=EntityType.DOMAIN,
            normalized_value="example.com",
        )
        assert entity.classification.classification == DataClassification.PUBLIC

    def test_entity_has_timestamps(self):
        entity = BaseEntity(
            entity_type=EntityType.IP,
            normalized_value="192.168.1.1",
        )
        assert entity.first_seen is not None
        assert entity.last_seen is not None


class TestBaseObservation:
    """Test base observation model."""

    def test_observation_has_auto_generated_id(self):
        obs = BaseObservation(
            entity_id="ENT-7F82A91",
            source_id="SRC-001",
            source_type="Citizen Report",
            raw_value="+34 612 345 678",
        )
        assert obs.id.startswith("OBS-")

    def test_observation_links_to_entity(self):
        obs = BaseObservation(
            entity_id="ENT-7F82A91",
            source_id="SRC-001",
            source_type="Citizen Report",
            raw_value="suspicious-email@example.com",
            country="Spain",
        )
        assert obs.entity_id == "ENT-7F82A91"
        assert obs.country == "Spain"

    def test_observation_distinct_from_entity(self):
        """Per Master Spec §7: entity ≠ observation. This distinction is mandatory."""
        entity = BaseEntity(
            entity_type=EntityType.PHONE,
            normalized_value="+34612345678",
        )
        obs = BaseObservation(
            entity_id=entity.id,
            source_id="SRC-001",
            source_type="Citizen Report",
            raw_value="+34 612 345 678",
        )
        assert entity.id != obs.id
        assert entity.id.startswith("ENT-")
        assert obs.id.startswith("OBS-")
        assert obs.entity_id == entity.id


class TestBaseRelationship:
    """Test base relationship model."""

    def test_relationship_has_auto_generated_id(self):
        rel = BaseRelationship(
            from_entity_id="ENT-AAA",
            to_entity_id="ENT-BBB",
            relationship_type="RESOLVES_TO",
            source_id="SRC-001",
        )
        assert rel.id.startswith("REL-")

    def test_relationship_has_confidence(self):
        rel = BaseRelationship(
            from_entity_id="ENT-AAA",
            to_entity_id="ENT-BBB",
            relationship_type="HOSTED_ON",
            source_id="SRC-001",
            confidence=Confidence.HIGH,
        )
        assert rel.confidence == Confidence.HIGH
