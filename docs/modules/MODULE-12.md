# Module 12 — IP/ASN Intelligence

**Status:** ACCEPTED
**Accept Date:** 2026-08-26
**Test Count:** 5 tests (within test_domain_intelligence.py::TestIPASNIntelligence)
**Layer:** Layer A (in-memory, MVP)
**Implementation:** `packages/services/domain_intelligence.py` → `IPASNIntelligenceService`

---

## Summary

IP/ASN Intelligence provides IP history tracking, domain-IP linking over time, related domain discovery by shared IP, ASN abuse contact management, and source licensing enforcement. Implemented as `IPASNIntelligenceService` within the domain intelligence module, sharing infrastructure observations with `InfrastructureIntelligenceService` (Module 09).

## Components Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| IPInfo / ASNInfo models | IMPLEMENTED | Inherited from InfrastructureIntelligenceService (Module 09) |
| IPASNIntelligenceService | IMPLEMENTED | IP registration, history, profiles, related domains, abuse contacts |
| IP history tracking | IMPLEMENTED | Historical snapshots per IP address |
| Domain-IP history | IMPLEMENTED | Chronological IP changes per domain |
| Related domains by IP | IMPLEMENTED | Domains sharing the same IP address |
| ASN profiling | IMPLEMENTED | ASN info, provider, country, network CIDR |
| Abuse contacts | IMPLEMENTED | ASN → abuse contact mapping for reporting |
| Source licensing enforcement | IMPLEMENTED | `source_licensed` and `source_type` fields on IP registration |

## Test Coverage

Tests in `tests/unit/test_domain_intelligence.py::TestIPASNIntelligence`:
- `test_register_ip_info` — IP registration with ASN, provider, country, CDN/hosting flags
- `test_register_asn_with_abuse_contact` — ASN registration with abuse contact
- `test_ip_profile` — IP profile with historical snapshots and related domains
- `test_asn_profile` — ASN profile with network info and abuse contact
- `test_domain_ip_history` — domain → chronological IP changes

## Layer B (REQUIRES EXTERNAL INFRASTRUCTURE)

- Real BGP/routing data via RIPEstat / RouteViews
- RDAP IP lookups via RIRs (ARIN, RIPE, APNIC, LACNIC, AFRINIC)
- Abuse contact database integration
- Persistent storage in PostgreSQL/OpenSearch
- Real-time IP change alerting via Kafka

## Acceptance Criteria

- [x] IP history tracking
- [x] Domain-IP linking
- [x] Related domains by IP
- [x] ASN profiling with abuse contacts
- [x] Source licensing enforcement
- [x] Tests passing
- [x] Layer B documented (REQUIRES EXTERNAL INFRASTRUCTURE)
