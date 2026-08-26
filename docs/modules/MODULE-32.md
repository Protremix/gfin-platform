# MODULE 32 — Federation

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 32 implements the Federation Protocol — the mechanism by which
national GFIN nodes communicate, share permitted intelligence, and
participate in cross-border operations. Per Architecture Review §6:
federation is event-driven, each node controls its data, and the global
platform stores only permitted metadata.

---

## 2. Architecture — Two Layers

### Layer A (In-Memory MVP)
- `FederationNode` — represents a national node (jurisdiction, org, status)
- `FederationNetwork` — manages all nodes, handles node registration/discovery
- `FederationMessage` — message between nodes (match, alert, request, response)
- `FederationProtocol` — message routing, delivery, and acknowledgment
- `NodeStatus` — ONLINE, OFFLINE, DEGRADED
- `FederationAuditLogger` — audit trail for all federation operations

### Layer B (Production)
- Kafka-based federation event streaming
- mTLS between nodes
- Real cross-datacenter replication
- REQUIRES EXTERNAL INFRASTRUCTURE

---

## 3. Acceptance Criteria

1. FederationNode tracks jurisdiction, org, status, and capabilities
2. FederationNetwork manages node registration, removal, and discovery
3. FederationMessage routes between nodes with delivery confirmation
4. Messages can be acknowledged by receiving nodes
5. Node status transitions: ONLINE ↔ OFFLINE ↔ DEGRADED
6. Offline nodes do not receive messages (queued or rejected)
7. All federation operations are audit logged
8. Network topology can be listed

---

## 4. Dependencies

- Module 25 (Global Matching) — match messages
- Module 26 (Cross-Border Requests) — request messages
