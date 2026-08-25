# ADR-002: Two-Layer Development Strategy

**Date:** 2026-08-25
**Status:** ACCEPTED
**Context:** GFIN requires both verifiable MVP functionality and production-ready infrastructure definitions. The development environment (Base44 sandbox) cannot deploy production infrastructure (Kafka, PostgreSQL, Neo4j, etc.), but the engineering team must still build and test core logic.

**Decision:** Adopt a two-layer development strategy:
- **Layer A (MVP/In-Memory):** Verifiable functionality using mocks, in-memory data structures, and fixture data. All tests must pass. Data is marked `is_synthetic=True`. This layer proves the logic works.
- **Layer B (Production-Ready Definitions):** Infrastructure definitions, manifests, and adapter code that are production-ready but not deployable from the current environment. Marked `REQUIRES EXTERNAL INFRASTRUCTURE`. This layer proves the architecture is sound.

**Rationale:**
- Allows rapid iteration and verification of business logic without external dependencies
- Prevents fabrication of deployment claims
- Production infrastructure can be deployed later without rewriting application code
- Clear separation between verified and unverified capabilities
- GPT Luna (GFIN-CEA) verifies each module at Layer A and acknowledges Layer B as future work

**Consequences:**
- Every module has both Layer A and Layer B components
- Layer B items are explicitly marked in module docs and code comments
- No claim of production readiness until Layer B is deployed and verified
- The two-layer approach is accepted by GPT Luna for all modules 00-12
