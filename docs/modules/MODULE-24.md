# MODULE 24 — Police Connector SDK

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 24 implements the Police Connector SDK — the interface that police
organizations implement to connect their national systems to GFIN. Per
Architecture Review §8.3, the connector SDK provides a standardized interface
for authentication, synchronization, observation submission, match reception,
alert handling, and cross-border request management.

Per Constitution: police data is federated — no full database uploads.
Per Threat Model: connector credentials are HIGHLY_RESTRICTED (Level 5).

---

## 2. Connector Interface (Architecture Review §8.3)

```
authenticate()         — Authenticate with GFIN
synchronize()         — Sync local data with GFIN
submit_observation()  — Submit an observation to GFIN
receive_match()       — Receive a match notification
receive_alert()       — Receive an alert notification
handle_request()      — Handle a cross-border request
acknowledge()         — Acknowledge receipt of data
retry()               — Retry failed operations
```

---

## 3. Architecture — Two Layers

### Layer A (In-Memory MVP — Sandbox)
- `PoliceConnectorInterface` — abstract base class (ABC) with 8 methods
- `MockPoliceConnector` — reference implementation with test data
- `ConnectorRegistry` — manages registered connectors by org_id
- `ConnectorCredential` — credential management (stored securely, never logged)
- `SyncResult` — synchronization result record
- `ConnectorEvent` — event types (MATCH, ALERT, REQUEST, SYNC)
- `ConnectorConfig` — configuration for a connector

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Real connectors implementing the interface for national police systems
- mTLS transport for connector-to-GFIN communication
- Credential vault (HashiCorp Vault or equivalent)
- Real-time WebSocket event streaming
- Delta sync with conflict resolution

---

## 4. Key Components

### 4.1 PoliceConnectorInterface (ABC)
- `authenticate(credentials) → bool`
- `synchronize(direction) → SyncResult`
- `submit_observation(observation) → str` (observation ID)
- `receive_match(match_data) → str` (acknowledgment ID)
- `receive_alert(alert_data) → str` (acknowledgment ID)
- `handle_request(request_data) → str` (response ID)
- `acknowledge(event_id) → bool`
- `retry(operation, params) → Any`

### 4.2 MockPoliceConnector
- Implements all 8 interface methods
- Uses in-memory test data
- Simulates national system behavior
- For development/testing only

### 4.3 ConnectorRegistry
- `register(connector)` — register a connector
- `unregister(org_id)` — unregister
- `get_connector(org_id)` → PoliceConnectorInterface
- `list_connectors()` → list of registered connectors
- Connection status tracking

### 4.4 ConnectorCredential
- `org_id`, `api_key`, `mtls_cert` (Layer B)
- Credentials stored encrypted, never logged in plaintext
- Rotation support

### 4.5 SyncResult
- `direction` (PUSH/PULL/BIDIRECTIONAL)
- `records_pushed`, `records_pulled`
- `conflicts` list
- `status` (SUCCESS/PARTIAL/FAILED)
- `timestamp`

---

## 5. Acceptance Criteria

1. PoliceConnectorInterface defines all 8 methods as abstract
2. MockPoliceConnector implements all 8 methods
3. ConnectorRegistry registers and manages connectors
4. authenticate() validates credentials and sets connection status
5. synchronize() returns a SyncResult with push/pull counts
6. submit_observation() returns an observation ID
7. receive_match() and receive_alert() return acknowledgment IDs
8. handle_request() processes cross-border requests
9. acknowledge() confirms receipt of events
10. retry() re-executes failed operations

---

## 6. Test Plan

- Unit: PoliceConnectorInterface (abstract methods)
- Unit: MockPoliceConnector (all 8 methods)
- Unit: ConnectorRegistry (register, unregister, get, list)
- Unit: ConnectorCredential (storage, rotation, no plaintext logging)
- Unit: SyncResult (fields, status)
- Integration: full connector lifecycle (register → auth → sync → observe → match → alert → request → acknowledge)

---

## 7. Dependencies

- Module 23 (Police API) — the API the connector connects to
- Module 01 (Governance) — audit logging
- Module 03 (Core Data Model) — entity types
