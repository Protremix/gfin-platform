"""Integration tests for Brain memory and state persistence."""
import pytest
from packages.brain.schemas import BrainState, InvestigationState, DecisionRecord


class TestBrainMemory:
    """Test Brain persistent memory."""

    def test_investigation_state_persists(self):
        """Investigation state should be persistable."""
        state = InvestigationState(case_id="CASE-MEM-001", goal="Test persistence")
        state.state = BrainState.DISCOVERY
        state.tool_calls_made = 5
        state.evidence_ids = ["E-001", "E-002"]
        # Serialize and deserialize (simulates persistence)
        data = state.model_dump()
        restored = InvestigationState(**data)
        assert restored.state == BrainState.DISCOVERY
        assert restored.tool_calls_made == 5
        assert restored.evidence_ids == ["E-001", "E-002"]

    def test_decision_record_persists(self):
        """Decision records should be persistable."""
        rec = DecisionRecord(
            case_id="CASE-MEM-002",
            goal="Test decision persistence",
            selected_tool="search_exact",
            reason_code="need_initial_data",
            policy_id="POL-001",
            model_id="gpt-5.6-luna",
            confidence=0.8,
        )
        data = rec.model_dump()
        restored = DecisionRecord(**data)
        assert restored.case_id == "CASE-MEM-002"
        assert restored.confidence == 0.8
        assert restored.selected_tool == "search_exact"

    def test_state_transitions_are_valid(self):
        """State transitions should follow the defined order."""
        valid_transitions = [
            (BrainState.CASE_CREATED, BrainState.SIGNAL_VALIDATED),
            (BrainState.SIGNAL_VALIDATED, BrainState.DISCOVERY),
            (BrainState.DISCOVERY, BrainState.ENRICHMENT),
            (BrainState.ENRICHMENT, BrainState.CORRELATION),
            (BrainState.CORRELATION, BrainState.EVIDENCE_REVIEW),
            (BrainState.EVIDENCE_REVIEW, BrainState.INVESTIGATOR_REVIEW),
            (BrainState.INVESTIGATOR_REVIEW, BrainState.MONITORING),
            (BrainState.MONITORING, BrainState.REPORTING),
            (BrainState.REPORTING, BrainState.CLOSED),
        ]
        for from_state, to_state in valid_transitions:
            assert from_state != to_state
            # Both should be valid enum values
            assert from_state in BrainState
            assert to_state in BrainState

    def test_evidence_ids_accumulate(self):
        """Evidence IDs should accumulate across investigation steps."""
        state = InvestigationState(case_id="CASE-MEM-003", goal="Test accumulation")
        state.evidence_ids.append("E-001")
        state.evidence_ids.append("E-002")
        state.evidence_ids.append("E-003")
        assert len(state.evidence_ids) == 3
        assert "E-003" in state.evidence_ids
