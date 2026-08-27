import json

import pytest

from common.model_gateway import (
    BaseModelGateway,
    ModelRequest,
    ModelResponse,
    TaskType,
)


@pytest.mark.asyncio
async def test_classification_fraud_types_returns_expected_categories(mock_gateway):
    """Test classification of fraud types returns expected categories using predefined responses."""
    prompt = "User received an urgent email asking to click a link and enter bank password."
    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content="PHISHING",
        provider="mock",
        model="mock-model",
        task_type=TaskType.CLASSIFICATION.value,
        tokens_used=12,
        latency_ms=4.2,
    )

    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt=prompt,
    )

    response = await mock_gateway.classify(request)

    assert response.content in ["PHISHING", "IDENTITY_THEFT", "INVESTMENT_SCAM", "RANSOMWARE", "WIRE_FRAUD"]
    assert response.content == "PHISHING"
    assert response.task_type == TaskType.CLASSIFICATION.value


@pytest.mark.asyncio
async def test_entity_extraction_returns_correct_entities(mock_gateway):
    """Test entity extraction from text returns correct entities."""
    prompt = "Suspicious activity detected from IP 192.168.1.100 and email badactor@phish.com on domain mal-site.org"
    expected_entities = {
        "ip_addresses": ["192.168.1.100"],
        "emails": ["badactor@phish.com"],
        "domains": ["mal-site.org"],
    }

    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content=json.dumps(expected_entities),
        provider="mock",
        model="mock-model",
        task_type=TaskType.EXTRACTION.value,
        tokens_used=25,
        latency_ms=6.1,
    )

    request = ModelRequest(
        task_type=TaskType.EXTRACTION,
        prompt=prompt,
        structured_output=True,
    )

    response = await mock_gateway.extract(request)

    extracted = json.loads(response.content)
    assert extracted["ip_addresses"] == ["192.168.1.100"]
    assert "badactor@phish.com" in extracted["emails"]
    assert "mal-site.org" in extracted["domains"]


@pytest.mark.asyncio
async def test_risk_scoring_produces_reasonable_scores(mock_gateway):
    """Test risk scoring produces reasonable scores in 0-1 range."""
    prompt = "Calculate risk score for wire transfer of $500,000 to new offshore account in high-risk jurisdiction."

    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content=json.dumps({"risk_score": 0.92, "level": "HIGH"}),
        provider="mock",
        model="mock-model",
        task_type=TaskType.REASONING.value,
        tokens_used=18,
        latency_ms=5.0,
    )

    request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt=prompt,
    )

    response = await mock_gateway.generate(request)
    data = json.loads(response.content)
    score = data["risk_score"]

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


@pytest.mark.asyncio
async def test_sentiment_analysis_returns_correct_polarity(mock_gateway):
    """Test sentiment analysis of reports returns correct polarity."""
    prompt = "Analyze sentiment of fraud complaint: 'I lost all my life savings to this scam, I am completely devastated.'"

    mock_gateway.predefined_responses[prompt] = ModelResponse(
        content="NEGATIVE",
        provider="mock",
        model="mock-model",
        task_type=TaskType.CLASSIFICATION.value,
        confidence=0.98,
    )

    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt=prompt,
    )

    response = await mock_gateway.generate(request)

    assert response.content in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    assert response.content == "NEGATIVE"
    assert response.confidence == 0.98


@pytest.mark.asyncio
async def test_accuracy_with_custom_gateway_subclass():
    """Verify custom BaseModelGateway subclass works with predefined evaluation responses."""
    class CustomAccuracyGateway(BaseModelGateway):
        async def _call_provider(self, provider, request, operation):
            return ModelResponse(
                content="WIRE_FRAUD",
                provider=provider.value if hasattr(provider, "value") else str(provider),
                model="accuracy-model",
                task_type=request.task_type.value,
                tokens_used=15,
                latency_ms=3.0,
            )

    gateway = CustomAccuracyGateway()
    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt="Wire transfer intercepted with forged authorization code",
    )

    response = await gateway.classify(request)
    assert response.content == "WIRE_FRAUD"
    assert response.model == "accuracy-model"
