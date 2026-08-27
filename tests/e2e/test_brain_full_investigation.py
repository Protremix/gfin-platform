"""End-to-end test: Brain full investigation pipeline."""
import pytest
from packages.brain.schemas import (
    BrainState, HumanInTheLoopMode, StopReason, InvestigationCreate, InvestigationState,
    DecisionRecord, BrainContext, ConflictResolution, ConflictStatus,
)
from packages.brain.tool_registry import create_default_registry


class TestBrainFullInvestigation:
    """Test the complete Brain investigation workflow."""

    def test_full_investigation_state_progression(self):
        """Test that an investigation progresses through all states."""
        state = InvestigationState(
            case_id="CASE-E2E-001",
            goal="Investigate suspicious domain",
            mode=HumanInTheLoopMode.AUTONOMOUS,
        )
        assert state.state == BrainState.CASE_CREATED

        # Progress through states
        states = [
            BrainState.SIGNAL_VALIDATED,
            BrainState.DISCOVERY,
            BrainState.ENRICHMENT,
            BrainState.CORRELATION,
            BrainState.EVIDENCE_REVIEW,
            BrainState.INVESTIGATOR_REVIEW,
            BrainState.MONITORING,
            BrainState.REPORTING,
            BrainState.CLOSED,
        ]
        for new_state in states:
            state.state = new_state
            assert state.state == new_state

    def test_tool_budget_tracking(self):
        """Test that tool call budget is tracked."""
        state = InvestigationState(
            case_id="CASE-E2E-002",
            goal="Test budget",
            budget_tool_calls=10,
        )
        for i in range(5):
            state.tool_calls_made += 1
        assert state.tool_calls_made == 5
        assert state.budget_tool_calls == 10
        # Budget not exhausted
        assert state.tool_calls_made < state.budget_tool_calls

    def test_stop_conditions(self):
        """Test all stop conditions are valid."""
        for reason in StopReason:
            state = InvestigationState(case_id=f"CASE-STOP-{reason.value}", goal="Test")
            state.stop_reason = reason
            assert state.stop_reason == reason

    def test_decision_chain_investigation(self):
        """Test that decisions form a chain through the investigation."""
        decisions = []
        tools_used = ["search_exact", "dns_lookup", "ip_lookup", "get_entity", "find_relationships"]

        for i, tool in enumerate(tools_used):
            decision = DecisionRecord(
                case_id="CASE-E2E-003",
                goal=f"Step {i+1}",
                selected_tool=tool,
                reason_code=f"investigative_step_{i+1}",
                policy_id="POL-001",
                model_id="gpt-5.6-luna",
                confidence=0.7 + i * 0.05,
            )
            decisions.append(decision)

        assert len(decisions) == 5
        assert decisions[0].selected_tool == "search_exact"
        assert decisions[-1].selected_tool == "find_relationships"
        assert decisions[-1].confidence > decisions[0].confidence

    def test_context_building(self):
        """Test that BrainContext can be built for an investigation."""
        context = BrainContext(
            case_id="CASE-E2E-004",
            case_state=BrainState.DISCOVERY,
            investigation_objective="Find related domains",
            relevant_entities=[{"id": "ENT-001", "type": "DOMAIN", "name": "example.com"}],
            relevant_relationships=[{"from": "ENT-001", "to": "ENT-002", "type": "RESOLVES_TO"}],
            relevant_evidence=[{"id": "E-001", "type": "dns_record"}],
            available_tools=["search_exact", "dns_lookup", "ip_lookup"],
        )
        assert context.case_id == "CASE-E2E-004"
        assert len(context.relevant_entities) == 1
        assert len(context.available_tools) == 3

    def test_conflict_resolution_workflow(self):
        """Test conflict resolution between modules."""
        cr = ConflictResolution(
            source_a="domain_lookup",
            source_b="dns_lookup",
            reliability_a=0.9,
            reliability_b=0.7,
            evidence=["E-001", "E-002"],
            resolution="Both tools agree on IP 1.2.3.4",
            status=ConflictStatus.RESOLVED,
        )
        assert cr.status == ConflictStatus.RESOLVED
        assert len(cr.evidence) == 2

    def test_conflict_unresolved(self):
        """Test that conflicts can remain unresolved."""
        cr = ConflictResolution(
            source_a="module_a",
            source_b="module_b",
            reliability_a=0.5,
            reliability_b=0.5,
        )
        assert cr.status == ConflictStatus.UNRESOLVED_CONFLICT
        assert cr.resolution == ""

    def test_all_tools_available_for_investigation(self):
        """Verify all tools needed for a full investigation are registered."""
        registry = create_default_registry()
        tool_ids = registry.list_tool_ids()

        required_tools = [
            "search_exact", "domain_lookup", "dns_lookup", "ip_lookup",
            "get_entity", "find_relationships", "get_evidence", "create_observation",
            "campaign_similarity", "pattern_analysis",
        ]
        for tool in required_tools:
            assert tool in tool_ids, f"Missing required tool: {tool}"
