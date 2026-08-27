# Module 38: Pilot Program

**Document ID:** MODULE-38  
**Directive:** Luna Strategic Directive — Step 3: Pilot Program (PLAN ONLY)  
**Status:** PLANNED — NOT EXECUTED (execution-gated on infrastructure + legal)  
**Date:** 2026-08-26  

---

## 1. Purpose

Define the GFIN Pilot Program: a limited-scope, controlled validation of the platform using synthetic data within the Layer A sandbox, with a clear path to expansion once Layer B infrastructure is provisioned.

**This pilot is PLANNED, not executed.** Execution requires:
- Layer B infrastructure (staging environment) provisioned
- Legal/governance review (DPA, MLAT) completed
- Security review (pentest scope accepted)
- Module 37 training materials accepted

---

## 2. Pilot Charter

### 2.1 Scope

| Dimension | In Scope | Out of Scope |
|-----------|---------|-------------|
| Data | Synthetic data + existing test fixtures | Real citizen data |
| Users | 5-10 trained operators + 3-5 investigators | Public access |
| Modules | 00-36 (Layer A in-memory) | Layer B production infrastructure |
| Integrations | Mock OSINT connectors | Real external API calls |
| AI | OpenAI gateway (test key) + Local AI mock | Production AI model selection |
| Geography | Single jurisdiction (simulated) | Multi-jurisdiction federation |
| Duration | 2 weeks | Ongoing operation |

### 2.2 Objectives

1. Validate end-to-end fraud intelligence workflow: report → triage → enrich → detect → campaign → alert
2. Verify RBAC and data classification enforcement across all roles
3. Test AI investigation orchestrator with synthetic scenarios
4. Measure performance baselines under controlled load
5. Identify UX/documentation gaps from operator feedback
6. Validate go/no-go gate readiness for staging deployment

### 2.3 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Detection quality | > 80% correct fraud type classification | AI gateway results vs. expected |
| False positive rate | < 15% | Manual review of flagged reports |
| Entity resolution accuracy | > 90% correct merges | Known-entity test cases |
| Search latency (p99) | < 300ms | Baseline metrics recorder |
| Event bus throughput | > 1000 events/s | Synthetic load test |
| Campaign detection rate | > 75% of seeded campaigns | Known-campaign test cases |
| Alert delivery rate | 100% | Alert engine logs |
| Audit log completeness | 100% of operations logged | Audit verification tests |
| Operator task completion | > 90% of training exercises completed | Training assessment |
| Critical incidents | 0 | Incident log |

### 2.4 Participants

| Role | Count | Responsibilities |
|------|-------|-----------------|
| Pilot Lead | 1 | Overall coordination, go/no-go decisions |
| Operators | 5-10 | Execute daily workflows, report issues |
| Investigators | 3-5 | Investigation workflows, evidence handling |
| Administrator | 1 | RBAC, audit review, compliance |
| Observer (DevOps) | 1 | Monitor system health, performance |
| Observer (Security) | 1 | Monitor security posture |

---

## 3. Synthetic Data Test Plan

### 3.1 Data Sources

| Source | Type | Volume | Purpose |
|--------|------|--------|---------|
| `synthetic_telemetry.py` | Metrics | 10 metrics × 1000 points | Performance baselining |
| `baseline_metrics.py` | Performance | 6 operations × 100 iterations | SLO validation |
| Test fixtures (tests/) | Entities + Reports | 500 entities, 200 reports | Workflow testing |
| Seeded campaigns | Campaigns | 10 known campaigns | Detection validation |
| Mock OSINT feeds | DNS, RDAP, Cert | 100 domains, 50 IPs | Enrichment testing |
| Simulated citizen reports | Reports | 100 reports (varied types) | Intake workflow |
| Synthetic evidence | Files | 50 evidence items | Chain of custody |

### 3.2 Test Scenarios

#### Scenario 1: Phishing Campaign Detection
- Seed 20 phishing reports across 5 fake domains
- Expected: Campaign detected, linked to 5 domains, alerts generated
- Validate: Campaign scoring, domain linking, alert routing

#### Scenario 2: Cross-Border Request Workflow
- Create report in Jurisdiction A, request data from Jurisdiction B
- Expected: 7-stage workflow completes, policy filtering applied
- Validate: Cross-border request module, federation boundary policy

#### Scenario 3: Evidence Chain of Custody
- Create, retrieve, verify, and attempt tamper on evidence
- Expected: Hash verification catches tampering, audit log records all access
- Validate: Evidence vault, audit log, hash verification

#### Scenario 4: AI Investigation
- Run AI orchestrator on a synthetic fraud case
- Expected: Investigation plan generated, tools executed, evidence-claim mapping, UNVERIFIED marking
- Validate: AI gateway, orchestrator, evidence-claim mapping

#### Scenario 5: Crypto Fund Tracing
- Trace synthetic wallet through 5 transactions
- Expected: BFS trace finds all connected wallets, risk scores calculated
- Validate: Crypto intelligence module, fund tracing

#### Scenario 6: Role-Based Access Control
- Attempt unauthorized access with each role
- Expected: RBAC denies unauthorized access, audit logs capture attempts
- Validate: RBAC, ABAC, audit log, access control matrix

#### Scenario 7: GDPR Right to Erasure
- Submit DSAR for an entity, process deletion
- Expected: Entity soft-deleted, evidence retained per policy, audit trail complete
- Validate: Compliance module, retention policies, deletion workflow

#### Scenario 8: System Recovery
- Simulate service failure, execute recovery
- Expected: Service restored within RTO, no data loss
- Validate: DR procedures, backup/restore runbook

### 3.3 Evidence Capture Template

For each scenario, capture:

```
SCENARIO: [name]
EXECUTOR: [name]
DATE: [date]
RESULT: [PASS/FAIL/PARTIAL]
METRICS:
  - latency_p50: [ms]
  - latency_p99: [ms]
  - throughput: [ops/s]
  - error_rate: [%]
OBSERVATIONS:
  - [free text]
ISSUES FOUND:
  - [issue description]
GAPS IDENTIFIED:
  - [documentation/code/process gap]
RECOMMENDATION:
  - [action item]
```

---

## 4. Data Protection & Compliance

### 4.1 Data Handling

- All pilot data is SYNTHETIC — no real PII
- Data classification: PUBLIC (synthetic) + MOCK RESTRICTED (for testing access controls)
- No data leaves the sandbox environment
- No external integrations activated
- All pilot activities audit-logged

### 4.2 Escalation Procedures

| Issue Type | Escalate To | Response Time |
|------------|------------|---------------|
| Security incident | Pilot Lead + Security Observer | Immediate |
| Data integrity issue | Pilot Lead + DevOps Observer | 1 hour |
| Performance degradation | DevOps Observer | 4 hours |
| UX/documentation gap | Pilot Lead | 24 hours |
| RBAC failure | Pilot Lead + Security Observer | Immediate |

### 4.3 Rollback Procedures

1. Stop all pilot activities
2. Export audit logs and metrics
3. Reset Layer A state (in-memory, no persistence)
4. Review findings
5. Address critical issues
6. Re-start pilot (if applicable)

### 4.4 Termination Criteria

Pilot is terminated if:
- Any security incident occurs
- Data integrity is compromised
- RBAC/access control failure detected
- > 3 critical issues found
- Legal/governance concern raised

---

## 5. Pilot Go/No-Go Checklist

### 5.1 Pre-Pilot Gates

- [ ] Module 37 (Documentation & Training) ACCEPTED
- [ ] All 2,414+ tests passing
- [ ] Lint clean (ruff)
- [ ] All 6 runbooks reviewed by operators
- [ ] Training assessments completed (80% pass rate)
- [ ] Synthetic data prepared and validated
- [ ] Pilot participants identified and trained
- [ ] Pilot environment (Layer A sandbox) verified
- [ ] Monitoring and alerting configured
- [ ] Escalation procedures communicated

### 5.2 Per-Scenario Gates

- [ ] Scenario prerequisites met
- [ ] Synthetic data loaded
- [ ] Monitoring active
- [ ] Evidence capture template ready

### 5.3 Post-Pilot Gates (for staging promotion)

- [ ] All 8 scenarios executed
- [ ] Success metrics met (see §2.3)
- [ ] No critical incidents
- [ ] All issues documented
- [ ] All gaps identified with remediation plan
- [ ] Operator feedback collected
- [ ] Go/no-go decision documented and signed

### 5.4 Mapping to 12 Go/No-Go Gates

| Gate | Pilot Readiness | Staging Readiness |
|------|----------------|-------------------|
| G1: K8s | N/A (Layer A) | Required |
| G2: Vault | N/A (Layer A) | Required |
| G3: Database | N/A (in-memory) | Required |
| G4: Kafka | N/A (in-memory pub/sub) | Required |
| G5: Neo4j | N/A (in-memory graph) | Required |
| G6: OpenSearch | N/A (in-memory index) | Required |
| G7: Redis | N/A (in-memory cache) | Required |
| G8: S3 | N/A (local filesystem) | Required |
| G9: Monitoring | Synthetic telemetry | Required |
| G10: Network Security | N/A (sandbox) | Required |
| G11: Backup/DR | N/A (no persistence) | Required |
| G12: Legal | N/A (synthetic data) | Required |

---

## 6. Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| Pre-pilot setup | 2 days | Data preparation, environment verification, participant training |
| Scenario execution | 8 days | 8 scenarios (1 day each), evidence capture |
| Analysis & reporting | 2 days | Metrics analysis, gap report, go/no-go decision |
| Remediation (if needed) | Variable | Address critical issues before staging |

**Total pilot duration: 12 days (2 weeks)**

---

## 7. Deliverables

| Deliverable | Status |
|-------------|--------|
| Pilot charter | COMPLETE (this document) |
| Synthetic data test plan | COMPLETE (§3) |
| Success metrics | COMPLETE (§2.3) |
| Data protection procedures | COMPLETE (§4) |
| Escalation/rollback/termination | COMPLETE (§4.2-4.4) |
| Go/no-go checklist | COMPLETE (§5) |
| Evidence capture template | COMPLETE (§3.3) |
| Pilot execution | NOT STARTED (execution-gated) |
| Pilot results report | NOT STARTED |
| Post-pilot go/no-go decision | NOT STARTED |

---

## 8. Acceptance Criteria

Module 38 is ACCEPTED when:

1. [ ] Pilot charter is reviewed and approved
2. [ ] Synthetic data test plan is validated
3. [ ] Success metrics are defined and agreed
4. [ ] Data protection procedures are reviewed
5. [ ] Go/no-go checklist maps to all 12 gates
6. [ ] Evidence capture template is ready
7. [ ] All participants identified and roles assigned
8. [ ] Pilot execution is PLANNED (not necessarily executed)

**Status: PLANNED — Execution gated on infrastructure + legal + training.**
