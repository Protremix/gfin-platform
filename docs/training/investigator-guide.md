# GFIN Fraud Investigator Guide

**Document Version:** 1.0  
**Target Audience:** Fraud Analysts, Senior Investigators, Sworn Law Enforcement Officers  
**Scope:** Practical Fraud Investigation, Intelligence Synthesis, and Cross-Border Coordination  

---

## 1. Fraud Report Intake and Triage Workflow (Module 14)

The GFIN Fraud Intake Pipeline receives fraud reports from citizens, financial institutions, and automated web crawlers. Reports undergo automated triage, spam filtering, composite risk scoring (0–100), and deduplication.

```
[ Incoming Report ] ──▶ [ Spam & Volume Check ] ──▶ [ Entity Enrichment ] ──▶ [ Composite Risk Scoring ]
                                                                                   │
                                                                                   ▼
[ Triage Decision ] ◄── [ Duplicate Detection (Similarity > 0.8) ] ◄───────────────┘
```

### 1.1 Ingesting and Triaging Reports Programmatically

```python
import sys
sys.path.insert(0, '/gfin')
from packages.services.fraud_reporting import FraudReportingService, RawReport

triage_service = FraudReportingService()

# Ingest new raw report
report = triage_service.submit_report(
    reporter_type="CITIZEN",
    category="PHISHING_FINANCIAL",
    title="Spoofed Online Banking Portal Stealing Credentials",
    description="Received SMS asking to update credentials at http://secure-verify-bank.com",
    raw_indicators=["http://secure-verify-bank.com", "+18005550199"],
    jurisdiction="US"
)

print(f"Report ID: {report.id}")
print(f"Initial Status: {report.status}")
print(f"Triage Priority: {report.priority}")
print(f"Composite Risk Score: {report.composite_score} / 100")
```
**Expected Output:**
```
Report ID: REP-2026-0881
Initial Status: TRIAGED
Triage Priority: HIGH
Composite Risk Score: 84.5 / 100
```

### 1.2 Deduplication and Linking
When duplicate reports (similarity score > 0.8) are detected, they are automatically linked to the primary parent report:

```python
duplicates = triage_service.find_duplicates(report_id="REP-2026-0881")
print(f"Linked Duplicate Reports: {[d.id for d in duplicates]}")
```

---

## 2. Entity Investigation & Graph Traversal (Modules 03 & 07)

GFIN represents infrastructure and actors in a property graph containing 26 concrete entity types and 20 relationship types (e.g., `RESOLVES_TO`, `REGISTERED_BY`, `HOSTED_ON`, `TRANSITIONED_TO`).

### 2.1 Graph Traversal & Relationship Analysis

```python
from packages.services.search import SearchPlatform

search = SearchPlatform()

# Search entity by identifier
results = search.search_fuzzy(query="secure-verify-bank.com")
primary_entity = results[0]

# Perform multi-hop graph expansion
graph_neighborhood = search.expand_graph_neighborhood(
    entity_id=primary_entity.id,
    max_depth=2,
    direction="BOTH"
)

print(f"Primary Entity: {primary_entity.normalized_value} ({primary_entity.entity_type})")
print(f"Discovered Connected Nodes: {len(graph_neighborhood.nodes)}")
print(f"Discovered Connected Relationships: {len(graph_neighborhood.edges)}")

for edge in graph_neighborhood.edges:
    print(f" - [{edge.source_id}] ──({edge.relationship_type})──▶ [{edge.target_id}]")
```
**Expected Output:**
```
Primary Entity: secure-verify-bank.com (domain)
Discovered Connected Nodes: 4
Discovered Connected Relationships: 3
 - [ENT-DOMAIN-1] ──(RESOLVES_TO)──▶ [ENT-IP-192.0.2.1]
 - [ENT-DOMAIN-1] ──(REGISTERED_BY)──▶ [ENT-ACTOR-WHOIS-99]
 - [ENT-IP-192.0.2.1] ──(HOSTED_ON)──▶ [ENT-ASN-65534]
```

---

## 3. Evidence Collection & Chain of Custody (Module 06)

Investigators attach digital artifacts (PCAP files, HTML dumps, screenshots, wallet ledgers) to cases with immutable cryptographic chain-of-custody logging.

```python
from packages.services.evidence_vault import EvidenceVault, CustodyAction

vault = EvidenceVault()

# Add evidence record to case
evidence = vault.attach_evidence_to_case(
    case_id="CASE-2026-004",
    title="Phishing Server Memory Dump",
    content_bytes=b"\x7fELF...",
    collector_id="INVESTIGATOR-J-SMITH",
    classification="RESTRICTED"
)

# Transfer chain of custody
vault.record_custody_transfer(
    evidence_id=evidence.id,
    from_user="INVESTIGATOR-J-SMITH",
    to_user="FORENSIC-LAB-LEAD",
    action=CustodyAction.HANDOFF,
    notes="Transferred for deep memory forensics"
)

# Verify complete chain of custody audit log
custody_history = vault.get_custody_history(evidence.id)
for entry in custody_history:
    print(f"[{entry.timestamp}] {entry.action}: {entry.from_user} -> {entry.to_user} ({entry.notes})")
```

---

## 4. Campaign Analysis & Infrastructure Linking (Module 16)

Investigators group correlated reports and shared infrastructure into unified threat campaigns to evaluate systemic impact.

```python
from packages.services.campaign_engine import CampaignEngine

campaign_engine = CampaignEngine()

# Link newly discovered domain entity to active campaign
campaign = campaign_engine.link_entity_to_campaign(
    campaign_id="CMP-2026-08-004",
    entity_id=primary_entity.id,
    investigator_id="INVESTIGATOR-J-SMITH"
)

# Recalculate campaign risk profile
new_score = campaign_engine.recalculate_campaign_score(campaign.id)
print(f"Updated Campaign Score: {new_score}")
```

---

## 5. Cross-Border Request Workflow (Module 26)

When fraud infrastructure or actors operate in external jurisdictions, investigators execute the 7-stage Cross-Border Request workflow:

```
[1. SUBMIT] ──▶ [2. VALIDATE] ──▶ [3. AUTHORIZE] ──▶ [4. ROUTE] ──▶ [5. REVIEW] ──▶ [6. DECIDE] ──▶ [7. CLOSE]
```

```python
from packages.services.cross_border_requests import CrossBorderRequestEngine, LegalBasis, UrgencyLevel

cb_engine = CrossBorderRequestEngine()

# Stage 1: SUBMIT Request
req = cb_engine.create_request(
    requesting_org="ORG-US-FBI",
    requesting_jurisdiction="US",
    target_jurisdiction="DE",
    investigator_name="Agent J. Smith",
    legal_basis=LegalBasis.MLAT_TREATY,
    purpose="Investigating transnational wire fraud ring",
    case_reference="CASE-2026-004",
    entity_id="ENT-IP-192.0.2.1",
    entity_type="ip_address",
    entity_value="192.0.2.1",
    requested_information="Subscriber records and server hosting payment logs",
    urgency=UrgencyLevel.PRIORITY
)
print(f"Stage 1 Complete - Status: {req.status}") # SUBMITTED

# Stage 2: VALIDATE
val_res = cb_engine.validate_request(req.id)
print(f"Stage 2 Complete - Validated: {val_res.is_valid}") # True

# Stage 3: AUTHORIZE
auth_res = cb_engine.authorize_request(req.id)
print(f"Stage 3 Complete - Authorized: {auth_res.is_authorized}") # True

# Stage 4: ROUTE
route_res = cb_engine.route_request(req.id)
print(f"Stage 4 Complete - Routed to Target Jurisdiction: {route_res.target_jurisdiction}") # DE

# Stage 5: REVIEW (Executed by Target Jurisdiction Officer)
cb_engine.start_review(req.id, reviewer_id="OFFICER-DE-BKA-01")

# Stage 6: DECIDE (APPROVE, PARTIAL, DENY)
decision = cb_engine.make_decision(
    request_id=req.id,
    decision_type="APPROVE",
    response_data={"hosting_provider": "Hetzner Online GmbH", "subscriber": "Redacted/Subpoena Attached"},
    reviewer_id="OFFICER-DE-BKA-01"
)
print(f"Stage 6 Complete - Decision: {decision.decision_type}")

# Stage 7: CLOSE & AUDIT
closed_req = cb_engine.close_request(req.id)
print(f"Stage 7 Complete - Final State: {closed_req.status}") # CLOSED
```

---

## 6. Crypto Intelligence & Fund Tracing (Module 28)

GFIN provides crypto wallet profiling and multi-hop transaction fund tracing across 6 blockchains (BTC, ETH, TRX, SOL, BSC, AVAX).

```python
from packages.services.crypto_intelligence import CryptoIntelligenceService

crypto_service = CryptoIntelligenceService()

# Profile cryptocurrency wallet
profile = crypto_service.profile_wallet(
    address="0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    blockchain="ETH"
)
print(f"Wallet Cluster Tag: {profile.cluster_tag}")
print(f"Risk Assessment Rating: {profile.risk_score} / 100")

# Trace flow of illicit funds (Breadth-First Search)
trace_result = crypto_service.trace_fund_flow(
    start_address="0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    blockchain="ETH",
    max_hops=4,
    min_amount_usd=1000.0
)

print(f"Fund Trace Hops Analyzed: {len(trace_result.hops)}")
for hop in trace_result.hops:
    print(f"Hop {hop.hop_index}: {hop.from_address} -> {hop.to_address} | Amount: {hop.amount} ETH | Mixer/Exchange Flag: {hop.is_known_entity}")
```

---

## 7. AI Investigation Orchestrator Usage (Module 22)

The AI Investigation Orchestrator empowers investigators with 15 authorized investigation tools under role-based access control:

### 7.1 Registered Investigation Tools (15 Tools)
1. `search_web`: Controlled web search for OSINT artifacts (`INVESTIGATOR`)
2. `inspect_url`: Crawl and extract page structure/headers (`INVESTIGATOR`)
3. `domain_lookup`: WHOIS & RDAP domain queries (`INVESTIGATOR`)
4. `rdap_lookup`: Regional Internet Registry query (`INVESTIGATOR`)
5. `dns_lookup`: DNS resolution & historical record lookup (`INVESTIGATOR`)
6. `ip_lookup`: IP geolocation & ASN query (`INVESTIGATOR`)
7. `certificate_lookup`: SSL/TLS X.509 cert SAN tracking (`INVESTIGATOR`)
8. `infrastructure_history`: Passive DNS & historical IP mapping (`INVESTIGATOR`)
9. `graph_search`: Multi-hop entity graph traversal (`INVESTIGATOR`)
10. `report_search`: Historical report pattern search (`INVESTIGATOR`)
11. `campaign_search`: Cross-campaign matching (`INVESTIGATOR`)
12. `case_search`: Case dossier search (`INVESTIGATOR`)
13. `entity_compare`: Deduplication & entity similarity evaluation (`INVESTIGATOR`)
14. `create_alert`: Dispatch high-priority alert (`SUPERVISOR` required)
15. `request_information`: Initiate formal cross-border request (`SUPERVISOR` required)

### 7.2 Executing AI Orchestration Workflows

```python
from packages.services.investigation_orchestrator import AIInvestigationOrchestrator

orchestrator = AIInvestigationOrchestrator()

# Execute automated multi-step investigation plan
plan_result = orchestrator.execute_investigation_plan(
    investigator_role="INVESTIGATOR",
    target_entity="http://secure-verify-bank.com",
    steps=["inspect_url", "dns_lookup", "ip_lookup", "graph_search"]
)

print("--- AI INVESTIGATION SYNTHESIS ---")
print(f"Evidence Claims Found: {len(plan_result.claims)}")
print(f"Requires Human Verification Flag: {plan_result.requires_human_review}")
print(f"Summary Report: {plan_result.summary}")
```

---

## 8. Report Generation & STIX 2.1 Export (Module 30 / OSINT Stack)

Investigators generate standard investigation reports and export threat intelligence in STIX 2.1 JSON format for dissemination.

```python
from packages.services.stix_exporter import STIXExporter

exporter = STIXExporter()

# Export Campaign & Entities as STIX 2.1 Bundle
stix_json = exporter.export_campaign_bundle(
    campaign_id="CMP-2026-08-004",
    include_indicators=True,
    include_relationships=True
)

print("--- STIX 2.1 JSON BUNDLE (SAMPLE OUTPUT) ---")
print(stix_json[:300] + "\n... [TRUNCATED STIX JSON] ...")
```
**Expected Output:**
```json
{
  "type": "bundle",
  "id": "bundle--5f2a11b9-8c22-481e-92a1-001281229101",
  "objects": [
    {
      "type": "campaign",
      "spec_version": "2.1",
      "id": "campaign--c8211029-...",
      "name": "Global Banking Smishing Cluster - Delta",
      "confidence": 90
    }
  ]
}
```
