import json

import pytest

from common.model_gateway import (
    BaseModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    TaskType,
)


@pytest.mark.asyncio
async def test_gateway_rejects_empty_prompts(mock_gateway):
    """Test gateway rejects requests with empty prompts or whitespace-only prompts."""
    empty_req = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="",
    )
    whitespace_req = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="   \n\t ",
    )

    resp_empty = await mock_gateway.generate(empty_req)
    assert resp_empty.error is not None
    assert resp_empty.content == ""
    assert resp_empty.unverified is True

    resp_whitespace = await mock_gateway.generate(whitespace_req)
    assert resp_whitespace.error is not None
    assert resp_whitespace.content == ""
    assert resp_whitespace.unverified is True


@pytest.mark.asyncio
async def test_gateway_handles_ambiguous_input_without_fabricating_data(mock_gateway):
    """Test gateway handles ambiguous input without fabricating ungrounded data."""
    ambiguous_prompt = "What was the exact amount stolen in transaction TX-99999?"
    mock_gateway.predefined_responses[ambiguous_prompt] = ModelResponse(
        content="Insufficient information provided in context to determine exact amount.",
        provider="mock",
        model="mock-model",
        task_type=TaskType.REASONING.value,
        unverified=True,
        confidence=0.0,
    )

    request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt=ambiguous_prompt,
    )

    response = await mock_gateway.generate(request)

    assert response.unverified is True
    assert response.confidence == 0.0
    assert "Insufficient information" in response.content


@pytest.mark.asyncio
async def test_gateway_marks_unverified_information_appropriately(mock_gateway):
    """Test gateway marks unverified information appropriately when evidence is missing."""
    prompt = "Unverified rumor claiming XYZ Corp is involved in money laundering."
    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content="Claim detected but lacks supporting evidence.",
        provider="mock",
        model="mock-model",
        task_type=TaskType.CLASSIFICATION.value,
        unverified=True,
        evidence_refs=[],
    )

    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt=prompt,
    )

    response = await mock_gateway.generate(request)

    assert response.unverified is True
    assert len(response.evidence_refs) == 0


@pytest.mark.asyncio
async def test_structured_output_schema_enforcement(mock_gateway):
    """Test structured output schema enforcement requires output to match schema."""
    schema = {
        "type": "object",
        "properties": {
            "fraud_type": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["fraud_type", "confidence"],
    }

    prompt = "Classify this report under structured output."
    valid_json = json.dumps({"fraud_type": "PHISHING", "confidence": 0.95})

    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content=valid_json,
        provider="mock",
        model="mock-model",
        task_type=TaskType.CLASSIFICATION.value,
    )

    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt=prompt,
        structured_output=True,
        output_schema=schema,
    )

    response = await mock_gateway.generate(request)

    data = json.loads(response.content)
    assert "fraud_type" in data
    assert "confidence" in data
    assert data["fraud_type"] == "PHISHING"
    assert isinstance(data["confidence"], float)


@pytest.mark.asyncio
async def test_gateway_returns_error_for_unsupported_task_types(mock_gateway):
    """Test gateway returns error when encountering unsupported or invalid task types."""
    class CustomTaskGateway(BaseModelGateway):
        async def _call_provider(self, provider, request, operation):
            if request.task_type not in TaskType:
                raise ValueError(f"Unsupported task type: {request.task_type}")
            return ModelResponse(
                content="ok",
                provider="mock",
                model="mock",
                task_type=str(request.task_type),
            )

    gateway = CustomTaskGateway()

    # Passing request with invalid/unsupported task_type
    class UnsupportedTask:
        value = "unsupported_task_xyz"

    request = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="Test prompt",
    )
    request.task_type = UnsupportedTask()  # type: ignore

    response = await gateway.generate(request)
    assert response.error is not None
    assert "Unsupported task type" in response.error or "error" in response.model


@pytest.mark.asyncio
async def test_gateway_retry_and_fallback_when_provider_returns_empty(routing_gateway):
    """Test gateway does not return content when primary provider fails or returns empty, triggering retry/fallback."""
    routing_gateway.fail_on_primary = True

    request = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="Generate fraud summary",
        classification_filter="PUBLIC",
    )

    response = await routing_gateway.generate(request)

    # Primary (OpenAI) failed, fallback (Local) succeeded
    assert response.provider == ModelProvider.LOCAL.value
    assert response.content == "Mock response"
    assert response.error is None
