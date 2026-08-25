# GFIN Module 05 — Event Bus

**Status:** ACCEPTED (Layer A)
**Start Date:** 2026-08-25
**Accept Date:** 2026-08-26
**Accepted By:** GPT Luna (GFIN-CEA)
**Verification:** GPT-5.6-LUNA verified all Layer A deliverables with evidence. Initial strict evaluation flagged Kafka requirements; clarified under two-layer strategy and accepted consistent with Modules 01-04. Final verdict: ACCEPTED (Layer A), Layer B REQUIRES EXTERNAL INFRASTRUCTURE.

---

## Acceptance Criteria

Per Master Spec §9 and Module 05:

| # | Criterion | Layer | Status | Evidence |
|---|-----------|-------|--------|----------|
| 1 | Kafka topic definitions (14 topics) | A | VERIFIED | 14 TopicDefinition objects with partitions, retention, replication, DLQ |
| 2 | Event schemas | A | VERIFIED | SCHEMA_REGISTRY with all 14 topics, validate_event() |
| 3 | Producers | A | VERIFIED | EventProducer adapter with classification/correlation support |
| 4 | Consumers | A | VERIFIED | EventConsumer adapter with subscribe/unsubscribe_all |
| 5 | Retry with backoff | A | VERIFIED | RetryPolicy (max_attempts=3, exponential backoff, capped) |
| 6 | Dead-letter queue | A | VERIFIED | DLQEntry with traceback, filter by topic, replay |
| 7 | Events survive restarts | B | REQUIRES EXTERNAL INFRASTRUCTURE | Kafka durability (Layer B) |
| 8 | Processed reliably | A+B | VERIFIED (A) / REQUIRES EXTERNAL (B) | Retry+DLQ in Layer A; Kafka consumer groups in Layer B |
| 9 | Kafka broker provisioning | B | REQUIRES EXTERNAL INFRASTRUCTURE | Factory raises NotImplementedError |

---

## Implementation

### Files

| File | Lines | Description |
|------|-------|-------------|
| `packages/common/event_bus.py` | 676 | Topics, event envelope, schema validation, bus, retry, DLQ, adapters, factory |
| `tests/unit/test_event_bus.py` | 896 | 60 tests across 11 test classes |

### 14 Kafka Topics

| Topic | Partition Key | Retention | DLQ Topic |
|-------|---------------|-----------|-----------|
| entity.created | entity_type | 7d | entity.created.dlq |
| entity.updated | entity_id | 7d | entity.updated.dlq |
| observation.created | entity_id | 14d | observation.created.dlq |
| relationship.created | source_entity_id | 14d | relationship.created.dlq |
| evidence.created | entity_id | 365d | evidence.created.dlq |
| report.created | report_id | 90d | report.created.dlq |
| campaign.created | campaign_id | 90d | campaign.created.dlq |
| campaign.updated | campaign_id | 90d | campaign.updated.dlq |
| infrastructure.changed | entity_id | 14d | infrastructure.changed.dlq |
| risk.changed | entity_id | 7d | risk.changed.dlq |
| alert.created | alert_id | 90d | alert.created.dlq |
| police.match | entity_id | 180d | police.match.dlq |
| police.request | request_id | 180d | police.request.dlq |
| audit.event | actor_id | 365d | audit.event.dlq |

### Event Envelope

All 9 required fields per Master Spec §9:
- event_id, event_type, schema_version, timestamp, source, entity_refs, classification, correlation_id, payload

### Components

- **TopicDefinition**: version-controlled topic contracts (name, partitions, retention, replication, DLQ)
- **Event**: canonical envelope with ClassificationLevel (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
- **EventSchema + SCHEMA_REGISTRY**: validation for all 14 topics with required/optional fields
- **RetryPolicy**: max_attempts=3, exponential backoff (100ms→5000ms cap, 2x multiplier)
- **DLQEntry**: failed events with failure_reason, attempt_count, timestamps, traceback
- **InMemoryEventBus**: pub/sub, retry, DLQ, replay, metrics, event history
- **EventProducer/EventConsumer**: decoupled adapters
- **create_event_bus()**: factory (memory works, kafka raises NotImplementedError)

---

## Test Results

- **Module 05 tests:** 60 passed in 2.92s
- **Full suite:** 502 passed in 20.31s
- **Failures:** 0

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Topic definitions | 9 | 14 topics, DLQ, retention, partition keys |
| Event envelope | 6 | Required fields, unique IDs, classification, serialization |
| Schema validation | 5 | Valid, missing fields, unknown types, registration |
| Pub/sub | 7 | Publish/receive, sync/async, multiple subscribers, unsubscribe |
| Retry | 3 | Policy defaults, exponential delay, retry on failure, succeed on retry |
| DLQ | 7 | Failed events, filter, timestamps, traceback, replay, ID format |
| Producer/consumer | 4 | Publish, classification, subscribe/unsubscribe, unsubscribe_all |
| Metrics | 4 | Published, consumed, failed, replayed |
| Event history | 2 | Records all, empty initially |
| Factory | 3 | Memory works, Kafka raises, unknown rejected |
| Integration | 3 | Entity lifecycle, multi-service, DLQ+replay workflow |
| Negative | 5 | Invalid rejected, Kafka unavailable, nonexistent, crash, empty |

---

## Layer B — REQUIRES EXTERNAL INFRASTRUCTURE

- Apache Kafka brokers (topic creation, partitioning, replication)
- Durable event persistence across service restarts
- Consumer groups with partition assignment and rebalancing
- Kafka-backed dead-letter topics with offset management
- Event replay from Kafka offsets (not just in-memory DLQ)
- Exactly-once delivery semantics
- Kafka Connect for source/sink connectors
- Kafka Streams for event processing pipelines
- Schema Registry integration (Confluent or equivalent)
- Cross-service event distribution (in-memory bus is process-local only)
- Production monitoring (Kafka metrics, consumer lag, throughput)
- TLS/SSL encryption for event transmission
- ACL-based topic access control

All marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
