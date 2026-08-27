"""GFIN Brain schemas — Pydantic models for Brain operations."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ───

class HumanInTheLoopMode(str, Enum):
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"


class BrainState(str, Enum):
    CASE_CREATED = "case_created"
    SIGNAL_VALIDATED = "signal_validated"
    DISCOVERY = "discovery"
    ENRICHMENT = "enrichment"
    CORRELATION = "correlation"
    EVIDENCE_REVIEW = "evidence_review"
    INVESTIGATOR_REVIEW = "investigator_review"
    MONITORING = "monitoring"
    REPORTING = "reporting"
    CLOSED = "closed"


class StopReason(str, Enum):
    GOAL_SATISFIED = "goal_satisfied"
    EVIDENCE_THRESHOLD_REACHED = "evidence_threshold_reached"
    BUDGET_EXHAUSTED = "budget_exhausted"
    NO_JUSTIFIED_ACTION = "no_justified_action"
    AUTHORIZATION_PREVENTS = "authorization_prevents"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    CONFIGURED_STOPPING_CONDITION = "configured_stopping_condition"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED_CONFLICT = "unresolved_conflict"


class ComponentHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


# ─── Tool Schemas ───

class ToolInputSchema(BaseModel):
    """JSON schema for tool input parameters."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ToolOutputSchema(BaseModel):
    """JSON schema for tool output."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition of a registered Brain tool."""
    tool_id: str
    name: str
    description: str
    input_schema: ToolInputSchema
    output_schema: ToolOutputSchema
    required_permissions: list[str] = Field(default_factory=list)
    classification: str = "PUBLIC"
    jurisdiction_scope: list[str] = Field(default_factory=list)
    rate_limit: int = 60  # calls per minute
    timeout: int = 30  # seconds
    audit_policy: str = "full"
    data_access_scope: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    enabled: bool = True
    version: str = "1.0.0"


class ToolCallRequest(BaseModel):
    """Request to execute a tool through the Brain."""
    tool_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    case_id: str
    authorization_token: str
    context_ref: Optional[str] = None


class ToolResult(BaseModel):
    """Result of a tool execution."""
    tool_id: str
    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    evidence_id: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=_utc_now)


# ─── Decision Record ───

class DecisionRecord(BaseModel):
    """Structured record of a Brain decision."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    goal: str
    available_evidence_ids: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    selected_tool: str
    reason_code: str
    policy_id: str
    model_id: str
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=_utc_now)
    result: Optional[dict[str, Any]] = None


# ─── Context ───

class BrainContext(BaseModel):
    """Controlled context package for GPT."""
    case_id: str
    case_state: BrainState
    investigation_objective: str
    relevant_entities: list[dict[str, Any]] = Field(default_factory=list)
    relevant_relationships: list[dict[str, Any]] = Field(default_factory=list)
    relevant_evidence: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    previous_searches: list[dict[str, Any]] = Field(default_factory=list)
    rejected_hypotheses: list[str] = Field(default_factory=list)
    contradictory_evidence: list[dict[str, Any]] = Field(default_factory=list)
    current_permissions: list[str] = Field(default_factory=list)
    current_classification: str = "PUBLIC"
    available_tools: list[str] = Field(default_factory=list)
    system_policies: list[str] = Field(default_factory=list)


# ─── Investigation ───

class InvestigationCreate(BaseModel):
    """Request to create a new investigation."""
    case_id: str
    goal: str
    mode: HumanInTheLoopMode = HumanInTheLoopMode.SUPERVISED
    budget_tool_calls: int = 100
    evidence_threshold: float = 0.7


class InvestigationState(BaseModel):
    """Current state of an investigation."""
    case_id: str
    goal: str
    state: BrainState = BrainState.CASE_CREATED
    mode: HumanInTheLoopMode = HumanInTheLoopMode.SUPERVISED
    tool_calls_made: int = 0
    budget_tool_calls: int = 100
    evidence_threshold: float = 0.7
    decisions: list[str] = Field(default_factory=list)  # decision_ids
    evidence_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    relationship_ids: list[str] = Field(default_factory=list)
    stop_reason: Optional[StopReason] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    pending_approval: bool = False


# ─── Conflict ───

class ConflictResolution(BaseModel):
    """Result of conflict resolution between modules."""
    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_a: str
    source_b: str
    reliability_a: float = 0.5
    reliability_b: float = 0.5
    evidence: list[str] = Field(default_factory=list)
    resolution: str = ""
    status: ConflictStatus = ConflictStatus.UNRESOLVED_CONFLICT


# ─── Health ───

class ComponentStatus(BaseModel):
    """Status of a single Brain component."""
    name: str
    health: ComponentHealth
    message: str = ""


class HealthReport(BaseModel):
    """Brain health report."""
    healthy: bool
    components: list[ComponentStatus] = Field(default_factory=list)
    boot_record: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=_utc_now)


class BrainStatus(BaseModel):
    """Brain operational status."""
    brain_ready: bool
    active_investigations: int = 0
    total_decisions: int = 0
    total_tool_calls: int = 0
    total_tool_failures: int = 0
    model_id: str = ""
    uptime_seconds: int = 0
