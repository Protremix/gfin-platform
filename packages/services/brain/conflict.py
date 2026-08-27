"""GFIN Brain Conflict Resolver — resolves disagreements between modules."""
from __future__ import annotations
from typing import Any
import logging

from packages.brain.schemas import ConflictResolution, ConflictStatus

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Resolves conflicts between module results.

    The Brain must not silently choose one.
    Records: CONFLICT, SOURCE_A, SOURCE_B, RELIABILITY, EVIDENCE, RESOLUTION, STATUS
    Possible result: UNRESOLVED_CONFLICT
    """

    def __init__(self):
        self._conflicts: list[ConflictResolution] = []

    def resolve(
        self,
        source_a: str,
        result_a: Any,
        source_b: str,
        result_b: Any,
        reliability_a: float = 0.5,
        reliability_b: float = 0.5,
        evidence: list[str] | None = None,
    ) -> ConflictResolution:
        """Resolve a conflict between two module results."""
        evidence = evidence or []

        # If results agree, no conflict
        if result_a == result_b:
            resolution = ConflictResolution(
                source_a=source_a,
                source_b=source_b,
                reliability_a=reliability_a,
                reliability_b=reliability_b,
                evidence=evidence,
                resolution=f"Both sources agree: {result_a}",
                status=ConflictStatus.RESOLVED,
            )
        # If one source is significantly more reliable
        elif abs(reliability_a - reliability_b) > 0.3:
            more_reliable = source_a if reliability_a > reliability_b else source_b
            resolution = ConflictResolution(
                source_a=source_a,
                source_b=source_b,
                reliability_a=reliability_a,
                reliability_b=reliability_b,
                evidence=evidence,
                resolution=f"Resolved in favor of {more_reliable} (higher reliability)",
                status=ConflictStatus.RESOLVED,
            )
        # Cannot resolve
        else:
            resolution = ConflictResolution(
                source_a=source_a,
                source_b=source_b,
                reliability_a=reliability_a,
                reliability_b=reliability_b,
                evidence=evidence,
                resolution="Insufficient evidence to resolve conflict",
                status=ConflictStatus.UNRESOLVED_CONFLICT,
            )

        self._conflicts.append(resolution)
        logger.info(f"Conflict resolved: {resolution.conflict_id} status={resolution.status.value}")
        return resolution

    def get_conflicts(self) -> list[ConflictResolution]:
        """Get all recorded conflicts."""
        return list(self._conflicts)

    def get_unresolved(self) -> list[ConflictResolution]:
        """Get all unresolved conflicts."""
        return [c for c in self._conflicts if c.status == ConflictStatus.UNRESOLVED_CONFLICT]
