# GFIN — Architecture Review

**Version:** 1.0
**Date:** 2026-08-25
**Status:** REVIEW REQUIRED
**Reviewer:** Project Owner (Rojs Gordons)
**Author:** GFIN-CEA

---

## 1. Architecture Overview

### 1.1 Purpose

The Global Fraud Intelligence Network (GFIN) is a continuously operating, evidence-based, internationally federated digital fraud intelligence platform. It discovers, correlates, monitors, and explains digital fraud signals across borders while preserving data sovereignty for law-enforcement organizations.

### 1.2 Two-Layer Architecture

The system is built in two layers:

**Layer A — Application / MVP (current)**
- Built and tested in the Base44 development environment
- Uses development adapters (in-memory, local storage) behind abstraction interfaces
- All domain logic, API contracts, schemas, and tests are production-grade
- Infrastructure adapters are NOT production-grade (no persistence, no distribution, no scale)

**Layer B — Production Infrastructure (not deployed from sandbox)**
- Infrastructure-as-Code (Terraform, Kubernetes manifests, Dockerfiles)
- Production adapters (PostgreSQL, Kafka, OpenSearch, Neo4j, Redis, S3)
- REQUIRES EXTERNAL INFRASTRUCTURE — not deployed, not claimed as deployed
- Migration path: implement production adapters for existing interfaces; no core rewrite

### 1.3 Core Architectural Principles

1. Evidence First — AI analyzes evidence, never creates it
2. Federated by Design — police organizations retain data control
3. Zero Trust — no implicit trust for any entity
4. Provider Independence — AI providers are replaceable through Model Gateway
5. Abstraction — all infrastructure behind interfaces (Layer A → Layer B migration)
6. No Single Point of Failure — graceful degradation when components fail
7. Human Accountability — AI assists, never makes legal decisions

### 1.4 Assumptions

- The platform operates as a fraud intelligence service, not a law-enforcement authority
- Citizen reports are allegations until corroborated
- All external content is untrusted (prompt injection defense)
- The platform does not claim to see "the entire internet"
- Technology stack is PROPOSED / NOT YET VALIDATED (see open-issues.md T-01 through T-12)

### 1.5 Unresolved Decisions

| # | Decision | Status | Blocks |
|---|----------|--------|--------|
| D-PENDING-01 | Graph database selection (Neo4j vs alternatives) | PENDING benchmark | Module 12 production |
| D-PENDING-02 | Cloud provider selection | PENDING | Module 40 |
| D-PENDING-03 | AI model selection per task type | PENDING evaluation | Module 19/37 production |
| D-PENDING-04 | Event streaming approach in Base44 | PENDING design | Module 05 design |
| D-PENDING-05 | Full-text search approach | PENDING design | Module 07 design |

---

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GFIN PLATFORM                                 │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│  │ Citizen Web │  │Citizen Mob. │  │Police Console│  ← APPS          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                   │
│         │                │                │                           │
│         └────────────────┼────────────────┘                           │
│                          │                                           │
│                 ┌────────┴────────┐                                   │
│                 │  API Gateway     │  ← ENTRY POINT                   │
│                 │  (FastAPI)       │                                   │
│                 └────────┬────────┘                                   │
│                          │                                           │
│    ┌─────────────────────┼─────────────────────┐                     │
│    │                     │                     │                     │
│ ┌──┴──────┐  ┌──────────┴──┐  ┌──────────┐  ┌──┴──────┐            │
│ │Identity  │  │Entity Svc   │  │Evidence  │  │Search   │ ← SERVICES  │
│ │Service   │  │             │  │Vault     │  │Service  │            │
│ └─────────┘  └────────────┘  └──────────┘  └─────────┘            │
│                                                                    │
│ ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐            │
│ │Fraud    │  │Campaign   │  │Monitor   │  │Alert     │            │
│ │Engine   │  │Engine     │  │Engine    │  │Engine    │            │
│ └─────────┘  └───────────┘  └──────────┘  └─────────┘            │
│                                                                    │
│ ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐            │
│ │AI       │  │AI         │  │Police    │  │Federa-   │            │
│ │Gateway  │  │Orchestr.  │  │API       │  │tion      │            │
│ └─────────┘  └───────────┘  └──────────┘  └─────────┘            │
│                                                                    │
│ ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐            │
│ │Crawler  │  │Domain     │  │DNS/IP    │  │Cert      │ ← INTEL    │
│ │Service  │  │Intel      │  │Intel     │  │Intel     │            │
│ └─────────┘  └───────────┘  └──────────┘  └─────────┘            │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────┴────┐      ┌─────┴────┐      ┌─────┴────┐
   │  SHARED  │      │  EVENTS  │      │  INFRA   │
   │ PACKAGES │      │  BUS    │      │ ABSTRAC. │
   │ schemas  │      │(iface)  │      │ (iface)  │
   │ common   │      │         │      │          │
   │ auth     │      │  Layer A│      │  Layer A │
   │ events   │      │  memory │      │  memory  │
   │ obs.     │      │         │      │          │
   │          │      │  Layer B│      │  Layer B │
   │          │      │  Kafka  │      │  Prod    │
   └──────────┘      └─────────┘      └──────────┘
```

### 2.1 Service Inventory

| Service | Layer | Responsibility | Key Interfaces |
|---------|-------|---------------|----------------|
| API Gateway | A+B | Request routing, auth, rate limiting | FastAPI |
| Identity | A+B | Authentication, authorization, orgs, roles | IdentityProvider |
| Entity | A+B | Entity CRUD, normalization, resolution | EntityRepository |
| Evidence | A+B | Evidence storage, hashing, chain of custody | ObjectStorage |
| Search | A+B | Entity, campaign, infrastructure search | SearchService |
| Crawler | A+B | Web discovery, crawling, extraction | WebCrawlSourceAdapter |
| Domain Intel | A+B | RDAP, domain profiles, history | SourceAdapter |
| DNS/IP Intel | A+B | DNS resolution, IP/ASN intelligence | SourceAdapter |
| Certificate Intel | A+B | CT logs, certificate relationships | SourceAdapter |
| Infrastructure | A+B | Infrastructure graph, clustering, changes | GraphStore |
| Fraud | A+B | Fraud detection, rules, classifiers | — |
| Campaign | A+B | Campaign detection, clustering | GraphStore |
| Monitoring | A+B | Subscriptions, change detection | EventBus |
| Alerts | A+B | Priority, routing, notifications | EventBus |
| AI Gateway | A+B | Provider abstraction, routing, fallback | ModelGateway |
| AI Orchestrator | A+B | Tool registry, investigation workflows | ModelGateway |
| Police API | A+B | Police endpoints, federation protocol | — |
| Federation | A+B | National nodes, sync, residency | EventBus |
| Analytics | A+B | Dashboards, trends, metrics | — |

### 2.2 Shared Packages

| Package | Responsibility |
|---------|---------------|
| schemas | Core domain types, enums, base models |
| common | Infrastructure abstraction interfaces + dev adapters |
| events | Event schemas, topic definitions |
| auth | Auth middleware, role/classification enforcement |
| observability | Structured logging, metrics interfaces |

---

## 3. Data Flow Diagram

### 3.1 Citizen Report Flow

```
Citizen
  │
  ├─ submits phone/email/URL/domain/crypto
  │
  ▼
API Gateway (auth, rate limit)
  │
  ▼
Entity Service
  │
  ├─ normalize input (Entity Resolution)
  ├─ check for existing entity (EntityRepository.find_by_normalized_value)
  │
  ├─ EXISTING ENTITY → create Observation → link to entity
  ├─ NEW ENTITY → create Entity → create Observation
  │
  ▼
Evidence Service
  │
  ├─ store submitted content (ObjectStorage.store)
  ├─ compute content hash (SHA-256)
  ├─ create Evidence record with provenance
  │
  ▼
Event Bus
  │
  ├─ publish: observation.created
  ├─ publish: report.created
  ├─ publish: entity.created (if new)
  │
  ▼
Fraud Engine (subscribes to report.created)
  │
  ├─ apply deterministic rules
  ├─ classify fraud category
  ├─ compute risk level
  │
  ▼
Campaign Engine (subscribes to observation.created)
  │
  ├─ check for campaign correlation
  ├─ update campaign if matched
  │
  ▼
Alert Engine (subscribes to risk.changed)
  │
  ├─ check if risk threshold exceeded
  ├─ create alert if needed
  │
  ▼
Search Service
  │
  ├─ index entity for future searches
  │
  ▼
Response to Citizen
  │
  ├─ risk assessment (evidence-based)
  ├─ recommended next steps
```

### 3.2 Police Investigation Flow

```
Investigator
  │
  ├─ search entity (phone, domain, etc.)
  │
  ▼
API Gateway (auth: INVESTIGATOR role)
  │
  ▼
Search Service
  │
  ├─ search entities, campaigns, infrastructure
  ├─ filter by classification (LAW_ENFORCEMENT access)
  │
  ▼
Entity Service
  │
  ├─ retrieve entity with observations, relationships
  ├─ retrieve evidence with provenance
  │
  ▼
Graph Store
  │
  ├─ explore connections (direct, indirect, cross-border)
  ├─ find paths between entities
  │
  ▼
Police API (if cross-border match)
  │
  ├─ check global index for international matches
  ├─ return match metadata (not case details)
  │
  ▼
Cross-Border Request (if needed)
  │
  ├─ REQUEST → VALIDATE → AUTHORIZE → REVIEW → APPROVE/DENY → AUDIT
  │
  ▼
AI Orchestrator (if AI assistance requested)
  │
  ├─ use controlled tools (graph_search, campaign_search, etc.)
  ├─ produce evidence-referenced analysis
  │
  ▼
Response to Investigator
  │
  ├─ entity profile with timeline
  ├─ relationship graph
  ├─ campaign correlation
  ├─ evidence with provenance
  ├─ AI analysis (marked UNVERIFIED if unsupported)
```

### 3.3 Web Discovery Flow

```
Seed (citizen report, analyst seed, scheduled)
  │
  ▼
Crawler Service
  │
  ├─ check robots.txt and source policy (Source Policy §3.3)
  ├─ schedule crawl job
  ├─ rate limit
  │
  ▼
Page Fetch (sandboxed)
  │
  ├─ download content (treated as UNTRUSTED)
  ├─ compute content hash
  │
  ▼
Entity Extraction
  │
  ├─ extract entities (phones, emails, URLs, domains, wallets)
  ├─ extract relationships (redirects, hosting, references)
  │
  ▼
Entity Service (normalization + resolution)
  │
  ├─ normalize extracted entities
  ├─ create observations with provenance (source: web crawl)
  │
  ▼
Evidence Service
  │
  ├─ store page content as evidence
  ├─ record retrieval timestamp, content hash
  │
  ▼
Event Bus
  │
  ├─ publish: observation.created
  ├─ publish: evidence.created
  ├─ publish: infrastructure.changed (if detected)
```

---

## 4. Trust Boundary Diagram

```
                    EXTERNAL UNTRUSTED ZONE
                    ═══════════════════════
                    
  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Citizens│  │Web Pages │  │External  │  │Police    │
  │         │  │(crawled) │  │AI Provs. │  │Connectors│
  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │            │              │              │
═══════╪════════════╪══════════════╪══════════════╪═════════
       │            │              │              │
       ▼            ▼              ▼              ▼
  ┌──────────────────────────────────────────────────────┐
  │              TRUST BOUNDARY 1: API GATEWAY            │
  │  • TLS termination                                    │
  │  • Authentication (token validation)                  │
  │  • Rate limiting                                      │
  │  • Input validation / schema enforcement              │
  │  • Classification-aware access control                │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │           TRUST BOUNDARY 2: AUTHORIZATION              │
  │  • RBAC (role: citizen, investigator, analyst, admin) │
  │  • ABAC (classification, jurisdiction, organization)  │
  │  • Per-resource access policy                         │
  │  • Zero Trust — every request re-evaluated            │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │         TRUST BOUNDARY 3: DATA CLASSIFICATION          │
  │                                                       │
  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐│
  │  │ PUBLIC  │ │COMMUNITY│ │RESTRICTED│ │LAW_ENFORCE.││
  │  │         │ │         │ │          │ │HIGHLY_RESTR.││
  │  └─────────┘ └─────────┘ └──────────┘ └─────────────┘│
  │  • Data never crosses classification boundaries        │
  │  • AI routing enforces classification (local only      │
  │    for LAW_ENFORCEMENT / HIGHLY_RESTRICTED)            │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │      TRUST BOUNDARY 4: FEDERATION / SOVEREIGNTY        │
  │                                                       │
  │  ┌──────┐  ┌──────┐  ┌──────┐                        │
  │  │ ES   │  │ FR   │  │ DE   │  ← National Nodes      │
  │  │Police│  │Police│  │Police│                         │
  │  └──────┘  └──────┘  └──────┘                         │
  │  • Police data stays in national system               │
  │  • Only permitted intelligence metadata crosses borders│
  │  • Cross-border requests require formal approval      │
  │  • Each request audited                               │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │      TRUST BOUNDARY 5: AI / MODEL GATEWAY              │
  │  • All AI access through Model Gateway                │
  │  • Classification-aware routing (restricted → local)   │
  │  • No direct AI provider access from application      │
  │  • Tool calls authenticated, authorized, logged       │
  │  • External content treated as data, not authority    │
  │  • Prompt injection defense                           │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │      TRUST BOUNDARY 6: EVIDENCE / IMMUTABILITY         │
  │  • Evidence stored with content hash (SHA-256)        │
  │  • Chain of custody maintained                        │
  │  • WORM storage for immutable evidence (Layer B)      │
  │  • Audit trail (immutable, append-only)               │
  │  • No silent evidence modification                    │
  └──────────────────────────────────────────────────────┘
```

### 4.1 Trust Boundary Rules

| Boundary | Rule | Enforcement |
|----------|------|-------------|
| TB1: API Gateway | All external requests must authenticate | Token validation; rate limiting |
| TB2: Authorization | Every request is role + attribute checked | RBAC + ABAC; classification-aware |
| TB3: Data Classification | Data never crosses classification boundaries | Classification enforcement in all services |
| TB4: Federation | No police data leaves national system without authorization | Federation protocol; request workflow |
| TB5: AI Gateway | No direct AI provider access; classification-aware routing | Model Gateway; tool registry |
| TB6: Evidence | Evidence is immutable; chain of custody preserved | Content hashing; WORM storage (Layer B) |

---

## 5. Data Classification Model

### 5.1 Classification Levels

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA CLASSIFICATION                       │
│                                                              │
│  Level 5: HIGHLY_RESTRICTED                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Active investigation details                          │ │
│  │ • Named suspects                                         │ │
│  │ • Sensitive evidence vault items                         │ │
│  │ • Police connector credentials                          │ │
│  │ • AI provider credentials                                │ │
│  │ Access: Explicitly authorized individuals only           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│  Level 4: LAW_ENFORCEMENT                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Police matches                                         │ │
│  │ • Cross-border request details                          │ │
│  │ • Investigation links                                    │ │
│  │ • Law-enforcement intelligence observations              │ │
│  │ Access: Authenticated police organizations               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│  Level 3: RESTRICTED                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Entity profiles                                        │ │
│  │ • Campaign analysis                                      │ │
│  │ • Infrastructure correlations                             │ │
│  │ • Risk assessments                                       │ │
│  │ Access: Authorized investigators, analysts               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│  Level 2: COMMUNITY                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Citizen reports (anonymized)                           │ │
│  │ • Aggregated fraud statistics                            │ │
│  │ • Community alerts                                       │ │
│  │ Access: Authenticated citizens                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│  Level 1: PUBLIC                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Public DNS records                                     │ │
│  │ • RDAP domain registration data                          │ │
│  │ • Certificate Transparency data                          │ │
│  │ • Aggregate statistics (no PII)                          │ │
│  │ Access: All users (no auth required for read)            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Access Matrix

| Data Level | Citizen | Investigator | Analyst | Administrator |
|-------------|---------|--------------|---------|----------------|
| PUBLIC | ✅ Read | ✅ Read | ✅ Read | ✅ Read |
| COMMUNITY | ✅ Read/Write | ✅ Read | ✅ Read | ✅ Read |
| RESTRICTED | ❌ | ✅ Read | ✅ Read | ✅ Read |
| LAW_ENFORCEMENT | ❌ | ✅ Read | ❌ | ✅ Read |
| HIGHLY_RESTRICTED | ❌ | ✅ (case-specific) | ❌ | ✅ (case-specific) |

### 5.3 Required Metadata Per Sensitive Object

```
owner:         → who created/controls this object
jurisdiction:   → legal jurisdiction the data belongs to
classification: → one of 5 levels (above)
access_policy:  → who can access, under what conditions
retention:      → how long kept, what happens on expiry
legal_basis:    → legal basis for processing (where required)
```

### 5.4 AI Data Routing

| Classification | External AI (OpenAI) | Local AI |
|----------------|---------------------|----------|
| PUBLIC | ✅ Permitted | ✅ Permitted |
| COMMUNITY | ✅ Minimized | ✅ Permitted |
| RESTRICTED | ⚠️ Only if authorized + necessary + DPA | ✅ Permitted |
| LAW_ENFORCEMENT | ❌ Prohibited | ✅ Within jurisdiction |
| HIGHLY_RESTRICTED | ❌ Prohibited | ✅ Within jurisdiction, isolated |

---

## 6. Federation Model

### 6.1 Architecture

```
                    GLOBAL CONTROL PLANE
                          │
            ┌─────────────┼─────────────┐
            │             │             │
     ┌──────┴──────┐ ┌───┴─────┐ ┌─────┴────┐
     │ GLOBAL      │ │ GLOBAL  │ │ GLOBAL   │
     │ ENTITY INDEX│ │ EVENT   │ │ MATCH    │
     │             │ │ BUS     │ │ ENGINE   │
     └──────┬──────┘ └────┬────┘ └────┬─────┘
            │             │             │
════════════╪═════════════╪═════════════╪══════════
  FEDERATION BOUNDARY (Trust Boundary 4)
════════════╪═════════════╪═════════════╪══════════
            │             │             │
     ┌──────┴──────┐ ┌───┴─────┐ ┌─────┴────┐
     │  ES NODE    │ │ FR NODE │ │ DE NODE  │
     │             │ │         │ │          │
     │ Police API  │ │Police API│ │Police API│
     │ Connector   │ │Connector │ │Connector │
     │             │ │         │ │          │
     │ [National   │ │[National│ │[National  │
     │  Case Data] │ │ CaseData]│ │ CaseData] │
     │ RETAINED    │ │RETAINED  │ │RETAINED   │
     └─────────────┘ └─────────┘ └──────────┘
```

### 6.2 What Crosses Borders

| Crosses Border | Does NOT Cross Border |
|----------------|----------------------|
| Match metadata (entity ID, jurisdiction, confidence) | Full police case files |
| Intelligence references (campaign ID, entity type) | Internal investigation details |
| Permitted observations (source, timestamp, classification) | Named suspects (without authorization) |
| Risk level changes | Evidence content (without explicit sharing) |
| Alert notifications | Police internal databases |
| Request workflow status | National law-enforcement procedures |

### 6.3 Cross-Border Request Workflow

```
REQUEST (Org A → Entity X)
    │
    ▼
VALIDATE (format, legal basis, purpose)
    │
    ▼
AUTHORIZATION (does Org A have access?)
    │
    ▼
DESTINATION (which jurisdiction holds data?)
    │
    ▼
REVIEW (Org B reviews request)
    │
    ▼
DECISION
    ├─ APPROVE → Secure response with permitted data
    ├─ PARTIAL → Partial response with subset
    └─ DENY → Denial with reason
    │
    ▼
AUDIT (full request, decision, and response logged)
```

### 6.4 Assumptions

- Each national node controls what data it shares
- The global platform stores only permitted intelligence metadata
- National nodes can disconnect from the federation at any time
- Federation protocol is event-driven (not batch sync)
- Data residency is enforced at the node level

### 6.5 Unresolved

- L-02: Law-enforcement data protection directive not confirmed
- L-03: Per-jurisdiction data residency requirements not defined
- L-06: Cross-border request legal framework not defined
- A-06: Federation model requires owner review

---

## 7. AI Architecture

### 7.1 Model Gateway

```
                    APPLICATION CODE
                         │
                         ▼
              ┌────────────────────┐
              │  MODEL GATEWAY      │
              │  (Interface)       │
              │                    │
              │  • Route by task   │
              │  • Route by class. │
              │  • Fallback        │
              │  • Retry           │
              │  • Cost controls    │
              │  • Logging/audit   │
              │  • Health monitor  │
              └──────┬──────┬──────┘
                     │      │
          ┌──────────┘      └──────────┐
          │                             │
     ┌────┴─────┐               ┌───────┴──┐
     │ EXTERNAL │               │ LOCAL    │
     │ PROVIDERS│               │ MODELS   │
     │          │               │          │
     │ OpenAI   │               │ OCR      │
     │ Other    │               │ Embeddings│
     │          │               │ Lang det. │
     │ Class:   │               │ Bulk clsf│
     │ PUBLIC   │               │          │
     │ COMMUN.  │               │ Class:   │
     │ RESTRICT.│               │ ALL      │
     │ (if auth)│               │          │
     └──────────┘               └──────────┘
```

### 7.2 Routing Rules

| Task Type | Classification | Provider | Rationale |
|-----------|---------------|----------|-----------|
| Embeddings | Any | LOCAL | Latency, privacy, cost |
| OCR | Any | LOCAL | Latency, no data egress |
| Language detection | Any | LOCAL | Latency, no data egress |
| Bulk classification | Any | LOCAL | Cost, volume |
| Complex reasoning | PUBLIC/COMMUNITY | EXTERNAL (OpenAI) | Requires deep reasoning |
| Multilingual analysis | PUBLIC/COMMUNITY | EXTERNAL (OpenAI) | Cross-lingual capability |
| Investigation summaries | PUBLIC/COMMUNITY | EXTERNAL (OpenAI) | Nuanced synthesis |
| Citizen assistant | PUBLIC/COMMUNITY | EXTERNAL (OpenAI) | Natural interaction |
| ANY task | LAW_ENFORCEMENT | LOCAL | No data egress |
| ANY task | HIGHLY_RESTRICTED | LOCAL | No data egress |

### 7.3 AI Investigation Orchestrator

```
INVESTIGATOR REQUEST
    │
    ▼
AI ORCHESTRATOR (sandboxed)
    │
    ├─ Plan investigation steps
    │
    ├─ Execute controlled tools:
    │   ├─ graph_search (authorized)
    │   ├─ campaign_search (authorized)
    │   ├─ domain_lookup (authorized)
    │   ├─ dns_lookup (authorized)
    │   ├─ ip_lookup (authorized)
    │   ├─ certificate_lookup (authorized)
    │   ├─ report_search (authorized)
    │   └─ entity_compare (authorized)
    │
    ├─ Every tool call:
    │   ├─ Authenticated
    │   ├─ Authorized
    │   ├─ Logged
    │   └─ Attributable
    │
    ├─ Synthesize results:
    │   ├─ Map claims to evidence IDs
    │   ├─ Assign confidence
    │   ├─ Mark UNVERIFIED if unsupported
    │
    ▼
OUTPUT (evidence-referenced, human-reviewable)
```

### 7.4 Hallucination Control

```
CLAIM
  ↓
EVIDENCE_ID (must exist in Evidence Vault)
  ↓
SOURCE (must be registered)
  ↓
TIMESTAMP (when observed)
  ↓
CONFIDENCE (LOW/MEDIUM/HIGH/UNKNOWN)
  ↓
If evidence insufficient → return UNKNOWN or INSUFFICIENT_DATA
```

### 7.5 Failure Behavior

| AI Provider Status | Platform Behavior |
|-------------------|-------------------|
| Primary (OpenAI) available | Full AI functionality |
| Primary unavailable, fallback available | Degraded AI — local models handle basic tasks |
| All AI unavailable | Core platform continues (ingestion, evidence, graph, deterministic rules, alerts) |
| AI returns unverified claims | Claims marked UNVERIFIED; human review required for critical decisions |

### 7.6 Unresolved

- L-05: AI provider data processing agreements not reviewed
- T-11: OpenAI not validated as final choice
- T-12: Local/open-source AI model selection not made
- A-07: AI architecture requires owner review

---

## 8. Police API Architecture

### 8.1 Endpoints

```
┌────────────────────────────────────────────────────┐
│                  POLICE API                          │
│                                                     │
│  POST /v1/police/match         — Match entity       │
│  POST /v1/police/observation    — Submit observation│
│  GET  /v1/police/entity/{id}    — Get entity intel  │
│  GET  /v1/police/campaign/{id}  — Get campaign intel│
│  POST /v1/police/monitor        — Subscribe to entity│
│  GET  /v1/police/alerts         — Get alerts         │
│  POST /v1/police/request        — Cross-border req. │
│  GET  /v1/police/request/{id}   — Get request status│
└────────────────────────────────────────────────────┘
```

### 8.2 Authentication and Authorization

```
Police Connector
    │
    ├─ mTLS (mutual TLS) — connector identity verified
    │
    ├─ API Key — per-organization credential
    │
    ├─ RBAC — INVESTIGATOR role required
    │
    ├─ ABAC — jurisdiction + classification checked
    │
    ├─ Rate limiting — per-organization quotas
    │
    ├─ Audit — every request logged (immutable)
    │
    └─ Monitoring — anomaly detection on API usage
```

### 8.3 Police Connector SDK

```
┌─────────────────────────────────────────────┐
│           POLICE CONNECTOR SDK                │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  Connector Interface (implement per   │   │
│  │  country/organization)                 │   │
│  │                                       │   │
│  │  • authenticate()                     │   │
│  │  • synchronize()                       │   │
│  │  • submit_observation()                │   │
│  │  • receive_match()                     │   │
│  │  • receive_alert()                     │   │
│  │  • handle_request()                    │   │
│  │  • acknowledge()                       │   │
│  │  • retry()                             │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Reference Implementation (mock)              │
│  ┌──────────────────────────────────────┐   │
│  │  MockPoliceConnector                  │   │
│  │  • Uses test data                     │   │
│  │  • Simulates national system           │   │
│  │  • For development/testing only        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 8.4 Police Data Model (What Is Shared)

```
PERMITTED INTELLIGENCE METADATA (crosses federation boundary)
┌────────────────────────────────────────────────────┐
│  ENTITY_ID         → Stable global ID               │
│  ENTITY_TYPE       → PHONE, DOMAIN, IP, etc.       │
│  JURISDICTION      → Which country/org              │
│  ORGANIZATION      → Which police org               │
│  INTELLIGENCE_TYPE → What kind of intelligence      │
│  FIRST_SEEN        → When first observed            │
│  LAST_SEEN         → When last observed             │
│  CONFIDENCE        → LOW/MEDIUM/HIGH                │
│  RELATED_CAMPAIGN  → Campaign ID (if any)            │
│  ACCESS_LEVEL      → MATCH_ONLY / REQUEST_REQUIRED   │
└────────────────────────────────────────────────────┘

DOES NOT CROSS:
• Case files
• Suspect names (without authorization)
• Evidence content (without explicit sharing)
• Internal police procedures
```

### 8.5 Unresolved

- L-02: Law-enforcement data protection directive not confirmed
- L-06: Cross-border request legal framework not defined
- T-10: OIDC/OAuth2 provider not validated
- A-08: Police API architecture requires owner review

---

## 9. Failure Model

### 9.1 Component Failure Matrix

| Component Fails | Impact | Degradation | Recovery |
|-----------------|--------|-------------|----------|
| API Gateway | No external access | Full outage | Restart; K8s auto-restart (Layer B) |
| Identity Service | No new auth | Existing tokens valid until expiry | Restart; fallback to cached tokens |
| Entity Service | No entity CRUD | Read-only if cache available | Restart; DB still has data |
| Evidence Vault | No evidence storage | New evidence lost; existing accessible | Restart; storage persists (Layer B) |
| Search Service | No search | Direct entity queries (fallback) | Re-index from database |
| Crawler | No new discovery | Existing intelligence available | Restart; resume from queue |
| Event Bus | No async events | Sync processing (fallback) | Restart; Kafka persists (Layer B) |
| Graph Store | No graph queries | Direct entity lookups (fallback) | Rebuild from entities + relationships |
| Fraud Engine | No detection | Deterministic rules (fallback) | Restart; rules are stateless |
| Campaign Engine | No campaign detection | Existing campaigns available | Restart; rebuild from events |
| Monitoring | No active monitoring | Subscriptions resume on restart | Replay missed events (Layer B) |
| Alert Engine | No new alerts | Existing alerts visible | Replay missed events |
| AI Gateway | No AI features | Deterministic rules continue | Fallback to local models |
| AI Orchestrator | No AI investigation | Manual investigation continues | Restart; tools are stateless |
| Police API | No police integration | Citizen features continue | Restart; connectors retry |
| Federation | No cross-border sync | National nodes operate independently | Replay missed sync events |
| External AI (OpenAI) | No advanced AI | Local models; deterministic rules | Auto-fallback to local models |
| External Source | No data from that source | Other sources continue | Retry; dead-letter queue |
| Database | No persistence | In-memory cache until exhausted | Restore from backup (Layer B) |
| Cache | No caching | Slower response times | Restart; rebuild from DB |

### 9.2 Cascade Failure Prevention

```
RULE: A failure in one component MUST NOT cascade to others.

Mitigations:
• Circuit breakers on all external calls
• Timeouts on all inter-service calls
• Dead-letter queues for failed events
• Graceful degradation (each service has a fallback mode)
• Independent service lifecycles (one crash ≠ system crash)
```

### 9.3 Recovery Time Objectives (Layer B — PROPOSED)

| Tier | RTO | RPO | Components |
|------|-----|-----|-----------|
| Critical | < 15 min | < 1 min | API Gateway, Identity, Entity, Evidence |
| Important | < 30 min | < 5 min | Search, Event Bus, Fraud Engine, Alerts |
| Enhancement | < 2 hours | < 30 min | AI Gateway, AI Orchestrator, Analytics, Crawler |
| Federation | < 1 hour | < 5 min | Police API, Federation |

**Note:** RTO/RPO values are PROPOSED. Must be validated in Module 35 (Disaster Recovery) and Module 38 (Load Testing).

### 9.4 Unresolved

- RTO/RPO targets not validated (Module 35)
- Multi-region failover not tested (Module 35)
- T-01: Kubernetes availability/restart behavior not validated
- A-09: Failure model requires owner review

---

## 10. Deployment Model

### 10.1 Layer A — MVP (Current)

```
┌─────────────────────────────────────────────┐
│         BASE44 SANDBOX (Current)             │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  Application Code                     │   │
│  │  (Python/FastAPI)                     │   │
│  │                                       │   │
│  │  • All interfaces implemented         │   │
│  │  • All dev adapters (in-memory)       │   │
│  │  • All domain logic                   │   │
│  │  • All API contracts                  │   │
│  │  • All schemas                         │   │
│  │  • All tests                           │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  Development Adapters                 │   │
│  │  • InMemoryEntityRepository           │   │
│  │  • InMemoryEventBus                   │   │
│  │  • EntitySearchService                │   │
│  │  • LocalObjectStorage                 │   │
│  │  • AdjacencyListGraph                 │   │
│  │  • MemoryCache                        │   │
│  │  • Base44IdentityProvider             │   │
│  │  • BaseModelGateway                   │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Status: IMPLEMENTED + TESTED               │
│  Not deployed to production                  │
└─────────────────────────────────────────────┘
```

### 10.2 Layer B — Production (Not Deployed)

```
┌─────────────────────────────────────────────────────────────┐
│                   CLOUD ENVIRONMENT                          │
│                   (REQUIRES EXTERNAL INFRASTRUCTURE)          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  KUBERNETES CLUSTER (multi-region where required)   │    │
│  │                                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │    │
│  │  │API Gw.   │ │Identity  │ │Entity    │  ← Pods    │    │
│  │  │(3 replicas│ │(2 replic.│ │(3 replic.│            │    │
│  │  └──────────┘ └──────────┘ └──────────┘            │    │
│  │  ... all services ...                                │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                  │
│  ┌───────────────────────┼──────────────────────────┐     │
│  │                       │                          │     │
│  │  ┌──────────┐  ┌──────┴───┐  ┌──────────┐       │     │
│  │  │PostgreSQL│  │  Kafka   │  │OpenSearch│       │     │
│  │  │(multi-AZ)│  │(3 broker)│  │(cluster) │       │     │
│  │  └──────────┘  └──────────┘  └──────────┘       │     │
│  │                                                    │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │     │
│  │  │  Redis   │  │  Neo4j   │  │ S3 (WORM)│        │     │
│  │  │(cluster) │  │(cluster) │  │(evidence)│        │     │
│  │  └──────────┘  └──────────┘  └──────────┘        │     │
│  │                                                    │     │
│  │  ┌──────────┐  ┌──────────┐                       │     │
│  │  │  Vault   │  │Prometheus│  ┌──────────┐        │     │
│  │  │(secrets) │  │+Grafana  │  │OTel Coll.│        │     │
│  │  └──────────┘  └──────────┘  └──────────┘        │     │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Status: REQUIRES EXTERNAL INFRASTRUCTURE                    │
│  Terraform + K8s manifests created but NOT APPLIED           │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 Migration Path (Layer A → Layer B)

```
STEP 1: Provision cloud infrastructure (Terraform)
    │
    ▼
STEP 2: Deploy K8s cluster and core services
    │
    ▼
STEP 3: Implement production adapters:
    │   • PostgresEntityRepository (for EntityRepository)
    │   • KafkaEventBus (for EventBus)
    │   • OpenSearchService (for SearchService)
    │   • S3ObjectStorage (for ObjectStorage)
    │   • Neo4jGraph (for GraphStore)
    │   • RedisCache (for CacheService)
    │   • OIDCIdentityProvider (for IdentityProvider)
    │   • OpenAIGateway (for ModelGateway)
    │
    ▼
STEP 4: Configure adapters via environment variables
    │   (.env: DATABASE_ADAPTER=postgresql, etc.)
    │
    ▼
STEP 5: Migrate data (if any from MVP)
    │
    ▼
STEP 6: Run acceptance tests against production adapters
    │
    ▼
STEP 7: Production deployment
```

### 10.4 National Node Deployment (Federation)

```
Each national node:
• Deployed in the respective country's jurisdiction
• Runs the same software with national-specific configuration
• Connects to the global control plane via federation protocol
• Retains all national case data locally
• Shares only permitted intelligence metadata

Data residency is enforced at the node level:
• Node config: jurisdiction=ES, residency=EU
• Data classified as LAW_ENFORCEMENT stays in ES node
• Only metadata cleared for sharing enters global index
```

### 10.5 Unresolved

- D-PENDING-02: Cloud provider not selected
- T-01 through T-12: Technology stack not validated
- L-03: Data residency requirements not defined per country
- A-10: Deployment model requires owner review

---

## Review Checklist

| # | Section | Status | Reviewer Action Required |
|---|---------|--------|--------------------------|
| 1 | Architecture Overview | DOCUMENTED | Review assumptions and unresolved decisions |
| 2 | Component Diagram | DOCUMENTED | Validate service decomposition and boundaries |
| 3 | Data Flow Diagram | DOCUMENTED | Validate data flows respect classification boundaries |
| 4 | Trust Boundary Diagram | DOCUMENTED | Validate trust boundaries are complete and correct |
| 5 | Data Classification Model | DOCUMENTED | Validate classification levels and access matrix |
| 6 | Federation Model | DOCUMENTED | Validate federation respects data sovereignty |
| 7 | AI Architecture | DOCUMENTED | Validate AI routing and hallucination controls |
| 8 | Police API Architecture | DOCUMENTED | Validate API design and data sharing model |
| 9 | Failure Model | DOCUMENTED | Validate failure modes and degradation behavior |
| 10 | Deployment Model | DOCUMENTED | Validate Layer A→B migration path |

**ARCHITECTURE STATUS: REVIEW REQUIRED**
