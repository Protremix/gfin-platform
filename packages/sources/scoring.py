"""GFIN Source Scoring — quality scores for data sources (Directive §18)."""
from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field
import logging

from packages.sources.registry import SourceRecord

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Quality score for a data source (Directive §18)."""
    authority: float = 0.5       # Is the source authoritative?
    reliability: float = 0.5    # How reliable is the data?
    freshness: float = 0.5      # How current is the data?
    coverage: float = 0.5       # How comprehensive?
    independence: float = 0.5    # Independent of other sources?
    provenance: float = 0.5     # Can we trace the data origin?
    availability: float = 0.5    # Is the API available?
    latency: float = 0.8         # How fast? (1.0 = fast)
    cost: float = 0.8            # How cheap? (1.0 = free)
    legal_usability: float = 0.5 # Can we legally use the data?
    version: str = "1.0.0"

    @property
    def overall(self) -> float:
        """Overall quality score (weighted average)."""
        weights = {
            "authority": 0.15,
            "reliability": 0.15,
            "freshness": 0.10,
            "coverage": 0.10,
            "independence": 0.10,
            "provenance": 0.10,
            "availability": 0.05,
            "latency": 0.05,
            "cost": 0.05,
            "legal_usability": 0.15,
        }
        total = sum(getattr(self, k) * w for k, w in weights.items())
        return round(total, 3)

    @property
    def is_authoritative(self) -> bool:
        """A low-quality source may be used as a lead but not as authoritative evidence."""
        return self.authority >= 0.7 and self.reliability >= 0.7 and self.legal_usability >= 0.7


class SourceScorer:
    """Scores data sources based on quality dimensions."""

    def score(self, source: SourceRecord) -> QualityScore:
        """Calculate quality score for a source."""
        # Map reliability string to float
        reliability_map = {"HIGH": 0.9, "MEDIUM-HIGH": 0.75, "MEDIUM": 0.6, "LOW": 0.3}
        rel = reliability_map.get(source.reliability, 0.5)

        # Authority based on source type
        authority = 0.5
        if source.provider in ("Google", "Verisign", "FBI", "ICANN"):
            authority = 0.9
        elif source.legal_basis.startswith("Public"):
            authority = 0.7
        elif source.legal_basis.startswith("Licensed"):
            authority = 0.6

        # Cost
        cost = 1.0 if source.auth_method.value == "public_api" else 0.6

        # Legal usability
        legal = 0.5
        if source.legal_basis.startswith("Public"):
            legal = 0.9
        elif source.legal_basis.startswith("Licensed"):
            legal = 0.7
        elif source.legal_basis.startswith("Official"):
            legal = 0.8

        # Independence (different from other sources)
        independence = 0.7  # Default

        return QualityScore(
            authority=authority,
            reliability=rel,
            freshness=0.7,
            coverage=0.6,
            independence=independence,
            provenance=0.7,
            availability=0.9,
            latency=0.8,
            cost=cost,
            legal_usability=legal,
        )
