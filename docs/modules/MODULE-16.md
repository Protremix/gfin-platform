# MODULE 16 — Campaign Engine

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 16 is the **Campaign Engine** — it detects, creates, manages, and tracks
fraud campaigns. A campaign is a set of correlated entities, reports, and
infrastructure indicators that together suggest a coordinated fraud operation.

Campaigns are **probabilistic** unless supported by authoritative evidence
(Constitution §22: "Campaigns are probabilistic unless supported by
authoritative evidence").

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `CampaignEngine` — create, update, detect, link, lifecycle management
- `CampaignDetector` — detect new campaigns from clusters of reports/entities
- `CampaignScorer` — score campaign severity from linked entities
- `CampaignLinker` — link reports/entities to existing campaigns
- Synthetic fixtures only

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Kafka-streamed campaign detection pipeline
- Neo4j graph database for entity clustering
- Real-time correlation engine
- ML-assisted campaign identification

---

## 3. Key Components

### 3.1 CampaignEngine
- `create_campaign` — create a new campaign
- `update_campaign` — update campaign properties
- `dismantle_campaign` — mark as DISMANTLED
- `reactivate_campaign` — move DORMANT → ACTIVE
- `link_entity` — link an entity to a campaign
- `unlink_entity` — remove entity from campaign
- `link_report` — link a report to a campaign
- `get_campaign` — retrieve campaign by ID
- `list_campaigns` — list all campaigns, optionally filtered by status
- Publish `campaign.created`, `campaign.updated`, `campaign.dismantled` events

### 3.2 CampaignDetector
- `detect_from_reports` — analyze a batch of reports for campaign-worthy clusters
  - Group reports by shared entities + same category
  - If 3+ reports share entities + same category → candidate campaign
  - If 2+ entities share infrastructure → candidate campaign
- `detect_from_entities` — cluster entities by shared infrastructure
  - Same IP/ASN across entities → cluster
  - Same SSL cert hash → cluster
  - Same DNS records → cluster
- Returns candidate campaigns (not yet created)

### 3.3 CampaignScorer
- `score_campaign` — calculate campaign severity from:
  - Entity count (weight: 20)
  - Report count (weight: 25)
  - Corroborated report count (weight: 30)
  - Affected country count (weight: 15)
  - Infrastructure overlap (weight: 10)
- Severity bands:
  - 0-25: LOW
  - 26-50: MEDIUM
  - 51-75: HIGH
  - 76-100: CRITICAL

### 3.4 CampaignLinker
- `link_report_to_campaigns` — find matching campaigns for a report
  - Entity overlap with campaign entities
  - Fraud type match
- `link_entity_to_campaigns` — find matching campaigns for an entity
  - Infrastructure overlap
  - Entity in same cluster

---

## 4. Campaign Lifecycle

```
DRAFT → ACTIVE → DORMANT → DISMANTLED
                ↑     ↓
                └─────┘ (reactivate)
```

- **DRAFT**: Campaign detected but not confirmed
- **ACTIVE**: Campaign confirmed and being tracked
- **DORMANT**: No new activity for 30+ days
- **DISMANTLED**: Campaign taken down (manually or detected)

---

## 5. Security Constraints

1. Campaigns are probabilistic — must be marked as such
2. Campaign data classification defaults to RESTRICTED
3. Only authorized roles can dismantle/reactivate campaigns
4. All campaign changes are audited
5. Entity linking respects entity classification boundaries

---

## 6. Acceptance Criteria

1. Campaigns can be created, updated, dismantled, reactivated
2. Detector correctly identifies campaign-worthy clusters
3. Scorer produces 0-100 severity with correct band
4. Linker correctly matches reports/entities to campaigns
5. Entity overlap detection works
6. Infrastructure overlap detection works
7. Campaign lifecycle state machine is enforced
8. Events are published for all state transitions
9. Campaign detection from reports works (3+ reports → candidate)
10. Audit logging for all changes

---

## 7. Test Plan

- Unit: CampaignEngine (CRUD, lifecycle, linking)
- Unit: CampaignDetector (report clustering, entity clustering)
- Unit: CampaignScorer (score calculation, bands)
- Unit: CampaignLinker (report linking, entity linking)
- Integration: full pipeline detect → create → score → link

---

## 8. Dependencies

- Module 03 (Core Data Model) — BaseCampaign, entities, reports
- Module 05 (Event Bus) — event publishing
- Module 14 (Fraud Reporting) — enriched reports
- Module 15 (Fraud Detection) — detection results
