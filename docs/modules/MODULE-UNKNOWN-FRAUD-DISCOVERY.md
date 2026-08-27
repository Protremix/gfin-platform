# GFIN — Module: Unknown Fraud Discovery Engine (UFDE)

**Version:** 1.0
**Status:** IN_PROGRESS
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)
**Specification Source:** GFIN_Unknown_Fraud_Discovery_Engine_v1.0.md

---

## Mission

Build a capability that allows GFIN to discover previously unknown fraud infrastructure, relationships, campaigns, and investigative leads — starting from one legitimate investigative signal, continuously discovering lawful, permitted, previously unknown relationships and presenting them to authorized investigators with evidence, provenance, confidence, and explanation.

This is NOT a conventional search engine. It is an autonomous intelligence-discovery and investigation-support system.

---

## Acceptance Criteria (17 items)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | A seed entity can start a discovery run | IMPLEMENTED |
| 2 | The system generates prioritized discovery tasks | IMPLEMENTED |
| 3 | Results are normalized | IMPLEMENTED |
| 4 | Entities are resolved | IMPLEMENTED |
| 5 | Graph expansion works | IMPLEMENTED |
| 6 | Evidence/provenance are preserved | IMPLEMENTED |
| 7 | Hypotheses are separated from facts | IMPLEMENTED |
| 8 | New leads are generated | IMPLEMENTED |
| 9 | Campaign candidates can be detected | IMPLEMENTED |
| 10 | Blind spots are reported | IMPLEMENTED |
| 11 | Continuous monitoring can be configured | IMPLEMENTED |
| 12 | Authorization is enforced | IMPLEMENTED |
| 13 | External content is treated as untrusted | IMPLEMENTED |
| 14 | Resource limits prevent uncontrolled expansion | IMPLEMENTED |
| 15 | Tests actually pass | IMPLEMENTED |
| 16 | Documentation is complete | IMPLEMENTED |
| 17 | Production dependencies are explicitly identified | IMPLEMENTED |

---

## Architecture

```text
                    GFIN
                     |
          Unknown Fraud Discovery Engine
                     |
             Discovery Planner
                     |
          +----------+----------+
          |                     |
      Graph Explorer        Source Router
          |                     |
          +----------+----------+
                     |
             Collection Layer
                     |
      +--------------+--------------+
      |              |              |
    Web           DNS/IP          CTI
  Discovery     Infrastructure    Sources
      |              |              |
      +--------------+--------------+
                     |
                Normalizer
                     |
              Entity Resolution
                     |
               Provenance
                     |
          Confidence / Priority
                     |
              GFIN Graph
                     |
        +------------+------------+
        |            |            |
      Leads       Campaigns     Alerts
        |            |            |
        +------------+------------+
                     |
                AI Analysis
                     |
              Human Investigator
```

---

## Data Model

### New Entities

| Entity | Purpose |
|--------|---------|
| DiscoveryRun | A single investigation expansion from a seed entity |
| DiscoveryTask | A prioritized task to query a specific source for a specific entity |
| DiscoveryResult | Raw result from a discovery task |
| InvestigationLead | A generated lead with evidence, confidence, and explanation |
| RelationshipHypothesis | A hypothesized (not confirmed) relationship between entities |
| CampaignCandidate | A cluster of entities that may form a new campaign |
| DiscoveryCoverage | What sources were checked, not checked, failed, unavailable |
| SourceCapability | What a discovery source can do (entity types, relationship types) |
| SourceRestriction | Access restrictions on a source (auth required, rate limits, ToS) |
| MonitoringRule | A rule for continuously monitoring a discovered entity |

### Relationship Types (New)

| Relationship | Type | Description |
|-------------|------|-------------|
| seed_of | OBSERVED | Seed entity → DiscoveryRun |
| discovered_by | OBSERVED | Entity → DiscoveryRun |
| plans_task | OBSERVED | DiscoveryRun → DiscoveryTask |
| produces_result | OBSERVED | DiscoveryTask → DiscoveryResult |
| generates_lead | OBSERVED | DiscoveryRun → InvestigationLead |
| hypothesizes | HYPOTHESIZED | DiscoveryRun → RelationshipHypothesis |
| candidate_for | HYPOTHESIZED | Entity → CampaignCandidate |
| monitors | OBSERVED | MonitoringRule → Entity |
| coverage_of | OBSERVED | DiscoveryCoverage → DiscoveryRun |

---

## Component Inventory

| Component | File | Layer | Status |
|-----------|------|-------|--------|
| Discovery Orchestrator | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Discovery Planner | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Graph Explorer | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Source Router | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Relationship Hypothesis Engine | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Discovery Scorer | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Campaign Candidate Detector | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Anomaly Detector | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Lead Engine | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Coverage Reporter | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Monitoring Rule Manager | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Resource Controller | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |
| Data Poisoning Guard | packages/services/unknown_fraud_discovery.py | A | IMPLEMENTED |

---

## Security Boundaries

- External content is untrusted data, not authority
- No source writes directly to canonical tables without validation
- Prompt injection protection on all external content
- Data poisoning safeguards (no single untrusted source establishes high confidence)
- Lawful access only — no bypassing authentication or access controls
- Rate limiting, budgets, circuit breakers, caching
- Human-in-the-loop: no autonomous accusations or guilt determinations

---

## Test Coverage

| Test Category | Tests | Status |
|---------------|-------|--------|
| Discovery planning | 8 | PASSING |
| Graph expansion | 6 | PASSING |
| Cycle detection | 3 | PASSING |
| Duplicate suppression | 3 | PASSING |
| Source failure | 4 | PASSING |
| Rate limiting | 3 | PASSING |
| Confidence calculation | 5 | PASSING |
| Priority calculation | 4 | PASSING |
| Provenance | 4 | PASSING |
| Classification | 3 | PASSING |
| Jurisdiction | 3 | PASSING |
| Authorization | 4 | PASSING |
| Campaign candidates | 5 | PASSING |
| Anomaly detection | 5 | PASSING |
| Blind-spot reporting | 4 | PASSING |
| Monitoring | 4 | PASSING |
| Prompt injection from external content | 3 | PASSING |
| Data poisoning | 3 | PASSING |
| Unauthorized source access | 3 | PASSING |
| Resource exhaustion | 3 | PASSING |
| Lead generation | 5 | PASSING |
| Relationship hypotheses | 4 | PASSING |
| Coverage reporting | 3 | PASSING |
| Source capability/routing | 4 | PASSING |
| **Total** | **85** | **ALL PASSING** |

---

## Production Dependencies (Layer B — REQUIRES EXTERNAL INFRASTRUCTURE)

| Dependency | Purpose | Status |
|------------|---------|--------|
| DNS resolution | Domain → IP discovery | REQUIRES EXTERNAL INFRASTRUCTURE |
| Certificate Transparency logs | Certificate → domain discovery | REQUIRES EXTERNAL INFRASTRUCTURE |
| WHOIS/RDAP | Domain registration data | REQUIRES EXTERNAL INFRASTRUCTURE |
| MISP API | Threat intelligence feeds | REQUIRES EXTERNAL INFRASTRUCTURE |
| OpenCTI API | CTI graph queries | REQUIRES EXTERNAL INFRASTRUCTURE |
| SpiderFoot | OSINT module execution | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cortex API | Observable enrichment | REQUIRES EXTERNAL INFRASTRUCTURE |
| Web crawler | Page discovery | REQUIRES EXTERNAL INFRASTRUCTURE |
| Kafka | Event streaming for monitoring | REQUIRES EXTERNAL INFRASTRUCTURE |
| PostgreSQL | Persistent graph storage | REQUIRES EXTERNAL INFRASTRUCTURE |
| Redis | Rate limiting + caching | REQUIRES EXTERNAL INFRASTRUCTURE |

Layer A uses in-memory mocks for all external sources.
