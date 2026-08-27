# GFIN Training Curriculum & Role-Based Exercise Tracks

**Document Version:** 1.0  
**Target Audience:** Training Coordinators, System Operators, Investigators, Administrators, Developers  
**Scope:** Runbook-Mapped Operational Modules, Practical Tracks, and Sign-Off Frameworks  

---

## 1. Runbook-Mapped Training Modules (6 Modules)

The core training curriculum is structured into 6 operational modules directly mapped to the 6 production runbooks defined in `docs/runbooks/runbooks.md`.

---

### Module TR-1: Platform Deployment & Readiness (Runbook 1)
- **Primary Objective:** Master pre-deployment checks, Helm deployment procedures, health endpoint verification, and post-deployment sanity checks.
- **Prerequisites:** Completion of GFIN Overview & Basic CLI familiarity.
- **Practical Exercise:**
  1. Evaluate all 12 Go/No-Go gates using `python -m packages.production.go_no_go_gates`.
  2. Simulate service deployment using Helm chart DRY-RUN mode.
  3. Validate `/health` endpoint output across core microservices.
- **Assessment Criteria:** Trainee must achieve 100% accuracy in identifying gate failures and verifying post-deployment health logs.

---

### Module TR-2: Automated & Manual Rollback Execution (Runbook 2)
- **Primary Objective:** Identify deployment regression triggers (P95 latency > 2x, error rate > 5%) and execute safe rollback procedures without data corruption.
- **Prerequisites:** Module TR-1.
- **Practical Exercise:**
  1. Trigger simulated error spike in staging cluster.
  2. Execute `helm rollback gfin` within 3 minutes of alert trigger.
  3. Perform cryptographic evidence vault hash verification post-rollback to confirm zero data loss.
- **Assessment Criteria:** Rollback executed under 5 minutes; complete post-rollback data integrity verified.

---

### Module TR-3: Cryptographic Key & Secret Rotation (Runbook 3)
- **Primary Objective:** Perform scheduled and emergency rotation of JWT signing keys, TLS certificates, API keys, and database credentials in HashiCorp Vault and Kubernetes.
- **Prerequisites:** Module TR-1, Basic Vault & Kubernetes RBAC knowledge.
- **Practical Exercise:**
  1. Provision new API key in HashiCorp Vault KV store.
  2. Apply updated secret manifest in Kubernetes namespace.
  3. Perform zero-downtime rolling restart of API Gateway and verify audit log generation.
- **Assessment Criteria:** Zero downtime during rotation; new credentials active and old credentials revoked safely.

---

### Module TR-4: Incident Response & Containment (Runbook 4)
- **Primary Objective:** Execute 6-stage incident response (Detect, Assess, Contain, Eradicate, Recover, Post-mortem) across P1 to P4 severity incidents.
- **Prerequisites:** Modules TR-1 through TR-3.
- **Practical Exercise:**
  1. Receive P1 simulated alert ("Data Leak via Unauthorized API Access").
  2. Execute NetworkPolicy isolate command on affected pod.
  3. Extract immutable audit logs to identify rogue token and execute credential revocation.
- **Assessment Criteria:** Incident contained within 15 minutes (P1 SLO); draft post-mortem report completed within 2 hours.

---

### Module TR-5: Backup & Disaster Recovery Execution (Runbook 5)
- **Primary Objective:** Configure, execute, and verify backups and cluster failover across PostgreSQL, Neo4j, OpenSearch, and S3 storage.
- **Prerequisites:** System Administrator role qualification.
- **Practical Exercise:**
  1. Perform manual PostgreSQL pg_dump and WAL archive upload to S3 bucket.
  2. Simulate local database loss and execute full point-in-time restore.
  3. Verify RTO < 1 hour and RPO < 5 minutes targets.
- **Assessment Criteria:** Successful restore with 100% record parity and checksum matching.

---

### Module TR-6: GDPR & Privacy Erasure Workflow (Runbook 6)
- **Primary Objective:** Execute Data Subject Access Requests (DSAR) and Right to Erasure procedures compliant with 5 data classification levels and audit requirements.
- **Prerequisites:** Compliance / Administrator qualification.
- **Practical Exercise:**
  1. Process DSAR request for test citizen email.
  2. Execute soft-deletion across Entity Repository, Graph Store, and OpenSearch Index.
  3. Verify anonymization of security audit logs.
- **Assessment Criteria:** Complete erasure across all search indices while maintaining immutable audit chain integrity.

---

## 2. Role-Based Exercise Tracks

Trainees follow specialized tracks aligned with their primary operational responsibilities:

### Track 1: Operator Track
- **Focus:** System startup/shutdown, entity lifecycle, evidence vault verification, DLQ replay, campaign status, and health metrics.
- **Required Modules:** TR-1, TR-2, TR-4.
- **Capstone Project:** Detect a DLQ backlog, identify root cause, replay failed events, and verify health snapshot.

### Track 2: Investigator Track
- **Focus:** Fraud report intake, graph traversal, 7-stage cross-border request execution, crypto fund tracing, and 15 AI Orchestrator tools.
- **Required Modules:** TR-4, TR-6.
- **Capstone Project:** Conduct a multi-hop crypto trace on an illicit wallet, run 7-stage CBR with target jurisdiction, and export STIX 2.1 bundle.

### Track 3: Administrator Track
- **Focus:** RBAC/ABAC matrix enforcement, Vault key rotation, audit log verification, rate limiting, GDPR erasure, and DR backups.
- **Required Modules:** TR-1 through TR-6.
- **Capstone Project:** Provision new agency org, enforce custom ABAC jurisdiction policies, rotate JWT keys, and perform DSAR erasure.

### Track 4: Developer Track
- **Focus:** Architecture, Pydantic schema extension, new fraud detection rules, event bus subscriber addition, model gateway integration, and testing.
- **Required Modules:** TR-1, TR-2.
- **Capstone Project:** Implement a new Entity schema, write a custom fraud detection rule, add unit tests, and pass Ruff linting.

---

## 3. Knowledge Assessment Question Summary (40 Questions Overview)

The curriculum integrates 40 formal assessment questions (10 per role track) detailed in `docs/training/knowledge-assessment.md`:

- **Operator Questions (1–10):** Health check interpretation, DLQ replaying, Evidence Vault SHA-256 verification, Campaign lifecycle states.
- **Investigator Questions (11–20):** Report triage scoring, 20 graph relationships, 7 CBR workflow stages, 15 AI tool permissions, STIX export.
- **Administrator Questions (21–30):** 9x8 RBAC/ABAC matrix, 5 Data Classification levels, Vault key rotation schedules, GDPR erasure steps, RTO/RPO targets.
- **Developer Questions (31–40):** Layer A vs B adapters, Pydantic model inheritance, Event Bus topic design, Ruff formatting, Pytest suite execution.

---

## 4. Operator Sign-Off Record Template

```
================================================================────────────────
                    GFIN OPERATOR QUALIFICATION SIGN-OFF RECORD
================================================================────────────────

Trainee Name:       ____________________________________________________
Trainee Role:       [ ] Operator  [ ] Investigator  [ ] Administrator  [ ] Developer
Organization:       ____________________________________________________
Jurisdiction:       ____________________________________________________

TRAINING MODULE COMPLETION VERIFICATION:
 [ ] Module TR-1: Platform Deployment & Readiness         Date: ____________
 [ ] Module TR-2: Automated & Manual Rollback             Date: ____________
 [ ] Module TR-3: Cryptographic Key & Secret Rotation     Date: ____________
 [ ] Module TR-4: Incident Response & Containment         Date: ____________
 [ ] Module TR-5: Backup & Disaster Recovery Execution    Date: ____________
 [ ] Module TR-6: GDPR & Privacy Erasure Workflow         Date: ____________

CAPSTONE EXERCISE VERIFICATION:
 Capstone Project Title: _________________________________________________
 Completion Date:        ____________
 Pass/Fail Status:       [ ] PASS   [ ] FAIL
 Evaluator Score:        ______ / 100 (Min. 80 Required)

KNOWLEDGE ASSESSMENT VERIFICATION:
 Score Achieved:         ______ / 40  (______ %)  [Min. 80% Required]

APPROVAL SIGNATURES:

Trainee Signature:       ___________________________  Date: ____________

Evaluator Signature:     ___________________________  Date: ____________
Evaluator Title:         ___________________________

Security Lead Sign-Off:  ___________________________  Date: ____________
================================================================────────────────
```
