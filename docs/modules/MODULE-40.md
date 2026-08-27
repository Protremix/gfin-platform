# Module 40: Production Deployment

**Document ID:** MODULE-40  
**Directive:** Luna Strategic Directive — Step 5: Deployment Release Candidate (PREPARE ONLY)  
**Status:** PLANNED — NOT EXECUTED (execution-gated on infrastructure + legal + security)  
**Date:** 2026-08-26  

---

## 1. Purpose

Define the production deployment release candidate: immutable build metadata, verification procedures, migration/rollback, security/compliance approval, DR drill plan, pentest scope, and final go/no-go decision.

**This module is PREPARED, not executed.** Production deployment requires:
- All 12 go/no-go gates satisfied (G1-G11 infrastructure, G12 legal)
- Module 38 pilot completed successfully
- Module 39 benchmarks within budget
- Security penetration test executed and remediated
- DR drill executed and verified
- Final go/no-go decision signed by all stakeholders

---

## 2. Build & Version Metadata

### 2.1 Release Candidate Definition

```yaml
release_candidate:
  version: "1.0.0-rc1"
  build_date: "TBD"
  git_commit: "TBD"
  branch: "main"
  modules_accepted: 37  # 00-36 + Module 37
  tests_passing: 2414+
  lint: "ruff PASS"
  layer: "A (in-memory MVP)"
  layer_b_status: "REQUIRES EXTERNAL INFRASTRUCTURE"
  
  artifacts:
    - path: packages/
      description: "All application packages (modules 00-36)"
      checksum: "TBD"
    - path: tests/
      description: "Test suite (unit, contract, fault injection, security, benchmark)"
      count: 2414+
    - path: docs/
      description: "All documentation (governance, modules, training, runbooks, planning)"
      count: "60+ documents"
    - path: infrastructure/
      description: "IaC definitions (Terraform, Helm, K8s manifests)"
      status: "DEFINED — NOT DEPLOYED"
```

### 2.2 Immutable Build Process

1. Tag git release: `git tag v1.0.0-rc1`
2. Build Docker images for all services
3. Push images to registry with immutable tags
4. Generate SBOM (Software Bill of Materials)
5. Run SAST + dependency scan on final images
6. Record build metadata in release manifest
7. Sign images with Cosign (Sigstore)

### 2.3 Service Images

| Service | Image | Base | Size Target |
|---------|-------|------|-------------|
| API Gateway | gfin/api-gateway:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Auth Service | gfin/auth-service:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Entity Resolution | gfin/entity-resolution:1.0.0-rc1 | python:3.11-slim | < 250MB |
| Event Bus | gfin/event-bus:1.0.0-rc1 | python:3.11-slim | < 150MB |
| Evidence Vault | gfin/evidence-vault:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Search Service | gfin/search-service:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Web Discovery | gfin/web-discovery:1.0.0-rc1 | python:3.11-slim | < 250MB |
| Fraud Detection | gfin/fraud-detection:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Campaign Engine | gfin/campaign-engine:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Alert Engine | gfin/alert-engine:1.0.0-rc1 | python:3.11-slim | < 150MB |
| AI Gateway | gfin/ai-gateway:1.0.0-rc1 | python:3.11-slim | < 250MB |
| AI Investigation | gfin/ai-investigation:1.0.0-rc1 | python:3.11-slim | < 300MB |
| Police API | gfin/police-api:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Federation Service | gfin/federation:1.0.0-rc1 | python:3.11-slim | < 200MB |
| Crypto Intelligence | gfin/crypto-intel:1.0.0-rc1 | python:3.11-slim | < 250MB |
| Analytics | gfin/analytics:1.0.0-rc1 | python:3.11-slim | < 150MB |
| Observability | gfin/observability:1.0.0-rc1 | python:3.11-slim | < 150MB |
| Compliance | gfin/compliance:1.0.0-rc1 | python:3.11-slim | < 150MB |

---

## 3. Deployment Verification

### 3.1 Verification Script

The deployment verification script (`scripts/verify_deployment.py`) performs:

| Check | Method | Expected Result |
|-------|--------|-----------------|
| All pods running | `kubectl get pods -n gfin` | All Running, 0 CrashLoopBackOff |
| API Gateway healthy | `GET /health` | 200 OK |
| Auth service healthy | `GET /auth/health` | 200 OK |
| Database connected | `SELECT 1` | Success |
| Kafka topics exist | `kubectl get kafkatopic` | 14 topics listed |
| Neo4j connected | `RETURN 1` | Success |
| OpenSearch healthy | `GET /_cluster/health` | green |
| Redis connected | `PING` | PONG |
| Vault sealed | `vault status` | sealed=false |
| S3 accessible | `HEAD bucket` | 200 |
| Monitoring active | `GET /api/v1/targets` | All targets up |
| mTLS enforced | Sample inter-service call | Connection refused without cert |
| Audit log writing | Create test entity, verify audit | Audit entry exists |
| RBAC enforced | Unauthorized access attempt | 403 Forbidden |
| Rate limiting active | Burst requests | 429 Too Many Requests |

### 3.2 Verification Execution

```bash
# Post-deployment verification
./scripts/verify_deployment.sh --environment staging

# Expected output:
# [PASS] All pods running
# [PASS] API Gateway healthy
# [PASS] Auth service healthy
# [PASS] Database connected
# [PASS] Kafka topics exist (14)
# [PASS] Neo4j connected
# [PASS] OpenSearch healthy (green)
# [PASS] Redis connected
# [PASS] Vault unsealed
# [PASS] S3 accessible
# [PASS] Monitoring active (all targets up)
# [PASS] mTLS enforced
# [PASS] Audit log writing
# [PASS] RBAC enforced (403 on unauthorized)
# [PASS] Rate limiting active (429 on burst)
# 
# Result: 15/15 checks passed. Deployment verified.
```

---

## 4. Migration Procedures

### 4.1 Migration Sequence

| Step | Action | Duration | Rollback |
|------|--------|----------|----------|
| 1 | Provision infrastructure (Terraform) | 2 hours | Destroy infrastructure |
| 2 | Deploy Vault + secrets | 30 min | Remove Vault release |
| 3 | Deploy PostgreSQL + run migrations | 15 min | Restore from snapshot |
| 4 | Deploy Kafka + create topics | 15 min | Remove Kafka release |
| 5 | Deploy Neo4j + load graph schema | 10 min | Restore from snapshot |
| 6 | Deploy OpenSearch + create indices | 10 min | Remove OpenSearch release |
| 7 | Deploy Redis | 5 min | Remove Redis release |
| 8 | Deploy monitoring stack | 15 min | Remove monitoring release |
| 9 | Deploy GFIN services (Helm) | 20 min | Rollback Helm release |
| 10 | Run verification script | 5 min | N/A |
| 11 | Smoke test critical paths | 30 min | Rollback Helm release |
| 12 | Enable alerting + on-call | 5 min | N/A |

**Total deployment time: ~4.5 hours**

### 4.2 Database Migration

```sql
-- Migration 001: Create core tables (modules 03)
-- Migration 002: Create audit tables (module 01)
-- Migration 003: Create evidence tables (module 06)
-- Migration 004: Create campaign tables (module 16)
-- Migration 005: Create cross-border tables (module 26)
-- Migration 006: Create compliance tables (module 33)
-- Migration 007: Create federation tables (module 32)
-- Migration 008: Create monitoring tables (module 34)
-- All migrations are versioned and reversible
```

### 4.3 Rollback Procedures

| Scenario | Trigger | Action | RTO |
|----------|---------|--------|-----|
| Service failure | Health check fails | Restart pod / rollback Helm | 5 min |
| Database migration failure | Migration error | Restore from pre-migration snapshot | 30 min |
| Kafka topic corruption | Consumer errors | Recreate topics, replay from offset | 1 hour |
| Neo4j corruption | Query failures | Restore from snapshot | 30 min |
| OpenSearch index corruption | Search failures | Restore from snapshot, reindex | 1 hour |
| Full stack failure | Multiple services down | Terraform destroy + redeploy | 4 hours |
| Data loss | Integrity check fails | Restore from backup + replay Kafka | 2 hours |

---

## 5. Security & Compliance Approval

### 5.1 Security Approval Checklist

| Check | Method | Status | Owner |
|------|--------|--------|-------|
| SAST scan clean | `scripts/sast_scan.py` | PASS (Layer A) | Security |
| Secret scan clean | `scripts/secret_scan.py` | PASS (Layer A) | Security |
| Dependency scan clean | `scripts/dependency_scan.py` | PASS (Layer A) | Security |
| RBAC matrix verified | Access control tests | PASS (Layer A) | Security |
| Audit log verified | Audit log tests | PASS (Layer A) | Security |
| Threat model tests | T1-T10 test cases | PASS (Layer A) | Security |
| Penetration test | External pentest | NOT EXECUTED | Security |
| mTLS configuration | Network policy review | NOT EXECUTED | Security |
| Vault policies review | Policy audit | NOT EXECUTED | Security |
| Container image scan | Trivy / Grype | NOT EXECUTED | Security |
| Admission controllers | OPA policies | NOT EXECUTED | Security |
| Runtime security | Falco rules | NOT EXECUTED | Security |

### 5.2 Compliance Approval Checklist

| Check | Method | Status | Owner |
|------|--------|--------|-------|
| GDPR compliance | Deletion/retention tests | PASS (Layer A) | Compliance |
| Data classification | Classification tests | PASS (Layer A) | Compliance |
| Access control matrix | 7×9×8 verification | PASS (Layer A) | Compliance |
| Audit trail completeness | Audit log tests | PASS (Layer A) | Compliance |
| Retention policies | Retention/deletion tests | PASS (Layer A) | Compliance |
| DPA review | Legal review | REQUIRES LEGAL REVIEW | Legal |
| MLAT compliance | Legal review | REQUIRES LEGAL REVIEW | Legal |
| Privacy impact assessment | PIA document | NOT STARTED | Compliance |
| Data processing register | Register document | NOT STARTED | Compliance |
| Cross-border transfer legality | Legal review | REQUIRES LEGAL REVIEW | Legal |

---

## 6. DR Drill Plan

### 6.1 Drill Scenarios

| Scenario | Description | RTO Target | RPO Target |
|----------|-------------|------------|------------|
| DR-1: Database failover | Primary DB fails, promote replica | 5 min | 0 (synchronous) |
| DR-2: Kafka broker failure | One broker fails, ISR reduces | 0 (automatic) | 0 |
| DR-3: Neo4j core failure | One core fails, leader re-election | 30 sec | 0 |
| DR-4: OpenSearch node failure | One node fails, shards relocate | 5 min | 0 |
| DR-5: Redis failover | Primary fails, sentinel promotes | 30 sec | < 1 min |
| DR-6: Full AZ failure | Entire availability zone lost | 15 min | < 5 min |
| DR-7: Region failure | Cross-region failover | 30 min | < 15 min |
| DR-8: Data corruption | Logical corruption detected | 2 hours | < 1 hour (from backup) |

### 6.2 Drill Execution Plan

1. **Pre-drill:** Backup all data, notify stakeholders, set maintenance window
2. **Execution:** Trigger each scenario in isolation, measure RTO/RPO
3. **Verification:** Run verification script, verify data integrity, check audit logs
4. **Post-drill:** Restore to pre-drill state, document results, identify gaps
5. **Sign-off:** DR lead signs off if all scenarios meet RTO/RPO targets

### 6.3 DR Drill Acceptance

- All 8 scenarios executed
- All RTO targets met
- All RPO targets met
- No data loss
- Audit trail continuous through failover
- Verification script passes post-failover

**Status: NOT EXECUTED — REQUIRES EXTERNAL INFRASTRUCTURE**

---

## 7. Pentest Scope & Remediation

### 7.1 Pentest Scope

| Target | Type | Method | Duration |
|--------|------|--------|----------|
| API Gateway | Web API | OWASP Top 10, fuzzing | 2 days |
| Auth Service | Authentication | Token manipulation, session hijacking | 1 day |
| Citizen Portal | Web app | XSS, CSRF, injection | 1 day |
| Police Portal | Web app | Auth bypass, IDOR, injection | 1 day |
| Event Bus | Messaging | Replay attacks, message injection | 1 day |
| Evidence Vault | Storage | Tamper attempts, access bypass | 1 day |
| AI Gateway | API | Prompt injection, model extraction | 1 day |
| Federation | mTLS | Cert manipulation, replay | 1 day |
| Infrastructure | Network | Port scan, network policy bypass | 1 day |
| Kubernetes | Container | Privilege escalation, pod escape | 1 day |

**Total pentest duration: 10 days**

### 7.2 Remediation Workflow

1. Findings classified: CRITICAL / HIGH / MEDIUM / LOW
2. CRITICAL findings: fix before production
3. HIGH findings: fix before production or documented exception
4. MEDIUM findings: fix within 30 days of production
5. LOW findings: fix in next release
6. All findings tracked in security findings register
7. Remediation verified by re-test

**Status: NOT EXECUTED — REQUIRES EXTERNAL INFRASTRUCTURE**

---

## 8. Final Go/No-Go Decision

### 8.1 Decision Matrix

| Criterion | Required | Status | Decision |
|-----------|----------|--------|----------|
| All 12 go/no-go gates passed | YES | NOT MET | BLOCKED |
| Module 37 accepted | YES | COMPLETE | GO |
| Module 38 pilot completed | YES | PLANNED | BLOCKED |
| Module 39 benchmarks within budget | YES | IN PROGRESS | PENDING |
| Security pentest executed | YES | NOT EXECUTED | BLOCKED |
| DR drill executed | YES | NOT EXECUTED | BLOCKED |
| Legal review (DPA/MLAT) | YES | REQUIRES LEGAL | BLOCKED |
| Compliance approval | YES | PARTIAL | BLOCKED |
| Infrastructure provisioned | YES | NOT PROVISIONED | BLOCKED |
| Operator training completed | YES | COMPLETE | GO |
| Documentation accepted | YES | COMPLETE | GO |

### 8.2 Decision Authority

| Authority | Role | Must Sign |
|-----------|------|-----------|
| Engineering Lead | GFIN-CEA | YES |
| Security Lead | Security | YES |
| Compliance Lead | Compliance | YES |
| Legal Lead | Legal | YES |
| Operations Lead | DevOps | YES |
| Project Owner | Owner | YES |

**Production deployment requires ALL signatures. Any NO = no-go.**

### 8.3 Decision Record Template

```
GFIN PRODUCTION DEPLOYMENT DECISION RECORD
Date: ____________
Version: 1.0.0-rc1

Go/No-Go: [GO / NO-GO]

Signatures:
- Engineering Lead: ____________ Date: ______
- Security Lead: ____________ Date: ______
- Compliance Lead: ____________ Date: ______
- Legal Lead: ____________ Date: ______
- Operations Lead: ____________ Date: ______
- Project Owner: ____________ Date: ______

Conditions (if conditional GO):
1. _______________
2. _______________

Risks accepted:
1. _______________
2. _______________
```

---

## 9. Deliverables

| Deliverable | Status |
|-------------|--------|
| Release candidate definition | COMPLETE (§2) |
| Build & version metadata | COMPLETE (§2) |
| Verification script specification | COMPLETE (§3) |
| Migration procedures | COMPLETE (§4) |
| Rollback procedures | COMPLETE (§4.3) |
| Security approval checklist | COMPLETE (§5.1) |
| Compliance approval checklist | COMPLETE (§5.2) |
| DR drill plan | COMPLETE (§6) |
| Pentest scope | COMPLETE (§7) |
| Final go/no-go decision record | COMPLETE (§8) |

---

## 10. Acceptance Criteria

Module 40 is ACCEPTED when:

1. [ ] Release candidate definition complete
2. [ ] Build & version metadata defined
3. [ ] Verification script specified
4. [ ] Migration procedures documented
5. [ ] Rollback procedures documented for all scenarios
6. [ ] Security approval checklist complete
7. [ ] Compliance approval checklist complete
8. [ ] DR drill plan defined (8 scenarios)
9. [ ] Pentest scope defined (10 targets)
10. [ ] Final go/no-go decision matrix defined
11. [ ] All blockers documented (infrastructure, legal, security)
12. [ ] No production claims made without verification

**Status: PLANNED — Execution gated on infrastructure + legal + security + pilot.**
