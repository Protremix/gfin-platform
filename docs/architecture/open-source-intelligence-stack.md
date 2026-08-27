# GFIN — Open Source Intelligence Stack Evaluation

**Version:** 1.0
**Status:** SPECIFICATION — EVALUATION COMPLETE
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

This document evaluates mature open-source intelligence and threat-intelligence technologies for integration into the Global Fraud Intelligence Network (GFIN). Each technology is evaluated against the GFIN architecture, security model, data flow, and licensing requirements.

**Core Principle:** GFIN is the product. Open-source projects are components, sources, standards, or reference implementations — not the accidental architecture of GFIN.

---

## 1. Evaluation Matrix Summary

| Technology | Recommendation | License | Maintenance | Integration Method |
|-----------|---------------|---------|-------------|-------------------|
| MISP | **INTEGRATE** | AGPL-3.0 (core); BSD-2 (PyMISP) | High activity (v2.5.44+) | API integration via PyMISP |
| OpenCTI | **INTEGRATE** | Apache-2.0 (CE) | High activity (10k+ stars) | GraphQL API adapter |
| SpiderFoot | **ISOLATE** | MIT (v4.0) | Low activity (last commit Nov 2023) | Isolated worker, no DB access |
| STIX 2.x | **USE** | OASIS standard (BSD-3 libs) | Maintained by OASIS | Interoperability format only |
| TAXII 2.x | **INTEGRATE** | OASIS standard (BSD-3 libs) | Maintained by OASIS | Gateway with policy filter |
| TheHive | **REJECT** | AGPLv3 (v4, archived); Commercial (v5) | Archived Dec 2025 | Not integrated — domain mismatch |
| Cortex | **INTEGRATE** | AGPL-3.0 | Maintained by StrangeBee | Standalone REST API, least privilege |

### Additional Projects Evaluated

| Project | Category | License | Recommendation | Rationale |
|---------|----------|---------|---------------|-----------|
| PyMISP | Intelligence | BSD-2 | **USE** | API client for MISP integration |
| cti-python-stix2 | Intelligence | BSD-3 | **USE** | Official STIX 2.x library (already POC'd) |
| Crawl4AI | Discovery | Apache-2.0 | **RESEARCH** | AI-ready web scraping for fraud sites |
| Splink | AI/Data | AGPL-3.0 | **RESEARCH** | Probabilistic entity resolution |
| Sentence-Transformers | AI | Apache-2.0 | **RESEARCH** | Local embeddings for semantic matching |
| ipwhois / pyasn | Discovery | BSD-2/MIT | **USE** | IP/ASN enrichment libraries |
| CertStream | Discovery | MIT | **RESEARCH** | Real-time Certificate Transparency |
| Ollama / vLLM | AI | MIT/Apache-2.0 | **RESEARCH** | Local LLM serving behind Model Gateway |
| Qdrant | AI/Data | Apache-2.0 | **RESEARCH** | Vector database for semantic search |
| Gitleaks | Security | MIT | **USE** | Secret scanning for CI/CD |
| Trivy | Security | Apache-2.0 | **USE** | Container/dependency scanning |
| Syft | Security | Apache-2.0 | **RESEARCH** | SBOM generation |
| pip-audit | Security | Apache-2.0 | **USE** | Python dependency auditing |
| OpenTelemetry | Observability | Apache-2.0 | **RESEARCH** | Distributed tracing standard |
| Prometheus | Observability | Apache-2.0 | **RESEARCH** | Metrics scraping |
| PaddleOCR | AI | Apache-2.0 | **RESEARCH** | Multilingual OCR for evidence |
| Meilisearch | Data | MIT | **RESEARCH** | Full-text search for investigator UI |
| IntelMQ | Intelligence | AGPL-3.0 | **RESEARCH** | Feed processing framework |
| Yeti | Intelligence | Apache-2.0 | **RESEARCH** | Lightweight observable platform |

---

## 2. Primary Technology Evaluations

### 2.1 MISP — INTEGRATE

**Official Repository:** https://github.com/MISP/MISP
**Official Website:** https://www.misp-project.org/
**Documentation:** https://misp.github.io/MISP/
**License:** AGPL-3.0-or-later (core); BSD-2-Clause (PyMISP); CC0/BSD (taxonomies, galaxies, objects)
**Latest Version:** v2.5.44+ (monthly releases, 283+ contributors)
**Docker:** Official at https://github.com/MISP/misp-docker

#### License Finding (VERIFIED from official source)

Source: https://www.misp-project.org/license/

> "AGPL only applies to the MISP core software and not to any other software using the API of MISP."

**Architectural Implication:** GFIN can communicate with MISP via REST API / PyMISP without triggering AGPL copyleft obligations. PyMISP is BSD-2-Clause. Source code disclosure under AGPL only triggers if MISP core PHP code is modified and offered as a network service.

**NOTE:** This is NOT legal advice. Formal legal counsel should verify before production deployment.

#### Fraud-Specific Capabilities

- `misp-taxonomy:financial-fraud`: Money mules, credit card fraud, APP fraud, BEC/CEO fraud, account takeover, SIM swapping
- `misp-galaxy:financial-fraud`: Financial threat tactics, scam frameworks
- MISP Objects: `bank-account`, `credit-card`, `transaction`, `cryptocurrency-transaction`, `btc-wallet`, `mule-account`
- Federation: Hub-and-spoke model ideal for central banks → commercial banks sharing
- STIX/TAXII: Native STIX 2.1 conversion, TAXII 2.1 push/poll

#### Integration Decision: C. Integrate through API

GFIN will NOT embed MISP core. GFIN will integrate through PyMISP (BSD-2) REST API client. MISP runs as a separate service.

See: `docs/integrations/misp.md` and `docs/adr/ADR-006-misp-integration.md`

#### Evaluation Matrix

| Criterion | Finding |
|-----------|---------|
| Architecture | Events → Attributes → Objects → Galaxies → Taxonomies |
| APIs | Full REST API, OpenAPI 3.0 spec, PyMISP SDK |
| Synchronization | Push/Pull, granular filtering by tags/org/distribution |
| Sharing Groups | Fine-grained multi-org sharing circles |
| Correlation | Automatic, CIDR matching, fuzzy hashing |
| STIX/TAXII | STIX 1.x/2.0/2.1 export, TAXII 1.1/2.1 |
| Docker/K8s | Official Docker, community Helm charts |
| Multi-tenancy | Organization-based with RBAC |
| Audit | Database logs, ZMQ streaming, syslog |
| Provenance | Creator Org vs Owner Org, sightings, proposals |
| Security | API keys, SAML, OIDC, LDAP, TOTP 2FA, PGP |
| Privacy | Warning lists, TLP enforcement, anonymization, hashing |
| Fraud suitability | HIGH — financial fraud taxonomies, bank-account objects |
| Resource reqs | 4-8 vCPUs, 16-32 GB RAM, MySQL/MariaDB + Redis |
| Operational complexity | MEDIUM — requires PHP, MySQL, Redis stack |

---

### 2.2 OpenCTI — INTEGRATE

**Official Repository:** https://github.com/OpenCTI-Platform/opencti
**Official Website:** https://filigran.io/products/opencti
**Documentation:** https://docs.opencti.io/
**License:** Apache-2.0 (Community Edition); Commercial (Enterprise Edition)
**Latest Version:** 6.x/7.x (weekly/bi-weekly releases, 10,000+ stars)
**Docker:** Official Docker support

#### Key Finding

OpenCTI is one of the most faithful STIX 2.1 implementations in open source. It provides a knowledge graph, 150+ connectors, enrichment framework, TAXII 2.1 server, and GraphQL API.

**Critical:** GFIN data model remains authoritative. OpenCTI is an interoperability layer, not the canonical model. If integrated, a GFIN ↔ OpenCTI Adapter with normalization, provenance, classification, and permission boundaries is required.

#### Integration Decision: C. Use as external CTI integration

GFIN will NOT replace its canonical data model with OpenCTI. GFIN will build a bidirectional adapter: GFIN ↔ OpenCTI via GraphQL API, with STIX 2.1 as the exchange format.

See: `docs/integrations/opencti.md` and `docs/adr/ADR-007-opencti-integration.md`

#### Evaluation Matrix

| Criterion | Finding |
|-----------|---------|
| STIX 2.1 model | Native, most faithful implementation |
| Knowledge graph | Elasticsearch/OpenSearch + Redis + RabbitMQ + S3/MinIO |
| Entities/Relationships | Full STIX SDOs, SCOs, SROs, SMOs |
| Confidence | 0-100 scoring, NATO Admiralty Code |
| Source attribution | STIX created_by_ref, marking definitions |
| Temporal tracking | first_seen/last_seen/valid_from/valid_until |
| Connectors | 150+ (import, enrichment, export, stream, analytics) |
| TAXII | Embedded TAXII 2.1 server + client polling |
| Streams | SSE real-time streams, RabbitMQ queues |
| API | GraphQL (full coverage) |
| Access control | RBAC, marking definitions, organization isolation |
| Multi-org | Supported with data segregation |
| Scalability | Elasticsearch-dependent; horizontal scaling |
| Deployment | Elasticsearch + Redis + RabbitMQ + S3 (heavy stack) |
| Audit | Full audit trail, activity logging |
| License | Apache-2.0 (CE) — commercial-safe |

---

### 2.3 SpiderFoot — ISOLATE

**Official Repository:** https://github.com/smicallef/spiderfoot
**Official Website:** https://www.spiderfoot.net/
**License:** MIT (v4.0, relicensed April 2022; previously GPLv3)
**Latest Version:** v4.0 (last commit November 2023)
**Docker:** Official Dockerfile and docker-compose

#### Key Finding

SpiderFoot provides 233 OSINT modules covering domains, IPs, emails, phones, Bitcoin, dark web. However, development has slowed significantly since late 2023.

**Critical:** SpiderFoot must NOT be given unrestricted access to GFIN production intelligence database. It must run in an isolated worker with restricted network access.

#### Integration Decision: ISOLATE — Isolated Discovery Worker

```text
GFIN Discovery Orchestrator → SpiderFoot Adapter → Isolated Worker → Normalizer → GFIN
```

Every imported result retains: source, retrieval time, original value, transformation, confidence, legal/source policy, classification.

See: `docs/integrations/spiderfoot.md` and `docs/adr/ADR-008-spiderfoot-isolation.md`

#### Evaluation Matrix

| Criterion | Finding |
|-----------|---------|
| Modules | 233 (reputation, search, DNS, dark web, social) |
| API | Web API (port 5001), CLI |
| Docker | Official Dockerfile, docker-compose |
| Correlation | 38 YAML rules, risk-level alerts |
| Data sources | 84+ API-key-dependent, 100+ free |
| Rate limiting | Per-module delays, thread pool, retry logic |
| Legal | API ToS compliance required per provider |
| Resources | ~200MB baseline, 1-2GB during scans, SQLite |
| Maintenance risk | LOW activity — may need custom module maintenance |
| Security | Must be isolated from production DB |

---

### 2.4 STIX 2.x — USE

**Official Specification:** https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html
**Python Library:** https://github.com/oasis-open/cti-python-stix2 (BSD-3-Clause)
**License:** OASIS standard (freely implementable); BSD-3-Clause (library)

#### Key Finding

STIX 2.x is an interoperability standard, NOT the GFIN internal data model. GFIN uses STIX for:
- Inbound ingestion from external CTI sources
- Outbound sharing with authorized consumers
- Interoperability with MISP, OpenCTI, TAXII servers

#### GFIN Fields NOT Representable in STIX 2.x (without custom extensions)

| GFIN Field | Solution |
|------------|----------|
| Data Classification (5-level) | Custom `x_gfin_classification` property |
| Jurisdiction | Custom `x_gfin_jurisdiction` property |
| Source Restrictions | Custom `x_gfin_source_restrictions` property |
| Organization Isolation | Custom `x_gfin_organization_id` property |
| Triage Priority | Custom `x_gfin_triage_priority` property |
| Report Score | Custom `x_gfin_score` property |
| Evidence Chain-of-Custody | Custom `x_gfin_evidence_ref` property |

#### POC Status: IMPLEMENTED (Layer A)

The STIX adapter POC has been implemented with 20 passing tests:
- Export: GFIN → STIX (email, domain, IP, URL, identity, campaign, custom)
- Import: STIX → GFIN (all above types)
- Round-trip: GFIN → STIX → GFIN (verified fidelity)
- Custom properties: classification, jurisdiction preserved across round-trips

Files: `packages/common/stix_adapter.py`, `tests/unit/test_stix_adapter.py`

See: `docs/integrations/stix-taxii.md` and `docs/adr/ADR-009-stix-taxii.md`

---

### 2.5 TAXII 2.x — INTEGRATE

**Official Specification:** https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html
**Python Client:** https://github.com/oasis-open/cti-taxii-client (BSD-3-Clause)
**License:** OASIS standard (freely implementable); BSD-3-Clause (library)

#### Key Finding

TAXII 2.x provides standardized exchange for police/CTI sharing. GFIN will build a TAXII Gateway with:
- Inbound: External → TAXII → Validation → Authorization → Normalization → GFIN
- Outbound: GFIN → Policy Filter → Classification Check → Jurisdiction Check → TAXII Collection → Consumer

**Critical:** Never expose restricted police intelligence merely because it is technically exportable.

See: `docs/integrations/stix-taxii.md` and `docs/adr/ADR-009-stix-taxii.md`

---

### 2.6 TheHive — REJECT

**Official Repository:** https://github.com/TheHive-Project/TheHive (ARCHIVED Dec 5, 2025)
**Official Website:** https://strangebee.com
**License:** AGPLv3 (v4, archived); Commercial/Proprietary (v5, StrangeBee)

#### Key Finding

TheHive's GitHub repository was **archived on December 5, 2025**. TheHive 5 is now closed-source commercial software.

**Domain Mismatch:** TheHive is built for cybersecurity incident response (SOC/CSIRT). Its core primitives are IOCs, MITRE ATT&CK, and Cortex analyzers. GFIN's domain is financial crime, AML, fraud detection, and regulatory reporting with bank accounts, transactions, and compliance workflows.

**Recommendation:** Do NOT integrate TheHive. GFIN should build its own domain-native case management model. The infrastructure overhead (Cassandra + Elasticsearch + S3) is unjustified for GFIN's use case.

See: `docs/integrations/thehive.md` and `docs/adr/ADR-010-thehive-rejection.md`

---

### 2.7 Cortex — INTEGRATE

**Official Repository:** https://github.com/TheHive-Project/Cortex
**Analyzers:** https://github.com/TheHive-Project/Cortex-Analyzers
**License:** AGPL-3.0 (core engine); AGPL-3.0 (analyzers)
**Maintenance:** Actively maintained by StrangeBee

#### Key Finding

Cortex can run **standalone** (without TheHive) as an independent enrichment microservice. It provides 150+ analyzers (300+ flavors) for IP, domain, hash, email analysis.

**Security Model:**
- Zero direct access to GFIN production database
- API-only communication (REST API)
- Dedicated service account with `analyze` role only
- Docker container execution mode for analyzer isolation
- Analyzer results are observations, NOT facts

#### Integration Decision: INTEGRATE — Standalone REST API, least privilege

```text
GFIN Entity → Enrichment Request → Cortex Adapter → Analyzer → Result → Normalizer → GFIN
```

Cortex runs with least privilege. Analyzer results never automatically become facts — they are observations requiring provenance and confidence scoring.

See: `docs/integrations/cortex.md` and `docs/adr/ADR-011-cortex-integration.md`

---

## 3. Additional Open-Source Projects

### High-Priority Recommendations

| Project | Category | License | Recommendation | Why Relevant |
|---------|----------|---------|---------------|-------------|
| Crawl4AI | Discovery | Apache-2.0 | RESEARCH | AI-ready web scraping for fraud site investigation |
| Splink | AI/Data | AGPL-3.0 | RESEARCH | Probabilistic entity resolution for victim reports |
| Sentence-Transformers | AI | Apache-2.0 | RESEARCH | Local embeddings for semantic fraud report matching |
| ipwhois/pyasn | Discovery | BSD-2/MIT | USE | WHOIS/ASN enrichment for IP infrastructure mapping |
| CertStream | Discovery | MIT | RESEARCH | Real-time Certificate Transparency for fake domain detection |
| Ollama/vLLM | AI | MIT/Apache | RESEARCH | Local LLM serving behind Model Gateway |
| Qdrant | AI/Data | Apache-2.0 | RESEARCH | Vector database for semantic fraud campaign search |
| PaddleOCR | AI | Apache-2.0 | RESEARCH | Multilingual OCR for screenshot evidence analysis |

### Security Tooling

| Project | License | Recommendation | Why |
|---------|---------|---------------|-----|
| Gitleaks | MIT | USE | Secret scanning for CI/CD pipeline |
| Trivy | Apache-2.0 | USE | Container/dependency vulnerability scanning |
| pip-audit | Apache-2.0 | USE | Python supply chain auditing |
| Syft | Apache-2.0 | RESEARCH | SBOM generation (CycloneDX) |

### Observability

| Project | License | Recommendation | Why |
|---------|---------|---------------|-----|
| OpenTelemetry | Apache-2.0 | RESEARCH | Vendor-neutral distributed tracing |
| Prometheus | Apache-2.0 | RESEARCH | Standard metrics scraping |

---

## 4. Security Findings

### Isolation Requirements (All External Tools)

| Requirement | Implementation |
|-------------|---------------|
| Least privilege | Dedicated service accounts, no admin access |
| Network isolation | Restricted network access, outbound allowlists |
| Resource limits | CPU, memory, disk quotas per tool |
| Read-only access | External tools never write to GFIN canonical tables |
| Separate credentials | Per-tool API keys, never shared |
| Audit logging | All tool actions logged with actor, action, timestamp |
| Container isolation | Isolated execution for external workers |

### Untrusted Content Boundary

All external content (MISP, OpenCTI, SpiderFoot, Cortex, feeds, user reports) is treated as DATA, not AUTHORITY. Content passes through:
1. Untrusted Data Boundary
2. Parser (sandboxed)
3. Validation (schema, injection detection)
4. Normalized Evidence
5. AI Processing (with prompt injection protection)

**Implemented:** `sanitize_for_ai()` and `detect_prompt_injection()` in `packages/auth/validation.py`

---

## 5. License Findings

| Technology | License | AGPL Concern? | Legal Review Required? |
|-----------|---------|---------------|------------------------|
| MISP core | AGPL-3.0 | NO — API use exempt per official FAQ | YES — verify before production |
| PyMISP | BSD-2-Clause | No | No |
| OpenCTI CE | Apache-2.0 | No | No |
| SpiderFoot | MIT | No | No |
| STIX/TAXII libs | BSD-3-Clause | No | No |
| TheHive v4 | AGPLv3 (archived) | N/A — not integrating | N/A |
| TheHive v5 | Commercial | N/A — not integrating | N/A |
| Cortex | AGPL-3.0 | YES — API use likely exempt but needs verification | YES |
| Cortex Analyzers | AGPL-3.0 | Per-analyzer license | YES |
| Splink | AGPL-3.0 | YES — if used as service; in-process use may be OK | YES |
| Crawl4AI | Apache-2.0 | No | No |
| Sentence-Transformers | Apache-2.0 | No | No |

**NOTE:** All license findings are engineering assessments, NOT legal advice. Formal legal counsel is required before production deployment of any AGPL-licensed technology.

---

## 6. Architecture Findings

### Integration Gateway

All external tools connect through adapter interfaces — never directly to GFIN canonical tables. See `docs/architecture/oss-integration-gateway.md`.

### Data Flow

All external data flows through the Ingestion Gateway: Schema Validation → Deduplication → Normalization → Provenance → Classification → Jurisdiction → Confidence → GFIN. See `docs/architecture/oss-data-flow.md`.

### GFIN Data Model Authority

The GFIN canonical data model (defined in `packages/schemas/`) remains authoritative. No external project replaces it. STIX is an export/import format, not the internal model.

---

## 7. POC Results

| Technology | POC Status | Result |
|-----------|-----------|--------|
| STIX 2.x | **IMPLEMENTED** | 20 passing tests, round-trip verified |
| MISP | SPECIFICATION | POC design ready, implementation pending |
| OpenCTI | SPECIFICATION | POC design ready, implementation pending |
| SpiderFoot | SPECIFICATION | POC design ready, implementation pending |
| TAXII | SPECIFICATION | POC design ready, implementation pending |
| Cortex | SPECIFICATION | POC design ready, implementation pending |
| TheHive | N/A | Not evaluated (rejected) |

---

## 8. Open Issues

See `docs/open-issues.md` for the full list. Key open issues:

1. MISP AGPL license — formal legal counsel required before production
2. Cortex AGPL license — verify API-use exemption
3. STIX extension definition — register `x_gfin_*` namespace formally
4. TAXII server implementation — select server (OpenCTI built-in or standalone)
5. SpiderFoot maintenance — low activity, may need custom module maintenance
6. Police federation — TAXII sharing agreements need legal review

---

## 9. Legal Review Required

| Item | Why |
|------|-----|
| MISP AGPL | Verify API-use exemption for GFIN integration |
| Cortex AGPL | Verify API-use exemption for standalone integration |
| Splink AGPL | Verify in-process use vs service use |
| TAXII sharing | Data sharing agreements with police/CTI organizations |
| Source restrictions | Per-provider API ToS compliance |

---

## 10. Files Changed

| File | Action | Description |
|------|--------|-------------|
| `docs/architecture/open-source-intelligence-stack.md` | CREATED | This document |
| `docs/architecture/oss-integration-gateway.md` | CREATED | Integration gateway architecture |
| `docs/architecture/oss-data-flow.md` | CREATED | Data flow pipeline design |
| `docs/integrations/misp.md` | CREATED | MISP integration specification |
| `docs/integrations/opencti.md` | CREATED | OpenCTI integration specification |
| `docs/integrations/spiderfoot.md` | CREATED | SpiderFoot integration specification |
| `docs/integrations/stix-taxii.md` | CREATED | STIX/TAXII integration specification |
| `docs/integrations/thehive.md` | CREATED | TheHive evaluation (rejection) |
| `docs/integrations/cortex.md` | CREATED | Cortex integration specification |
| `docs/adr/ADR-006-misp-integration.md` | CREATED | MISP integration ADR |
| `docs/adr/ADR-007-opencti-integration.md` | CREATED | OpenCTI integration ADR |
| `docs/adr/ADR-008-spiderfoot-isolation.md` | CREATED | SpiderFoot isolation ADR |
| `docs/adr/ADR-009-stix-taxii.md` | CREATED | STIX/TAXII ADR |
| `docs/adr/ADR-010-thehive-rejection.md` | CREATED | TheHive rejection ADR |
| `docs/adr/ADR-011-cortex-integration.md` | CREATED | Cortex integration ADR |
| `packages/common/stix_adapter.py` | CREATED | STIX import/export adapter (POC) |
| `tests/unit/test_stix_adapter.py` | CREATED | STIX adapter tests (20 tests) |
| `docs/open-issues.md` | UPDATED | Added OSINT stack open issues |
| `docs/module-status.md` | UPDATED | Added OSINT evaluation module |

---

## FINAL PRINCIPLE

GFIN is the product. Open-source projects are components, sources, standards, or reference implementations.

Do not allow any external project to become the accidental architecture of GFIN.

Prefer interoperable standards, especially STIX/TAXII where appropriate.

Preserve GFIN's:
- Canonical data model
- Provenance
- Classification
- Jurisdiction
- Organization isolation
- Auditability
- Security boundaries
