# GFIN — Privacy Model

**Version:** 1.0
**Date:** 2026-08-25
**Status:** DRAFT — REQUIRES LEGAL COUNSEL VALIDATION
**Source:** Constitution Articles XX, XLVII, Master Spec §46–48

---

## 1. Data Classification

Every sensitive object in the system must carry a classification. This is enforced at the data model level, not just at the UI level.

| Classification | Description | Access | Example |
|---------------|-------------|--------|---------|
| **PUBLIC** | Freely available public information | All users | Public DNS records, RDAP data |
| **COMMUNITY** | Shared within the GFIN community | Authenticated citizens | Aggregated fraud statistics, citizen reports (anonymized) |
| **RESTRICTED** | Investigative intelligence | Authorized investigators, analysts | Entity profiles, campaign analysis, infrastructure correlations |
| **LAW_ENFORCEMENT** | Police-specific intelligence | Authenticated police organizations | Police matches, cross-border requests, investigation links |
| **HIGHLY_RESTRICTED** | Case-specific sensitive data | Explicitly authorized individuals only | Active investigation details, named suspects, evidence vault items |

## 2. Required Metadata for Sensitive Objects

Every sensitive object must have:

- **owner** — the organization or user that created/controls the object
- **jurisdiction** — the legal jurisdiction the data belongs to
- **classification** — one of the five levels above
- **access_policy** — who can access this object, under what conditions
- **retention_policy** — how long the data is kept, and what happens on expiry
- **legal_basis** — the legal basis for processing (where required, e.g., GDPR)

## 3. Data Minimization

The platform follows data minimization as a default:

- Only necessary information is processed or transmitted
- AI receives only the information required for the specific task
- API responses include only fields the caller is authorized to see
- Search results are filtered by classification and access policy
- Cross-border sharing includes only permitted intelligence metadata
- Crawler stores only relevant observations, not full page content (unless evidence requires it)

## 4. Retention

Retention policies are configurable per data classification and per jurisdiction.

| Classification | Default Retention | Notes |
|---------------|-------------------|-------|
| PUBLIC | Indefinite | Public data has no retention constraint |
| COMMUNITY | 2 years | Configurable; citizen reports retained for trend analysis |
| RESTRICTED | 3 years | Configurable; intelligence observations |
| LAW_ENFORCEMENT | Per jurisdiction | Determined by law-enforcement data protection rules |
| HIGHLY_RESTRICTED | Per case | Retained for the duration of the case + statutory period |

**Note:** Retention periods are engineering defaults. Actual retention must comply with applicable legal requirements. Legal counsel must validate before production.

## 5. Data Residency

The architecture supports regional or country-specific deployment where required.

**Potential regions:** EU, UK, US, APAC, country-specific

**Principles:**
- Sensitive data remains in the required jurisdiction whenever policy requires it
- Federation protocol respects data residency constraints
- Cross-border information requests are subject to residency checks
- Data residency is a configurable policy, not hard-coded

## 6. Citizen Privacy

- Citizen reports can be submitted with optional anonymity
- Personal data of citizens (email, phone for alerts) is minimized and protected
- Citizen data is not shared with law enforcement without legal authorization
- Citizens can request data deletion where applicable (GDPR right to erasure)
- Aggregated statistics do not reveal individual reporter identity

## 7. AI Privacy

- Data sent to external AI providers is minimized and authorized
- Restricted police data is not sent to external AI providers unless: authorized, necessary, contractually permitted, technically protected, and compliant
- Local AI models are preferred for processing sensitive data
- AI request and response logs are maintained for audit
- AI providers are accessed through the Model Gateway, which enforces data classification routing

## 8. Deletion and Erasure

- Deletion policies are enforced per retention schedule
- Evidence subject to legal hold is not deleted
- Deletion is logged in the audit trail
- Where GDPR right to erasure applies, personal data is deleted unless a legal basis for retention exists
- Deletion of an entity does not delete evidence or audit trails that reference it (references are anonymized)

## 9. Compliance Layer

The platform includes a configurable compliance layer (not hard-coded to one jurisdiction):

- Data residency enforcement
- Retention policy engine
- Legal basis metadata
- Access governance
- Purpose limitation checks
- Audit trail
- Policy tests that demonstrate restricted data cannot cross unauthorized boundaries
