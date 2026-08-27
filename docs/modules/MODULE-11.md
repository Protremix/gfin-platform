# Module 11 — Certificate Intelligence

**Status:** ACCEPTED
**Accept Date:** 2026-08-26
**Test Count:** 4 tests (within test_domain_intelligence.py::TestCertificateIntelligence)
**Layer:** Layer A (in-memory, MVP)
**Implementation:** `packages/services/domain_intelligence.py` → `CertificateIntelligenceService`

---

## Summary

Certificate Intelligence provides certificate timeline tracking, SAN (Subject Alternative Name) indexing, newly observed domain detection via certificates, and certificate relationship mapping. Implemented as `CertificateIntelligenceService` within the domain intelligence module, sharing infrastructure observations with `InfrastructureIntelligenceService` (Module 09).

## Components Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| CertificateObservation model | IMPLEMENTED | Inherited from InfrastructureIntelligenceService (Module 09) |
| CertificateIntelligenceService | IMPLEMENTED | Certificate registration, timeline, SAN index, newly observed domains |
| Certificate timeline tracking | IMPLEMENTED | Chronological certificate history per domain |
| SAN tracking | IMPLEMENTED | SAN domain → certificate domain index for shared-cert discovery |
| Newly observed domains | IMPLEMENTED | Domains appearing in certificates not previously seen |
| Certificate relationships | IMPLEMENTED | Domains sharing certificates, shared issuer analysis |
| Certificate metrics | IMPLEMENTED | Total certs, unique issuers, self-signed count, SAN coverage |

## Test Coverage

Tests in `tests/unit/test_domain_intelligence.py::TestCertificateIntelligence`:
- `test_register_certificate` — certificate registration and observation creation
- `test_certificate_timeline` — chronological timeline per domain
- `test_certificate_relationships` — domains sharing certificates
- `test_certificate_metrics` — aggregate certificate metrics

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- Real Certificate Transparency (CT) log streaming via ct-explorer
- Persistent storage in PostgreSQL/OpenSearch
- Real-time newly-observed-domain alerting via Kafka
- Historical certificate database integration (censys/crt.sh)

## Acceptance Criteria

- [x] Certificate timeline tracking
- [x] SAN tracking and reverse lookup
- [x] Newly observed domain detection
- [x] Certificate relationship mapping
- [x] Tests passing
- [x] Layer B documented (REQUIRES EXTERNAL INFRASTRUCTURE)
