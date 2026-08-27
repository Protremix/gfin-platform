"""Tests for GFIN STIX 2.x Import/Export Adapter.

Per OSINT Stack Evaluation §29: POC demonstrating STIX import/export path.

Layer A: In-memory conversion tests (no external dependencies).
Layer B: Would test against real TAXII server (REQUIRES EXTERNAL INFRASTRUCTURE).
"""


from common.stix_adapter import GFIN_CLASSIFICATION, STIXAdapter
from schemas.base import BaseEntity, Classification
from schemas.enums import DataClassification, EntityType


def make_entity(entity_type, value, classification=DataClassification.PUBLIC, jurisdiction=None):
    """Helper to create a BaseEntity with proper Classification model."""
    cls = Classification(classification=classification, jurisdiction=jurisdiction)
    return BaseEntity(
        entity_type=entity_type,
        normalized_value=value,
        classification=cls,
    )


class TestSTIXExport:
    """Test GFIN → STIX export."""

    def test_export_email(self):
        """GFIN Email entity → STIX Email Address Observable."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.EMAIL, "phishing@fake-bank.com")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "email-addr"
        assert stix_obj.value == "phishing@fake-bank.com"

    def test_export_domain(self):
        """GFIN Domain entity → STIX Domain Name Observable."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.DOMAIN, "fake-bank.com")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "domain-name"
        assert stix_obj.value == "fake-bank.com"

    def test_export_ip(self):
        """GFIN IP entity → STIX IPv4 Address Observable."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.IP, "192.168.1.1")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "ipv4-addr"
        assert stix_obj.value == "192.168.1.1"

    def test_export_url(self):
        """GFIN URL entity → STIX URL Observable."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.URL, "https://fake-bank.com/login")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "url"
        assert stix_obj.value == "https://fake-bank.com/login"

    def test_export_identity_organization(self):
        """GFIN Organization entity → STIX Identity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.ORGANIZATION, "Fake Bank Corp")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "identity"
        assert stix_obj.identity_class == "organization"

    def test_export_identity_person(self):
        """GFIN Person entity → STIX Identity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.PERSON, "John Doe")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj.type == "identity"
        assert stix_obj.identity_class == "individual"

    def test_export_custom_properties_preserved(self):
        """GFIN custom properties (classification, jurisdiction) are preserved in STIX export."""
        adapter = STIXAdapter()
        entity = make_entity(
            EntityType.EMAIL, "test@example.com",
            classification=DataClassification.RESTRICTED,
            jurisdiction="ES",
        )
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert hasattr(stix_obj, GFIN_CLASSIFICATION)
        assert getattr(stix_obj, GFIN_CLASSIFICATION) == "RESTRICTED"

    def test_export_bundle(self):
        """Export multiple GFIN entities to a STIX Bundle."""
        adapter = STIXAdapter()
        entities = [make_entity(EntityType.EMAIL, f"test{i}@example.com") for i in range(5)]
        bundle = adapter.export_entities(entities)
        assert bundle is not None
        assert bundle.type == "bundle"
        assert len(bundle.objects) == 5
        assert adapter.stats()["exported"] == 5

    def test_export_unknown_entity_type(self):
        """Unknown entity types are exported as custom observables."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.CRYPTO_WALLET, "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert stix_obj["type"] == "x-gfin-entity"
        assert stix_obj["entity_type"] == "CRYPTO_WALLET"


class TestSTIXImport:
    """Test STIX → GFIN import."""

    def test_import_email(self):
        """STIX Email Address Observable → GFIN Email entity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.EMAIL, "import@example.com")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity_type"] == "EMAIL"
        assert result["entities"][0]["entity_value"] == "import@example.com"

    def test_import_domain(self):
        """STIX Domain Name Observable → GFIN Domain entity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.DOMAIN, "imported-domain.com")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity_type"] == "DOMAIN"
        assert result["entities"][0]["entity_value"] == "imported-domain.com"

    def test_import_ip(self):
        """STIX IPv4 Address Observable → GFIN IP entity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.IP, "10.0.0.1")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity_type"] == "IP"
        assert result["entities"][0]["entity_value"] == "10.0.0.1"

    def test_import_url(self):
        """STIX URL Observable → GFIN URL entity."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.URL, "https://malicious.example.com/path")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity_type"] == "URL"
        assert result["entities"][0]["entity_value"] == "https://malicious.example.com/path"


class TestSTIXRoundTrip:
    """Test round-trip: GFIN → STIX → GFIN."""

    def test_email_round_trip(self):
        """Email entity survives GFIN → STIX → GFIN round-trip."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.EMAIL, "roundtrip@example.com")
        bundle = adapter.export_entities([entity])
        assert len(bundle.objects) == 1
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 1
        imported = result["entities"][0]
        assert imported["entity_type"] == "EMAIL"
        assert imported["entity_value"] == "roundtrip@example.com"
        assert imported["classification"] == "PUBLIC"

    def test_domain_round_trip(self):
        """Domain entity survives GFIN → STIX → GFIN round-trip."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.DOMAIN, "roundtrip-domain.com")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        imported = result["entities"][0]
        assert imported["entity_type"] == "DOMAIN"
        assert imported["entity_value"] == "roundtrip-domain.com"

    def test_ip_round_trip(self):
        """IP entity survives GFIN → STIX → GFIN round-trip."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.IP, "172.16.0.1")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        imported = result["entities"][0]
        assert imported["entity_type"] == "IP"
        assert imported["entity_value"] == "172.16.0.1"

    def test_url_round_trip(self):
        """URL entity survives GFIN → STIX → GFIN round-trip."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.URL, "https://roundtrip.example.com")
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        imported = result["entities"][0]
        assert imported["entity_type"] == "URL"
        assert imported["entity_value"] == "https://roundtrip.example.com"

    def test_custom_properties_round_trip(self):
        """GFIN custom properties survive round-trip."""
        adapter = STIXAdapter()
        entity = make_entity(
            EntityType.EMAIL, "custom@example.com",
            classification=DataClassification.RESTRICTED,
            jurisdiction="ES",
        )
        bundle = adapter.export_entities([entity])
        result = adapter.import_bundle(bundle)
        imported = result["entities"][0]
        assert imported["classification"] == "RESTRICTED"
        assert imported["source_type"] == "STIX"


class TestSTIXAdapterStats:
    """Test adapter statistics and error handling."""

    def test_stats_after_export(self):
        """Stats track export count."""
        adapter = STIXAdapter()
        entities = [make_entity(EntityType.EMAIL, f"s{i}@e.com") for i in range(3)]
        adapter.export_entities(entities)
        stats = adapter.stats()
        assert stats["exported"] == 3
        assert stats["errors"] == 0

    def test_stats_after_import(self):
        """Stats track import count."""
        adapter = STIXAdapter()
        entity = make_entity(EntityType.EMAIL, "stat@example.com")
        bundle = adapter.export_entities([entity])
        adapter.import_bundle(bundle)
        stats = adapter.stats()
        assert stats["exported"] == 1
        assert stats["imported"] == 1

    def test_empty_bundle(self):
        """Empty bundle exports/imports cleanly."""
        adapter = STIXAdapter()
        bundle = adapter.export_entities([])
        obj_count = len(getattr(bundle, "objects", []))
        assert obj_count == 0
        result = adapter.import_bundle(bundle)
        assert len(result["entities"]) == 0
        assert len(result["errors"]) == 0
