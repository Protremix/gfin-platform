# GFIN — Legal Assumptions

**Version:** 1.0
**Date:** 2026-08-25
**Status:** DRAFT — REQUIRES LEGAL COUNSEL VALIDATION
**Authority:** Project Owner

---

## ⚠️ DISCLAIMER

This document records engineering-level assumptions to guide development. It is NOT legal advice. All assumptions must be validated by qualified legal counsel before any production deployment. Country-specific deployments require country-specific legal review.

---

## 1. General Assumptions

1. The platform operates as a fraud intelligence and reporting service, not as a law-enforcement authority.
2. Citizen reports are treated as allegations and observations, not as established facts.
3. The platform does not make legal determinations of criminal guilt.
4. Law-enforcement organizations retain sovereignty over their internal case data.
5. Cross-border information sharing requires explicit authorization from the data-owning organization.
6. Data collection uses only legally accessible, permitted, licensed, or user-submitted sources.
7. The platform does not bypass authentication, access controls, or paywalls.

## 2. European Union

**Assumed applicable frameworks:**
- GDPR (Regulation 2016/679) — personal data protection
- Directive (EU) 2016/680 — law-enforcement data protection
- ePrivacy Directive — electronic communications
- Digital Services Act (DSA) — intermediary services
- NIS2 Directive — cybersecurity

**Engineering implications:**
- Data minimization is a default, not an option
- Legal basis must be recorded for each data processing activity
- Data subject rights (access, rectification, erasure where applicable) must be supportable
- Data residency within EU/EEA where required
- Retention policies must be configurable and enforceable
- Automated decision-making requires appropriate safeguards
- Cross-border transfers require appropriate legal mechanisms

**Status:** UNVERIFIED — requires legal counsel to confirm applicability and specific obligations.

## 3. Law-Enforcement Data

**Assumed principles:**
- Police organizations retain control of their internal case data
- The platform does not require or request full database uploads
- Only permitted intelligence metadata is shared through the federation protocol
- Cross-border information requests follow a formal workflow: REQUEST → VALIDATE → AUTHORIZE → REVIEW → APPROVE/DENY → AUDIT
- Each request records: requesting organization, investigator identity, legal basis, purpose, entity, requested information, urgency, case reference

**Engineering implications:**
- Police API enforces authentication, authorization, audit, rate limiting, and monitoring
- Access controls are classification-aware (RESTRICTED, LAW_ENFORCEMENT, HIGHLY_RESTRICTED)
- Sharing policies are enforced at the data level, not just the API level

**Status:** UNVERIFIED — requires legal counsel to validate per-jurisdiction requirements.

## 4. Web Crawling

**Assumed principles:**
- The crawler respects applicable robots.txt and terms of service
- Rate limits are applied to avoid overloading sources
- No authentication bypass or access-control circumvention
- The crawler identifies itself where required
- Crawled content is treated as untrusted input
- No mass scraping of platforms where terms prohibit it (e.g., Telegram)

**Engineering implications:**
- Crawl policies are configurable per source
- Robots.txt and terms compliance is checked before crawling
- Provenance and acquisition method are recorded for every crawled item

**Status:** UNVERIFIED — specific source terms must be reviewed before crawling each source.

## 5. Telegram

**Assumed constraints:**
- No unauthorized mass scraping or prohibited aggregation of Telegram data
- Telegram intelligence uses only: user-submitted data, official APIs/bots within applicable terms, licensed/permitted sources, law-enforcement information obtained through lawful processes
- Current Telegram platform terms must be checked before implementing any Telegram connector
- Telegram data is not used for AI/ML training where platform terms prohibit it

**Status:** UNVERIFIED — Telegram terms of service must be reviewed before implementation.

## 6. AI Provider Usage

**Assumed principles:**
- AI providers (OpenAI, local models, others) are used as analytical tools, not authorities
- Data sent to external AI providers is minimized and authorized
- Enterprise/API privacy and retention controls are used where available
- The platform controls what data is sent, why, by whose authority, and with what retention
- Restricted police data is not sent to external AI providers unless authorized, necessary, contractually permitted, technically protected, and compliant

**Engineering implications:**
- Model Gateway controls all AI provider access
- Request logging and audit are mandatory
- Data classification determines what can be sent to which provider type (local vs external)

**Status:** UNVERIFIED — provider-specific data processing agreements must be reviewed.

## 7. Open Issues

| # | Issue | Impact | Resolution Required |
|---|-------|--------|---------------------|
| L-01 | GDPR applicability and specific obligations not yet confirmed | EU deployment | Legal counsel |
| L-02 | Law-enforcement data protection directive applicability not confirmed | Police API, Federation | Legal counsel |
| L-03 | Per-jurisdiction data residency requirements not yet defined | Infrastructure design | Legal counsel per country |
| L-04 | Telegram terms of service not reviewed | Telegram module | Legal/contracts review |
| L-05 | AI provider data processing agreements not reviewed | Model Gateway, OpenAI module | Legal/contracts review |
| L-06 | Cross-border information request legal framework not defined | Federation, Police API | Legal counsel |
| L-07 | Retention period requirements per classification not defined | Data lifecycle | Legal counsel + policy decision |
