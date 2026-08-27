# ADR-SOURCE-001: Dynamic API Discovery

## Status: ACCEPTED
## Date: 2026-08-26

## Context
GFIN must not depend on a fixed list of sources. It must continuously discover new APIs, feeds, and providers that can improve investigations.

## Decision
Build an API Discovery Engine that proactively discovers, evaluates, and registers lawful data sources. Sources must pass 12-step validation before integration. All access is policy-controlled.

## Consequences
- Source catalog is dynamic, not hardcoded
- Every source has a quality score (10 dimensions)
- Provider responses are treated as untrusted data
- Credentials never exposed to the Brain
