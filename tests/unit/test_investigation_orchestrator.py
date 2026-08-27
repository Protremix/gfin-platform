"""Tests for AI Investigation Orchestrator — Module 22.

Tests cover:
- ToolRegistry: register, unregister, authorize, execute, list, call log
- InvestigationTool: validate_params, execute, concrete tool implementations
- InvestigationPlan: add steps, completion status
- InvestigationStep: status transitions
- InvestigationResult: evidence, claims, unverified, human review
- Orchestrator: plan, execute, synthesize, generate report
- Integration: full investigation pipeline
"""

from unittest.mock import MagicMock

import pytest

from services.investigation_orchestrator import (
    Claim,
    CreateAlertTool,
    DnsLookupTool,
    DomainLookupTool,
    EntityCompareTool,
    Evidence,
    EvidenceType,
    InvestigationPlan,
    InvestigationResult,
    InvestigationStep,
    InvestigationTool,
    Orchestrator,
    RequestInformationTool,
    SearchWebTool,
    StepStatus,
    ToolParam,
    ToolRegistry,
    UserRole,
    create_default_registry,
)

# ─── Fixtures ───


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def orchestrator(mock_event_bus, mock_audit):
    reg = create_default_registry(audit_logger=mock_audit)
    return Orchestrator(registry=reg, event_bus=mock_event_bus, audit_logger=mock_audit)


# ─── ToolRegistry Tests ───


class TestToolRegistry:
    def test_register_tool(self):
        reg = ToolRegistry()
        tool = SearchWebTool()
        reg.register(tool)
        assert reg.tool_count == 1
        assert reg.get_tool("search_web") is not None

    def test_unregister_tool(self):
        reg = ToolRegistry()
        reg.register(SearchWebTool())
        assert reg.unregister("search_web") is True
        assert reg.tool_count == 0

    def test_unregister_nonexistent(self):
        reg = ToolRegistry()
        assert reg.unregister("nonexistent") is False

    def test_get_tool_nonexistent(self):
        reg = ToolRegistry()
        assert reg.get_tool("nonexistent") is None

    def test_authorize_investigator_can_use_basic(self):
        reg = ToolRegistry()
        reg.register(DomainLookupTool())
        assert reg.authorize(UserRole.INVESTIGATOR.value, "domain_lookup") is True

    def test_authorize_investigator_cannot_use_supervisor_tool(self):
        reg = ToolRegistry()
        reg.register(CreateAlertTool())
        assert reg.authorize(UserRole.INVESTIGATOR.value, "create_alert") is False

    def test_authorize_supervisor_can_use_supervisor_tool(self):
        reg = ToolRegistry()
        reg.register(CreateAlertTool())
        assert reg.authorize(UserRole.SUPERVISOR.value, "create_alert") is True

    def test_authorize_admin_can_use_anything(self):
        reg = ToolRegistry()
        reg.register(RequestInformationTool())
        assert reg.authorize(UserRole.ADMIN.value, "request_information") is True

    def test_authorize_nonexistent_tool(self):
        reg = ToolRegistry()
        assert reg.authorize(UserRole.ADMIN.value, "nonexistent") is False

    def test_list_tools_no_filter(self):
        reg = create_default_registry()
        tools = reg.list_tools()
        assert len(tools) == 15

    def test_list_tools_by_investigator_role(self):
        reg = create_default_registry()
        tools = reg.list_tools(user_role=UserRole.INVESTIGATOR.value)
        # Investigator can use all tools with required_role <= INVESTIGATOR (level 1)
        tool_names = [t["name"] for t in tools]
        assert "domain_lookup" in tool_names
        assert "create_alert" not in tool_names

    def test_list_tools_by_supervisor_role(self):
        reg = create_default_registry()
        tools = reg.list_tools(user_role=UserRole.SUPERVISOR.value)
        tool_names = [t["name"] for t in tools]
        assert "create_alert" in tool_names
        assert "request_information" in tool_names

    def test_execute_success(self, mock_audit):
        reg = ToolRegistry(audit_logger=mock_audit)
        reg.register(DomainLookupTool())
        result = reg.execute(
            user="analyst1",
            user_role=UserRole.INVESTIGATOR.value,
            tool_name="domain_lookup",
            params={"domain": "example.com"},
        )
        assert "result" in result
        assert "evidence_id" in result
        assert result["evidence_id"].startswith("EVD-")
        assert result["result"]["domain"] == "example.com"

    def test_execute_unauthorized(self):
        reg = ToolRegistry()
        reg.register(CreateAlertTool())
        with pytest.raises(PermissionError):
            reg.execute(
                user="user1",
                user_role=UserRole.INVESTIGATOR.value,
                tool_name="create_alert",
                params={"target_type": "entity", "target_id": "ENT-001", "priority": "HIGH"},
            )

    def test_execute_nonexistent_tool(self):
        reg = ToolRegistry()
        with pytest.raises(ValueError, match="Tool not found"):
            reg.execute("user", UserRole.ADMIN.value, "nonexistent", {})

    def test_execute_invalid_params(self):
        reg = ToolRegistry()
        reg.register(DomainLookupTool())
        with pytest.raises(ValueError, match="Missing required parameter"):
            reg.execute("user", UserRole.INVESTIGATOR.value, "domain_lookup", {})

    def test_execute_logs_call(self):
        reg = ToolRegistry()
        reg.register(DomainLookupTool())
        reg.execute("user1", UserRole.INVESTIGATOR.value, "domain_lookup", {"domain": "test.com"})
        log = reg.get_call_log()
        assert len(log) == 1
        assert log[0].tool_name == "domain_lookup"
        assert log[0].user == "user1"
        assert log[0].success is True

    def test_execute_audit_logged(self, mock_audit):
        reg = ToolRegistry(audit_logger=mock_audit)
        reg.register(DomainLookupTool())
        reg.execute("user1", UserRole.INVESTIGATOR.value, "domain_lookup", {"domain": "test.com"})
        mock_audit.log.assert_called_once()

    def test_get_call_log_by_tool(self):
        reg = ToolRegistry()
        reg.register(DomainLookupTool())
        reg.register(DnsLookupTool())
        reg.execute("user1", UserRole.INVESTIGATOR.value, "domain_lookup", {"domain": "a.com"})
        reg.execute("user1", UserRole.INVESTIGATOR.value, "dns_lookup", {"domain": "b.com"})
        log = reg.get_call_log(tool_name="domain_lookup")
        assert len(log) == 1
        assert log[0].tool_name == "domain_lookup"

    def test_get_call_log_by_user(self):
        reg = ToolRegistry()
        reg.register(DomainLookupTool())
        reg.execute("user1", UserRole.INVESTIGATOR.value, "domain_lookup", {"domain": "a.com"})
        reg.execute("user2", UserRole.INVESTIGATOR.value, "domain_lookup", {"domain": "b.com"})
        log = reg.get_call_log(user="user1")
        assert len(log) == 1
        assert log[0].user == "user1"


# ─── InvestigationTool Tests ───


class TestInvestigationTool:
    def test_validate_params_success(self):
        tool = DomainLookupTool()
        valid, _msg = tool.validate_params({"domain": "example.com"})
        assert valid is True

    def test_validate_params_missing(self):
        tool = DomainLookupTool()
        valid, msg = tool.validate_params({})
        assert valid is False
        assert "domain" in msg

    def test_execute_returns_data(self):
        tool = DomainLookupTool()
        result = tool.execute({"domain": "example.com"})
        assert result["domain"] == "example.com"

    def test_to_dict(self):
        tool = DomainLookupTool()
        d = tool.to_dict()
        assert d["name"] == "domain_lookup"
        assert "description" in d
        assert "params" in d

    def test_search_web_tool(self):
        tool = SearchWebTool()
        result = tool.execute({"query": "fraud"})
        assert result["query"] == "fraud"

    def test_entity_compare_tool(self):
        tool = EntityCompareTool()
        result = tool.execute({"entity_a": "E1", "entity_b": "E2"})
        assert result["entity_a"] == "E1"
        assert result["entity_b"] == "E2"

    def test_create_alert_tool(self):
        tool = CreateAlertTool()
        result = tool.execute(
            {"target_type": "domain", "target_id": "example.com", "priority": "HIGH"}
        )
        assert "alert_id" in result

    def test_request_information_tool(self):
        tool = RequestInformationTool()
        result = tool.execute({"target_jurisdiction": "EU", "entity_id": "E1"})
        assert "request_id" in result
        assert result["status"] == "pending"


# ─── InvestigationPlan Tests ───


class TestInvestigationPlan:
    def test_add_step(self):
        plan = InvestigationPlan(id="PLAN-001", target="example.com", objective="Investigate")
        step = plan.add_step("domain_lookup", {"domain": "example.com"})
        assert len(plan.steps) == 1
        assert step.id == "STEP-001"
        assert step.tool_name == "domain_lookup"
        assert step.status == StepStatus.PENDING.value

    def test_add_multiple_steps(self):
        plan = InvestigationPlan(id="PLAN-001", target="example.com", objective="Investigate")
        plan.add_step("domain_lookup", {"domain": "example.com"})
        plan.add_step("dns_lookup", {"domain": "example.com"})
        plan.add_step("graph_search", {"entity_id": "example.com"})
        assert len(plan.steps) == 3
        assert plan.steps[2].id == "STEP-003"

    def test_completed_steps(self):
        plan = InvestigationPlan(id="PLAN-001", target="example.com", objective="Investigate")
        step1 = plan.add_step("domain_lookup", {"domain": "example.com"})
        plan.add_step("dns_lookup", {"domain": "example.com"})
        step1.mark_completed({"result": "data"}, ["EVD-001"])
        assert plan.completed_steps == 1

    def test_is_complete(self):
        plan = InvestigationPlan(id="PLAN-001", target="example.com", objective="Investigate")
        step1 = plan.add_step("domain_lookup")
        step2 = plan.add_step("dns_lookup")
        assert plan.is_complete is False
        step1.mark_completed({}, [])
        step2.mark_completed({}, [])
        assert plan.is_complete is True

    def test_is_complete_with_failure(self):
        plan = InvestigationPlan(id="PLAN-001", target="x.com", objective="test")
        step1 = plan.add_step("domain_lookup")
        step1.mark_failed("Error")
        assert plan.is_complete is True


# ─── InvestigationStep Tests ───


class TestInvestigationStep:
    def test_mark_running(self):
        step = InvestigationStep(id="S1", tool_name="domain_lookup")
        step.mark_running()
        assert step.status == StepStatus.RUNNING.value

    def test_mark_completed(self):
        step = InvestigationStep(id="S1", tool_name="domain_lookup")
        step.mark_completed({"data": "test"}, ["EVD-001", "EVD-002"])
        assert step.status == StepStatus.COMPLETED.value
        assert step.result == {"data": "test"}
        assert len(step.evidence_ids) == 2

    def test_mark_failed(self):
        step = InvestigationStep(id="S1", tool_name="domain_lookup")
        step.mark_failed("Connection error")
        assert step.status == StepStatus.FAILED.value
        assert step.error == "Connection error"

    def test_mark_skipped(self):
        step = InvestigationStep(id="S1", tool_name="domain_lookup")
        step.mark_skipped()
        assert step.status == StepStatus.SKIPPED.value


# ─── InvestigationResult Tests ───


class TestInvestigationResult:
    def test_default_result(self):
        result = InvestigationResult(plan_id="P1", target="example.com", objective="test")
        assert result.steps_completed == 0
        assert result.steps_failed == 0
        assert len(result.evidence) == 0
        assert result.requires_human_review is False

    def test_add_evidence_and_claims(self):
        result = InvestigationResult(plan_id="P1", target="example.com", objective="test")
        ev = Evidence(
            id="EVD-001", evidence_type="TOOL_OUTPUT", source="domain_lookup", description="test"
        )
        result.evidence.append(ev)
        claim = Claim(id="CLM-001", statement="Test claim", evidence_ids=["EVD-001"])
        result.claims.append(claim)
        assert len(result.evidence) == 1
        assert len(result.claims) == 1

    def test_unverified_claims(self):
        result = InvestigationResult(plan_id="P1", target="x.com", objective="test")
        result.unverified_claims.append("Cannot verify domain ownership")
        assert len(result.unverified_claims) == 1

    def test_requires_human_review(self):
        result = InvestigationResult(plan_id="P1", target="x.com", objective="test")
        result.requires_human_review = True
        assert result.requires_human_review is True


# ─── Orchestrator Tests ───


class TestOrchestrator:
    def test_plan_investigation(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "Investigate fraud")
        assert plan.target == "example.com"
        assert plan.objective == "Investigate fraud"
        assert len(plan.steps) >= 5

    def test_plan_has_ordered_steps(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "test")
        for i, step in enumerate(plan.steps):
            assert step.id == f"STEP-{i + 1:03d}"

    def test_plan_event_published(self, mock_event_bus, mock_audit):
        reg = create_default_registry()
        orch = Orchestrator(registry=reg, event_bus=mock_event_bus)
        orch.plan_investigation("example.com", "test")
        mock_event_bus.publish.assert_called()
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "investigation.planned" in topics

    def test_execute_plan_success(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "Investigate")
        result = orchestrator.execute_plan(plan, user="investigator1")
        assert result.steps_completed > 0
        assert len(result.evidence) > 0
        assert len(result.claims) > 0

    def test_execute_plan_all_steps(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "test")
        result = orchestrator.execute_plan(plan, user="investigator1")
        assert result.steps_completed == len(plan.steps)

    def test_execute_plan_generates_evidence(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "test")
        result = orchestrator.execute_plan(plan, user="investigator1")
        for ev in result.evidence:
            assert ev.id.startswith("EVD-")
            assert ev.evidence_type == EvidenceType.TOOL_OUTPUT.value

    def test_execute_plan_generates_claims(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "test")
        result = orchestrator.execute_plan(plan, user="investigator1")
        for claim in result.claims:
            if claim.verified:
                assert len(claim.evidence_ids) > 0

    def test_execute_plan_completion_event(self, mock_event_bus, mock_audit):
        reg = create_default_registry()
        orch = Orchestrator(registry=reg, event_bus=mock_event_bus)
        plan = orch.plan_investigation("example.com", "test")
        orch.execute_plan(plan, user="investigator1")
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "investigation.completed" in topics

    def test_execute_plan_skips_unauthorized(self, mock_event_bus, mock_audit):
        reg = create_default_registry()
        orch = Orchestrator(registry=reg, event_bus=mock_event_bus)
        plan = InvestigationPlan(id="P1", target="example.com", objective="test")
        plan.add_step("domain_lookup", {"domain": "example.com"})
        plan.add_step(
            "create_alert",
            {"target_type": "domain", "target_id": "example.com", "priority": "HIGH"},
        )
        result = orch.execute_plan(
            plan, user="investigator1", user_role=UserRole.INVESTIGATOR.value
        )
        # domain_lookup should complete, create_alert should be skipped
        assert result.steps_completed == 1
        assert plan.steps[1].status == StepStatus.SKIPPED.value
        assert result.requires_human_review is True

    def test_execute_plan_with_failed_step(self, mock_event_bus, mock_audit):
        reg = ToolRegistry()

        # Register a tool that will fail
        class FailingTool(InvestigationTool):
            def __init__(self):
                super().__init__(
                    name="failing_tool",
                    description="A tool that fails",
                    params=[ToolParam(name="query")],
                )

            def execute(self, params, context=None):
                raise RuntimeError("Tool error")

        reg.register(FailingTool())
        reg.register(DomainLookupTool())
        orch = Orchestrator(registry=reg)
        plan = InvestigationPlan(id="P1", target="example.com", objective="test")
        plan.add_step("failing_tool", {"query": "test"})
        plan.add_step("domain_lookup", {"domain": "example.com"})
        result = orch.execute_plan(plan, user="investigator1")
        assert result.steps_failed == 1
        assert plan.steps[0].status == StepStatus.FAILED.value
        assert result.requires_human_review is True

    def test_generate_report(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "test")
        result = orchestrator.execute_plan(plan, user="investigator1")
        report = orchestrator.generate_report(result)
        assert report["plan_id"] == plan.id
        assert report["target"] == "example.com"
        assert "claims" in report
        assert "summary" in report
        assert "requires_human_review" in report

    def test_report_contains_summary_text(self, orchestrator):
        plan = orchestrator.plan_investigation("example.com", "Investigate fraud")
        result = orchestrator.execute_plan(plan, user="investigator1")
        report = orchestrator.generate_report(result)
        assert "GFIN Investigation Report" in report["summary"]
        assert "example.com" in report["summary"]

    def test_registry_accessible(self, orchestrator):
        assert isinstance(orchestrator.registry, ToolRegistry)
        assert orchestrator.registry.tool_count == 15


# ─── Integration Tests ───


class TestIntegrationInvestigation:
    def test_full_investigation_pipeline(self, mock_event_bus, mock_audit):
        """Full pipeline: plan → execute → synthesize → report."""
        reg = create_default_registry(audit_logger=mock_audit)
        orch = Orchestrator(registry=reg, event_bus=mock_event_bus, audit_logger=mock_audit)

        plan = orch.plan_investigation("fraudster.com", "Investigate domain for fraud")
        result = orch.execute_plan(plan, user="investigator1")
        report = orch.generate_report(result)

        assert result.steps_completed > 0
        assert len(result.evidence) > 0
        assert len(result.claims) > 0
        assert report["target"] == "fraudster.com"
        assert report["steps_completed"] > 0
        mock_audit.log.assert_called()

    def test_full_investigation_with_role_escalation(self, mock_event_bus, mock_audit):
        """Supervisor can use all tools including create_alert and request_information."""
        reg = create_default_registry()
        orch = Orchestrator(registry=reg, event_bus=mock_event_bus)

        plan = InvestigationPlan(id="P1", target="example.com", objective="Full investigation")
        plan.add_step("domain_lookup", {"domain": "example.com"})
        plan.add_step(
            "create_alert",
            {"target_type": "domain", "target_id": "example.com", "priority": "HIGH"},
        )
        plan.add_step(
            "request_information", {"target_jurisdiction": "EU", "entity_id": "example.com"}
        )

        result = orch.execute_plan(plan, user="supervisor1", user_role=UserRole.SUPERVISOR.value)

        assert result.steps_completed == 3
        assert result.steps_failed == 0

    def test_audit_trail_complete(self, mock_audit):
        """Every tool call is logged in the audit trail."""
        reg = create_default_registry(audit_logger=mock_audit)
        orch = Orchestrator(registry=reg)
        plan = orch.plan_investigation("example.com", "test")
        orch.execute_plan(plan, user="investigator1")

        # Each step generates an audit log entry
        assert reg.get_call_log()
        assert mock_audit.log.call_count >= plan.completed_steps
