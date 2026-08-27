# GFIN — Architecture: Unknown Fraud Discovery Engine

**Version:** 1.0
**Status:** IMPLEMENTED (Layer A)
**Date:** 2026-08-26

---

## Overview

The Unknown Fraud Discovery Engine (UFDE) is an autonomous intelligence-discovery and investigation-support system. Starting from one seed entity, it continuously discovers lawful, permitted, previously unknown relationships and intelligence leads, presenting them to authorized investigators with evidence, provenance, confidence, and explanation.

## Architecture Diagram

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

## Components

| Component | Responsibility |
|-----------|---------------|
| DiscoveryOrchestrator | Manages full discovery run from seed to leads |
| DiscoveryPlanner | Decides what to investigate next (prioritized tasks) |
| SourceRouter | Routes tasks to appropriate sources (mock in Layer A) |
| GraphExplorer | Expands investigation graph with cycle detection + dedup |
| RelationshipHypothesizer | Generates observed/derived/hypothesized relationships |
| DiscoveryScorer | Calculates evidence confidence + investigation priority |
| DataPoisoningGuard | Prevents single untrusted sources from high confidence |
| CampaignCandidateDetector | Identifies clusters that may form new campaigns |
| AnomalyDetector | Detects anomalous patterns (anomaly ≠ fraud) |
| LeadEngine | Generates leads with full explanation |
| CoverageReporter | Reports checked/not-checked/unavailable sources |
| MonitoringRuleManager | Configures continuous monitoring for discovered entities |
| ResourceController | Enforces rate limits, budgets, prevents explosion |

## Data Flow

1. Seed Entity → DiscoveryPlanner generates prioritized tasks
2. SourceRouter executes tasks against sources
3. GraphExplorer adds results to investigation graph (with dedup + cycle detection)
4. RelationshipHypothesizer generates hypotheses for inferred relationships
5. DiscoveryScorer calculates confidence and priority (separate metrics)
6. DataPoisoningGuard validates confidence against single-source rules
7. AnomalyDetector identifies anomalous patterns
8. CampaignCandidateDetector identifies potential new campaigns
9. LeadEngine generates investigative leads with full explanation
10. CoverageReporter generates blind-spot report
11. MonitoringRuleManager creates monitoring rules for high-priority entities

## Security Boundaries

- External content is untrusted data, not authority
- No source writes to canonical tables without validation
- Prompt injection protection on all external content
- Data poisoning safeguards (no single untrusted source → high confidence)
- Lawful access only — no bypassing authentication
- Rate limiting, budgets, circuit breakers
- Human-in-the-loop: no autonomous accusations or guilt determinations
- Authorization enforced per source (investigator vs police_officer)

## Layer A vs Layer B

| Component | Layer A (In-Memory) | Layer B (Production) |
|-----------|-------------------|---------------------|
| SourceRouter | Mock sources returning simulated results | Real DNS, CT, WHOIS, MISP, OpenCTI, Cortex |
| GraphExplorer | In-memory dict | PostgreSQL + Neo4j |
| Monitoring | In-memory rules | Kafka + scheduled workers |
| ResourceController | In-memory counters | Redis rate limiting |
| CoverageReporter | Static source list | Dynamic source registry |
