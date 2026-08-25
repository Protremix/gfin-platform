# GFIN — Architecture Status

**Last Updated:** 2026-08-25
**Phase:** 0 — Governance

---

## Current Architecture State

The architecture is at the governance stage. No implementation exists yet. The following architectural decisions have been documented in principle but not yet validated through implementation.

## Target Architecture

```
                         GLOBAL FRAUD INTELLIGENCE NETWORK
                                      |
                             GLOBAL CONTROL PLANE
                                      |
              +-----------------------+-----------------------+
              |                                               |
      GLOBAL INTELLIGENCE CORE                         NATIONAL NODES
              |                                    /          |          \
              |                                  ES           FR          DE
              |                               Police        Police      Police
              |
       GLOBAL ENTITY INDEX
              |
       GLOBAL EVENT BUS
              |
      +-------+--------+---------+
      |                |         |
    Web             Citizens   Police
  Sources            Reports   Connectors
      |                |         |
      +----------------+---------+
                       |
               ENTITY RESOLUTION
                       |
       +---------------+---------------+
       |               |               |
     FRAUD       INFRASTRUCTURE     FINANCIAL
     GRAPH           GRAPH            GRAPH
       +---------------+---------------+
                       |
                 GLOBAL GRAPH
                       |
                AI ORCHESTRATOR
                       |
        +--------------+--------------+
        |              |              |
      OpenAI        Local AI       Other AI
        |              |              |
        +--------------+--------------+
                       |
                EVIDENCE ENGINE
                       |
                  RISK ENGINE
                       |
                CAMPAIGN ENGINE
                       |
             GLOBAL EARLY WARNING
                       |
             +---------+---------+
             |                   |
          CITIZENS            POLICE
```

## Architecture Principles (Documented)

All 16 architecture principles from the Constitution and Spec are documented in `/docs/governance/architecture-principles.md`. Key principles:

1. Evidence First (AI analyzes, doesn't create evidence)
2. Federated by Design (police retain data control)
3. Zero Trust (no implicit trust)
4. Least Privilege (minimum permissions)
5. Data Minimization (only necessary data)
6. Provider Independence (replaceable AI providers via Model Gateway)
7. Auditability (all actions logged)
8. Reproducibility (results traceable to evidence)
9. Continuous Intelligence (ongoing monitoring)
10. Human Accountability (AI doesn't make legal decisions)
11. No Single Point of Failure
12. Failure Tolerance (graceful degradation)
13. Safe Attribution (IP ≠ person, similarity ≠ proof)
14. Citizen Data Integrity (reports are allegations)
15. Prompt Injection Defense (external content is data)
16. Security Supremacy (security > convenience)

## Technology Stack (Proposed — Requires Validation)

| Layer | Technology | Validation Status |
|-------|-----------|-------------------|
| Backend | Python / FastAPI | UNVERIFIED — pending Module 01 |
| High-perf services | Go | UNVERIFIED — pending performance analysis |
| Containers | Docker | UNVERIFIED — pending Module 01 |
| Orchestration | Kubernetes | REQUIRES EXTERNAL INFRASTRUCTURE |
| Event streaming | Apache Kafka | REQUIRES EXTERNAL INFRASTRUCTURE |
| Transactional DB | PostgreSQL | UNVERIFIED — pending Module 03 |
| Search | OpenSearch | UNVERIFIED — pending Module 07 |
| Cache | Redis-compatible | UNVERIFIED — pending Module 01 |
| Object storage | S3-compatible | REQUIRES EXTERNAL INFRASTRUCTURE |
| Graph | Neo4j | PENDING — requires benchmark testing (D-01) |
| Observability | OpenTelemetry/Prometheus/Grafana | REQUIRES EXTERNAL INFRASTRUCTURE |
| Identity | OIDC/OAuth2/MFA | UNVERIFIED — pending Module 02 |
| Secrets | Vault/KMS | REQUIRES EXTERNAL INFRASTRUCTURE |

## Abstraction Strategy

Per project rules (Rule 8), all interfaces are built through abstraction layers so Base44 can later be replaced or supplemented by external cloud infrastructure:

| Layer | Abstraction | Base44 Implementation | External Target |
|-------|------------|----------------------|----------------|
| Database | Entity repository pattern | Base44 entities (JSON schema) | PostgreSQL + SQLAlchemy |
| Events | Event bus interface | Base44 workflows / in-memory queue | Apache Kafka |
| Search | Search service interface | Base44 entity queries | OpenSearch |
| Storage | Object storage interface | Base44 file upload | S3-compatible |
| AI | Model Gateway interface | Backend functions calling AI | OpenAI/local/other via gateway |
| Auth | Identity provider interface | Base44 auth | OIDC/OAuth2 provider |
| Cache | Cache service interface | In-memory / Redis mock | Redis |
| Graph | Graph store interface | Adjacency list in entities | Neo4j |

## Architecture Decision Records

ADR-001: Use abstraction layers for all infrastructure components — see `/docs/adr/ADR-001-abstraction-layers.md`

## Open Architecture Questions

| # | Question | Impact | Resolution |
|---|----------|--------|------------|
| A-01 | Graph database selection (Neo4j vs alternatives) | Infrastructure Graph, Campaign Engine | Benchmark testing in Module 12 |
| A-02 | Event streaming in Base44 (mock vs real) | Event Bus module | Module 05 design |
| A-03 | Full-text search in Base44 vs external | Search module | Module 07 design |
| A-04 | Multi-region deployment strategy | Federation, DR | Module 32/35 design |
