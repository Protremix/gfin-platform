# GFIN GPT Brain Architecture

## Overview

The GPT Brain is the central AI reasoning brain of the GFIN platform. It orchestrates all GFIN modules through a controlled, secure tool interface.

## Architecture

```
                    GPT BRAIN
                        |
                  ORCHESTRATOR
                        |
        +---------------+----------------+
        |               |                |
     MEMORY          POLICIES          TOOLS
        |                                |
        |                +---------------+
        |                |               |
     CASES            SEARCH           GRAPH         EVIDENCE
     TIMELINE         DOMAIN           CRYPTO        CAMPAIGN
     KNOWLEDGE        PHONE            GEOINT        TEMPORAL
                      EMAIL             ALERTS        REPORTS
```

## Components

### Brain Orchestrator (`services/brain/orchestrator.py`)
Central investigation lifecycle management and control loop.

### Context Engine (`services/brain/context.py`)
Selects minimum relevant information for GPT decisions.

### Decision Engine (`services/brain/decision.py`)
Records structured decision metadata (not chain-of-thought).

### Tool Router (`services/brain/tool_router.py`)
Validates, authorizes, and executes tool calls through the full pipeline.

### State Manager (`services/brain/state.py`)
Manages investigation state with 10 states, persists across restarts.

### Conflict Resolver (`services/brain/conflict.py`)
Resolves disagreements between modules, never silently chooses.

### Brain Health (`services/brain/health.py`)
Health checks for all 8 mandatory components.

### Tool Registry (`packages/brain/tool_registry.py`)
Central registry of 30+ tools across 8 categories.

## Tool-Call Pipeline

```
GPT DECISION -> TOOL_VALIDATION -> AUTHORIZATION -> CLASSIFICATION_CHECK ->
JURISDICTION_CHECK -> RATE_LIMIT -> TOOL_EXECUTION -> OUTPUT_VALIDATION ->
EVIDENCE_PROVENANCE -> AUDIT -> RETURN_TO_GPT
```

## Security Hierarchy

```
SYSTEM SECURITY > LEGAL/SOURCE POLICY > ACCESS CONTROL > CLASSIFICATION >
JURISDICTION > CASE PERMISSIONS > BRAIN > GPT
```

## Human-in-the-Loop Modes

- **ASSISTED**: GPT proposes, investigator approves
- **SUPERVISED**: Low-risk automatic, high-risk requires approval
- **AUTONOMOUS**: Authorized workflows run automatically

## Investigation States

CASE_CREATED -> SIGNAL_VALIDATED -> DISCOVERY -> ENRICHMENT -> CORRELATION ->
EVIDENCE_REVIEW -> INVESTIGATOR_REVIEW -> MONITORING -> REPORTING -> CLOSED

Version: 1.0.0
