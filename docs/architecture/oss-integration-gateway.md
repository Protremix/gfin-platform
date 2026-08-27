# GFIN OSS Integration Gateway — Architecture

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

The OSS Integration Gateway is the architectural boundary through which all external open-source intelligence tools connect to GFIN. It provides a unified adapter interface, ensuring that no external tool writes directly to GFIN canonical tables.

## Design Principle

```text
GFIN Platform
    │
    ▼
Adapter Interface (Python ABC)
    │
    ├── MISP Adapter
    ├── OpenCTI Adapter
    ├── SpiderFoot Adapter
    ├── Cortex Adapter
    ├── TAXII Adapter
    ├── STIX Import/Export Adapter
    └── Custom Adapters (extensible)
    │
    ▼
External OSS Service
    │
    └── API / Queue / Feed / TAXII / STIX
```

This provides:

- **Upgradeability** — External tools can be upgraded independently
- **Isolation** — External tools have no direct access to GFIN data
- **Licensing clarity** — No external source code copied into GFIN
- **Security boundaries** — All external data enters through validated adapters
- **Independent scaling** — External tools scale independently
- **Easier removal** — Any tool can be removed by disabling its adapter
- **Easier replacement** — Any tool can be replaced with a new adapter

## Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime
from pydantic import BaseModel


class ImportResult(BaseModel):
    """Result of importing data from an external source."""
    source_id: str
    source_type: str
    retrieval_timestamp: datetime
    observations: list[dict[str, Any]]  # Normalized GFIN observations
    entities: list[dict[str, Any]]       # Normalized GFIN entities
    relationships: list[dict[str, Any]]  # Normalized GFIN relationships
    errors: list[str] = []
    warnings: list[str] = []


class OSSAdapter(ABC):
    """Abstract base class for all external OSS tool adapters."""

    @abstractmethod
    async def connect(self, **kwargs: Any) -> bool:
        """Establish connection to the external service."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external service."""
        ...

    @abstractmethod
    async def fetch(self, query: dict[str, Any]) -> ImportResult:
        """Fetch intelligence from the external service."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the external service is reachable and healthy."""
        ...

    @abstractmethod
    def normalize(self, raw_data: Any) -> ImportResult:
        """Normalize raw external data into GFIN canonical format."""
        ...

    @abstractmethod
    def get_source_info(self) -> dict[str, str]:
        """Return source metadata (name, version, license, etc.)."""
        ...
```

## Ingestion Gateway

The Ingestion Gateway is the single entry point for all normalized data from adapters:

```python
class IngestionGateway:
    """Gateway for ingesting normalized data from external adapters.

    All external data passes through this gateway before entering
    GFIN canonical tables. No external tool may bypass this gateway.
    """

    def ingest(self, result: ImportResult) -> IngestionReport:
        """Process an ImportResult through the full ingestion pipeline."""
        # 1. Schema validation
        # 2. Deduplication
        # 3. Provenance assignment
        # 4. Classification
        # 5. Jurisdiction tagging
        # 6. Confidence scoring
        # 7. Source restriction check
        # 8. Write to GFIN canonical tables
        # 9. Publish event to Event Bus
        ...
```

## Per-Tool Integration Patterns

### MISP — API Integration

- **Pattern:** GFIN → MISP REST API → normalized observations → GFIN
- **Library:** PyMISP (Python)
- **Access:** Read-only (GFIN consumes MISP events, attributes, objects)
- **Write-back:** Optional — GFIN can publish observations back to MISP feeds
- **Isolation:** MISP runs as a separate service, GFIN accesses via API only
- **License boundary:** API usage does not trigger AGPL obligations (per MISP official licensing FAQ)

### OpenCTI — API Integration with STIX Normalization

- **Pattern:** GFIN → OpenCTI GraphQL API → STIX objects → GFIN adapter → GFIN canonical
- **Library:** OpenCTI Python client or direct GraphQL
- **Access:** Read-only (GFIN consumes OpenCTI knowledge graph)
- **Write-back:** Optional — GFIN can export STIX bundles to OpenCTI
- **Isolation:** OpenCTI runs as a separate service, GFIN accesses via API
- **Critical:** GFIN data model remains authoritative; OpenCTI is an interoperability layer, not the canonical model

### SpiderFoot — Isolated Worker

- **Pattern:** GFIN → SpiderFoot Adapter → Isolated Worker → Raw Results → Normalizer → GFIN
- **Library:** SpiderFoot CLI/API
- **Access:** SpiderFoot has NO access to GFIN databases
- **Isolation:** SpiderFoot runs in an isolated container with restricted network access
- **Security:** All results are treated as untrusted observations requiring provenance and validation
- **Output:** JSON results normalized to GFIN entity/observation schema

### TAXII — Gateway with Policy Filter

- **Pattern:** External → TAXII 2.x → GFIN TAXII Gateway → Validation → Authorization → GFIN
- **Library:** cti-taxii-client (OASIS official Python library)
- **Access:** Bidirectional (inbound consumption + outbound sharing)
- **Security:** All TAXII collections require authentication and authorization
- **Outbound policy:** Classification + jurisdiction + source restriction checks before any export

### STIX — Import/Export Adapter

- **Pattern:** GFIN canonical → STIX 2.x mapping → STIX bundle → Export
- **Pattern:** STIX bundle → Import → GFIN mapping → GFIN canonical
- **Library:** stix2 (OASIS official Python library)
- **Critical:** STIX is an interoperability format, NOT the GFIN internal data model
- **Mapping:** Explicit mapping table between GFIN entities and STIX objects (see STIX integration doc)

### TheHive — Case Management (Under Evaluation)

- **Pattern:** TBD — depends on overlap assessment with GFIN's planned case model
- **Options:** ISOLATE (run alongside GFIN) or REJECT (GFIN builds its own)
- **Integration:** If used, REST API integration only

### Cortex — Enrichment Engine

- **Pattern:** GFIN Entity → Enrichment Request → Cortex Adapter → Analyzer → Result → Normalizer → GFIN
- **Library:** Cortex REST API
- **Access:** Cortex runs with least privilege, isolated from GFIN databases
- **Critical:** Analyzer results are observations, NOT facts. They require provenance and confidence scoring.
- **Isolation:** Cortex runs in a separate container with restricted credentials

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Adapter Interface (ABC) | SPECIFICATION | Defined in this document |
| Ingestion Gateway | SPECIFICATION | Design defined, implementation PENDING |
| MISP Adapter | SPECIFICATION | Awaiting ADR approval |
| OpenCTI Adapter | SPECIFICATION | Awaiting ADR approval |
| SpiderFoot Adapter | SPECIFICATION | Awaiting ADR approval |
| TAXII Gateway | SPECIFICATION | Awaiting ADR approval |
| STIX Import/Export | SPECIFICATION | Awaiting ADR approval |
| Cortex Adapter | SPECIFICATION | Awaiting ADR approval |
| TheHive Adapter | RESEARCH | Under evaluation |

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- Kubernetes namespace for external tool isolation
- Network policies for adapter isolation
- External tool Docker images (official images only)
- API key vault for per-tool credentials
- Monitoring and alerting for adapter health
