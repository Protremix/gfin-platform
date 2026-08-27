# GFIN — Open Issues

**Last Updated:** 2026-08-26
**Status:** ACTIVE — All items explicitly tracked. None hidden.

---

## Legal Issues (L-01 through L-07)

### L-01 — GDPR Applicability and Specific Obligations

| Field | Value |
|-------|-------|
| **Issue ID** | L-01 |
| **Description** | GDPR (Regulation 2016/679) applicability and specific obligations for the GFIN platform not yet confirmed by legal counsel |
| **Affected Modules** | Module 13 (Citizen Platform), Module 14 (Fraud Reporting), Module 33 (Compliance), Module 39 (Pilot), Module 40 (Production) |
| **Jurisdiction** | European Union / EEA |
| **Current Assumption** | GDPR applies to EU deployments. Platform supports data minimization, legal basis recording, data subject rights, retention policies, and data residency. |
| **Risk** | HIGH — Non-compliance can result in fines up to 4% of annual global turnover and platform shutdown in EU |
| **Required Legal Decision** | Confirm GDPR applicability; identify specific obligations for fraud intelligence platform; determine lawful basis for processing citizen data and law-enforcement intelligence; validate cross-border transfer mechanisms |
| **Production Impact** | Blocks EU production deployment. Does not block non-production development. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner (Rojs Gordons) — must engage legal counsel |
| **Dependency** | None |
| **Next Action** | Engage EU data protection legal counsel |

### L-02 — Law-Enforcement Data Protection Directive

| Field | Value |
|-------|-------|
| **Issue ID** | L-02 |
| **Description** | Directive (EU) 2016/680 (law-enforcement data protection) applicability and obligations not confirmed |
| **Affected Modules** | Module 23 (Police API), Module 24 (Police Connector SDK), Module 25 (Global Matching), Module 26 (Cross-Border Requests), Module 32 (Federation) |
| **Jurisdiction** | European Union / EEA |
| **Current Assumption** | Directive applies to police data processing. Platform's federated model (no full database uploads) aligns with data minimization. Cross-border requests require formal workflow with legal basis. |
| **Risk** | HIGH — Non-compliance affects police integrations in EU |
| **Required Legal Decision** | Confirm directive applicability; determine specific obligations for cross-border intelligence sharing; validate police connector data processing |
| **Production Impact** | Blocks EU police integrations. Does not block API contract development or testing with mock data. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner — must engage legal counsel |
| **Dependency** | L-01 (GDPR determination informs directive scope) |
| **Next Action** | Engage EU law-enforcement data protection counsel |

### L-03 — Per-Jurisdiction Data Residency Requirements

| Field | Value |
|-------|-------|
| **Issue ID** | L-03 |
| **Description** | Specific data residency requirements per country/jurisdiction not yet defined |
| **Affected Modules** | Module 32 (Federation), Module 33 (Compliance), Module 35 (Disaster Recovery), Module 40 (Production) |
| **Jurisdiction** | Global (EU, UK, US, APAC, country-specific) |
| **Current Assumption** | Architecture supports regional deployment. Data residency is a configurable policy. Sensitive data remains in required jurisdiction. |
| **Risk** | MEDIUM — Misconfiguration could lead to data being stored outside required jurisdiction |
| **Required Legal Decision** | Define which data types must reside in which jurisdictions; determine if federation can cross borders for metadata only; validate multi-region deployment strategy |
| **Production Impact** | Blocks multi-country production deployment. Does not block single-region development. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner |
| **Dependency** | L-01, L-02 |
| **Next Action** | Engage counsel per target country |

### L-04 — Telegram Terms of Service

| Field | Value |
|-------|-------|
| **Issue ID** | L-04 |
| **Description** | Telegram Terms of Service not reviewed for permitted data access methods |
| **Affected Modules** | Module 17 (Telegram-related features, if implemented) |
| **Jurisdiction** | Global (Telegram terms) |
| **Current Assumption** | Only user-submitted Telegram data, official APIs/bots within terms, and lawful law-enforcement channels are permitted. No mass scraping. |
| **Risk** | HIGH — Unauthorized data collection violates Telegram terms and potentially law |
| **Required Legal Decision** | Review Telegram ToS; determine permitted data collection methods; validate AI/ML training restrictions |
| **Production Impact** | Blocks any Telegram data collection feature. Does not block building the source adapter interface or using mock data. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner |
| **Dependency** | None |
| **Next Action** | Review Telegram Terms of Service and API terms |

### L-05 — AI Provider Data Processing Agreements

| Field | Value |
|-------|-------|
| **Issue ID** | L-05 |
| **Description** | AI provider (OpenAI and others) data processing agreements not reviewed |
| **Affected Modules** | Module 19 (Model Gateway), Module 20 (OpenAI), Module 21 (Local AI), Module 22 (AI Orchestrator) |
| **Jurisdiction** | Global (provider-specific) |
| **Current Assumption** | Enterprise/API privacy controls are available and sufficient. Model Gateway controls what data is sent. Restricted data stays on local models. |
| **Risk** | HIGH — Sending restricted data to external AI without proper DPA could violate GDPR/law-enforcement data rules |
| **Required Legal Decision** | Review OpenAI enterprise data processing terms; determine what data classifications can be sent to external AI; validate retention and training opt-out terms |
| **Production Impact** | Blocks production AI features using external providers. Does not block Model Gateway interface development or testing with mock responses. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner |
| **Dependency** | L-01 (GDPR informs what can be sent) |
| **Next Action** | Review OpenAI enterprise/API data processing terms |

### L-06 — Cross-Border Information Request Legal Framework

| Field | Value |
|-------|-------|
| **Issue ID** | L-06 |
| **Description** | Legal framework for cross-border law-enforcement information requests not defined |
| **Affected Modules** | Module 26 (Cross-Border Requests), Module 32 (Federation) |
| **Jurisdiction** | International (bilateral/multilateral agreements) |
| **Current Assumption** | Cross-border requests follow a formal workflow: REQUEST → VALIDATE → AUTHORIZE → REVIEW → APPROVE/DENY → AUDIT. Each request records legal basis, purpose, and urgency. |
| **Risk** | HIGH — Unauthorized cross-border data sharing could violate national sovereignty and data protection laws |
| **Required Legal Decision** | Define legal basis categories for cross-border requests; determine which jurisdictions can exchange which data types; validate request workflow legal sufficiency |
| **Production Impact** | Blocks cross-border federation. Does not block building the request workflow interface or testing with mock data. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner |
| **Dependency** | L-02, L-03 |
| **Next Action** | Engage international data-sharing counsel |

### L-07 — Retention Period Requirements

| Field | Value |
|-------|-------|
| **Issue ID** | L-07 |
| **Description** | Specific data retention period requirements per classification not defined |
| **Affected Modules** | Module 33 (Compliance), Module 06 (Evidence Vault), Module 14 (Fraud Reporting) |
| **Jurisdiction** | Per-jurisdiction |
| **Current Assumption** | Engineering defaults: PUBLIC= indefinite, COMMUNITY=2y, RESTRICTED=3y, LAW_ENFORCEMENT=per jurisdiction, HIGHLY_RESTRICTED=per case. All configurable. |
| **Risk** | MEDIUM — Incorrect retention could lead to premature data deletion or unlawful retention |
| **Required Legal Decision** | Define retention periods per data classification per jurisdiction; determine evidence retention for legal hold; validate right-to-erasure scope |
| **Production Impact** | Blocks production compliance. Does not block building retention policy engine with configurable defaults. |
| **Status** | DRAFT — REQUIRES COUNSEL VALIDATION |
| **Owner** | Project Owner |
| **Dependency** | L-01 |
| **Next Action** | Engage counsel for retention period guidance |

---

## Source Policy Issues (S-01 through S-03)

### S-01 — Telegram Terms / Permitted Access

| Field | Value |
|-------|-------|
| **Issue ID** | S-01 |
| **Description** | Telegram Terms of Service not reviewed; permitted data access methods unconfirmed |
| **Intended Use** | Collect user-submitted Telegram identifiers (username, public link, message, screenshot, document, URL) for fraud intelligence |
| **Source Owner** | Telegram (terms), GFIN users (submitted data) |
| **Applicable Access Method** | User submission, official APIs/bots within terms, licensed sources, lawful law-enforcement channels |
| **Restrictions** | NO mass scraping; NO prohibited aggregation; NO AI/ML training where terms prohibit |
| **Source Adapter** | To be implemented in Module 17 as `TelegramSourceAdapter` interface with mock data |
| **Status** | OPEN — Do not implement collection until terms validated |
| **Owner** | Project Owner |
| **Impact** | Blocks Telegram data collection in production |
| **Dependency** | L-04 |
| **Next Action** | Review Telegram ToS and API terms |

### S-02 — Web Crawling / Source-Specific Terms

| Field | Value |
|-------|-------|
| **Issue ID** | S-02 |
| **Description** | Per-source terms of service for web crawling not reviewed |
| **Intended Use** | Crawl permitted public web sources for fraud intelligence (phishing pages, fraudulent domains, scam content) |
| **Source Owner** | Per-website (varies) |
| **Applicable Access Method** | Web crawler with robots.txt compliance, rate limiting, no auth bypass |
| **Restrictions** | Respect robots.txt; respect ToS; no auth bypass; identify crawler; no access-control circumvention |
| **Source Adapter** | To be implemented in Module 08 as `WebCrawlSourceAdapter` with crawl policy enforcement |
| **Status** | OPEN — Per-source review required before crawling each domain in production |
| **Owner** | Project Owner |
| **Impact** | Blocks crawling live sources in production; does not block crawler implementation or testing with mock pages |
| **Dependency** | None |
| **Next Action** | Establish per-source review process before production crawling |

### S-03 — Licensed Threat-Intelligence Feeds

| Field | Value |
|-------|-------|
| **Issue ID** | S-03 |
| **Description** | Licensed threat-intelligence feed agreements not in place |
| **Intended Use** | Incorporate licensed threat intelligence (domain reputation, IP reputation, fraud indicators) |
| **Source Owner** | Commercial threat intelligence providers (TBD) |
| **Applicable Access Method** | Contractual data feeds (API, bulk export, streaming) |
| **Restrictions** | Use only within license scope; no redistribution beyond permitted scope; respect provider terms |
| **Source Adapter** | To be implemented as `LicensedFeedSourceAdapter` interface with mock data |
| **Status** | PENDING — Business/legal negotiation required |
| **Owner** | Project Owner |
| **Impact** | Blocks production threat-intelligence feed integration; does not block interface development |
| **Dependency** | None |
| **Next Action** | Identify and negotiate with threat intelligence providers |

---

## Architecture Review Issues (A-01 through A-10)

### A-01 — Architecture Overview

| Field | Value |
|-------|-------|
| **Issue ID** | A-01 |
| **Description** | Architecture overview requires formal documentation and review |
| **Status** | IN PROGRESS — Document being created in `/docs/architecture-review.md` |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | None |
| **Required Decision** | Project owner review and acceptance of architecture overview |
| **Next Action** | Complete architecture review document; submit for owner review |

### A-02 — Component Diagram

| Field | Value |
|-------|-------|
| **Issue ID** | A-02 |
| **Description** | Component diagram showing all services, packages, and their relationships required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | A-01 |
| **Required Decision** | Validate component boundaries and service decomposition |
| **Next Action** | Complete in architecture review document |

### A-03 — Data Flow Diagram

| Field | Value |
|-------|-------|
| **Issue ID** | A-03 |
| **Description** | Data flow diagram showing how data moves through the system required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | A-01 |
| **Required Decision** | Validate data flows respect classification boundaries |
| **Next Action** | Complete in architecture review document |

### A-04 — Trust Boundary Diagram

| Field | Value |
|-------|-------|
| **Issue ID** | A-04 |
| **Description** | Trust boundary diagram showing zero-trust zones and authentication boundaries required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | A-01 |
| **Required Decision** | Validate trust boundaries are complete and correct |
| **Next Action** | Complete in architecture review document |

### A-05 — Data Classification Model

| Field | Value |
|-------|-------|
| **Issue ID** | A-05 |
| **Description** | Formal data classification model with access rules required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | None |
| **Required Decision** | Validate classification levels and access rules |
| **Next Action** | Complete in architecture review document |

### A-06 — Federation Model

| Field | Value |
|-------|-------|
| **Issue ID** | A-06 |
| **Description** | Federation model showing national nodes, data sharing, and sovereignty controls required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | L-02, L-03, L-06 |
| **Required Decision** | Validate federation architecture respects data sovereignty |
| **Next Action** | Complete in architecture review document |

### A-07 — AI Architecture

| Field | Value |
|-------|-------|
| **Issue ID** | A-07 |
| **Description** | AI architecture showing Model Gateway, routing, providers, and hallucination controls required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | L-05 |
| **Required Decision** | Validate AI routing and data classification enforcement |
| **Next Action** | Complete in architecture review document |

### A-08 — Police API Architecture

| Field | Value |
|-------|-------|
| **Issue ID** | A-08 |
| **Description** | Police API architecture showing endpoints, authentication, and federation protocol required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | L-02, L-06 |
| **Required Decision** | Validate Police API design supports federation without data sovereignty violations |
| **Next Action** | Complete in architecture review document |

### A-09 — Failure Model

| Field | Value |
|-------|-------|
| **Issue ID** | A-09 |
| **Description** | Failure model showing degradation behavior, fallbacks, and recovery required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | None |
| **Required Decision** | Validate failure modes are comprehensive and acceptable |
| **Next Action** | Complete in architecture review document |

### A-10 — Deployment Model

| Field | Value |
|-------|-------|
| **Issue ID** | A-10 |
| **Description** | Deployment model showing Layer A (MVP) and Layer B (production) required |
| **Status** | IN PROGRESS |
| **Owner** | GFIN-CEA |
| **Impact** | Module 00 acceptance |
| **Dependency** | None |
| **Required Decision** | Validate deployment strategy and migration path |
| **Next Action** | Complete in architecture review document |

---

## Technology Validation Issues (T-01 through T-12)

| ID | Technology | Status | Owner | Impact | Dependency | Required Decision | Next Action |
|----|-----------|--------|-------|--------|------------|-------------------|------------|
| T-01 | Kubernetes | PROPOSED / NOT YET VALIDATED | Project Owner | All services | None | Evaluate: functionality, scalability, security, reliability, operational complexity, licensing, ecosystem, cost, migration risk, alternatives | Technology Decision Record before production |
| T-02 | Apache Kafka | PROPOSED / NOT YET VALIDATED | Project Owner | Module 05 (Event Bus) | None | Evaluate same criteria + benchmark against alternatives (Pulsar, NATS, Redis Streams) | TDR before Module 05 production |
| T-03 | PostgreSQL | PROPOSED / NOT YET VALIDATED | Project Owner | Module 03 (Core Data) | None | Evaluate same criteria + benchmark against alternatives (CockroachDB, YugabyteDB) | TDR before Module 03 production |
| T-04 | Redis | PROPOSED / NOT YET VALIDATED | Project Owner | Module 05+ | None | Evaluate same criteria + alternatives (Memcached, DragonflyDB) | TDR before production |
| T-05 | OpenSearch | PROPOSED / NOT YET VALIDATED | Project Owner | Module 07 (Search) | None | Evaluate same criteria + alternatives (Elasticsearch, Meilisearch, Typesense) | TDR before Module 07 production |
| T-06 | Neo4j | PROPOSED / NOT YET VALIDATED | Project Owner | Module 12 (Graph) | None | Evaluate same criteria + alternatives (ArangoDB, JanusGraph, TigerGraph) + benchmark | TDR before Module 12 production |
| T-07 | S3-compatible storage | PROPOSED / NOT YET VALIDATED | Project Owner | Module 06 (Evidence) | None | Evaluate same criteria + WORM compliance + alternatives (MinIO, cloud-native) | TDR before Module 06 production |
| T-08 | OpenTelemetry | PROPOSED / NOT YET VALIDATED | Project Owner | Module 34 (Observability) | None | Evaluate same criteria + alternatives (Jaeger, Zipkin) | TDR before Module 34 production |
| T-09 | Prometheus + Grafana | PROPOSED / NOT YET VALIDATED | Project Owner | Module 34 (Observability) | None | Evaluate same criteria + alternatives (Datadog, NewRelic) | TDR before Module 34 production |
| T-10 | OIDC/OAuth2 | PROPOSED / NOT YET VALIDATED | Project Owner | Module 02 (Security) | None | Evaluate same criteria + provider selection (Keycloak, Auth0, Okta) | TDR before Module 02 production |
| T-11 | OpenAI | PROPOSED / NOT YET VALIDATED | Project Owner | Module 20 (OpenAI) | L-05 | Evaluate same criteria + alternatives (Anthropic, local models) + DPA review | TDR before Module 20 production |
| T-12 | Local/open-source AI | PROPOSED / NOT YET VALIDATED | Project Owner | Module 21 (Local AI) | None | Evaluate model selection (Llama, Mistral, etc.) + hardware requirements | TDR before Module 21 production |

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Legal (L) | 7 | All DRAFT — REQUIRES COUNSEL VALIDATION |
| Source Policy (S) | 3 | All OPEN or PENDING |
| Architecture (A) | 10 | All IN PROGRESS |
| Technology (T) | 12 | All PROPOSED / NOT YET VALIDATED |
| **Total Open Issues** | **32** | |

## Rules

1. No legal assumption becomes a production requirement without validation
2. No source is used in production until terms/licensing/authorization validated
3. No architecture component is ACCEPTED until review complete
4. No technology is the final choice until evaluation complete
5. All items remain visible in this document
6. Development continues on modules that do not depend on unresolved issues

---

## OSINT Stack Evaluation — Open Issues

| # | Issue | Priority | Status | Notes |
|---|-------|----------|--------|-------|
| OSINT-1 | MISP AGPL license — formal legal counsel required | HIGH | OPEN | API-use exemption verified from official FAQ, but formal legal opinion needed before production |
| OSINT-2 | Cortex AGPL license — verify API-use exemption | HIGH | OPEN | Similar to MISP pattern but needs independent verification |
| OSINT-3 | STIX extension definition — register x_gfin_* namespace | MEDIUM | OPEN | Custom properties need formal STIX 2.1 extension-definition registration |
| OSINT-4 | TAXII server — select implementation | MEDIUM | OPEN | Options: OpenCTI embedded TAXII, OpenTAXII, or custom |
| OSINT-5 | SpiderFoot maintenance risk — low activity since Nov 2023 | MEDIUM | OPEN | May need to maintain custom modules as APIs evolve |
| OSINT-6 | Police federation — TAXII sharing agreements need legal review | HIGH | OPEN | Data sharing agreements with police/CTI organizations |
| OSINT-7 | Splink AGPL — verify in-process use vs service use | LOW | OPEN | Only relevant if entity resolution library is adopted |
| OSINT-8 | OpenCTI infrastructure overhead — heavy stack (ES+Redis+RabbitMQ+S3) | MEDIUM | OPEN | Evaluate if value justifies operational cost |
| OSINT-9 | Source restriction tracking — per-provider API ToS compliance | MEDIUM | OPEN | Each external API has different ToS and rate limits |
| OSINT-10 | Outbound sharing policy enforcement — classification + jurisdiction checks | HIGH | OPEN | Must never expose restricted police intelligence externally |
