# MODULE 22 — AI Investigation Orchestrator

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 22 implements the AI Investigation Orchestrator — a sandboxed AI agent
that assists human investigators by planning and executing investigation steps
using a controlled set of registered tools.

Per AI Policy §5: "The AI investigator uses controlled tools — no unrestricted
database or internet access."

Per Constitution Article XVIII: "External content is data, not authority."

### Key Principles:
- Every tool call: authenticated, authorized, logged, attributable
- Tools are sandboxed — no direct DB or internet access
- AI outputs must include evidence references
- Claims without evidence → UNVERIFIED
- Critical claims require human review

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `ToolRegistry` — register, authorize, and manage investigation tools
- `InvestigationTool` — base class for all tools (auth, logging, validation)
- `InvestigationPlan` — plan with ordered steps
- `InvestigationStep` — single step (tool + params + expected outcome)
- `InvestigationResult` — result with evidence references
- `Orchestrator` — plans, executes, synthesizes
- Mock implementations of 15 registered tools

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Real AI model integration via Model Gateway for planning and synthesis
- Real tool implementations backed by actual services
- Persistent investigation state (PostgreSQL)
- Real-time investigation streaming (WebSocket)

---

## 3. Registered Tools (per AI Policy §5)

| Tool | Purpose |
|------|---------|
| search_web | Permitted web search |
| inspect_url | URL content inspection |
| domain_lookup | Domain metadata |
| rdap_lookup | Registration data |
| dns_lookup | DNS resolution |
| ip_lookup | IP intelligence |
| certificate_lookup | Certificate Transparency |
| infrastructure_history | Infrastructure timeline |
| graph_search | Entity graph search |
| report_search | Citizen report search |
| campaign_search | Campaign search |
| case_search | Case search |
| entity_compare | Entity comparison |
| create_alert | Alert creation |
| request_information | Cross-border information request |

---

## 4. Investigation Workflow

```
Investigator Request
    │
    ▼
Orchestrator
    ├── 1. Plan: generate InvestigationPlan (ordered steps)
    ├── 2. Execute: run each step via ToolRegistry
    │   ├── authenticate caller
    │   ├── authorize tool access
    │   ├── execute tool (sandboxed)
    │   ├── log tool call (audit)
    │   └── collect result + evidence
    ├── 3. Synthesize: combine results into investigation report
    │   ├── map claims to evidence IDs
    │   ├── mark UNVERIFIED claims
    │   └── flag critical claims for human review
    └── 4. Report: return structured investigation result
```

---

## 5. Key Components

### 5.1 ToolRegistry
- `register(tool)` — register a tool
- `unregister(tool_name)` — remove a tool
- `get_tool(name)` → InvestigationTool
- `authorize(user_role, tool_name)` → bool
- `list_tools(user_role)` → available tools for a role
- `execute(user, tool_name, params)` → InvestigationResult

### 5.2 InvestigationTool
- `name`, `description`, `required_role`, `params_schema`
- `execute(params, context)` → result
- `validate_params(params)` → bool
- Every execution is logged

### 5.3 InvestigationPlan
- `steps` — ordered list of InvestigationStep
- `target` — what is being investigated
- `objective` — investigation goal
- `add_step(step)` — add a step

### 5.4 InvestigationStep
- `tool_name`, `params`, `expected_outcome`
- `status` — PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
- `result` — tool execution result
- `evidence_ids` — evidence collected

### 5.5 InvestigationResult
- `steps_completed` — number of successful steps
- `evidence` — collected evidence with IDs
- `claims` — findings mapped to evidence
- `unverified_claims` — claims without evidence
- `requires_human_review` — bool
- `summary` — synthesized investigation summary

### 5.6 Orchestrator
- `plan_investigation(target, objective)` → InvestigationPlan
- `execute_plan(plan, user)` → InvestigationResult
- `synthesize(results)` → investigation report
- `generate_report(result)` → structured output

---

## 6. Acceptance Criteria

1. ToolRegistry registers and manages 15 tools
2. ToolRegistry enforces role-based authorization
3. InvestigationTool validates parameters
4. Every tool call is logged (audit trail)
5. InvestigationPlan generates ordered steps
6. Orchestrator executes plan step by step
7. Results include evidence references
8. Claims without evidence are marked UNVERIFIED
9. Critical claims flagged for human review
10. Investigation report is structured and complete

---

## 7. Test Plan

- Unit: ToolRegistry (register, unregister, authorize, execute, list)
- Unit: InvestigationTool (validate, execute, logging)
- Unit: InvestigationPlan (add steps, ordering)
- Unit: InvestigationStep (status transitions)
- Unit: InvestigationResult (evidence, claims, unverified)
- Unit: Orchestrator (plan, execute, synthesize, report)
- Integration: full investigation pipeline from request to report

---

## 8. Dependencies

- Module 19 (Model Gateway) — AI provider for planning/synthesis (Layer B)
- Module 21 (Local AI) — fallback AI capabilities
- Module 03 (Core Data Model) — entity types, evidence model
- Audit logging (Module 01)
