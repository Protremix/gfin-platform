# GFIN — Known Issues

**Last Updated:** 2026-08-25

---

## Active Issues

### Legal (Requires Legal Counsel)

| ID | Issue | Impact | Severity | Status | Blocks |
|----|-------|--------|----------|--------|--------|
| L-01 | GDPR applicability and specific obligations not confirmed | EU deployment | HIGH | OPEN | Production deployment only |
| L-02 | Law-enforcement data protection directive applicability not confirmed | Police API, Federation | HIGH | OPEN | Production deployment only |
| L-03 | Per-jurisdiction data residency requirements not defined | Infrastructure design | MEDIUM | OPEN | Module 32 design |
| L-04 | Telegram Terms of Service not reviewed | Telegram module | HIGH | OPEN | Module 17 (Telegram) if implemented |
| L-05 | AI provider data processing agreements not reviewed | Model Gateway, OpenAI module | HIGH | OPEN | Module 20 production use |
| L-06 | Cross-border information request legal framework not defined | Federation, Police API | HIGH | OPEN | Module 26 production use |
| L-07 | Retention period requirements per classification not defined | Data lifecycle | MEDIUM | OPEN | Module 33 (Compliance) |

### Source Policy

| ID | Issue | Impact | Severity | Status | Blocks |
|----|-------|--------|----------|--------|--------|
| S-01 | Telegram ToS not reviewed | Telegram data sources | HIGH | OPEN | Telegram-related features |
| S-02 | Per-source crawling terms not reviewed | Web crawling | MEDIUM | OPEN | Module 08 (Web Discovery) crawling live sources |
| S-03 | Licensed feed agreements not in place | External intelligence feeds | LOW | PENDING | Licensed feed integration |

### Architecture

| ID | Issue | Impact | Severity | Status | Blocks |
|----|-------|--------|----------|--------|--------|
| A-01 | Graph database selection not finalized (Neo4j vs alternatives) | Infrastructure Graph, Campaign Engine | MEDIUM | PENDING | Module 12 benchmark |
| A-02 | Event streaming approach in Base44 (mock vs real) not decided | Event Bus module | MEDIUM | PENDING | Module 05 design |
| A-03 | Full-text search approach in Base44 vs external not decided | Search module | MEDIUM | PENDING | Module 07 design |
| A-04 | Multi-region deployment strategy not defined | Federation, DR | LOW | PENDING | Module 32/35 design |

### Security

| ID | Issue | Impact | Severity | Status | Blocks |
|----|-------|--------|----------|--------|--------|
| T-05 | Penetration testing not yet performed | Overall security | HIGH | PENDING | Module 36 |
| T-06 | Red-team testing not yet performed | Overall security | HIGH | PENDING | Module 36 |

## Resolved Issues

None yet.

## Issue Naming Convention

- **L-##** — Legal issues
- **S-##** — Source policy issues
- **A-##** — Architecture issues
- **T-##** — Security/threat issues
- **D-##** — Defects (implementation bugs)
