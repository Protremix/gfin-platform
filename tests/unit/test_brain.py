"""Unit tests for GFIN Brain service."""
import pytest
from packages.brain.schemas import (
    BrainState, HumanInTheLoopMode, StopReason, RiskLevel,
    ToolDefinition, ToolInputSchema, ToolOutputSchema,
    DecisionRecord, BrainContext, InvestigationCreate, InvestigationState,
    ConflictResolution, ConflictStatus, HealthReport, BrainStatus,
    ComponentStatus, ComponentHealth,
)
from packages.brain.tool_registry import ToolRegistry, create_default_registry


class TestBrainSchemas:
    """Test Brain schema validation."""

    def test_brain_state_enum(self):
        assert BrainState.CASE_CREATED == "case_created"
        assert BrainState.CLOSED == "closed"
        assert len(BrainState) == 10

    def test_human_mode_enum(self):
        assert HumanInTheLoopMode.ASSISTED == "assisted"
        assert HumanInTheLoopMode.SUPERVISED == "supervised"
        assert HumanInTheLoopMode.AUTONOMOUS == "autonomous"

    def test_stop_reason_enum(self):
        assert StopReason.GOAL_SATISFIED == "goal_satisfied"
        assert len(StopReason) == 7

    def test_risk_level_enum(self):
        assert RiskLevel.LOW == "low"
        assert RiskLevel.CRITICAL == "critical"

    def test_tool_definition_defaults(self):
        tool = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
        )
        assert tool.enabled is True
        assert tool.risk_level == RiskLevel.LOW
        assert tool.rate_limit == 60
        assert tool.timeout == 30

    def test_decision_record_auto_id(self):
        rec = DecisionRecord(
            case_id="CASE-001",
            goal="test goal",
            selected_tool="search_exact",
            reason_code="need_data",
            policy_id="POL-001",
            model_id="gpt-5.6-luna",
        )
        assert rec.decision_id  # auto-generated UUID
        assert rec.confidence == 0.0
        assert rec.result is None

    def test_investigation_create_defaults(self):
        inv = InvestigationCreate(case_id="CASE-001", goal="Find fraud")
        assert inv.mode == HumanInTheLoopMode.SUPERVISED
        assert inv.budget_tool_calls == 100
        assert inv.evidence_threshold == 0.7

    def test_investigation_state_defaults(self):
        state = InvestigationState(case_id="CASE-001", goal="Find fraud")
        assert state.state == BrainState.CASE_CREATED
        assert state.tool_calls_made == 0
        assert state.stop_reason is None

    def test_conflict_resolution_defaults(self):
        cr = ConflictResolution(source_a="module_a", source_b="module_b")
        assert cr.status == ConflictStatus.UNRESOLVED_CONFLICT
        assert cr.conflict_id  # auto-generated

    def test_health_report(self):
        report = HealthReport(
            healthy=True,
            components=[ComponentStatus(name="tool_registry", health=ComponentHealth.HEALTHY)],
        )
        assert report.healthy is True
        assert len(report.components) == 1


class TestToolRegistry:
    """Test ToolRegistry."""

    def test_register_tool(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test",
            input_schema=ToolInputSchema(required=["query"]),
            output_schema=ToolOutputSchema(),
            required_permissions=["search:read"],
        )
        registry.register(tool, lambda **kw: {"ok": True})
        assert registry.is_valid("test_tool")
        assert registry.get_tool("test_tool") is not None

    def test_duplicate_register_raises(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="dup_tool",
            name="Dup",
            description="dup",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
        )
        registry.register(tool, lambda **kw: {})
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool, lambda **kw: {})

    def test_unregister(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="temp_tool",
            name="Temp",
            description="temp",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
        )
        registry.register(tool, lambda **kw: {})
        assert registry.is_valid("temp_tool")
        registry.unregister("temp_tool")
        assert not registry.is_valid("temp_tool")

    def test_validate_params(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="valid_tool",
            name="Valid",
            description="valid",
            input_schema=ToolInputSchema(required=["query"]),
            output_schema=ToolOutputSchema(),
        )
        registry.register(tool, lambda **kw: {})
        ok, msg = registry.validate_params("valid_tool", {"query": "test"})
        assert ok is True
        ok, msg = registry.validate_params("valid_tool", {})
        assert ok is False
        assert "query" in msg

    def test_check_permissions(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="perm_tool",
            name="Perm",
            description="perm",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
            required_permissions=["admin:read"],
        )
        registry.register(tool, lambda **kw: {})
        ok, _ = registry.check_permissions("perm_tool", ["admin:read"])
        assert ok is True
        ok, msg = registry.check_permissions("perm_tool", ["user:read"])
        assert ok is False
        assert "admin:read" in msg

    def test_check_classification(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="class_tool",
            name="Class",
            description="class",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
            classification="RESTRICTED",
        )
        registry.register(tool, lambda **kw: {})
        ok, _ = registry.check_classification("class_tool", "LAW_ENFORCEMENT")
        assert ok is True
        ok, msg = registry.check_classification("class_tool", "PUBLIC")
        assert ok is False

    def test_default_registry(self):
        registry = create_default_registry()
        tools = registry.list_tools()
        assert len(tools) > 0
        # Check key tools are registered
        tool_ids = [t.tool_id for t in tools]
        assert "search_exact" in tool_ids
        assert "domain_lookup" in tool_ids
        assert "dns_lookup" in tool_ids
        assert "get_entity" in tool_ids
        assert "get_evidence" in tool_ids
        assert "wallet_lookup" in tool_ids
        assert "campaign_similarity" in tool_ids

    def test_get_all_definitions(self):
        registry = create_default_registry()
        defs = registry.get_all_definitions()
        assert len(defs) > 0
        assert "search_exact" in defs
        assert "name" in defs["search_exact"]

    def test_disabled_tool(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="disabled_tool",
            name="Disabled",
            description="disabled",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
            enabled=False,
        )
        registry.register(tool, lambda **kw: {})
        assert not registry.is_valid("disabled_tool")
        assert "disabled_tool" not in registry.list_tool_ids(enabled_only=True)


class TestBrainStateTransitions:
    """Test BrainState transitions."""

    def test_state_order(self):
        states = list(BrainState)
        assert states[0] == BrainState.CASE_CREATED
        assert states[-1] == BrainState.CLOSED

    def test_state_values(self):
        assert BrainState.CASE_CREATED.value == "case_created"
        assert BrainState.SIGNAL_VALIDATED.value == "signal_validated"
        assert BrainState.DISCOVERY.value == "discovery"
        assert BrainState.ENRICHMENT.value == "enrichment"
        assert BrainState.CORRELATION.value == "correlation"
        assert BrainState.EVIDENCE_REVIEW.value == "evidence_review"
        assert BrainState.INVESTIGATOR_REVIEW.value == "investigator_review"
        assert BrainState.MONITORING.value == "monitoring"
        assert BrainState.REPORTING.value == "reporting"
        assert BrainState.CLOSED.value == "closed"
