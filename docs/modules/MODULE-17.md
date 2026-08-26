# MODULE 17 — Continuous Monitoring

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 17 implements the **Continuous Monitoring** loop from the Constitution's
Continuous Intelligence principle:

```
DISCOVER → CORRELATE → MONITOR → CHANGE DETECTED → REANALYZE → ALERT → DISCOVER AGAIN
```

It monitors entities and campaigns for changes, triggers re-analysis, and
generates alerts when risk thresholds are crossed.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `SubscriptionService` — subscribe/unsubscribe to entity/campaign monitoring
- `ChangeDetector` — detect entity changes (new observations, risk changes, new reports)
- `MonitoringEngine` — orchestrate monitoring loop, evaluate subscriptions
- `AlertEngine` — generate alerts from detected changes
- Synthetic fixtures only

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Kafka-streamed change events
- Redis-backed subscription state
- Real-time change detection via database triggers
- WebSocket push notifications
- Email/SMS alert delivery

---

## 3. Key Components

### 3.1 SubscriptionService
- `subscribe` — subscribe to entity or campaign monitoring
  - entity_id: monitor a specific entity
  - campaign_id: monitor a campaign
  - watch_types: list of change types to watch
  - callback: how to notify (event, alert)
- `unsubscribe` — stop monitoring
- `list_subscriptions` — list active subscriptions
- `get_subscription` — retrieve subscription details

### 3.2 ChangeDetector
- `detect_entity_changes` — compare entity snapshot vs current state
  - NEW_OBSERVATION: entity has new observations
  - RISK_LEVEL_CHANGED: entity risk level changed
  - NEW_REPORTS: new reports filed for entity
  - INFRASTRUCTURE_CHANGED: entity infrastructure changed
  - CAMPAIGN_LINKED: entity linked to new campaign
- `detect_campaign_changes` — compare campaign snapshot vs current state
  - NEW_ENTITIES: campaign has new entities
  - SEVERITY_CHANGED: campaign severity changed
  - STATUS_CHANGED: campaign status changed
  - ACTIVITY_SPIKE: sudden increase in reports

### 3.3 MonitoringEngine
- `run_check` — check all subscriptions for changes
  - For each subscription, detect changes
  - If changes detected, trigger alert engine
  - Record monitoring check timestamp
- `get_status` — get monitoring status for an entity/campaign
- `evaluate` — evaluate a single subscription

### 3.4 AlertEngine
- `evaluate_changes` — process detected changes and generate alerts
  - Alert types: RISK_ESCALATION, NEW_REPORT, INFRASTRUCTURE_CHANGE, CAMPAIGN_UPDATE
  - Priority: LOW, MEDIUM, HIGH, URGENT based on change severity
  - Publish `alert.created` event
- `get_alerts` — retrieve alerts for an entity/campaign
- `acknowledge_alert` — mark alert as acknowledged

---

## 4. Monitoring Loop

```
1. SubscriptionService has N active subscriptions
2. MonitoringEngine.run_check():
   a. For each subscription:
      i. ChangeDetector detects changes since last check
      ii. If changes: AlertEngine evaluates changes
      iii. If alert-worthy: create alert, publish event
   b. Record check timestamp
3. Repeat (scheduled or triggered)
```

---

## 5. Acceptance Criteria

1. Subscriptions can be created, listed, and removed
2. Change detector correctly identifies entity changes
3. Change detector correctly identifies campaign changes
4. Monitoring engine evaluates all subscriptions
5. Alert engine generates correct alert types and priorities
6. Risk escalation triggers HIGH/URGENT alert
7. New reports trigger MEDIUM alert
8. Infrastructure changes trigger MEDIUM alert
9. Campaign status change triggers alert
10. Alerts can be acknowledged
11. Events are published for all alerts

---

## 6. Test Plan

- Unit: SubscriptionService (subscribe, unsubscribe, list)
- Unit: ChangeDetector (entity changes, campaign changes)
- Unit: MonitoringEngine (run_check, evaluate)
- Unit: AlertEngine (evaluate_changes, acknowledge)
- Integration: full monitoring loop

---

## 7. Dependencies

- Module 03 (Core Data Model) — entities, reports, campaigns
- Module 05 (Event Bus) — event publishing
- Module 15 (Fraud Detection) — risk scores
- Module 16 (Campaign Engine) — campaign data
