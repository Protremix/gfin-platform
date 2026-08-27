# GFIN Externalization Roadmap — Luna Guidance

**Document ID:** GFIN-EXT-001  
**Authority:** GPT Luna (GFIN-CEA) — LUNA-EXTERNAL-GUIDANCE-002  
**Date:** 2026-08-26  
**For:** Rojs (Project Owner)  

---

## Executive Position

GFIN is **software-ready for externalization, but not production-ready**. Layer A is frozen and conditionally approved. All 12 production gates remain blocked on external dependencies [GFIN-GRR-001].

## 8-Week Execution Plan

| Week | Phase | Key Actions | Evidence Refs |
|------|-------|-------------|---------------|
| 1-2 | Foundation | Select cloud/on-prem, provision accounts, K8s, networking, Vault | GFIN-IMP-001 |
| 3-4 | Core services | Deploy PostgreSQL, Redis, S3, Kafka/Strimzi, Vault HA, PKI | GFIN-IMP-001, GFIN-DRC-001 |
| 5 | Search & graph | Deploy Neo4j, OpenSearch, health checks, integration validation | GFIN-IMP-001, GFIN-DRC-001 |
| 6 | Operations | Activate monitoring, alerting, CI/CD, backups, retention | GFIN-IMP-001, GFIN-GRR-001 |
| 7 | Staging | Full stack deploy, integration tests, RBAC/NetworkPolicy validation, migration rehearsal | GFIN-IMP-001, GFIN-GRR-001 |
| 8 | Assurance | DR drill, security testing, load testing, migration verification, legal gate review, go/no-go | GFIN-IMP-001, GFIN-GRR-001 |

**Note:** 8 weeks is a provisioning sequence, not a guaranteed launch date. Remediation or legal delays can extend it.

## Answers to Owner Questions

### Q1: Which cloud provider?
**INSUFFICIENT_DATA.** Run a scored evaluation across AWS, GCP, Azure, and on-prem before commitment. Consider: data residency requirements, GDPR compliance, regional availability, pricing, support tier, existing team expertise.

### Q2: What will infrastructure cost?
**INSUFFICIENT_DATA.** Need workload sizing (requests/sec, data volume, storage, retention) for 31 services across 4 environment tiers. Produce low/base/high estimates after sizing.

### Q3: How many people on the team?
**INSUFFICIENT_DATA on exact headcount.** Minimum accountable owners needed:
- Platform engineer (K8s, networking, IaC)
- Security lead (pentest, RBAC, Vault, mTLS)
- Data engineer (Postgres, Neo4j, OpenSearch, migration)
- SRE/Ops (monitoring, alerting, DR, on-call)
- QA (test execution, load testing, validation)
- Legal coordinator (DPA/MLAT, compliance)

### Q4: Can legal review start before infrastructure?
**YES — start immediately, in parallel.** Legal/DPA/MLAT is an independent blocked gate (G10). It does not depend on infrastructure. Engage counsel now with the evidence pack from GFIN-HOC-001.

### Q5: Pentest on Layer A or wait for staging?
Run code analysis, dependency, container, and pre-production testing early. **Do NOT treat Layer A alone as production security clearance.** The security gate (G9) requires SAST/DAST/container scans with 0 Critical/High findings. Full pentest should run on staging environment (Week 7-8).

### Q6: Realistic timeline to go-live?
8 weeks for provisioning + variable time for:
- Legal review (could be 1-6 months)
- Pentest + remediation (2-4 weeks after staging)
- DR drill (1 week)
- Approval signatures (1-2 weeks)

**Realistic estimate: 3-6 months from today**, depending on legal review speed and pentest findings.

### Q7: Any shortcuts?
**Do not waive G1-G12.** Any exception must be documented, risk-accepted by the owner, and must not bypass legal, security, DR, backup, or migration controls.

### Q8: What if legal takes 6 months?
Continue engineering, staging, DR rehearsal, and security remediation in parallel. **Do NOT authorize production go-live while G10 is blocked.** Prepare a revised schedule and preserve evidence validity through revalidation.

## Immediate Actions (This Week)

1. **Appoint gate owners** — assign accountable owners for each of G1-G12
2. **Begin cloud evaluation** — score AWS/GCP/Azure/on-prem against GFIN requirements
3. **Start legal review** — send evidence pack to counsel, request specific written answers
4. **Create infrastructure backlog** — from GFIN-IMP-001, create Jira/ticket for each provisioning step
5. **Track closure evidence** — against master readiness index (GFIN-RRI-001)

## Key Evidence References

| ID | Document |
|----|----------|
| GFIN-EVD-003 | Luna Phase Evidence Report |
| GFIN-GRR-001 | Gate Rehearsal Report (12 gates) |
| GFIN-IMP-001 | Infrastructure Mobilization Package (21.8KB) |
| GFIN-DRC-001 | Dependency Readiness Checklist |
| GFIN-HOC-001 | Production External Handoff Checklist |
| GFIN-CA-001 | Consistency Audit (99/100 PASS) |
| GFIN-RRI-001 | Release Readiness Index |
| LUNA-FINAL-CEA-004-SIGNOFF | Final Layer A sign-off |
