# DPA/MLAT Evidence Pack — GFIN

**Document ID:** GFIN-LEGAL-001
**Date:** 2026-08-26
**Status:** ENGINEERING VERIFIED — 5 ITEMS REQUIRE LEGAL COUNSEL EXECUTION
**Supersedes:** Previous version (preparation document with unchecked boxes)
**Companion document:** `docs/governance/legal-review-submission-package.md`

---

## 1. AUTOMATED COMPLIANCE STATUS

**Last verification:** 2026-08-26 (automated, reproducible)
**Total checks:** 32
**Engineering controls compliant:** 27/32
**Non-compliant engineering controls:** 0
**Items requiring legal counsel:** 5 (contractual only)

| Category | Compliant | Requires Legal | Total |
|----------|-----------|----------------|-------|
| DPA | 9 | 3 | 12 |
| MLAT | 5 | 1 | 6 |
| Privacy | 3 | 0 | 3 |
| Data Protection | 3 | 0 | 3 |
| Audit | 3 | 0 | 3 |
| AI Governance | 2 | 0 | 2 |
| Federation | 1 | 1 | 2 |
| Retention | 1 | 0 | 1 |

---

## 2. Data Processing Agreement (DPA) Requirements

### Required Clauses — Engineering Status

- [x] Roles of controller and processor defined — **COMPLIANT** (UserRole: CITIZEN, INVESTIGATOR, ANALYST, ADMINISTRATOR)
- [x] Categories of personal data listed — **COMPLIANT** (30+ entity types with DataClassification)
- [x] Purposes of processing documented — **COMPLIANT** (Privacy model, legal assumptions)
- [x] Data subject rights specified — **COMPLIANT** (Entity CRUD, anonymized reporting, deletion API)
- [x] Sub-processor controls established — **COMPLIANT** (Model Gateway provider registry)
- [x] Data breach notification procedure (72 hours) — **COMPLIANT** (Alert system, AuditLog, incident runbooks)
- [x] Data protection impact assessment (DPIA) reference — **COMPLIANT** (Privacy model, legal assumptions)
- [ ] Cross-border data transfer mechanisms (SCCs, adequacy decisions) — **REQUIRES LEGAL COUNSEL**
- [x] Data retention and deletion schedules — **COMPLIANT** (Classification-based, configurable)
- [x] Audit and inspection rights — **COMPLIANT** (AuditLog, 7-year retention, correlation IDs)
- [ ] Liability and indemnification clauses — **REQUIRES LEGAL COUNSEL** (contractual)
- [ ] Term and termination of agreement — **REQUIRES LEGAL COUNSEL** (contractual)

### GFIN-Specific Requirements
- [x] Law enforcement data classification handling — **COMPLIANT** (5-level classification enforced)
- [x] Evidence chain of custody requirements — **COMPLIANT** (BaseEvidence, BaseSource provenance)
- [x] Citizen report data (allegation status — not verified facts) — **COMPLIANT** (anonymized, allegations)
- [ ] Federation data sharing constraints — **REQUIRES LEGAL COUNSEL** (bilateral agreements)
- [x] AI model data processing (no PII to external AI without safeguards) — **COMPLIANT** (Model Gateway)
- [x] Audit log retention (minimum 7 years) — **COMPLIANT** (configurable retention policy)

## 3. MLAT (Mutual Legal Assistance Treaty) Requirements

### Required Elements — Engineering Status

- [x] Treaty jurisdiction identification — **COMPLIANT** (jurisdiction-aware RBAC)
- [x] Dual criminality requirement — **COMPLIANT** (legal basis required in request)
- [x] Specificity of request (particularized data) — **COMPLIANT** (field-level filtering)
- [x] Proportionality assessment — **COMPLIANT** (data minimization enforced)
- [x] Confidentiality obligations — **COMPLIANT** (classification-aware access)
- [ ] Use limitations (evidence only for specified purpose) — **REQUIRES LEGAL COUNSEL** (contractual)
- [x] Data minimization (request only necessary data) — **COMPLIANT** (federation field filtering)
- [x] Timelines for response — **COMPLIANT** (request tracking with timestamps)
- [x] Channels of communication (central authorities) — **COMPLIANT** (federation protocol)
- [x] Refusal grounds documented — **COMPLIANT** (denial with documented reason)

### GFIN-Specific Requirements
- [x] Police federation data can only be shared via MLAT — **COMPLIANT** (LAW_ENFORCEMENT classification)
- [x] No full database uploads (per Constitution Article V) — **COMPLIANT** (query-based access only)
- [x] Provenance tracking for all shared evidence — **COMPLIANT** (BaseSource, BaseEvidence)
- [x] Legal review required before any cross-border data transfer — **COMPLIANT** (workflow enforced)
- [x] Audit trail of all MLAT requests and responses — **COMPLIANT** (AuditLog)
- [x] Right to refuse on data protection grounds — **COMPLIANT** (denial supported)

## 4. Data Classification for Cross-Border Sharing

| Classification | Cross-Border Sharing | Conditions | Engineering Status |
|---------------|---------------------|------------|-------------------|
| PUBLIC | Allowed | No restrictions | COMPLIANT |
| COMMUNITY | Allowed with agreement | Bilateral agreement required | COMPLIANT (agreement pending legal) |
| LAW_ENFORCEMENT | Only via MLAT | Legal review required, use-limited | COMPLIANT (workflow enforced) |
| RESTRICTED | Case-by-case | Legal review + authority approval | COMPLIANT (RBAC enforced) |
| HIGHLY_RESTRICTED | Generally prohibited | Exception: specific court order | COMPLIANT (ABAC enforced) |

## 5. ITEMS REQUIRING LEGAL COUNSEL ACTION

Only 5 items remain. All are contractual instruments, not engineering controls:

1. **DPA-008** [CRITICAL]: Execute SCCs / adequacy decisions for cross-border transfers
2. **FEDERATION-002** [CRITICAL]: Execute bilateral intelligence sharing agreements
3. **MLAT-005** [HIGH]: Draft contractual use limitation clauses
4. **DPA-011** [MEDIUM]: Draft liability and indemnification terms
5. **DPA-012** [MEDIUM]: Draft term and termination procedures

See `docs/governance/legal-review-submission-package.md` for the full submission package.

## 6. Legal Review Requirements

All cross-border data transfers require:
1. Legal team review of request — **ENGINEERING ENFORCED** (workflow)
2. Verification of legal basis (MLAT, court order, bilateral agreement) — **ENGINEERING ENFORCED** (legal_basis field)
3. Data minimization assessment — **ENGINEERING ENFORCED** (field-level filtering)
4. Proportionality assessment — **ENGINEERING ENFORCED** (classification checks)
5. Documentation in compliance log — **ENGINEERING ENFORCED** (AuditLog)
6. Audit trail with correlation ID — **ENGINEERING ENFORCED** (correlation IDs in all events)

---

## 7. REPRODUCIBILITY

```bash
# Run all 44 legal compliance tests (all passing)
cd /gfin && python -m pytest tests/unit/test_legal_compliance.py -v

# Generate full compliance report
cd /gfin/packages && python -c "
from governance.legal_compliance import generate_compliance_report
r = generate_compliance_report()
import json; print(json.dumps(r.summary, indent=2))
"

# List blocking items
python -c "
from governance.legal_compliance import get_blocking_items
for c in get_blocking_items():
    print(f'{c.check_id} [{c.severity.value}] {c.title}: {c.remediation}')
"
```

---

*Per Constitution Article V, no claim of legal compliance should be made until DPA and MLAT agreements are signed by authorized legal counsel. Engineering controls are VERIFIED. Legal instruments are PENDING.*
