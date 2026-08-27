"""GFIN Brain Orchestrator — central investigation lifecycle and control loop."""
from __future__ import annotations
from typing import Any, Optional, Protocol
from datetime import datetime, timezone
import logging

from packages.brain.schemas import (
    InvestigationCreate, InvestigationState, BrainState,
    HumanInTheLoopMode, StopReason, DecisionRecord,
    BrainContext, ToolCallRequest, ToolResult,
)

logger = logging.getLogger(__name__)


class ModelGatewayInterface(Protocol):
    """Abstract interface for the Model Gateway."""
    def invoke(self, prompt: str, context: BrainContext, model_id: str) -> dict[str, Any]: ...


class BrainOrchestrator:
    """Central orchestrator for GFIN investigations.

    The Brain thinks and coordinates. Modules perform specialized work.
    The Brain is subordinate to security.

    Control Loop:
        CASE_GOAL -> UNDERSTAND -> PLAN -> SELECT_TOOL -> EXECUTE ->
        OBSERVE_RESULT -> UPDATE_MEMORY -> UPDATE_GRAPH -> UPDATE_TIMELINE ->
        EVALUATE_EVIDENCE -> IDENTIFY_GAPS -> PLAN_NEXT -> REPEAT
    """

    def __init__(
        self,
        model_gateway: ModelGatewayInterface,
        tool_router: ToolRouter,
        context_engine: ContextEngine,
        decision_engine: DecisionEngine,
        state_manager: StateManager,
        conflict_resolver: ConflictResolver,
    ):
        self.gateway = model_gateway
        self.router = tool_router
        self.context_engine = context_engine
        self.decision_engine = decision_engine
        self.state_manager = state_manager
        self.conflict_resolver = conflict_resolver
        self._investigations: dict[str, InvestigationState] = {}
        self._model_id = "gpt-5.6-luna"

    def create_investigation(self, request: InvestigationCreate) -> InvestigationState:
        """Create a new investigation."""
        state = InvestigationState(
            case_id=request.case_id,
            goal=request.goal,
            mode=request.mode,
            budget_tool_calls=request.budget_tool_calls,
            evidence_threshold=request.evidence_threshold,
        )
        self._investigations[request.case_id] = state
        self.state_manager.set_state(request.case_id, BrainState.CASE_CREATED)
        logger.info(f"Investigation created: {request.case_id} goal={request.goal}")
        return state

    def continue_investigation(self, case_id: str) -> InvestigationState:
        """Continue an investigation by running the control loop."""
        state = self._investigations.get(case_id)
        if not state:
            raise ValueError(f"Investigation not found: {case_id}")
        if state.stop_reason:
            logger.warning(f"Investigation already stopped: {case_id} reason={state.stop_reason}")
            return state

        # Run the control loop
        self._run_control_loop(state)
        return state

    def stop_investigation(self, case_id: str, reason: StopReason) -> InvestigationState:
        """Stop an investigation."""
        state = self._investigations.get(case_id)
        if not state:
            raise ValueError(f"Investigation not found: {case_id}")
        state.stop_reason = reason
        state.updated_at = datetime.now(timezone.utc)
        logger.info(f"Investigation stopped: {case_id} reason={reason.value}")
        return state

    def resume_investigation(self, case_id: str) -> InvestigationState:
        """Resume a stopped investigation."""
        state = self._investigations.get(case_id)
        if not state:
            raise ValueError(f"Investigation not found: {case_id}")
        if not state.stop_reason:
            logger.warning(f"Investigation not stopped: {case_id}")
            return state
        state.stop_reason = None
        state.updated_at = datetime.now(timezone.utc)
        logger.info(f"Investigation resumed: {case_id}")
        return self.continue_investigation(case_id)

    def approve_action(self, case_id: str, decision_id: str) -> bool:
        """Approve a pending action (for ASSISTED/SUPERVISED modes)."""
        state = self._investigations.get(case_id)
        if not state:
            raise ValueError(f"Investigation not found: {case_id}")
        state.pending_approval = False
        return True

    def get_investigation(self, case_id: str) -> Optional[InvestigationState]:
        """Get investigation state."""
        return self._investigations.get(case_id)

    def _run_control_loop(self, state: InvestigationState, max_steps: int = 50) -> None:
        """Run the central Brain control loop.

        CASE_GOAL -> UNDERSTAND -> PLAN -> SELECT_TOOL -> EXECUTE ->
        OBSERVE_RESULT -> UPDATE_MEMORY -> UPDATE_GRAPH -> UPDATE_TIMELINE ->
        EVALUATE_EVIDENCE -> IDENTIFY_GAPS -> PLAN_NEXT -> REPEAT
        """
        for step in range(max_steps):
            # Check stop conditions
            stop = self._check_stop_conditions(state)
            if stop:
                state.stop_reason = stop
                return

            # UNDERSTAND: Build context
            context = self.context_engine.build_context(state)

            # PLAN: Ask GPT what to do next
            prompt = self._build_planning_prompt(state, context)
            gpt_response = self.gateway.invoke(prompt, context, self._model_id)

            # SELECT_TOOL: Extract tool decision from GPT response
            tool_id = gpt_response.get("selected_tool", "")
            tool_params = gpt_response.get("tool_params", {})
            confidence = gpt_response.get("confidence", 0.0)
            reason = gpt_response.get("reason", "default")

            if not tool_id:
                state.stop_reason = StopReason.NO_JUSTIFIED_ACTION
                return

            # Check human-in-the-loop
            if self._requires_approval(state, tool_id):
                state.pending_approval = True
                state.updated_at = datetime.now(timezone.utc)
                return  # Wait for approval

            # EXECUTE tool through the pipeline
            request = ToolCallRequest(
                tool_id=tool_id,
                params=tool_params,
                case_id=state.case_id,
                authorization_token="",  # Set by security layer
            )
            result = self.router.execute_tool(request)

            # Record decision
            decision = DecisionRecord(
                case_id=state.case_id,
                goal=state.goal,
                candidate_tools=list(self.router.registry.list_tool_ids()),
                selected_tool=tool_id,
                reason_code=reason,
                policy_id="POL-001",
                model_id=self._model_id,
                confidence=confidence,
                result=result.model_dump() if result.success else {"error": result.error},
            )
            self.decision_engine.record_decision(decision)
            state.decisions.append(decision.decision_id)
            state.tool_calls_made += 1

            # OBSERVE RESULT + UPDATE memory/graph/timeline
            if result.success and result.evidence_id:
                state.evidence_ids.append(result.evidence_id)

            # EVALUATE EVIDENCE
            if len(state.evidence_ids) > 0:
                confidence_level = sum(1 for _ in state.evidence_ids) / max(state.budget_tool_calls, 1)
                if confidence_level >= state.evidence_threshold:
                    state.stop_reason = StopReason.EVIDENCE_THRESHOLD_REACHED
                    return

            # State transitions
            self._advance_state(state)

        state.stop_reason = StopReason.BUDGET_EXHAUSTED

    def _check_stop_conditions(self, state: InvestigationState) -> Optional[StopReason]:
        """Check all stop conditions."""
        if state.stop_reason:
            return state.stop_reason
        if state.tool_calls_made >= state.budget_tool_calls:
            return StopReason.BUDGET_EXHAUSTED
        return None

    def _requires_approval(self, state: InvestigationState, tool_id: str) -> bool:
        """Check if the current action requires human approval."""
        tool = self.router.registry.get_tool(tool_id)
        if not tool:
            return True

        if state.mode == HumanInTheLoopMode.ASSISTED:
            return True
        elif state.mode == HumanInTheLoopMode.SUPERVISED:
            from packages.brain.schemas import RiskLevel
            return tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        else:  # AUTONOMOUS
            from packages.brain.schemas import RiskLevel
            return tool.risk_level == RiskLevel.CRITICAL

    def _advance_state(self, state: InvestigationState) -> None:
        """Advance the investigation state if appropriate."""
        transitions = {
            BrainState.CASE_CREATED: BrainState.SIGNAL_VALIDATED,
            BrainState.SIGNAL_VALIDATED: BrainState.DISCOVERY,
            BrainState.DISCOVERY: BrainState.ENRICHMENT,
            BrainState.ENRICHMENT: BrainState.CORRELATION,
            BrainState.CORRELATION: BrainState.EVIDENCE_REVIEW,
            BrainState.EVIDENCE_REVIEW: BrainState.INVESTIGATOR_REVIEW,
            BrainState.INVESTIGATOR_REVIEW: BrainState.MONITORING,
            BrainState.MONITORING: BrainState.REPORTING,
            BrainState.REPORTING: BrainState.CLOSED,
        }
        new_state = transitions.get(state.state)
        if new_state:
            state.state = new_state
            self.state_manager.set_state(state.case_id, new_state)
        state.updated_at = datetime.now(timezone.utc)

    def _build_planning_prompt(self, state: InvestigationState, context: BrainContext) -> str:
        """Build the prompt for GPT planning."""
        return (
            f"Investigation goal: {state.goal}\n"
            f"Current state: {state.state.value}\n"
            f"Tools called: {state.tool_calls_made}/{state.budget_tool_calls}\n"
            f"Evidence collected: {len(state.evidence_ids)} items\n"
            f"Available tools: {', '.join(context.available_tools[:20])}\n"
            f"\nSelect the next tool to call and provide tool_params. "
            f"Also provide confidence (0.0-1.0) and reason.\n"
            f"Respond as JSON: {{selected_tool, tool_params, confidence, reason}}"
        )
