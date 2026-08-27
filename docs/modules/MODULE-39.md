# Module 39: Scaling & Optimization

**Document ID:** MODULE-39  
**Directive:** Luna Strategic Directive — Step 4: Layer A Optimization  
**Status:** IN PROGRESS  
**Date:** 2026-08-26  

---

## 1. Purpose

Establish reproducible Layer A performance baselines, identify bottlenecks, define performance budgets, add regression benchmarks to CI, and document which scaling questions cannot be answered without Layer B infrastructure.

**Layer A is in-memory only.** No production-scale claims are made from these results. The purpose is to validate algorithmic correctness and identify optimization opportunities before they become production blockers.

---

## 2. Performance Baselines

### 2.1 Baseline Methodology

All baselines are recorded using `packages/observability/baseline_metrics.py` which records:
- Operation count
- Total elapsed time
- Min, max, mean, p50, p95, p99 latency
- Throughput (ops/s)
- SLO threshold check

### 2.2 Baseline Operations

| Operation | Module | Current SLO | Test Volume | Metric |
|-----------|--------|-------------|-------------|--------|
| Entity create | 03 | < 10ms p99 | 10,000 | Latency |
| Entity resolve | 04 | < 100ms p99 | 1,000 pairs | Latency |
| Graph query (1-hop) | 06 | < 50ms p99 | 1,000 nodes | Latency |
| Graph query (2-hop) | 06 | < 200ms p99 | 1,000 nodes | Latency |
| Evidence create | 07 | < 50ms p99 | 1,000 items | Latency |
| Search query | 13 | < 300ms p99 | 10,000 docs | Latency |
| Event publish | 05 | < 5ms p99 | 10,000 events | Latency |
| Cache get | 15 | < 1ms p99 | 10,000 entries | Latency |
| AI gateway call | 19 | < 2000ms p99 | 100 calls | Latency |
| Fraud report triage | 14 | < 500ms p99 | 1,000 reports | Latency |
| Campaign detection | 16 | < 1000ms p99 | 100 campaigns | Latency |
| Alert dispatch | 18 | < 100ms p99 | 1,000 alerts | Latency |

### 2.3 Capacity Tests

| Component | Test | Volume | Pass Criterion |
|-----------|------|--------|----------------|
| Entity repository | Bulk create | 50,000 records | Completes < 10s |
| Graph engine | Large graph | 5,000 nodes + 25,000 edges | Query < 500ms |
| Event bus | High throughput | 100,000 events | Completes < 30s |
| Search index | Bulk indexing | 50,000 documents | Index < 15s |
| Evidence vault | Bulk storage | 5,000 items | Store < 10s |
| Cache | High cardinality | 50,000 entries | Get < 2ms |
| Audit log | Append-only growth | 10,000 entries | Query < 100ms |
| Fraud reports | Bulk triage | 10,000 reports | Triage < 30s |

---

## 3. Performance Budgets

### 3.1 Layer A Budgets

| Operation | Budget (p99) | Current | Status |
|-----------|-------------|---------|--------|
| Entity create | 10ms | TBD | TO MEASURE |
| Entity resolve | 100ms | TBD | TO MEASURE |
| Graph 1-hop | 50ms | TBD | TO MEASURE |
| Graph 2-hop | 200ms | TBD | TO MEASURE |
| Evidence create | 50ms | TBD | TO MEASURE |
| Search | 300ms | TBD | TO MEASURE |
| Event publish | 5ms | TBD | TO MEASURE |
| Cache get | 1ms | TBD | TO MEASURE |
| Report triage | 500ms | TBD | TO MEASURE |
| Campaign detect | 1000ms | TBD | TO MEASURE |
| Alert dispatch | 100ms | TBD | TO MEASURE |

### 3.2 Layer B Budgets (Production Targets)

| Operation | Budget (p99) | Justification |
|-----------|-------------|---------------|
| Entity create | 50ms | DB write + index update |
| Entity resolve | 200ms | DB read + graph query |
| Graph 1-hop | 100ms | Neo4j traversal |
| Graph 2-hop | 500ms | Neo4j multi-hop |
| Evidence create | 100ms | S3 write + DB record |
| Search | 500ms | OpenSearch query |
| Event publish | 10ms | Kafka produce |
| Cache get | 5ms | Redis GET |
| Report triage | 1000ms | AI gateway + enrichment |
| Campaign detect | 2000ms | Graph + scoring |
| Alert dispatch | 200ms | Kafka + notification |

---

## 4. Regression Benchmarks

### 4.1 CI Integration

Regression benchmarks run on every PR and merge to main:

```yaml
# .github/workflows/regression-benchmarks.yml (PLANNED)
benchmarks:
  - name: entity-operations
    operations: [create, resolve, merge, search]
    iterations: 1000
    threshold_p99: 50ms
  - name: graph-operations
    operations: [1-hop, 2-hop, neighbors, path]
    iterations: 500
    threshold_p99: 200ms
  - name: event-bus
    operations: [publish, subscribe, replay]
    iterations: 5000
    threshold_p99: 10ms
  - name: evidence-vault
    operations: [create, verify, retrieve]
    iterations: 500
    threshold_p99: 50ms
  - name: search
    operations: [exact, fuzzy, graph-assisted]
    iterations: 1000
    threshold_p99: 300ms
  - name: cache
    operations: [get, set, evict]
    iterations: 10000
    threshold_p99: 2ms
```

### 4.2 Benchmark Test File

A benchmark test file will be created at `tests/benchmark/` with:

- `test_entity_benchmarks.py` — Entity CRUD + resolution timing
- `test_graph_benchmarks.py` — Graph query timing at scale
- `test_event_benchmarks.py` — Event bus throughput + latency
- `test_evidence_benchmarks.py` — Evidence vault operations
- `test_search_benchmarks.py` — Search query performance
- `test_cache_benchmarks.py` — Cache hit/miss/eviction

Each benchmark:
1. Sets up a known dataset
2. Runs operations for N iterations
3. Records p50, p95, p99
4. Asserts p99 is within budget
5. Outputs results in machine-readable format (JSON)

---

## 5. Optimization Targets

### 5.1 Known Bottlenecks (Layer A)

| Bottleneck | Module | Impact | Optimization |
|------------|--------|--------|-------------|
| In-memory search is O(n) scan | 13 | Slow at >10k docs | Inverted index or transition to OpenSearch |
| Graph adjacency list is Python dict | 06 | Memory-heavy | Use compact representation or Neo4j |
| Event bus subscribers are synchronous | 05 | Slow consumer blocks | Async dispatch with backpressure |
| Entity resolution is O(n²) compare | 04 | Slow at >1k entities | Blocking index / LSH for candidates |
| Cache has no size limit | 15 | Unbounded memory | LRU with max size (implemented) |
| Audit log query is O(n) scan | 01 | Slow at >10k entries | Index by user_id, event_type, timestamp |

### 5.2 Optimization Opportunities

| Opportunity | Module | Expected Gain | Effort |
|------------|--------|--------------|--------|
| Inverted index for search | 13 | 10x search speedup | Medium |
| Async event dispatch | 05 | 5x throughput | Low |
| LSH for entity resolution | 04 | 10x resolution speedup | Medium |
| Audit log time-index | 01 | 5x query speedup | Low |
| Batch entity creates | 03 | 3x bulk insert | Low |
| Graph neighbor cache | 06 | 2x query speedup | Low |

---

## 6. Scaling Questions Requiring Layer B

The following questions CANNOT be answered with Layer A testing:

| Question | Why Layer A Can't Answer | What's Needed |
|----------|------------------------|---------------|
| What's the max throughput with real Kafka? | In-memory pub/sub has no network/disk overhead | Strimzi Kafka cluster |
| How does the system scale horizontally? | In-memory = single process | K8s + multiple replicas |
| What's the real Neo4j query latency? | In-memory adjacency list ≠ Cypher engine | Neo4j 5.x deployment |
| How does OpenSearch handle 10M+ documents? | In-memory index is limited by RAM | OpenSearch cluster |
| What's the real PostgreSQL write throughput? | In-memory dict has no WAL/FSync overhead | PostgreSQL 16 + pgBackRest |
| How does the system handle network partitions? | No network in-memory | Multi-node K8s + network policies |
| What's the real AI gateway latency? | Mock gateway returns instantly | OpenAI API + network |
| How does Redis cache behave under contention? | In-memory dict has no I/O contention | Redis cluster |
| What's the DR RTO/RPO with real infrastructure? | No persistence to recover | PostgreSQL WAL + S3 backup |
| How does federation handle mTLS + latency? | In-memory, no network | Federation service + mTLS certs |

---

## 7. Deliverables

| Deliverable | Status |
|-------------|--------|
| Performance baseline recording | IN PROGRESS |
| Capacity test suite | IN PROGRESS |
| Performance budget definitions | COMPLETE (§3) |
| Regression benchmark plan | COMPLETE (§4) |
| Benchmark test files | TO CREATE |
| Bottleneck analysis | COMPLETE (§5.1) |
| Optimization recommendations | COMPLETE (§5.2) |
| Layer B scaling questions documented | COMPLETE (§6) |

---

## 8. Acceptance Criteria

Module 39 is ACCEPTED when:

1. [ ] Performance baselines recorded for all 12 operations
2. [ ] Capacity tests pass for all 8 components
3. [ ] Performance budgets defined (Layer A + Layer B)
4. [ ] Regression benchmark tests created and passing
5. [ ] Benchmark results within budget or documented exceptions
6. [ ] Bottleneck analysis complete with optimization recommendations
7. [ ] Layer B scaling questions documented
8. [ ] No production-scale claims from Layer A results

**Status: IN PROGRESS — Benchmark tests to be created next.**
