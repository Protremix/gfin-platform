"""Integration tests for Brain restart and recovery."""
import pytest
from packages.brain.schemas import BrainState, InvestigationState, DecisionRecord


class TestBrainRestart:
    """Test Brain can resume after restart."""

    def test_state_recovery_after_restart(self):
        """Brain should recover investigation state after restart."""
        # Simulate pre-restart state
        state = InvestigationState(case_id="CASE-RST-001", goal="Test restart")
        state.state = BrainState.CORRELATION
        state.tool_calls_made = 42
        state.evidence_ids = ["E-001", "E-002", "E-003"]
        state.entity_ids = ["ENT-001", "ENT-002"]
        state.relationship_ids = ["REL-001"]

        # Simulate persistence (serialize)
        serialized = state.model_dump()

        # Simulate restart (deserialize)
        restored = InvestigationState(**serialized)
        assert restored.state == BrainState.CORRELATION
        assert restored.tool_calls_made == 42
        assert len(restored.evidence_ids) == 3
        assert len(restored.entity_ids) == 2
        assert len(restored.relationship_ids) == 1

    def test_audit_continuity_after_restart(self):
        """Audit records should survive restart."""
        decisions = [
            DecisionRecord(
                case_id="CASE-RST-002",
                goal="Step 1",
                selected_tool="search_exact",
                reason_code="initial_search",
                policy_id="POL-001",
                model_id="gpt-5.6-luna",
                confidence=0.7,
            ),
            DecisionRecord(
                case_id="CASE-RST-002",
                goal="Step 2",
                selected_tool="dns_lookup",
                reason_code="need_infrastructure_data",
                policy_id="POL-001",
                model_id="gpt-5.6-luna",
                confidence=0.8,
            ),
        ]

        # Serialize all decisions
        serialized = [d.model_dump() for d in decisions]

        # Restore after "restart"
        restored = [DecisionRecord(**d) for d in serialized]
        assert len(restored) == 2
        assert restored[0].selected_tool == "search_exact"
        assert restored[1].selected_tool == "dns_lookup"
        assert restored[1].confidence == 0.8

    def test_resume_from_each_state(self):
        """Brain should be able to resume from any valid state."""
        for state in BrainState:
            inv = InvestigationState(case_id=f"CASE-RST-{state.value}", goal="Test resume")
            inv.state = state
            # Should be able to serialize and restore from any state
            restored = InvestigationState(**inv.model_dump())
            assert restored.state == state
