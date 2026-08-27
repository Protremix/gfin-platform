"""GFIN Source packages — registry, scoring, and policy for external data sources."""
from packages.sources.registry import SourceRegistry, SourceRecord
from packages.sources.scoring import SourceScorer, QualityScore
from packages.sources.policy import SourcePolicy, AccessStatus, AuthMethod

__all__ = [
    "SourceRegistry", "SourceRecord",
    "SourceScorer", "QualityScore",
    "SourcePolicy", "AccessStatus", "AuthMethod",
]
