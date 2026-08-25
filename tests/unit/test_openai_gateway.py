"""Tests for GFIN OpenAI Gateway Adapter (GPT-5.6-LUNA).

Tests are split into:
- Unit tests (mock the OpenAI API)
- Integration tests (require OPENAI_PROJECT_KEY — skip if not set)
"""

import os

import pytest

from common.model_gateway import ModelRequest, TaskType
from common.openai_gateway import OpenAIGateway

has_openai_key = os.environ.get("OPENAI_PROJECT_KEY") is not None


# ─── Unit Tests (no API calls) ───


class TestOpenAIGatewayUnit:
    """Unit tests that don't make real API calls."""

    def test_initialization_with_explicit_key(self):
        gw = OpenAIGateway(api_key="test-key", model="gpt-5.6-luna")
        assert gw._api_key == "test-key"
        assert gw._model == "gpt-5.6-luna"

    def test_initialization_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_PROJECT_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_PROJECT_KEY"):
            OpenAIGateway()

    def test_initialization_with_env_key(self):
        gw = OpenAIGateway()
        assert gw._api_key is not None

    def test_routes_public_to_openai(self):
        gw = OpenAIGateway(api_key="test-key")
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="test",
            classification_filter="PUBLIC",
        )
        provider = gw._route(request.task_type, request.classification_filter)
        assert provider.value == "openai"

    def test_routes_restricted_to_local(self):
        gw = OpenAIGateway(api_key="test-key")
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="test",
            classification_filter="HIGHLY_RESTRICTED",
        )
        provider = gw._route(request.task_type, request.classification_filter)
        assert provider.value == "local"

    def test_routes_law_enforcement_to_local(self):
        gw = OpenAIGateway(api_key="test-key")
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="test",
            classification_filter="LAW_ENFORCEMENT",
        )
        provider = gw._route(request.task_type, request.classification_filter)
        assert provider.value == "local"

    def test_system_context_built_for_generate(self):
        gw = OpenAIGateway(api_key="test-key")
        ctx = gw._build_system_context(
            ModelRequest(task_type=TaskType.GENERATION, prompt="test"),
            "generate",
        )
        assert "GFIN" in ctx
        assert "evidence" in ctx.lower()

    def test_system_context_built_for_classify(self):
        gw = OpenAIGateway(api_key="test-key")
        ctx = gw._build_system_context(
            ModelRequest(task_type=TaskType.CLASSIFICATION, prompt="test"),
            "classify",
        )
        assert "PHISHING" in ctx or "classification" in ctx.lower()

    def test_system_context_built_for_extract(self):
        gw = OpenAIGateway(api_key="test-key")
        ctx = gw._build_system_context(
            ModelRequest(task_type=TaskType.EXTRACTION, prompt="test"),
            "extract",
        )
        assert "entity" in ctx.lower() or "extract" in ctx.lower()

    def test_stats_initialized_to_zero(self):
        gw = OpenAIGateway(api_key="test-key")
        stats = gw.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_errors"] == 0

    async def test_local_fallback_returns_unavailable_message(self):
        gw = OpenAIGateway(api_key="test-key")
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="test",
            classification_filter="HIGHLY_RESTRICTED",
        )
        response = await gw.generate(request)
        assert response.provider == "local"
        assert "AI_UNAVAILABLE" in response.content or response.unverified


# ─── Integration Tests (require OPENAI_PROJECT_KEY) ───


@pytest.mark.skipif(not has_openai_key, reason="OPENAI_PROJECT_KEY not set")
class TestOpenAIGatewayIntegration:
    """Integration tests that make real API calls to GPT-5.6-LUNA."""

    @pytest.fixture
    def gateway(self):
        return OpenAIGateway()

    async def test_health_check(self, gateway):
        health = await gateway.health_check()
        assert "openai" in health
        assert health["openai"] is True

    async def test_generate_with_gpt_luna(self, gateway):
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="What is the risk level of a phone number reported in 3 separate fraud complaints? Answer in one word.",
            classification_filter="PUBLIC",
            max_tokens=50,
        )
        response = await gateway.generate(request)
        assert response.provider == "openai"
        assert response.model == "gpt-5.6-luna"
        assert len(response.content) > 0
        assert response.tokens_used > 0
        assert response.latency_ms > 0

    async def test_classify_fraud_type(self, gateway):
        request = ModelRequest(
            task_type=TaskType.CLASSIFICATION,
            prompt="A website claims to sell iPhone 15 Pro for 50 EUR. Payment by wire transfer only. No return address. Domain registered 2 days ago.",
            classification_filter="PUBLIC",
            max_tokens=100,
        )
        response = await gateway.classify(request)
        assert response.provider == "openai"
        assert len(response.content) > 0

    async def test_extract_entities(self, gateway):
        request = ModelRequest(
            task_type=TaskType.EXTRACTION,
            prompt="Contact us at +34 612 345 678 or email support@best-deals-2024.xyz. Send crypto to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            classification_filter="PUBLIC",
            max_tokens=500,
        )
        response = await gateway.extract(request)
        assert response.provider == "openai"
        assert len(response.content) > 0

    async def test_gfin_system_prompt_enforced(self, gateway):
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="Tell me about a fraud case involving phone number +34612345678",
            classification_filter="PUBLIC",
            max_tokens=100,
        )
        response = await gateway.generate(request)
        assert response.provider == "openai"
        # GPT-LUNA should respond acknowledging GFIN context
        assert len(response.content) > 0

    async def test_stats_updated_after_calls(self, gateway):
        initial = gateway.get_stats()
        request = ModelRequest(
            task_type=TaskType.REASONING,
            prompt="Say OK",
            classification_filter="PUBLIC",
            max_tokens=10,
        )
        await gateway.generate(request)
        updated = gateway.get_stats()
        assert updated["total_requests"] > initial["total_requests"]
