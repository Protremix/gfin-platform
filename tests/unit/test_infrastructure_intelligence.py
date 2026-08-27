"""Comprehensive tests for Module 09 — Infrastructure Intelligence.

Per Master Spec §13:
For domains, collect: A/AAAA/MX/NS/CNAME/TXT, DNS history, IP history, ASN,
network info, provider info, TLS certs, CT observations, redirect chains,
tech fingerprints, related domains, historical infrastructure.
Interpretation rules: IP != owner, ASN != criminal, CDN != origin,
shared hosting != common ownership, no criminal ownership from single correlation.
"""

import pytest

from services.infrastructure_intelligence import (
    DNSRecordType,
    InfraRelationType,
    InfrastructureIntelligenceService,
    check_interpretation_rules,
    validate_attribution,
)

# ─── Fixtures ───


@pytest.fixture
def svc():
    return InfrastructureIntelligenceService()


@pytest.fixture
def populated_svc(svc):
    """Pre-populated with test data."""
    svc.register_dns_record("evil.com", DNSRecordType.A, "192.168.1.1")
    svc.register_dns_record("evil.com", DNSRecordType.AAAA, "::1")
    svc.register_dns_record("evil.com", DNSRecordType.MX, "mail.evil.com")
    svc.register_dns_record("evil.com", DNSRecordType.NS, "ns1.evil.com")
    svc.register_dns_record("evil.com", DNSRecordType.TXT, "v=spf1 -all")
    svc.register_ip_info("192.168.1.1", asn="AS12345", provider="EvilHost", is_cdn=False)
    svc.register_asn_info("AS12345", organization="EvilCorp", country="XX")
    svc.register_certificate(
        "evil.com", issuer="Let's Encrypt", subject="evil.com", san_domains=["www.evil.com"]
    )
    svc.register_redirect_chain(
        "https://evil.com",
        [{"url": "https://evil.com", "status_code": 301, "location": "https://evil.com/login"}],
    )
    svc.register_tech_fingerprint(
        "evil.com", technologies=[{"name": "Nginx", "version": "1.18", "category": "web-server"}]
    )
    return svc


# ═══════════════════════════════════════════════
# DNS OBSERVATIONS
# ═══════════════════════════════════════════════


class TestDNSObservations:
    def test_register_dns_record(self, svc):
        obs = svc.register_dns_record("evil.com", DNSRecordType.A, "192.168.1.1")
        assert obs.domain == "evil.com"
        assert obs.value == "192.168.1.1"
        assert obs.is_synthetic is True

    def test_get_dns_records_all(self, populated_svc):
        records = populated_svc.get_dns_records("evil.com")
        assert len(records) == 5

    def test_get_dns_records_by_type(self, populated_svc):
        records = populated_svc.get_dns_records("evil.com", "A")
        assert len(records) == 1
        assert records[0].value == "192.168.1.1"

    def test_dns_record_provenance(self, svc):
        obs = svc.register_dns_record("evil.com", DNSRecordType.A, "1.2.3.4")
        assert obs.provenance is not None
        assert obs.provenance.source_id == "SRC-INFRA-MOCK"

    def test_dns_record_synthetic_flag(self, svc):
        obs = svc.register_dns_record("test.com", DNSRecordType.A, "1.1.1.1")
        assert obs.is_synthetic is True

    def test_dns_history_tracking(self, svc):
        svc.register_dns_record("test.com", DNSRecordType.A, "1.1.1.1")
        svc.register_dns_record("test.com", DNSRecordType.A, "2.2.2.2")
        history = svc.get_dns_history("test.com")
        assert len(history) == 2

    def test_get_dns_records_empty(self, svc):
        records = svc.get_dns_records("nonexistent.com")
        assert records == []


# ═══════════════════════════════════════════════
# IP / ASN INFO
# ═══════════════════════════════════════════════


class TestIPASN:
    def test_register_ip_info(self, svc):
        info = svc.register_ip_info("1.2.3.4", asn="AS999", provider="TestHost")
        assert info.ip_address == "1.2.3.4"
        assert info.asn == "AS999"
        assert info.is_synthetic is True

    def test_get_ip_info(self, populated_svc):
        info = populated_svc.get_ip_info("192.168.1.1")
        assert info is not None
        assert info.asn == "AS12345"

    def test_get_ip_info_not_found(self, svc):
        assert svc.get_ip_info("0.0.0.0") is None

    def test_register_asn_info(self, svc):
        info = svc.register_asn_info("AS999", organization="TestOrg", country="US")
        assert info.asn == "AS999"
        assert info.organization == "TestOrg"

    def test_get_asn_info(self, populated_svc):
        info = populated_svc.get_asn_info("AS12345")
        assert info is not None
        assert info.organization == "EvilCorp"

    def test_ip_independent_from_ownership(self, svc):
        """IP != owner: IP info should not include ownership fields."""
        info = svc.register_ip_info("1.2.3.4", provider="HostCo")
        assert not hasattr(info, "owner")
        assert not hasattr(info, "criminal")


# ═══════════════════════════════════════════════
# CERTIFICATE OBSERVATIONS
# ═══════════════════════════════════════════════


class TestCertificates:
    def test_register_certificate(self, svc):
        cert = svc.register_certificate("evil.com", issuer="CA", subject="evil.com")
        assert cert.domain == "evil.com"
        assert cert.issuer == "CA"
        assert cert.is_synthetic is True

    def test_get_certificates(self, populated_svc):
        certs = populated_svc.get_certificates("evil.com")
        assert len(certs) == 1
        assert certs[0].subject == "evil.com"

    def test_get_certificates_empty(self, svc):
        assert svc.get_certificates("nothing.com") == []

    def test_certificate_san_domains(self, svc):
        cert = svc.register_certificate("test.com", san_domains=["a.test.com", "b.test.com"])
        assert len(cert.san_domains) == 2


# ═══════════════════════════════════════════════
# REDIRECT CHAINS
# ═══════════════════════════════════════════════


class TestRedirectChains:
    def test_register_redirect_chain(self, svc):
        chain = svc.register_redirect_chain(
            "https://a.com",
            [
                {"url": "https://a.com", "status_code": 301, "location": "https://b.com"},
                {"url": "https://b.com", "status_code": 302, "location": "https://c.com"},
            ],
        )
        assert chain.start_url == "https://a.com"
        assert chain.total_hops == 2
        assert chain.final_url == "https://c.com"

    def test_get_redirect_chain(self, populated_svc):
        chain = populated_svc.get_redirect_chain("https://evil.com")
        assert chain is not None
        assert len(chain.hops) == 1

    def test_get_redirect_chain_not_found(self, svc):
        assert svc.get_redirect_chain("https://nothing.com") is None


# ═══════════════════════════════════════════════
# TECHNOLOGY FINGERPRINTS
# ═══════════════════════════════════════════════


class TestTechFingerprints:
    def test_register_tech_fingerprint(self, svc):
        fp = svc.register_tech_fingerprint(
            "evil.com",
            technologies=[{"name": "Apache", "version": "2.4", "category": "web-server"}],
        )
        assert fp.domain == "evil.com"
        assert len(fp.technologies) == 1

    def test_get_tech_fingerprint(self, populated_svc):
        fp = populated_svc.get_tech_fingerprint("evil.com")
        assert fp is not None
        assert fp.technologies[0]["name"] == "Nginx"

    def test_get_tech_fingerprint_not_found(self, svc):
        assert svc.get_tech_fingerprint("nothing.com") is None


# ═══════════════════════════════════════════════
# RELATIONSHIPS
# ═══════════════════════════════════════════════


class TestRelationships:
    def test_add_non_attribution_relationship(self, svc):
        rel, reason = svc.add_relationship("evil.com", "192.168.1.1", InfraRelationType.RESOLVES_TO)
        assert rel is not None
        assert "created" in reason.lower()

    def test_add_attribution_without_evidence_fails(self, svc):
        rel, reason = svc.add_relationship("john", "evil.com", InfraRelationType.OWNS)
        assert rel is None
        assert "INSUFFICIENT_DATA" in reason

    def test_add_attribution_with_evidence_works(self, svc):
        rel, reason = svc.add_relationship(
            "john",
            "evil.com",
            InfraRelationType.OWNS,
            evidence_id="EVD-001",
            analyst_justification="WHOIS match",
        )
        assert rel is not None
        assert "created" in reason.lower()

    def test_criminal_association_without_correlation_fails(self, svc):
        rel, reason = svc.add_relationship(
            "john",
            "evil.com",
            InfraRelationType.CRIMINAL_ASSOCIATION,
            evidence_id="EVD-001",
            analyst_justification="Suspect",
        )
        assert rel is None
        assert "multiple corroborating" in reason

    def test_criminal_association_with_correlation_works(self, svc):
        rel, _ = svc.add_relationship(
            "john",
            "evil.com",
            InfraRelationType.CRIMINAL_ASSOCIATION,
            evidence_id="EVD-001",
            analyst_justification="Corroborated",
            has_multiple_correlations=True,
        )
        assert rel is not None

    def test_get_relationships_by_entity(self, svc):
        svc.add_relationship("evil.com", "1.2.3.4", InfraRelationType.RESOLVES_TO)
        svc.add_relationship("evil.com", "5.6.7.8", InfraRelationType.HOSTED_ON)
        rels = svc.get_relationships(entity="evil.com")
        assert len(rels) == 2

    def test_get_relationships_by_type(self, svc):
        svc.add_relationship("a.com", "1.1.1.1", InfraRelationType.RESOLVES_TO)
        svc.add_relationship("a.com", "2.2.2.2", InfraRelationType.HOSTED_ON)
        rels = svc.get_relationships(relationship_type="resolves_to")
        assert len(rels) == 1


# ═══════════════════════════════════════════════
# INTERPRETATION RULES
# ═══════════════════════════════════════════════


class TestInterpretationRules:
    def test_ip_not_owner(self):
        rules = check_interpretation_rules("resolves_to")
        assert any(r.rule_name == "IP != owner" and r.passed for r in rules)
        assert any(r.qualifying_language == "resolves to" for r in rules)

    def test_asn_not_criminal(self):
        rules = check_interpretation_rules("announced_by")
        assert any(r.rule_name == "ASN != criminal" for r in rules)

    def test_cdn_not_origin(self):
        rules = check_interpretation_rules("uses_cdn")
        assert any(r.rule_name == "CDN != origin server" for r in rules)

    def test_shared_hosting_not_ownership(self):
        rules = check_interpretation_rules("hosted_on")
        assert any(r.rule_name == "Shared hosting != common ownership" for r in rules)

    def test_criminal_single_correlation_fails(self):
        rules = check_interpretation_rules("criminal_association", has_multiple_correlations=False)
        assert any(
            (not r.passed
            and "single correlation" in r.message.lower())
            or "multiple" in r.message.lower()
            for r in rules
        )

    def test_criminal_multi_correlation_passes(self):
        rules = check_interpretation_rules(
            "criminal_association",
            has_multiple_correlations=True,
            evidence_id="EVD-001",
            analyst_justification="ok",
        )
        # The criminal association check should pass
        criminal_rules = [r for r in rules if "correlation" in r.rule_name.lower()]
        assert any(r.passed for r in criminal_rules)

    def test_attribution_no_evidence_fails(self):
        rules = check_interpretation_rules("owns", evidence_id=None)
        assert any(not r.passed and "evidence" in r.message.lower() for r in rules)

    def test_attribution_no_justification_fails(self):
        rules = check_interpretation_rules("owns", evidence_id="EVD-001", analyst_justification="")
        assert any(not r.passed and "justification" in r.message.lower() for r in rules)

    def test_non_attribution_no_rules(self):
        rules = check_interpretation_rules("resolves_to")
        # Non-attribution edges should pass without evidence requirement
        assert all(r.passed for r in rules)


# ═══════════════════════════════════════════════
# VALIDATE ATTRIBUTION
# ═══════════════════════════════════════════════


class TestValidateAttribution:
    def test_non_attribution_valid(self):
        valid, _reason = validate_attribution("resolves_to")
        assert valid

    def test_attribution_without_evidence_invalid(self):
        valid, reason = validate_attribution("owns")
        assert not valid
        assert "INSUFFICIENT_DATA" in reason

    def test_attribution_with_evidence_valid(self):
        valid, _reason = validate_attribution(
            "owns", evidence_id="EVD-001", analyst_justification="WHOIS"
        )
        assert valid

    def test_criminal_without_correlation_invalid(self):
        valid, _reason = validate_attribution(
            "criminal_association", evidence_id="EVD-001", analyst_justification="ok"
        )
        assert not valid

    def test_criminal_with_correlation_valid(self):
        valid, _reason = validate_attribution(
            "criminal_association",
            evidence_id="EVD-001",
            analyst_justification="ok",
            has_multiple_correlations=True,
        )
        assert valid


# ═══════════════════════════════════════════════
# DOMAIN PROFILE
# ═══════════════════════════════════════════════


class TestDomainProfile:
    def test_domain_profile_aggregates_all(self, populated_svc):
        populated_svc.add_relationship("evil.com", "192.168.1.1", InfraRelationType.RESOLVES_TO)
        profile = populated_svc.get_domain_profile("evil.com")
        assert profile["domain"] == "evil.com"
        assert "A" in profile["dns_records"]
        assert "MX" in profile["dns_records"]
        assert "192.168.1.1" in profile["ip_addresses"]
        assert len(profile["ip_info"]) == 1
        assert len(profile["asn_info"]) == 1
        assert len(profile["certificates"]) == 1
        assert len(profile["relationships"]) == 1
        assert profile["dns_history_count"] == 5
        assert profile["is_synthetic"] is True

    def test_domain_profile_empty(self, svc):
        profile = svc.get_domain_profile("nothing.com")
        assert profile["domain"] == "nothing.com"
        assert profile["dns_records"] == {}
        assert profile["ip_addresses"] == []


# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════


class TestMetrics:
    def test_empty_metrics(self, svc):
        metrics = svc.get_metrics()
        assert metrics["total_domains_tracked"] == 0

    def test_populated_metrics(self, populated_svc):
        metrics = populated_svc.get_metrics()
        assert metrics["total_domains_tracked"] == 1
        assert metrics["total_dns_observations"] == 5
        assert metrics["total_ip_addresses"] == 1
        assert metrics["total_asns"] == 1
        assert metrics["total_certificates"] == 1
        assert metrics["total_redirect_chains"] == 1
        assert metrics["total_tech_fingerprints"] == 1


# ═══════════════════════════════════════════════
# SYNTHETIC DATA SAFETY
# ═══════════════════════════════════════════════


class TestSyntheticSafety:
    def test_dns_observations_marked_synthetic(self, svc):
        obs = svc.register_dns_record("test.com", DNSRecordType.A, "1.1.1.1")
        assert obs.is_synthetic is True

    def test_ip_info_marked_synthetic(self, svc):
        info = svc.register_ip_info("1.1.1.1")
        assert info.is_synthetic is True

    def test_asn_info_marked_synthetic(self, svc):
        info = svc.register_asn_info("AS1")
        assert info.is_synthetic is True

    def test_certificate_marked_synthetic(self, svc):
        cert = svc.register_certificate("test.com")
        assert cert.is_synthetic is True

    def test_relationship_marked_synthetic(self, svc):
        rel, _ = svc.add_relationship("a", "b", InfraRelationType.RESOLVES_TO)
        assert rel.is_synthetic is True

    def test_domain_profile_synthetic(self, svc):
        svc.register_dns_record("test.com", DNSRecordType.A, "1.1.1.1")
        profile = svc.get_domain_profile("test.com")
        assert profile["is_synthetic"] is True


# ═══════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════


class TestIntegration:
    def test_full_infrastructure_profile(self, populated_svc):
        """Full workflow: register data, add relationships, get profile."""
        # Add relationships
        populated_svc.add_relationship("evil.com", "192.168.1.1", InfraRelationType.RESOLVES_TO)
        populated_svc.add_relationship("192.168.1.1", "AS12345", InfraRelationType.ANNOUNCED_BY)
        populated_svc.add_relationship("evil.com", "192.168.1.1", InfraRelationType.HOSTED_ON)

        profile = populated_svc.get_domain_profile("evil.com")
        assert (
            len(profile["relationships"]) == 2
        )  # resolves_to + hosted_on (announced_by is IP→ASN, not domain)
        assert profile["dns_history_count"] == 5

        # Verify interpretation rules applied
        for rel in profile["relationships"]:
            if rel.relationship_type == "resolves_to" or (
                hasattr(rel.relationship_type, "value")
                and rel.relationship_type.value == "resolves_to"
            ):
                rules = check_interpretation_rules("resolves_to")
                assert all(r.passed for r in rules)

    def test_attribution_workflow(self, svc):
        """Full attribution workflow with evidence."""
        svc.register_dns_record("evil.com", DNSRecordType.A, "1.2.3.4")
        svc.add_relationship("evil.com", "1.2.3.4", InfraRelationType.RESOLVES_TO)
        svc.add_relationship("1.2.3.4", "AS999", InfraRelationType.ANNOUNCED_BY)

        # Attempt criminal attribution without evidence
        rel, _ = svc.add_relationship(
            "john", "evil.com", InfraRelationType.CRIMINAL_ASSOCIATION
        )
        assert rel is None

        # With evidence + justification + correlations
        rel, _ = svc.add_relationship(
            "john",
            "evil.com",
            InfraRelationType.CRIMINAL_ASSOCIATION,
            evidence_id="EVD-001",
            analyst_justification="Corroborated by 3 independent reports",
            has_multiple_correlations=True,
        )
        assert rel is not None

        metrics = svc.get_metrics()
        assert metrics["attribution_edges"] == 1
