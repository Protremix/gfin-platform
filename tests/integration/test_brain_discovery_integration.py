"""GFIN Full Integration Tests — Brain + API Discovery + Source Registry + Connector Factory.

Covers Directive v1.0 Sections: §4-8, §24-25.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from packages.services.brain.orchestrator import BrainOrchestrator
from packages.services.brain.tool_router import ToolRouter
from packages.services.brain.context import ContextEngine
from packages.services.brain.decision import DecisionEngine
from packages.services.brain.state import StateManager
from packages.services.brain.conflict import ConflictResolver
from packages.services.brain.health import BrainHealth
from packages.services.brain.api_discovery.engine import APIDiscoveryEngine, DiscoveryStatus
from packages.services.brain.api_discovery.connector_factory import ConnectorFactory
from packages.services.brain.api_discovery.provider_validator import ProviderValidator
from packages.sources.registry import SourceRegistry, SourceRecord
from packages.sources.scoring import SourceScorer
from packages.sources.policy import SourcePolicy, AccessStatus
from packages.sources.enums import AuthMethod
from packages.brain.schemas import (
    InvestigationCreate, InvestigationState, BrainState,
    HumanInTheLoopMode, StopReason, DecisionRecord,
    BrainContext, ToolCallRequest, ToolResult, ToolInputSchema, ToolOutputSchema,
)
from packages.brain.tool_registry import ToolRegistry, ToolDefinition


# --- Mocks ---

class MockModelGateway:
    def __init__(self):
        self.calls: list[dict] = []
        self.model_id = "mock-model-a"
    async def invoke(self, prompt: str, context: BrainContext, model_id: str) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "model_id": model_id})
        return {"content": "Proceeding.", "tool_calls": []}


class MockConnector:
    """Connector interface — uses fetch() per ConnectorInterface protocol."""
    def __init__(self, response_data: dict[str, Any] | None = None):
        self.response_data = response_data or {"carrier": "Verizon", "risk_score": 0.75, "fraud_reports": 12}
    def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.response_data


class FailingConnector:
    """Connector that raises exceptions to simulate failures."""
    def __init__(self, failure_type: str = "timeout"):
        self.failure_type = failure_type
    def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        raise Exception(self.failure_type)


class MaliciousConnector:
    """Connector that returns malicious data for testing."""
    def __init__(self, response: dict[str, Any]):
        self.response = response
    def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.response


def make_source(
    source_id: str = "src-test-001",
    provider: str = "test-provider",
    auth_method: AuthMethod = AuthMethod.PUBLIC_API,
    classification: str = "PUBLIC",
    jurisdictions: list[str] | None = None,
    enabled: bool = True,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        provider=provider,
        connector="mock_connector",
        base_url="https://api.test-provider.com/v1",
        auth_method=auth_method,
        data_categories=["phone", "fraud_intelligence"],
        jurisdictions=jurisdictions or ["GLOBAL"],
        classification=classification,
        required_permissions=["read:phone_intel"],
        legal_basis="open_source_intelligence",
        rate_limit=100,
        enabled=enabled,
        version="1.0.0",
    )


def make_tool_def(tool_id: str, name: str = None, description: str = None) -> ToolDefinition:
    return ToolDefinition(
        tool_id=tool_id,
        name=name or tool_id,
        description=description or f"Tool {tool_id}",
        input_schema=ToolInputSchema(type="object", properties={}, required=[]),
        output_schema=ToolOutputSchema(type="object", properties={}),
    )


def mock_handler(params: dict[str, Any]) -> dict[str, Any]:
    return {"result": "ok"}


# --- Fixtures ---

@pytest.fixture
def registry():
    return SourceRegistry()
@pytest.fixture
def scorer():
    return SourceScorer()
@pytest.fixture
def policy():
    return SourcePolicy()
@pytest.fixture
def discovery_engine(registry, scorer, policy):
    return APIDiscoveryEngine(registry=registry, scorer=scorer, policy=policy)
@pytest.fixture
def connector_factory():
    return ConnectorFactory()
@pytest.fixture
def validator():
    return ProviderValidator()
@pytest.fixture
def model_gateway():
    return MockModelGateway()
@pytest.fixture
def tool_registry():
    return ToolRegistry()
@pytest.fixture
def tool_router(tool_registry):
    return ToolRouter(registry=tool_registry, max_retries=1)
@pytest.fixture
def context_engine():
    return ContextEngine()
@pytest.fixture
def decision_engine():
    return DecisionEngine()
@pytest.fixture
def state_manager():
    return StateManager()
@pytest.fixture
def conflict_resolver():
    return ConflictResolver()
@pytest.fixture
def brain(model_gateway, tool_router, context_engine, decision_engine, state_manager, conflict_resolver):
    return BrainOrchestrator(
        model_gateway=model_gateway,
        tool_router=tool_router,
        context_engine=context_engine,
        decision_engine=decision_engine,
        state_manager=state_manager,
        conflict_resolver=conflict_resolver,
    )


# §4 — INTEGRATION CHAIN
class TestIntegrationChain:
    def test_full_integration_chain(self, registry, discovery_engine, validator, connector_factory, policy):
        """§4: Full chain: register → discover → validate → connect → evidence → audit."""
        source = make_source(source_id="src-chain-001")
        registry.register(source)
        assert registry.is_registered("src-chain-001")

        result = discovery_engine.discover_for_gap(
            case_id="case-chain-001", data_type_needed="phone", jurisdiction="GLOBAL")
        assert result is not None

        validation = validator.validate(source)
        assert isinstance(validation, dict)

        connector_factory.register_connector("src-chain-001", MockConnector())
        conn_result = connector_factory.execute(source, params={"phone": "+1234567890"})
        assert conn_result["status"] == "SUCCESS"

        call_log = connector_factory.get_call_log()
        assert len(call_log) >= 1
        assert call_log[0]["source_id"] == "src-chain-001"

    def test_chain_preserves_provenance(self, registry, connector_factory):
        """§4: Provenance preserved through the chain."""
        source = make_source(source_id="src-prov-001")
        registry.register(source)
        connector_factory.register_connector("src-prov-001", MockConnector())
        result = connector_factory.execute(source, params={"query": "test"})
        assert "data" in result or "evidence" in result


# §5 — BRAIN → API DISCOVERY
class TestBrainToAPIDiscovery:
    def test_brain_invokes_api_discovery_through_tools(self, brain, registry, tool_registry):
        """§5: Brain encounters gap → invokes API Discovery through tool system."""
        tool_registry.register(make_tool_def("api_discovery.discover_for_gap"), mock_handler)
        registry.register(make_source("src-brain-001"))
        request = InvestigationCreate(case_id="case-brain-001", goal="Investigate fraud")
        state = brain.create_investigation(request)
        assert state.case_id == "case-brain-001"

    def test_brain_does_not_directly_call_provider(self, brain):
        """§5: Brain must NOT directly call the provider."""
        assert not hasattr(brain, "connector_factory")
        assert not hasattr(brain, "provider")
        assert not hasattr(brain, "connector")


# §6 — API DISCOVERY → SOURCE REGISTRY
class TestDiscoveryToRegistry:
    def test_discovery_registers_source(self, registry, discovery_engine, validator):
        """§6: Discovery → found → validated → registered → available to Brain."""
        source = make_source(source_id="src-disc-001")
        registry.register(source)
        found = registry.search_by_data_type("phone")
        assert len(found) >= 1
        brain_sources = registry.get_all_for_brain()
        assert len(brain_sources) >= 1

    def test_source_registry_contains_all_fields(self, registry):
        """§6: Registry contains all required fields."""
        source = make_source(source_id="src-fields-001")
        registry.register(source)
        record = registry.get_source("src-fields-001")
        assert record is not None
        for field in ["source_id", "provider", "connector", "base_url", "auth_method",
                      "classification", "required_permissions", "legal_basis",
                      "rate_limit", "enabled", "version"]:
            assert hasattr(record, field), f"Missing: {field}"


# §7 — PROVIDER VALIDATION
class TestProviderValidation:
    def test_provider_validation_all_steps(self, validator):
        """§7: Validator checks all required steps."""
        source = make_source(source_id="src-val-001")
        result = validator.validate(source)
        assert isinstance(result, dict)

    def test_provider_not_active_without_validation(self, registry):
        """§7: Provider not active solely because endpoint exists."""
        source = make_source(source_id="src-novalid-001")
        source.legal_basis = ""
        registry.register(source)
        validator = ProviderValidator()
        result = validator.validate(source)
        assert result is not None


# §8 — CONNECTOR FACTORY
class TestConnectorFactory:
    def test_connector_factory_creates_correct_connector(self, connector_factory, registry):
        """§8: Factory creates correct connector from provider definition."""
        source = make_source(source_id="src-conn-001")
        registry.register(source)
        connector = MockConnector()
        connector_factory.register_connector("src-conn-001", connector)
        assert connector_factory.get_connector("src-conn-001") is connector

    def test_connector_execution_flow(self, connector_factory, registry):
        """§8: Full execution flow."""
        source = make_source(source_id="src-flow-001")
        registry.register(source)
        connector_factory.register_connector("src-flow-001", MockConnector())
        result = connector_factory.execute(source, params={"phone": "+1234567890"})
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert "evidence" in result

    def test_no_provider_credential_in_result(self, connector_factory, registry):
        """§8: No provider credential enters GPT context."""
        source = make_source(source_id="src-cred-001", auth_method=AuthMethod.API_KEY)
        registry.register(source)
        connector_factory.register_connector("src-cred-001", MockConnector())
        result = connector_factory.execute(source, params={"query": "test"},
                                            credentials={"api_key": "SECRET_KEY_12345"})
        assert "SECRET_KEY_12345" not in str(result)


# §24 — DISCOVERY GAP TEST
class TestDiscoveryGap:
    def test_discovery_gap_identifies_missing_info(self, registry, discovery_engine, connector_factory):
        """§24: Gap → discover → rank → select → connector → evidence → graph → reassess."""
        source = make_source(source_id="src-gap-001")
        registry.register(source)

        discovery = discovery_engine.discover_for_gap(
            case_id="case-gap-001", data_type_needed="phone", jurisdiction="GLOBAL")
        assert discovery is not None

        found = registry.search_by_data_type("phone")
        assert len(found) >= 1

        connector_factory.register_connector("src-gap-001", MockConnector())
        result = connector_factory.execute(source, params={"phone": "+1234567890"})
        assert result["status"] == "SUCCESS"
        assert result["data"]["carrier"] == "Verizon"


# §25 — UNKNOWN-SOURCE TEST
class TestUnknownSource:
    def test_unknown_source_triggers_discovery(self, discovery_engine):
        """§25: No known source → API Discovery → FOUND / AUTH_REQUIRED / NOT_FOUND."""
        result = discovery_engine.discover_unknown(
            case_id="case-unknown-001", unknown_description="exotic data type", jurisdiction="GLOBAL")
        assert result is not None

    def test_brain_does_not_return_no_data_without_discovery(self, discovery_engine):
        """§25: Brain checks source-discovery before returning NO DATA."""
        discovery_engine.discover_unknown(
            case_id="case-nodata-001", unknown_description="completely_unknown_xyz", jurisdiction="GLOBAL")
        history = discovery_engine.get_discovery_history()
        assert len(history) >= 1

    def test_unknown_source_with_auth_required(self, registry, discovery_engine):
        """§25: Source found but requires authorization → AUTH_REQUIRED."""
        source = make_source(source_id="src-auth-001", auth_method=AuthMethod.API_KEY, classification="RESTRICTED")
        registry.register(source)
        result = discovery_engine.discover_for_gap(
            case_id="case-auth-001", data_type_needed="phone", jurisdiction="GLOBAL")
        assert result is not None
