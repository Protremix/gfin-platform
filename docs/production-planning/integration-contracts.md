# GFIN External OSINT Integration Contracts
## Per-System Contracts, Threat Model, and Security Requirements

**Document ID:** GFIN-INT-001
**Author:** GPT Luna (GFIN-CEA)
**Directive:** Luna Strategic Assessment — Step 4: Integration Contracts & Threat Modeling
**Status:** DEFINED — REQUIRES EXTERNAL INFRASTRUCTURE
**Date:** 2026-08-26

---

## 1. Overview

This document defines formal integration contracts for all external OSINT (Open Source Intelligence) systems that GFIN connects to. Each contract specifies authentication, data minimization, provenance tracking, failure behavior, rate limiting, and security requirements.

**All integrations are REQUIRES EXTERNAL INFRASTRUCTURE — none are deployed.**

---

## 2. Integration Inventory

| System | Type | Direction | Classification Filter | Status |
|--------|------|-----------|----------------------|--------|
| MISP | Threat Intelligence Platform | Pull | PUBLIC, COMMUNITY | REQUIRES EXTERNAL INFRASTRUCTURE |
| OpenCTI | Threat Intelligence Platform | Bidirectional | PUBLIC, COMMUNITY, RESTRICTED | REQUIRES EXTERNAL INFRASTRUCTURE |
| SpiderFoot | OSINT Scanner | Pull | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cortex | Analysis Engine | Push/Pull | PUBLIC, COMMUNITY | REQUIRES EXTERNAL INFRASTRUCTURE |
| Interpol I-24/7 | Law Enforcement | Bidirectional | LAW_ENFORCEMENT | REQUIRES LEGAL REVIEW |
| Europol SIENA | Law Enforcement | Bidirectional | LAW_ENFORCEMENT | REQUIRES LEGAL REVIEW |
| HaveIBeenPwned | Breach Data | Pull | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |
| VirusTotal | Malware/URL Scanner | Pull | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |
| urlscan.io | URL Scanner | Pull | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |
| AbuseIPDB | IP Reputation | Pull | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |

---

## 3. Contract: MISP

```yaml
integration:
  name: MISP
  version: ">= 2.4"
  type: pull
  description: Pull IOCs (indicators of compromise) from MISP instances

  authentication:
    method: api_key
    header: Authorization
    rotation: 90 days
    storage: HashiCorp Vault KV v2
    audit: every API key read logged

  endpoints:
    events_index: GET /events/index
    event_get: GET /events/{event_id}
    attribute_search: POST /attributes/restSearch

  data_minimization:
    fields_received:
      - event_id
      - info (event description)
      - threat_level_id
      - analysis
      - date
      - attribute_category
      - attribute_type
      - attribute_value
      - attribute_comment
      - attribute_to_ids
    fields_excluded:
      - org (source org identity, unless agreed)
      - sharing_group_id
      - user_id
      - event_creator_email
    classification_filter: COMMUNITY
    max_records_per_request: 500

  provenance:
    source_id_format: "SRC-MISP-{misp_event_id}"
    evidence_required: true
    evidence_type: "api_response_json"
    audit_trail: true
    attribution: "MISP instance: {instance_name}"

  rate_limiting:
    requests_per_minute: 30
    burst: 10
    backoff: exponential
    circuit_breaker_threshold: 10
    circuit_breaker_timeout: 60s

  failure_behavior:
    timeout: 30s
    retry: 3 attempts
    retry_backoff: 1s, 2s, 4s (exponential)
    circuit_breaker: open after 10 consecutive failures
    fallback: degraded mode, serve cached data, log warning
    dlq: send failed sync events to gfin.dlq.discovery

  security:
    encryption_in_transit: TLS 1.3
    encryption_at_rest: AES-256 (for cached MISP data)
    ip_allowlist: [MISP instance IP]
    data_residency: EU only
    secrets_in_code: false
    secrets_in_logs: false

  validation:
    input_validation: schema-validated JSON, reject if invalid
    output_validation: all IOCs validated against schema before ingestion
    duplicate_detection: dedup by (type, value) hash
    stale_data_threshold: 7 days (re-fetch after)

  monitoring:
    health_endpoint: GET /servers/getPyMISPVersion
    health_check_interval: 60s
    metrics:
      - requests_total
      - errors_total
      - latency_ms
      - records_pulled
      - last_sync_timestamp
```

---

## 4. Contract: OpenCTI

```yaml
integration:
  name: OpenCTI
  version: ">= 5.0"
  type: bidirectional
  description: Sync threat intelligence with OpenCTI platform

  authentication:
    method: api_key
    header: Authorization
    rotation: 90 days
    storage: HashiCorp Vault KV v2

  endpoints:
    query: POST /graphql
    stream: GET /stream

  data_minimization:
    fields_exchanged:
      - stix_id
      - entity_type
      - name
      - description
      - created
      - modified
      - confidence
      - created_by
      - object_marking
    classification_filter: RESTRICTED
    max_records_per_batch: 100

  provenance:
    source_id_format: "SRC-OPENCTI-{stix_id}"
    evidence_required: true
    bidirectional_provenance: true
    audit_trail: true

  rate_limiting:
    requests_per_minute: 60
    burst: 20

  failure_behavior:
    timeout: 45s
    retry: 3 attempts
    retry_backoff: exponential
    circuit_breaker_threshold: 10
    fallback: degraded mode, mark as stale

  security:
    encryption_in_transit: TLS 1.3
    encryption_at_rest: AES-256
    ip_allowlist: [OpenCTI instance IPs]
    data_residency: EU only

  stix_mapping:
    gfin_entity_to_stix:
      Person: "identity" (type: individual)
      Phone: "phone-number"
      Email: "email-addr"
      Domain: "domain-name"
      URL: "url"
      IPAddress: "ipv4-addr" or "ipv6-addr"
      CryptoWallet: "cryptocurrency-wallet"
    stix_to_gfin_entity:
      reverse mapping of above
```

---

## 5. Contract: SpiderFoot

```yaml
integration:
  name: SpiderFoot
  version: ">= 4.0"
  type: pull
  description: Automated OSINT scanning of entities

  authentication:
    method: api_key
    header: X-SF-API-Key
    rotation: 60 days
    storage: HashiCorp Vault KV v2

  endpoints:
    start_scan: POST /api/v1/scan
    get_result: GET /api/v1/scan/{scan_id}
    list_modules: GET /api/v1/modules

  data_minimization:
    fields_sent:
      - target_value (entity identifier)
      - target_type (domain, ip, email, phone, username)
    fields_received:
      - module_name
      - data (result data)
      - source (provenance URL/API)
    classification_filter: PUBLIC
    max_concurrent_scans: 5

  provenance:
    source_id_format: "SRC-SF-{scan_id}-{module}"
    evidence_required: true
    audit_trail: true

  rate_limiting:
    scans_per_hour: 10
    result_poll_interval: 30s

  failure_behavior:
    timeout: 60s (scans can be long)
    retry: 2 attempts
    circuit_breaker_threshold: 5
    fallback: mark scan as failed, log

  security:
    encryption_in_transit: TLS 1.3
    data_residency: EU
    modules_whitelist:
      - sfp_dnsresolve
      - sfp_whois
      - sfp_ipinfo
      - sfp_h1enrichment
    modules_blacklist:
      - sfp_binaryedge
      - sfp_censys
      - sfp_shodan
```

---

## 6. Contract: Cortex

```yaml
integration:
  name: Cortex
  version: ">= 3.0"
  type: push/pull
  description: Automated analysis engine for observables

  authentication:
    method: api_key
    header: Authorization
    rotation: 60 days
    storage: HashiCorp Vault KV v2

  endpoints:
    create_job: POST /api/job
    get_report: GET /api/job/{job_id}/report
    list_analyzers: GET /api/analyzer

  data_minimization:
    fields_sent:
      - data (observable value)
      - dataType (type of observable)
    fields_received:
      - analyzer_name
      - report (analysis results)
      - success (boolean)
    classification_filter: COMMUNITY
    max_jobs_per_minute: 20

  provenance:
    source_id_format: "SRC-CORTEX-{job_id}"
    evidence_required: true
    audit_trail: true

  rate_limiting:
    jobs_per_minute: 20
    burst: 5
    max_concurrent_jobs: 10

  failure_behavior:
    timeout: 120s (analyzers can be slow)
    retry: 2 attempts
    circuit_breaker_threshold: 5
    fallback: mark as unanalyzed, continue

  security:
    encryption_in_transit: TLS 1.3
    analyzers_whitelist:
      - DNS
      - Whois
      - VirusTotal
      - urlscan.io
    analyzers_blacklist:
      - Any analyzer sending data to non-EU endpoints
```

---

## 7. Contract: Federation (Interpol/Europol)

```yaml
integration:
  name: Interpol I-24/7 (and Europol SIENA)
  type: bidirectional
  description: Law enforcement data federation

  authentication:
    method: mTLS + bilateral agreement
    certificate_authority: Government PKI
    rotation: per bilateral agreement
    storage: HashiCorp Vault KV v2, isolated partition

  data_minimization:
    fields_exchanged:
      - case_reference
      - entity_identifiers (hashed, per agreement)
      - fraud_type
      - evidence_summary
      - jurisdiction
    fields_excluded:
      - witness identities
      - victim personal data (unless MLAT approved)
      - internal investigation notes
    classification_filter: LAW_ENFORCEMENT
    requires_mlat: true

  provenance:
    source_id_format: "SRC-INTERPOL-{case_id}" / "SRC-EUROPOL-{case_id}"
    evidence_required: true
    audit_trail: true
    legal_basis_required: true

  rate_limiting:
    requests_per_day: 100 (per agreement)
    manual_review_required: true

  failure_behavior:
    timeout: 60s
    retry: 1 attempt (legal sensitivity)
    circuit_breaker_threshold: 3
    fallback: manual intervention

  security:
    encryption_in_transit: mTLS (government PKI)
    encryption_at_rest: AES-256
    data_residency: jurisdiction-specific
    audit: all exchanges logged to immutable audit trail
    legal_review_required: true

  status: REQUIRES LEGAL REVIEW — not implemented until bilateral agreements signed
```

---

## 8. Contract: Third-Party OSINT APIs

### 8.1 HaveIBeenPwned
```yaml
name: HaveIBeenPwned
type: pull
auth: api_key
rate_limit: 1 req/sec
classification_filter: PUBLIC
data_minimal: email → breach names only (no password data pulled)
provenance: SRC-HIBP-{email_hash}
timeout: 15s
```

### 8.2 VirusTotal
```yaml
name: VirusTotal
type: pull
auth: api_key
rate_limit: 4 req/min (free) / 1000 req/day (paid)
classification_filter: PUBLIC
data_minimal: hash/URL/domain → detection ratio, categories
provenance: SRC-VT-{scan_id}
timeout: 30s
```

### 8.3 urlscan.io
```yaml
name: urlscan.io
type: pull
auth: api_key
rate_limit: 1000 req/day (free) / higher (paid)
classification_filter: PUBLIC
data_minimal: URL → scan result, page screenshot (stored as evidence)
provenance: SRC-URLSCAN-{scan_id}
timeout: 30s
```

### 8.4 AbuseIPDB
```yaml
name: AbuseIPDB
type: pull
auth: api_key
rate_limit: 1000 req/day
classification_filter: PUBLIC
data_minimal: IP → abuse confidence score, reports count
provenance: SRC-ABUSEIPDB-{ip}
timeout: 15s
```

---

## 9. Threat Model

### 9.1 Threat Catalog

| ID | Threat | Vector | Impact | Likelihood | Mitigation |
|----|--------|--------|--------|-----------|------------|
| T1 | Malicious data injection via OSINT source | MISP/OpenCTI feed compromised | Poisoned intelligence, false correlations | Medium | Input validation, UNVERIFIED classification, corroboration required |
| T2 | API key compromise | Secret leak, insider threat | Unauthorized data access, impersonation | Low | Vault dynamic secrets, 60-90 day rotation, audit logging |
| T3 | Data exfiltration via integration | Excessive data pulled/pushed | Privacy violation, GDPR breach | Medium | Data minimization rules, classification filter, audit trail |
| T4 | Supply chain attack on OSINT tool | SpiderFoot/Cortex module compromised | Malicious code execution, data theft | Low | Module whitelist, container scanning, signed images |
| T5 | Denial of service on external API | Rate limit exceeded, service down | Degraded intelligence gathering | Medium | Circuit breaker, fallback to cache, rate limiting |
| T6 | Man-in-the-middle on integration channel | Network interception | Data tampering, interception | Low | TLS 1.3, certificate pinning for federation |
| T7 | Privilege escalation via integration | Integration service account too broad | Unauthorized access to GFIN data | Low | Per-integration service account, minimal RBAC |
| T8 | Data poisoning in federation | Partner sends false intelligence | False alerts, misdirection | Medium | Federation data classified as UNVERIFIED, corroboration required |
| T9 | Replay attack on API requests | Captured requests replayed | Duplicate data, confusion | Low | Nonce/timestamp in requests, idempotency keys |
| T10 | Stale data served from cache | Cache not invalidated | Outdated intelligence used in decisions | Medium | TTL on cached data, stale data threshold, re-validation |

### 9.2 Risk Matrix

```
         Low Impact    Medium Impact    High Impact
High     —             T1, T8           T2, T4
Likeliab. T9, T10      T3, T5           T6, T7
Low     —              T10              —
```

### 9.3 Control Summary

| Control | Threats Addressed | Implementation |
|---------|-------------------|---------------|
| Input validation + UNVERIFIED classification | T1, T8 | Schema validation, all external data marked UNVERIFIED until corroborated |
| Vault dynamic secrets + rotation | T2 | Short-lived secrets, no static keys in code |
| Data minimization rules | T3 | Explicit field allowlist per integration |
| Module/analyzer whitelists | T4 | Only approved modules run |
| Circuit breaker + fallback | T5 | Open after N failures, degrade gracefully |
| TLS 1.3 + cert pinning | T6 | All integration channels encrypted |
| Per-integration RBAC | T7 | Dedicated service account per integration |
| Idempotency keys + nonces | T9 | Deduplication at ingestion |
| TTL + stale detection | T10 | Cached data expires, re-validation triggers |

---

## 10. Integration Testing Requirements

| Test | Requirement | Verification |
|------|-------------|-------------|
| Contract conformance | API responses match expected schema | JSON schema validation tests |
| Authentication | Invalid credentials rejected | Negative auth tests |
| Rate limit enforcement | Over-limit requests rejected | Burst test |
| Data minimization | No excluded fields returned | Response field audit |
| Provenance tracking | All data has source attribution | Provenance chain verification |
| Circuit breaker | Opens after N failures, recovers | Failure injection test |
| Fallback behavior | Degrades gracefully | Service down simulation |
| Encryption | TLS 1.3 enforced | ssl-scan integration tests |
| Audit logging | All operations logged | Log capture + verification |
| Idempotency | Duplicate submissions don't duplicate data | Resubmit test |

---

## 11. Status

| Item | Status |
|------|--------|
| MISP contract | DEFINED |
| OpenCTI contract | DEFINED |
| SpiderFoot contract | DEFINED |
| Cortex contract | DEFINED |
| Federation contract | DEFINED — REQUIRES LEGAL REVIEW |
| Third-party API contracts | DEFINED |
| Threat model | COMPLETE |
| Integration tests | DEFINED — REQUIRES EXTERNAL INFRASTRUCTURE |
| Deployment | NOT STARTED — REQUIRES EXTERNAL INFRASTRUCTURE |

---

*End of document — GFIN-INT-001*
