import logging

import pytest

from common.model_gateway import (
    BaseModelGateway,
    ModelRequest,
    TaskType,
)


@pytest.mark.asyncio
async def test_every_model_request_has_correlation_id(mock_gateway):
    """Test every ModelRequest gets assigned a correlation_id if not explicitly provided."""
    # Explicit correlation_id
    req_explicit = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt="Test explicit correlation ID",
        correlation_id="corr-explicit-123",
    )
    res_explicit = await mock_gateway.classify(req_explicit)
    assert res_explicit.correlation_id == "corr-explicit-123"

    # Implicit correlation_id
    req_implicit = ModelRequest(
        task_type=TaskType.EXTRACTION,
        prompt="Test implicit correlation ID",
        correlation_id=None,
    )
    res_implicit = await mock_gateway.extract(req_implicit)
    assert res_implicit.correlation_id is not None
    assert len(res_implicit.correlation_id) > 0


@pytest.mark.asyncio
async def test_model_response_includes_required_audit_fields(mock_gateway):
    """Test ModelResponse includes provider, model, tokens_used, latency_ms, and timestamp."""
    request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt="Audit response fields test",
    )

    response = await mock_gateway.generate(request)

    assert isinstance(response.provider, str)
    assert len(response.provider) > 0
    assert isinstance(response.model, str)
    assert len(response.model) > 0
    assert isinstance(response.tokens_used, int)
    assert response.tokens_used >= 0
    assert isinstance(response.latency_ms, int | float)
    assert response.latency_ms >= 0.0
    assert response.timestamp is not None


@pytest.mark.asyncio
async def test_gateway_tracks_total_requests_errors_and_tokens(mock_gateway):
    """Test gateway tracks total_requests, total_errors, total_tokens."""
    initial_requests = mock_gateway.total_requests
    initial_errors = mock_gateway.total_errors
    initial_tokens = mock_gateway.total_tokens

    # Successful request
    req1 = ModelRequest(task_type=TaskType.CLASSIFICATION, prompt="Valid request 1")
    res1 = await mock_gateway.generate(req1)

    assert mock_gateway.total_requests == initial_requests + 1
    assert mock_gateway.total_tokens == initial_tokens + res1.tokens_used

    # Failing empty prompt request
    req_fail = ModelRequest(task_type=TaskType.CLASSIFICATION, prompt="")
    await mock_gateway.generate(req_fail)

    assert mock_gateway.total_requests == initial_requests + 2
    assert mock_gateway.total_errors == initial_errors + 1


@pytest.mark.asyncio
async def test_error_responses_include_error_type_and_correlation_id():
    """Test error responses include error message and preserve request correlation_id."""
    class ErrorGateway(BaseModelGateway):
        async def _call_provider(self, provider, request, operation):
            raise TimeoutError("Provider gateway timeout connection failed")

    gateway = ErrorGateway()
    corr_id = "error-tracking-corr-99"

    request = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="Request triggering failure",
        correlation_id=corr_id,
    )

    response = await gateway.generate(request)

    assert response.error is not None
    assert "Provider gateway timeout" in response.error
    assert response.correlation_id == corr_id


@pytest.mark.asyncio
async def test_all_ai_operations_are_logged(mock_gateway, caplog):
    """Test all AI operations are logged (verify log capture)."""
    caplog.set_level(logging.INFO, logger="common.model_gateway")

    corr_id = "log-verification-001"
    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt="Log capture test prompt",
        correlation_id=corr_id,
    )

    await mock_gateway.classify(request)

    assert "Calling gateway operation=classify" in caplog.text
    assert corr_id in caplog.text
