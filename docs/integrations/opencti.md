# GFIN — OpenCTI Integration Specification

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

OpenCTI is integrated as an external CTI peer and STIX 2.1 interoperability layer. GFIN communicates with OpenCTI via its GraphQL API. GFIN's canonical data model remains authoritative — OpenCTI is NOT the GFIN data store.

## Official Sources

| Resource | URL |
|----------|-----|
| OpenCTI Repository | https://github.com/OpenCTI-Platform/opencti |
| Connectors | https://github.com/OpenCTI-Platform/connectors |
| Python Client (pycti) | https://github.com/OpenCTI-Platform/client-python |
| Documentation | https://docs.opencti.io/ |
| Website | https://filigran.io/products/opencti |

## License

- **Community Edition:** Apache-2.0 (commercial-safe)
- **Enterprise Edition:** Commercial (Filigran)

**Finding:** Apache-2.0 permits commercial use with attribution. No copyleft concerns for CE.

## Integration Architecture

```text
GFIN Platform
    │
    ▼
OpenCTI Adapter (Python, pycti or direct GraphQL)
    │
    ├── Inbound: OpenCTI STIX objects → GFIN entities/relationships
    ├── Outbound: GFIN entities → OpenCTI STIX objects (optional)
    └── Health Check: OpenCTI API status
    │
    ▼
OpenCTI Platform (separate service, Apache-2.0)
    │
    ├── Knowledge Graph (Elasticsearch/OpenSearch)
    ├── Connectors (150+ import/enrichment/export)
    ├── TAXII 2.1 Server (embedded)
    ├── Real-time Streams (SSE)
    └── RBAC with marking definitions
```

## Key Decision: GFIN Data Model is Authoritative

OpenCTI uses STIX 2.1 as its native data model. GFIN does NOT adopt STIX as its internal model. The OpenCTI adapter performs bidirectional translation:

- **Inbound:** OpenCTI STIX → GFIN canonical (via STIX adapter + normalization)
- **Outbound:** GFIN canonical → STIX → OpenCTI (via STIX adapter)

This means the existing STIX adapter POC (`packages/common/stix_adapter.py`) is reused for OpenCTI integration.

## GFIN ↔ OpenCTI Data Mapping

| OpenCTI Concept | GFIN Concept | Transformation |
|----------------|-------------|----------------|
| STIX Domain Object | GFIN Entity | Type-specific mapping (see STIX mapping table) |
| STIX Cyber Observable | GFIN Entity | Observable value → normalized_value |
| STIX Relationship | GFIN Relationship | relationship_type → GFIN relationship type |
| STIX Report | GFIN Report | Report name → title, labels → category |
| STIX Marking Definition | GFIN Classification | TLP → GFIN classification level |
| STIX Sighting | GFIN Observation | Sighting → observation with provenance |
| OpenCTI Confidence | GFIN Confidence | 0-100 → LOW/MEDIUM/HIGH/CONFIRMED |
| OpenCTX x_opencti_stix_ids | GFIN metadata | Cross-reference stored in metadata |

## Connector Leverage

OpenCTI's 150+ connectors can be used to enrich GFIN intelligence:

| Connector Type | GFIN Use Case |
|---------------|---------------|
| External Import | MISP, AbuseIPDB, VirusTotal, Shodan feeds → OpenCTI → GFIN |
| Internal Enrichment | IP/domain enrichment on-demand |
| Internal Export | STIX 2.1 bundle export for sharing |
| Stream | Real-time updates to GFIN via SSE |

## Security Model

| Requirement | Implementation |
|-------------|---------------|
| Authentication | OpenCTI API key or OAuth2 |
| Authorization | Dedicated GFIN user with read-only or restricted role |
| Network | OpenCTI on isolated network segment |
| Data in transit | TLS/HTTPS mandatory |
| Audit | All API calls logged in GFIN audit trail |
| Marking definitions | TLP mapping to GFIN classification |
| Organization isolation | GFIN org in OpenCTI with data segregation |

## Deployment (Layer B — REQUIRES EXTERNAL INFRASTRUCTURE)

| Component | Specification |
|-----------|--------------|
| OpenCTI Core | Docker container |
| Search Engine | Elasticsearch 8.x or OpenSearch 2.x |
| Cache | Redis 7.x+ |
| Message Queue | RabbitMQ 3.x+ |
| Object Storage | MinIO or S3 |
| Resources | 8+ vCPUs, 32+ GB RAM (heavy stack) |
| K8s | Helm charts available |

**WARNING:** OpenCTI's infrastructure requirements (Elasticsearch + Redis + RabbitMQ + S3) are significant. Evaluate whether the value justifies the operational overhead.

## POC Plan

1. Deploy OpenCTI in Docker (Layer B)
2. Configure financial fraud taxonomies
3. Implement OpenCTI Adapter using pycti
4. Test inbound: Create OpenCTI entity → verify GFIN ingestion
5. Test outbound: Create GFIN entity → verify OpenCTI creation
6. Test TAXII: Use OpenCTI's embedded TAXII server for external sharing
7. Test streams: Subscribe to OpenCTI SSE for real-time updates

## Status

| Component | Status |
|-----------|--------|
| Specification | COMPLETE |
| POC | PENDING (Layer B infrastructure required) |
| Adapter implementation | PENDING (reuses STIX adapter) |
| Integration tests | PENDING |
| Legal review | NOT REQUIRED (Apache-2.0) |
