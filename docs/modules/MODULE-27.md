# MODULE 27 — Police Console

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 27 implements the Police Console backend service — the service layer
that police operators interact with through the Police Console app. Per
Architecture Review §2, the Police Console is one of three apps (alongside
Citizen Web and Citizen Mobile).

The console provides: entity search, investigation workspace, alert
viewing, observation submission, cross-border request management, and
campaign viewing.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP)
- `PoliceConsoleService` — main service with all console operations
- `ConsoleSession` — operator session with role, jurisdiction, permissions
- `ConsoleRole` — OFFICER, SUPERVISOR, ADMIN
- `ConsoleAction` — enum of all console actions
- `ConsoleAuditLogger` — audit trail for console actions
- `InvestigationWorkspace` — workspace for ongoing investigations
- `ConsolePermissions` — role-based action permissions

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- FastAPI REST endpoints for the Police Console app
- WebSocket for real-time alert delivery
- OIDC/OAuth2 authentication
- Frontend SPA (React/Next.js)

---

## 3. Console Operations

1. **search_entity** — Search for entities in the global index
2. **view_entity** — View entity details (policy-filtered)
3. **submit_observation** — Submit an observation about an entity
4. **view_alerts** — View alerts for the operator's jurisdiction
5. **view_campaign** — View campaign details
6. **create_cross_border_request** — Initiate a cross-border request
7. **view_cross_border_requests** — View requests from/to their org
8. **manage_investigation** — Create/update investigation workspaces
9. **view_audit_trail** — View audit trail (supervisor/admin only)

---

## 4. Acceptance Criteria

1. ConsoleSession tracks operator, role, jurisdiction, permissions
2. ConsolePermissions enforce role-based access
3. search_entity returns policy-filtered results
4. view_entity returns only permitted fields
5. submit_observation creates an observation record
6. view_alerts returns alerts for the operator's jurisdiction
7. create_cross_border_request delegates to CrossBorderRequestEngine
8. InvestigationWorkspace tracks entities, notes, and status
9. All actions are audit logged
10. Role enforcement: OFFICER cannot view audit trail, ADMIN can

---

## 5. Dependencies

- Module 23 (Police API) — authentication, match
- Module 25 (Global Matching) — entity search
- Module 26 (Cross-Border Requests) — request workflow
- Module 18 (Alert Engine) — alerts
