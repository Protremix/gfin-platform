# MODULE 33 — Compliance

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 33 implements the Compliance framework — data classification
enforcement, privacy controls, retention policies, and audit compliance
per the GFIN governance model. Per Privacy Model: data classification
levels (PUBLIC, COMMUNITY, LAW_ENFORCEMENT, RESTRICTED, HIGHLY_RESTRICTED)
govern access and sharing.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP)
- `ComplianceService` — main service for compliance checks and enforcement
- `DataClassification` — 5 levels (PUBLIC → HIGHLY_RESTRICTED)
- `RetentionPolicy` — data retention rules by classification
- `ComplianceCheck` — check data access against classification rules
- `ComplianceViolation` — record of a compliance violation
- `PrivacyFilter` — filter data based on classification and access level

### Layer B (Production)
- Legal framework integration per jurisdiction
- Automated data retention enforcement
- Compliance reporting
- REQUIRES EXTERNAL INFRASTRUCTURE

---

## 3. Acceptance Criteria

1. DataClassification defines 5 levels with access rules
2. ComplianceService checks data access against classification
3. RetentionPolicy defines retention periods by classification
4. ComplianceViolation recorded on access violations
5. PrivacyFilter removes restricted fields based on accessor's clearance
6. All compliance checks are logged
7. Violations can be queried and tracked

---

## 4. Dependencies

- Module 03 (Core Data Model) — entity classification
- Module 01 (Governance) — privacy model, data classifications
