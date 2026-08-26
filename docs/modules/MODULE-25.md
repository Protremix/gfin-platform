# MODULE 25 — Global Matching

**Status:** IN_PROGRESS
**Started:** 2026-08-26
**Spec by:** GPT Luna (GFIN-CEA)

---

## 1. Purpose

Module 25 implements the Global Match Engine — the component in the Global
Control Plane that checks entities against the Global Entity Index for
international/cross-border matches. Per Architecture Review §6.1, the Match
Engine sits above the Federation Boundary and returns only permitted
intelligence metadata.

Per Terminology: "Global Match = A permitted intelligence reference indicating
that an entity has been observed elsewhere. Does NOT mean guilt, ownership,
criminal identity, or disclosure of another country's case."

Per Directive §12: "Match ≠ Guilt — A global match means observed elsewhere,
not criminal identity."

---

## 2. Architecture

```
                    GLOBAL CONTROL PLANE
                          │
            ┌─────────────┼─────────────┐
            │             │             │
     ┌──────┴──────┐ ┌───┴─────┐ ┌─────┴────┐
     │ GLOBAL      │ │ GLOBAL  │ │ GLOBAL   │
     │ ENTITY INDEX│ │ EVENT   │ │ MATCH    │
     │             │ │ BUS     │ │ ENGINE   │
     └──────┬──────┘ └────┬────┘ └────┬─────┘
            │             │             │
════════════╪═════════════╪═════════════╪══════════
  FEDERATION BOUNDARY
════════════╪═════════════╪═════════════╪══════════
```

### Layer A (In-Memory MVP)
- GlobalMatchEngine — match entities against the global index
- GlobalEntityIndex — in-memory index of entities by jurisdiction
- MatchPolicy — what data is permitted to cross federation boundary
- MatchNotification — notify police connectors of matches

### Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE)
- Distributed global index (Elasticsearch/OpenSearch cluster)
- Real-time match streaming via Kafka
- Cross-datacenter replication
- ML-based entity matching with fuzzy matching

---

## 3. Key Principles

1. **Match ≠ Guilt** — a match means "observed elsewhere", not criminal identity
2. **Permitted metadata only** — only entity_id, type, jurisdiction, confidence, first/last seen
3. **No case details cross** — suspect names, case files, investigation notes stay local
4. **Federation boundary enforcement** — data classification checked at boundary
5. **Every match is logged** — audit trail for all match queries and results

---

## 4. Components

### 4.1 GlobalEntityIndex
- `register_entity(entity)` — add/update entity in global index
- `lookup(entity_type, entity_value)` → list of matches across jurisdictions
- `remove_entity(entity_id)` — remove from index
- `get_entity(entity_id)` → entity record
- `stats` — entity count, by type, by jurisdiction

### 4.2 GlobalMatchEngine
- `match(entity_type, entity_value, requesting_jurisdiction)` → MatchResult
- `match_batch(entities)` → list[MatchResult]
- `notify_connector(org_id, match)` — send match notification to police connector
- `set_policy(policy)` — set matching policy

### 4.3 MatchPolicy
- `is_permitted(field_name)` → bool — check if a field can cross boundary
- `filter_match_data(data)` → filtered data with only permitted fields
- Permitted: entity_id, entity_type, jurisdiction, confidence, first_seen, last_seen
- Not permitted: suspect_names, case_files, investigation_notes, raw_reports

### 4.4 MatchResult
- entity_id, entity_type, entity_value
- matched: bool
- matches: list of match entries (jurisdiction, confidence, first_seen, last_seen)
- requesting_jurisdiction
- policy_filtered: bool

### 4.5 MatchNotification
- notification_id, org_id, entity_id, match_data
- status: PENDING, SENT, ACKNOWLEDGED
- timestamp

---

## 5. Acceptance Criteria

1. GlobalEntityIndex stores entities by type and value across jurisdictions
2. GlobalMatchEngine matches entities and returns results
3. MatchPolicy filters out non-permitted fields at federation boundary
4. Match results contain only permitted intelligence metadata
5. Match ≠ Guilt principle enforced (no suspect names, case files)
6. Match notifications sent to appropriate police connectors
7. Every match query is logged for audit
8. Batch matching supported
9. Self-jurisdiction matches are excluded (don't match own data)
10. Entity removal from index works

---

## 6. Test Plan

- Unit: GlobalEntityIndex (register, lookup, remove, stats)
- Unit: GlobalMatchEngine (match, match_batch, notify)
- Unit: MatchPolicy (is_permitted, filter_match_data)
- Unit: MatchResult (fields, policy_filtered)
- Unit: MatchNotification (status transitions)
- Integration: full match pipeline from entity registration to notification

---

## 7. Dependencies

- Module 23 (Police API) — match queries from police
- Module 24 (Police Connector SDK) — match notifications to connectors
- Module 03 (Core Data Model) — entity types
