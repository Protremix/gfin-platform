# Module 10 — Domain Intelligence

**Status:** ACCEPTED
**Accept Date:** 2026-08-26
**Test Count:** 22 tests (across modules 10-12 combined)
**Layer:** Layer A (in-memory, MVP)
**Implementation:** `packages/services/domain_intelligence.py`

---

## Summary

Domain Intelligence provides RDAP-based domain profiling, domain lifecycle tracking, related domain discovery, and links to fraud reports and campaigns. Implemented as `DomainIntelligenceService` within the domain intelligence module.

## Components Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| DomainProfile model | IMPLEMENTED | Pydantic model with registration, expiry, status, NS, related domains |
| DomainIntelligenceService | IMPLEMENTED | RDAP profile building, related domain discovery, fraud report/campaign linking |
| Domain lifecycle tracking | IMPLEMENTED | Registration date, expiry, status (active/expired/pending) |
| Related domain discovery | IMPLEMENTED | By shared NS, shared IP, shared certificate SAN |
| Fraud report/campaign links | IMPLEMENTED | Links domain profiles to fraud reports and campaigns |

## Test Coverage

Tests in `tests/unit/test_domain_intelligence.py`:
- `TestDomainIntelligence` — domain profile creation, related domain discovery, lifecycle tracking, fraud report/campaign linking

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- Real RDAP lookups via IANA/bootstrap registry
- WHOIS data integration (where licensed)
- Persistent storage in PostgreSQL/OpenSearch
- Distributed caching (Redis) for domain profile lookups

## Acceptance Criteria

- [x] Domain profile model with lifecycle tracking
- [x] Related domain discovery (NS, IP, certificate)
- [x] Fraud report and campaign linking
- [x] Tests passing
- [x] Layer B documented (REQUIRES EXTERNAL INFRASTRUCTURE)
