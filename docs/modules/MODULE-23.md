# MODULE 23 — Police API

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 23 implements the Police API — the controlled interface through which
law enforcement agencies access GFIN intelligence. Per the Constitution and
Architecture Review §8:

- Police data is federated — no full database uploads
- Every police API request is authenticated, authorized, audited, and rate-limited
- Data classification enforced (LAW_ENFORCEMENT data stays on local AI)
- Cross-border requests go through a formal authorization workflow

### Endpoints (Architecture Review §8.1):
```
POST /v1/police/match         — Match entity
POST /v1/police/observation   — Submit observation
GET  /v1/police/entity/{id}   — Get entity intelligence
GET  /v1/police/campaign/{id}  — Get campaign intelligence
POST /v1/police/monitor       — Subscribe to entity
GET  /v1/police/alerts        — Get alerts
POST /v1/police/request       — Cross-border request
GET  /v1/police/request/{id}  — Get request status
```

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `PoliceAPI` — in-memory API service (no HTTP server, direct calls)
- `PoliceAuth` — authentication and authorization
- `PoliceEndpoint` — endpoint handlers for each operation
- `PoliceAuditLog` — immutable audit trail for all police access
- `PoliceRateLimiter` — per-organization rate limiting
- `MatchResult` — entity match response
- `ObservationRecord` — police-submitted observation
- `CrossBorderRequest` — cross-border information request

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- FastAPI HTTP endpoints with mTLS
- OIDC/OAuth2 authentication for police users
- PostgreSQL-backed audit trail (immutable, WORM)
- Redis-backed rate limiting
- Real entity matching against production database
- Federation protocol implementation

---

## 3. Key Components

### 3.1 PoliceAuth
- `authenticate(api_key)` → PoliceSession | None
- `authorize(session, endpoint)` → bool
- Roles: POLICE_OFFICER, POLICE_SUPERVISOR, POLICE_ADMIN
- ABAC: jurisdiction + classification checked
- Sessions have expiry and scope

### 3.2 PoliceAPI (main service)
- `match_entity(entity_type, entity_value, jurisdiction)` → MatchResult
- `submit_observation(observation)` → ObservationRecord
- `get_entity_intel(entity_id, session)` → EntityIntel
- `get_campaign_intel(campaign_id, session)` → CampaignIntel
- `subscribe_monitor(entity_id, session)` → Subscription
- `get_alerts(session)` → list[Alert]
- `create_cross_border_request(request, session)` → CrossBorderRequest
- `get_request_status(request_id, session)` → RequestStatus

### 3.3 PoliceAuditLog
- `log(session, endpoint, params, result)` → audit entry
- Every request logged: user, org, jurisdiction, endpoint, timestamp, result
- Immutable — entries cannot be deleted or modified
- `query(filter)` → list of audit entries

### 3.4 PoliceRateLimiter
- `check_limit(org_id, endpoint)` → bool
- Per-organization quotas (e.g., 1000 req/hour)
- Per-endpoint limits (e.g., match: 100/hour, observation: 500/hour)

### 3.5 CrossBorderRequest
- Status workflow: PENDING → REVIEW → APPROVED/DENIED → EXECUTED → CLOSED
- `create()` → PENDING
- `review()` → REVIEW
- `approve()` / `deny()` → APPROVED / DENIED
- `execute()` → EXECUTED
- `close()` → CLOSED

---

## 4. Data Model — What Is Shared (Architecture Review §8.4)

### PERMITTED (crosses federation boundary):
- ENTITY_ID, ENTITY_TYPE, JURISDICTION, ORGANIZATION
- INTELLIGENCE_TYPE, FIRST_SEEN, LAST_SEEN, CONFIDENCE
- RELATED_CAMPAIGN, ACCESS_LEVEL

### DOES NOT CROSS:
- Case files, suspect names (without authorization)
- Raw citizen reports (without authorization)
- Internal investigation notes

---

## 5. Acceptance Criteria

1. PoliceAuth authenticates API keys and creates sessions
2. PoliceAuth authorizes by role and jurisdiction (ABAC)
3. PoliceAPI match_entity returns match results
4. PoliceAPI submit_observation records police observations
5. PoliceAPI get_entity_intel returns entity intelligence (filtered by clearance)
6. Cross-border requests follow PENDING → REVIEW → APPROVED/DENIED workflow
7. Every API call is logged in the audit trail (immutable)
8. Rate limiting enforces per-organization quotas
9. Unauthorized requests are rejected with appropriate errors
10. Sessions expire and enforce scope

---

## 6. Test Plan

- Unit: PoliceAuth (authenticate, authorize, session expiry, ABAC)
- Unit: PoliceAPI (all 8 endpoints)
- Unit: PoliceAuditLog (log, query, immutability)
- Unit: PoliceRateLimiter (check, enforce, reset)
- Unit: CrossBorderRequest (status workflow)
- Integration: full API pipeline from auth to response

---

## 7. Dependencies

- Module 01 (Governance) — audit logging infrastructure
- Module 03 (Core Data Model) — entity types, classification
- Module 16 (Campaign Engine) — campaign data for get_campaign_intel
- Module 17 (Continuous Monitoring) — subscriptions, alerts
