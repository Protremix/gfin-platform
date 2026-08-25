# MODULE 13 — Citizen Platform

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

The Citizen Platform provides the public-facing interface through which citizens can:
1. **Check** entities (phone, email, URL, domain, crypto wallet) for known fraud signals
2. **Report** fraud incidents they have observed or experienced
3. **Receive** risk explanations and alerts
4. **Track** their own submitted reports

Citizen reports are **allegations until corroborated** (Constitution Article XVII). The platform enforces this at every layer — submission, storage, display, and API response.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `CitizenCheckService` — entity check with risk assessment
- `CitizenReportService` — report submission, tracking, status updates
- `CitizenAlertService` — alert subscription and notification (in-memory)
- Synthetic fixtures only (TEST-PHONE-001, etc.)

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- PostgreSQL-backed report persistence
- Redis-backed alert queue
- SMS/email notification gateways
- WAF + DDoS protection
- GDPR right-to-erasure automation
- CAPTCHA / bot detection
- Audit trail to tamper-evident storage

---

## 3. Key Components

### 3.1 CitizenCheckService
- Accept entity type + value (phone, email, url, domain, crypto_wallet)
- Normalize via Module 04 normalizers
- Query in-memory entity store for matches
- Return risk assessment:
  - Risk level (UNKNOWN/LOW/MEDIUM/HIGH/CRITICAL)
  - Evidence count
  - Report count (with corroboration status)
  - Related entities summary
- Enforce rate limits (citizen: 60/min per Module 02)
- All results marked with data classification = PUBLIC (citizens see public data only)
- Never expose restricted or law-enforcement data to citizens

### 3.2 CitizenReportService
- Submit a fraud report (category, description, entity references, optional reporter info)
- Anonymous reporting supported (reporter_id = None)
- Initial status = UNVERIFIED always
- Validate all entity references exist
- Generate evidence provenance (Source: citizen report, classification: COMMUNITY)
- Store report in-memory
- Track report status changes (UNVERIFIED → UNDER_REVIEW → CORROBORATED / DISPUTED / etc.)
- Only the reporter (or admin) can view their own report
- Publish `citizen.report.submitted` event (Module 05 Event Bus)

### 3.3 CitizenAlertService
- Subscribe to alerts for an entity (phone, email, domain, etc.)
- When a matching entity gets new reports/evidence, notify subscriber
- In-memory storage; Layer B uses Redis + notification gateways
- Citizens can unsubscribe at any time
- Alert channels: email (placeholder), SMS (placeholder)
- No alert content reveals restricted data

---

## 4. Security Constraints

1. **Citizens see PUBLIC data only** — enforced by authorization layer
2. **Reports are allegations** — displayed as "Reported" not "Confirmed"
3. **Rate limited** — 60 req/min for citizens (Module 02)
4. **Anonymous reporting** — reporter_id can be None
5. **No bulk data access** — paginated, max 50 results per query
6. **No PII leakage** — citizen data not shared without legal authorization
7. **Input validation** — all inputs sanitized (Module 02 validation)
8. **Audit logged** — all citizen actions logged (Module 02 audit)

---

## 5. Data Flow

```
Citizen Request
      │
      ├─ Check Entity ──→ Normalize ──→ Query ──→ Risk Assessment ──→ Response (PUBLIC only)
      │
      ├─ Submit Report ──→ Validate ──→ Create (UNVERIFIED) ──→ Provenance ──→ Event Bus
      │
      └─ Track Report ──→ Auth Check ──→ Status ──→ Response
```

---

## 6. Acceptance Criteria

1. CitizenCheckService returns risk assessment for known entities
2. CitizenCheckService returns "no known fraud signals" for unknown entities
3. Citizen reports always start as UNVERIFIED
4. Anonymous reports supported (reporter_id = None)
5. Report status transitions follow the defined state machine
6. Invalid status transitions are rejected
7. Citizens can only see their own reports
8. Rate limiting enforced (60/min)
9. No restricted/LE data exposed to citizens
10. Entity references validated before report creation
11. Events published on report submission
12. Alert subscription/unsubscription works
13. Alert notification fires on matching new report
14. All citizen actions audit-logged
15. Input validation on all endpoints

---

## 7. Test Plan

- Unit tests: CitizenCheckService (check, risk, no results, authorization)
- Unit tests: CitizenReportService (submit, track, status, anonymous, validation)
- Unit tests: CitizenAlertService (subscribe, unsubscribe, notify, no-leak)
- Integration: end-to-end check → report → alert flow
- Integration: rate limiting enforcement
- Integration: authorization boundary (citizen vs analyst vs admin)

---

## 8. Dependencies

- Module 02 (Security & Identity) — RBAC, rate limiting, validation, audit
- Module 03 (Core Data Model) — BaseEntity, ReportEntity, entities
- Module 04 (Entity Resolution) — normalizers
- Module 05 (Event Bus) — event publishing
- Module 07 (Search Platform) — entity search
