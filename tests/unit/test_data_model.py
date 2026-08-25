"""Tests for Module 03 — Core Data Model.

Tests cover:
- All 25 concrete entity models (validation, normalization, defaults)
- Entity factory function
- Relationship models (validation, self-relationship prevention)
- Relationship factory function
- Entity-relationship integration
"""

import pytest
from datetime import datetime

from schemas.enums import EntityType, RelationshipType, DataClassification, Confidence
from schemas.entities import (
    PersonEntity, OrganizationEntity, PhoneEntity, EmailEntity, DomainEntity,
    URLEntity, IPEntity, ASNEntity, NetworkEntity, DNSRecordEntity,
    CertificateEntity, WebsiteEntity, TelegramIdentifierEntity, SocialAccountEntity,
    CryptoWalletEntity, TransactionEntity, PaymentIdentifierEntity,
    DocumentEntity, ImageEntity, ReportEntity, CaseEntity, CampaignEntity,
    InfrastructureClusterEntity, FraudPatternEntity, AlertEntity, CountryEntity,
    ENTITY_TYPE_TO_CLASS, create_entity,
)
from schemas.relationships import (
    Relationship, create_relationship, RELATIONSHIP_TYPE_TO_CLASS,
)


# ─── Entity Model Tests ───

class TestPersonEntity:
    def test_valid_person(self):
        p = PersonEntity(full_name="John Smith", nationality="US")
        assert p.entity_type == EntityType.PERSON
        assert p.normalized_value == "john smith"
        assert "John Smith" in p.raw_values
        assert p.nationality == "US"

    def test_person_requires_name(self):
        with pytest.raises(Exception):
            PersonEntity(full_name="")

    def test_person_invalid_nationality(self):
        with pytest.raises(Exception):
            PersonEntity(full_name="Test", nationality="USA")  # 3 letters, not 2

    def test_person_with_aliases(self):
        p = PersonEntity(full_name="John Smith", aliases=["J. Smith", "Johnny"])
        assert "J. Smith" in p.raw_values
        assert "Johnny" in p.raw_values

    def test_person_custom_normalized_value(self):
        p = PersonEntity(full_name="John Smith", normalized_value="custom_id")
        assert p.normalized_value == "custom_id"


class TestOrganizationEntity:
    def test_valid_org(self):
        org = OrganizationEntity(name="Acme Corp", registration_country="US")
        assert org.entity_type == EntityType.ORGANIZATION
        assert org.normalized_value == "acme corp"

    def test_org_requires_name(self):
        with pytest.raises(Exception):
            OrganizationEntity(name="")

    def test_org_invalid_country(self):
        with pytest.raises(Exception):
            OrganizationEntity(name="Test", registration_country="XX1")


class TestPhoneEntity:
    def test_valid_phone(self):
        phone = PhoneEntity(e164="+34612345678")
        assert phone.entity_type == EntityType.PHONE
        assert phone.normalized_value == "+34612345678"

    def test_phone_normalizes_spaces(self):
        phone = PhoneEntity(e164="+34 612 345 678")
        assert phone.e164 == "+34612345678"

    def test_phone_invalid_format(self):
        with pytest.raises(Exception):
            PhoneEntity(e164="call me")

    def test_phone_too_short(self):
        with pytest.raises(Exception):
            PhoneEntity(e164="+123")


class TestEmailEntity:
    def test_valid_email(self):
        email = EmailEntity(email="user@example.com")
        assert email.entity_type == EntityType.EMAIL
        assert email.normalized_value == "user@example.com"
        assert email.local_part == "user"
        assert email.domain_part == "example.com"

    def test_email_normalizes_uppercase(self):
        email = EmailEntity(email="USER@EXAMPLE.COM")
        assert email.email == "user@example.com"

    def test_email_invalid(self):
        with pytest.raises(Exception):
            EmailEntity(email="not_an_email")


class TestDomainEntity:
    def test_valid_domain(self):
        d = DomainEntity(domain="example.com")
        assert d.entity_type == EntityType.DOMAIN
        assert d.normalized_value == "example.com"
        assert d.tld == "com"

    def test_domain_normalizes(self):
        d = DomainEntity(domain="EXAMPLE.COM")
        assert d.domain == "example.com"

    def test_domain_invalid(self):
        with pytest.raises(Exception):
            DomainEntity(domain="not_a_domain")

    def test_domain_with_registrar(self):
        d = DomainEntity(domain="test.org", registrar="GoDaddy")
        assert d.registrar == "GoDaddy"
        assert d.tld == "org"


class TestURLEntity:
    def test_valid_url(self):
        u = URLEntity(url="https://example.com/path?query=1")
        assert u.entity_type == EntityType.URL
        assert u.scheme == "https"
        assert u.domain == "example.com"
        assert u.path == "/path"

    def test_url_must_be_http(self):
        with pytest.raises(Exception):
            URLEntity(url="ftp://example.com/file")


class TestIPEntity:
    def test_valid_ipv4(self):
        ip = IPEntity(ip="192.168.1.1")
        assert ip.entity_type == EntityType.IP
        assert ip.ip_version == 4
        assert ip.normalized_value == "192.168.1.1"

    def test_valid_ipv6(self):
        ip = IPEntity(ip="2001:db8::1")
        assert ip.ip_version == 6

    def test_invalid_ip(self):
        with pytest.raises(Exception):
            IPEntity(ip="999.999.999.999")

    def test_ip_with_asn(self):
        ip = IPEntity(ip="8.8.8.8", asn="AS15169", country="US")
        assert ip.asn == "AS15169"


class TestASNEntity:
    def test_valid_asn(self):
        asn = ASNEntity(asn_number=15169, holder_name="Google")
        assert asn.entity_type == EntityType.ASN
        assert asn.normalized_value == "AS15169"

    def test_asn_out_of_range(self):
        with pytest.raises(Exception):
            ASNEntity(asn_number=0)

    def test_asn_negative(self):
        with pytest.raises(Exception):
            ASNEntity(asn_number=-1)


class TestNetworkEntity:
    def test_valid_cidr(self):
        net = NetworkEntity(cidr="192.168.0.0/24")
        assert net.entity_type == EntityType.NETWORK
        assert net.normalized_value == "192.168.0.0/24"

    def test_invalid_cidr(self):
        with pytest.raises(Exception):
            NetworkEntity(cidr="not_a_network")


class TestDNSRecordEntity:
    def test_valid_a_record(self):
        r = DNSRecordEntity(domain="example.com", record_type="A", record_value="1.2.3.4")
        assert r.entity_type == EntityType.DNS_RECORD
        assert "example.com" in r.normalized_value

    def test_invalid_record_type(self):
        with pytest.raises(Exception):
            DNSRecordEntity(domain="example.com", record_type="INVALID", record_value="x")


class TestCertificateEntity:
    def test_valid_cert(self):
        c = CertificateEntity(
            serial_number="1234",
            issuer="DigiCert",
            subject="example.com",
            fingerprint_sha256="a" * 64,
        )
        assert c.entity_type == EntityType.CERTIFICATE
        assert c.fingerprint_sha256 == "a" * 64

    def test_cert_normalizes_fingerprint(self):
        c = CertificateEntity(fingerprint_sha256="A" * 64)
        assert c.fingerprint_sha256 == "a" * 64


class TestWebsiteEntity:
    def test_valid_website(self):
        w = WebsiteEntity(title="Scam Page", content_hash="abc123")
        assert w.entity_type == EntityType.WEBSITE
        assert w.normalized_value == "abc123"

    def test_website_with_tech(self):
        w = WebsiteEntity(content_hash="x", technologies=["WordPress", "Nginx"])
        assert "WordPress" in w.technologies


class TestTelegramEntity:
    def test_valid_username(self):
        t = TelegramIdentifierEntity(username="testuser")
        assert t.entity_type == EntityType.TELEGRAM_IDENTIFIER
        assert "tg:@testuser" in t.normalized_value

    def test_strips_at_sign(self):
        t = TelegramIdentifierEntity(username="@testuser")
        assert t.username == "testuser"

    def test_invalid_username_too_short(self):
        with pytest.raises(Exception):
            TelegramIdentifierEntity(username="ab")

    def test_phone_identifier(self):
        t = TelegramIdentifierEntity(phone="+34612345678")
        assert "tg:+34612345678" in t.normalized_value


class TestSocialAccountEntity:
    def test_valid_social(self):
        s = SocialAccountEntity(platform="twitter", username="user1")
        assert s.entity_type == EntityType.SOCIAL_ACCOUNT
        assert s.normalized_value == "twitter:user1"

    def test_social_requires_platform(self):
        with pytest.raises(Exception):
            SocialAccountEntity(platform="", username="user1")


class TestCryptoWalletEntity:
    def test_valid_wallet(self):
        w = CryptoWalletEntity(blockchain="bitcoin", address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
        assert w.entity_type == EntityType.CRYPTO_WALLET
        assert "bitcoin:" in w.normalized_value

    def test_wallet_requires_blockchain(self):
        with pytest.raises(Exception):
            CryptoWalletEntity(blockchain="", address="x")


class TestTransactionEntity:
    def test_valid_transaction(self):
        t = TransactionEntity(
            blockchain="ethereum", tx_hash="0xabc123",
            from_address="0xfrom", to_address="0xto", amount=1.5
        )
        assert t.entity_type == EntityType.TRANSACTION
        assert "ethereum:0xabc123" in t.normalized_value


class TestPaymentIdentifierEntity:
    def test_valid_iban(self):
        p = PaymentIdentifierEntity(payment_type="iban", identifier="ES1234567890123456789012")
        assert p.entity_type == EntityType.PAYMENT_IDENTIFIER
        assert "iban:" in p.normalized_value


class TestDocumentEntity:
    def test_valid_document(self):
        d = DocumentEntity(doc_type="pdf", content_hash="sha256:abc123")
        assert d.entity_type == EntityType.DOCUMENT
        assert d.normalized_value == "sha256:abc123"


class TestImageEntity:
    def test_valid_image(self):
        i = ImageEntity(content_hash="sha256:xyz", width=800, height=600, format="png")
        assert i.entity_type == EntityType.IMAGE
        assert i.normalized_value == "sha256:xyz"


class TestReportEntity:
    def test_valid_report(self):
        r = ReportEntity(category="phishing", description="Fake banking site")
        assert r.entity_type == EntityType.REPORT
        assert r.status == "UNVERIFIED"

    def test_invalid_report_status(self):
        with pytest.raises(Exception):
            ReportEntity(status="INVALID")

    def test_report_with_risk(self):
        r = ReportEntity(category="investment_fraud", risk_level="HIGH")
        assert r.risk_level == "HIGH"


class TestCaseEntity:
    def test_valid_case(self):
        c = CaseEntity(case_number="CASE-2026-001", jurisdiction="ES")
        assert c.entity_type == EntityType.CASE
        assert c.case_status == "OPEN"

    def test_invalid_case_status(self):
        with pytest.raises(Exception):
            CaseEntity(case_status="INVALID")


class TestCampaignEntity:
    def test_valid_campaign(self):
        c = CampaignEntity(name="Phishing Wave 2026", fraud_type="phishing", severity="HIGH")
        assert c.entity_type == EntityType.CAMPAIGN
        assert c.campaign_status == "ACTIVE"

    def test_invalid_campaign_status(self):
        with pytest.raises(Exception):
            CampaignEntity(name="Test", campaign_status="INVALID")


class TestInfrastructureClusterEntity:
    def test_valid_cluster(self):
        ic = InfrastructureClusterEntity(
            cluster_name="Phishing Kit A",
            cluster_type="phishing_kit",
            member_entity_ids=["ENT-1", "ENT-2"],
        )
        assert ic.entity_type == EntityType.INFRASTRUCTURE_CLUSTER
        assert len(ic.member_entity_ids) == 2


class TestFraudPatternEntity:
    def test_valid_pattern(self):
        fp = FraudPatternEntity(
            pattern_type="investment_scam",
            description="Fake crypto investment",
            indicators=["guaranteed returns", "clone website"],
        )
        assert fp.entity_type == EntityType.FRAUD_PATTERN
        assert len(fp.indicators) == 2


class TestAlertEntity:
    def test_valid_alert(self):
        a = AlertEntity(alert_type="domain_change", priority="P0", entity_ids=["ENT-1"])
        assert a.entity_type == EntityType.ALERT
        assert a.alert_status == "NEW"

    def test_invalid_alert_status(self):
        with pytest.raises(Exception):
            AlertEntity(alert_status="INVALID")


class TestCountryEntity:
    def test_valid_country(self):
        c = CountryEntity(iso_code="ES", name="Spain", is_eu_member=True)
        assert c.entity_type == EntityType.COUNTRY
        assert c.normalized_value == "ES"

    def test_country_invalid_iso(self):
        with pytest.raises(Exception):
            CountryEntity(iso_code="ESP")  # 3 letters


# ─── Entity Factory Tests ───

class TestEntityFactory:
    def test_create_person(self):
        p = create_entity("PERSON", full_name="Test Person")
        assert isinstance(p, PersonEntity)
        assert p.full_name == "Test Person"

    def test_create_phone(self):
        p = create_entity("PHONE", e164="+34612345678")
        assert isinstance(p, PhoneEntity)

    def test_create_domain(self):
        d = create_entity("DOMAIN", domain="test.com")
        assert isinstance(d, DomainEntity)

    def test_create_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown entity type"):
            create_entity("UNKNOWN_TYPE")

    def test_factory_covers_all_types(self):
        """Every concrete EntityType enum value must have a factory mapping."""
        # OBSERVATION, EVIDENCE, SOURCE are meta-types (use BaseObservation, BaseEvidence, BaseSource)
        meta_types = {"OBSERVATION", "EVIDENCE", "SOURCE"}
        for et in EntityType:
            if et.value in meta_types:
                continue
            assert et.value in ENTITY_TYPE_TO_CLASS, f"Missing factory for {et.value}"


# ─── Relationship Model Tests ───

class TestRelationship:
    def test_valid_relationship(self):
        rel = Relationship(
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            relationship_type=RelationshipType.OWNS.value,
            source_id="SRC-1",
        )
        assert rel.relationship_type == "OWNS"

    def test_invalid_relationship_type(self):
        with pytest.raises(Exception):
            Relationship(
                from_entity_id="ENT-1",
                to_entity_id="ENT-2",
                relationship_type="INVALID_TYPE",
                source_id="SRC-1",
            )

    def test_self_relationship_blocked(self):
        with pytest.raises(Exception, match="Self-relationship"):
            Relationship(
                from_entity_id="ENT-1",
                to_entity_id="ENT-1",
                relationship_type=RelationshipType.RELATED_TO.value,
                source_id="SRC-1",
            )

    def test_relationship_has_provenance(self):
        rel = Relationship(
            from_entity_id="ENT-1",
            to_entity_id="ENT-2",
            relationship_type=RelationshipType.USES.value,
            source_id="SRC-1",
        )
        assert rel.source_id == "SRC-1"
        assert rel.confidence == Confidence.UNKNOWN


# ─── Relationship Factory Tests ───

class TestRelationshipFactory:
    def test_create_owns(self):
        rel = create_relationship("OWNS", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1")
        assert rel.relationship_type == "OWNS"

    def test_create_resolves_to(self):
        rel = create_relationship("RESOLVES_TO", from_entity_id="ENT-1", to_entity_id="ENT-2", source_id="SRC-1")
        assert rel.relationship_type == "RESOLVES_TO"

    def test_create_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown relationship type"):
            create_relationship("INVALID", from_entity_id="A", to_entity_id="B", source_id="S")

    def test_factory_covers_all_types(self):
        """Every RelationshipType enum value must have a factory mapping."""
        for rt in RelationshipType:
            assert rt.value in RELATIONSHIP_TYPE_TO_CLASS, f"Missing factory for {rt.value}"


# ─── Integration Tests ───

class TestEntityRelationshipIntegration:
    def test_domain_resolves_to_ip(self):
        domain = create_entity("DOMAIN", domain="example.com")
        ip = create_entity("IP", ip="1.2.3.4")
        rel = create_relationship(
            "RESOLVES_TO",
            from_entity_id=domain.id,
            to_entity_id=ip.id,
            source_id="SRC-1",
            confidence=Confidence.HIGH,
        )
        assert rel.from_entity_id == domain.id
        assert rel.to_entity_id == ip.id
        assert rel.confidence == Confidence.HIGH

    def test_person_owns_phone(self):
        person = create_entity("PERSON", full_name="John Smith")
        phone = create_entity("PHONE", e164="+34612345678")
        rel = create_relationship(
            "OWNS",
            from_entity_id=person.id,
            to_entity_id=phone.id,
            source_id="SRC-1",
        )
        assert rel.relationship_type == "OWNS"

    def test_entity_part_of_campaign(self):
        domain = create_entity("DOMAIN", domain="scam-site.com")
        campaign = create_entity("CAMPAIGN", name="Phishing Wave")
        rel = create_relationship(
            "PART_OF_CAMPAIGN",
            from_entity_id=domain.id,
            to_entity_id=campaign.id,
            source_id="SRC-1",
        )
        assert rel.relationship_type == "PART_OF_CAMPAIGN"

    def test_entity_has_classification(self):
        person = create_entity("PERSON", full_name="Restricted Person")
        assert hasattr(person, 'classification')
        assert person.classification.classification == DataClassification.PUBLIC

    def test_entity_has_provenance_field(self):
        domain = create_entity("DOMAIN", domain="test.com")
        assert domain.provenance is None  # Not set by default, but field exists
        assert hasattr(domain, 'provenance')

    def test_entity_has_confidence(self):
        ip = create_entity("IP", ip="8.8.8.8")
        assert ip.confidence == Confidence.UNKNOWN

    def test_entity_has_timestamps(self):
        entity = create_entity("DOMAIN", domain="example.com")
        assert entity.first_seen is not None
        assert entity.last_seen is not None
        assert isinstance(entity.first_seen, datetime)
        assert isinstance(entity.last_seen, datetime)
