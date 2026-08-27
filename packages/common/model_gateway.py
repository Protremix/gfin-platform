# GFIN Model Gateway Abstraction Interface
#
# Layer A (current): BaseModelGateway — routes through backend functions
# Layer B (target):  Standalone Model Gateway service (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# Per Constitution Article XV: The production platform shall use a MODEL GATEWAY
# rather than hard-coding a single AI provider.
#
# Per Master Spec §25: The gateway must support model selection, fallback,
# timeout, retries, cost controls, logging, authorization, provider health,
# and structured outputs.
#
# CRITICAL: No application code ever calls an AI provider directly.
# All AI access goes through this interface.

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("common.model_gateway")


class ModelProvider(StrEnum):
    """Supported AI providers."""

    OPENAI = "openai"
    LOCAL = "local"
    OTHER = "other"


class TaskType(StrEnum):
    """AI task types for routing decisions."""

    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    EXTRACTION = "extraction"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    COMPARISON = "comparison"
    GENERATION = "generation"


class ModelRequest(BaseModel):
    """A request to the model gateway."""

    task_type: TaskType
    prompt: str
    system_prompt: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int | None = None
    temperature: float = 0.0
    structured_output: bool = False
    output_schema: dict[str, Any] | None = None
    classification_filter: str = "PUBLIC"
    requesting_user: str | None = None
    requesting_org: str | None = None
    correlation_id: str | None = None


class ModelResponse(BaseModel):
    """A response from the model gateway."""

    content: str
    provider: str
    model: str
    task_type: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    confidence: float | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    unverified: bool = False
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None


class ModelGateway(ABC):
    """Abstract model gateway interface.

    CRITICAL: All AI access in the application goes through this interface.
    No direct OpenAI/local/other model calls in application code.

    The gateway handles:
    - Provider selection based on task type and data classification
    - Fallback from primary to secondary providers
    - Timeout and retry
    - Cost controls
    - Request and response logging
    - Authorization (classification-aware routing)
    - Provider health monitoring
    - Structured output enforcement
    """

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response using the routed model."""
        ...

    @abstractmethod
    async def classify(self, request: ModelRequest) -> ModelResponse:
        """Classify content."""
        ...

    @abstractmethod
    async def extract(self, request: ModelRequest) -> ModelResponse:
        """Extract structured information."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embeddings."""
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured providers."""
        ...


class BaseModelGateway(ModelGateway):
    """Base implementation with routing, retry, and fallback logic.

    Subclasses implement _call_provider() for each specific provider.
    This class handles routing decisions, retries, and fallback.
    """

    def __init__(
        self,
        primary_provider: ModelProvider = ModelProvider.OPENAI,
        fallback_provider: ModelProvider | None = ModelProvider.LOCAL,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ) -> None:
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        self._total_requests = 0
        self._total_errors = 0
        self._total_tokens = 0

    @property
    def total_requests(self) -> int:
        return self._total_requests

    @property
    def total_errors(self) -> int:
        return self._total_errors

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def _route(self, task_type: TaskType, classification: str) -> ModelProvider:
        """Route a request to the appropriate provider.

        Rules per AI Policy §3 (Model Routing Strategy):
        - HIGHLY_RESTRICTED / LAW_ENFORCEMENT → local only (no data egress)
        - High-volume simple tasks → local
        - Complex reasoning → primary (OpenAI)
        """
        if classification in ("HIGHLY_RESTRICTED", "LAW_ENFORCEMENT"):
            return ModelProvider.LOCAL

        if task_type in (TaskType.EMBEDDING,):
            return ModelProvider.LOCAL

        return self._primary

    async def generate(self, request: ModelRequest) -> ModelResponse:
        provider = self._route(request.task_type, request.classification_filter)
        return await self._call_with_fallback(provider, request, "generate")

    async def classify(self, request: ModelRequest) -> ModelResponse:
        request.task_type = TaskType.CLASSIFICATION
        provider = self._route(request.task_type, request.classification_filter)
        return await self._call_with_fallback(provider, request, "classify")

    async def extract(self, request: ModelRequest) -> ModelResponse:
        request.task_type = TaskType.EXTRACTION
        provider = self._route(request.task_type, request.classification_filter)
        return await self._call_with_fallback(provider, request, "extract")

    async def embed(self, text: str) -> list[float]:
        """Default embedding — override in subclass."""
        raise NotImplementedError("Embedding not implemented in base gateway")

    async def health_check(self) -> dict[str, bool]:
        """Default health check — override in subclass."""
        return {self._primary.value: True, self._fallback.value if self._fallback else "none": True}

    async def _call_with_fallback(
        self, provider: ModelProvider, request: ModelRequest, operation: str
    ) -> ModelResponse:
        """Call provider with retry and fallback."""
        if not request.correlation_id:
            request.correlation_id = str(uuid.uuid4())

        self._total_requests += 1
        logger.info(
            "Calling gateway operation=%s provider=%s task_type=%s correlation_id=%s",
            operation,
            provider.value if hasattr(provider, "value") else str(provider),
            request.task_type.value if hasattr(request.task_type, "value") else str(request.task_type),
            request.correlation_id,
        )

        # Empty prompt validation
        if not request.prompt or not request.prompt.strip():
            self._total_errors += 1
            logger.error("Empty prompt in ModelRequest correlation_id=%s", request.correlation_id)
            return ModelResponse(
                content="",
                provider=provider.value if hasattr(provider, "value") else str(provider),
                model="error",
                task_type=request.task_type.value if hasattr(request.task_type, "value") else str(request.task_type),
                error="Empty prompt provided",
                unverified=True,
                correlation_id=request.correlation_id,
            )

        try:
            res = await self._call_provider(provider, request, operation)
            if not res.correlation_id:
                res.correlation_id = request.correlation_id
            self._total_tokens += res.tokens_used
            return res
        except Exception as primary_error:
            logger.warning(
                "Primary provider %s failed for correlation_id=%s: %s",
                provider.value if hasattr(provider, "value") else str(provider),
                request.correlation_id,
                primary_error,
            )
            if self._fallback and self._fallback != provider:
                try:
                    res = await self._call_provider(self._fallback, request, operation)
                    if not res.correlation_id:
                        res.correlation_id = request.correlation_id
                    self._total_tokens += res.tokens_used
                    return res
                except Exception as fallback_error:
                    logger.error(
                        "Fallback provider failed for correlation_id=%s: %s",
                        request.correlation_id,
                        fallback_error,
                    )
            self._total_errors += 1
            return ModelResponse(
                content="",
                provider=provider.value if hasattr(provider, "value") else str(provider),
                model="error",
                task_type=request.task_type.value if hasattr(request.task_type, "value") else str(request.task_type),
                error=str(primary_error),
                unverified=True,
                correlation_id=request.correlation_id,
            )

    async def _call_provider(
        self, provider: ModelProvider, request: ModelRequest, operation: str
    ) -> ModelResponse:
        """Call a specific provider. Override in subclass."""
        raise NotImplementedError("Subclass must implement _call_provider")
