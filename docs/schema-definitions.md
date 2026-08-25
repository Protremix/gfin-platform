# GFIN Schema Definitions — Module 03

**Date:** 2026-08-25
**Status:** DOCUMENTED
**Module:** 03

---

## Overview

GFIN data model uses Pydantic v2 models as the canonical schema definition.
Production PostgreSQL table definitions will be generated from these schemas.
Currently uses the database abstraction layer from Module 01 (in-memory dev adapter).

**REQUIRES EXTERNAL INFRASTRUCTURE:** PostgreSQL + Alembic migrations for production.

---

## Core Concepts (Mandatory Distinction)

| Concept | Class | Description |
|---------|-------|-------------|
| ENTITY | BaseEntity | Something being tracked (phone, domain, person) |
| OBSERVATION | BaseObservation | Something observed about an entity (a sighting) |
| EVIDENCE | BaseEvidence | Material supporting an observation/claim (screenshot) |
| RELATIONSHIP | BaseRelationship | A connection between entities (person owns phone) |
| SOURCE | BaseSource | Where the information originated (citizen, police feed) |
| REPORT | BaseReport | User/organization-submitted fraud report |
| CASE | BaseCase | Investigation context grouping entities/evidence |
| CAMPAIGN | BaseCampaign | Correlated set of potentially related fraud activity |
| ALERT | BaseAlert | Notification triggered by monitoring/detection |
| ORGANIZATION | BaseOrganization | LE agency, NGO, or partner (multi-tenant) |
| COUNTRY | BaseCountry | Geographic/jurisdiction entity |
| USER | BaseUser | Authenticated platform participant with role |
| ACCESS_POLICY | BaseAccessPolicy | ABAC policy definition |

**These are NOT collapsed into one generic record.** Each is a distinct Pydantic model.

---

## Schema Inheritance

```
BaseModel (Pydantic)
├── Classification (embedded)
├── Provenance (embedded)
├── AuditMetadata (embedded)
├── BaseEntity → 26 concrete entity types
├── BaseObservation
├── BaseRelationship → 20 typed relationship models
├── BaseEvidence
├── BaseSource
├── BaseReport
├── BaseCase
├── BaseCampaign
├── BaseAlert
├── BaseOrganization
├── BaseCountry
├── BaseUser
└── BaseAccessPolicy
```

---

## Stable IDs

All records use stable, immutable UUID-based IDs with type prefixes:

| Type | Prefix | Format |
|------|--------|--------|
| Entity | ENT- | ENT-{8 hex chars} |
| Observation | OBS- | OBS-{8 hex chars} |
| Relationship | REL- | REL-{8 hex chars} |
| Evidence | EVD- | EVD-{8 hex chars} |
| Source | SRC- | SRC-{8 hex chars} |
| Report | RPT- | RPT-{8 hex chars} |
| Organization | ORG- | ORG-{8 hex chars} |
| User | USR- | USR-{8 hex chars} |
| Policy | POL- | POL-{8 hex chars} |
| Country | CTRY- | CTRY-{8 hex chars} |

**Never** use mutable user-facing values (phone, email, domain) as primary IDs.

---

## Multi-Tenant / Jurisdiction Fields

Every record type includes:

| Field | Type | Purpose |
|-------|------|---------|
| organization_id | str \| None | Organization isolation (multi-tenant) |
| jurisdiction | str \| None | ISO 3166-1 alpha-2 jurisdiction scoping |
| classification | Classification | 5-level data classification (PUBLIC → HIGHLY_RESTRICTED) |

---

## Lifecycle (AuditMetadata)

Every record includes:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| created_by | str \| None | None | User ID of creator |
| created_at | datetime | utc_now() | Creation timestamp |
| updated_by | str \| None | None | User ID of last updater |
| updated_at | datetime \| None | None | Last update timestamp |
| version | int | 1 | Optimistic concurrency version |
| is_deleted | bool | False | Soft deletion flag |
| deleted_at | datetime \| None | None | Deletion timestamp |
| deleted_by | str \| None | None | User ID of deleter |

Methods: `soft_delete(deleted_by)`, `update_audit(updated_by)`

---

## Provenance Fields (Provenance model)

| Field | Type | Purpose |
|-------|------|---------|
| source_id | str | FK → BaseSource.id |
| source_type | str | Type of source |
| acquisition_method | str | How data was obtained |
| timestamp | datetime | When provenance was recorded |
| observation_timestamp | datetime \| None | When the observation was made |
| retrieval_timestamp | datetime \| None | When data was retrieved |
| reliability | str | Source reliability (HIGH/MEDIUM/LOW/UNKNOWN) |
| reference | str \| None | External reference |
| terms_classification | str \| None | Source terms classification |

---

## Reference Integrity

The data model uses string-based foreign key references:

| From | To | Field |
|------|-----|-------|
| BaseObservation | BaseEntity | entity_id |
| BaseObservation | BaseSource | source_id |
| BaseRelationship | BaseEntity | from_entity_id |
| BaseRelationship | BaseEntity | to_entity_id |
| BaseRelationship | BaseSource | source_id |
| BaseEvidence | BaseSource | source_id |
| BaseEvidence | BaseObservation | observation_ids[] |
| BaseReport | BaseEntity | related_entity_ids[] |
| BaseReport | BaseEvidence | related_evidence_ids[] |
| BaseCase | BaseEntity | related_entity_ids[] |
| BaseCase | BaseReport | related_report_ids[] |

**Production PostgreSQL:** These will become proper FK constraints with indexes.
**Current (Layer A):** Validated in application logic (database adapter).

---

## 26 Concrete Entity Types

| # | Entity | Key Fields | Validation |
|---|--------|-----------|------------|
| 1 | Person | full_name, aliases, nationality | Name required, ISO 3166-1 |
| 2 | Organization | name, registration_number, country | Name required |
| 3 | Phone | e164, country_code, carrier | E.164 normalization |
| 4 | Email | email, local_part, domain_part | RFC email format |
| 5 | Domain | domain, tld, registrar | DNS format, lowercase |
| 6 | URL | url, scheme, domain, path | http(s) required |
| 7 | IP | ip, ip_version, asn, country | IPv4/IPv6 via ipaddress |
| 8 | ASN | asn_number, holder_name | Range 1-4294967295 |
| 9 | Network | cidr, network_type, country | CIDR via ipaddress |
| 10 | DNS Record | record_type, record_value, domain | Type whitelist |
| 11 | Certificate | serial, issuer, fingerprint | SHA-256 hex |
| 12 | Website | title, content_hash, technologies | — |
| 13 | Telegram | username, phone, user_id | Username 5-32 chars |
| 14 | Social Account | platform, username, user_id | Platform required |
| 15 | Crypto Wallet | blockchain, address, balance | Blockchain required |
| 16 | Transaction | tx_hash, from/to, amount | — |
| 17 | Payment ID | payment_type, identifier, processor | Type required |
| 18 | Document | doc_type, content_hash, language | — |
| 19 | Image | content_hash, width, height, format | — |
| 20 | Report | status, category, risk_level | ReportStatus enum |
| 21 | Case | case_number, status, jurisdiction | Status enum |
| 22 | Campaign | name, status, severity, fraud_type | Status enum |
| 23 | Infra Cluster | cluster_name, type, members | — |
| 24 | Fraud Pattern | pattern_type, indicators, ttp_refs | — |
| 25 | Alert | alert_type, priority, status, entity_ids | Status enum |
| 26 | Country | iso_code, name, region, is_eu | ISO 3166-1 alpha-2 |

---

## 20 Relationship Types

OWNS, USES, HOSTED_ON, RESOLVES_TO, REDIRECTS_TO, REGISTERED_WITH,
SHARES_CERTIFICATE, SHARES_INFRASTRUCTURE, REFERENCES, CONTACTED,
REPORTED_BY, RELATED_TO, MATCHES, PART_OF_CAMPAIGN, OBSERVED_IN_CASE,
OBSERVED_IN_COUNTRY, PAYMENT_TO, SIMILAR_TO, MONITORED_BY

All relationships:
- Require source_id (provenance)
- Prevent self-relationships
- Carry confidence + classification
- Support observation period timestamps

---

## Production Database Capabilities (REQUIRES EXTERNAL INFRASTRUCTURE)

| Capability | Layer A | Layer B (Production) |
|-----------|---------|---------------------|
| Storage | In-memory dict | PostgreSQL tables |
| Migrations | N/A | Alembic migration scripts |
| Foreign keys | Application validation | PostgreSQL FK constraints |
| Indexes | N/A | B-tree on normalized_value, GIN on raw_values |
| Full-text search | N/A | OpenSearch (Module 07) |
| Graph queries | BFS in memory | Neo4j (Module 12) |
| Soft delete | audit.is_deleted flag | PostgreSQL DELETE policy + partial index |
| Optimistic concurrency | audit.version | PostgreSQL version column + check |
| JSON metadata | dict field | PostgreSQL JSONB column |
| Multi-tenant isolation | Application filter | PostgreSQL RLS (Row-Level Security) |
| Retention lifecycle | retention_policy field | Scheduled cleanup + TTL |

---

## Test Coverage Summary

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_data_model.py | 81 | Entity models, relationships, factory, basic integration |
| test_data_model_enhanced.py | 122 | Provenance, classification, jurisdiction, org ownership, access policy, soft deletion, versioning, serialization, auth integration, negative/fail-closed |
| **Total Module 03** | **203** | All acceptance criteria |
