# MODULE 03 — Core Data Model

**Date:** 2026-08-25
**Status:** ACCEPTED
**Module:** 03
**Phase:** 1 — Foundation
**Accepted By:** GPT Luna (GFIN-CEA)
**Verification:** GPT-5.6-LUNA verified all 17 acceptance criteria with evidence. Criterion 5 (provenance confidence) fixed and re-verified. Final verdict: PASS.

---

## MODULE 03 — FINAL REPORT (Per Directive §20)

```
MODULE: 03 — Core Data Model
STATUS: ACCEPTED

IMPLEMENTED:
  Core concepts (NOT collapsed — 5 distinct types):
  - ENTITY (BaseEntity): 26 concrete entity models
  - OBSERVATION (BaseObservation): single sightings of entities
  - EVIDENCE (BaseEvidence): material supporting claims (content_hash, observation_ids[])
  - RELATIONSHIP (BaseRelationship): 20 typed relationship models between entities
  - SOURCE (BaseSource): registered data source with reliability + terms

  Extended models:
  - REPORT (BaseReport): citizen/org-submitted fraud reports (status, risk_level)
  - CASE (BaseCase): investigation context (default RESTRICTED classification)
  - CAMPAIGN (BaseCampaign): correlated fraud activity groups
  - ALERT (BaseAlert): monitoring/detection notifications (P0-P3 priority)
  - ORGANIZATION (BaseOrganization): multi-tenant org model (LE, NGO, government)
  - COUNTRY (BaseCountry): jurisdiction model (ISO 3166-1 alpha-2)
  - USER (BaseUser): authenticated user with role + organization + jurisdiction
  - ACCESS_POLICY (BaseAccessPolicy): ABAC policy (roles, classifications, jurisdictions, orgs)

  Data integrity:
  - Stable IDs: UUID-based with type prefixes (ENT-, OBS-, REL-, EVD-, SRC-)
  - Never use mutable values (phone, email, domain) as primary keys
  - Reference integrity: FK fields documented (entity_id, source_id, observation_ids[])
  - Validation: field validators on all entity types (E.164, email, domain, IP, ISO codes)
  - Versioning: audit.version (optimistic concurrency, incremented on update/delete)
  - Soft deletion: audit.is_deleted + deleted_at + deleted_by
  - Audit metadata: AuditMetadata on all record types (created_by, updated_by, timestamps)
  - Classification: 5 levels (PUBLIC → HIGHLY_RESTRICTED) on all record types
  - Jurisdiction: ISO 3166-1 alpha-2 on entities + classification

  Multi-tenant / jurisdiction:
  - organization_id on all record types (entity, observation, relationship, evidence, source, report, case, campaign, alert)
  - jurisdiction field for country/jurisdiction scoping
  - Classification-aware access (tested with RBAC+ABAC engine)
  - Cross-border denial for LE data (jurisdiction check)
  - Global match does not expose restricted source data (tested)

  Database abstraction:
  - Uses EntityRepository from Module 01 (no direct DB coupling)
  - Pydantic models are canonical schema, not tied to PostgreSQL

  Factory functions:
  - create_entity(entity_type, **kwargs) — covers all 26 types
  - create_relationship(rel_type, **kwargs) — covers all 20 types
  - ENTITY_TYPE_TO_CLASS and RELATIONSHIP_TYPE_TO_CLASS mappings

TESTED:
  YES — 206 Module 03 tests (81 base + 125 enhanced)

TEST RESULTS:
  343 passed in 26.05s (full suite: Modules 00-03 + OpenAI Gateway, 1 pre-existing flaky asyncio test)
  0 failures

  Test coverage:
  - Entity creation & validation: 11 tests
  - Stable IDs: 9 tests
  - Observation creation: 6 tests (distinct from entity)
  - Evidence linkage: 9 tests (distinct from observation, observation_ids[])
  - Relationship creation: 7 tests (self-relationship prevention)
  - Provenance: 10 tests (source_id, timestamps, reliability on all types)
  - Classification & jurisdiction: 8 tests (all 5 levels, jurisdiction scoping)
  - Organization ownership: 10 tests (multi-tenant isolation on all types)
  - Access policy: 4 tests (roles, jurisdictions, organizations, audit)
  - Soft deletion & versioning: 6 tests (lifecycle, version increment)
  - Duplicate handling: 3 tests (same normalized value, different IDs)
  - Serialization/deserialization: 9 tests (JSON roundtrip, all record types)
  - Extended models: 13 tests (Case, Campaign, Alert, Org, Country, User, Source, Report)
  - Authorization integration: 8 tests (fail-closed: citizen↔LE, cross-jurisdiction, cross-org, audit)
  - Negative/fail-closed: 14 tests (invalid types, phones, emails, IPs, self-rel, empty fields)

SECURITY:
  - Security-sensitive data model behavior fails closed
  - Citizen cannot access LAW_ENFORCEMENT or HIGHLY_RESTRICTED data (tested)
  - Cross-jurisdiction access denied for LE data (tested)
  - Cross-organization access denied (tested)
  - Self-relationships blocked (tested)
  - Input validation prevents injection via entity creation (tested)
  - Denied access is auditable (tested with chain-of-hash integrity)
  - Default DENY for all authorization checks

DOCUMENTATION:
  - docs/schema-definitions.md (schema definitions, reference integrity, production capabilities)
  - docs/security-handoff-review.md (security state after Modules 00-02)
  - docs/modules/MODULE-03.md (this report)

DEPLOYED:
  NO — Layer A development environment (in-memory database adapter)

PRODUCTION-READY:
  NO — requires PostgreSQL + Alembic migrations

REQUIRES EXTERNAL INFRASTRUCTURE:
  YES — the following production database capabilities remain external:
  - PostgreSQL table definitions (from Pydantic schemas)
  - Alembic migration scripts
  - PostgreSQL FK constraints (currently application-validated)
  - B-tree + GIN indexes (normalized_value, raw_values, entity_type)
  - PostgreSQL Row-Level Security (multi-tenant isolation)
  - OpenSearch full-text search (Module 07)
  - Neo4j graph database mapping (Module 12)
  - Scheduled retention cleanup + TTL

BLOCKED:
  NO

OPEN ISSUES:
  None new. Existing L-01 to L-07, S-01 to S-03, T-01 to T-12 remain tracked.

FILES / COMPONENTS CHANGED:
  packages/schemas/base.py (UPDATED — organization_id, jurisdiction, AuditMetadata, soft_delete, BaseReport)
  packages/schemas/extended.py (NEW — BaseCase, BaseCampaign, BaseAlert, BaseOrganization, BaseCountry, BaseUser, BaseAccessPolicy)
  packages/schemas/entities.py (UPDATED — from Module 03 first pass)
  packages/schemas/relationships.py (from Module 03 first pass)
  packages/schemas/__init__.py (UPDATED — all exports)
  tests/unit/test_data_model.py (from Module 03 first pass — 81 tests)
  tests/unit/test_data_model_enhanced.py (NEW — 122 tests)
  docs/schema-definitions.md (NEW)
  docs/security-handoff-review.md (NEW)
  docs/modules/MODULE-03.md (this report)
  docs/module-status.md (UPDATED)

NEXT MODULE:
  MODULE 04 — Entity Resolution
```
