# GFIN — Terminology

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED

---

## Core Concepts

| Term | Definition |
|------|-----------|
| **Entity** | A normalized, resolved object in the intelligence graph (e.g., a phone number, domain, IP address, crypto wallet). Has a stable global ID (e.g., `ENT-7F82A91`). |
| **Observation** | A single recorded sighting of an entity from a specific source at a specific time. Distinct from the entity itself. An entity may have many observations. |
| **Evidence** | Stored, verifiable artifact that supports a claim or observation. Has content hash, provenance, and chain of custody. |
| **Relationship** | A typed, provenance-bearing connection between two entities (e.g., `RESOLVES_TO`, `HOSTED_ON`). |
| **Source** | An origin of data — citizen report, web crawl, permitted public source, law-enforcement intelligence, licensed feed. Every source has identity, method, classification, and reliability assessment. |
| **Provenance** | The complete traceable origin of a piece of data: where it came from, how it was acquired, when, by whom, and under what terms. |
| **Normalization** | The process of converting diverse raw representations (e.g., `+34 612 345 678`, `0034 612 345 678`) into a single canonical form while preserving the original. |
| **Entity Resolution** | The process of determining whether two observations refer to the same entity, including matching, deduplication, confidence scoring, and merge/split workflows. |
| **Campaign** | A set of correlated entities, observations, and infrastructure indicators that together suggest a coordinated fraud operation. Probabilistic unless supported by authoritative evidence. |
| **Global Match** | A permitted intelligence reference indicating that an entity has been observed elsewhere. Does NOT mean guilt, ownership, criminal identity, or disclosure of another country's case. |
| **Intelligence Graph** | The global graph of entities, relationships, observations, and evidence that the platform continuously builds and maintains. |

## Data Classifications

| Classification | Meaning |
|---------------|---------|
| **PUBLIC** | Freely available public information |
| **COMMUNITY** | Shared within the GFIN community (citizen reports, aggregated intelligence) |
| **RESTRICTED** | Limited access — authorized investigators and analysts only |
| **LAW_ENFORCEMENT** | Police and authorized law-enforcement organizations only |
| **HIGHLY_RESTRICTED** | Highest sensitivity — case-specific, explicitly authorized access only |

## Report States

| State | Meaning |
|-------|---------|
| **UNVERIFIED** | Submitted but not yet reviewed |
| **UNDER_REVIEW** | Actively being assessed |
| **CORROBORATED** | Supported by independent evidence |
| **DISPUTED** | Contradicted by other evidence |
| **FALSE_POSITIVE** | Determined to be incorrect |
| **VERIFIED** | Confirmed through multiple independent sources |
| **OFFICIALLY_ESTABLISHED** | Supported by authoritative evidence (e.g., law enforcement, court) |

## Risk Levels

| Level | Meaning |
|-------|---------|
| **UNKNOWN** | Insufficient evidence to assess |
| **LOW** | Minimal indicators of fraud |
| **MEDIUM** | Some indicators present, warrants caution |
| **HIGH** | Strong indicators of fraud |
| **CRITICAL** | Multiple strong indicators + active campaign correlation |

## Module States

| State | Meaning |
|-------|---------|
| **NOT_STARTED** | Not yet begun |
| **PLANNED** | Specification complete, implementation not started |
| **IN_PROGRESS** | Active development |
| **TESTING** | Implementation complete, tests running |
| **BLOCKED** | Cannot proceed without external input or resolution |
| **ACCEPTED** | All acceptance criteria met with evidence |
| **DEPRECATED** | Superseded or retired |

## Alert Priorities

| Priority | Meaning |
|----------|---------|
| **P0** | Critical — immediate action required |
| **P1** | High — urgent attention needed |
| **P2** | Medium — should be reviewed soon |
| **P3** | Informational — awareness only |

## User Roles

| Role | Description |
|------|-------------|
| **Citizen** | Can check entities, submit reports, receive alerts |
| **Investigator** | Law-enforcement user with global search, graph, campaign, and case tools |
| **Intelligence Analyst** | Campaign discovery, trend analysis, infrastructure monitoring, early warning |
| **Administrator** | Users, organizations, roles, permissions, policies, audit, federation |

## Key Distinctions

- **Entity ≠ Observation** — An entity is the resolved object; an observation is a single sighting of it
- **AI ≠ Authority** — AI may discover, classify, correlate, recommend; it may not independently determine guilt or make legal findings
- **Match ≠ Guilt** — A global match means observed elsewhere, not criminal identity
- **Similarity ≠ Proof** — Similarity between entities is a signal, not evidence of ownership or criminality
- **Report ≠ Fact** — A citizen report is an allegation until corroborated
- **IP ≠ Person** — An IP address does not identify a person
- **Implemented ≠ Tested ≠ Production Ready** — Each has distinct verification requirements
