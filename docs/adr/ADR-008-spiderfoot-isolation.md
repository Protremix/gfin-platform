# ADR-008: SpiderFoot Isolation Strategy

**Status:** ACCEPTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

GFIN needs automated OSINT discovery capabilities (domain enumeration, IP reputation, email breach lookup, dark web monitoring). SpiderFoot provides 233 modules but must not be given access to GFIN production data.

## Decision

**ISOLATE SpiderFoot in an ephemeral Docker container with no database access.**

SpiderFoot runs as a discovery worker. It receives target data (domain, IP, email) and returns raw JSON results. Results are normalized and ingested through the GFIN Ingestion Gateway with full provenance.

## Rationale

1. **Security:** SpiderFoot must never access GFIN's production intelligence database
2. **MIT license:** No copyleft restrictions
3. **233 modules:** Comprehensive OSINT coverage (reputation, DNS, dark web, breaches)
4. **Isolation pattern:** Matches GFIN's untrusted content boundary principle
5. **Ephemeral execution:** Container destroyed after scan, results exported via API

## Consequences

- GFIN must maintain SpiderFoot modules as third-party APIs evolve (maintenance risk: development slowed since Nov 2023)
- Each scan requires an isolated container (Layer B: Kubernetes Job or Docker)
- API keys for data providers must be managed per-scan, never stored in container
- Results are observations with provenance, NOT facts

## Alternatives Considered

- **Run SpiderFoot as persistent service:** Rejected — security risk, resource waste
- **Build custom OSINT modules:** Possible but 233 modules provide immediate value
- **Use only free API sources:** Possible but limits coverage significantly
