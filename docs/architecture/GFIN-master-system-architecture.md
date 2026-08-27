# GFIN — Master System Architecture

**Version:** 1.0
**Status:** LIVING DOCUMENT — Updated as modules are added
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)
**Directive Source:** GFIN_Autonomous_Global_Fraud_Intelligence_Master_Directive_v1.0.md (44 sections)

---

## 1. System Mission

GFIN is an autonomous, international fraud-intelligence and investigation-support platform. Its purpose is to discover, correlate, understand, monitor, and expose relationships between digital-fraud indicators across sources that GFIN is legally and technically authorized to access.

> Turn fragmented fraud signals into a continuously expanding, evidence-based intelligence graph that can discover previously unknown relationships and investigative leads.

The core product loop:

```text
SOURCE
  ↓
OBSERVATION
  ↓
VALIDATION
  ↓
ENTITY RESOLUTION
  ↓
RELATIONSHIP
  ↓
GRAPH
  ↓
DISCOVERY
  ↓
CORRELATION
  ↓
LEAD
  ↓
MONITORING
  ↓
ALERT
```

---

## 2. Master System Diagram

```text
Citizens                         Police
  │                                │
  ▼                                ▼
PUBLIC LAYER                    LAW ENFORCEMENT LAYER
  │                                │
  ▼                                ▼
  ┌─────────────────────────────────────────────────┐
  │              INGESTION GATEWAY                   │
  │  Validation → Normalization → Dedup → Provenance │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │              SOURCE ECOSYSTEM                    │
  │                                                  │
  │  DNS  │  RDAP  │  CT Logs  │  WHOIS  │  Web     │
  │  MISP │  OpenCTI │  SpiderFoot │  Cortex       │
  │  STIX/TAXII  │  Crypto  │  Police Connectors    │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │           ENTITY RESOLUTION                     │
  │  Normalizers → Matchers → Dedup → Merge/Split    │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │           CLASSIFICATION & JURISDICTION          │
  │  5 Levels │ Org Isolation │ Access Controls       │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │           INTELLIGENCE GRAPH                     │
  │  Entities │ Relationships │ Evidence │ Provenance │
  │  30+ Entity Types │ 20+ Relationship Types       │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │        UNKNOWN FRAUD DISCOVERY ENGINE            │
  │  Planner → Source Router → Graph Explorer        │
  │  Hypothesizer → Scorer → Campaign Detector       │
  │  Anomaly Detector → Lead Engine → Coverage       │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │           CORRELATION & CAMPAIGNS                │
  │  Multi-source correlation │ Campaign Engine      │
  │  Campaign Candidates → Promotion → Confirmed     │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │              AI GATEWAY                          │
  │  Model Router (OpenAI/Local/Other)               │
  │  Classification-aware routing │ Evidence-first    │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │         INVESTIGATIVE LEADS & ALERTS              │
  │  Leads (with explanation) │ Alerts │ Monitoring  │
  └──────────────────────┬──────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────┐
  │           HUMAN INVESTIGATOR                      │
  │  Inspect │ Confirm │ Reject │ Expand │ Escalate  │
  └─────────────────────────────────────────────────┘
```

This diagram represents **actual architecture**, not marketing claims.

---

## 3. Component Map

### Core Infrastructure (Layer A: In-Memory, Layer B: Production)

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Canonical Data Model | 03 | IMPLEMENTED (26 entities, 20 rels) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Security & Identity | 02 | IMPLEMENTED (RBAC+ABAC, audit) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Evidence Vault | 06 | IMPLEMENTED (custody, hash, access) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Event Bus | 05 | IMPLEMENTED (pub/sub, retry, DLQ) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Search Platform | 07 | IMPLEMENTED (9 search types) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Intelligence Layer

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Entity Resolution | 04 | IMPLEMENTED (11 normalizers) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Web Discovery Engine | 08 | IMPLEMENTED (crawl, policy) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Infrastructure Intelligence | 09 | IMPLEMENTED (DNS, IP, ASN, certs) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Domain Intelligence | 10 | IMPLEMENTED (RDAP, profiles) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Certificate Intelligence | 11 | IMPLEMENTED (timelines, SANs) | REQUIRES EXTERNAL INFRASTRUCTURE |
| IP/ASN Intelligence | 12 | IMPLEMENTED (history, abuse) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Unknown Fraud Discovery Engine | UFDE | IMPLEMENTED (96 tests) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Fraud Reporting | 14 | IMPLEMENTED (triage, scoring) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Fraud Detection | 15 | IMPLEMENTED (signals, patterns) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Campaign Engine | 16 | IMPLEMENTED (detection, lifecycle) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Continuous Monitoring | 17 | IMPLEMENTED (subscriptions, alerts) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Alert Engine | 18 | IMPLEMENTED (routing, escalation) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Anomaly Detection | UFDE | IMPLEMENTED (4 types) | REQUIRES EXTERNAL INFRASTRUCTURE |

### AI Layer

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Model Gateway | 19 | IMPLEMENTED (provider abstraction) | REQUIRES EXTERNAL INFRASTRUCTURE |
| OpenAI Gateway | 20 | IMPLEMENTED (gpt-5.6-luna) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Local AI | 21 | IMPLEMENTED (classifier, embeddings) | REQUIRES EXTERNAL INFRASTRUCTURE |
| AI Investigation Orchestrator | 22 | IMPLEMENTED (15 tools, authz) | REQUIRES EXTERNAL INFRASTRUCTURE |
| AI Evaluation | 37 | IMPLEMENTED (7 metrics) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Federation Layer

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Police API | 23 | IMPLEMENTED (8 endpoints) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Police Connector SDK | 24 | IMPLEMENTED (8 methods) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Global Matching | 25 | IMPLEMENTED (cross-border) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cross-Border Requests | 26 | IMPLEMENTED (7-stage workflow) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Police Console | 27 | IMPLEMENTED (dashboard, cases) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Federation | 32 | IMPLEMENTED (node network) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Citizen Layer

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Citizen Platform | 13 | IMPLEMENTED (entity check, reports) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Multilingual | 29 | IMPLEMENTED (10 langs) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Intelligence & Crypto

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Crypto Intelligence | 28 | IMPLEMENTED (6 blockchains) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Global Early Warning | 31 | IMPLEMENTED (4 levels) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Analytics | 30 | IMPLEMENTED (trends, dashboard) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Operations Layer

| Component | Module | Layer A Status | Layer B Status |
|-----------|--------|---------------|----------------|
| Compliance | 33 | IMPLEMENTED (5 classifications) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Observability | 34 | IMPLEMENTED (metrics, tracing) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Disaster Recovery | 35 | IMPLEMENTED (backup, failover) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Security Testing | 36 | IMPLEMENTED (checklist, findings) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Load Testing | 38 | IMPLEMENTED (scenarios, thresholds) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Pilot | 39 | IMPLEMENTED (participants, feedback) | REQUIRES EXTERNAL INFRASTRUCTURE |
| Production | 40 | IMPLEMENTED (readiness checklist) | REQUIRES EXTERNAL INFRASTRUCTURE |

### Interoperability

| Component | Status | Layer A | Layer B |
|-----------|--------|---------|---------|
| STIX 2.x Adapter | IMPLEMENTED | 21 tests passing | REQUIRES EXTERNAL INFRASTRUCTURE |
| MISP Integration | SPECIFICATION | ADR-006 accepted | PENDING (Layer B) |
| OpenCTI Integration | SPECIFICATION | ADR-007 accepted | PENDING (Layer B) |
| SpiderFoot Integration | SPECIFICATION | ADR-008 accepted | PENDING (Layer B) |
| TheHive | REJECTED | N/A | N/A |
| Cortex Integration | SPECIFICATION | ADR-011 accepted | PENDING (Layer B) |
| TAXII Gateway | SPECIFICATION | ADR-009 accepted | PENDING (Layer B) |

---

## 4. Data Flow

### Inbound: External Source → GFIN Graph

```text
External Source (MISP, DNS, Web, Police, Citizen Report, CTI Feed)
    ↓
Adapter (PyMISP, DNS resolver, Web crawler, Police Connector, STIX)
    ↓
Raw Observation (untrusted data)
    ↓
Validation (schema, injection detection, sanitization)
    ↓
Normalization (canonical schema mapping)
    ↓
Entity Resolution (dedup, merge, split)
    ↓
Provenance Assignment (source, time, reliability, transformation)
    ↓
Classification (PUBLIC / COMMUNITY / RESTRICTED / LAW_ENFORCEMENT / HIGHLY_RESTRICTED)
    ↓
Jurisdiction Tagging
    ↓
GFIN Canonical Model
    ↓
GFIN Intelligence Graph
```

### Discovery: Seed → Lead

```text
Seed Entity
    ↓
Discovery Planner (prioritized tasks by entity type)
    ↓
Source Router (routes to appropriate sources)
    ↓
Collection (executes tasks against sources)
    ↓
Graph Explorer (BFS expansion, cycle detection, dedup)
    ↓
Relationship Hypothesizer (OBSERVED / DERIVED / HYPOTHESIZED)
    ↓
Discovery Scorer (confidence + priority, separate metrics)
    ↓
Data Poisoning Guard (single source cap, multi-source requirement)
    ↓
Anomaly Detector (infrastructure concentration, cert reuse, cross-border)
    ↓
Campaign Candidate Detector (clusters → CAMPAIGN_CANDIDATE)
    ↓
Lead Engine (leads with evidence, explanation, confidence)
    ↓
Coverage Reporter (checked, not checked, failed, unavailable)
    ↓
Monitoring Rule Manager (TTL-based monitoring for high-priority entities)
    ↓
Human Investigator (confirm, reject, expand, escalate)
```

### Outbound: GFIN → External Consumer

```text
GFIN Intelligence
    ↓
Policy Filter (classification, jurisdiction, source restrictions)
    ↓
Classification Check (PUBLIC / COMMUNITY only for external sharing)
    ↓
Source Restriction Check
    ↓
STIX Adapter (GFIN → STIX 2.1)
    ↓
TAXII Gateway (policy-filtered exchange)
    ↓
External Consumer (Police, CTI organization, partner)
```

---

## 5. Intelligence Graph

### Entity Types (30+)

| Category | Entities |
|----------|----------|
| Identity | Person, Organization |
| Communication | Phone, Email |
| Infrastructure | Domain, URL, IP, ASN, Server, Certificate, DNS |
| Financial | CryptoWallet, Transaction, PaymentIdentifier |
| Intelligence | Report, Campaign, Case, Evidence, Observation |
| Discovery | DiscoveryRun, DiscoveryTask, DiscoveryResult, InvestigationLead, RelationshipHypothesis, CampaignCandidate, DiscoveryCoverage, SourceCapability, SourceRestriction, MonitoringRule |
| System | User, Source |

### Relationship Types (20+)

| Type | Description |
|------|-------------|
| resolves_to | Domain → IP (OBSERVED) |
| belongs_to_asn | IP → ASN (OBSERVED) |
| has_certificate | Domain → Certificate (OBSERVED) |
| has_san | Certificate → Domain (OBSERVED) |
| registered_by | Domain → Organization (OBSERVED) |
| reported_in | Entity → Report (OBSERVED) |
| associated_with | Entity → Entity (OBSERVED/HYPOTHESIZED) |
| part_of | Entity → Campaign (OBSERVED/HYPOTHESIZED) |
| potentially_related_to | Entity → Entity (HYPOTHESIZED) |
| sent_to / received_from | Wallet → Wallet (OBSERVED) |
| linked_to_case | Entity → Case (OBSERVED) |
| indicates | Entity → Campaign (HYPOTHESIZED) |
| discovered_by | Entity → DiscoveryRun (OBSERVED) |
| generates_lead | DiscoveryRun → InvestigationLead (OBSERVED) |
| monitors | MonitoringRule → Entity (OBSERVED) |

### Relationship Certainty Levels

| Level | Meaning |
|-------|---------|
| OBSERVED | Direct evidence from a source |
| DERIVED | Deterministic transformation supports it |
| HYPOTHESIZED | Multiple signals suggest it, evidence incomplete |
| CONFIRMED | Independent evidence confirms it |
| REJECTED | Evidence disproves it |

---

## 6. Source Ecosystem

### Source Categories

| Category | Sources | Layer A | Layer B |
|----------|---------|---------|---------|
| Public Web | Web crawler, public pages | Mock | REQUIRES INFRASTRUCTURE |
| Domain/Network | DNS, RDAP, WHOIS, CT logs | Mock | REQUIRES INFRASTRUCTURE |
| IP/ASN | IP intelligence, reverse DNS | Mock | REQUIRES INFRASTRUCTURE |
| Threat Intel | MISP, OpenCTI, STIX/TAXII | Mock + STIX POC | REQUIRES INFRASTRUCTURE |
| OSINT | SpiderFoot | Mock | REQUIRES INFRASTRUCTURE |
| Enrichment | Cortex | Mock | REQUIRES INFRASTRUCTURE |
| Crypto | Blockchain data, analytics | Mock | REQUIRES INFRASTRUCTURE |
| Law Enforcement | Police connectors, federation | Mock | REQUIRES INFRASTRUCTURE |
| Citizen | User reports, entity check | IMPLEMENTED | REQUIRES INFRASTRUCTURE |

### Source Authorization Matrix

| Source | Investigator | Police Officer | Admin |
|--------|-------------|----------------|-------|
| DNS / RDAP / WHOIS / CT | ✓ | ✓ | ✓ |
| Web crawler | ✓ | ✓ | ✓ |
| MISP | ✓ (auth required) | ✓ | ✓ |
| OpenCTI | ✓ (auth required) | ✓ | ✓ |
| Cortex | ✓ (auth required) | ✓ | ✓ |
| SpiderFoot | ✓ | ✓ | ✓ |
| Police Database | ✗ | ✓ | ✓ |
| Crypto Intelligence | ✓ | ✓ | ✓ |

---

## 7. AI Architecture

```text
GFIN Evidence
    ↓
Normalized Intelligence
    ↓
Context Builder
    ↓
AI Gateway (Model Gateway)
    ├── OpenAI (gpt-5.6-luna) — classification-aware routing
    ├── Local AI — for RESTRICTED/HIGHLY_RESTRICTED data
    └── Other approved providers
    ↓
Model Router (routes by data classification)
    ↓
AI Analysis
    ↓
Structured Result (with evidence references)
    ↓
Human / System Decision
```

### AI Rules (Per Directive §20, §22, §39)

- AI is the reasoning layer, NOT the database of truth
- AI must NOT fabricate evidence
- Every material conclusion must reference evidence used
- AI-generated relationships must NEVER silently become facts
- External content is DATA, not AUTHORITY
- External content must not control AI (prompt injection protection)
- Evidence-first: Source → Observation → Evidence → Relationship → Context → AI
- Never: Internet → AI → "Fact"

---

## 8. Security Model

### Principles (Per Directive §24)

| Principle | Implementation |
|-----------|---------------|
| Zero trust | Every request authenticated and authorized |
| Least privilege | Users get minimum access needed |
| Default deny | Access denied unless explicitly granted |
| Classification-aware | 5 levels enforced on all data |
| Jurisdiction-aware | Cross-border sharing restricted |
| Organization isolation | Per-org data scoping |
| Encryption | TLS in transit, encryption at rest (Layer B) |
| Auditability | All actions logged with actor, action, timestamp |
| Secret management | Secrets in environment, never in code |
| External content = DATA | Not AUTHORITY — cannot override system instructions |

### Classification Levels

| Level | Who Can Access | AI Routing |
|-------|---------------|------------|
| PUBLIC | Everyone | OpenAI (external) |
| COMMUNITY | Authenticated users | OpenAI (external) |
| RESTRICTED | Authorized investigators | OpenAI if authorized |
| LAW_ENFORCEMENT | Police officers | Local models only |
| HIGHLY_RESTRICTED | Senior officers | Local models only |

### Prompt Injection Protection

| Layer | Implementation |
|-------|---------------|
| Untrusted-content isolation | External content sandboxed before AI processing |
| Tool authorization boundaries | AI tools have scoped permissions |
| System/developer instruction separation | System prompts separate from external data |
| Evidence constraints | AI operates on structured evidence, not raw internet |
| Least-privilege tool access | Tools limited to minimum needed |
| Regex detection | `detect_prompt_injection()` + `sanitize_for_ai()` |

**NOTE:** Regex detection is DETECTION ONLY, not complete prevention. Architecture uses multiple layers (§8 of directive).

---

## 9. Police Federation

```text
Police Organization A          Police Organization B
        │                              │
        ▼                              ▼
   Police Connector              Police Connector
        │                              │
        ▼                              ▼
   ┌─────────────────────────────────────────────┐
   │              GFIN Federation Layer          │
   │  Org Identity │ Scoped API │ Classification  │
   │  Jurisdiction Policy │ Audit Trail │ Rate   │
   └──────────────────────┬──────────────────────┘
                          │
          GFIN Intelligence Graph (classification-aware)
```

### Federation Rules (Per Directive §25, §26)

- Each police org receives: identity, credentials, scoped API, classification policy, jurisdiction policy, audit trail, rate limits
- Federation preserves source ownership
- No centralizing restricted source data unnecessarily
- Police org retains source documents in its own environment
- Cross-border requests follow 7-stage workflow (submit→validate→authorize→route→review→decide→close)
- Never assume all countries can legally share the same data

---

## 10. Citizen Network

```text
Citizen
    ↓
Entity Check (PUBLIC sources only)
    ↓
Result: SAFE / CAUTION / DANGER (with explanation)
    ↓
Optional: Report Submission (UNVERIFIED)
    ↓
Validation → Normalization → Correlation → Graph
```

### Citizen Rules (Per Directive §12, §13)

- Citizen submissions enter as UNVERIFIED OBSERVATIONS
- Never expose private police intelligence to ordinary users
- Entity check uses PUBLIC sources only
- Risk-oriented response with explanation and limitations
- Never make unsupported accusations

---

## 11. Provenance

Every discovery, observation, relationship, and lead must retain:

| Field | Description |
|-------|-------------|
| source | Which source produced this |
| retrieval_time | When the data was retrieved |
| observation_time | When the event occurred |
| raw_reference | Original value before transformation |
| transformation | What normalization was applied |
| connector | Which adapter produced this |
| connector_version | Version of the adapter |
| confidence | 0.0-1.0 (with method documented) |
| classification | One of 5 levels |
| jurisdiction | Legal jurisdiction |
| organization | Owning organization |
| authorization_basis | Legal basis for acquisition (if required) |

---

## 12. Autonomous Discovery

### Discovery Loop (Per Directive §3, §14, §15)

```text
NEW SIGNAL
    ↓
DISCOVER (Discovery Planner → Source Router → Collection)
    ↓
ENRICH (Cortex, OpenCTI, MISP)
    ↓
CORRELATE (multi-source correlation)
    ↓
RESOLVE ENTITIES (Entity Resolution)
    ↓
EXPAND GRAPH (Graph Explorer with limits)
    ↓
DETECT PATTERNS (Anomaly Detector)
    ↓
GENERATE LEADS (Lead Engine with explanation)
    ↓
MONITOR (Monitoring Rule Manager)
    ↓
NEW SIGNAL (from monitoring or new report)
    ↓
REPEAT
```

### Resource Controls (Per Directive §14)

| Control | Default | Configurable |
|---------|---------|-------------|
| Max depth | 5 | ✓ |
| Max nodes | 100 | ✓ |
| Max tasks | 50 | ✓ |
| Max runtime | 300s | ✓ |
| Per-source budget | 10 queries | ✓ |
| Rate limit | 60/min | ✓ |
| Concurrency | 5 | ✓ |

---

## 13. Monitoring

### Monitoring Flow (Per Directive §18)

```text
Important Entity Discovered
    ↓
Monitoring Rule Created (TTL-based)
    ↓
Monitor: DNS, certificates, IP, reports, feeds
    ↓
Change Detected
    ↓
Validate → Correlate → Recalculate → Alert
```

### TTL Policy

| Priority | TTL |
|----------|-----|
| ≥ 0.8 | 30 days (LONG) |
| 0.7-0.8 | 7 days (MEDIUM) |
| 0.6-0.7 | 24 hours (SHORT) |
| < 0.6 | Not monitored |

Does not monitor every entity forever without a policy.

---

## 14. Observability (Per Directive §31)

| Metric | Description |
|--------|-------------|
| source_health | Per-source availability status |
| discovery_throughput | Entities discovered per run |
| queue_depth | Pending tasks |
| failed_connectors | Sources in failure state |
| graph_growth | New entities/relationships per cycle |
| false_positive_rate | Rejected leads / total leads |
| alert_rate | Alerts per time window |
| ai_errors | Model gateway failures |
| latency | Source response times |
| resource_usage | CPU, memory, disk |
| coverage | Sources checked vs not checked |

---

## 15. Deployment Architecture (Per Directive §33)

### Layer B: Production (REQUIRES EXTERNAL INFRASTRUCTURE)

| Component | Technology |
|-----------|-----------|
| Container Orchestration | Kubernetes |
| Primary Database | PostgreSQL |
| Event Streaming | Kafka |
| Cache | Redis |
| Search | OpenSearch |
| Graph Database | Neo4j |
| Object Storage | S3 |
| Secret Management | Kubernetes Secrets / Vault |
| Observability | OpenTelemetry / Prometheus / Grafana |
| Backup | Automated backup + disaster recovery |
| Disaster Recovery | RTO/RPO targets defined (Module 35) |

**STATUS:** None of the above is deployed. All marked as REQUIRES EXTERNAL INFRASTRUCTURE.

---

## 16. Disaster Recovery

| Capability | Status |
|-----------|--------|
| Backup/Restore | IMPLEMENTED (Layer A — in-memory) |
| Failover/Failback | IMPLEMENTED (Layer A — simulated) |
| RTO/RPO Targets | DEFINED (RTO: 4h, RPO: 1h) |
| Verification | IMPLEMENTED (Layer A) |
| Production DR | REQUIRES EXTERNAL INFRASTRUCTURE |

---

## 17. Interoperability

| Standard | Status |
|----------|--------|
| STIX 2.1 | POC IMPLEMENTED (21 tests passing) |
| TAXII 2.1 | SPECIFICATION (ADR-009 accepted) |
| MISP (via PyMISP) | SPECIFICATION (ADR-006 accepted) |
| OpenCTI (via GraphQL) | SPECIFICATION (ADR-007 accepted) |
| SpiderFoot (isolated) | SPECIFICATION (ADR-008 accepted) |
| Cortex (standalone) | SPECIFICATION (ADR-011 accepted) |
| TheHive | REJECTED (ADR-010) |

---

## 18. Open-Source Integrations

Per Directive §19: Do not install technologies simply because they exist. Evaluate functionality, license, maintenance, security, scalability, API, interoperability, operational cost, overlap, removal difficulty.

All evaluations documented in `docs/architecture/open-source-intelligence-stack.md`.

| Technology | Decision | ADR | POC Status |
|-----------|----------|-----|-----------|
| MISP | INTEGRATE | ADR-006 | PENDING (Layer B) |
| OpenCTI | INTEGRATE | ADR-007 | PENDING (Layer B) |
| SpiderFoot | ISOLATE | ADR-008 | PENDING (Layer B) |
| STIX/TAXII | USE | ADR-009 | IMPLEMENTED (21 tests) |
| TheHive | REJECT | ADR-010 | N/A |
| Cortex | INTEGRATE | ADR-011 | PENDING (Layer B) |

Prefer adapters and external services over copying large codebases into GFIN.

---

## 19. Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Layer A only (in-memory) | No persistent storage | Deploy Layer B infrastructure |
| Mock sources | No real intelligence | Deploy real source connectors |
| No deployed infrastructure | Nothing runs in production | Provision Kubernetes + databases |
| AGPL licenses (MISP, Cortex) | Legal review required | Formal legal counsel before production |
| SpiderFoot low activity | May need custom module maintenance | Monitor and maintain custom modules |
| Single OpenAI model | Provider risk | Model Gateway supports fallback to local |
| No real police federation | No live data sharing | Deploy police connectors + federation |

---

## 20. Implementation Priority (Per Directive §36)

| Priority | Capability | Module | Status |
|----------|-----------|--------|--------|
| 1 | Canonical data model | 03 | ACCEPTED |
| 2 | Security / identity | 02 | ACCEPTED |
| 3 | Evidence / provenance | 06 | ACCEPTED |
| 4 | Intelligence graph | 03 | ACCEPTED |
| 5 | Ingestion gateway | Architecture | DEFINED |
| 6 | Source adapters | OSINT Stack | SPECIFICATION |
| 7 | Discovery engine | UFDE | IN_PROGRESS |
| 8 | Entity resolution | 04 | ACCEPTED |
| 9 | Correlation | 14, 16 | ACCEPTED |
| 10 | Campaign detection | 16, UFDE | ACCEPTED |
| 11 | Anomaly detection | UFDE | IMPLEMENTED |
| 12 | Continuous monitoring | 17, UFDE | ACCEPTED |
| 13 | AI reasoning | 19-22 | ACCEPTED |
| 14 | Citizen network | 13 | ACCEPTED |
| 15 | Police federation | 23-27, 32 | ACCEPTED |
| 16 | Global interoperability | STIX, OSINT | SPECIFICATION |
| 17 | Advanced analytics | 30, 31 | ACCEPTED |

---

## 21. Non-Negotiable Engineering Rules (Per Directive §39)

### Never:
- Fabricate implementation status
- Fabricate test results
- Fabricate source coverage
- Fabricate evidence
- Turn hypotheses into facts
- Expose restricted intelligence to unauthorized users
- Bypass access controls
- Hard-code external providers into core logic
- Introduce dependencies without evaluation
- Allow external content to control AI
- Create a feature without integrating it into the overall intelligence architecture

### Always:
- Preserve provenance
- Validate external data
- Record confidence
- Enforce authorization
- Enforce classification
- Enforce jurisdiction
- Document architecture decisions
- Test security boundaries
- Report limitations honestly

---

## 22. Module Evaluation Checklist (Per Directive §34)

Before implementing any new module, answer:

1. Does this improve fraud discovery?
2. Does it improve correlation?
3. Does it improve evidence quality?
4. Does it improve coverage?
5. Does it improve cross-border intelligence?
6. Does it improve autonomous operation?
7. Does it reduce false positives?
8. Does it integrate with the intelligence graph?
9. Does it preserve provenance?
10. Does it preserve classification and jurisdiction?
11. Does it make the system more resilient?
12. Can it operate without creating an unnecessary silo?

If the answer is no to most of these, reconsider the module.

---

## 23. Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Full suite | 1931 | ALL PASSING |
| UFDE (new) | 96 | ALL PASSING |
| STIX adapter | 21 | ALL PASSING |
| Coverage | 93.31% | — |

---

## 24. Document Maintenance

This document is a LIVING DOCUMENT. It must be updated as modules are added.

When implementing a feature (Per Directive §42):
1. Identify which intelligence entities it touches
2. Identify which graph relationships it creates
3. Identify provenance requirements
4. Identify classification/jurisdiction requirements
5. Identify source adapters
6. Identify downstream discovery opportunities
7. Identify monitoring opportunities
8. Identify AI opportunities
9. Identify failure modes
10. Update this master architecture
11. Add tests
12. Report actual implementation status

Do not implement isolated features without considering their place in the global intelligence loop.

---

## 25. Final Vision (Per Directive §43)

```text
A signal enters GFIN.
    ↓
GFIN identifies what the signal represents.
    ↓
GFIN searches all permitted relevant sources.
    ↓
GFIN enriches the signal.
    ↓
GFIN resolves entities.
    ↓
GFIN finds relationships.
    ↓
GFIN expands the graph.
    ↓
GFIN discovers previously unknown infrastructure.
    ↓
GFIN detects patterns and clusters.
    ↓
GFIN identifies potential campaigns.
    ↓
GFIN checks for cross-border relationships.
    ↓
GFIN continuously monitors important entities.
    ↓
GFIN detects changes.
    ↓
GFIN generates evidence-backed alerts.
    ↓
Investigators receive explainable leads.
    ↓
New information enters the graph.
    ↓
The system becomes more informative over time.
```

That continuous loop is the product.

---

## END OF MASTER SYSTEM ARCHITECTURE
