# GFIN — Cortex Integration Specification

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

Cortex is integrated as a standalone enrichment microservice. It runs independently (without TheHive) with least-privilege access. Analyzer results are treated as observations, NOT facts — they require provenance and confidence scoring before entering GFIN.

## Official Sources

| Resource | URL |
|----------|-----|
| Cortex Core | https://github.com/TheHive-Project/Cortex |
| Cortex Analyzers | https://github.com/TheHive-Project/Cortex-Analyzers |
| Documentation | https://docs.strangebee.com/cortex/ |
| Analyzer Docs | https://thehive-project.github.io/Cortex-Analyzers/ |

## License

- **Cortex Core:** AGPL-3.0
- **Cortex Analyzers:** AGPL-3.0 (per-analyzer)
- **Finding:** API usage likely exempt from AGPL copyleft (similar to MISP), but requires formal legal verification.

## Integration Architecture

```text
GFIN Entity (observable to enrich)
    │
    ▼
Enrichment Request (GFIN Enrichment Service)
    │
    ▼
Cortex Adapter (REST API client)
    │
    ├── POST /api/analyzer/{id}/run (submit observable)
    ├── GET /api/job/{id} (poll status)
    └── GET /api/job/{id}/report (fetch results)
    │
    ▼
Cortex Server (standalone, AGPL-3.0)
    │
    ├── GFIN Organization (dedicated, isolated)
    ├── Service Account (analyze role only)
    ├── Analyzer execution (Docker container mode)
    └── External API keys (centralized, never exposed to GFIN)
    │
    ▼
Result (structured JSON: full + summary taxonomy)
    │
    ▼
Evidence/Observation Normalizer
    │
    ├── Source: Cortex analyzer name
    ├── Retrieval time: job completion timestamp
    ├── Original value: raw analyzer output
    ├── Transformation: taxonomy normalization
    ├── Confidence: per-analyzer confidence
    ├── Classification: from enrichment config
    └── Jurisdiction: from GFIN config
    │
    ▼
GFIN (with provenance + confidence)
```

## Analyzer Categories

| Category | Examples | Observable Types |
|----------|---------|-----------------|
| Threat Intelligence | VirusTotal, AlienVault OTX, MISP, CrowdStrike | IP, Domain, Hash, URL |
| OSINT | Shodan, Censys, PassiveTotal, SecurityTrails | IP, Domain |
| Sandbox | Joe Sandbox, Hybrid Analysis, Any.Run | File, URL |
| Reputation | AbuseIPDB, GreyNoise, URLScan | IP, Domain, URL |
| GeoIP | MaxMind, IPWhois | IP |
| Certificate | Crt.sh | Domain |
| Email | EmailRep, HaveIBeenPwned, EmlParser | Email |
| File Analysis | YARA, FileInfo, ClamAV, NSRL | File |

## Security Model

| Requirement | Implementation |
|-------------|---------------|
| Database access | NONE — Cortex has its own Elasticsearch |
| Communication | REST API only (HTTPS) |
| Authentication | Dedicated API key, `analyze` role only |
| Organization | Dedicated `GFIN_Enrichment` organization in Cortex |
| Analyzer isolation | Docker container mode (ephemeral, non-root) |
| External API keys | Stored in Cortex org settings, never exposed to GFIN |
| Network | Analyzer containers: no route to GFIN internal network |
| Audit | All enrichment requests logged in GFIN audit trail |

## Analyzer Result Handling

**CRITICAL:** Analyzer results are observations, NOT facts.

1. Results are parsed as structured JSON (full + summary taxonomy)
2. Taxonomy levels: `info`, `safe`, `suspicious`, `malicious`
3. Results are normalized to GFIN observation schema
4. Provenance: source = Cortex analyzer name, retrieval = job timestamp
5. Confidence: mapped from taxonomy level (malicious → HIGH, suspicious → MEDIUM, info → LOW)
6. Results NEVER automatically become facts — they require human review or corroboration

### Taxonomy → Confidence Mapping

| Cortex Taxonomy Level | GFIN Confidence |
|----------------------|-----------------|
| malicious | HIGH |
| suspicious | MEDIUM |
| safe | LOW (counter-evidence) |
| info | LOW |

## Deployment (Layer B — REQUIRES EXTERNAL INFRASTRUCTURE)

| Component | Specification |
|-----------|--------------|
| Cortex Core | Docker container (official image) |
| Database | Elasticsearch 8.x (dedicated to Cortex) |
| Worker mode | Docker container execution for analyzers |
| Resources | 4-8 vCPUs, 16+ GB RAM |
| Network | Isolated segment, HTTPS to GFIN |
| K8s | Helm charts available |
| External API keys | VirusTotal, AbuseIPDB, Shodan, etc. |

## POC Plan

1. Deploy Cortex standalone in Docker (Layer B)
2. Configure GFIN_Enrichment organization
3. Create service account with `analyze` role
4. Configure analyzers (VirusTotal, AbuseIPDB, Shodan)
5. Implement Cortex Adapter (REST API client)
6. Test: Enrich IP → verify result ingestion with provenance
7. Test: Enrich domain → verify taxonomy → confidence mapping
8. Verify: Analyzer results are observations, not facts

## Status

| Component | Status |
|-----------|--------|
| Specification | COMPLETE |
| POC | PENDING (Layer B infrastructure required) |
| Adapter implementation | PENDING |
| Integration tests | PENDING |
| Legal review | REQUIRED (AGPL verification) |
