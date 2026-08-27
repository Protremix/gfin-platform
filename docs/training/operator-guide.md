# GFIN Operator Documentation & Guide

**Document Version:** 1.0  
**Target Audience:** System Operators, Operations Center (NOC/SOC) Personnel  
**Scope:** Layer A In-Memory MVP Operations & Layer B Production Transition  

---

## 1. System Overview & Architecture (Modules 00–36)

The Global Fraud Intelligence Network (GFIN) is a federated intelligence sharing and analysis platform designed to detect, analyze, and counter transnational financial fraud and cybercrime. The platform architecture comprises 37 specialized modules organized across four functional layers:

```
[ Citizen & Police Portals (Mods 13, 23, 27) ] ──▶ [ API Gateway & Auth (Mods 01, 02) ]
                                                            │
                                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Core Domain Services                                                                   │
│  - Entity Resolution (Mod 04)      - Event Bus & DLQ (Mod 05)  - Evidence Vault (Mod 06)│
│  - OSINT & Infra (Mods 08-12)      - Fraud Scoring (Mods 14,15)- Campaign Engine (Mod 16) │
│  - Continuous Monitoring (Mod 17)  - Alert Engine (Mod 18)   - AI Orchestrator (Mod 22)│
│  - Police & Cross-Border (23-26)  - Crypto Intel (Mod 28)    - Multilingual (Mod 29)  │
│  - Analytics & Warning (30-31)     - Federation (Mod 32)     - Compliance (Mod 33)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                                            │
                                                            ▼
 [ Observability (Mod 34) ] ──▶ [ DR & Backup (Mod 35) ] ──▶ [ Security Controls (Mod 36) ]
```

### Module Architecture Summary
- **Foundation (00–03):** Governance, Monorepo Dev Runtime, RBAC/ABAC Security Engine, Canonical Pydantic Data Model (26 Entities, 20 Relationships).
- **Core Operations (04–07):** Entity Resolution Engine, Event Bus (14 Kafka Topics + Dead Letter Queue), Cryptographic Evidence Vault, Graph & Fuzzy Search Platform.
- **Intelligence Stack (08–12):** Web Crawling, DNS/IP/ASN/RDAP/Certificate Intelligence, Technical Fingerprinting.
- **Applications & Scoring (13–18):** Citizen Reporting Portal, Automated Triage, Fraud Rule Engine (7 Signals, 4 Patterns), Campaign Lifecycle Engine, Continuous Monitoring, Multi-Channel Alert Router.
- **AI & Law Enforcement (19–28):** Model Gateway (GPT-5.6-Luna), Local AI Classifiers/Embeddings/OCR, 15-Tool Investigation Orchestrator, Police REST API, Police Connector SDK, Global Match Engine, 7-Stage Cross-Border Request Workflow, Police Web Console, Crypto Intelligence & Fund Tracing.
- **Federation & Governance (29–36):** Multilingual Engine (27 languages), Real-Time Analytics, Global Early Warning System, Federation Node Network, Compliance Framework (5 Classification Levels), Observability Stack, Disaster Recovery Engine, Security Testing Framework.

---

## 2. System Startup and Shutdown Procedures

### 2.1 Layer A (In-Memory MVP Execution)

To initialize the in-memory GFIN operating environment for testing or local simulation:

#### Step 1: Environment Initialization & Verification
```bash
# Navigate to the workspace root
cd /gfin

# Activate python environment and verify package installation
python3 -c "import packages; print('GFIN Package Suite Loaded Successfully')"
```
**Expected Output:**
```
GFIN Package Suite Loaded Successfully
```

#### Step 2: Running Platform Health Verification
```bash
python3 -c "
import sys
sys.path.insert(0, '/gfin')
from packages.observability.health import HealthCheckRegistry, SystemStatus

registry = HealthCheckRegistry()
status = registry.check_all()
print(f'System Status: {status.status.value}')
for component, check in status.components.items():
    print(f' - {component}: {check.status.value} ({check.message})')
"
```
**Expected Output:**
```
System Status: HEALTHY
 - memory: HEALTHY (Memory usage within normal bounds)
 - storage: HEALTHY (In-memory storage operational)
 - event_bus: HEALTHY (Event bus queues active)
 - ai_gateway: HEALTHY (Model gateway mock/online ready)
```

#### Step 3: Graceful Shutdown Procedure
In Layer A, services run in-process. Graceful shutdown requires flushing event queues and committing evidence vault index logs to persistent disk dumps:

```python
# Graceful In-Process Shutdown Code Snippet
from packages.events.event_bus import EventBus
from packages.services.evidence_vault import EvidenceVault

def shutdown_system(event_bus: EventBus, vault: EvidenceVault):
    print("Initiating GFIN Layer A graceful shutdown...")
    # 1. Flush event bus pending messages
    event_bus.flush()
    # 2. Verify evidence vault hash integrity prior to stopping
    integrity_ok = vault.verify_vault_integrity()
    print(f"Pre-shutdown Evidence Vault Integrity Check: {integrity_ok}")
    print("Shutdown complete. All state safely flushed.")
```

### 2.2 Layer B (Kubernetes Production Operations)

#### Startup Order (Production):
1. **Infrastructure Tier:** PostgreSQL, Neo4j, OpenSearch, Kafka Cluster, Redis, HashiCorp Vault.
2. **Core Tier:** Security/Auth Service, Event Bus Consumers, Entity Resolution Service.
3. **Domain Services Tier:** Evidence Vault, Fraud Engine, AI Gateway, Campaign Engine.
4. **Ingress & Portals:** API Gateway, Citizen Web App, Police Console.

```bash
# Production Startup Commands
kubectl apply -f infrastructure/kubernetes/namespaces.yaml
helm install gfin-infra ./infrastructure/helm/gfin-infra
helm install gfin-core ./infrastructure/helm/gfin-core
kubectl rollout status deployment/gfin-api-gateway -n gfin
```

#### Shutdown Order (Production):
```bash
# Drain external ingress first
kubectl scale deployment/gfin-api-gateway --replicas=0 -n gfin
# Drain application workloads
helm uninstall gfin-core
# Drain infrastructure safely
helm uninstall gfin-infra
```

---

## 3. Entity Management Operations

Entities are the primary data structures representing actors, infrastructure, accounts, and identifiers in GFIN.

### 3.1 Creating Entities
Operators can create entities programmatically or via API endpoints using canonical schemas.

```python
import sys
sys.path.insert(0, '/gfin')
from packages.schemas.entities import DomainEntity
from packages.schemas.enums import DataClassification

# Step 1: Instantiate Entity Model
domain_entity = DomainEntity(
    domain_name="fraudulent-phishing-bank.com",
    registrar="BadActor Registrar LLC",
    organization_id="ORG-LE-US-001",
    jurisdiction="US",
    classification=DataClassification.RESTRICTED
)

print(f"Created Entity ID: {domain_entity.id}")
print(f"Normalized Key: {domain_entity.normalized_value}")
```
**Expected Output:**
```
Created Entity ID: ENT-DOMAIN-a1b2c3d4-8e9f...
Normalized Key: fraudulent-phishing-bank.com
```

### 3.2 Resolving and Matching Entities (Module 04)
The Entity Resolution Engine compares incoming entity data against known entities using rule-based normalizers and similarity scoring.

```python
from packages.services.entity_resolution import EntityResolutionEngine, MatchRule

engine = EntityResolutionEngine()

# Evaluate candidate matching
match_result = engine.resolve_candidate(
    entity_type="domain",
    raw_value="FRAUDULENT-PHISHING-BANK.COM"
)

print(f"Match Found: {match_result.is_match}")
print(f"Matched Entity ID: {match_result.matched_entity_id}")
print(f"Confidence Score: {match_result.confidence_score}")
```
**Expected Output:**
```
Match Found: True
Matched Entity ID: ENT-DOMAIN-a1b2c3d4-8e9f...
Confidence Score: 1.00
```

### 3.3 Merging and Splitting Entities
When two entities are confirmed to represent the same underlying real-world actor or infrastructure, operators merge them:

```python
merge_record = engine.merge_entities(
    primary_id="ENT-DOMAIN-a1b2c3d4",
    secondary_id="ENT-DOMAIN-z9y8x7w6",
    merged_by="OPERATOR-42",
    reason="Identical WHOIS registrant and co-located IP"
)

print(f"Merge Status: {merge_record.status}")
print(f"Active Primary ID: {merge_record.primary_id}")
```
**Expected Output:**
```
Merge Status: MERGED
Active Primary ID: ENT-DOMAIN-a1b2c3d4
```

---

## 4. Evidence Vault Operations (Module 06)

The Evidence Vault maintains tamper-evident, cryptographically verifiable records with strict chain-of-custody tracking.

### 4.1 Storing Evidence and Generating Hash
```python
from packages.services.evidence_vault import EvidenceVault, EvidenceItem
from packages.schemas.enums import DataClassification

vault = EvidenceVault()

# Create evidence item
evidence = vault.store_evidence(
    title="Phishing Site HTML Artifact",
    content_bytes=b"<html><form action='http://evil.com/steal'>...</form></html>",
    classification=DataClassification.LAW_ENFORCEMENT,
    submitted_by="OPERATOR-01",
    organization_id="ORG-US-FBI"
)

print(f"Evidence ID: {evidence.id}")
print(f"SHA-256 Digest: {evidence.content_hash}")
```
**Expected Output:**
```
Evidence ID: EVD-8f3a9b2c...
SHA-256 Digest: 4a2e56... (64-char hex string)
```

### 4.2 Verifying Evidence Integrity
```python
is_valid = vault.verify_evidence_hash(evidence.id)
print(f"Verification Check Result: {'PASS - TAMPER FREE' if is_valid else 'FAIL - ALTERED'}")
```
**Expected Output:**
```
Verification Check Result: PASS - TAMPER FREE
```

### 4.3 Retention Policy Enforcement
Retention rules are governed by data classification:
- `PUBLIC`: 5 Years
- `COMMUNITY`: 7 Years
- `LAW_ENFORCEMENT`: 10 Years
- `RESTRICTED`: 15 Years
- `HIGHLY_RESTRICTED`: 20 Years

```python
expired_items = vault.audit_retention_expirations()
print(f"Items Pending Retention Purge: {len(expired_items)}")
```

---

## 5. Event Bus & DLQ Management (Module 05)

GFIN uses an asynchronous pub/sub event bus supporting 14 core topics (e.g., `fraud.report.submitted`, `entity.resolved`, `campaign.detected`, `alert.generated`).

### 5.1 Publishing and Subscribing
```python
from packages.events.event_bus import EventBus, Event

bus = EventBus()

# Subscribe operator handler
def handle_fraud_report(event: Event):
    print(f"[EVENT RECEIVED] Topic: {event.topic} | Payload: {event.payload}")

bus.subscribe("fraud.report.submitted", handle_fraud_report)

# Publish event
bus.publish(
    topic="fraud.report.submitted",
    payload={"report_id": "REP-9921", "risk_score": 88.5},
    sender="OPERATOR-CONSOLE"
)
```
**Expected Output:**
```
[EVENT RECEIVED] Topic: fraud.report.submitted | Payload: {'report_id': 'REP-9921', 'risk_score': 88.5}
```

### 5.2 Dead Letter Queue (DLQ) Operations
When a subscriber handler fails repeatedly (e.g., maximum retry limit exceeded), the event bus routes the failed payload to the DLQ:

```python
# Inspect DLQ
dlq_messages = bus.get_dlq_messages()
print(f"DLQ Message Count: {len(dlq_messages)}")

# Replay messages from DLQ
replayed_count = bus.replay_dlq(topic_filter="fraud.report.submitted")
print(f"Successfully Replayed Messages: {replayed_count}")
```

---

## 6. Campaign Management Operations (Module 16)

A Campaign represents an orchestrated cluster of fraud activity linked across multiple reports, entities, and technical infrastructure.

### 6.1 Automated Campaign Detection & Scoring
```python
from packages.services.campaign_engine import CampaignEngine

campaign_service = CampaignEngine()

# Run correlation across unlinked high-risk reports
new_campaign = campaign_service.detect_campaigns(min_linked_reports=3)

if new_campaign:
    print(f"Campaign Detected: {new_campaign.id}")
    print(f"Campaign Title: {new_campaign.title}")
    print(f"Threat Score: {new_campaign.score} / 100")
```
**Expected Output:**
```
Campaign Detected: CMP-2026-08-004
Campaign Title: Global Banking Smishing Cluster - Delta
Threat Score: 92.4 / 100
```

### 6.2 Campaign Lifecycle Transitions
Campaigns transition through a controlled state machine:
`DRAFT` ──▶ `ACTIVE` ──▶ `DORMANT` ──▶ `DISMANTLED`

```python
# Transition campaign state
updated_campaign = campaign_service.update_status(
    campaign_id="CMP-2026-08-004",
    new_status="ACTIVE",
    operator_id="OPERATOR-01",
    justification="Validated cross-border infrastructure linkage"
)
print(f"New Campaign Lifecycle State: {updated_campaign.status}")
```

---

## 7. Alert Configuration & Routing (Module 18)

The Alert Engine routes real-time threat notifications to operational channels based on priority (`P0_CRITICAL`, `P1_HIGH`, `P2_MEDIUM`, `P3_LOW`).

```python
from packages.services.alert_engine import AlertEngine, AlertRule

alert_engine = AlertEngine()

# Configure Alert Routing Rule
rule = AlertRule(
    rule_id="RULE-P0-CRITICAL-SMS",
    min_priority="P0_CRITICAL",
    channels=["WEBHOOK", "SMS", "POLICE_API"],
    destination_org="ORG-LE-EUROPOL"
)
alert_engine.add_rule(rule)

# Dispatch Test Alert
alert = alert_engine.dispatch_alert(
    title="Critical Zero-Day Phishing Cluster Detected",
    priority="P0_CRITICAL",
    category="PHISHING_CAMPAIGN",
    details={"campaign_id": "CMP-2026-08-004"}
)

print(f"Alert ID: {alert.id} Dispatched to Channels: {alert.dispatched_channels}")
```
**Expected Output:**
```
Alert ID: ALT-8812 Dispatched to Channels: ['WEBHOOK', 'SMS', 'POLICE_API']
```

---

## 8. System Monitoring and Health Checks (Module 34)

Operators monitor system health, service metrics, and error rates via standard status endpoints and metrics snapshots.

```python
from packages.observability.metrics import MetricsCollector

metrics = MetricsCollector()
snapshot = metrics.get_snapshot()

print("--- GFIN OPERATIONAL METRICS SNAPSHOT ---")
print(f"Total Reports Ingested: {snapshot.get('reports_total', 0)}")
print(f"Active Resolved Entities: {snapshot.get('entities_resolved_total', 0)}")
print(f"DLQ Backlog Count: {snapshot.get('event_bus_dlq_count', 0)}")
print(f"P99 API Response Latency: {snapshot.get('api_latency_p99_ms', 0.0)} ms")
```

---

## 9. Operator Checklist & Verification Matrix

Before concluding operational shifts, operators must verify:
- [ ] Platform health check status is `HEALTHY` across all components.
- [ ] Dead Letter Queue (DLQ) depth is zero or all failed messages have been triaged.
- [ ] Evidence Vault integrity check returns `PASS`.
- [ ] P0 Critical alerts have been assigned to active investigation leads.
