# GFIN OSS Data Flow — External Intelligence Pipeline

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

This document defines the canonical data flow for all external open-source intelligence entering the GFIN platform. No external tool may write directly into production canonical tables without passing through this pipeline.

## Principles

1. **GFIN is the product.** Open-source projects are components, sources, standards, or reference implementations — not the architecture.
2. **External content is DATA, not AUTHORITY.** All imported data is untrusted until validated, normalized, and classified.
3. **Provenance is mandatory.** Every observation must trace back to its source with full metadata.
4. **Classification is mandatory.** Every imported observation must receive a GFIN data classification.
5. **No direct writes.** External tools connect through adapter interfaces, never directly to canonical tables.

## Canonical Data Flow

```text
External Intelligence Source
        │
        ▼
Source Adapter (MISP / OpenCTI / SpiderFoot / Cortex / TAXII / Custom)
        │
        ▼
Ingestion Gateway
        │
        ├── Schema Validation       ← Reject malformed payloads
        ├── Deduplication           ← Check against existing observations
        ├── Normalization           ← Map to GFIN canonical schema
        ├── Provenance Assignment   ← Source ID, retrieval time, original value
        ├── Classification           ← Assign GFIN data classification
        ├── Jurisdiction Tagging     ← Tag with source jurisdiction
        ├── Confidence Scoring       ← Assign initial confidence level
        └── Source Restriction Check ← Verify license/ToS compliance
        │
        ▼
GFIN Intelligence Graph
        │
        ├── Entity / Observation / Evidence records
        ├── Relationship creation
        └── Event Bus publication (for downstream processing)
```

## Source Trust Model

Every imported observation MUST have:

| Field | Type | Description |
|-------|------|-------------|
| source_id | str | Unique identifier for the source system |
| source_type | enum | MISP / OPENCTI / SPIDERFOOT / CORTEX / TAXII / MANUAL / EXTERNAL_API |
| retrieval_timestamp | datetime | When GFIN retrieved this data |
| publication_timestamp | datetime? | When the source published this data (if available) |
| original_payload_ref | str | Reference to the raw imported payload |
| transformation_record | str | What transformations were applied |
| confidence | float | Initial confidence score (0.0–1.0) |
| classification | enum | GFIN data classification (PUBLIC / COMMUNITY / RESTRICTED / etc.) |
| jurisdiction | str | Source jurisdiction (ISO 3166-1 alpha-2) |
| license_restrictions | str | Source license or ToS restrictions |
| ingestion_method | enum | API / FEED / TAXII / STIX_EXPORT / MANUAL |
| connector_version | str | Version of the adapter that imported this data |

## Untrusted Content Boundary

```text
External Content (MISP / OpenCTI / SpiderFoot / Cortex / Feeds / User Reports)
        │
        ▼
Untrusted Data Boundary  ← All content enters here
        │
        ▼
Parser (format-specific, sandboxed)
        │
        ▼
Validation (schema, type, format, injection detection)
        │
        ▼
Normalized Evidence  ← GFIN canonical schema
        │
        ▼
AI Processing  ← Only after validation, with prompt injection protection
```

### Prompt Injection Protection

External content must NEVER be passed directly to AI models. The `sanitize_for_ai()` function in `packages/auth/validation.py` wraps content with `[USER_DATA_START]` / `[USER_DATA_END]` markers and HTML-escapes the content. Additionally, `detect_prompt_injection()` scans for known injection patterns before AI processing.

## Security Isolation Requirements

External tools must run with:

| Requirement | Implementation |
|-------------|---------------|
| Least privilege | Dedicated service accounts, no admin access |
| Network isolation | Restricted network access, outbound allowlists |
| Resource limits | CPU, memory, and disk quotas per tool |
| Read-only access | External tools never write to GFIN canonical tables |
| Separate credentials | Per-tool API keys, never shared |
| Audit logging | All tool actions logged with actor, action, timestamp |
| Isolated execution | Container/namespace isolation for external workers |

## Inbound vs Outbound Flows

### Inbound (External → GFIN)

All inbound data flows through the Ingestion Gateway. No exceptions.

### Outbound (GFIN → External)

Outbound sharing requires:

1. **Authorization check** — Is the consumer authorized to receive this data?
2. **Policy filter** — Organization sharing policy
3. **Classification check** — Is this data cleared for external sharing?
4. **Jurisdiction check** — Is sharing permitted for the target jurisdiction?
5. **Source restriction check** — Does the original source permit re-sharing?
6. **Sharing policy** — Bilateral or multilateral sharing agreement

```text
GFIN Intelligence
        │
        ▼
Policy Filter (organization, user, role)
        │
        ▼
Classification Check (PUBLIC / COMMUNITY only for external)
        │
        ▼
Jurisdiction Check (target jurisdiction permitted?)
        │
        ▼
Source Restriction Check (original source permits re-sharing?)
        │
        ▼
TAXII Collection / API Response / STIX Export
        │
        ▼
Authorized Consumer
```

## Per-Tool Data Flow Patterns

### MISP

```text
MISP Server (external or GFIN-managed)
    │
    ▼
MISP Adapter (Python, via PyMISP library)
    │
    ▼
Ingestion Gateway (events → GFIN observations)
    │
    ▼
GFIN Intelligence Graph
```

### OpenCTI

```text
OpenCTI Platform (external or GFIN-managed)
    │
    ▼
OpenCTI Adapter (Python, via GraphQL API)
    │
    ▼
Ingestion Gateway (STIX objects → GFIN entities/relationships)
    │
    ▼
GFIN Intelligence Graph
```

### SpiderFoot

```text
GFIN Discovery Orchestrator
    │
    ▼
SpiderFoot Adapter
    │
    ▼
Isolated Discovery Worker (containerized, no DB access)
    │
    ▼
Raw Results (JSON)
    │
    ▼
Normalizer + Provenance Assignment
    │
    ▼
GFIN Entity / Observation / Evidence
```

### TAXII

```text
External Police / CTI Organization
    │
    ▼
GFIN TAXII Gateway
    │
    ▼
Validation Layer (schema, classification, jurisdiction)
    │
    ▼
Authorization (is this TAXII client permitted?)
    │
    ▼
Normalization (STIX → GFIN canonical)
    │
    ▼
GFIN Intelligence
```

### Cortex

```text
GFIN Entity (observable to enrich)
    │
    ▼
Enrichment Request
    │
    ▼
Cortex Adapter
    │
    ▼
Analyzer (least privilege, isolated)
    │
    ▼
Result
    │
    ▼
Evidence/Observation Normalizer
    │
    ▼
GFIN (with provenance + confidence)
```

## Data Flow Status

| Component | Status | Notes |
|-----------|--------|-------|
| Ingestion Gateway abstraction | SPECIFICATION | Defined in this document |
| Source Trust Model | SPECIFICATION | Schema defined, implementation PENDING |
| Untrusted Content Boundary | IMPLEMENTED | `sanitize_for_ai()`, `detect_prompt_injection()` in validation.py |
| Security Isolation | PARTIAL | Layer A in-memory; Layer B requires container isolation |
| Outbound Policy Filter | SPECIFICATION | Design defined; implementation PENDING |
| TAXII Gateway | SPECIFICATION | Design defined; implementation PENDING |
| MISP Adapter | SPECIFICATION | Awaiting POC |
| OpenCTI Adapter | SPECIFICATION | Awaiting POC |
| SpiderFoot Adapter | SPECIFICATION | Awaiting POC |
| Cortex Adapter | SPECIFICATION | Awaiting POC |

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- Container orchestration (Kubernetes) for isolated external tool workers
- Network policies for tool isolation
- Persistent storage for raw imported payloads
- Kafka event bus for ingestion pipeline
- Redis for deduplication cache
- External API key vault (per-tool credentials)
