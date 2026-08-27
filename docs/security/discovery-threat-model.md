# GFIN — Security: Discovery Threat Model

**Version:** 1.0
**Status:** IMPLEMENTED (Layer A)
**Date:** 2026-08-26

---

## Threats Addressed

### 1. Data Poisoning

**Threat:** External actors publish misleading data to manipulate GFIN's intelligence graph.

**Mitigation:**
- DataPoisoningGuard: Single untrusted source cannot establish confidence > 0.6
- High confidence (>0.8) requires ≥2 independent sources
- Source reliability scoring per source
- Cross-source comparison before accepting relationships
- Temporal consistency checks
- Analyst review required for high-confidence claims

### 2. Prompt Injection from External Content

**Threat:** External content contains instructions designed to manipulate GFIN's AI analysis.

**Mitigation:**
- All external content treated as DATA, not AUTHORITY
- External content passes through untrusted data boundary
- `sanitize_for_ai()` and `detect_prompt_injection()` applied to all external content
- AI system/developer instructions separated from external content
- External content never executes arbitrary instructions against GFIN

### 3. Unauthorized Source Access

**Threat:** Users attempt to access sources beyond their authorization level.

**Mitigation:**
- Per-source authorization checks (investigator vs police_officer)
- Police database requires LAW_ENFORCEMENT classification
- MISP/OpenCTI/Cortex require authentication
- Coverage report explicitly shows AUTHORIZATION_REQUIRED sources
- Lawful escalation path for authorized users

### 4. Resource Exhaustion / Graph Explosion

**Threat:** Discovery process consumes unbounded resources.

**Mitigation:**
- max_depth, max_nodes, max_tasks, max_runtime_seconds limits
- Per-source rate limits and budgets
- ResourceController enforces all limits
- Circuit breakers and queue backpressure
- Duplicate suppression prevents redundant work

### 5. False Confidence from Multiple Low-Quality Sources

**Threat:** Multiple low-reliability sources create false high-confidence claims.

**Mitigation:**
- Confidence uses 1 - product(1 - reliability_i) model (diminishing returns)
- Confidence capped at 95% (never 100% from external sources)
- Source reliability scores factored into confidence calculation
- DataPoisoningGuard validates high-confidence claims require quality sources

## Human-in-the-Loop Guarantees

The system MUST NOT autonomously:
- Accuse a person
- Declare guilt
- Make arrests
- Make legal determinations
- Alter official case findings

Investigators MUST be able to:
- Inspect evidence
- Reject a relationship
- Confirm a relationship
- Suppress a false positive
- Request additional discovery
- Stop monitoring
- Escalate an investigation
