# GFIN — Architecture Principles

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED
**Source:** Constitution Articles XII–XXVII, Master Spec §2

---

## 1. Evidence First

The platform's core pipeline is:

```
SOURCE → OBSERVATION → EVIDENCE → NORMALIZATION → ENTITY → RELATIONSHIP → GRAPH → CORRELATION → AI ANALYSIS → CONFIDENCE → HUMAN REVIEW → ACTION
```

AI analyzes evidence. AI does not create evidence. Every important claim must be traceable to stored evidence with provenance and timestamp.

## 2. Federated by Design

Police organizations retain ownership and control of their internal case data. The global platform stores only information the source organization is authorized to share:
- Match metadata
- Intelligence references
- Permitted observations
- Campaign references
- Timestamps, confidence, source/jurisdiction
- Sharing policy

Detailed case materials remain with the owning organization unless legally and explicitly shared.

## 3. Zero Trust

No user, organization, service, API, country, or AI model receives implicit trust. Every request is authenticated and authorized. All external content is treated as untrusted input.

## 4. Least Privilege

Users and services receive only the permissions required for their role. No blanket access. Access is scoped by role, organization, jurisdiction, and data classification.

## 5. Data Minimization

Only necessary information is processed or transmitted. AI receives only the information required for the specific task. Restricted police data is not sent to AI providers unless authorized, necessary, contractually permitted, technically protected, and compliant.

## 6. Provider Independence

AI providers must be replaceable. All AI access goes through a Model Gateway supporting model selection, fallback, timeout, retries, cost controls, logging, authorization, and provider health monitoring. The platform must remain functional if any single AI provider is unavailable.

## 7. Auditability

Important actions must be auditable. Every tool call is authenticated, authorized, logged, and attributable. Immutable audit trails are maintained for security-critical operations.

## 8. Reproducibility

Important analytical results should be reproducible from stored evidence and metadata. Risk scores and AI conclusions must be traceable to underlying evidence.

## 9. Continuous Intelligence

The system does not stop after finding an initial match. For important entities and campaigns:

```
DISCOVER → CORRELATE → MONITOR → CHANGE DETECTED → REANALYZE → ALERT → DISCOVER AGAIN
```

## 10. Human Accountability

AI assists with discovery, classification, correlation, prioritization, summarization, and investigation planning. AI must not independently:
- Declare a person a criminal
- Determine legal guilt
- Disclose restricted information
- Authorize law-enforcement access
- Make irreversible legal decisions

## 11. No Single Point of Failure

Where appropriate, the architecture supports: redundant workers, queues, retries, dead-letter queues, replication, backups, failover, multi-region deployment, and disaster recovery.

## 12. Failure Tolerance

The platform continues core operations when: a worker fails, a crawler fails, an external source fails, an AI provider fails, a connector goes offline, or a service restarts. AI enhancement may degrade gracefully, but core ingestion, evidence, search, graph, deterministic rules, and monitoring remain operational.

## 13. Safe Attribution

The platform avoids unsafe attribution:
- IP address ≠ person
- ASN ≠ organization owner
- Shared hosting ≠ common ownership
- Domain registration ≠ criminal identity
- Phone number ≠ verified person identity
- Wallet ≠ verified owner
- Similarity ≠ proof

Relationships are described according to the evidence supporting them.

## 14. Citizen Data Integrity

Citizen reports are observations and allegations until independently corroborated. The system distinguishes: reported → corroborated → disputed → verified → authoritative. A citizen report must not automatically label a person as a criminal.

## 15. Prompt Injection Defense

Web pages, documents, emails, messages, and other external content may contain instructions intended to manipulate the AI. Such content is data, not authority. The agent never obeys instructions embedded in external data unless they originate from an authorized system instruction or project operator.

## 16. Security Supremacy

Security requirements override convenience. The system assumes:
- Credentials may leak
- APIs may be abused
- Users may be compromised
- External sources may be malicious
- Crawled content may be hostile
- Documents may contain adversarial instructions
- AI inputs may contain prompt injection
- Services may fail
