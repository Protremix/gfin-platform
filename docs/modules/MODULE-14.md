# MODULE 14 — Fraud Reporting

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 13 provides the citizen-facing submission interface. Module 14 is the **backend processing pipeline** that takes submitted reports and prepares them for analysis:

1. **Triage** — automated categorization, priority assessment, spam/junk detection
2. **Enrichment** — link to entities, infrastructure intelligence, related reports
3. **Scoring** — calculate a composite risk score from multiple signals
4. **Deduplication** — detect and merge duplicate reports for the same entity
5. **Campaign Linking** — associate reports with active fraud campaigns

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `ReportTriageService` — automated triage pipeline
- `ReportEnrichmentService` — enrich with entity/infrastructure data
- `ReportScoringService` — composite risk scoring
- `ReportDeduplicationService` — duplicate detection
- `CampaignLinkingService` — link reports to campaigns
- Synthetic fixtures only

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Kafka-streamed processing pipeline
- Redis-backed dedup cache
- PostgreSQL-backed report persistence
- AI-assisted triage (via Model Gateway)
- Real-time campaign correlation engine

---

## 3. Key Components

### 3.1 ReportTriageService
- Accept a raw report from Module 13
- Validate and normalize category
- Assign priority: LOW, MEDIUM, HIGH, URGENT based on:
  - Category severity (e.g., active_phishing = HIGH)
  - Reporter credibility (repeat reporter = boost)
  - Entity risk level (known high-risk entity = boost)
  - Volume spike (many reports for same entity = URGENT)
- Spam/junk detection:
  - Too short description (< 10 chars)
  - Repeated submissions from same reporter
  - Gibberish detection (no real words)
  - Mark as SPAM status
- Publish `report.triaged` event

### 3.2 ReportEnrichmentService
- For each report:
  - Resolve entity references (Module 04)
  - Link to infrastructure intelligence (Module 09)
  - Find related reports for same entity
  - Find related campaigns
  - Attach enrichment metadata

### 3.3 ReportScoringService
- Composite risk score (0-100) from:
  - Report count for entity (weight: 25)
  - Corroborated report count (weight: 30)
  - Evidence count (weight: 20)
  - Campaign association (weight: 15)
  - Entity risk level (weight: 10)
- Score bands:
  - 0-20: LOW
  - 21-50: MEDIUM
  - 51-75: HIGH
  - 76-100: CRITICAL
- Store score on report metadata

### 3.4 ReportDeduplicationService
- Detect duplicate reports:
  - Same entity + same category + similar description (Levenshtein > 0.8)
  - Same reporter + same entity within 24h
- Mark duplicates: keep original, mark others as DUPLICATE status
- Publish `report.deduplicated` event

### 3.5 CampaignLinkingService
- For each report:
  - Check if entity matches any active campaign
  - If match, link report to campaign
  - Publish `report.campaign_linked` event

---

## 4. Security Constraints

1. All processing respects data classification boundaries
2. Enrichment only uses data the report's classification allows
3. Scoring algorithm is auditable and deterministic
4. Spam detection is non-blocking (marks, doesn't delete)
5. Deduplication preserves original report provenance

---

## 5. Acceptance Criteria

1. Triage assigns correct priority based on category + signals
2. Spam/junk reports are detected and marked
3. Enrichment links reports to entities and related data
4. Scoring produces 0-100 score with correct band
5. Duplicate reports are detected and marked
6. Reports are linked to matching campaigns
7. All processing events are published
8. Priority can be overridden by admin
9. Triage handles edge cases (empty, gibberish, repeat)
10. Scoring is deterministic for same inputs

---

## 6. Test Plan

- Unit: ReportTriageService (priority, spam, edge cases)
- Unit: ReportEnrichmentService (entity link, related, campaign)
- Unit: ReportScoringService (score calculation, bands, determinism)
- Unit: ReportDeduplicationService (detection, marking)
- Unit: CampaignLinkingService (link, no-match)
- Integration: full pipeline submit → triage → enrich → score → dedup → campaign

---

## 7. Dependencies

- Module 02 (Security) — audit, validation
- Module 03 (Core Data Model) — BaseReport, entities, campaigns
- Module 04 (Entity Resolution) — normalizers, matching
- Module 05 (Event Bus) — event publishing
- Module 09 (Infrastructure Intelligence) — enrichment data
- Module 13 (Citizen Platform) — report source
