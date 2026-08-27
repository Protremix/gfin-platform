# ADR-011: Cortex Integration as Standalone Enrichment Service

**Status:** ACCEPTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

GFIN needs automated observable enrichment (IP reputation, domain analysis, hash lookup, email breach check). Cortex provides 150+ analyzers (300+ flavors) and can run standalone without TheHive.

## Decision

**INTEGRATE Cortex as a standalone enrichment microservice with least-privilege access.**

Cortex runs independently with its own Elasticsearch. GFIN communicates via REST API. Analyzer results are observations, NOT facts — they require provenance and confidence scoring.

## Rationale

1. **Standalone capable:** Cortex works without TheHive — manages its own users, DB, API
2. **150+ analyzers:** Comprehensive enrichment for IP, domain, hash, email, file
3. **Security isolation:** Zero access to GFIN production database, API-only communication
4. **Docker execution:** Analyzers run in isolated containers with least privilege
5. **Centralized API keys:** External service credentials managed in Cortex, never exposed to GFIN

## Consequences

- GFIN must deploy Cortex + dedicated Elasticsearch (Layer B infrastructure)
- Legal counsel must verify AGPL API-use exemption (similar to MISP)
- Analyzer results are observations with taxonomy → confidence mapping
- Results NEVER automatically become facts — require human review or corroboration
- GFIN must manage external API keys (VirusTotal, Shodan, AbuseIPDB) in Cortex org settings

## Alternatives Considered

- **Build custom analyzers:** Rejected — 150+ analyzers provide immediate value
- **Use SpiderFoot for enrichment:** Partially overlaps but SpiderFoot is discovery-focused, not enrichment-focused
- **Integrate TheHive + Cortex:** Rejected — TheHive rejected (ADR-010), Cortex runs standalone
