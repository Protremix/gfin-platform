"""Unit tests for GFIN Fraud Pattern Engine."""

import pytest

from services.pattern_engine import FraudPattern, PatternEngine


class MockEntity:
    """Mock object entity for testing attribute-based pattern detection."""

    def __init__(self, entity_id, **kwargs):
        self.id = entity_id
        self.entity_id = entity_id
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestFraudPattern:
    def test_pattern_dataclass_creation(self):
        pat = FraudPattern(
            id="pat_001",
            pattern_type="SHARED_INFRASTRUCTURE",
            entities=["e1", "e2"],
            evidence={"indicator": "ip", "value": "1.1.1.1"},
            confidence=0.85,
        )
        assert pat.id == "pat_001"
        assert pat.pattern_type == "SHARED_INFRASTRUCTURE"
        assert pat.entities == ["e1", "e2"]
        assert pat.confidence == 0.85

    def test_pattern_to_dict(self):
        pat = FraudPattern(
            id="pat_001",
            pattern_type="SHARED_INFRASTRUCTURE",
            entities=["e1", "e2"],
        )
        d = pat.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "pat_001"
        assert d["pattern_type"] == "SHARED_INFRASTRUCTURE"
        assert d["verification_status"] == "UNVERIFIED"

    def test_default_unverified_status(self):
        pat = FraudPattern(id="p1", pattern_type="TEST")
        assert pat.verification_status == "UNVERIFIED"

    def test_default_limitations(self):
        pat = FraudPattern(id="p1", pattern_type="TEST")
        assert isinstance(pat.limitations, list)
        assert len(pat.limitations) > 0


class TestSharedInfrastructure:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_shared_ip(self, engine):
        entities = [
            {"id": "domain1.com", "ip": "192.0.2.1"},
            {"id": "domain2.net", "ip": "192.0.2.1"},
            {"id": "domain3.org", "ip": "198.51.100.2"},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "SHARED_INFRASTRUCTURE"
        assert sorted(patterns[0].entities) == ["domain1.com", "domain2.net"]
        assert patterns[0].evidence["indicator_type"] == "ip"
        assert patterns[0].evidence["shared_value"] == "192.0.2.1"

    def test_detect_shared_asn(self, engine):
        entities = [
            {"id": "d1", "asn": "AS12345"},
            {"id": "d2", "asn": "AS12345"},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert len(patterns) == 1
        assert patterns[0].evidence["indicator_type"] == "asn"

    def test_detect_shared_cert(self, engine):
        entities = [
            {"id": "d1", "cert": "cert_sha256_hash_123"},
            {"id": "d2", "cert": "cert_sha256_hash_123"},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert len(patterns) == 1
        assert patterns[0].evidence["indicator_type"] == "cert"

    def test_detect_shared_dns(self, engine):
        entities = [
            {"id": "d1", "dns": ["ns1.scamdns.com"]},
            {"id": "d2", "dns": ["ns1.scamdns.com"]},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert len(patterns) == 1
        assert patterns[0].evidence["indicator_type"] == "dns"

    def test_shared_infra_empty_entities(self, engine):
        patterns = engine.detect_shared_infrastructure([])
        assert patterns == []

    def test_shared_infra_single_entity(self, engine):
        patterns = engine.detect_shared_infrastructure([{"id": "d1", "ip": "1.1.1.1"}])
        assert patterns == []

    def test_shared_infra_no_shared_elements(self, engine):
        entities = [
            {"id": "d1", "ip": "1.1.1.1"},
            {"id": "d2", "ip": "2.2.2.2"},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert patterns == []

    def test_shared_infra_unverified_marking(self, engine):
        entities = [
            {"id": "d1", "ip": "1.1.1.1"},
            {"id": "d2", "ip": "1.1.1.1"},
        ]
        patterns = engine.detect_shared_infrastructure(entities)
        assert patterns[0].verification_status == "UNVERIFIED"


class TestSimilarContent:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_similar_template_hash(self, engine):
        entities = [
            {"id": "site1", "template": "crypto_scam_v1_hash"},
            {"id": "site2", "template": "crypto_scam_v1_hash"},
        ]
        patterns = engine.detect_similar_content(entities)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "SIMILAR_CONTENT"
        assert patterns[0].evidence["match_type"] == "template_hash"

    def test_detect_similar_text_jaccard(self, engine):
        text1 = "Welcome to global high yield investment platform. Guaranteed 100 percent daily return on bitcoin."
        text2 = "Welcome to global high yield investment platform. Guaranteed 100 percent daily return on Ethereum."
        entities = [
            {"id": "siteA", "content": text1},
            {"id": "siteB", "content": text2},
        ]
        patterns = engine.detect_similar_content(entities)
        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "SIMILAR_CONTENT"
        assert patterns[0].evidence["match_type"] == "text_jaccard"

    def test_similar_content_empty_entities(self, engine):
        assert engine.detect_similar_content([]) == []

    def test_similar_content_single_entity(self, engine):
        assert engine.detect_similar_content([{"id": "s1", "template": "t1"}]) == []

    def test_similar_content_unrelated_text(self, engine):
        entities = [
            {"id": "s1", "content": "completely different text about organic farming and agriculture in France"},
            {"id": "s2", "content": "quantum computing research laboratory and physics paper publications in Japan"},
        ]
        patterns = engine.detect_similar_content(entities)
        assert patterns == []


class TestPaymentCorrelation:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_shared_iban(self, engine):
        entities = [
            {"id": "shop1.com", "iban": "GB82WEST12345678901234"},
            {"id": "shop2.com", "iban": "GB82WEST12345678901234"},
        ]
        patterns = engine.detect_payment_correlation(entities)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "PAYMENT_CORRELATION"
        assert patterns[0].evidence["payment_type"] == "iban"
        assert patterns[0].evidence["shared_destination"] == "GB82WEST12345678901234"

    def test_detect_shared_wallet(self, engine):
        entities = [
            {"id": "invest1.io", "wallet": "0x1234567890abcdef1234567890abcdef12345678"},
            {"id": "invest2.io", "wallet": "0x1234567890abcdef1234567890abcdef12345678"},
        ]
        patterns = engine.detect_payment_correlation(entities)
        assert len(patterns) == 1
        assert patterns[0].evidence["payment_type"] == "wallet"

    def test_payment_correlation_empty_entities(self, engine):
        assert engine.detect_payment_correlation([]) == []

    def test_payment_correlation_no_shared_payments(self, engine):
        entities = [
            {"id": "e1", "iban": "IBAN1"},
            {"id": "e2", "iban": "IBAN2"},
        ]
        assert engine.detect_payment_correlation(entities) == []


class TestContactReuse:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_shared_phone(self, engine):
        entities = [
            {"id": "call1.com", "phone": "+447911123456"},
            {"id": "call2.com", "phone": "+447911123456"},
        ]
        patterns = engine.detect_contact_reuse(entities)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "CONTACT_REUSE"
        assert patterns[0].evidence["contact_type"] == "phone"

    def test_detect_shared_email(self, engine):
        entities = [
            {"id": "site1.com", "email": "support@fraud-center.org"},
            {"id": "site2.com", "email": "SUPPORT@FRAUD-CENTER.ORG"},
        ]
        patterns = engine.detect_contact_reuse(entities)
        assert len(patterns) == 1
        assert patterns[0].evidence["contact_type"] == "email"

    def test_contact_reuse_empty_entities(self, engine):
        assert engine.detect_contact_reuse([]) == []

    def test_contact_reuse_no_shared_contacts(self, engine):
        entities = [
            {"id": "e1", "email": "a@b.com"},
            {"id": "e2", "email": "x@y.com"},
        ]
        assert engine.detect_contact_reuse(entities) == []


class TestInfrastructureCluster:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_infra_cluster_multiple_dims(self, engine):
        e1 = {"id": "node1", "ip": "192.0.2.1", "asn": "AS12345", "cert": "cert_abc"}
        e2 = {"id": "node2", "ip": "192.0.2.1", "asn": "AS12345", "cert": "cert_abc"}

        patterns = engine.detect_infrastructure_cluster([e1, e2])
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "INFRASTRUCTURE_CLUSTER"
        assert patterns[0].evidence["matching_dimensions_count"] == 3

    def test_infra_cluster_single_dim_insufficient(self, engine):
        e1 = {"id": "node1", "ip": "192.0.2.1"}
        e2 = {"id": "node2", "ip": "192.0.2.1"}

        patterns = engine.detect_infrastructure_cluster([e1, e2])
        assert patterns == []

    def test_infra_cluster_empty_entities(self, engine):
        assert engine.detect_infrastructure_cluster([]) == []


class TestPotentialFraudNetwork:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_detect_potential_fraud_network_with_signals(self, engine):
        entities = [
            {"id": "e1", "ip": "1.1.1.1", "phone": "+123456", "wallet": "0xabc"},
            {"id": "e2", "ip": "1.1.1.1", "phone": "+123456", "wallet": "0xabc"},
            {"id": "e3", "ip": "1.1.1.1", "phone": "+999999"},
        ]
        net = engine.detect_potential_fraud_network(entities)
        assert isinstance(net, FraudPattern)
        assert net.pattern_type == "POTENTIAL_FRAUD_NETWORK"
        assert len(net.entities) == 3
        assert net.confidence > 0.8
        assert net.verification_status == "UNVERIFIED"

    def test_detect_potential_fraud_network_empty(self, engine):
        net = engine.detect_potential_fraud_network([])
        assert net.pattern_type == "POTENTIAL_FRAUD_NETWORK"
        assert net.confidence == 0.0
        assert net.entities == []
        assert net.verification_status == "UNVERIFIED"

    def test_detect_potential_fraud_network_single_entity(self, engine):
        net = engine.detect_potential_fraud_network([{"id": "solo"}])
        assert net.pattern_type == "POTENTIAL_FRAUD_NETWORK"
        assert net.confidence == 0.0

    def test_detect_potential_fraud_network_no_correlation(self, engine):
        entities = [
            {"id": "e1", "ip": "1.1.1.1"},
            {"id": "e2", "ip": "2.2.2.2"},
        ]
        net = engine.detect_potential_fraud_network(entities)
        assert net.confidence == 0.0

    def test_potential_fraud_network_unverified_marking(self, engine):
        entities = [
            {"id": "e1", "phone": "+12345"},
            {"id": "e2", "phone": "+12345"},
        ]
        net = engine.detect_potential_fraud_network(entities)
        assert net.verification_status == "UNVERIFIED"


class TestExplainPattern:
    @pytest.fixture
    def engine(self):
        return PatternEngine()

    def test_explain_pattern_shared_infra(self, engine):
        pat = FraudPattern(
            id="p1",
            pattern_type="SHARED_INFRASTRUCTURE",
            entities=["e1", "e2"],
            evidence={"indicator_type": "ip", "shared_value": "1.1.1.1", "entity_count": 2},
            confidence=0.85,
        )
        exp = engine.explain_pattern(pat)
        assert exp["pattern_id"] == "p1"
        assert exp["pattern_type"] == "SHARED_INFRASTRUCTURE"
        assert any("Shared Infrastructure" in line for line in exp["evidence_chain"])

    def test_explain_pattern_similar_content(self, engine):
        pat = FraudPattern(
            id="p2",
            pattern_type="SIMILAR_CONTENT",
            entities=["e1", "e2"],
            evidence={"shared_template": "tmpl_123"},
            confidence=0.80,
        )
        exp = engine.explain_pattern(pat)
        assert any("Content Match" in line for line in exp["evidence_chain"])

    def test_explain_pattern_payment_correlation(self, engine):
        pat = FraudPattern(
            id="p3",
            pattern_type="PAYMENT_CORRELATION",
            entities=["e1", "e2"],
            evidence={"payment_type": "iban", "shared_destination": "DE123456"},
            confidence=0.95,
        )
        exp = engine.explain_pattern(pat)
        assert any("Payment Correlation" in line for line in exp["evidence_chain"])

    def test_explain_pattern_contact_reuse(self, engine):
        pat = FraudPattern(
            id="p4",
            pattern_type="CONTACT_REUSE",
            entities=["e1", "e2"],
            evidence={"contact_type": "phone", "shared_contact": "+12345"},
            confidence=0.90,
        )
        exp = engine.explain_pattern(pat)
        assert any("Contact Reuse" in line for line in exp["evidence_chain"])

    def test_explain_pattern_infra_cluster(self, engine):
        pat = FraudPattern(
            id="p5",
            pattern_type="INFRASTRUCTURE_CLUSTER",
            entities=["e1", "e2"],
            evidence={"matching_dimensions": {"ip": ["1.1.1.1"], "asn": ["AS123"]}},
            confidence=0.90,
        )
        exp = engine.explain_pattern(pat)
        assert any("Infrastructure Cluster" in line for line in exp["evidence_chain"])

    def test_explain_pattern_potential_fraud_network(self, engine):
        pat = FraudPattern(
            id="p6",
            pattern_type="POTENTIAL_FRAUD_NETWORK",
            entities=["e1", "e2"],
            evidence={"sub_patterns_count": 3, "sub_pattern_types": ["SHARED_INFRASTRUCTURE", "CONTACT_REUSE"]},
            confidence=0.92,
        )
        exp = engine.explain_pattern(pat)
        assert any("Potential Fraud Network" in line for line in exp["evidence_chain"])

    def test_explain_pattern_required_keys(self, engine):
        pat = FraudPattern(id="p_keys", pattern_type="TEST")
        exp = engine.explain_pattern(pat)

        required_keys = [
            "pattern_id",
            "pattern_type",
            "evidence_chain",
            "evidence",
            "confidence",
            "limitations",
            "verification_status",
            "similarity",
            "features",
        ]
        for key in required_keys:
            assert key in exp

    def test_explain_pattern_uppercase_keys(self, engine):
        pat = FraudPattern(id="p_upper", pattern_type="TEST")
        exp = engine.explain_pattern(pat)

        for upper_key in ["SIMILARITY", "EVIDENCE", "FEATURES", "CONFIDENCE", "LIMITATIONS"]:
            assert upper_key in exp

    def test_explain_pattern_dict_input(self, engine):
        d = {
            "id": "p_dict",
            "pattern_type": "SHARED_INFRASTRUCTURE",
            "entities": ["e1"],
            "confidence": 0.7,
        }
        exp = engine.explain_pattern(d)
        assert exp["pattern_id"] == "p_dict"
        assert exp["verification_status"] == "UNVERIFIED"
