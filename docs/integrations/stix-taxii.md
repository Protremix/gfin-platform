# GFIN ↔ STIX 2.x / TAXII 2.x Integration Specification

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

This document defines how GFIN integrates with STIX 2.x (Structured Threat Information Expression) and TAXII 2.x (Trusted Automated Exchange of Intelligence Information) as interoperability standards — not as GFIN's internal data model.

## Critical Principle

**STIX is an interoperability format, NOT the GFIN canonical data model.**

GFIN's data model (defined in `packages/schemas/`) remains authoritative. STIX is used for:
- Inbound ingestion from external CTI sources
- Outbound sharing with authorized consumers
- Interoperability with MISP, OpenCTI, and TAXII servers

---

## STIX 2.x Evaluation

### Official Sources

| Resource | URL |
|----------|-----|
| STIX 2.1 Specification | https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1-part-1-stix-common/specdoc/ |
| Official Python Library | https://github.com/oasis-open/cti-python-stix2 |
| TAXII 2.x Specification | https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1-part-1-restful-messaging/specdoc/ |
| TAXII Python Client | https://github.com/oasis-open/cti-taxii-client |
| STIX Validator | https://github.com/oasis-open/cti-stix-validator |

### License

- STIX and TAXII specifications: OASIS standards, freely implementable
- cti-python-stix2 library: BSD 3-Clause license
- cti-taxii-client library: BSD 3-Clause license
- **Finding:** No licensing obstacle to integration. BSD permits commercial use with attribution.

### STIX 2.x Object Types Evaluated

| STIX Object | Relevance to GFIN | Mapping Status |
|-------------|-------------------|----------------|
| Indicator | HIGH — fraud indicators (phishing URLs, malicious domains) | MAPPED |
| Observed Data | HIGH — entity observations (DNS lookups, cert observations) | MAPPED |
| Identity | MEDIUM — organizations, persons, sources | MAPPED |
| Location | MEDIUM — countries, regions for jurisdiction | MAPPED |
| Infrastructure | MEDIUM — domain infrastructure, hosting clusters | MAPPED |
| Malware | LOW — not primary focus of fraud intelligence | PARTIAL |
| Report | HIGH — fraud reports, case summaries | MAPPED |
| Relationship | HIGH — entity relationships | MAPPED |
| Sighting | HIGH — observation confirmations | MAPPED |
| Attack Pattern | LOW — fraud techniques (could map to fraud patterns) | PARTIAL |
| Course of Action | LOW — mitigation steps | NOT MAPPED |
| Threat Actor | LOW — not primary focus | NOT MAPPED |
| Intrusion Set | LOW — not primary focus | NOT MAPPED |
| Campaign | MEDIUM — fraud campaigns | MAPPED (with caveats) |
| Tool | LOW — not primary focus | NOT MAPPED |
| Vulnerability | LOW — not primary focus | NOT MAPPED |
| Note | MEDIUM — analyst notes on investigations | MAPPED |
| Opinion | LOW — not primary focus | NOT MAPPED |
| Language Content | MEDIUM — multilingual support | NOT MAPPED |

---

## GFIN ↔ STIX Mapping Table

### Entity Mappings

| GFIN Entity | STIX Object | Transformation Rules | Information Loss | Provenance |
|-------------|------------|---------------------|------------------|------------|
| Person | Identity (type: "individual") | name → name, emails → contact_information | GFIN's reporter_id has no STIX equivalent | Map to Identity.created_by_ref |
| Organization | Identity (type: "organization") | name → name, domain → contact_information | GFIN's organization_id has no direct STIX equivalent | Map to Identity.created_by_ref |
| Phone | Custom Observable (type: "phone-number") | phone → value | GFIN phone normalization (E.164) stored in custom property | Source retained in custom x-gfin-source |
| Email | Email Address Observable | email → value | None — direct mapping | Source → custom property |
| Domain | Domain Name Observable | domain → value | GFIN domain lifecycle (registration, expiry) not in STIX | Registration data → custom x-gfin-registration |
| URL | URL Observable | url → value | None — direct mapping | Source → custom property |
| IP | IPv4/IPv6 Address Observable | ip → value, version → IP version | GFIN IP history (changes over time) not natively in STIX | History → Observed Data objects |
| ASN | Custom Observable (type: "asn") | asn → number, provider → name | GFIN abuse contacts not in STIX | Custom x-gfin-abuse-contact |
| Certificate | X509 Certificate Observable | fingerprint → hashes, issuer → issuer, subject → subject, not_before → validity_not_before, not_after → validity_not_after | GFIN certificate timeline (chronological observations) requires multiple Observed Data objects | Timeline → Observed Data with first_seen/last_seen |
| Crypto Wallet | Custom Observable (type: "cryptocurrency-wallet") | address → value, currency → currency | GFIN transaction graph not in STIX | Custom x-gfin-transaction-refs |
| Campaign | Campaign | name → name, fraud_type → custom, status → custom | GFIN campaign status (DRAFT/ACTIVE/CLOSED) not in STIX | Custom x-gfin-campaign-status |
| Report | Report | title → name, description → description, category → labels | GFIN report status, triage priority, score not in STIX standard | Custom properties for GFIN-specific fields |
| Case | Report (type: "case") or custom | case_id → custom, status → custom | GFIN case model (investigation workflow) not natively in STIX | Custom x-gfin-case-* properties |

### Relationship Mappings

| GFIN Relationship | STIX Relationship Type | Transformation | Information Loss |
|-------------------|----------------------|----------------|------------------|
| OWNS | "owns" (custom) | Direct mapping | None |
| USES | "uses" | Direct mapping | None |
| HOSTED_ON | "communicates-with" or custom | Maps to "hosted-on" custom | GFIN temporal data (when hosted) lost |
| RESOLVES_TO | "resolves-to" (custom) | Direct mapping | None |
| REDIRECTS_TO | "redirects-to" (custom) | Direct mapping | None |
| REGISTERED_WITH | "registered-with" (custom) | Custom relationship type | GFIN registrar details lost |
| SHARES_CERTIFICATE | "related-to" | Generic mapping | Specificity lost (shares cert vs generic related) |
| SHARES_INFRASTRUCTURE | "related-to" | Generic mapping | Specificity lost |
| REFERENCES | "refers-to" (custom) | Custom relationship type | None |
| CONTACTED | "communicates-with" | Maps to STIX standard | Directionality may differ |
| REPORTED_BY | "reported-by" (custom) | Custom relationship type | None |
| RELATED_TO | "related-to" | Direct mapping | None |
| MATCHES | "indicates" (if indicator) | Maps to indicator relationship | GFIN match confidence not in STIX standard |
| PART_OF_CAMPAIGN | "part-of" (custom) | Custom relationship type | GFIN campaign membership metadata lost |
| PAYMENT_TO | "transfers-to" (custom) | Custom relationship type | Transaction amount/hash lost |
| SIMILAR_TO | "related-to" | Generic mapping | Similarity score lost |

### Sighting/Observation Mappings

| GFIN Concept | STIX Object | Transformation | Information Loss |
|-------------|------------|----------------|------------------|
| Entity Observation | Observed Data | entity → object, timestamp → first_observed/last_observed, count → number_observed | GFIN observation metadata (source classification) → custom |
| Evidence | Report or Observed Data | evidence → custom property on observed data | GFIN evidence chain-of-custody not in STIX |
| Match Result | Sighting | entity → sighting_of_ref, jurisdiction → custom, confidence → custom | GFIN jurisdiction-based matching not in STIX standard |

### GFIN Fields NOT Representable in STIX 2.x

| GFIN Field | Why STIX Can't Represent It | Solution |
|------------|---------------------------|----------|
| Data Classification (PUBLIC → HIGHLY_RESTRICTED) | STIX has marking definitions but not GFIN's 5-level hierarchy | Custom `x-gfin-classification` property |
| Jurisdiction (ISO 3166-1 alpha-2) | STIX Location has country/region but not jurisdiction semantics | Custom `x-gfin-jurisdiction` property |
| Source Restrictions (license/ToS) | STIX has no concept of source-specific data usage restrictions | Custom `x-gfin-source-restrictions` property |
| Organization Isolation | STIX has no multi-tenant isolation model | Custom `x-gfin-organization-id` property |
| Triage Priority | STIX has no triage/priority concept for reports | Custom `x-gfin-triage-priority` property |
| Report Score | STIX has no numeric scoring for reports | Custom `x-gfin-score` property |
| Match Confidence | STIX confidence is 0-100 but GFIN uses categorical (LOW/MEDIUM/HIGH) | Map categorical to numeric + custom |
| Evidence Chain-of-Custody | STIX has no chain-of-custody model | Custom `x-gfin-evidence-ref` property |
| Audit Trail | STIX has no audit trail for individual objects | GFIN maintains separate audit (not exported via STIX) |

---

## TAXII 2.x Gateway Design

### Inbound TAXII Flow

```text
External Police / CTI Organization
        │
        ▼
TAXII 2.x Server (external)
        │
        ▼
GFIN TAXII Gateway
    │
    ├── Authentication (API key / certificate)
    ├── Authorization (is this TAXII client permitted?)
    ├── Validation Layer (STIX schema validation)
    ├── Classification Filter (reject HIGHLY_RESTRICTED from external)
    ├── Jurisdiction Tagging
    └── Normalization (STIX → GFIN canonical)
    │
    ▼
GFIN Intelligence Graph
```

### Outbound TAXII Flow

```text
GFIN Intelligence
    │
    ▼
Policy Filter (organization, user, role)
    │
    ▼
Classification Check (PUBLIC / COMMUNITY only for external)
    │
    ▼
Jurisdiction Check (target jurisdiction permitted?)
    │
    ▼
Source Restriction Check (original source permits re-sharing?)
    │
    ▼
STIX Normalization (GFIN canonical → STIX 2.x)
    │
    ▼
TAXII Collection (filtered, authorized)
    │
    ▼
Authorized Consumer (authenticated TAXII client)
```

### Outbound Export Policy

Every outbound export MUST pass:

1. **Authorization** — Is the consumer authorized to receive this data?
2. **Organization policy** — Does the data owner's policy permit sharing?
3. **Jurisdiction** — Is sharing permitted for the target jurisdiction?
4. **Classification** — Only PUBLIC and COMMUNITY data may be exported externally
5. **Source restrictions** — Does the original source permit re-sharing?
6. **Sharing policy** — Bilateral or multilateral agreement required

**CRITICAL:** Never expose restricted police intelligence merely because it is technically exportable.

---

## POC: STIX Import/Export

### POC Status: IMPLEMENTED (Layer A)

A minimal POC has been implemented demonstrating the STIX import/export path:

- **Import:** Parse STIX 2.x bundle → map to GFIN canonical entities → store as observations
- **Export:** GFIN entities → map to STIX 2.x objects → generate STIX bundle
- **Library:** `stix2` Python library (BSD-3-Clause)

### POC Files

```
packages/common/stix_adapter.py     — STIX import/export adapter (Layer A)
tests/unit/test_stix_adapter.py     — Unit tests for STIX mapping
```

### POC Result: PASSING

The POC demonstrates:
1. GFIN Email entity → STIX Email Address Observable → round-trip back to GFIN Email
2. GFIN Domain entity → STIX Domain Name Observable → round-trip
3. GFIN IP entity → STIX IPv4 Address Observable → round-trip
4. GFIN Report → STIX Report → round-trip with custom properties preserved
5. GFIN Relationship → STIX Relationship → round-trip
6. GFIN custom properties (x-gfin-classification, x-gfin-jurisdiction) preserved

---

## Recommendation

| Technology | Status | Rationale |
|-----------|--------|-----------|
| STIX 2.x | **USE** | Essential interoperability standard. Use as import/export format, not canonical model. |
| TAXII 2.x | **INTEGRATE** | Standardized exchange mechanism for police/CTI sharing. Build GFIN TAXII Gateway. |

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- TAXII 2.x server implementation (or use OpenCTI's TAXII server)
- Certificate-based authentication for TAXII clients
- Persistent STIX bundle storage
- Kafka event stream for STIX/TAXII processing pipeline
- STIX validation service (cti-stix-validator)

## Open Issues

1. **Custom property namespace:** Need to register `x-gfin-*` custom property namespace formally
2. **STIX patterning:** GFIN indicators need conversion to STIX patterning language for Indicator objects
3. **TAXII server:** Need to select TAXII 2.x server implementation (OpenCTI built-in, or standalone)
4. **Police federation:** TAXII sharing agreements need legal review (see Legal Review Required section)
5. **STIX 2.1 vs 2.0:** Need to decide which version to target (2.1 recommended for maturity)
