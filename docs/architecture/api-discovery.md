# GFIN API Discovery Architecture

## Overview
The API Discovery Engine continuously discovers lawful data sources (APIs, feeds, providers) that can improve investigations.

## Architecture
```
GPT BRAIN -> Evidence Gap -> API Discovery Engine -> Source Registry ->
Policy/Authorization -> Connector -> Provider -> Evidence -> Graph -> GPT BRAIN
```

## Key Principles
1. GFIN is investigative, not intrusive — no authentication bypass
2. Sources must be registered before use — no unregistered external access
3. All provider responses are untrusted DATA — protect against prompt injection
4. Credentials never exposed — never in prompts, logs, evidence, or reports
5. Discovery is continuous — periodically refresh source catalog

## Source Categories
- Developer portals, Government open data, Law enforcement catalogs
- Financial/regulatory, Blockchain data, Threat intelligence
- Social platforms, Advertising, Geospatial, Company registries
- Court/government, Telecom, Archival, Search/index, Licensed intelligence

## Quality Scoring (10 dimensions)
authority, reliability, freshness, coverage, independence, provenance,
availability, latency, cost, legal_usability

## Access Status
- FOUND_AND_ACCESSIBLE
- FOUND_BUT_AUTH_REQUIRED
- FOUND_BUT_NOT_SUPPORTED
- NOT_FOUND

Version: 1.0.0
