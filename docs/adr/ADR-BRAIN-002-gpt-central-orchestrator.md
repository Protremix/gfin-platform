# ADR-BRAIN-002: GPT as Central Orchestrator

## Status
ACCEPTED

## Date
2026-08-26

## Context
GFIN needs a central reasoning brain to coordinate investigations across 40+ specialized modules. GPT (via Model Gateway) was selected as the reasoning engine.

## Decision
GPT serves as the central AI reasoning brain. All modules operate as controlled tools through a registered, permission-checked tool registry. GPT never directly accesses databases or infrastructure.

## Consequences
- All module access is mediated through the Tool Registry
- Provider independence maintained through Model Gateway
- Security hierarchy enforces system security > brain > GPT
- Brain state persists across restarts
- Model can be replaced without architecture changes
