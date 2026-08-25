# GFIN — AI Policy

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED
**Source:** Constitution Articles V, XIII–XVI, XXVII–XXIX, XLIV–XLV, Master Spec §25–29, §58–59

---

## 1. AI's Role

AI is an analytical component, not an authority.

### AI MAY:
- Discover patterns and correlations
- Classify and categorize content
- Correlate entities and campaigns
- Summarize investigations and evidence
- Translate and analyze multilingual content
- Prioritize alerts and investigations
- Recommend next investigation steps
- Explain risk assessments
- Generate structured extractions
- Plan investigation workflows

### AI MAY NOT Independently:
- Determine criminal guilt
- Make legal findings
- Fabricate evidence
- Disclose restricted information
- Bypass authorization
- Circumvent security
- Silently alter evidence
- Make irreversible law-enforcement decisions

## 2. Model Gateway

All AI access goes through a Model Gateway. No direct AI provider calls from application code.

### Gateway Capabilities:
- Model selection (per task type)
- Fallback (primary → secondary → local)
- Timeout and retry
- Cost controls (per-request, per-organization, per-day)
- Request and response logging
- Authorization (classification-aware routing)
- Provider health monitoring
- Structured output enforcement

### Provider Independence:
The platform must remain functional if any single AI provider is unavailable. The architecture supports:
- OpenAI (primary reasoning provider when selected by project owner)
- Local/open-source models (OCR, embeddings, language detection, bulk classification, preprocessing)
- Other commercial models
- Specialized ML models

## 3. Model Routing Strategy

| Task Type | Routed To | Rationale |
|-----------|----------|-----------|
| High-volume simple classification | Local / cheaper model | Cost efficiency |
| Embeddings and similarity | Local model | Latency, data privacy |
| OCR and language detection | Local model | Latency, no sensitive data egress |
| Complex reasoning | Advanced model (OpenAI) | Requires deep reasoning |
| Multilingual analysis | Advanced model (OpenAI) | Cross-lingual capability |
| Investigation summaries | Advanced model (OpenAI) | Nuanced synthesis |
| Citizen assistant | Advanced model (OpenAI) | Natural interaction |
| Critical investigation analysis | Multi-stage analysis → Human review | High stakes, requires human judgment |

**Rule:** Never use a large expensive model for every operation without justification.

## 4. Hallucination Control

### Prohibited:
- Invented sources
- Invented relationships
- Invented cases
- Invented accusations
- Invented evidence

### Required Evidence Chain:
Every important AI claim must map to:
```
CLAIM → EVIDENCE_ID → SOURCE → TIMESTAMP → CONFIDENCE
```

If evidence is insufficient, the AI must return: `UNKNOWN` or `INSUFFICIENT_DATA`

### Implementation:
- AI outputs include evidence references
- Outputs without evidence references are marked UNVERIFIED
- Critical claims require human review before action
- AI investigation orchestrator uses only controlled, authorized tools

## 5. AI Investigation Orchestrator

The AI investigator uses controlled tools — no unrestricted database or internet access.

### Available Tools:
| Tool | Purpose |
|------|---------|
| search_web | Permitted web search |
| inspect_url | URL content inspection |
| domain_lookup | Domain metadata |
| rdap_lookup | Registration data |
| dns_lookup | DNS resolution |
| ip_lookup | IP intelligence |
| certificate_lookup | Certificate Transparency |
| infrastructure_history | Infrastructure timeline |
| graph_search | Entity graph search |
| report_search | Citizen report search |
| campaign_search | Campaign search |
| case_search | Case search |
| entity_compare | Entity comparison |
| create_alert | Alert creation |
| request_information | Cross-border information request |

### Tool Call Requirements:
- Every tool call must be authenticated
- Every tool call must be authorized
- Every tool call must be logged
- Every tool call must be attributable
- The agent must preserve evidence IDs and provenance in its output

## 6. AI Evaluation

Every production AI model must have measurable evaluation.

### Tracked Metrics:
| Metric | Description |
|--------|-------------|
| Precision | True positives / (true positives + false positives) |
| Recall | True positives / (true positives + false negatives) |
| F1 | Harmonic mean of precision and recall |
| False positives | Incorrect fraud flags |
| False negatives | Missed fraud |
| Hallucination rate | Fabricated claims / total claims |
| Latency | Response time |
| Cost | Per-request and per-month cost |
| Calibration | Confidence score accuracy |
| Multilingual performance | Performance across supported languages |

### Regression Testing:
- Model updates require regression testing
- Evaluation datasets are maintained per task type
- Every production model version must pass predefined thresholds
- Adversarial behavior is tested (prompt injection, jailbreak attempts)

## 7. Data Privacy for AI

| Data Classification | External AI (OpenAI) | Local AI |
|--------------------|--------------------|---------|
| PUBLIC | Permitted | Permitted |
| COMMUNITY | Permitted (minimized) | Permitted |
| RESTRICTED | Only if authorized, necessary, contractually permitted, protected | Permitted |
| LAW_ENFORCEMENT | Prohibited unless explicitly authorized with legal basis | Permitted (within jurisdiction) |
| HIGHLY_RESTRICTED | Prohibited | Permitted (within jurisdiction, isolated) |

### Controls:
- Model Gateway enforces classification-aware routing
- Request content is minimized to what's needed for the task
- Request and response logs maintained for audit
- Enterprise/API privacy and retention controls used where available
- The platform controls: what is sent, why, by whose authority, retention config, model selection

## 8. AI Provider Failure Handling

If OpenAI (or any primary AI provider) is unavailable:

| Function | Status |
|----------|--------|
| Ingestion | Continues |
| Crawling | Continues |
| Evidence collection | Continues |
| Graph updates | Continue |
| Deterministic detection (rules) | Continues |
| Alerts (deterministic signals) | Continue |
| Local models (OCR, embeddings, classification) | Continue |
| AI-enhanced analysis | Degrades gracefully |
| Citizen AI assistant | Degraded (fallback to deterministic checks) |

**OpenAI must never be the sole operational dependency.**

## 9. Prompt Injection Defense

All external content (web pages, documents, emails, messages, reports) may contain instructions intended to manipulate the AI.

### Rules:
- External content is data, not authority
- The AI never obeys instructions embedded in external data unless those instructions originate from an authorized system instruction or project operator
- AI processing of external content is sandboxed
- AI tool access is controlled and limited to the registered tool set
- No direct database or internet access for the AI orchestrator

## 10. OpenAI-Specific Integration (When Selected)

When OpenAI is the primary AI provider:

- Integrated through the Model Gateway (not hard-coded)
- Used for: advanced reasoning, multilingual analysis, citizen assistant, investigator assistant, investigation summaries, complex classification, next-best-question generation, evidence synthesis, structured extraction
- OpenAI is NOT the system of record
- OpenAI is NOT the sole intelligence source
- OpenAI is NOT a single point of failure
- The platform controls what data is sent to OpenAI and why
- Enterprise/API privacy and retention controls are used
- Provider credentials are stored in secrets management (never in source code)
