# ADR-004: Evidence-First Intelligence Pipeline

**Date:** 2026-08-26
**Status:** ACCEPTED
**Context:** GFIN processes fraud intelligence from multiple sources (web discovery, infrastructure intelligence, citizen reports, police federation). The Constitution mandates an evidence-first approach: no intelligence is accepted without provenance, source classification, and verifiable chain of custody.

**Decision:** All intelligence flows through a structured pipeline:
```
SOURCE → OBSERVATION → EVIDENCE → ENTITY → RELATIONSHIP → GRAPH → CORRELATION → AI ANALYSIS → CONFIDENCE → HUMAN REVIEW
```

Every observation:
1. Has a Provenance object (source_id, source_type, acquisition_method, retrieval_timestamp, reference)
2. Is linked to an Evidence record in the Evidence Vault (Module 06)
3. Creates or updates Entities through the Core Data Model (Module 03)
4. Establishes typed Relationships with confidence scores
5. Is queryable through the Search Platform (Module 07)
6. Can be traced from final intelligence back to original source

**Rationale:**
- Constitution mandates evidence-first intelligence
- Chain of custody is required for legal/admissible intelligence
- Provenance tracking enables source reliability assessment
- Confidence scoring prevents over-reliance on single sources

**Consequences:**
- All 30+ entity types include provenance fields
- Evidence Vault (Module 06) is a dependency for all intelligence modules
- Web Discovery (Module 08) and Infrastructure Intelligence (Module 09) create observations with evidence links
- No intelligence is stored without provenance — enforced at the schema level
