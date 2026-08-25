# GFIN — Technology Validation

**Version:** 1.0
**Date:** 2026-08-25
**Status:** PROPOSED / NOT YET VALIDATED

---

## TECHNOLOGY STATUS: PROPOSED / NOT YET VALIDATED

No technology in the proposed stack is confirmed as the final production choice. Each component requires a Technology Decision Record (TDR) evaluating the criteria below before production deployment.

---

## Technology Decision Record (TDR) Template

Every major infrastructure component requires a completed TDR before production use.

### Required Evaluation Criteria

| Criterion | Description |
|-----------|-------------|
| **Functionality** | Does the technology meet all functional requirements? |
| **Scalability** | Can it scale to target load (entities, events, queries, storage)? |
| **Security** | What are the security properties? Encryption, access control, audit, isolation? |
| **Reliability** | What is the expected uptime, failure behavior, and recovery? |
| **Operational Complexity** | How difficult is it to deploy, configure, monitor, and troubleshoot? |
| **Licensing** | What license applies? Are there commercial requirements? Is the license compatible with GFIN's use case? |
| **Ecosystem** | Community size, available tooling, integrations, documentation quality, long-term viability |
| **Cost** | Infrastructure cost, operational cost, per-unit cost, cost at scale |
| **Migration Risk** | How difficult is it to migrate away if needed? Is there vendor lock-in? |
| **Alternatives** | What alternatives exist? Why was this chosen over them? |

### TDR Format

```markdown
# TDR-XX: [Technology Name]

## Decision
[ACCEPTED / REJECTED / PROPOSED]

## Context
[Why this decision is needed]

## Evaluation

### Functionality
[Assessment]

### Scalability
[Assessment with target metrics]

### Security
[Assessment]

### Reliability
[Assessment with expected uptime, failure modes]

### Operational Complexity
[Assessment]

### Licensing
[License and commercial requirements]

### Ecosystem
[Community, tooling, integrations]

### Cost
[Estimated costs at target scale]

### Migration Risk
[Lock-in assessment, migration difficulty]

### Alternatives Considered
| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| [Alt 1] | | | Rejected because... |
| [Alt 2] | | | |

## Consequences
[Impact of this decision]

## Decision Date
[Date or PENDING]

## Validated By
[Name or PENDING]
```

---

## Pending TDRs

| TDR | Technology | Status | Needed By | Alternatives to Evaluate |
|-----|-----------|--------|-----------|------------------------|
| TDR-01 | Kubernetes (orchestration) | NOT STARTED | Module 01 production | Docker Swarm, Nomad, managed K8s (EKS/GKE/AKS) |
| TDR-02 | Apache Kafka (event streaming) | NOT STARTED | Module 05 production | Pulsar, NATS, Redis Streams, AWS Kinesis/SQS |
| TDR-03 | PostgreSQL (transactional DB) | NOT STARTED | Module 03 production | CockroachDB, YugabyteDB, MySQL |
| TDR-04 | Redis (cache) | NOT STARTED | Module 05 production | Memcached, DragonflyDB, ValKey |
| TDR-05 | OpenSearch (search) | NOT STARTED | Module 07 production | Elasticsearch, Meilisearch, Typesense, Vespa |
| TDR-06 | Neo4j (graph DB) | NOT STARTED | Module 12 production | ArangoDB, JanusGraph, TigerGraph, Memgraph, PostgreSQL+AGE |
| TDR-07 | S3-compatible (object storage) | NOT STARTED | Module 06 production | AWS S3, MinIO, Cloudflare R2, Backblaze B2 |
| TDR-08 | OpenTelemetry (observability) | NOT STARTED | Module 34 production | Jaeger, Zipkin, Datadog, NewRelic |
| TDR-09 | Prometheus + Grafana (metrics) | NOT STARTED | Module 34 production | Datadog, NewRelic, InfluxDB+Grafana |
| TDR-10 | OIDC/OAuth2 (identity) | NOT STARTED | Module 02 production | Keycloak, Auth0, Okta, Authentik, Zitadel |
| TDR-11 | OpenAI (AI provider) | NOT STARTED | Module 20 production | Anthropic (Claude), Google (Gemini), local models |
| TDR-12 | Local/open-source AI | NOT STARTED | Module 21 production | Llama, Mistral, Phi, Qwen, Ollama, vLLM |

---

## Current Layer A Technology (Development)

These are used in development and do NOT require a TDR (they are development-only):

| Component | Technology | Status |
|-----------|-----------|--------|
| Runtime | Python 3.11 | IMPLEMENTED + TESTED |
| Web framework | FastAPI | IMPLEMENTED + TESTED |
| Validation | Pydantic v2 | IMPLEMENTED + TESTED |
| Database (dev) | In-memory dict | IMPLEMENTED + TESTED |
| Event bus (dev) | In-memory pub/sub | IMPLEMENTED + TESTED |
| Search (dev) | Entity query scan | IMPLEMENTED + TESTED |
| Storage (dev) | Local filesystem | IMPLEMENTED + TESTED |
| Graph (dev) | Adjacency list | IMPLEMENTED + TESTED |
| Cache (dev) | In-memory dict with TTL | IMPLEMENTED + TESTED |
| Identity (dev) | Token-based mock | IMPLEMENTED + TESTED |
| Model Gateway (dev) | Mock with routing | IMPLEMENTED + TESTED |
| Testing | pytest + pytest-asyncio | IMPLEMENTED + TESTED |
| Linting | Ruff | CONFIGURED |
| Type checking | MyPy (strict) | CONFIGURED |
| Secret scanning | Gitleaks | CONFIGURED |
| Dependency scanning | pip-audit + safety | CONFIGURED |

---

## Rules

1. No technology is the final choice until its TDR is complete and accepted
2. TDRs must evaluate all 10 criteria
3. Alternatives must be genuinely considered, not strawman
4. Cost estimates must be at target production scale, not development scale
5. Security assessment must consider GFIN's specific threat model
6. Migration risk must assess what happens if we need to switch
7. TDRs are stored in `/docs/adr/` with prefix `TDR-`
8. TDR status: PROPOSED → UNDER EVALUATION → ACCEPTED or REJECTED
9. A REJECTED TDR triggers evaluation of the next alternative
10. All TDRs require project owner approval
