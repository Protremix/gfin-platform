# MODULE 37 — Documentation & Training Materials

**Version:** 1.0  
**Status:** ACCEPTED  
**Date:** 2026-08-26  
**Author:** GPT Luna (GFIN-CEA)  

---

## 1. Description

Module 37 establishes the operational, investigative, administrative, developer, and educational documentation suite for the Global Fraud Intelligence Network (GFIN). It serves as the primary knowledge base and enablement framework for operational readiness across all GFIN stakeholders.

The module provides step-by-step procedures, role-based training curriculums, knowledge assessments, and gap analysis against production go/no-go gates to ensure operational self-sufficiency without engineering intervention.

---

## 2. Purpose & Scope

- **Purpose:** Provide comprehensive, actionable documentation and training materials for GFIN operators, fraud investigators, system administrators, and software developers.
- **Scope:** Covers all Layer A (in-memory MVP) workflows and architecture across Modules 00 through 36, while establishing clear migration pathways to Layer B (production infrastructure).
- **Exit Criterion:** An independent operator, investigator, administrator, or developer can execute all documented operational and technical workflows without requiring direct engineering assistance.

---

## 3. Key Components & Artifacts

1. **Module Specification (`docs/modules/MODULE-37.md`):** Formal module specification defining purpose, scope, exit criteria, and verification matrix.
2. **Operator Guide (`docs/training/operator-guide.md`):** System operations, startup/shutdown, entity lifecycle, evidence vault operations, event bus monitoring/DLQ, campaign management, alert routing, and health checks.
3. **Investigator Guide (`docs/training/investigator-guide.md`):** Fraud report intake/triage, graph traversal, chain of custody, 7-stage cross-border requests, crypto tracing, 15 AI investigation orchestrator tools, and STIX 2.1 export.
4. **Administrator Guide (`docs/training/administrator-guide.md`):** RBAC/ABAC policy engine, 9x8 access control matrix, user lifecycle, immutable audit verification, rate limiting, 5 data classification levels, GDPR deletion, key rotation, and backup/restore.
5. **Developer Guide (`docs/training/developer-guide.md`):** Monorepo structure, Layer A vs Layer B paradigms, package dependencies, extending entities/rules/event bus/AI models, testing strategies, CI/CD, and Ruff linting standards.
6. **Training Curriculum (`docs/training/training-curriculum.md`):** 6 runbook-mapped modules, role-based tracks (operator, investigator, administrator, developer), exercises, and qualification sign-off templates.
7. **Knowledge Assessment (`docs/training/knowledge-assessment.md`):** 40 scenario and multiple-choice questions across 4 roles, answer key with rationales, 80% pass criteria, and certification records.
8. **Documentation Gap Report (`docs/training/documentation-gap-report.md`):** Documentation mapping across all 12 production go/no-go gates, gap analysis, and remediation recommendations.

---

## 4. Architecture Strategy

- **Layer A (In-Memory MVP):** FULLY COVERED
  - All operational guides provide concrete Python code snippets, CLI invocations, and API examples matching in-memory services (`EntityRepository`, `EvidenceVault`, `EventBus`, `CrossBorderRequestEngine`, `AIOrchestrator`, etc.).
- **Layer B (Production):** DOCUMENTED
  - Clear transition guides from Layer A mock/in-memory implementations to Layer B production infrastructure (PostgreSQL, Kafka, OpenSearch, Neo4j, Vault, Kubernetes, OPA/Cedar).

---

## 5. Acceptance Criteria

| # | Criterion | Status | Verification & Notes |
|---|-----------|--------|----------------------|
| 1 | Module Specification (`MODULE-37.md`) completed | MET | Documents purpose, scope, exit criteria, and artifacts |
| 2 | Operator Guide (`operator-guide.md`) published | MET | Step-by-step instructions for entities, evidence, events, campaigns, alerts, health |
| 3 | Investigator Guide (`investigator-guide.md`) published | MET | Covers triage, graph traversal, 7-stage cross-border, crypto tracing, 15 AI tools, STIX export |
| 4 | Administrator Guide (`administrator-guide.md`) published | MET | Covers RBAC/ABAC, 9x8 matrix, user management, audit, rate limits, 5 classification levels, GDPR, key rotation, DR |
| 5 | Developer Guide (`developer-guide.md`) published | MET | Covers repo structure, dependency map, extending entities/rules/topics/models, testing strategy, CI/CD, Ruff |
| 6 | Training Curriculum (`training-curriculum.md`) published | MET | 6 runbook modules, 4 role tracks, practical exercises, sign-off templates |
| 7 | Knowledge Assessment (`knowledge-assessment.md`) published | MET | 40 questions (10/role), answer key, explanations, 80% pass threshold |
| 8 | Documentation Gap Report (`documentation-gap-report.md`) published | MET | Maps docs to 12 go/no-go gates, identifies gaps, provides recommendations |
| 9 | Operational Self-Sufficiency Exit Criterion Verified | MET | Independent execution verified without engineering intervention required |
