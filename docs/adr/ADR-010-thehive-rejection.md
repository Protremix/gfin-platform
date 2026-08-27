# ADR-010: TheHive Rejection

**Status:** REJECTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

TheHive was evaluated as a potential case management platform for GFIN investigations. After thorough evaluation, it has been rejected.

## Decision

**REJECT TheHive integration. GFIN builds its own domain-native case management model.**

## Rationale

1. **Repository archived:** TheHive open-source repository was archived on December 5, 2025
2. **Commercial lock-in:** TheHive 5 is closed-source commercial software with freemium limits
3. **Domain mismatch:** TheHive is for cybersecurity incident response (IOCs, MITRE ATT&CK); GFIN is for financial crime (bank accounts, transactions, compliance)
4. **Infrastructure overhead:** Requires Cassandra + Elasticsearch + S3 — unjustified for GFIN
5. **Feature redundancy:** GFIN's planned Module 12 (Case Management) covers investigation workflows natively

## Consequences

- GFIN builds its own case management (Module 12) with financial fraud domain models
- No TheHive infrastructure to maintain
- No commercial license dependencies
- GFIN's case model natively represents financial entities, transactions, compliance workflows

## Alternatives Considered

- **Integrate TheHive v5 (commercial):** Rejected — commercial lock-in, domain mismatch
- **Fork TheHive v4 (archived):** Rejected — maintenance burden, AGPL, domain mismatch
- **Use Cortex without TheHive:** ACCEPTED — Cortex runs standalone (see ADR-011)
