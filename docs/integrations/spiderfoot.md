# GFIN — SpiderFoot Integration Specification

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

SpiderFoot is integrated as an isolated OSINT discovery worker. It runs in a contained environment with NO direct access to GFIN production databases. All results are treated as untrusted observations requiring provenance and validation.

## Official Sources

| Resource | URL |
|----------|-----|
| Repository | https://github.com/smicallef/spiderfoot |
| Website | https://www.spiderfoot.net/ |
| Documentation | https://www.spiderfoot.net/documentation/ |
| Docker | Official Dockerfile + docker-compose |

## License

- **SpiderFoot v4.0:** MIT License (relicensed April 2022; previously GPLv3)
- **Finding:** MIT permits commercial use, modification, and integration without restrictions.

## Maintenance Risk

- Last commit: November 5, 2023 (commit #1822)
- Development has slowed significantly
- GFIN may need to maintain custom modules as third-party APIs evolve
- **Risk Level:** MEDIUM — stable but low activity

## Integration Architecture

```text
GFIN Discovery Orchestrator
    │
    ▼
SpiderFoot Adapter
    │
    ├── Start scan (CLI or API)
    ├── Configure modules (per target type)
    └── Set rate limits and thread pool
    │
    ▼
Isolated Discovery Worker (Docker container)
    │
    ├── NO access to GFIN database
    ├── Restricted network (egress allowlist only)
    ├── Resource limits (CPU, memory, disk)
    └── Ephemeral execution (results exported, container destroyed)
    │
    ▼
Raw Results (JSON)
    │
    ▼
Normalizer + Provenance Assignment
    │
    ├── Source: SpiderFoot module name
    ├── Retrieval time: scan completion timestamp
    ├── Original value: raw result data
    ├── Transformation: normalization applied
    ├── Confidence: per-module confidence
    ├── Classification: from scan configuration
    └── Jurisdiction: from target or scan config
    │
    ▼
GFIN Entity / Observation / Evidence
```

## Module Categories

| Category | Count | Examples |
|----------|-------|---------|
| Reputation Systems | 67 | VirusTotal, AbuseIPDB, GreyNoise, AlienVault OTX |
| Search Engines | 47 | Google, Bing, Shodan, Censys |
| Content Analysis | 27 | Web scraping, technology detection, credential extraction |
| Crawling & Scanning | 20 | Web spidering, port scanning, CMS detection |
| Passive DNS | 15 | SecurityTrails, DNSDB, Hackertarget |
| Leaks & Breaches | 24 | HaveIBeenPwned, DeHashed, LeakIX |
| Social Media | 11 | Twitter, Keybase, Gravatar |
| DNS Enumeration | 10 | Subdomain brute-forcing, zone transfers |
| Public Registries | 17 | ARIN, RIPE, OpenCorporates, GLEIF |
| Dark Web | 5 | Tor exit nodes, Ahmia, OnionSearch |

## Security Isolation

| Requirement | Implementation |
|-------------|---------------|
| Database access | NONE — SpiderFoot has its own SQLite |
| Network access | Restricted egress allowlist (API endpoints only) |
| Filesystem | Ephemeral container, results exported via API |
| Credentials | Per-scan API keys, never stored in container |
| Resource limits | CPU: 2 cores, Memory: 2GB, Disk: 10GB |
| Audit | All scan operations logged in GFIN |
| Execution | Ephemeral container, destroyed after scan |

## Legal Considerations

- API ToS compliance required per data provider
- Passive vs Active mode selection per target
- Rate limiting per provider requirements
- Data retention per provider terms
- GFIN must maintain its own API keys for each provider

## POC Plan

1. Deploy SpiderFoot in isolated Docker container (Layer B)
2. Configure modules for fraud-relevant targets (domains, IPs, emails)
3. Implement SpiderFoot Adapter (CLI-based, parse JSON output)
4. Test: Scan a known fraudulent domain → verify GFIN ingestion
5. Verify: Provenance, classification, confidence on all imported data
6. Test: Active vs passive mode restrictions
7. Verify: No database access from SpiderFoot container

## Status

| Component | Status |
|-----------|--------|
| Specification | COMPLETE |
| POC | PENDING (Layer B infrastructure required) |
| Adapter implementation | PENDING |
| Integration tests | PENDING |
| Legal review | REQUIRED (API ToS per provider) |
