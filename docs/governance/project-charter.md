# GFIN — Project Charter

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED
**Authority:** Project Owner (Rojs Gordons)
**Applies to:** All GFIN engineering agents and automated engineering workflows

---

## 1. Mission

Build and maintain a secure, evidence-based, continuously operating, internationally federated digital fraud intelligence platform that helps citizens and authorized law-enforcement organizations detect, understand, correlate, monitor, and investigate digital fraud.

## 2. Scope

The Global Fraud Intelligence Network (GFIN) is a 24/7 platform that:

- Discovers and collects legally accessible digital fraud signals from permitted sources
- Accepts and processes citizen fraud reports
- Normalizes, resolves, and correlates entities across an international intelligence graph
- Detects fraud campaigns through infrastructure, content, and behavioral correlation
- Monitors high-value entities and campaigns continuously
- Provides evidence-based risk assessments with full provenance
- Supports authorized law-enforcement investigations through a federated API
- Maintains strict separation between citizen data, public intelligence, and restricted police data
- Operates independently of any single AI provider, country, police database, or external data source

## 3. Primary Audiences

1. **Citizens and victims** — can check entities (phone, email, URL, domain, crypto wallet), submit fraud reports, receive risk explanations, and get alerts
2. **Law-enforcement and authorized government organizations** — can search globally, investigate entities and campaigns, request cross-border information, and integrate via the Police Connector SDK

## 4. Non-Goals

- GFIN does not claim to see "the entire internet"
- GFIN does not store complete police case databases — federation is the default model
- GFIN does not determine criminal guilt or make legal findings
- GFIN does not bypass legal, contractual, or technical access controls
- GFIN does not depend on any single AI provider as a sole operational dependency

## 5. Success Criteria

- Citizens can perform a complete check/report flow
- Authorized investigators can complete a test investigation from search to report
- Two simulated countries can exchange permitted intelligence without exposing restricted data
- AI provider can be switched without application-layer redesign
- Core platform operations continue when AI providers, external sources, or individual workers fail
- Every important claim is traceable to evidence with provenance and confidence

## 6. Development Approach

Modular development per the GFIN Agent Constitution:
- 40 development modules (00–40) from Governance through Production
- Each module follows: SPECIFY → DESIGN → IMPLEMENT → TEST → VERIFY → DOCUMENT → ACCEPT → COMMIT
- No module is marked complete until acceptance criteria pass
- No module is marked ACCEPTED without evidence

## 7. Governing Documents

- **GFIN Agent Constitution v1.0** — 53 articles governing all engineering agents
- **GFIN Master Engineering Specification v1.0** — 62 sections defining architecture, modules, and acceptance criteria
- This charter — project-level authority and scope

## 8. Technical Stack (Proposed)

| Layer | Technology |
|-------|-----------|
| Backend | Python / FastAPI, Go (high-performance services) |
| Containers | Docker |
| Orchestration | Kubernetes |
| Event streaming | Apache Kafka |
| Transactional DB | PostgreSQL |
| Search | OpenSearch |
| Cache | Redis-compatible |
| Object storage | S3-compatible |
| Graph | Neo4j (or benchmarked alternative) |
| Observability | OpenTelemetry / Prometheus / Grafana |
| Identity | OIDC / OAuth2 / MFA |
| Secrets | Vault / KMS equivalent |

**Note:** Technology selections must be validated through performance, security, operational, and licensing analysis before production deployment (per Spec §51).

## 9. Repository

```
/gfin
  /apps          — User-facing applications
  /services      — Backend microservices
  /packages      — Shared libraries
  /infrastructure — Deployment and ops configuration
  /tests         — Test suites
  /docs          — Documentation
```

## 10. Authority and Escalation

- **Project Owner:** Rojs Gordons — final authority on scope, priorities, and dependency changes
- **Escalation triggers:** requirements conflict, unclear legal authority, security compromise, unclear data ownership, uncertain API behavior, contradictory evidence, conflicting acceptance criteria, unresolvable critical defects
- **Escalation format:** problem → evidence → impact → options → recommendation → unresolved questions
