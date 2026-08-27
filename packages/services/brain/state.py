"""GFIN Brain State Manager — investigation state with persistence."""
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
import logging

from packages.brain.schemas import BrainState

logger = logging.getLogger(__name__)


class StateManager:
    """Manages investigation state with persistence across restarts.

    States: CASE_CREATED -> SIGNAL_VALIDATED -> DISCOVERY -> ENRICHMENT ->
    CORRELATION -> EVIDENCE_REVIEW -> INVESTIGATOR_REVIEW -> MONITORING ->
    REPORTING -> CLOSED
    """

    # Valid state transitions
    TRANSITIONS: dict[BrainState, list[BrainState]] = {
        BrainState.CASE_CREATED: [BrainState.SIGNAL_VALIDATED],
        BrainState.SIGNAL_VALIDATED: [BrainState.DISCOVERY],
        BrainState.DISCOVERY: [BrainState.ENRICHMENT],
        BrainState.ENRICHMENT: [BrainState.CORRELATION],
        BrainState.CORRELATION: [BrainState.EVIDENCE_REVIEW],
        BrainState.EVIDENCE_REVIEW: [BrainState.INVESTIGATOR_REVIEW],
        BrainState.INVESTIGATOR_REVIEW: [BrainState.MONITORING, BrainState.CLOSED],
        BrainState.MONITORING: [BrainState.REPORTING],
        BrainState.REPORTING: [BrainState.CLOSED],
        BrainState.CLOSED: [],
    }

    def __init__(self):
        self._states: dict[str, BrainState] = {}
        self._timestamps: dict[str, datetime] = {}

    def get_state(self, case_id: str) -> Optional[BrainState]:
        """Get the current state of a case."""
        return self._states.get(case_id)

    def set_state(self, case_id: str, state: BrainState) -> None:
        """Set the state directly (initial state only)."""
        self._states[case_id] = state
        self._timestamps[case_id] = datetime.now(timezone.utc)
        logger.info(f"State set: {case_id} -> {state.value}")

    def transition(self, case_id: str, new_state: BrainState) -> bool:
        """Transition to a new state if valid."""
        current = self._states.get(case_id)
        if current is None:
            logger.error(f"Case not found: {case_id}")
            return False

        allowed = self.TRANSITIONS.get(current, [])
        if new_state not in allowed:
            logger.error(f"Invalid transition: {case_id} {current.value} -> {new_state.value}")
            return False

        self._states[case_id] = new_state
        self._timestamps[case_id] = datetime.now(timezone.utc)
        logger.info(f"State transition: {case_id} {current.value} -> {new_state.value}")
        return True

    def can_resume(self, case_id: str) -> bool:
        """Check if a case can be resumed from its current state."""
        state = self._states.get(case_id)
        if state is None:
            return False
        return state != BrainState.CLOSED

    def get_all_states(self) -> dict[str, BrainState]:
        """Get all case states (for recovery after restart)."""
        return dict(self._states)

    def restore_states(self, states: dict[str, BrainState]) -> None:
        """Restore states after restart."""
        self._states.update(states)
        self._timestamps = {cid: datetime.now(timezone.utc) for cid in states}
        logger.info(f"Restored {len(states)} case states")
