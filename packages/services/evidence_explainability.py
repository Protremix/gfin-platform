# GFIN Evidence & Explainability Engine
#
# Per Advanced Intelligence Superset Directive v1.0 §3-4:
# - Every material GFIN conclusion must be explainable
# - Evidence chain: CONCLUSION → RELATIONSHIP → OBSERVATION → SOURCE → ORIGINAL RECORD → TIMESTAMP → PROCESSING → EVIDENCE HASH
# - Explainability contract: structured JSON with conclusion, evidence, observations, relationships, sources, confidence, limitations
# - API: GET /evidence/{id}, GET /entities/{id}/explain, GET /relationships/{id}/explain
#
# Layer A: In-memory explainability engine
# Layer B: Persistent evidence graph database (REQUIRES EXTERNAL INFRASTRUCTURE)

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import utc_now

# ═══════════════════════════════════════════════
# EVIDENCE CHAIN MODELS
# ═══════════════════════════════════════════════


class ConclusionType(StrEnum):
    """Types of conclusions GFIN can reach."""

    ENTITY_IDENTIFIED = "ENTITY_IDENTIFIED"
    RELATIONSHIP_ESTABLISHED = "RELATIONSHIP_ESTABLISHED"
    CAMPAIGN_DETECTED = "CAMPAIGN_DETECTED"
    CORRELATION_FOUND = "CORRELATION_FOUND"
    INFRASTRUCTURE_LINKED = "INFRASTRUCTURE_LINKED"
    PATTERN_MATCHED = "PATTERN_MATCHED"
    ENTITY_RESOLVED = "ENTITY_RESOLVED"
    DISCOVERY_MADE = "DISCOVERY_MADE"
    ALERT_GENERATED = "ALERT_GENERATED"
    HYPOTHESIS_FORMED = "HYPOTHESIS_FORMED"


class EvidenceStrength(StrEnum):
    """Strength of evidence supporting a conclusion."""

    CONFIRMED = "CONFIRMED"  # Multiple independent sources corroborate
    STRONG = "STRONG"  # Single reliable source or multiple weak sources
    MODERATE = "MODERATE"  # Single source of moderate reliability
    WEAK = "WEAK"  # Single unreliable source
    UNVERIFIED = "UNVERIFIED"  # No source yet


class SourceReliability(StrEnum):
    """Reliability rating of a source (Admiralty Code-inspired)."""

    A_FULLY_RELIABLE = "A_FULLY_RELIABLE"
    B_USUALLY_RELIABLE = "B_USUALLY_RELIABLE"
    C_FAIRLY_RELIABLE = "C_FAIRLY_RELIABLE"
    D_NOT_USUALLY_RELIABLE = "D_NOT_USUALLY_RELIABLE"
    E_UNRELIABLE = "E_UNRELIABLE"
    F_RELIABILITY_UNDETERMINED = "F_RELIABILITY_UNDETERMINED"


class SourceCredibility(StrEnum):
    """Credibility of information from a source."""

    _1_CONFIRMED = "1_CONFIRMED"
    _2_PROBABLE = "2_PROBABLE"
    _3_POSSIBLY_TRUE = "3_POSSIBLY_TRUE"
    _4_DOUBTFUL = "4_DOUBTFUL"
    _5_IMPROBABLE = "5_IMPROBABLE"
    _6_TRUTH_CANNOT_BE_JUDGED = "6_TRUTH_CANNOT_BE_JUDGED"


# ═══════════════════════════════════════════════
# EVIDENCE ITEM
# ═══════════════════════════════════════════════


class EvidenceItem(BaseModel):
    """A single piece of evidence supporting a conclusion.

    Every evidence item links back to its source and has a hash for integrity.
    """

    item_id: str = Field(default_factory=lambda: f"EVI-{uuid4().hex[:8].upper()}")
    source: str  # Where this evidence came from
    source_reliability: SourceReliability = SourceReliability.F_RELIABILITY_UNDETERMINED
    source_credibility: SourceCredibility = SourceCredibility._6_TRUTH_CANNOT_BE_JUDGED
    observation: str  # What was observed
    observed_at: datetime = Field(default_factory=utc_now)
    recorded_at: datetime = Field(default_factory=utc_now)
    processing: str = ""  # How this evidence was processed
    evidence_hash: str = ""  # Integrity hash
    classification: str = "PUBLIC"
    jurisdiction: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def compute_hash(self) -> str:
        content = f"{self.source}:{self.observation}:{self.observed_at.isoformat()}"
        self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()
        return self.evidence_hash


# ═══════════════════════════════════════════════
# EVIDENCE CHAIN
# ═══════════════════════════════════════════════


class EvidenceChain(BaseModel):
    """A chain of evidence leading to a conclusion.

    CONCLUSION → RELATIONSHIP → OBSERVATION → SOURCE → ORIGINAL RECORD → TIMESTAMP → PROCESSING → EVIDENCE HASH
    """

    chain_id: str = Field(default_factory=lambda: f"ECH-{uuid4().hex[:8].upper()}")
    conclusion_type: ConclusionType
    conclusion: str  # What GFIN concluded
    entity_id: str | None = None
    relationship_id: str | None = None
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    confidence: EvidenceStrength = EvidenceStrength.UNVERIFIED
    limitations: list[str] = Field(default_factory=list)
    generated_by: str = "GFIN"  # Which component generated this conclusion
    timestamp: datetime = Field(default_factory=utc_now)
    ai_generated: bool = False

    model_config = {"use_enum_values": True}

    def compute_confidence(self) -> EvidenceStrength:
        """Compute overall confidence from evidence items."""
        if not self.evidence_items:
            self.confidence = EvidenceStrength.UNVERIFIED
            return self.confidence

        # Count independent sources
        sources = {item.source for item in self.evidence_items}
        source_count = len(sources)

        # Check if multiple reliable sources corroborate
        reliable_sources = {
            item.source for item in self.evidence_items
            if item.source_reliability in (
                SourceReliability.A_FULLY_RELIABLE,
                SourceReliability.B_USUALLY_RELIABLE,
            )
        }

        if source_count >= 3 and len(reliable_sources) >= 2:
            self.confidence = EvidenceStrength.CONFIRMED
        elif source_count >= 2:
            self.confidence = EvidenceStrength.STRONG
        elif source_count >= 1:
            reliability = self.evidence_items[0].source_reliability
            if reliability in (SourceReliability.A_FULLY_RELIABLE, SourceReliability.B_USUALLY_RELIABLE):
                self.confidence = EvidenceStrength.MODERATE
            else:
                self.confidence = EvidenceStrength.WEAK
        else:
            self.confidence = EvidenceStrength.UNVERIFIED

        return self.confidence


# ═══════════════════════════════════════════════
# EXPLAINABILITY RESPONSE
# ═══════════════════════════════════════════════


class ExplainabilityResponse(BaseModel):
    """Structured explainability response per §4 of the directive.

    Answers: "Why does GFIN believe this?"
    """

    conclusion: str
    conclusion_type: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    relationships: list[dict[str, str]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str = ""
    confidence_explanation: str = ""
    limitations: list[str] = Field(default_factory=list)
    generated_by: str = "GFIN"
    timestamp: datetime = Field(default_factory=utc_now)
    ai_generated: bool = False
    ai_disclaimer: str = ""

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# EVIDENCE & EXPLAINABILITY ENGINE
# ═══════════════════════════════════════════════


class EvidenceExplainabilityEngine:
    """Engine for recording, querying, and explaining evidence-backed conclusions.

    Layer A: In-memory evidence chains and explainability.
    Layer B: Persistent evidence graph with query optimization (REQUIRES EXTERNAL INFRASTRUCTURE).

    Key rules:
    - AI-generated explanations must NOT invent evidence.
    - Every conclusion must link to evidence.
    - Confidence is computed from source quality and corroboration.
    - Limitations must be stated explicitly.
    """

    def __init__(self) -> None:
        self._chains: dict[str, EvidenceChain] = {}  # chain_id -> chain
        self._entity_chains: dict[str, list[str]] = {}  # entity_id -> [chain_ids]
        self._relationship_chains: dict[str, list[str]] = {}  # relationship_id -> [chain_ids]
        self._evidence_items: dict[str, EvidenceItem] = {}  # item_id -> item

    # ─── Recording ───

    def record_evidence(
        self,
        source: str,
        observation: str,
        observed_at: datetime | None = None,
        source_reliability: SourceReliability = SourceReliability.F_RELIABILITY_UNDETERMINED,
        source_credibility: SourceCredibility = SourceCredibility._6_TRUTH_CANNOT_BE_JUDGED,
        processing: str = "",
        classification: str = "PUBLIC",
        jurisdiction: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceItem:
        """Record a single piece of evidence."""
        item = EvidenceItem(
            source=source,
            observation=observation,
            observed_at=observed_at or utc_now(),
            source_reliability=source_reliability,
            source_credibility=source_credibility,
            processing=processing,
            classification=classification,
            jurisdiction=jurisdiction,
            metadata=metadata or {},
        )
        item.compute_hash()
        self._evidence_items[item.item_id] = item
        return item

    def create_conclusion(
        self,
        conclusion_type: ConclusionType,
        conclusion: str,
        evidence_items: list[EvidenceItem],
        entity_id: str | None = None,
        relationship_id: str | None = None,
        generated_by: str = "GFIN",
        limitations: list[str] | None = None,
        ai_generated: bool = False,
    ) -> EvidenceChain:
        """Create a conclusion backed by an evidence chain."""
        chain = EvidenceChain(
            conclusion_type=conclusion_type,
            conclusion=conclusion,
            entity_id=entity_id,
            relationship_id=relationship_id,
            evidence_items=evidence_items,
            generated_by=generated_by,
            limitations=limitations or [],
            ai_generated=ai_generated,
        )
        chain.compute_confidence()

        self._chains[chain.chain_id] = chain

        if entity_id:
            if entity_id not in self._entity_chains:
                self._entity_chains[entity_id] = []
            self._entity_chains[entity_id].append(chain.chain_id)

        if relationship_id:
            if relationship_id not in self._relationship_chains:
                self._relationship_chains[relationship_id] = []
            self._relationship_chains[relationship_id].append(chain.chain_id)

        return chain

    # ─── Explainability API ───

    def explain_entity(self, entity_id: str) -> ExplainabilityResponse:
        """Explain why GFIN believes what it believes about an entity.

        Implements: GET /entities/{id}/explain
        """
        chain_ids = self._entity_chains.get(entity_id, [])
        chains = [self._chains[cid] for cid in chain_ids if cid in self._chains]

        if not chains:
            return ExplainabilityResponse(
                conclusion=f"No conclusions about {entity_id}",
                conclusion_type="NONE",
                limitations=["No evidence found for this entity"],
            )

        # Aggregate evidence
        all_evidence: list[dict[str, Any]] = []
        all_observations: list[str] = []
        all_sources: list[dict[str, Any]] = []
        all_limitations: list[str] = []
        ai_generated = False

        for chain in chains:
            for item in chain.evidence_items:
                all_evidence.append({
                    "item_id": item.item_id,
                    "source": item.source,
                    "observation": item.observation,
                    "observed_at": item.observed_at.isoformat(),
                    "reliability": item.source_reliability,
                    "credibility": item.source_credibility,
                    "hash": item.evidence_hash,
                })
                all_observations.append(item.observation)
                all_sources.append({
                    "source": item.source,
                    "reliability": item.source_reliability,
                    "credibility": item.source_credibility,
                })
            all_limitations.extend(chain.limitations)
            if chain.ai_generated:
                ai_generated = True

        # Use highest confidence chain as primary conclusion
        best_chain = max(chains, key=lambda c: list(EvidenceStrength).index(c.confidence) if c.confidence in list(EvidenceStrength) else 0)

        response = ExplainabilityResponse(
            conclusion=best_chain.conclusion,
            conclusion_type=best_chain.conclusion_type,
            evidence=all_evidence,
            observations=all_observations,
            sources=all_sources,
            confidence=best_chain.confidence,
            confidence_explanation=self._explain_confidence(best_chain),
            limitations=list(set(all_limitations)) if all_limitations else ["No limitations noted"],
            generated_by=best_chain.generated_by,
            ai_generated=ai_generated,
        )

        if ai_generated:
            response.ai_disclaimer = "This conclusion includes AI-generated analysis. AI output is ANALYSIS, not SOURCE OF TRUTH. Verify with primary evidence."

        return response

    def explain_relationship(self, relationship_id: str) -> ExplainabilityResponse:
        """Explain why GFIN believes a relationship exists.

        Implements: GET /relationships/{id}/explain
        """
        chain_ids = self._relationship_chains.get(relationship_id, [])
        chains = [self._chains[cid] for cid in chain_ids if cid in self._chains]

        if not chains:
            return ExplainabilityResponse(
                conclusion=f"No evidence for relationship {relationship_id}",
                conclusion_type="NONE",
                limitations=["No evidence found for this relationship"],
            )

        return self._build_explanation(chains)

    def get_evidence(self, evidence_id: str) -> EvidenceItem | None:
        """Get a single evidence item by ID.

        Implements: GET /evidence/{id}
        """
        return self._evidence_items.get(evidence_id)

    def get_chain(self, chain_id: str) -> EvidenceChain | None:
        """Get an evidence chain by ID."""
        return self._chains.get(chain_id)

    def get_entity_chains(self, entity_id: str) -> list[EvidenceChain]:
        """Get all evidence chains for an entity."""
        chain_ids = self._entity_chains.get(entity_id, [])
        return [self._chains[cid] for cid in chain_ids if cid in self._chains]

    # ─── Internal ───

    def _build_explanation(self, chains: list[EvidenceChain]) -> ExplainabilityResponse:
        all_evidence: list[dict[str, Any]] = []
        all_observations: list[str] = []
        all_sources: list[dict[str, Any]] = []
        all_limitations: list[str] = []
        ai_generated = False

        for chain in chains:
            for item in chain.evidence_items:
                all_evidence.append({
                    "item_id": item.item_id,
                    "source": item.source,
                    "observation": item.observation,
                    "observed_at": item.observed_at.isoformat(),
                    "reliability": item.source_reliability,
                    "hash": item.evidence_hash,
                })
                all_observations.append(item.observation)
                all_sources.append({"source": item.source, "reliability": item.source_reliability})
            all_limitations.extend(chain.limitations)
            if chain.ai_generated:
                ai_generated = True

        best_chain = max(chains, key=lambda c: list(EvidenceStrength).index(c.confidence) if c.confidence in list(EvidenceStrength) else 0)

        response = ExplainabilityResponse(
            conclusion=best_chain.conclusion,
            conclusion_type=best_chain.conclusion_type,
            evidence=all_evidence,
            observations=all_observations,
            sources=all_sources,
            confidence=best_chain.confidence,
            confidence_explanation=self._explain_confidence(best_chain),
            limitations=list(set(all_limitations)) if all_limitations else ["No limitations noted"],
            generated_by=best_chain.generated_by,
            ai_generated=ai_generated,
        )

        if ai_generated:
            response.ai_disclaimer = "This conclusion includes AI-generated analysis. AI output is ANALYSIS, not SOURCE OF TRUTH."

        return response

    def _explain_confidence(self, chain: EvidenceChain) -> str:
        """Explain WHY a confidence level was assigned."""
        sources = {item.source for item in chain.evidence_items}
        reliable = {
            item.source for item in chain.evidence_items
            if item.source_reliability in (SourceReliability.A_FULLY_RELIABLE, SourceReliability.B_USUALLY_RELIABLE)
        }

        explanation = f"Confidence: {chain.confidence}. "
        explanation += f"Based on {len(chain.evidence_items)} evidence items from {len(sources)} source(s). "
        if reliable:
            explanation += f"Reliable sources: {', '.join(reliable)}. "
        if len(sources) >= 3:
            explanation += "Multiple independent sources corroborate this conclusion. "
        elif len(sources) >= 2:
            explanation += "Two sources provide moderate corroboration. "
        else:
            explanation += "Single source — corroboration recommended. "
        if chain.ai_generated:
            explanation += "Includes AI-generated analysis requiring human review. "
        return explanation

    # ─── Corroboration ───

    def check_corroboration(self, observation: str, tolerance: float = 0.8) -> dict[str, Any]:
        """Check if an observation is corroborated by multiple sources."""
        matching = [
            item for item in self._evidence_items.values()
            if observation.lower() in item.observation.lower()
            or item.observation.lower() in observation.lower()
        ]
        sources = {item.source for item in matching}
        return {
            "observation": observation,
            "corroborating_sources": list(sources),
            "corroboration_count": len(sources),
            "is_corroborated": len(sources) >= 2,
            "evidence_items": [item.item_id for item in matching],
        }

    # ─── Intelligence Decay ───

    def get_freshness(self, entity_id: str, max_age_days: int = 30) -> dict[str, Any]:
        """Check how fresh the evidence is for an entity (intelligence decay)."""
        chains = self.get_entity_chains(entity_id)
        if not chains:
            return {"entity_id": entity_id, "freshness": "NO_EVIDENCE", "age_days": None}

        latest = max(
            item.observed_at for chain in chains for item in chain.evidence_items
        )
        age = (utc_now() - latest).days

        if age <= max_age_days // 3:
            freshness = "FRESH"
        elif age <= max_age_days:
            freshness = "AGING"
        else:
            freshness = "STALE"

        return {
            "entity_id": entity_id,
            "freshness": freshness,
            "age_days": age,
            "last_observed": latest.isoformat(),
            "recommendation": "Re-verify stale evidence" if freshness == "STALE" else "Evidence is current",
        }

    # ─── Stats ───

    def stats(self) -> dict[str, Any]:
        return {
            "total_chains": len(self._chains),
            "total_evidence_items": len(self._evidence_items),
            "entity_conclusions": len(self._entity_chains),
            "relationship_conclusions": len(self._relationship_chains),
            "ai_generated_chains": sum(1 for c in self._chains.values() if c.ai_generated),
        }
