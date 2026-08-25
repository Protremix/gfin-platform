# ADR-005: Infrastructure Interpretation Rules

**Date:** 2026-08-26
**Status:** ACCEPTED
**Context:** Infrastructure intelligence (DNS, IP, ASN, certificates) can be misinterpreted to make unfounded attribution claims. The Master Spec §13 explicitly states: "IP != owner, ASN != criminal, CDN != origin server, shared hosting != common ownership. Never infer criminal ownership from a single technical correlation."

**Decision:** Enforce infrastructure interpretation rules at two levels:

1. **Schema Level:** Model IP, ASN, CDN, origin, hosting, and ownership as distinct typed relationships. The IPInfo model has no `owner` field. The ASNInfo model has no `criminal` field. Attribution edges (OWNS, OPERATES, CRIMINAL_ASSOCIATION) are separate relationship types that require evidence and analyst justification.

2. **Operational Level:** The `validate_attribution()` function enforces:
   - Attribution edges require `evidence_id` (links to Evidence Vault)
   - Attribution edges require `analyst_justification` (human review)
   - Criminal association requires `has_multiple_correlations=True` (no single-correlation inference)
   - Returns `INSUFFICIENT_DATA` when attribution evidence is absent
   - Qualifying language is required in display ("resolves to", "announced by", "hosted on")

**Rationale:**
- Technical correlations are not evidence of criminal activity
- False attribution can cause real harm to innocent parties
- Legal standards require corroboration for criminal claims
- The Constitution mandates evidence-first intelligence

**Consequences:**
- 11 typed relationship types in InfraRelationType enum
- 5 interpretation rules enforced by check_interpretation_rules()
- Attribution edges cannot be created automatically — always require human justification
- Module 09 tests verify all 5 rules (56 tests, all passing)
