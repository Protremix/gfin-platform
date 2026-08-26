# MODULE 31 — Global Early Warning

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 31 implements the Global Early Warning system — the proactive
detection and alerting component based on the Continuous Intelligence loop
per Directive §13: DISCOVER → CORRELATE → MONITOR → CHANGE DETECT →
REANALYZE → ALERT → DISCOVER AGAIN.

The system monitors for emerging threats, entity infrastructure changes,
campaign escalations, and anomalous patterns, issuing early warning
notifications before they become critical alerts.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP)
- `EarlyWarningEngine` — monitors and detects emerging threats
- `WarningRule` — configurable rules for early warning triggers
- `WarningLevel` — INFO, WATCH, WARNING, CRITICAL
- `WarningEvent` — a detected early warning event
- `WarningMonitor` — tracks entities and campaigns for changes
- `WarningNotification` — notification dispatched to operators

### Layer B (Production)
- Real-time Kafka stream processing
- ML-based anomaly detection
- Integration with Module 05 (Event Bus) for live events
- REQUIRES EXTERNAL INFRASTRUCTURE

---

## 3. Warning Rules

Rules define conditions that trigger early warnings:
- Entity velocity: new entities appearing at unusual rate
- Campaign escalation: campaign confidence increasing rapidly
- Infrastructure change: domain/IP infrastructure modified
- New correlation: new entity-to-campaign link detected
- Jurisdiction spread: campaign spreading to new jurisdictions

---

## 4. Acceptance Criteria

1. WarningRule defines condition, threshold, level, and scope
2. EarlyWarningEngine evaluates rules against monitored data
3. WarningLevel escalates: INFO < WATCH < WARNING < CRITICAL
4. WarningEvent captures detection details
5. WarningMonitor tracks entity and campaign changes
6. Notifications dispatched for WARNING and CRITICAL levels
7. Rules can be added, removed, and listed
8. Historical warnings can be retrieved
9. Each warning has a timestamp, rule, and detected data

---

## 5. Dependencies

- Module 03 (Core Data Model) — entity types
- Module 18 (Alert Engine) — alert infrastructure
