# GFIN Module 04 — Entity Resolution

**Status:** ACCEPTED
**Start Date:** 2026-08-25
**Accept Date:** 2026-08-26
**Accepted By:** GPT Luna (GFIN-CEA)
**Verification:** GPT-5.6-LUNA verified all 13 acceptance criteria with evidence. Criterion 13 (REQUIRES EXTERNAL INFRASTRUCTURE) initially NEEDS FIX, fixed and re-verified. Final verdict: VERIFIED.

---

## Acceptance Criteria

Per Master Spec §8 (Identity Resolution) and Module 04:

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Normalization for all entity types (phone, email, domain, URL, IP, crypto, Telegram, orgs, persons) | VERIFIED | 11 normalizer functions in entity_resolution.py |
| 2 | Matching (exact, normalized, similar, none) with confidence | VERIFIED | MatchType enum, match_entities() function |
| 3 | Deduplication — candidate detection without auto-merge | VERIFIED | find_duplicates() returns candidates only |
| 4 | Confidence scoring (HIGH/MEDIUM/LOW/UNKNOWN) | VERIFIED | MatchResult.confidence field |
| 5 | Entity merge workflow (reversible, auditable, soft-delete) | VERIFIED | merge_entities() + MergeRecord audit |
| 6 | Entity split workflow (reverses merge, restores entity) | VERIFIED | split_entity() + SplitRecord audit |
| 7 | Known equivalent representations resolve correctly | VERIFIED | All 5 phone variants → +34612345678 |
| 8 | No unsafe false merges (similarity ≠ ownership) | VERIFIED | MatchResult has no attribution fields; negative tests |
| 9 | Original raw representation always retained | VERIFIED | raw_values list on entity, transferred on merge |
| 10 | Database abstraction maintained | VERIFIED | Uses EntityRepository, no direct DB coupling |
| 11 | All tests pass | VERIFIED | 98 Module 04 tests pass; 442 full suite pass |
| 12 | Negative tests (fail-safe) | VERIFIED | 8 negative tests: different entities NOT merged, invalid input rejected |
| 13 | Production capabilities marked REQUIRES EXTERNAL INFRASTRUCTURE | VERIFIED | 10 capabilities listed in code |

---

## Implementation

### Files

| File | Lines | Description |
|------|-------|-------------|
| `packages/services/entity_resolution.py` | 728 | Normalization, matching, deduplication, merge/split, service |
| `tests/unit/test_entity_resolution.py` | 787 | 98 tests across 12 test classes |

### Normalization Functions (11)

1. `normalize_phone` — E.164 format (+34 612 345 678 → +34612345678, 0034 → +)
2. `normalize_email` — lowercase, strip, RFC format validation
3. `normalize_domain` — lowercase, strip trailing dot, remove protocol/path
4. `normalize_url` — add https://, lowercase scheme+host, remove default ports
5. `normalize_ip` — IPv4/IPv6 canonical via ipaddress module
6. `normalize_crypto_address` — Ethereum/Bitcoin/Tron blockchain-specific
7. `normalize_telegram` — strip @, lowercase, 5-32 chars
8. `normalize_social_account` — platform-specific (Twitter, Instagram)
9. `normalize_person_name` — lowercase, whitespace-normalized
10. `normalize_organization_name` — lowercase, remove legal suffixes
11. `normalize_value` — dispatch to appropriate normalizer by entity type

### Matching

- `MatchType`: EXACT, NORMALIZED, SIMILAR, NONE
- `MatchResult`: match_type, confidence, normalized_value_match, raw_values_overlap, details
- `match_entities(a, b)`: compares normalized and raw values

### Deduplication

- `find_duplicates()`: O(n²) comparison (Layer A; production uses indexed lookups)
- Returns `DeduplicationCandidate` pairs — does NOT auto-merge
- Filters by minimum confidence threshold

### Merge/Split

- `merge_entities()`: transfers raw values, soft-deletes merged entity, returns `MergeRecord`
- `split_entity()`: restores merged entity, removes transferred values, returns `SplitRecord`
- Fully reversible and auditable

### EntityResolutionService

- `resolve_or_create()`: normalize → find existing → or create new
- `find_matches()`: find potential matches for an entity
- `deduplicate()`: find all duplicate candidates
- `merge()` / `split()`: merge and split via service API

---

## Test Results

- **Module 04 tests:** 98 passed in 2.47s
- **Full suite:** 442 passed in 22.59s
- **Failures:** 0

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Phone normalization | 11 | All 5 spec variants + edge cases + rejections |
| Email normalization | 6 | Case, whitespace, invalid rejection |
| Domain normalization | 7 | Case, trailing dot, protocol, path, subdomain |
| URL normalization | 10 | Scheme, case, ports, path, trailing slash, invalid |
| IP normalization | 6 | IPv4 + IPv6 canonical, invalid |
| Crypto normalization | 6 | Ethereum, Bitcoin, Tron, unknown blockchain |
| Telegram normalization | 6 | @-prefix, case, length, invalid |
| Social account | 4 | Twitter, Instagram, invalid |
| Person/Org | 6 | Whitespace, suffix removal, empty rejection |
| Matching | 6 | Exact, normalized, different types, similarity≠attribution |
| Deduplication | 4 | Find, filter, min confidence, no auto-merge |
| Merge/Split | 9 | Transfer, soft-delete, type check, self-merge, audit, reverse |
| Resolution service | 11 | Create, resolve, all types, matches, dedup, merge+split |
| Negative/fail-safe | 8 | Different entities NOT merged, invalid rejected, preserved |

---

## Production Capabilities — REQUIRES EXTERNAL INFRASTRUCTURE

The following are NOT available in Layer A:

- PostgreSQL indexed lookups for normalized_value (currently O(n²) in-memory scan)
- Apache Kafka event emission for entity.merge, entity.split events (Module 05)
- Distributed merge locking (prevents concurrent merges on same entity)
- Fuzzy matching with ML-based similarity (currently exact normalized comparison)
- Phoneword/phonetic matching for person names (Soundex, Metaphone)
- International phone number validation via libphonenumber (currently regex-based)
- Blockchain address checksum validation (EIP-55 for Ethereum)
- IDN (Internationalized Domain Name) punycode conversion
- Bulk deduplication with parallel processing (currently sequential)
- Merge conflict resolution with concurrent entity updates

All marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
