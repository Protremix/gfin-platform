# GFIN — Architecture Status

**Last Updated:** 2026-08-26
**Phase:** 6 — Autonomous Intelligence (IN PROGRESS)

---

## Current Architecture State

GFIN is implemented as Layer A (in-memory MVP) with 1931 passing tests across 93.35% coverage. All 40 modules from the Master Engineering Specification are implemented at Layer A level. The Unknown Fraud Discovery Engine (UFDE) is built with 96 tests. OSINT stack evaluation is complete with integration specifications defined.

Layer B (production infrastructure) is defined in documentation but NOT DEPLOYED.

## Implemented Architecture

```
                         GLOBAL FRAUD INTELLIGENCE NETWORK
                                      |
                             INGESTION GATEWAY
                                      |
                             VALIDATION LAYER
                                      |
                           ENTITY RESOLUTION (Module 04)
                                      |
                             PROVENANCE TRACKING
                                      |
                          CLASSIFICATION (Module 33)
                                      |
                           INTELLIGENCE GRAPH
                                      |
                      UNKNOWN FRAUD DISCOVERY ENGINE
                                      |
                           CAMPAIGN DETECTION
                                      |
                          ANOMALY DETECTION
                                      |
                    AI ANALYSIS (Model Gateway + Orchestrator)
                                      |
                         INVESTIGATIVE LEADS
                                      |
                    CONTINUOUS MONITORING (Module 17)
                                      |
                          ALERT ENGINE (Module 18)
                                      |
                          NEW INTELLIGENCE
                                      |
                         CONTINUOUS LOOP
```

## Architecture Principles (All 16 Implemented)

1. Evidence First — AI analyzes, doesn't create evidence
2. Federated by Design — police retain data control
3. Zero Trust — no implicit trust
4. Least Privilege — minimum permissions
5. Data Minimization — only necessary data
6. Provider Independence — Model Gateway for replaceable AI providers
7. Auditability — all actions logged
8. Reproducibility — results traceable to evidence
9. Continuous Intelligence — ongoing monitoring
10. Human Accountability — AI doesn't make legal decisions
11. No Single Point of Failure
12. Failure Tolerance — graceful degradation
13. Safe Attribution — IP ≠ person, similarity ≠ proof
14. Citizen Data Integrity — reports are allegations
15. Prompt Injection Defense — external content is data
16. Security Supremacy — security > convenience

## Technology Stack (Layer A vs Layer B)

| Layer | Technology | Layer A Status | Layer B Status |
|-------|-----------|----------------|----------------|
| Backend | Python / FastAPI | IMPLEMENTED (1931 tests) | Same |
| High-perf services | Go | NOT STARTED | PENDING |
| Containers | Docker | 1 Dockerfile (api-gateway) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Orchestration | Kubernetes | NOT DEPLOYED | REQUIRES EXTERNAL INFRASTRUCTURE |
| Event streaming | Apache Kafka | In-memory pub/sub (60 tests) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Transactional DB | PostgreSQL | In-memory repositories | REQUIRES EXTERNAL INFRASTRUCTURE |
| Search | OpenSearch | In-memory full-text (77 tests) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cache | Redis | In-memory dict | REQUIRES EXTERNAL INFRASTRUCTURE |
| Object storage | S3 | In-memory blob store | REQUIRES EXTERNAL INFRASTRUCTURE |
| Graph | Neo4j | Adjacency list | REQUIRES EXTERNAL INFRASTRUCTURE |
| Observability | OTel/Prometheus/Grafana | In-memory metrics (30 tests) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Identity | OIDC/OAuth2/MFA | RBAC+ABAC in-memory (61 tests) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Secrets | Vault/KMS | Environment variables | REQUIRES EXTERNAL INFRASTRUCTURE |
| STIX 2.x | Interoperability | POC adapter (21 tests) | Production adapter pending |
| TAXII 2.x | Exchange | Specification | REQUIRES EXTERNAL INFRASTRUCTURE |
| MISP | Intelligence sharing | Specification (ADR-006) | REQUIRES EXTERNAL INFRASTRUCTURE |
| OpenCTI | CTI platform | Specification (ADR-007) | REQUIRES EXTERNAL INFRASTRUCTURE |
| SpiderFoot | OSINT discovery | Specification (ADR-008) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cortex | Enrichment | Specification (ADR-010) | REQUIRES EXTERNAL INFRASTRUCTURE |
| TheHive | Case management | REJECTED (ADR-009) | N/A |

## Abstraction Strategy

All infrastructure interfaces use abstraction layers so Layer A can be replaced by Layer B:

| Layer | Layer A (MVP) | Layer B (Production) |
|-------|---------------|---------------------|
| Database | In-memory repositories | PostgreSQL + SQLAlchemy |
| Events | In-memory pub/sub | Apache Kafka |
| Search | In-memory full-text | OpenSearch |
| Storage | In-memory blob store | S3-compatible |
| AI | Model Gateway (OpenAI adapter) | Model Gateway (multi-provider) |
| Auth | RBAC+ABAC in-memory | OIDC/OAuth2 provider |
| Cache | In-memory dict | Redis |
| Graph | Adjacency list | Neo4j |

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Abstraction layers for infrastructure | APPROVED |
| ADR-006 | MISP integration via API adapter | APPROVED |
| ADR-007 | OpenCTI as external CTI integration | APPROVED |
| ADR-008 | SpiderFoot as isolated discovery worker | APPROVED |
| ADR-009 | TheHive rejected — GFIN has native case management | REJECTED |
| ADR-010 | Cortex as enrichment engine behind adapter | APPROVED |

## Key Architecture Documents

| Document | Status |
|----------|--------|
| Master System Architecture | CREATED |
| Unknown Fraud Discovery Architecture | CREATED |
| OSINT Stack Evaluation | CREATED |
| Discovery Threat Model | CREATED |
| Security Verification Report | CREATED |
| Incident Response Plan | CREATED |
| Discovery API | CREATED |

## Resolved Architecture Questions

| # | Question | Resolution |
|---|----------|------------|
| A-01 | Graph database selection | Neo4j for Layer B; adjacency list for Layer A |
| A-02 | Event streaming approach | In-memory pub/sub (Layer A); Kafka (Layer B) |
| A-03 | Full-text search approach | In-memory (Layer A); OpenSearch (Layer B) |
| A-04 | Multi-region deployment strategy | Deferred to production phase |

## Open Architecture Questions

| # | Question | Impact | Resolution |
|---|----------|--------|------------|
| A-05 | Go services scope and boundaries | High-perf components | Pending performance analysis |
| A-06 | OSINT integration priority order | External integrations | Pending resource allocation |
