import pytest

from common.model_gateway import (
    BaseModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    TaskType,
)


@pytest.mark.asyncio
async def test_highly_restricted_classification_routes_to_local(routing_gateway):
    """Test HIGHLY_RESTRICTED classification routes to LOCAL provider only to prevent data egress."""
    request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt="Analyze confidential suspect communication log",
        classification_filter="HIGHLY_RESTRICTED",
    )

    response = await routing_gateway.generate(request)

    assert response.provider == ModelProvider.LOCAL.value
    assert response.provider != ModelProvider.OPENAI.value


@pytest.mark.asyncio
async def test_law_enforcement_classification_routes_to_local(routing_gateway):
    """Test LAW_ENFORCEMENT classification routes to LOCAL provider only."""
    request = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt="Classify law enforcement wiretap transcript metadata",
        classification_filter="LAW_ENFORCEMENT",
    )

    response = await routing_gateway.generate(request)

    assert response.provider == ModelProvider.LOCAL.value
    assert response.provider != ModelProvider.OPENAI.value


@pytest.mark.asyncio
async def test_public_classification_routes_to_primary_openai(routing_gateway):
    """Test PUBLIC classification routes to primary (OpenAI) provider."""
    request = ModelRequest(
        task_type=TaskType.SUMMARIZATION,
        prompt="Summarize public security advisory blog post",
        classification_filter="PUBLIC",
    )

    response = await routing_gateway.generate(request)

    assert response.provider == ModelProvider.OPENAI.value


@pytest.mark.asyncio
async def test_requesting_user_and_requesting_org_tracked_in_requests(routing_gateway):
    """Test requesting_user and requesting_org are tracked in requests."""
    user_id = "usr_analyst_101"
    org_id = "org_interpol"

    request = ModelRequest(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entity data for report #8831",
        requesting_user=user_id,
        requesting_org=org_id,
        classification_filter="PUBLIC",
    )

    await routing_gateway.extract(request)

    assert len(routing_gateway.request_history) > 0
    last_req = routing_gateway.request_history[-1]
    assert last_req.requesting_user == user_id
    assert last_req.requesting_org == org_id


@pytest.mark.asyncio
async def test_classification_filter_enforced_on_every_request(routing_gateway):
    """Test classification_filter is enforced on every request and overrides task type defaults."""
    # Even for REASONING (which defaults to primary for PUBLIC), HIGHLY_RESTRICTED forces LOCAL
    restricted_request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt="Reasoning over restricted data",
        classification_filter="HIGHLY_RESTRICTED",
    )
    restricted_response = await routing_gateway.generate(restricted_request)
    assert restricted_response.provider == ModelProvider.LOCAL.value

    # PUBLIC classification allows primary OPENAI provider
    public_request = ModelRequest(
        task_type=TaskType.REASONING,
        prompt="Reasoning over public data",
        classification_filter="PUBLIC",
    )
    public_response = await routing_gateway.generate(public_request)
    assert public_response.provider == ModelProvider.OPENAI.value


@pytest.mark.asyncio
async def test_unauthorized_task_types_rejected():
    """Test unauthorized task types or tasks exceeding permissions are rejected."""
    class AuthEnforcingGateway(BaseModelGateway):
        def __init__(self, allowed_tasks: set[TaskType]):
            super().__init__()
            self.allowed_tasks = allowed_tasks

        async def _call_provider(self, provider, request, operation):
            if request.task_type not in self.allowed_tasks:
                raise PermissionError(f"Task type {request.task_type} is unauthorized for user {request.requesting_user}")
            return ModelResponse(
                content="Authorized",
                provider=provider.value if hasattr(provider, "value") else str(provider),
                model="auth-model",
                task_type=request.task_type.value,
            )

    auth_gateway = AuthEnforcingGateway(allowed_tasks={TaskType.CLASSIFICATION, TaskType.EXTRACTION})

    # Authorized request
    valid_req = ModelRequest(
        task_type=TaskType.CLASSIFICATION,
        prompt="Valid classification",
        requesting_user="guest_user",
    )
    valid_res = await auth_gateway.classify(valid_req)
    assert valid_res.content == "Authorized"

    # Unauthorized request (GENERATION not in allowed_tasks)
    unauth_req = ModelRequest(
        task_type=TaskType.GENERATION,
        prompt="Unauthorized generation request",
        requesting_user="guest_user",
    )
    unauth_res = await auth_gateway.generate(unauth_req)
    assert unauth_res.error is not None
    assert "unauthorized" in unauth_res.error.lower()
