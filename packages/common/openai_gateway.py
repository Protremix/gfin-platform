# GFIN OpenAI Model Gateway Adapter
#
# Uses GPT-5.6-LUNA as the primary AI model for GFIN operations.
# All AI access goes through the ModelGateway interface — no direct OpenAI calls
# from application code.
#
# Per Constitution Article XV: Provider independence through Model Gateway.
# Per AI Policy §3: Model routing by task type and data classification.
#
# Environment variables:
#   OPENAI_PROJECT_KEY — API key (required)
#   OPENAI_MODEL       — Primary model (default: gpt-5.6-luna)
#   OPENAI_TIMEOUT     — Request timeout in seconds (default: 30)
#   OPENAI_MAX_RETRIES — Max retries before fallback (default: 3)

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import structlog
from openai import AsyncOpenAI

from common.model_gateway import (
    BaseModelGateway,
    ModelProvider,
    ModelRequest,
    ModelResponse,
)

logger = structlog.get_logger("gfin.openai_gateway")

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3


class OpenAIGateway(BaseModelGateway):
    """OpenAI adapter for the GFIN Model Gateway.

    Uses GPT-5.6-LUNA as the primary model for:
    - Complex reasoning
    - Multilingual analysis
    - Citizen AI assistant
    - Investigation summaries
    - Evidence synthesis
    - Structured extraction

    Classification-aware routing:
    - PUBLIC / COMMUNITY → OpenAI (external)
    - RESTRICTED → OpenAI only if authorized (via ModelGateway routing)
    - LAW_ENFORCEMENT / HIGHLY_RESTRICTED → Local models only (enforced by BaseModelGateway._route)

    Fallback: If OpenAI is unavailable, falls back to local provider (if configured).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        fallback_gateway: BaseModelGateway | None = None,
    ) -> None:
        super().__init__(
            primary_provider=ModelProvider.OPENAI,
            fallback_provider=ModelProvider.LOCAL,
            max_retries=max_retries or DEFAULT_MAX_RETRIES,
            timeout_seconds=timeout or DEFAULT_TIMEOUT,
        )

        self._api_key = api_key or os.environ.get("OPENAI_PROJECT_KEY")
        if not self._api_key:
            raise ValueError(
                "OPENAI_PROJECT_KEY not set. "
                "Set the environment variable or pass api_key explicitly."
            )

        self._model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries or DEFAULT_MAX_RETRIES
        self._fallback_gateway = fallback_gateway
        self._total_requests = 0
        self._total_tokens = 0
        self._total_errors = 0

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            timeout=self._timeout,
        )

        logger.info(
            "openai_gateway_initialized",
            model=self._model,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )

    async def _call_provider(
        self,
        provider: ModelProvider,
        request: ModelRequest,
        operation: str,
    ) -> ModelResponse:
        """Call the appropriate provider. OpenAI for primary, fallback gateway for local."""
        if provider == ModelProvider.OPENAI:
            return await self._call_openai(request, operation)
        elif provider == ModelProvider.LOCAL:
            if self._fallback_gateway:
                return await self._fallback_gateway._call_provider(provider, request, operation)
            return await self._call_local_fallback(request, operation)
        else:
            return await self._call_local_fallback(request, operation)

    async def _call_openai(self, request: ModelRequest, operation: str) -> ModelResponse:
        """Call OpenAI GPT-5.6-LUNA with retry and error handling."""
        start_time = time.time()
        self._total_requests += 1

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Build operation-specific system prompt
        system_context = self._build_system_context(request, operation)
        if system_context:
            messages.insert(0, {"role": "system", "content": system_context})

        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                # GPT-5.6-LUNA only supports default temperature (1.0)
            }
            if request.max_tokens:
                kwargs["max_completion_tokens"] = request.max_tokens

            # Add structured output if requested
            if request.structured_output and request.output_schema:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "gfin_response",
                        "schema": request.output_schema,
                        "strict": True,
                    },
                }
            elif request.structured_output:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self._call_with_retry(kwargs)
            latency_ms = (time.time() - start_time) * 1000

            tokens = 0
            if response.usage:
                tokens = response.usage.total_tokens
                self._total_tokens += tokens

            content = response.choices[0].message.content or ""

            return ModelResponse(
                content=content,
                provider="openai",
                model=str(response.model or self._model),
                task_type=request.task_type.value,
                tokens_used=tokens,
                latency_ms=latency_ms,
                correlation_id=request.correlation_id,
            )

        except Exception as e:
            self._total_errors += 1
            logger.error(
                "openai_call_failed",
                error=str(e),
                error_type=type(e).__name__,
                operation=operation,
                model=self._model,
            )
            raise

    async def _call_with_retry(self, kwargs: dict[str, Any]):
        """Call OpenAI with exponential backoff retry.

        Also retries on empty content — GPT-5.6-LUNA (reasoning model)
        may occasionally produce no visible output while using tokens
        for internal reasoning. Retrying typically returns content.
        """
        last_error = None
        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                if not content and attempt < self._max_retries - 1:
                    logger.warning(
                        "openai_empty_content_retry",
                        attempt=attempt + 1,
                        tokens=response.usage.total_tokens if response.usage else 0,
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                return response
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "openai_retry",
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                        error=str(e)[:100],
                    )
                    await asyncio.sleep(wait_time)
        if last_error:
            raise last_error
        return response

    async def _call_local_fallback(self, request: ModelRequest, operation: str) -> ModelResponse:
        """Fallback when OpenAI is unavailable and no fallback gateway is configured.

        Returns a minimal response indicating AI is unavailable.
        The caller should handle this gracefully — core platform continues
        without AI enhancement.
        """
        return ModelResponse(
            content="AI_UNAVAILABLE: OpenAI is unreachable and no local fallback is configured. "
            "Core platform operations continue without AI enhancement.",
            provider="local",
            model="fallback",
            task_type=request.task_type.value,
            error="No local model configured",
            unverified=True,
        )

    def _build_system_context(self, request: ModelRequest, operation: str) -> str:
        """Build operation-specific system context for GFIN AI tasks."""
        contexts = {
            "generate": (
                "You are a GFIN fraud intelligence assistant. "
                "Every claim you make must reference evidence by ID. "
                "If you do not have sufficient evidence, state INSUFFICIENT_DATA. "
                "Never fabricate sources, evidence, or relationships."
            ),
            "classify": (
                "You are a GFIN fraud classification engine. "
                "Classify the input into one of: PHISHING, INVESTMENT_FRAUD, "
                "ROMANCE_SCAM, TECH_SUPPORT_SCAM, IMPERSONATION, "
                "SHOPPING_SCAM, CRYPTO_FRAUD, OTHER, UNKNOWN. "
                "Respond with the classification and a brief evidence-based rationale."
            ),
            "extract": (
                "You are a GFIN entity extraction engine. "
                "Extract entities (phones, emails, URLs, domains, crypto wallets) "
                "from the input. Return as JSON with entity_type, value, and confidence. "
                "Only extract what is explicitly present. Never fabricate entities."
            ),
        }
        return contexts.get(operation, "")

    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using OpenAI.

        Note: Per AI Policy, embeddings should prefer local models for latency/privacy.
        This implementation uses OpenAI's embedding API but the routing layer
        should direct embeddings to local providers when available.
        """
        try:
            response = await self._client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("openai_embed_failed", error=str(e)[:100])
            # Return zero vector as fallback — caller should handle
            return [0.0] * 1536

    async def health_check(self) -> dict[str, bool]:
        """Check if OpenAI is available."""
        try:
            await self._client.chat.completions.create(
                model=self._model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_completion_tokens=5,
            )
            return {"openai": True, "local": self._fallback_gateway is not None}
        except Exception:
            return {"openai": False, "local": self._fallback_gateway is not None}

    def get_stats(self) -> dict[str, int]:
        """Get gateway usage statistics."""
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_errors": self._total_errors,
        }


# ─── Factory ───

_gateway: OpenAIGateway | None = None


def get_openai_gateway() -> OpenAIGateway:
    """Get or create the singleton OpenAI gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = OpenAIGateway()
    return _gateway


def set_openai_gateway(gateway: OpenAIGateway) -> None:
    """Override the gateway (for testing)."""
    global _gateway
    _gateway = gateway
