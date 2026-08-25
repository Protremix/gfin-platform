# GFIN — Source Policy

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED
**Source:** Constitution Articles XXXIV–XXXVI, Master Spec §12, §17

---

## 1. Purpose

Defines the rules governing all external data sources used by the GFIN platform. Every source must be registered, evaluated, and compliant before use.

## 2. Required Source Metadata

Every external data source must have:

| Field | Description |
|-------|-------------|
| **source_id** | Unique identifier |
| **source_identity** | Name and type of source (e.g., "Citizen Report", "Web Crawl", "RDAP", "Certificate Transparency") |
| **acquisition_method** | How data is obtained (API, crawl, user submission, licensed feed, law-enforcement channel) |
| **terms_classification** | Applicable terms of service, license, or policy |
| **reliability_assessment** | Assessed reliability (HIGH, MEDIUM, LOW, UNKNOWN) |
| **timestamp** | When the source was registered and last reviewed |
| **provenance** | Full provenance chain for data from this source |
| **data_classification** | Default classification for data from this source |
| **retention_policy** | How long data from this source is retained |
| **access_policy** | Who can access data from this source |

## 3. Source Categories

### 3.1 Citizen Submissions
- **Method:** User-submitted via web/mobile
- **Reliability:** LOW (unverified) → MEDIUM (corroborated) → HIGH (verified)
- **Classification:** COMMUNITY (report metadata), RESTRICTED (linked entities)
- **Terms:** GFIN Terms of Service
- **Constraints:** Reports are allegations until corroborated; reporter privacy protected

### 3.2 Permitted Public Sources
- **Method:** APIs, public databases, RDAP, DNS, Certificate Transparency
- **Reliability:** MEDIUM-HIGH (factual infrastructure data)
- **Classification:** PUBLIC
- **Terms:** Per-source terms of service
- **Constraints:** Respect rate limits; no auth bypass; provenance recorded

### 3.3 Web Crawl
- **Method:** Distributed crawler with scheduling and queueing
- **Reliability:** LOW-MEDIUM (content may be manipulated)
- **Classification:** PUBLIC (raw), COMMUNITY (processed)
- **Terms:** Per-site robots.txt and terms of service
- **Constraints:**
  - Respect robots.txt and applicable policies
  - Use rate limits
  - No authentication bypass or access-control circumvention
  - Identify crawler where required
  - Preserve provenance
  - Protect crawler environment from malicious content
  - Crawled content is untrusted input
  - No attempt to crawl "the entire internet"
  - Priority-based discovery only

### 3.4 Licensed/Permitted Feeds
- **Method:** Contractual data feeds (threat intelligence, blockchain intelligence, etc.)
- **Reliability:** MEDIUM-HIGH (per contract)
- **Classification:** Per contract terms
- **Terms:** Contractual license terms
- **Constraints:** Use only within license scope; no redistribution beyond permitted scope

### 3.5 Law-Enforcement Intelligence
- **Method:** Police API, Connector SDK, Federation Protocol
- **Reliability:** HIGH (authoritative source)
- **Classification:** LAW_ENFORCEMENT → HIGHLY_RESTRICTED
- **Terms:** Per-jurisdiction law-enforcement data sharing agreements
- **Constraints:**
  - Only permitted intelligence metadata is shared (no full case databases)
  - Cross-border sharing requires formal request workflow with approvals
  - Source organization retains ownership and control
  - Every share is audited

### 3.6 Telegram
- **Method:** User-submitted, official APIs/bots within terms, licensed sources, lawful law-enforcement channels
- **Reliability:** LOW-MEDIUM (user-submitted), HIGH (law-enforcement)
- **Classification:** COMMUNITY (user-submitted), LAW_ENFORCEMENT (lawful)
- **Terms:** Telegram Terms of Service (MUST be reviewed before implementation)
- **Constraints:**
  - NO unauthorized mass scraping or prohibited aggregation
  - NO use for AI/ML training where platform terms prohibit it
  - User-submitted data only: username, public link, message, screenshot, document, URL
  - Provenance and source classification maintained for all Telegram data

## 4. Source Registration Workflow

```
IDENTIFY SOURCE
→ EVALUATE (security, legal, reliability, terms)
→ CLASSIFY (data classification, access policy)
→ REGISTER (source_id, metadata)
→ APPROVE (project owner or administrator)
→ ACTIVATE (begin data collection)
→ MONITOR (ongoing reliability and compliance assessment)
→ REVIEW PERIODICALLY (terms may change)
```

## 5. Source Violation Handling

If a source is found to be used in violation of its terms:
1. Suspend data collection from that source immediately
2. Document the violation in `/docs/known-issues.md`
3. Assess impact on existing data collected from that source
4. Determine whether existing data must be purged
5. Re-evaluate source registration before resuming

## 6. Prohibited Sources

The following are explicitly prohibited:
- Sources requiring authentication bypass to access
- Sources whose terms explicitly prohibit automated collection
- Sources accessed through credential theft or social engineering
- Mass scraping of platforms where terms prohibit it
- Any source used in a way that violates applicable law

## 7. Open Source Issues

| # | Issue | Status | Resolution |
|---|-------|--------|------------|
| S-01 | Telegram ToS not reviewed | OPEN | Legal/contracts review before Module 17 (Telegram) implementation |
| S-02 | Per-source crawling terms not reviewed | OPEN | Per-source review before crawling each domain |
| S-03 | Licensed feed agreements not in place | PENDING | Business/legal negotiation required |
