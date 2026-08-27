"""Unit tests for GFIN Campaign DNA Engine."""

import pytest

from services.campaign_dna import CampaignDNAEngine, CampaignSignature


class MockCampaign:
    """Mock object campaign for testing attribute-based feature extraction."""

    def __init__(self, campaign_id, **kwargs):
        self.id = campaign_id
        self.campaign_id = campaign_id
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestCampaignSignature:
    def test_dataclass_creation(self):
        sig = CampaignSignature(
            id="sig_123",
            campaign_id="camp_001",
            features={"language": ["en"]},
            feature_hash="abc123hash",
            similarity_threshold=0.8,
            confidence=0.9,
        )
        assert sig.id == "sig_123"
        assert sig.campaign_id == "camp_001"
        assert sig.features == {"language": ["en"]}
        assert sig.feature_hash == "abc123hash"
        assert sig.similarity_threshold == 0.8
        assert sig.confidence == 0.9

    def test_to_dict(self):
        sig = CampaignSignature(
            id="sig_123",
            campaign_id="camp_001",
            features={"language": ["en"]},
            feature_hash="abc123hash",
        )
        d = sig.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "sig_123"
        assert d["campaign_id"] == "camp_001"
        assert d["verification_status"] == "UNVERIFIED"

    def test_default_unverified_status(self):
        sig = CampaignSignature(id="s1", campaign_id="c1")
        assert sig.verification_status == "UNVERIFIED"

    def test_default_limitations_present(self):
        sig = CampaignSignature(id="s1", campaign_id="c1")
        assert isinstance(sig.limitations, list)
        assert len(sig.limitations) > 0


class TestFeatureExtraction:
    @pytest.fixture
    def engine(self):
        return CampaignDNAEngine()

    def test_extract_features_dict_campaign(self, engine):
        campaign = {
            "id": "c_dict",
            "language": "en",
            "phrasing": ["crypto investment guaranteed return"],
            "domains": ["scam-invest.com", "fake-crypto.net"],
            "phones": ["+1234567890"],
            "emails": ["support@scam-invest.com"],
            "hosting": ["AWS-AS16509"],
            "certificates": ["sha256_cert_fingerprint_01"],
            "dns": ["ns1.scam-dns.com"],
            "payments": ["GB82WEST12345678901234"],
            "wallets": ["0x1234567890abcdef1234567890abcdef12345678"],
            "timing": ["2026-08-01T00:00:00Z"],
            "ips": ["1.2.3.4"],
            "countries": ["US", "GB"],
            "reports": ["rep_001", "rep_002"],
        }
        feat = engine.extract_features(campaign)
        assert feat["language"] == ["en"]
        assert "crypto investment guaranteed return" in feat["phrasing"]
        assert "scam-invest.com" in feat["domain_patterns"]
        assert "+1234567890" in feat["phone_patterns"]
        assert "support@scam-invest.com" in feat["email_patterns"]
        assert "AWS-AS16509" in feat["hosting_patterns"]
        assert "sha256_cert_fingerprint_01" in feat["certificate_reuse"]
        assert "ns1.scam-dns.com" in feat["dns_patterns"]
        assert "GB82WEST12345678901234" in feat["payment_destinations"]
        assert "0x1234567890abcdef1234567890abcdef12345678" in feat["wallet_relationships"]
        assert "1.2.3.4" in feat["infrastructure"]
        assert "US" in feat["geography"]
        assert "rep_001" in feat["victim_reports"]

    def test_extract_features_object_campaign(self, engine):
        obj = MockCampaign(
            campaign_id="c_obj",
            language="es",
            phrases=["invierte hoy mismo"],
            domain_list=["invertir-facil.com"],
            phone_numbers=["+34600000000"],
            email_addresses=["contact@invertir-facil.com"],
            asn_list=["HETZNER-AS24940"],
            certs=["cert_hash_es"],
            nameservers=["ns1.hetzner.com"],
            ibans=["ES9121000418450200051332"],
            crypto_addresses=["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],
            timestamps=["2026-08-20"],
            ip_addresses=["83.136.252.48"],
            regions=["ES"],
            report_ids=["rep_es_1"],
        )
        feat = engine.extract_features(obj)
        assert feat["language"] == ["es"]
        assert "invierte hoy mismo" in feat["phrasing"]
        assert "invertir-facil.com" in feat["domain_patterns"]
        assert "+34600000000" in feat["phone_patterns"]
        assert "contact@invertir-facil.com" in feat["email_patterns"]
        assert "HETZNER-AS24940" in feat["hosting_patterns"]
        assert "cert_hash_es" in feat["certificate_reuse"]

    def test_extract_features_nested_features(self, engine):
        campaign = {
            "id": "c_nested",
            "features": {
                "language": ["fr"],
                "website_structure": ["dom_fingerprint_v1"],
                "geography": ["FR", "BE"],
            }
        }
        feat = engine.extract_features(campaign)
        assert feat["language"] == ["fr"]
        assert feat["website_structure"] == ["dom_fingerprint_v1"]
        assert feat["geography"] == ["BE", "FR"]

    def test_extract_features_empty_campaign(self, engine):
        feat = engine.extract_features({})
        assert len(feat) == 15
        for cat in engine.FEATURE_CATEGORIES:
            assert cat in feat
            assert isinstance(feat[cat], list)
            assert len(feat[cat]) == 0

    def test_extract_features_language_formats(self, engine):
        f1 = engine.extract_features({"language": "EN"})
        assert f1["language"] == ["en"]
        f2 = engine.extract_features({"languages": ["EN", "de", "ES"]})
        assert f2["language"] == ["de", "en", "es"]

    def test_extract_features_phrasing(self, engine):
        f = engine.extract_features({"slogans": ["High Yield", "Zero Risk"]})
        assert "High Yield" in f["phrasing"]
        assert "Zero Risk" in f["phrasing"]

    def test_extract_features_website_structure(self, engine):
        f = engine.extract_features({"website_structure": {"template": "crypto_v2", "layout": "sidebar"}})
        assert "layout:sidebar" in f["website_structure"]
        assert "template:crypto_v2" in f["website_structure"]

    def test_extract_features_domain_patterns(self, engine):
        f = engine.extract_features({"domains": ["EXAMple-SCAM.com  "]})
        assert f["domain_patterns"] == ["example-scam.com"]

    def test_extract_features_phone_patterns(self, engine):
        f = engine.extract_features({"phones": ["+44123456789"]})
        assert f["phone_patterns"] == ["+44123456789"]

    def test_extract_features_email_patterns(self, engine):
        f = engine.extract_features({"emails": ["Admin@SCAM.org"]})
        assert f["email_patterns"] == ["admin@scam.org"]

    def test_extract_features_hosting_patterns(self, engine):
        f = engine.extract_features({"hosting": ["Cloudflare"]})
        assert f["hosting_patterns"] == ["Cloudflare"]

    def test_extract_features_certificate_reuse(self, engine):
        f = engine.extract_features({"certs": ["cert_sha256_abcdef"]})
        assert f["certificate_reuse"] == ["cert_sha256_abcdef"]

    def test_extract_features_dns_patterns(self, engine):
        f = engine.extract_features({"nameservers": ["NS1.CLOUDFLARE.COM"]})
        assert f["dns_patterns"] == ["ns1.cloudflare.com"]

    def test_extract_features_payment_destinations(self, engine):
        f = engine.extract_features({"ibans": ["DE89370400440532013000"]})
        assert f["payment_destinations"] == ["DE89370400440532013000"]

    def test_extract_features_wallet_relationships(self, engine):
        f = engine.extract_features({"wallets": ["0x71C7656EC7ab88b098defB751B7401B5f6d8976F"]})
        assert "0x71C7656EC7ab88b098defB751B7401B5f6d8976F" in f["wallet_relationships"]

    def test_extract_features_timing(self, engine):
        f = engine.extract_features({"cadence": {"active_hours": "08:00-18:00 UTC"}})
        assert "active_hours:08:00-18:00 UTC" in f["timing"]

    def test_extract_features_infrastructure(self, engine):
        f = engine.extract_features({"ips": ["192.0.2.1", "198.51.100.2"]})
        assert "192.0.2.1" in f["infrastructure"]
        assert "198.51.100.2" in f["infrastructure"]

    def test_extract_features_geography(self, engine):
        f = engine.extract_features({"countries": ["us", "ca"]})
        assert f["geography"] == ["CA", "US"]

    def test_extract_features_victim_reports(self, engine):
        f = engine.extract_features({"reports": 42})
        assert f["victim_reports"] == ["count:42"]

    def test_extract_features_all_15_categories_present(self, engine):
        feat = engine.extract_features({"language": "en"})
        assert len(feat) == 15
        for cat in engine.FEATURE_CATEGORIES:
            assert cat in feat


class TestSignatureGeneration:
    @pytest.fixture
    def engine(self):
        return CampaignDNAEngine()

    def test_generate_signature_returns_dataclass(self, engine):
        sig = engine.generate_signature({"id": "c1", "language": "en"})
        assert isinstance(sig, CampaignSignature)
        assert sig.campaign_id == "c1"
        assert sig.id.startswith("sig_")

    def test_hash_stability(self, engine):
        c1 = {"id": "c_stable", "language": "en", "ips": ["1.1.1.1"], "domains": ["test.com"]}
        c2 = {"id": "c_stable", "domains": ["test.com"], "language": "en", "ips": ["1.1.1.1"]}
        sig1 = engine.generate_signature(c1)
        sig2 = engine.generate_signature(c2)
        assert sig1.feature_hash == sig2.feature_hash

    def test_different_campaigns_different_hashes(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "ips": ["1.1.1.1"]})
        sig2 = engine.generate_signature({"id": "c2", "ips": ["2.2.2.2"]})
        assert sig1.feature_hash != sig2.feature_hash

    def test_confidence_calculation(self, engine):
        sig_sparse = engine.generate_signature({"id": "sparse", "language": "en"})
        sig_dense = engine.generate_signature({
            "id": "dense",
            "language": "en",
            "phrasing": ["scam"],
            "domains": ["scam.com"],
            "phones": ["+123"],
            "emails": ["a@b.com"],
            "hosting": ["host"],
            "certs": ["cert"],
            "dns": ["ns1"],
            "payments": ["iban"],
            "wallets": ["0x1"],
            "timing": ["2026"],
            "ips": ["1.1.1.1"],
            "geography": ["US"],
            "reports": ["r1"],
        })
        assert sig_dense.confidence > sig_sparse.confidence

    def test_unverified_status_in_generated_signature(self, engine):
        sig = engine.generate_signature({"id": "c_unv", "language": "en"})
        assert sig.verification_status == "UNVERIFIED"


class TestSimilarityComputation:
    @pytest.fixture
    def engine(self):
        return CampaignDNAEngine()

    def test_compute_similarity_identical_signatures(self, engine):
        c = {"id": "c1", "language": "en", "ips": ["1.1.1.1"], "wallets": ["0x123"]}
        sig1 = engine.generate_signature(c)
        sig2 = engine.generate_signature(c)
        sim = engine.compute_similarity(sig1, sig2)
        assert sim == 1.0

    def test_compute_similarity_similar_signatures(self, engine):
        c1 = {"id": "c1", "language": "en", "ips": ["1.1.1.1", "2.2.2.2"], "wallets": ["0x123"]}
        c2 = {"id": "c2", "language": "en", "ips": ["1.1.1.1", "3.3.3.3"], "wallets": ["0x123"]}
        sig1 = engine.generate_signature(c1)
        sig2 = engine.generate_signature(c2)
        sim = engine.compute_similarity(sig1, sig2)
        assert 0.0 < sim < 1.0

    def test_compute_similarity_dissimilar_signatures(self, engine):
        c1 = {"id": "c1", "language": "en", "ips": ["1.1.1.1"], "wallets": ["0x123"]}
        c2 = {"id": "c2", "language": "es", "ips": ["9.9.9.9"], "wallets": ["0x999"]}
        sig1 = engine.generate_signature(c1)
        sig2 = engine.generate_signature(c2)
        sim = engine.compute_similarity(sig1, sig2)
        assert sim == 0.0

    def test_compute_similarity_empty_signatures(self, engine):
        sig1 = engine.generate_signature({"id": "empty1"})
        sig2 = engine.generate_signature({"id": "empty2"})
        sim = engine.compute_similarity(sig1, sig2)
        assert 0.0 <= sim <= 1.0

    def test_compute_similarity_dict_inputs(self, engine):
        d1 = {"features": {"language": ["en"], "ips": ["1.1.1.1"]}}
        d2 = {"features": {"language": ["en"], "ips": ["1.1.1.1"]}}
        sim = engine.compute_similarity(d1, d2)
        assert sim == 1.0


class TestFindSimilarCampaigns:
    @pytest.fixture
    def engine(self):
        return CampaignDNAEngine()

    def test_find_similar_campaigns_above_threshold(self, engine):
        c1 = {"id": "target", "language": "en", "ips": ["1.1.1.1"], "wallets": ["0x123"]}
        c2 = {"id": "similar", "language": "en", "ips": ["1.1.1.1"], "wallets": ["0x123"]}
        c3 = {"id": "different", "language": "es", "ips": ["9.9.9.9"], "wallets": ["0x999"]}

        matches = engine.find_similar_campaigns("target", [c1, c2, c3], threshold=0.7)
        assert len(matches) == 1
        assert matches[0]["campaign_id"] == "similar"
        assert matches[0]["similarity"] >= 0.7

    def test_find_similar_campaigns_below_threshold(self, engine):
        c1 = {"id": "target", "language": "en", "ips": ["1.1.1.1"]}
        c2 = {"id": "dissimilar", "language": "ja", "ips": ["8.8.8.8"]}

        matches = engine.find_similar_campaigns("target", [c1, c2], threshold=0.5)
        assert len(matches) == 0

    def test_find_similar_campaigns_dict_all_campaigns(self, engine):
        c1 = {"id": "target", "language": "en", "ips": ["1.1.1.1"]}
        c2 = {"id": "match1", "language": "en", "ips": ["1.1.1.1"]}

        campaigns_dict = {"target": c1, "match1": c2}
        matches = engine.find_similar_campaigns("target", campaigns_dict, threshold=0.7)
        assert len(matches) == 1
        assert matches[0]["campaign_id"] == "match1"

    def test_find_similar_campaigns_list_all_campaigns(self, engine):
        c1 = {"id": "target", "language": "en", "ips": ["1.1.1.1"]}
        c2 = {"id": "match1", "language": "en", "ips": ["1.1.1.1"]}

        matches = engine.find_similar_campaigns("target", [c1, c2], threshold=0.7)
        assert len(matches) == 1

    def test_find_similar_campaigns_target_not_found(self, engine):
        c1 = {"id": "c1", "language": "en"}
        matches = engine.find_similar_campaigns("nonexistent", [c1], threshold=0.5)
        assert matches == []

    def test_find_similar_campaigns_outputs_unverified(self, engine):
        c1 = {"id": "target", "language": "en", "ips": ["1.1.1.1"]}
        c2 = {"id": "match1", "language": "en", "ips": ["1.1.1.1"]}

        matches = engine.find_similar_campaigns("target", [c1, c2], threshold=0.7)
        assert matches[0]["verification_status"] == "UNVERIFIED"


class TestExplainSimilarity:
    @pytest.fixture
    def engine(self):
        return CampaignDNAEngine()

    def test_explain_similarity_returns_dict(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "language": "en", "ips": ["1.1.1.1"]})
        sig2 = engine.generate_signature({"id": "c2", "language": "en", "ips": ["1.1.1.1", "2.2.2.2"]})
        exp = engine.explain_similarity(sig1, sig2)
        assert isinstance(exp, dict)

    def test_explain_similarity_contains_required_keys(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "language": "en"})
        sig2 = engine.generate_signature({"id": "c2", "language": "en"})
        exp = engine.explain_similarity(sig1, sig2)

        required_keys = [
            "similarity",
            "matching_features",
            "differing_features",
            "confidence",
            "limitations",
            "verification_status",
            "evidence",
            "features",
        ]
        for key in required_keys:
            assert key in exp

    def test_explain_similarity_uppercase_keys_present(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "language": "en"})
        sig2 = engine.generate_signature({"id": "c2", "language": "en"})
        exp = engine.explain_similarity(sig1, sig2)

        for uppercase_key in ["SIMILARITY", "EVIDENCE", "FEATURES", "CONFIDENCE", "LIMITATIONS"]:
            assert uppercase_key in exp

    def test_explain_similarity_unverified_marking(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "language": "en"})
        sig2 = engine.generate_signature({"id": "c2", "language": "en"})
        exp = engine.explain_similarity(sig1, sig2)
        assert exp["verification_status"] == "UNVERIFIED"

    def test_explain_similarity_matching_features_populated(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "language": "en", "wallets": ["0xabc"]})
        sig2 = engine.generate_signature({"id": "c2", "language": "en", "wallets": ["0xabc"]})
        exp = engine.explain_similarity(sig1, sig2)
        assert "language" in exp["matching_features"]
        assert "wallet_relationships" in exp["matching_features"]

    def test_explain_similarity_differing_features_populated(self, engine):
        sig1 = engine.generate_signature({"id": "c1", "ips": ["1.1.1.1"]})
        sig2 = engine.generate_signature({"id": "c2", "ips": ["2.2.2.2"]})
        exp = engine.explain_similarity(sig1, sig2)
        assert "infrastructure" in exp["differing_features"]
