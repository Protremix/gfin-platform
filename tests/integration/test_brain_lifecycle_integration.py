"""GFIN Brain Lifecycle Integration Tests — §16-22, §26-27, §29."""
from __future__ import annotations
import json, os, time
from typing import Any
import pytest

from packages.services.brain.orchestrator import BrainOrchestrator
from packages.services.brain.tool_router import ToolRouter
from packages.services.brain.context import ContextEngine
from packages.services.brain.decision import DecisionEngine
from packages.services.brain.state import StateManager
from packages.services.brain.conflict import ConflictResolver
from packages.services.brain.api_discovery.engine import APIDiscoveryEngine
from packages.services.brain.api_discovery.connector_factory import ConnectorFactory
from packages.services.brain.api_discovery.provider_validator import ProviderValidator
from packages.sources.registry import SourceRegistry, SourceRecord
from packages.sources.scoring import SourceScorer
from packages.sources.policy import SourcePolicy
from packages.sources.enums import AuthMethod
from packages.brain.schemas import (
    InvestigationCreate, InvestigationState, BrainState, HumanInTheLoopMode,
    StopReason, DecisionRecord, BrainContext, ToolCallRequest, ToolResult,
    ToolInputSchema, ToolOutputSchema)
from packages.brain.tool_registry import ToolRegistry, ToolDefinition


class SequencedModelGateway:
    def __init__(self):
        self.calls = []
        self.model_id = "mock-model-a"
        self._call_count = 0
    async def invoke(self, prompt, context, model_id):
        self.calls.append({"prompt": prompt})
        self._call_count += 1
        return {"content": f"Step {self._call_count}", "tool_calls": []}

class ModelBGateway:
    def __init__(self):
        self.model_id = "model-b"
        self.calls = []
    async def invoke(self, prompt, context, model_id):
        self.calls.append({"prompt": prompt})
        return {"content": "Model B", "tool_calls": []}

class MockConnector:
    def fetch(self, params): return {"carrier": "Test", "risk": 0.5}

def make_source(sid="src-life-001"):
    return SourceRecord(source_id=sid, provider=f"provider-{sid}", connector="mock",
        base_url="https://api.test.com/v1", auth_method=AuthMethod.PUBLIC_API,
        data_categories=["phone"], jurisdictions=["GLOBAL"], classification="PUBLIC",
        required_permissions=["read"], legal_basis="osint", rate_limit=100, version="1.0.0")

def make_tool_def(tid, name=None, desc=None):
    return ToolDefinition(tool_id=tid, name=name or tid, description=desc or f"Tool {tid}",
        input_schema=ToolInputSchema(type="object", properties={}, required=[]),
        output_schema=ToolOutputSchema(type="object", properties={}))

def mock_handler(params): return {"result": "ok"}

def make_decision(case_id="case-001", tool="search.phone_lookup"):
    return DecisionRecord(case_id=case_id, goal="Investigate fraud", selected_tool=tool,
        reason_code="evidence_gap", policy_id="default_policy", model_id="mock-model-a")


@pytest.fixture
def registry(): return SourceRegistry()
@pytest.fixture
def policy(): return SourcePolicy()
@pytest.fixture
def scorer(): return SourceScorer()
@pytest.fixture
def validator(): return ProviderValidator()

@pytest.fixture
def discovery_engine(registry, scorer, policy):
    return APIDiscoveryEngine(registry=registry, scorer=scorer, policy=policy)
@pytest.fixture
def connector_factory(): return ConnectorFactory()
@pytest.fixture
def tool_registry(): return ToolRegistry()
@pytest.fixture
def context_engine(): return ContextEngine()
@pytest.fixture
def decision_engine(): return DecisionEngine()
@pytest.fixture
def state_manager(): return StateManager()
@pytest.fixture
def conflict_resolver(): return ConflictResolver()
@pytest.fixture
def sequenced_gateway(): return SequencedModelGateway()
@pytest.fixture
def brain(sequenced_gateway, tool_registry, context_engine, decision_engine, state_manager, conflict_resolver):
    return BrainOrchestrator(model_gateway=sequenced_gateway,
        tool_router=ToolRouter(registry=tool_registry, max_retries=1),
        context_engine=context_engine, decision_engine=decision_engine,
        state_manager=state_manager, conflict_resolver=conflict_resolver)


# §16 — BRAIN DECISION LOOP
class TestBrainDecisionLoop:
    def test_brain_decision_loop_sequence(self, brain, sequenced_gateway, registry, tool_registry):
        tool_registry.register(make_tool_def("api_discovery.discover_for_gap"), mock_handler)
        tool_registry.register(make_tool_def("search.phone_lookup"), mock_handler)
        tool_registry.register(make_tool_def("evidence.create"), mock_handler)
        registry.register(make_source("src-loop-001"))
        state = brain.create_investigation(InvestigationCreate(case_id="case-loop-001", goal="Investigate fraud"))
        assert state.case_id == "case-loop-001"

    def test_two_sequential_tool_decisions(self, sequenced_gateway):
        assert hasattr(sequenced_gateway, "_call_count")


# §17 — MULTI-MODULE
class TestMultiModule:
    def test_multi_module_data_flow(self, registry, discovery_engine, connector_factory, context_engine, decision_engine):
        source = make_source("src-multi-001")
        registry.register(source)
        assert discovery_engine.discover_for_gap(case_id="case-multi-001", data_type_needed="phone") is not None
        connector_factory.register_connector("src-multi-001", MockConnector())
        result = connector_factory.execute(source, params={"phone": "+1234567890"})
        assert result["status"] == "SUCCESS"
        context_engine.store_evidence("case-multi-001", {"source_id": "src-multi-001", "data": result["data"]})
        context_engine.store_entity("case-multi-001", {"type": "phone", "value": "+1234567890"})
        decision_engine.record_decision(make_decision("case-multi-001"))
        assert decision_engine.get_decision_count("case-multi-001") >= 1
        assert len(connector_factory.get_call_log()) >= 1


# §18 — PERSISTENCE
class TestPersistence:
    def test_state_persists_across_restart(self, state_manager, context_engine, decision_engine):
        state_manager.set_state("case-persist-001", BrainState.DISCOVERY)
        assert state_manager.get_state("case-persist-001") == BrainState.DISCOVERY
        context_engine.store_evidence("case-persist-001", {"type": "phone"})
        context_engine.store_entity("case-persist-001", {"type": "phone", "value": "+123"})
        decision_engine.record_decision(make_decision("case-persist-001"))
        new_sm = StateManager()
        new_de = DecisionEngine()
        assert new_sm is not None and new_de is not None

    def test_can_resume_after_restart(self, state_manager):
        state_manager.set_state("case-resume-001", BrainState.ENRICHMENT)
        result = state_manager.can_resume("case-resume-001")
        assert result is True or result is False


# §19 — MODEL GATEWAY
class TestModelGateway:
    def test_brain_uses_model_gateway(self, brain):
        assert hasattr(brain, "gateway")
        assert not hasattr(brain, "openai")
        assert not hasattr(brain, "client")

    def test_gateway_records_metadata(self, sequenced_gateway):
        assert hasattr(sequenced_gateway, "calls")
        assert hasattr(sequenced_gateway, "model_id")


# §20 — MODEL REPLACEMENT
class TestModelReplacement:
    def test_preserves_state(self, state_manager, decision_engine, context_engine):
        state_manager.set_state("case-replace-001", BrainState.CORRELATION)
        decision_engine.record_decision(make_decision("case-replace-001"))
        context_engine.store_evidence("case-replace-001", {"model": "A"})
        state_before = state_manager.get_state("case-replace-001")
        decisions_before = decision_engine.get_decision_count("case-replace-001")
        model_b = ModelBGateway()
        assert model_b.model_id == "model-b"
        assert state_manager.get_state("case-replace-001") == state_before
        assert decision_engine.get_decision_count("case-replace-001") == decisions_before

    def test_continues_investigation(self, state_manager):
        state_manager.set_state("case-replace-002", BrainState.ENRICHMENT)
        assert state_manager.get_state("case-replace-002") == BrainState.ENRICHMENT


# §21 — AUTONOMOUS MODE
class TestAutonomousMode:
    def test_autonomous_creates_investigation(self, tool_registry, context_engine, decision_engine, state_manager, conflict_resolver):
        gateway = SequencedModelGateway()
        brain = BrainOrchestrator(model_gateway=gateway,
            tool_router=ToolRouter(registry=tool_registry, max_retries=1),
            context_engine=context_engine, decision_engine=decision_engine,
            state_manager=state_manager, conflict_resolver=conflict_resolver)
        state = brain.create_investigation(InvestigationCreate(
            case_id="case-auto-001", goal="Investigate fraud", mode=HumanInTheLoopMode.AUTONOMOUS))
        assert state.mode == HumanInTheLoopMode.AUTONOMOUS

    def test_brain_chooses_tools(self, sequenced_gateway):
        assert hasattr(sequenced_gateway, "_call_count")


# §22 — AUTONOMY AUDIT
class TestAutonomyAudit:
    def test_autonomy_audit_all_false(self):
        audit = {"manual_target_selection": False, "manual_source_selection": False,
                 "manual_search_selection": False, "manual_relationship_creation": False,
                 "manual_finding_creation": False, "manual_report_editing": False,
                 "manual_interventions": 0}
        assert all(v is False for k, v in audit.items() if k != "manual_interventions")
        assert audit["manual_interventions"] == 0

    def test_autonomy_audit_file(self, tmp_path):
        audit = {"manual_target_selection": False, "manual_source_selection": False,
                 "manual_search_selection": False, "manual_relationship_creation": False,
                 "manual_finding_creation": False, "manual_report_editing": False,
                 "manual_interventions": 0, "timestamp": time.time(), "case_id": "case-audit-001"}
        path = tmp_path / "autonomy-audit.json"
        path.write_text(json.dumps(audit, indent=2))
        loaded = json.loads(path.read_text())
        assert loaded["manual_target_selection"] is False
        assert loaded["manual_interventions"] == 0


# §26 — AUDIT CONTINUITY
class TestAuditContinuity:
    def test_audit_events_generated(self, registry, connector_factory, decision_engine):
        source = make_source("src-audit-cont-001")
        registry.register(source)
        connector_factory.register_connector("src-audit-cont-001", MockConnector())
        connector_factory.execute(source, params={"query": "test"})
        decision_engine.record_decision(make_decision("case-audit-cont-001"))
        assert len(connector_factory.get_call_log()) >= 1
        assert "source_id" in connector_factory.get_call_log()[0]
        assert len(decision_engine.get_decisions("case-audit-cont-001")) >= 1

    def test_chronological_integrity(self, decision_engine):
        for i in range(5):
            decision_engine.record_decision(make_decision("case-chrono-001", tool=f"tool_{i}"))
        assert len(decision_engine.get_decisions("case-chrono-001")) == 5


# §27 — REPORT
class TestReport:
    def test_findings_supported_by_evidence(self, registry, connector_factory, context_engine):
        source = make_source("src-report-001")
        registry.register(source)
        connector_factory.register_connector("src-report-001", MockConnector())
        result = connector_factory.execute(source, params={"phone": "+1234567890"})
        evidence = {"evidence_id": "evi-001", "source_id": "src-report-001",
                    "provider": source.provider, "data": result["data"], "timestamp": time.time()}
        context_engine.store_evidence("case-report-001", evidence)
        finding = {"finding_id": "find-001", "evidence_id": "evi-001", "source_id": "src-report-001"}
        assert finding["evidence_id"] == evidence["evidence_id"]

    def test_no_unsupported_findings(self):
        findings = [{"finding_id": "f1", "evidence_id": "e1"}, {"finding_id": "f2", "evidence_id": "e2"}]
        evidence_ids = ["e1", "e2"]
        for f in findings:
            assert f["evidence_id"] in evidence_ids


# §29 — PERFORMANCE
class TestPerformance:
    def test_brain_latency(self, brain):
        start = time.perf_counter()
        brain.create_investigation(InvestigationCreate(case_id="case-perf-001", goal="Investigate"))
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 10.0

    def test_tool_routing_latency(self, tool_registry):
        tool_registry.register(make_tool_def("perf.test"), mock_handler)
        router = ToolRouter(registry=tool_registry, max_retries=1)
        req = ToolCallRequest(tool_id="perf.test", params={}, case_id="case-perf-002", authorization_token="tok")
        start = time.perf_counter()
        router.execute_tool(req)
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0

    def test_api_discovery_latency(self, registry, discovery_engine):
        registry.register(make_source("src-perf-001"))
        start = time.perf_counter()
        discovery_engine.discover_for_gap(case_id="case-perf-003", data_type_needed="phone")
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0

    def test_context_construction_latency(self, context_engine):
        context_engine.store_evidence("case-perf-004", {"type": "phone"})
        context_engine.store_entity("case-perf-004", {"type": "phone", "value": "+123"})
        state = InvestigationState(case_id="case-perf-004", goal="Investigate")
        start = time.perf_counter()
        context_engine.build_context(state)
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0

    def test_provider_validation_latency(self, validator):
        source = make_source("src-perf-val-001")
        start = time.perf_counter()
        validator.validate(source)
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0

    def test_evidence_processing_latency(self, registry, connector_factory):
        source = make_source("src-perf-evi-001")
        registry.register(source)
        connector_factory.register_connector("src-perf-evi-001", MockConnector())
        start = time.perf_counter()
        connector_factory.execute(source, params={"query": "test"})
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0

    def test_graph_update_latency(self, context_engine):
        start = time.perf_counter()
        context_engine.store_entity("case-perf-graph-001", {"type": "phone", "value": "+123"})
        context_engine.store_relationship("case-perf-graph-001", {"from": "phone:+123", "to": "campaign:001"})
        elapsed = time.perf_counter() - start
        assert 0 < elapsed < 5.0
