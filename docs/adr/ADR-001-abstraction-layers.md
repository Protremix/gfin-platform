# ADR-001: Abstraction Layers for Infrastructure Portability

**Date:** 2026-08-25
**Status:** ACCEPTED
**Context:** GFIN development occurs in a Base44 workspace. The production target architecture requires Kubernetes, Kafka, Neo4j, OpenSearch, PostgreSQL, Redis, S3, and multi-region deployment — none of which can be deployed from the current environment.

**Decision:** All infrastructure components are accessed through abstraction interfaces. Each interface has an initial Base44 adapter and a target external adapter. The core application logic depends only on interfaces, never on specific infrastructure.

**Interface Layer:**

| Interface | Base44 Adapter | External Target |
|-----------|---------------|-----------------|
| `EntityRepository` | Base44 entities | PostgreSQL + SQLAlchemy |
| `EventBus` | In-memory / workflow triggers | Apache Kafka |
| `SearchService` | Base44 entity queries | OpenSearch |
| `ObjectStorage` | Base44 file upload | S3-compatible |
| `ModelGateway` | Backend function calling AI providers | Standalone service with OpenAI/local/other |
| `IdentityProvider` | Base44 auth | OIDC/OAuth2 provider |
| `CacheService` | In-memory dict / mock | Redis |
| `GraphStore` | Adjacency list in entities | Neo4j |

**Alternatives Considered:**
1. Wait for external infrastructure before starting — rejected: blocks all progress, project owner explicitly requested building what can be built now.
2. Build directly on Base44 without abstractions — rejected: creates tight coupling, makes migration painful and risky.
3. Documentation only — rejected: project owner requested implementation.

**Consequences:**
- All interfaces must be designed upfront with both adapters in mind.
- Mock/staging adapters are used where external services are unavailable.
- Slight overhead from abstraction layers is acceptable for the portability benefit.
- Base44 limitations (no joins, limited query types, no full-text search) require workarounds in the Base44 adapter.
- Migration to production infrastructure requires implementing the target adapter and migrating data — no core application rewrite.

**Compliance:**
- Constitution Article V (Provider Independence) — satisfied by ModelGateway interface
- Constitution Article XII (Architecture Principles) — abstraction supports all principles
- Constitution Article XXVI (Failure Tolerance) — interfaces support fallback adapters
- Constitution Article XXVII (No Single Point of Failure) — interfaces allow redundant implementations
