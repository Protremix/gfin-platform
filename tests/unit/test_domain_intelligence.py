"""Tests for Modules 10/11/12 — Domain, Certificate, IP/ASN Intelligence.

Per §14 (Domain Intelligence): domain profile with RDAP, registrar, creation date,
nameservers, status, DNS, historical observations, certificates, related domains,
infrastructure clusters, fraud reports, campaigns, first/last seen.
Per §15 (Certificate Intelligence): CT logs, certificates, SANs, domain relationships,
certificate timelines, related infrastructure, newly observed domains.
Per §16 (IP/ASN Intelligence): current/historical IP, prefix, ASN, network, provider,
country, routing metadata, abuse contact, related domains.
"""

import pytest
from datetime import datetime

from services.domain_intelligence import (
    DomainIntelligenceService, RDAPInfo, DomainProfile,
    CertificateIntelligenceService,
    IPASNIntelligenceService,
)
from services.infrastructure_intelligence import (
    InfrastructureIntelligenceService, DNSRecordType, InfraRelationType,
)
from schemas.base import utc_now


@pytest.fixture
def infra():
    return InfrastructureIntelligenceService()


# ═══════════════════════════════════════════════
# DOMAIN INTELLIGENCE (§14)
# ═══════════════════════════════════════════════

class TestDomainIntelligence:
    def test_register_rdap_info(self, infra):
        svc = DomainIntelligenceService(infra)
        rdap = svc.register_rdap_info("evil.com", registrar="EvilRegistrar", creation_date=datetime(2024, 1, 1))
        assert rdap.registrar == "EvilRegistrar"
        assert rdap.is_synthetic is True

    def test_rdap_non_public_requires_legal_basis(self, infra):
        svc = DomainIntelligenceService(infra)
        with pytest.raises(ValueError, match="legal_basis"):
            svc.register_rdap_info("secret.com", is_public_data=False)

    def test_rdap_non_public_with_legal_basis(self, infra):
        svc = DomainIntelligenceService(infra)
        rdap = svc.register_rdap_info("secret.com", is_public_data=False, legal_basis="Court order #123")
        assert rdap.is_public_data is False
        assert rdap.legal_basis == "Court order #123"

    def test_domain_profile_aggregates_all(self, infra):
        svc = DomainIntelligenceService(infra)
        infra.register_dns_record("evil.com", DNSRecordType.A, "192.168.1.1")
        svc.register_rdap_info("evil.com", registrar="TestReg")
        svc.add_related_domain("evil.com", "phishing.com")
        svc.link_fraud_report("evil.com", "RPT-001")
        svc.link_campaign("evil.com", "CMP-001")

        profile = svc.get_domain_profile("evil.com")
        assert profile.domain == "evil.com"
        assert profile.rdap_info is not None
        assert "A" in profile.dns_records
        assert "phishing.com" in profile.related_domains
        assert "RPT-001" in profile.fraud_report_ids
        assert "CMP-001" in profile.campaign_ids
        assert profile.is_synthetic is True

    def test_domain_profile_empty(self, infra):
        svc = DomainIntelligenceService(infra)
        profile = svc.get_domain_profile("nothing.com")
        assert profile.domain == "nothing.com"
        assert profile.rdap_info is None

    def test_related_domain_bidirectional(self, infra):
        svc = DomainIntelligenceService(infra)
        svc.add_related_domain("a.com", "b.com", bidirectional=True)
        profile_a = svc.get_domain_profile("a.com")
        profile_b = svc.get_domain_profile("b.com")
        assert "b.com" in profile_a.related_domains
        assert "a.com" in profile_b.related_domains

    def test_domain_metrics(self, infra):
        svc = DomainIntelligenceService(infra)
        svc.register_rdap_info("a.com")
        svc.register_rdap_info("b.com")
        svc.add_related_domain("a.com", "b.com")
        svc.link_fraud_report("a.com", "RPT-001")
        metrics = svc.get_metrics()
        assert metrics["total_domains"] == 2
        assert metrics["total_related_domain_links"] >= 2  # bidirectional
        assert metrics["total_fraud_report_links"] == 1


# ═══════════════════════════════════════════════
# CERTIFICATE INTELLIGENCE (§15)
# ═══════════════════════════════════════════════

class TestCertificateIntelligence:
    def test_register_certificate(self, infra):
        svc = CertificateIntelligenceService(infra)
        cert = svc.register_certificate("evil.com", issuer="CA", san_domains=["www.evil.com"])
        assert cert.domain == "evil.com"
        assert cert.issuer == "CA"
        assert cert.is_synthetic is True

    def test_certificate_timeline(self, infra):
        svc = CertificateIntelligenceService(infra)
        svc.register_certificate("evil.com", issuer="CA1")
        svc.register_certificate("evil.com", issuer="CA2")
        timeline = svc.get_certificate_timeline("evil.com")
        assert len(timeline) == 2

    def test_newly_observed_domains(self, infra):
        svc = CertificateIntelligenceService(infra)
        svc.register_certificate("evil.com", san_domains=["new-domain.com", "www.evil.com"])
        new_domains = svc.get_newly_observed_domains()
        assert len(new_domains) >= 1
        assert any(d["domain"] == "new-domain.com" for d in new_domains)

    def test_get_domains_by_san(self, infra):
        svc = CertificateIntelligenceService(infra)
        svc.register_certificate("a.com", san_domains=["shared.com"])
        svc.register_certificate("b.com", san_domains=["shared.com"])
        domains = svc.get_domains_by_san("shared.com")
        assert "a.com" in domains
        assert "b.com" in domains

    def test_certificate_relationships(self, infra):
        svc = CertificateIntelligenceService(infra)
        svc.register_certificate("a.com", san_domains=["shared.com"])
        svc.register_certificate("b.com", san_domains=["shared.com"])
        rels = svc.get_certificate_relationships("a.com")
        assert any(r["related_domain"] == "b.com" for r in rels)

    def test_certificate_metrics(self, infra):
        svc = CertificateIntelligenceService(infra)
        svc.register_certificate("a.com", san_domains=["x.com"])
        metrics = svc.get_metrics()
        assert metrics["total_certificates"] == 1
        assert metrics["total_domains_with_certs"] == 1


# ═══════════════════════════════════════════════
# IP / ASN INTELLIGENCE (§16)
# ═══════════════════════════════════════════════

class TestIPASNIntelligence:
    def test_register_ip_info(self, infra):
        svc = IPASNIntelligenceService(infra)
        info = svc.register_ip_info("1.2.3.4", asn="AS999", provider="HostCo", country="US")
        assert info.ip_address == "1.2.3.4"
        assert info.is_synthetic is True

    def test_unlicensed_source_rejected(self, infra):
        svc = IPASNIntelligenceService(infra)
        with pytest.raises(ValueError, match="source_licensed"):
            svc.register_ip_info("1.1.1.1", source_licensed=False)

    def test_register_asn_with_abuse_contact(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.register_asn_info("AS999", organization="Org", abuse_contact="abuse@org.com")
        assert svc.get_abuse_contact("AS999") == "abuse@org.com"

    def test_link_domain_ip(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.link_domain_ip("evil.com", "192.168.1.1")
        svc.link_domain_ip("evil.com", "10.0.0.1")
        history = svc.get_domain_ip_history("evil.com")
        assert "192.168.1.1" in history
        assert "10.0.0.1" in history

    def test_related_domains_by_ip(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.link_domain_ip("a.com", "1.1.1.1")
        svc.link_domain_ip("b.com", "1.1.1.1")
        related = svc.get_related_domains_by_ip("1.1.1.1")
        assert "a.com" in related
        assert "b.com" in related

    def test_ip_profile(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.register_ip_info("1.2.3.4", asn="AS999", country="US")
        svc.register_asn_info("AS999", organization="Org", abuse_contact="abuse@org.com")
        svc.link_domain_ip("evil.com", "1.2.3.4")
        profile = svc.get_ip_profile("1.2.3.4")
        assert profile["abuse_contact"] == "abuse@org.com"
        assert "evil.com" in profile["related_domains"]
        assert profile["is_synthetic"] is True

    def test_asn_profile(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.register_asn_info("AS999", organization="Org")
        profile = svc.get_asn_profile("AS999")
        assert profile["info"] is not None
        assert profile["is_synthetic"] is True

    def test_ip_metrics(self, infra):
        svc = IPASNIntelligenceService(infra)
        svc.register_ip_info("1.1.1.1", asn="AS1")
        svc.link_domain_ip("a.com", "1.1.1.1")
        metrics = svc.get_metrics()
        assert metrics["total_ips_tracked"] == 1
        assert metrics["total_domain_ip_links"] == 1


# ═══════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════

class TestIntegration:
    def test_full_domain_workflow(self, infra):
        """Full domain intelligence workflow across all three services."""
        # Register infrastructure data
        infra.register_dns_record("evil.com", DNSRecordType.A, "192.168.1.1")
        infra.register_dns_record("evil.com", DNSRecordType.NS, "ns1.evil.com")

        # Domain intelligence
        dom_svc = DomainIntelligenceService(infra)
        dom_svc.register_rdap_info("evil.com", registrar="EvilReg", creation_date=datetime(2024, 1, 1))
        dom_svc.add_related_domain("evil.com", "phishing.com")
        dom_svc.link_fraud_report("evil.com", "RPT-001")
        dom_svc.link_campaign("evil.com", "CMP-001")

        # Certificate intelligence
        cert_svc = CertificateIntelligenceService(infra)
        cert_svc.register_certificate("evil.com", issuer="CA", san_domains=["www.evil.com", "mail.evil.com"])

        # IP/ASN intelligence
        ip_svc = IPASNIntelligenceService(infra)
        ip_svc.register_ip_info("192.168.1.1", asn="AS12345", provider="EvilHost", country="XX")
        ip_svc.register_asn_info("AS12345", organization="EvilCorp", abuse_contact="abuse@evilcorp.com")
        ip_svc.link_domain_ip("evil.com", "192.168.1.1")

        # Verify domain profile
        profile = dom_svc.get_domain_profile("evil.com")
        assert profile.rdap_info is not None
        assert "A" in profile.dns_records
        assert len(profile.certificates) == 1
        assert "phishing.com" in profile.related_domains
        assert "RPT-001" in profile.fraud_report_ids
        assert "CMP-001" in profile.campaign_ids

        # Verify IP profile
        ip_profile = ip_svc.get_ip_profile("192.168.1.1")
        assert ip_profile["abuse_contact"] == "abuse@evilcorp.com"
        assert "evil.com" in ip_profile["related_domains"]

        # Verify cert relationships
        cert_rels = cert_svc.get_certificate_relationships("evil.com")
        assert isinstance(cert_rels, list)
