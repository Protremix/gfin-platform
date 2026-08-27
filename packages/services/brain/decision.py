"""GFIN Brain Decision Engine — records structured decision metadata."""
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
import logging

from packages.brain.schemas import DecisionRecord

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Records structured decision metadata for Brain decisions.

    Does NOT store private model chain-of-thought.
    Stores structured decision metadata only.
    """

    def __init__(self):
        self._decisions: dict[str, DecisionRecord] = {}
        self._case_decisions: dict[str, list[str]] = {}

    def record_decision(self, decision: DecisionRecord) -> str:
        """Record a decision and return its ID."""
        self._decisions[decision.decision_id] = decision
        self._case_decisions.setdefault(decision.case_id, []).append(decision.decision_id)
        logger.info(
            f"Decision recorded: {decision.decision_id} case={decision.case_id} "
            f"tool={decision.selected_tool} confidence={decision.confidence}"
        )
        return decision.decision_id

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a specific decision by ID."""
        return self._decisions.get(decision_id)

    def get_decisions(self, case_id: str) -> list[DecisionRecord]:
        """Get all decisions for a case."""
        ids = self._case_decisions.get(case_id, [])
        return [self._decisions[did] for did in ids if did in self._decisions]

    def get_decision_count(self, case_id: str) -> int:
        """Get the number of decisions for a case."""
        return len(self._case_decisions.get(case_id, []))

    def get_total_decisions(self) -> int:
        """Get total decisions across all cases."""
        return len(self._decisions)

    def query_decisions(self, case_id: Optional[str] = None, tool_id: Optional[str] = None) -> list[DecisionRecord]:
        """Query decisions by case and/or tool."""
        results = list(self._decisions.values())
        if case_id:
            results = [d for d in results if d.case_id == case_id]
        if tool_id:
            results = [d for d in results if d.selected_tool == tool_id]
        return results
