# Tests for GFIN Evidence & Explainability Engine
# Per Advanced Intelligence Superset Directive v1.0 §3-4

import sys

import pytest

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

from services.evidence_explainability import (
    ConclusionType,
    EvidenceExplainabilityEngine,
    EvidenceStrength,
    SourceCredibility,
    SourceReliability,
)


@pytest.fixture
def engine():
    return EvidenceExplainabilityEngine()


@pytest.fixture
def reliable_evidence(engine):
    """Create evidence from a fully reliable source."""
    return engine.record_evidence(
        source="certificate_transparency",
        observation="Domain scam-example.invalid has certificate issued by Let's Encrypt",
        source_reliability=SourceReliability.A_FULLY_RELIABLE,
        source_credibility=SourceCredibility._1_CONFIRMED,
        processing="CT log query",
    )


@pytest.fixture
def moderate_evidence(engine):
    return engine.record_evidence(
        source="dns_resolver",
        observation="Domain resolves to 192.0.2.1",
        source_reliability=SourceReliability.B_USUALLY_RELIABLE,
        source_credibility=SourceCredibility._2_PROBABLE,
    )


# ═══════════════════════════════════════════════
# EVIDENCE RECORDING TESTS
# ═══════════════════════════════════════════════


class TestEvidenceRecording:
    def test_record_evidence(self, engine):
        item = engine.record_evidence(
            source="test_source",
            observation="Test observation",
        )
        assert item.item_id.startswith("EVI-")
        assert item.source == "test_source"
        assert item.observation == "Test observation"
        assert item.evidence_hash != ""

    def test_evidence_has_hash(self, engine, reliable_evidence):
        assert reliable_evidence.evidence_hash != ""
        assert len(reliable_evidence.evidence_hash) == 64

    def test_evidence_has_provenance(self, engine):
        item = engine.record_evidence(
            source="rdap",
            observation="Domain registered on 2026-01-15",
            source_reliability=SourceReliability.B_USUALLY_RELIABLE,
            processing="RDAP API query",
        )
        assert item.source == "rdap"
        assert item.source_reliability == "B_USUALLY_RELIABLE"
        assert item.processing == "RDAP API query"

    def test_evidence_classification(self, engine):
        item = engine.record_evidence(
            source="internal",
            observation="Sensitive observation",
            classification="CONFIDENTIAL",
            jurisdiction="EU",
        )
        assert item.classification == "CONFIDENTIAL"
        assert item.jurisdiction == "EU"

    def test_get_evidence_by_id(self, engine, reliable_evidence):
        retrieved = engine.get_evidence(reliable_evidence.item_id)
        assert retrieved is not None
        assert retrieved.item_id == reliable_evidence.item_id

    def test_get_nonexistent_evidence(self, engine):
        result = engine.get_evidence("EVI-NONEXIST")
        assert result is None


# ═══════════════════════════════════════════════
# CONCLUSION & CONFIDENCE TESTS
# ═══════════════════════════════════════════════


class TestConclusions:
    def test_create_conclusion(self, engine, reliable_evidence):
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Domain scam-example.invalid is a fraudulent domain",
            evidence_items=[reliable_evidence],
            entity_id="DOMAIN:scam-example.invalid",
        )
        assert chain.chain_id.startswith("ECH-")
        assert chain.conclusion_type == "ENTITY_IDENTIFIED"
        assert len(chain.evidence_items) == 1

    def test_confidence_confirmed_multiple_reliable(self, engine):
        """3+ independent reliable sources → CONFIRMED."""
        items = []
        for src in ["ct_log", "rdap", "dns"]:
            items.append(engine.record_evidence(
                source=src,
                observation=f"Observed by {src}",
                source_reliability=SourceReliability.A_FULLY_RELIABLE,
            ))
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Confirmed conclusion",
            evidence_items=items,
        )
        assert chain.confidence == EvidenceStrength.CONFIRMED.value

    def test_confidence_strong_two_sources(self, engine):
        """2 sources → STRONG."""
        items = [
            engine.record_evidence(source="src1", observation="Obs 1",
                                   source_reliability=SourceReliability.A_FULLY_RELIABLE),
            engine.record_evidence(source="src2", observation="Obs 2",
                                   source_reliability=SourceReliability.B_USUALLY_RELIABLE),
        ]
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.RELATIONSHIP_ESTABLISHED,
            conclusion="Strong conclusion",
            evidence_items=items,
        )
        assert chain.confidence == EvidenceStrength.STRONG.value

    def test_confidence_moderate_single_reliable(self, engine):
        """1 reliable source → MODERATE."""
        item = engine.record_evidence(
            source="ct_log", observation="Single reliable observation",
            source_reliability=SourceReliability.A_FULLY_RELIABLE,
        )
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Moderate conclusion",
            evidence_items=[item],
        )
        assert chain.confidence == EvidenceStrength.MODERATE.value

    def test_confidence_weak_unreliable(self, engine):
        """1 unreliable source → WEAK."""
        item = engine.record_evidence(
            source="unknown", observation="Unreliable observation",
            source_reliability=SourceReliability.E_UNRELIABLE,
        )
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Weak conclusion",
            evidence_items=[item],
        )
        assert chain.confidence == EvidenceStrength.WEAK.value

    def test_confidence_unverified_no_evidence(self, engine):
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.HYPOTHESIS_FORMED,
            conclusion="Unverified hypothesis",
            evidence_items=[],
        )
        assert chain.confidence == EvidenceStrength.UNVERIFIED.value

    def test_limitations_recorded(self, engine, reliable_evidence):
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.CORRELATION_FOUND,
            conclusion="Possible correlation",
            evidence_items=[reliable_evidence],
            limitations=["Only one source", "Temporal data incomplete"],
        )
        assert len(chain.limitations) == 2
        assert "Only one source" in chain.limitations

    def test_ai_generated_flag(self, engine, reliable_evidence):
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.PATTERN_MATCHED,
            conclusion="AI detected pattern",
            evidence_items=[reliable_evidence],
            ai_generated=True,
        )
        assert chain.ai_generated is True


# ═══════════════════════════════════════════════
# EXPLAINABILITY TESTS
# ═══════════════════════════════════════════════


class TestExplainability:
    def test_explain_entity(self, engine, reliable_evidence, moderate_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Domain is associated with fraud campaign",
            evidence_items=[reliable_evidence, moderate_evidence],
            entity_id="DOMAIN:scam-example.invalid",
            limitations=["Single domain analysis", "No victim reports yet"],
        )
        explanation = engine.explain_entity("DOMAIN:scam-example.invalid")
        assert explanation.conclusion == "Domain is associated with fraud campaign"
        assert explanation.conclusion_type == "ENTITY_IDENTIFIED"
        assert len(explanation.evidence) == 2
        assert len(explanation.observations) == 2
        assert len(explanation.sources) == 2
        assert explanation.confidence != ""
        assert "Single domain analysis" in explanation.limitations

    def test_explain_entity_no_evidence(self, engine):
        explanation = engine.explain_entity("DOMAIN:unknown.invalid")
        assert "No conclusions" in explanation.conclusion
        assert explanation.confidence == ""
        assert "No evidence found" in explanation.limitations[0]

    def test_explain_relationship(self, engine, reliable_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.RELATIONSHIP_ESTABLISHED,
            conclusion="DOMAIN resolves to IP",
            evidence_items=[reliable_evidence],
            relationship_id="REL-001",
        )
        explanation = engine.explain_relationship("REL-001")
        assert explanation.conclusion == "DOMAIN resolves to IP"
        assert len(explanation.evidence) == 1

    def test_explain_relationship_no_evidence(self, engine):
        explanation = engine.explain_relationship("REL-NONEXIST")
        assert "No evidence" in explanation.conclusion

    def test_confidence_explanation(self, engine, reliable_evidence, moderate_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Test conclusion",
            evidence_items=[reliable_evidence, moderate_evidence],
            entity_id="DOMAIN:test.invalid",
        )
        explanation = engine.explain_entity("DOMAIN:test.invalid")
        assert explanation.confidence_explanation != ""
        assert "source" in explanation.confidence_explanation.lower()

    def test_ai_disclaimer(self, engine, reliable_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.PATTERN_MATCHED,
            conclusion="AI found a pattern",
            evidence_items=[reliable_evidence],
            entity_id="DOMAIN:ai-test.invalid",
            ai_generated=True,
        )
        explanation = engine.explain_entity("DOMAIN:ai-test.invalid")
        assert explanation.ai_generated is True
        assert "AI" in explanation.ai_disclaimer
        assert "NOT" in explanation.ai_disclaimer.upper() or "ANALYSIS" in explanation.ai_disclaimer.upper()

    def test_explain_includes_source_reliability(self, engine, reliable_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Test",
            evidence_items=[reliable_evidence],
            entity_id="DOMAIN:rel-test.invalid",
        )
        explanation = engine.explain_entity("DOMAIN:rel-test.invalid")
        assert len(explanation.sources) == 1
        assert "reliability" in explanation.sources[0]


# ═══════════════════════════════════════════════
# CORROBORATION TESTS
# ═══════════════════════════════════════════════


class TestCorroboration:
    def test_corroborated_observation(self, engine):
        engine.record_evidence(source="src1", observation="Domain resolves to 192.0.2.1")
        engine.record_evidence(source="src2", observation="Domain resolves to 192.0.2.1")
        result = engine.check_corroboration("Domain resolves to 192.0.2.1")
        assert result["is_corroborated"] is True
        assert result["corroboration_count"] == 2

    def test_uncorroborated_observation(self, engine):
        engine.record_evidence(source="src1", observation="Domain resolves to 192.0.2.1")
        result = engine.check_corroboration("Domain resolves to 192.0.2.1")
        assert result["is_corroborated"] is False
        assert result["corroboration_count"] == 1

    def test_no_matching_evidence(self, engine):
        result = engine.check_corroboration("Something completely different")
        assert result["is_corroborated"] is False
        assert result["corroboration_count"] == 0


# ═══════════════════════════════════════════════
# INTELLIGENCE DECAY TESTS
# ═══════════════════════════════════════════════


class TestIntelligenceDecay:
    def test_fresh_evidence(self, engine):
        item = engine.record_evidence(source="src", observation="Fresh observation")
        engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Fresh",
            evidence_items=[item],
            entity_id="DOMAIN:fresh.invalid",
        )
        decay = engine.get_freshness("DOMAIN:fresh.invalid")
        assert decay["freshness"] in ("FRESH", "AGING")
        assert decay["age_days"] is not None

    def test_no_evidence(self, engine):
        decay = engine.get_freshness("DOMAIN:unknown.invalid")
        assert decay["freshness"] == "NO_EVIDENCE"


# ═══════════════════════════════════════════════
# AI SECURITY TESTS
# ═══════════════════════════════════════════════


class TestAISecurity:
    def test_ai_must_not_invent_evidence(self, engine):
        """AI-generated conclusions must still have real evidence items."""
        item = engine.record_evidence(source="real_source", observation="Real observation")
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.PATTERN_MATCHED,
            conclusion="AI pattern",
            evidence_items=[item],
            ai_generated=True,
        )
        # Every AI conclusion must have at least one real evidence item
        assert len(chain.evidence_items) > 0
        assert chain.evidence_items[0].source == "real_source"

    def test_ai_disclaimer_mandatory(self, engine, reliable_evidence):
        chain = engine.create_conclusion(
            conclusion_type=ConclusionType.PATTERN_MATCHED,
            conclusion="AI conclusion",
            evidence_items=[reliable_evidence],
            entity_id="DOMAIN:ai-sec.invalid",
            ai_generated=True,
        )
        explanation = engine.explain_entity("DOMAIN:ai-sec.invalid")
        assert explanation.ai_generated is True
        assert explanation.ai_disclaimer != ""


# ═══════════════════════════════════════════════
# STATS TESTS
# ═══════════════════════════════════════════════


class TestStats:
    def test_stats(self, engine, reliable_evidence, moderate_evidence):
        engine.create_conclusion(
            conclusion_type=ConclusionType.ENTITY_IDENTIFIED,
            conclusion="Test",
            evidence_items=[reliable_evidence, moderate_evidence],
            entity_id="DOMAIN:stats.invalid",
        )
        stats = engine.stats()
        assert stats["total_chains"] == 1
        assert stats["total_evidence_items"] == 2
        assert stats["entity_conclusions"] == 1
