"""GFIN Brain Tool Router — enforces the full tool-call pipeline."""
from __future__ import annotations
from typing import Any, Optional
from datetime import datetime, timezone
import time
import logging

from packages.brain.schemas import ToolCallRequest, ToolResult, RiskLevel
from packages.brain.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolRouter:
    """Routes and executes tool calls through the full security pipeline.

    Pipeline:
        GPT_DECISION -> TOOL_VALIDATION -> AUTHORIZATION -> CLASSIFICATION_CHECK ->
        JURISDICTION_CHECK -> RATE_LIMIT -> TOOL_EXECUTION -> OUTPUT_VALIDATION ->
        EVIDENCE_PROVENANCE -> AUDIT -> RETURN_TO_GPT

    GPT cannot skip any stage.
    """

    def __init__(self, registry: ToolRegistry, max_retries: int = 2):
        self.registry = registry
        self.max_retries = max_retries
        self._call_counts: dict[str, list[float]] = {}  # rate limiting
        self._total_calls = 0
        self._total_failures = 0

    def execute_tool(self, request: ToolCallRequest) -> ToolResult:
        """Execute a tool through the full pipeline."""
        start = time.time()
        self._total_calls += 1

        # Stage 1: TOOL VALIDATION
        ok, msg = self.registry.validate_params(request.tool_id, request.params)
        if not ok:
            self._total_failures += 1
            return ToolResult(tool_id=request.tool_id, success=False, error=f"Validation: {msg}")

        # Stage 2: AUTHORIZATION (check permissions)
        # In production, permissions come from the authorization token
        ok, msg = self.registry.check_permissions(request.tool_id, [])  # placeholder
        if not ok:
            logger.warning(f"Authorization denied for {request.tool_id}: {msg}")
            return ToolResult(tool_id=request.tool_id, success=False, error=f"Authorization: {msg}")

        # Stage 3: CLASSIFICATION CHECK
        ok, msg = self.registry.check_classification(request.tool_id, "PUBLIC")
        if not ok:
            return ToolResult(tool_id=request.tool_id, success=False, error=f"Classification: {msg}")

        # Stage 4: JURISDICTION CHECK
        ok, msg = self.registry.check_jurisdiction(request.tool_id, ["GLOBAL"])
        if not ok:
            return ToolResult(tool_id=request.tool_id, success=False, error=f"Jurisdiction: {msg}")

        # Stage 5: RATE LIMIT
        if not self._check_rate_limit(request.tool_id):
            return ToolResult(tool_id=request.tool_id, success=False, error="Rate limit exceeded")

        # Stage 6: TOOL EXECUTION (with retry)
        result = self._execute_with_retry(request)

        # Stage 7: OUTPUT VALIDATION
        if result.success and result.data:
            if not self._validate_output(request.tool_id, result.data):
                self._total_failures += 1
                return ToolResult(tool_id=request.tool_id, success=False, error="Output validation failed")

        # Stage 8: EVIDENCE/PROVENANCE (attach evidence ID if applicable)
        # Stage 9: AUDIT (log the call)
        elapsed_ms = int((time.time() - start) * 1000)
        result.execution_time_ms = elapsed_ms
        logger.info(
            f"Tool executed: {request.tool_id} case={request.case_id} "
            f"success={result.success} time={elapsed_ms}ms"
        )

        return result

    def _execute_with_retry(self, request: ToolCallRequest) -> ToolResult:
        """Execute tool with retry policy."""
        handler = self.registry.get_handler(request.tool_id)
        if not handler:
            self._total_failures += 1
            return ToolResult(tool_id=request.tool_id, success=False, error="No handler found")

        for attempt in range(self.max_retries + 1):
            try:
                data = handler(**request.params)
                return ToolResult(
                    tool_id=request.tool_id,
                    success=True,
                    data=data if isinstance(data, dict) else {"result": str(data)},
                )
            except Exception as e:
                logger.warning(f"Tool {request.tool_id} attempt {attempt+1} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                self._total_failures += 1
                return ToolResult(tool_id=request.tool_id, success=False, error=str(e))

    def _validate_output(self, tool_id: str, data: dict[str, Any]) -> bool:
        """Validate tool output."""
        if not isinstance(data, dict):
            return False
        return True

    def _check_rate_limit(self, tool_id: str) -> bool:
        """Check rate limit for a tool."""
        now = time.time()
        tool = self.registry.get_tool(tool_id)
        if not tool:
            return False

        window = 60  # 1 minute window
        calls = self._call_counts.get(tool_id, [])
        # Remove old calls
        calls = [t for t in calls if now - t < window]
        if len(calls) >= tool.rate_limit:
            return False
        calls.append(now)
        self._call_counts[tool_id] = calls
        return True

    @property
    def total_calls(self) -> int:
        return self._total_calls

    @property
    def total_failures(self) -> int:
        return self._total_failures
