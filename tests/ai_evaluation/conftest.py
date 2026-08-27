import sys
import uuid
from typing import Any

# Set up python path for packages and current directory
sys.path.insert(0, ".")
sys.path.insert(0, "packages")

import pytest

from common.model_gateway import (
    BaseModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    TaskType,
)


class MockGateway(BaseModelGateway):
    """Mock gateway implementation for AI evaluation testing."""

    def __init__(
        self,
        primary_provider: ModelProvider = ModelProvider.OPENAI,
        fallback_provider: ModelProvider | None = ModelProvider.LOCAL,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            primary_provider=primary_provider,
            fallback_provider=fallback_provider,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        self.request_history: list[ModelRequest] = []
        self.predefined_responses: dict[str, ModelResponse] = {}
        self.fail_on_primary: bool = False
        self.fail_on_all: bool = False
        self.empty_content_on_primary: bool = False

    async def _call_provider(
        self,
        provider_or_req: Any,
        req_or_op: Any = None,
        op: str = "generate",
    ) -> ModelResponse:
        if isinstance(provider_or_req, ModelRequest):
            request: ModelRequest = provider_or_req
            provider: ModelProvider = self._primary
            operation: str = str(req_or_op) if req_or_op else op
        else:
            provider = provider_or_req
            request = req_or_op
            operation = op

        self.request_history.append(request)

        if self.fail_on_all:
            raise RuntimeError("Provider service failed")

        if self.fail_on_primary and provider == self._primary:
            raise RuntimeError("Primary provider failed")

        if self.empty_content_on_primary and provider == self._primary:
            raise RuntimeError("Primary provider returned empty content")

        corr_id = request.correlation_id or str(uuid.uuid4())

        # Check for predefined response matching prompt or task_type
        if request.prompt in self.predefined_responses:
            resp = self.predefined_responses[request.prompt]
            resp.correlation_id = corr_id
            return resp

        # Default mocked response
        task_str = (
            request.task_type.value
            if isinstance(request.task_type, TaskType)
            else str(request.task_type)
        )
        provider_str = (
            provider.value if isinstance(provider, ModelProvider) else str(provider)
        )

        return ModelResponse(
            content="Mock response",
            provider=provider_str,
            model="mock-model",
            task_type=task_str,
            tokens_used=10,
            latency_ms=5.0,
            correlation_id=corr_id,
        )


@pytest.fixture
def mock_gateway() -> MockGateway:
    """Fixture returning a standard mock gateway."""
    return MockGateway()


@pytest.fixture
def routing_gateway() -> MockGateway:
    """Fixture returning a mock gateway configured for routing tests."""
    return MockGateway(
        primary_provider=ModelProvider.OPENAI,
        fallback_provider=ModelProvider.LOCAL,
    )
