"""GFIN AI Investigation Orchestrator — Module 22.

Sandboxed AI agent that assists investigators by planning and executing
investigation steps using controlled, registered tools.

Per AI Policy §5: controlled tools only, no direct DB or internet access.
Per Constitution Article XVIII: external content is data, not authority.

Layer A: In-memory tool implementations with mock data
Layer B: Real AI planning/synthesis via Model Gateway, real tool backends (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EvidenceType(str, Enum):
    ENTITY_RECORD = "ENTITY_RECORD"
    REPORT = "REPORT"
    CAMPAIGN = "CAMPAIGN"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DOMAIN = "DOMAIN"
    IP = "IP"
    CERTIFICATE = "CERTIFICATE"
    WEB_CONTENT = "WEB_CONTENT"
    GRAPH_RELATION = "GRAPH_RELATION"
    TOOL_OUTPUT = "TOOL_OUTPUT"


class UserRole(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"
    ANALYST = "ANALYST"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


# ─── Models ───


class ToolParam(BaseModel):
    """Parameter schema for a tool."""

    name: str
    type: str = "string"
    required: bool = True
    description: str = ""


class Evidence(BaseModel):
    """A piece of evidence collected during investigation."""

    id: str
    evidence_type: str
    source: str  # tool name that produced it
    description: str
    data: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Claim(BaseModel):
    """A finding claim mapped to evidence."""

    id: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    verified: bool = True
    requires_human_review: bool = False
    critical: bool = False


class ToolCallLog(BaseModel):
    """Audit log entry for a tool call."""

    id: str
    tool_name: str
    user: str
    user_role: str
    params: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    success: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_ids: list[str] = Field(default_factory=list)


class InvestigationStep(BaseModel):
    """A single step in an investigation plan."""

    id: str
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = ""
    status: str = StepStatus.PENDING.value
    result: dict[str, Any] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    error: str | None = None

    def mark_running(self) -> None:
        self.status = StepStatus.RUNNING.value

    def mark_completed(self, result: dict[str, Any], evidence_ids: list[str]) -> None:
        self.status = StepStatus.COMPLETED.value
        self.result = result
        self.evidence_ids = evidence_ids

    def mark_failed(self, error: str) -> None:
        self.status = StepStatus.FAILED.value
        self.error = error

    def mark_skipped(self) -> None:
        self.status = StepStatus.SKIPPED.value


class InvestigationPlan(BaseModel):
    """An ordered plan of investigation steps."""

    id: str
    target: str
    objective: str
    steps: list[InvestigationStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_step(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        expected_outcome: str = "",
    ) -> InvestigationStep:
        step = InvestigationStep(
            id=f"STEP-{len(self.steps) + 1:03d}",
            tool_name=tool_name,
            params=params or {},
            expected_outcome=expected_outcome,
        )
        self.steps.append(step)
        return step

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED.value)

    @property
    def is_complete(self) -> bool:
        return all(
            s.status
            in (StepStatus.COMPLETED.value, StepStatus.SKIPPED.value, StepStatus.FAILED.value)
            for s in self.steps
        )


class InvestigationResult(BaseModel):
    """Result of an investigation."""

    plan_id: str
    target: str
    objective: str
    steps_completed: int = 0
    steps_failed: int = 0
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Investigation Tool ───


class InvestigationTool:
    """Base class for all investigation tools."""

    def __init__(
        self,
        name: str,
        description: str,
        required_role: str = UserRole.INVESTIGATOR.value,
        params: list[ToolParam] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.required_role = required_role
        self.params_schema = params or []

    def validate_params(self, params: dict[str, Any]) -> tuple[bool, str]:
        """Validate parameters against schema."""
        for p in self.params_schema:
            if p.required and p.name not in params:
                return False, f"Missing required parameter: {p.name}"
        return True, ""

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute the tool (override in subclasses)."""
        return {"tool": self.name, "result": "mock", "params": params}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required_role": self.required_role,
            "params": [p.model_dump() for p in self.params_schema],
        }


# ─── Concrete Tool Implementations (Layer A: Mock) ───


class SearchWebTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="search_web",
            description="Permitted web search for external information",
            required_role=UserRole.INVESTIGATOR.value,
            params=[ToolParam(name="query", description="Search query")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {"results": [], "query": params.get("query", ""), "mock": True}


class InspectUrlTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="inspect_url",
            description="Inspect URL content and metadata",
            params=[ToolParam(name="url", description="URL to inspect")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = params.get("url", "")
        return {"url": url, "status": "mock", "content": "", "headers": {}, "mock": True}


class DomainLookupTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="domain_lookup",
            description="Domain metadata lookup",
            params=[ToolParam(name="domain", description="Domain name")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        domain = params.get("domain", "")
        return {"domain": domain, "registered": True, "registrar": "mock", "mock": True}


class RdapLookupTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="rdap_lookup",
            description="Registration Data Access Protocol lookup",
            params=[ToolParam(name="domain", description="Domain name")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        domain = params.get("domain", "")
        return {"domain": domain, "registrant": "mock", "mock": True}


class DnsLookupTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="dns_lookup",
            description="DNS resolution lookup",
            params=[ToolParam(name="domain", description="Domain to resolve")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        domain = params.get("domain", "")
        return {"domain": domain, "records": [], "mock": True}


class IpLookupTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="ip_lookup",
            description="IP intelligence lookup",
            params=[ToolParam(name="ip", description="IP address")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        ip = params.get("ip", "")
        return {"ip": ip, "asn": "mock", "country": "mock", "abuse_contacts": [], "mock": True}


class CertificateLookupTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="certificate_lookup",
            description="Certificate Transparency log lookup",
            params=[ToolParam(name="domain", description="Domain to check certificates for")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        domain = params.get("domain", "")
        return {"domain": domain, "certificates": [], "mock": True}


class InfrastructureHistoryTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="infrastructure_history",
            description="Infrastructure change timeline",
            params=[ToolParam(name="target", description="Domain or IP")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        target = params.get("target", "")
        return {"target": target, "timeline": [], "mock": True}


class GraphSearchTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="graph_search",
            description="Entity relationship graph search",
            params=[ToolParam(name="entity_id", description="Entity ID to search from")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        entity_id = params.get("entity_id", "")
        return {"entity_id": entity_id, "nodes": [], "edges": [], "mock": True}


class ReportSearchTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="report_search",
            description="Search citizen fraud reports",
            params=[ToolParam(name="query", description="Search query")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = params.get("query", "")
        return {"query": query, "reports": [], "mock": True}


class CampaignSearchTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="campaign_search",
            description="Search fraud campaigns",
            params=[ToolParam(name="query", description="Search query")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = params.get("query", "")
        return {"query": query, "campaigns": [], "mock": True}


class CaseSearchTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="case_search",
            description="Search investigation cases",
            required_role=UserRole.INVESTIGATOR.value,
            params=[ToolParam(name="query", description="Search query")],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = params.get("query", "")
        return {"query": query, "cases": [], "mock": True}


class EntityCompareTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="entity_compare",
            description="Compare two entities for relationships",
            params=[
                ToolParam(name="entity_a", description="First entity ID"),
                ToolParam(name="entity_b", description="Second entity ID"),
            ],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "entity_a": params.get("entity_a", ""),
            "entity_b": params.get("entity_b", ""),
            "shared_infrastructure": [],
            "shared_campaigns": [],
            "mock": True,
        }


class CreateAlertTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="create_alert",
            description="Create an alert from investigation findings",
            required_role=UserRole.SUPERVISOR.value,
            params=[
                ToolParam(name="target_type", description="Type of target"),
                ToolParam(name="target_id", description="ID of target"),
                ToolParam(name="priority", description="Alert priority"),
            ],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {"alert_id": "ALT-MOCK-001", "mock": True, "params": params}


class RequestInformationTool(InvestigationTool):
    def __init__(self) -> None:
        super().__init__(
            name="request_information",
            description="Cross-border information request",
            required_role=UserRole.SUPERVISOR.value,
            params=[
                ToolParam(name="target_jurisdiction", description="Target jurisdiction"),
                ToolParam(name="entity_id", description="Entity to query"),
            ],
        )

    def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "request_id": "REQ-MOCK-001",
            "status": "pending",
            "mock": True,
            "params": params,
        }


# ─── Tool Registry ───


# Role hierarchy for authorization
ROLE_HIERARCHY: dict[str, int] = {
    UserRole.INVESTIGATOR.value: 1,
    UserRole.ANALYST.value: 2,
    UserRole.SUPERVISOR.value: 3,
    UserRole.ADMIN.value: 4,
}


class ToolRegistry:
    """Registry for investigation tools with authorization."""

    def __init__(self, audit_logger: Any | None = None) -> None:
        self._tools: dict[str, InvestigationTool] = {}
        self._audit_logger = audit_logger
        self._call_log: list[ToolCallLog] = []
        self._call_counter = 0
        self._evidence_counter = 0

    def register(self, tool: InvestigationTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool."""
        return self._tools.pop(tool_name, None) is not None

    def get_tool(self, name: str) -> InvestigationTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, user_role: str | None = None) -> list[dict[str, Any]]:
        """List available tools, optionally filtered by role."""
        tools = list(self._tools.values())
        if user_role:
            user_level = ROLE_HIERARCHY.get(user_role, 0)
            tools = [t for t in tools if ROLE_HIERARCHY.get(t.required_role, 0) <= user_level]
        return [t.to_dict() for t in tools]

    def authorize(self, user_role: str, tool_name: str) -> bool:
        """Check if a user role is authorized to use a tool."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return False
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        tool_level = ROLE_HIERARCHY.get(tool.required_role, 0)
        return user_level >= tool_level

    def execute(
        self,
        user: str,
        user_role: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool with full authorization and logging."""
        # 1. Check tool exists
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        # 2. Authorize
        if not self.authorize(user_role, tool_name):
            raise PermissionError(f"User role '{user_role}' not authorized for tool '{tool_name}'")

        # 3. Validate params
        valid, error_msg = tool.validate_params(params)
        if not valid:
            raise ValueError(f"Invalid parameters: {error_msg}")

        # 4. Execute
        result = tool.execute(params)

        # 5. Generate evidence
        self._evidence_counter += 1
        evidence_id = f"EVD-{self._evidence_counter:06d}"
        evidence = Evidence(
            id=evidence_id,
            evidence_type=EvidenceType.TOOL_OUTPUT.value,
            source=tool_name,
            description=f"Output from {tool_name}",
            data=result,
        )

        # 6. Log
        self._call_counter += 1
        log_entry = ToolCallLog(
            id=f"CALL-{self._call_counter:06d}",
            tool_name=tool_name,
            user=user,
            user_role=user_role,
            params=params,
            result_summary=str(result)[:200],
            success=True,
            evidence_ids=[evidence_id],
        )
        self._call_log.append(log_entry)

        # 7. External audit
        if self._audit_logger:
            with contextlib.suppress(Exception):
                self._audit_logger.log(
                    user_id=user,
                    action="tool_execute",
                    resource_type="tool",
                    resource_id=tool_name,
                    details={"params": params, "evidence_id": evidence_id},
                )

        return {
            "result": result,
            "evidence_id": evidence_id,
            "evidence": evidence,
            "call_log_id": log_entry.id,
        }

    def get_call_log(
        self, tool_name: str | None = None, user: str | None = None
    ) -> list[ToolCallLog]:
        """Retrieve tool call audit log."""
        result = list(self._call_log)
        if tool_name:
            result = [entry for entry in result if entry.tool_name == tool_name]
        if user:
            result = [entry for entry in result if entry.user == user]
        return result

    @property
    def tool_count(self) -> int:
        return len(self._tools)


# ─── Orchestrator ───


class Orchestrator:
    """AI Investigation Orchestrator — plans, executes, synthesizes."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._registry = registry or ToolRegistry(audit_logger=audit_logger)
        self._event_bus = event_bus
        self._audit = audit_logger
        self._plan_counter = 0
        self._claim_counter = 0

    def plan_investigation(self, target: str, objective: str) -> InvestigationPlan:
        """Generate an investigation plan for a target.

        Layer A: deterministic plan based on target type.
        Layer B: AI model generates plan via Model Gateway.
        """
        self._plan_counter += 1
        plan = InvestigationPlan(
            id=f"PLAN-{self._plan_counter:06d}",
            target=target,
            objective=objective,
        )

        # Deterministic plan: look up domain, IP, certificates, graph, reports
        plan.add_step(
            tool_name="domain_lookup",
            params={"domain": target},
            expected_outcome="Domain registration information",
        )
        plan.add_step(
            tool_name="dns_lookup",
            params={"domain": target},
            expected_outcome="DNS records (A, MX, NS, TXT)",
        )
        plan.add_step(
            tool_name="certificate_lookup",
            params={"domain": target},
            expected_outcome="SSL certificate history",
        )
        plan.add_step(
            tool_name="rdap_lookup",
            params={"domain": target},
            expected_outcome="Registration data (RDAP)",
        )
        plan.add_step(
            tool_name="graph_search",
            params={"entity_id": target},
            expected_outcome="Entity relationships in the graph",
        )
        plan.add_step(
            tool_name="report_search",
            params={"query": target},
            expected_outcome="Related citizen reports",
        )
        plan.add_step(
            tool_name="campaign_search",
            params={"query": target},
            expected_outcome="Related fraud campaigns",
        )

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="investigation.planned",
                    event={
                        "plan_id": plan.id,
                        "target": target,
                        "steps": len(plan.steps),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return plan

    def execute_plan(
        self,
        plan: InvestigationPlan,
        user: str,
        user_role: str = UserRole.INVESTIGATOR.value,
    ) -> InvestigationResult:
        """Execute an investigation plan step by step."""
        evidence_list: list[Evidence] = []
        failed_steps = 0

        for step in plan.steps:
            step.mark_running()

            try:
                exec_result = self._registry.execute(
                    user=user,
                    user_role=user_role,
                    tool_name=step.tool_name,
                    params=step.params,
                )
                step.mark_completed(
                    result=exec_result["result"],
                    evidence_ids=[exec_result["evidence_id"]],
                )
                evidence_list.append(exec_result["evidence"])

            except PermissionError as e:
                step.mark_skipped()
                failed_steps += 1
                if self._event_bus:
                    with contextlib.suppress(Exception):
                        self._event_bus.publish(
                            topic="investigation.step_skipped",
                            event={
                                "plan_id": plan.id,
                                "step_id": step.id,
                                "reason": str(e),
                            },
                        )

            except Exception as e:
                step.mark_failed(str(e))
                failed_steps += 1

        # Synthesize results
        result = self._synthesize(plan, evidence_list, failed_steps)

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="investigation.completed",
                    event={
                        "plan_id": plan.id,
                        "steps_completed": plan.completed_steps,
                        "steps_failed": failed_steps,
                        "evidence_count": len(evidence_list),
                        "requires_review": result.requires_human_review,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return result

    def _synthesize(
        self,
        plan: InvestigationPlan,
        evidence_list: list[Evidence],
        failed_steps: int,
    ) -> InvestigationResult:
        """Synthesize investigation results from evidence."""
        result = InvestigationResult(
            plan_id=plan.id,
            target=plan.target,
            objective=plan.objective,
            steps_completed=plan.completed_steps,
            steps_failed=failed_steps,
            evidence=evidence_list,
        )

        # Generate claims from evidence
        for ev in evidence_list:
            self._claim_counter += 1
            claim = Claim(
                id=f"CLM-{self._claim_counter:06d}",
                statement=f"Tool '{ev.source}' produced evidence for target '{plan.target}'",
                evidence_ids=[ev.id],
                confidence=0.9,
                verified=True,
            )
            result.claims.append(claim)

        # Mark as requiring human review if any steps failed
        if failed_steps > 0:
            result.requires_human_review = True
            self._claim_counter += 1
            result.claims.append(
                Claim(
                    id=f"CLM-{self._claim_counter:06d}",
                    statement=f"Investigation incomplete — {failed_steps} step(s) failed or were skipped",
                    evidence_ids=[],
                    confidence=0.0,
                    verified=False,
                    requires_human_review=True,
                )
            )
            result.unverified_claims.append(f"Failed steps: {failed_steps} — manual review needed")

        # Generate summary
        result.summary = self._generate_summary(plan, evidence_list, result)

        return result

    def _generate_summary(
        self,
        plan: InvestigationPlan,
        evidence_list: list[Evidence],
        result: InvestigationResult,
    ) -> str:
        """Generate a text summary of the investigation."""
        lines = [
            f"GFIN Investigation Report — {plan.id}",
            f"Target: {plan.target}",
            f"Objective: {plan.objective}",
            f"Steps completed: {result.steps_completed}/{len(plan.steps)}",
            f"Steps failed: {result.steps_failed}",
            f"Evidence collected: {len(evidence_list)} items",
            f"Claims made: {len(result.claims)}",
            f"Unverified claims: {len(result.unverified_claims)}",
        ]
        if result.requires_human_review:
            lines.append("⚠ REQUIRES HUMAN REVIEW")
        lines.append("")
        lines.append("Evidence:")
        for ev in evidence_list:
            lines.append(f"  [{ev.id}] {ev.evidence_type} from {ev.source}: {ev.description}")
        lines.append("")
        lines.append("Claims:")
        for claim in result.claims:
            status = "VERIFIED" if claim.verified else "UNVERIFIED"
            lines.append(f"  [{claim.id}] [{status}] {claim.statement}")
            if claim.evidence_ids:
                lines.append(f"    Evidence: {', '.join(claim.evidence_ids)}")

        return "\n".join(lines)

    def generate_report(self, result: InvestigationResult) -> dict[str, Any]:
        """Generate a structured report from investigation results."""
        return {
            "plan_id": result.plan_id,
            "target": result.target,
            "objective": result.objective,
            "steps_completed": result.steps_completed,
            "steps_failed": result.steps_failed,
            "evidence_count": len(result.evidence),
            "claims": [c.model_dump() for c in result.claims],
            "unverified_claims": result.unverified_claims,
            "requires_human_review": result.requires_human_review,
            "summary": result.summary,
            "created_at": result.created_at.isoformat(),
        }

    @property
    def registry(self) -> ToolRegistry:
        return self._registry


# ─── Default Registry Factory ───


def create_default_registry(audit_logger: Any | None = None) -> ToolRegistry:
    """Create a registry with all 15 registered tools."""
    registry = ToolRegistry(audit_logger=audit_logger)
    tools = [
        SearchWebTool(),
        InspectUrlTool(),
        DomainLookupTool(),
        RdapLookupTool(),
        DnsLookupTool(),
        IpLookupTool(),
        CertificateLookupTool(),
        InfrastructureHistoryTool(),
        GraphSearchTool(),
        ReportSearchTool(),
        CampaignSearchTool(),
        CaseSearchTool(),
        EntityCompareTool(),
        CreateAlertTool(),
        RequestInformationTool(),
    ]
    for tool in tools:
        registry.register(tool)
    return registry
