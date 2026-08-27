# ADR-009: STIX 2.x / TAXII 2.x as Interoperability Standards

**Status:** ACCEPTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

GFIN needs standardized formats for cross-organization intelligence sharing with police, CTI organizations, and financial institutions. STIX 2.x provides the expression format; TAXII 2.x provides the exchange protocol.

## Decision

**ADOPT STIX 2.1 as the interoperability format and TAXII 2.1 as the exchange protocol.**

STIX is NOT the GFIN internal data model. GFIN's canonical schema (defined in `packages/schemas/`) remains authoritative. STIX is used for import/export and cross-organization sharing only.

GFIN fields not natively representable in STIX (classification, jurisdiction, source restrictions, org isolation) are carried as custom `x_gfin_*` properties.

## Rationale

1. **OASIS standard:** Freely implementable, no licensing concerns
2. **BSD-3 libraries:** Official Python libraries (stix2, taxii2-client) are permissive
3. **Industry standard:** Used by MISP, OpenCTI, SIEMs, and law enforcement globally
4. **POC verified:** 20 passing tests demonstrate round-trip fidelity
5. **Extensible:** STIX 2.1 extension definitions support custom properties

## Consequences

- GFIN must maintain STIX ↔ GFIN mapping table (see `docs/integrations/stix-taxii.md`)
- Custom `x_gfin_*` properties must be registered formally
- TAXII Gateway must enforce policy: classification, jurisdiction, source restriction checks
- Outbound sharing: only PUBLIC and COMMUNITY data may be exported externally
- POC implemented: `packages/common/stix_adapter.py` with 20 passing tests

## Alternatives Considered

- **Custom JSON format:** Rejected — loses interoperability with MISP, OpenCTI, police systems
- **STIX as canonical model:** Rejected — STIX can't represent GFIN's classification, jurisdiction, org isolation
- **MISP format only:** Rejected — STIX is more widely adopted for cross-org sharing
