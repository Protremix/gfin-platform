# MODULE 15 — Fraud Detection

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 15 is the **Fraud Detection Engine** — it takes enriched, scored reports
(from Module 14) and applies detection rules and pattern matching to identify
confirmed fraud patterns with confidence levels.

This is the system that turns raw reports + entity data + intelligence into
**actionable fraud detections**.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `DetectionRule` — rule definitions (signal-based, pattern-based, threshold-based)
- `FraudDetectionEngine` — evaluates reports against rules
- `SignalDetector` — detects individual fraud signals
- `PatternMatcher` — matches multi-entity, multi-report patterns
- `DetectionResult` — output with matched rules, confidence, signals
- Synthetic fixtures only

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Kafka-streamed detection pipeline
- Redis-backed rule cache
- ML model integration via Model Gateway
- Real-time pattern correlation engine
- Graph database for pattern matching (Neo4j)

---

## 3. Key Components

### 3.1 DetectionRule
A rule that defines a fraud pattern:
- `id` — unique rule identifier
- `name` — human-readable name
- `rule_type` — SIGNAL, PATTERN, THRESHOLD, COMPOSITE
- `category` — fraud category this rule detects
- `conditions` — list of conditions (field, operator, value)
- `min_confidence` — minimum confidence to trigger (0-1)
- `severity` — LOW, MEDIUM, HIGH, CRITICAL
- `enabled` — on/off
- `description` — what this rule detects

### 3.2 FraudDetectionEngine
- Register/unregister rules
- Evaluate a report against all enabled rules
- Return list of DetectionResults (one per matched rule)
- Track detection history
- Publish `fraud.detected` event

### 3.3 SignalDetector
- Individual fraud signals:
  - NEW_DOMAIN_SHORT_LIFESPAN: domain registered < 30 days
  - HIGH_REPORT_VOLUME: 5+ reports for same entity
  - CROSS_CATEGORY_PATTERN: same entity reported in 3+ categories
  - KNOWN_BAD_INFRASTRUCTURE: entity on known bad IP/ASN
  - EVIDENCE_CORROBORATION: 2+ corroborated reports
  - CAMPAIGN_CORRELATION: entity linked to active campaign
  - REPEAT_REPORTER_HIGH_CONFIDENCE: 5+ reports from credible reporter

### 3.4 PatternMatcher
- Multi-entity patterns:
  - SAME_ENTITY_MULTIPLE_REPORTS: same entity, 3+ reports
  - INFRASTRUCTURE_OVERLAP: multiple entities sharing infrastructure
  - TEMPORAL_CLUSTERING: 3+ reports within 1 hour for same category
  - CROSS_JURISDICTION: reports from 3+ countries for same entity

### 3.5 DetectionResult
- `report_id` — which report triggered the detection
- `rule_id` — which rule matched
- `rule_name` — human-readable name
- `signals` — list of matched signals
- `confidence` — 0-1 confidence score
- `severity` — LOW/MEDIUM/HIGH/CRITICAL
- `entity_ids` — entities involved
- `detected_at` — timestamp

---

## 4. Detection Logic

### Signal-based detection
Each signal contributes to confidence:
- HIGH_REPORT_VOLUME: +0.2
- EVIDENCE_CORROBORATION: +0.3
- CAMPAIGN_CORRELATION: +0.25
- NEW_DOMAIN_SHORT_LIFESPAN: +0.15
- KNOWN_BAD_INFRASTRUCTURE: +0.2
- CROSS_CATEGORY_PATTERN: +0.15
- REPEAT_REPORTER_HIGH_CONFIDENCE: +0.1

Max confidence = 1.0 (capped).

### Pattern-based detection
Patterns are higher-level:
- Same entity with 5+ reports AND 2+ corroborated = HIGH confidence
- Infrastructure overlap across 3+ entities = MEDIUM confidence
- Temporal clustering of 10+ reports = HIGH confidence

### Threshold-based detection
- Entity risk score >= 75 = automatic HIGH detection
- Entity risk score >= 90 = automatic CRITICAL detection

---

## 5. Acceptance Criteria

1. Detection rules can be registered/unregistered
2. Engine evaluates reports against all enabled rules
3. Signal detector correctly identifies individual signals
4. Pattern matcher correctly identifies multi-entity patterns
5. Confidence is calculated correctly from signals
6. Severity is assigned based on confidence and rule severity
7. Detection events are published
8. Disabled rules are not evaluated
9. Detection history is tracked
10. Threshold-based detection triggers at correct score levels

---

## 6. Test Plan

- Unit: DetectionRule (validation, enable/disable)
- Unit: FraudDetectionEngine (register, evaluate, history)
- Unit: SignalDetector (each signal type)
- Unit: PatternMatcher (each pattern type)
- Unit: DetectionResult (confidence calc, severity)
- Integration: full detection pipeline

---

## 7. Dependencies

- Module 03 (Core Data Model) — entities, reports
- Module 05 (Event Bus) — event publishing
- Module 14 (Fraud Reporting) — enriched/scored reports
- Module 09 (Infrastructure Intelligence) — infrastructure data
