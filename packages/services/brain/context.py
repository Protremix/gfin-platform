"""GFIN Brain Context Engine — selects minimum relevant information for decisions."""
from __future__ import annotations
from typing import Any
import logging

from packages.brain.schemas import BrainContext, BrainState, InvestigationState

logger = logging.getLogger(__name__)


class ContextEngine:
    """Selects the minimum relevant information required for the current decision.

    Prevents:
    - Unnecessary data exposure
    - Context overload
    - Cross-case leakage
    - Classification violations
    """

    def __init__(self, max_context_size: int = 32000):
        self.max_context_size = max_context_size
        self._entity_store: dict[str, list] = {}
        self._relationship_store: dict[str, list] = {}
        self._evidence_store: dict[str, list] = {}
        self._timeline_store: dict[str, list] = {}
        self._search_store: dict[str, list] = {}

    def build_context(self, state: InvestigationState) -> BrainContext:
        """Build a controlled context package for the current decision."""
        case_id = state.case_id

        # Get relevant entities (limited to prevent overload)
        entities = self._entity_store.get(case_id, [])
        relevant_entities = self._select_relevant(entities, limit=20)

        # Get relevant relationships
        relationships = self._relationship_store.get(case_id, [])
        relevant_rels = self._select_relevant(relationships, limit=30)

        # Get relevant evidence
        evidence = self._evidence_store.get(case_id, [])
        relevant_evidence = self._select_relevant(evidence, limit=15)

        # Get timeline
        timeline = self._timeline_store.get(case_id, [])

        # Get previous searches
        searches = self._search_store.get(case_id, [])
        recent_searches = searches[-10:]  # Last 10 searches

        context = BrainContext(
            case_id=case_id,
            case_state=state.state,
            investigation_objective=state.goal,
            relevant_entities=relevant_entities,
            relevant_relationships=relevant_rels,
            relevant_evidence=relevant_evidence,
            timeline=timeline,
            previous_searches=recent_searches,
            current_permissions=[],  # Set by security layer
            current_classification="PUBLIC",
            available_tools=[],  # Set by tool registry
        )

        self._check_context_size(context)
        return context

    def store_entity(self, case_id: str, entity: dict[str, Any]) -> None:
        """Store an entity for a case."""
        self._entity_store.setdefault(case_id, []).append(entity)

    def store_relationship(self, case_id: str, relationship: dict[str, Any]) -> None:
        """Store a relationship for a case."""
        self._relationship_store.setdefault(case_id, []).append(relationship)

    def store_evidence(self, case_id: str, evidence: dict[str, Any]) -> None:
        """Store evidence for a case."""
        self._evidence_store.setdefault(case_id, []).append(evidence)

    def store_timeline_event(self, case_id: str, event: dict[str, Any]) -> None:
        """Store a timeline event for a case."""
        self._timeline_store.setdefault(case_id, []).append(event)

    def store_search(self, case_id: str, search: dict[str, Any]) -> None:
        """Store a search record for a case."""
        self._search_store.setdefault(case_id, []).append(search)

    def _select_relevant(self, items: list, limit: int = 20) -> list:
        """Select the most relevant items, respecting limits."""
        if len(items) <= limit:
            return items
        # Simple selection: most recent items
        return items[-limit:]

    def _check_context_size(self, context: BrainContext) -> None:
        """Check that context does not exceed size limit."""
        import json
        size = len(json.dumps(context.model_dump()))
        if size > self.max_context_size:
            logger.warning(
                f"Context size {size} exceeds limit {self.max_context_size} for case {context.case_id}"
            )

    def clear_case(self, case_id: str) -> None:
        """Clear all stored data for a case (prevents cross-case leakage)."""
        self._entity_store.pop(case_id, None)
        self._relationship_store.pop(case_id, None)
        self._evidence_store.pop(case_id, None)
        self._timeline_store.pop(case_id, None)
        self._search_store.pop(case_id, None)
