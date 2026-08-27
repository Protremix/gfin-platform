# GFIN Pilot Vertical Slice — Definition & Acceptance Criteria

**Date:** 2026-08-26
**Status:** PROPOSED — Awaiting owner approval
**Per Luna Assessment:** "Do not productionize all 40 modules in parallel. Prove one complete slice first."

---

## 1. Pilot Workflow: Citizen-to-Police Intelligence Chain

```
CITIZEN submits fraud report
    │
    ▼
[Module 13: Citizen Platform] — entity check (PUBLIC-only), report submission (UNVERIFIED)
    │
    ▼
[Module 14: Fraud Reporting] — triage (priority, spam, dedup), enrichment, scoring
    │
    ▼
[Module 15: Fraud Detection] — signal analysis, pattern matching, threshold detection
    │
    ▼
[Module 16: Campaign Engine] — campaign clustering, linking, scoring
    │
    ▼
[Module 18: Alert Engine] — routing, escalation, notification dispatch
    │
    ▼
[Module 23: Police API] — query by authorized officer, audit trail
    │
    ▼
[Module 25: Global Matching] — cross-border entity match check
    │
    ▼
[Module 03: Core Data Model] — entity persistence throughout
```

**Modules exercised:** 03, 13, 14, 15, 16, 18, 23, 25 (8 modules)
**Additional modules touched:** 02 (Security/Identity), 06 (Evidence Vault), 09 (Infrastructure Intelligence)

---

## 2. Pilot Scope

### In Scope
- One partner organization (law enforcement or fraud unit)
- Citizen fraud report submission (web form)
- Automatic triage, scoring, detection
- Campaign detection and linking
- Alert routing to partner
- Police API query by authorized officers
- Cross-border entity match check (read-only)
- Audit trail for all operations
- Multi-tenant isolation (partner data isolated)

### Out of Scope (for initial pilot)
- Web discovery / crawling
- Full blockchain tracing
- Multilingual translation (English only)
- Advanced analytics dashboards
- Federation (single-node operation)
- AI Investigation Orchestrator (manual investigation only)
- Disaster recovery automation (manual recovery)
- Load testing at scale

### Success Metrics
- Citizen can submit a fraud report end-to-end
- Report is automatically triaged and scored within 60 seconds
- Fraud detection produces signals and risk scores
- Campaign engine links related reports
- Alerts route to the correct partner channel
- Police officers can query reports and entities via API
- All operations have audit trail entries
- Partner data is isolated from other tenants
- System recovers from process restart without data loss

---

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Citizen report submission works with PostgreSQL persistence | Integration test |
| 2 | Triage/scoring runs end-to-end with real DB | Integration test |
| 3 | Fraud detection produces signals from persisted data | Integration test |
| 4 | Campaign engine links reports stored in DB | Integration test |
| 5 | Alert routes to partner notification channel | Integration test |
| 6 | Police API returns persisted reports with RBAC | Integration test |
| 7 | Global matching checks cross-border entities | Integration test |
| 8 | Audit trail has entries for every operation | Integration test |
| 9 | Cross-tenant access is blocked | Negative test |
| 10 | Process restart preserves all data | Integration test |
| 11 | API endpoints respond with correct schemas | Contract test |
| 12 | Health/readiness endpoints work | Integration test |

---

## 4. Data Classes Required for Pilot

| Entity | Fields | Source Module |
|--------|--------|---------------|
| Person | name, email, phone, address | 03 |
| Phone | number, carrier, country | 03 |
| Domain | name, registrar, status | 03/10 |
| URL | url, domain, status | 03 |
| IPAddress | ip, asn, country | 03/09 |
| FraudReport | report_type, description, entity_refs, status, priority, score | 13/14 |
| Campaign | name, status, score, linked_reports | 16 |
| Alert | type, priority, channel, status | 18 |
| AuditEntry | action, actor, target, timestamp | 02 |
| User | email, role, org_id | 02 |

---

## 5. Infrastructure Requirements (Minimum)

| Component | Specification | Status |
|-----------|--------------|--------|
| PostgreSQL 15+ | 2-4 vCPU, 8-16 GB RAM, managed, PITR | REQUIRES EXTERNAL INFRASTRUCTURE |
| Docker | Container for API + worker | REQUIRES EXTERNAL INFRASTRUCTURE |
| TLS | All connections encrypted | REQUIRES EXTERNAL INFRASTRUCTURE |
| Object Storage | Evidence files (S3-compatible) | REQUIRES EXTERNAL INFRASTRUCTURE |
| CI/CD | Automated test + migration pipeline | REQUIRES EXTERNAL INFRASTRUCTURE |
