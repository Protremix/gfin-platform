# ADR-007: OpenCTI Integration as External CTI Peer

**Status:** ACCEPTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

GFIN needs to interoperate with the broader CTI ecosystem. OpenCTI is the leading open-source STIX 2.1-native threat intelligence platform with 150+ connectors and an embedded TAXII 2.1 server.

## Decision

**INTEGRATE OpenCTI as an external CTI peer via GraphQL API.**

GFIN's canonical data model remains authoritative. OpenCTI is NOT the GFIN data store. A bidirectional adapter performs GFIN ↔ STIX 2.1 ↔ OpenCTI translation, reusing the existing STIX adapter POC.

## Rationale

1. **STIX 2.1 native:** Most faithful implementation — ideal interoperability layer
2. **Apache-2.0:** Commercial-safe license with no copyleft concerns
3. **Connector ecosystem:** 150+ connectors can feed GFIN through OpenCTI
4. **TAXII server:** Embedded TAXII 2.1 server for police/CTI sharing
5. **Knowledge graph:** Graph-based analysis complements GFIN's entity graph

## Consequences

- GFIN must deploy OpenCTI stack (Elasticsearch + Redis + RabbitMQ + S3) — significant infrastructure
- Adapter must handle GFIN ↔ STIX mapping with custom properties for GFIN-specific fields
- OpenCTI confidence (0-100) must map to GFIN confidence (LOW/MEDIUM/HIGH/CONFIRMED)
- GFIN data model authority must be maintained — OpenCTI is a peer, not the source of truth

## Alternatives Considered

- **Adopt OpenCTI as canonical model:** Rejected — GFIN's financial fraud domain requires fields STIX can't natively represent
- **Use MISP only:** Possible but OpenCTI's graph model and connector ecosystem add value
- **Build custom CTI platform:** Rejected — OpenCTI provides needed interoperability
