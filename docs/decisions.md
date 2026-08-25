# GFIN — Decisions Log

**Last Updated:** 2026-08-25

---

## Decision Records

### D-01: Modular development per GFIN Constitution
**Date:** 2026-08-25
**Status:** APPROVED
**Context:** The project requires a structured, verifiable development approach.
**Decision:** Follow the 40-module development plan from the Master Engineering Specification, with each module requiring acceptance before proceeding.
**Alternatives:** Agile/incremental without formal module gates — rejected as insufficient for evidence integrity requirements.
**Consequences:** Development is slower but each module is independently verifiable.

### D-02: Build via abstraction layers for infrastructure portability
**Date:** 2026-08-25
**Status:** APPROVED
**Context:** Development occurs in a Base44 workspace that cannot deploy Kubernetes, Kafka, Neo4j, or other production infrastructure.
**Decision:** All infrastructure components (database, events, search, storage, AI, auth, cache, graph) are accessed through abstraction interfaces. Base44 implementations serve as the initial adapter. External cloud infrastructure can be added later by implementing new adapters without rewriting core application logic.
**Alternatives:**
1. Wait for external infrastructure before starting — rejected (blocks all progress).
2. Build directly on Base44 without abstractions — rejected (creates tight coupling, hard to migrate).
3. Build only documentation, no code — rejected (project owner requested implementation).
**Consequences:** Slight overhead from abstraction layers. All interfaces must be designed upfront. Mock/staging adapters are used where external services are unavailable.
**ADR:** See `/docs/adr/ADR-001-abstraction-layers.md`

### D-03: OpenAI as primary AI provider through Model Gateway (not hard-coded)
**Date:** 2026-08-25
**Status:** APPROVED
**Context:** Project owner selected OpenAI as primary AI provider, but Constitution requires provider independence.
**Decision:** OpenAI is accessed exclusively through the Model Gateway. The gateway supports fallback to local models and other providers. No application code calls OpenAI APIs directly.
**Alternatives:** Direct OpenAI integration — rejected (violates Constitution Article V and XV).
**Consequences:** All AI calls go through an additional layer. Provider switching is possible without code changes.

### D-04: Legal assumptions flagged as REQUIRES VALIDATION, not blocking
**Date:** 2026-08-25
**Status:** APPROVED
**Context:** Legal counsel validation is required for production but not for initial development.
**Decision:** Legal assumptions (L-01 through L-07) are documented as DRAFT/UNVERIFIED. They guide engineering decisions but are explicitly flagged as requiring legal validation before production deployment. They do not block Module 00 or subsequent development modules.
**Alternatives:** Block all development until legal counsel is engaged — rejected by project owner (Rule 6: do not wait unless current module genuinely depends on it).
**Consequences:** Legal validation becomes a production gate, not a development gate.

### D-05: Use Base44 entities as initial database layer
**Date:** 2026-08-25
**Status:** APPROVED
**Context:** The project needs a data persistence layer for development. Base44 provides JSON-schema entities with CRUD operations.
**Decision:** Use Base44 entity schemas as the initial database adapter, behind a repository abstraction interface. The entity schemas will mirror the GFIN core data model. Migration to PostgreSQL will require implementing the repository interface for PostgreSQL.
**Alternatives:**
1. Use a mock in-memory database — rejected (insufficient for real testing).
2. Wait for PostgreSQL — rejected (blocks development).
**Consequences:** Entity schemas must be designed to map cleanly to relational tables. Some Base44 limitations (no joins, limited query types) require workarounds.

## Pending Decisions

| ID | Decision | Status | Needed By |
|----|----------|--------|-----------|
| D-PENDING-01 | Graph database selection (Neo4j vs alternatives) | PENDING benchmark | Module 12 |
| D-PENDING-02 | Cloud provider for production | PENDING | Module 01/40 |
| D-PENDING-03 | AI model selection per task type | PENDING evaluation | Module 19/37 |
| D-PENDING-04 | Event streaming in Base44 (mock vs adapter) | PENDING design | Module 05 |
| D-PENDING-05 | Full-text search approach | PENDING design | Module 07 |
