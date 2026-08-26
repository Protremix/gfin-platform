# MODULE 26 — Cross-Border Requests

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 26 implements the full Cross-Border Request workflow — the formal
process for requesting intelligence across jurisdictions. Per Architecture
Review §6.3:

```
REQUEST → VALIDATE → AUTHORIZE → DESTINATION → REVIEW → DECISION → AUDIT
```

Per Legal Assumptions: each request records requesting organization,
investigator identity, legal basis, purpose, entity, requested information,
urgency, and case reference.

Per Architecture Review §6.4: each national node controls what data it
shares. The global platform stores only permitted intelligence metadata.

---

## 2. Workflow (Architecture Review §6.3)

1. **REQUEST** — Org A requests intelligence about Entity X from jurisdiction B
2. **VALIDATE** — format, legal basis, purpose validation
3. **AUTHORIZATION** — does Org A have access rights?
4. **DESTINATION** — which jurisdiction holds the requested data?
5. **REVIEW** — Org B (destination) reviews the request
6. **DECISION** — APPROVE (full data), PARTIAL (subset), DENY (with reason)
7. **AUDIT** — full request, decision, and response logged

---

## 3. Architecture — Two Layers

### Layer A (In-Memory MVP)
- `CrossBorderRequestEngine` — orchestrates the full workflow
- `RequestValidator` — validates format, legal basis, purpose
- `RequestAuthorizer` — checks access rights
- `RequestRouter` — routes to destination jurisdiction
- `RequestReviewer` — destination jurisdiction review
- `RequestDecision` — approve/partial/deny with data response
- `RequestAuditTrail` — full audit trail for each request
- `LegalBasis` — legal basis tracking

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Federation protocol over Kafka for inter-jurisdiction communication
- Real legal framework integration per jurisdiction
- Encrypted response transport between nodes
- Per-jurisdiction data residency enforcement

---

## 4. Components

### 4.1 CrossBorderRequestEngine
- `create_request(...)` → CrossBorderRequestRecord (status: SUBMITTED)
- `validate(request_id)` → ValidationResult
- `authorize(request_id)` → AuthorizationResult
- `route(request_id)` → RoutingResult
- `review(request_id, reviewer)` → review record
- `decide(request_id, decision, response_data)` → DecisionResult
- `get_request(request_id)` → full request record with workflow state
- `get_audit_trail(request_id)` → list of audit entries

### 4.2 RequestValidator
- `validate(request)` → ValidationResult
- Checks: format, legal_basis present, purpose stated, entity specified
- Returns: valid bool, errors list

### 4.3 RequestAuthorizer
- `authorize(request)` → AuthorizationResult
- Checks: requesting org exists, has access rights, jurisdiction permitted
- Returns: authorized bool, reason

### 4.4 RequestDecision
- APPROVE — full permitted data returned
- PARTIAL — subset of data returned (with reason)
- DENY — denied with reason

### 4.5 CrossBorderRequestRecord
- id, requesting_org, requesting_jurisdiction, target_jurisdiction
- investigator_name, legal_basis, purpose, case_reference
- entity_id, entity_type, entity_value
- requested_information, urgency
- status: SUBMITTED → VALIDATED → AUTHORIZED → ROUTED → REVIEWING → DECIDED → CLOSED
- decision: NONE, APPROVED, PARTIAL, DENIED
- response_data, denial_reason
- timestamps for each stage

### 4.6 Urgency Levels
- ROUTINE — normal processing
- PRIORITY — elevated priority
- EMERGENCY — urgent, time-sensitive

---

## 5. Acceptance Criteria

1. Request created with all required fields (legal basis, purpose, entity)
2. Validation rejects requests with missing legal basis or purpose
3. Authorization rejects requests from unauthorized organizations
4. Routing identifies the destination jurisdiction
5. Review stage records reviewer and decision
6. APPROVE returns permitted data (policy-filtered)
7. PARTIAL returns subset with explanation
8. DENY returns with reason
9. Every stage transition is audited
10. Full audit trail retrievable per request
11. Urgency levels supported
12. Status transitions are validated (can't skip stages)

---

## 6. Test Plan

- Unit: RequestValidator (valid/invalid requests)
- Unit: RequestAuthorizer (authorized/denied)
- Unit: CrossBorderRequestEngine (full workflow)
- Unit: Status transitions (valid/invalid)
- Unit: Decision types (approve/partial/deny)
- Unit: Audit trail completeness
- Integration: full pipeline from request to response

---

## 7. Dependencies

- Module 23 (Police API) — basic CrossBorderRequest model
- Module 25 (Global Matching) — match results trigger cross-border requests
- Module 03 (Core Data Model) — entity types, classification
