# GFIN — Threat Model (Enhanced)

**Version:** 2.0
**Date:** 2026-08-25
**Status:** REVIEW REQUIRED
**Methodology:** STRIDE + threat-specific analysis
**Scope:** All GFIN components, services, interfaces, and trust boundaries

---

## THREAT MODEL STATUS: REVIEW REQUIRED

This threat model covers 20 major threats. Each threat follows the format:
THREAT → ATTACK SURFACE → IMPACT → MITIGATION → DETECTION → RESPONSE

---

## T-01: Malicious Users

| Field | Value |
|-------|-------|
| **THREAT** | A user intentionally submits false reports, fraudulent evidence, or misleading information to poison the intelligence graph or harass targets |
| **ATTACK SURFACE** | Citizen report submission (web/mobile), entity check API, evidence upload |
| **IMPACT** | False fraud flags on innocent entities; wasted investigation resources; platform credibility erosion; potential defamation of targets |
| **MITIGATION** | (1) Report status starts as UNVERIFIED — never automatically fact. (2) Source reliability assessment per reporter (LOW for new accounts). (3) Rate limiting on report submission. (4) Cross-correlation required before CORROBORATED status. (5) Dispute mechanism for flagged entities. (6) Account reputation scoring. |
| **DETECTION** | (1) Volume anomaly detection — sudden spike from single user. (2) Contradiction detection — reports conflict with established evidence. (3) Pattern detection — same user reporting many unrelated entities. (4) Reputation degradation triggers alert. |
| **RESPONSE** | (1) Flag suspicious reports for manual review. (2) Reduce source reliability score. (3) Suspend account if pattern confirmed. (4) Mark affected entity reports as DISPUTED. (5) Document in audit trail. |

## T-02: Compromised Citizen Accounts

| Field | Value |
|-------|-------|
| **THREAT** | An attacker gains access to a citizen account through credential theft, phishing, or session hijacking |
| **ATTACK SURFACE** | Citizen authentication, session tokens, password reset flow, API tokens |
| **IMPACT** | False reports submitted under victim's identity; access to victim's report history; potential privacy exposure of victim's submitted data |
| **MITIGATION** | (1) MFA recommended for citizens (required for elevated accounts). (2) Short-lived session tokens. (3) Rate limiting per account. (4) Anomaly detection on access patterns. (5) Password strength requirements. |
| **DETECTION** | (1) Login from new geography/device. (2) Unusual report volume. (3) Access from known-bad IPs. (4) Concurrent sessions from different locations. |
| **RESPONSE** | (1) Force re-authentication. (2) Notify account owner. (3) Flag reports submitted during compromise period. (4) Revoke active sessions. (5) Require password reset. |

## T-03: Compromised Police Accounts

| Field | Value |
|-------|-------|
| **THREAT** | An attacker compromises a law-enforcement user account, gaining access to restricted intelligence, cross-border data, and investigation tools |
| **ATTACK SURFACE** | Police API authentication, Police Console, OIDC/OAuth2 tokens, investigator credentials |
| **IMPACT** | CATASTROPHIC — unauthorized access to LAW_ENFORCEMENT and HIGHLY_RESTRICTED data; cross-border intelligence exposure; investigation compromise; potential targeting of witnesses or suspects |
| **MITIGATION** | (1) MFA mandatory for all police users. (2) Short-lived tokens (15-minute rotation). (3) ABAC enforcement — jurisdiction and organization scoping. (4) Per-request audit logging (immutable). (5) Just-in-time access for HIGHLY_RESTRICTED data. (6) Network restrictions (VPN/IP allowlist). (7) Session binding to device. |
| **DETECTION** | (1) Access from unauthorized network/IP. (2) Unusual query patterns (bulk entity access, cross-jurisdiction searches). (3) Access at unusual hours. (4) Failed authorization attempts. (5) SIEM correlation across sessions. (6) Anomaly detection on API call patterns. |
| **RESPONSE** | (1) Immediately revoke all tokens for the account. (2) Alert security team and police organization. (3) Full audit review of all access during compromise period. (4) Assess what data was accessed/exfiltrated. (5) Notify affected jurisdictions if cross-border data was accessed. (6) Incident response process initiated. (7) Document in immutable audit trail. |

## T-04: Malicious Source Content

| Field | Value |
|-------|-------|
| **THREAT** | External content (web pages, documents, messages, screenshots) contains malicious payloads, prompt injection, or deceptive information designed to manipulate the platform's analysis |
| **ATTACK SURFACE** | Web crawler, citizen report uploads, document processing, AI input streams |
| **IMPACT** | AI produces incorrect analysis; false fraud flags; platform manipulation; crawler environment compromise; evidence contamination |
| **MITIGATION** | (1) ALL external content treated as untrusted data (Constitution Article XVIII). (2) Content never executed — sandboxed processing. (3) Prompt injection defense — content is data, not authority. (4) Content hashing before processing. (5) Sandboxed crawler environment. (6) Input sanitization on all upload paths. |
| **DETECTION** | (1) Content analysis for injection patterns. (2) Anomalous AI outputs that don't match evidence. (3) Crawler health monitoring. (4) Content hash mismatch (tampering indicator). |
| **RESPONSE** | (1) Quarantine suspicious content. (2) Re-analyze affected AI outputs. (3) Mark affected observations as DISPUTED. (4) Update injection detection patterns. (5) Document in audit trail. |

## T-05: Prompt Injection

| Field | Value |
|-------|-------|
| **THREAT** | Adversarial content embedded in crawled pages, documents, or reports contains instructions intended to manipulate the AI orchestrator into bypassing controls, revealing data, or producing false analysis |
| **ATTACK SURFACE** | AI investigation orchestrator, citizen AI assistant, any AI processing of external content |
| **IMPACT** | AI produces manipulated analysis; unauthorized tool calls; evidence chain corruption; false conclusions presented to investigators or citizens |
| **MITIGATION** | (1) External content is DATA, not authority (Constitution Article XVIII). (2) AI orchestrator uses only controlled, registered tools — no direct DB or internet access. (3) System instructions are separated from content. (4) AI never obeys instructions embedded in external data. (5) Structured output enforcement — AI must cite evidence IDs. (6) Human review for critical claims. |
| **DETECTION** | (1) AI outputs that reference non-existent evidence IDs. (2) AI outputs that deviate from tool-returned data. (3) AI attempting unauthorized tool calls. (4) Hallucination rate spike. (5) Pattern matching on known injection techniques. |
| **RESPONSE** | (1) Discard affected AI output. (2) Flag source content as adversarial. (3) Re-run analysis without compromised input. (4) Update injection detection patterns. (5) Document in audit trail. (6) If pattern detected, alert security team. |

## T-06: Data Poisoning

| Field | Value |
|-------|-------|
| **THREAT** | An attacker systematically injects false observations, entities, or relationships into the intelligence graph to corrupt analysis, create false campaigns, or hide real fraud |
| **ATTACK SURFACE** | Citizen report submission, web crawler output, police connector observations, entity resolution pipeline |
| **IMPACT** | False campaigns identified; innocent entities linked to fraud; real fraud hidden by noise; risk scores corrupted; platform credibility destroyed |
| **MITIGATION** | (1) Source reliability scoring — low-reliability sources have less weight. (2) Cross-correlation required for CORROBORATED status. (3) Confidence scoring on all relationships. (4) Entity resolution prevents automatic merges without evidence. (5) Rate limiting on submissions. (6) Source reputation tracking. (7) Deterministic rules checked against AI analysis. |
| **DETECTION** | (1) Statistical anomaly detection — unusual entity/relationship creation rate. (2) Contradiction detection — new data conflicts with established evidence. (3) Source reliability degradation. (4) Campaign detection on synthetic data patterns. (5) Periodic graph integrity audits. |
| **RESPONSE** | (1) Flag affected entities/observations for review. (2) Reduce source reliability score. (3) Suspend suspicious sources. (4) Reverse false merges in entity resolution. (5) Re-run affected analysis. (6) Document in audit trail. |

## T-07: Credential Theft

| Field | Value |
|-------|-------|
| **THREAT** | Attackers steal credentials (API keys, passwords, tokens, certificates) to gain unauthorized access to GFIN services, AI providers, or infrastructure |
| **ATTACK SURFACE** | API tokens, OIDC tokens, AI provider credentials (OpenAI API keys), police connector credentials, infrastructure access keys, source API keys |
| **IMPACT** | Unauthorized API access; AI provider account misuse (cost, data exfiltration); police connector impersonation; infrastructure access; evidence tampering |
| **MITIGATION** | (1) NO credentials in source code, repos, logs, or docs (Constitution Article XIX). (2) All credentials in Vault/KMS (Layer B). (3) Short-lived tokens with rotation. (4) MFA mandatory for non-citizen users. (5) Secret scanning (gitleaks) in pre-commit and CI. (6) Credential rotation policy. (7) Network restrictions on credential usage. |
| **DETECTION** | (1) Credential usage from unexpected location/IP. (2) Unusual API call patterns. (3) Cost spike on AI provider. (4) Failed authentication followed by successful from new IP. (5) SIEM alerting on credential access patterns. (6) Gitleaks detection in commits. |
| **RESPONSE** | (1) Immediately rotate compromised credential. (2) Revoke all active sessions/tokens. (3) Audit all access using the compromised credential. (4) Assess data exposure. (5) Notify affected parties (AI provider, police orgs). (6) Incident response process. (7) Document in audit trail. |

## T-08: API Abuse

| Field | Value |
|-------|-------|
| **THREAT** | An attacker or compromised client floods the GFIN API with requests to exhaust resources, degrade service, or extract bulk data |
| **ATTACK SURFACE** | API Gateway, all REST endpoints, Police API, search endpoints |
| **IMPACT** | Service degradation or outage; denial of service to legitimate users; bulk data extraction; cost increase (AI, infrastructure) |
| **MITIGATION** | (1) Rate limiting per IP, per user, per organization. (2) API quotas per tier. (3) Request size limits. (4) Query complexity limits (prevent expensive graph queries). (5) WAF (Layer B). (6) Autoscaling (Layer B). (7) Circuit breakers. (8) DLP on responses. |
| **DETECTION** | (1) Request rate exceeds threshold. (2) Unusual query patterns. (3) Large response sizes. (4) Error rate spike. (5) Resource exhaustion metrics (CPU, memory, connections). |
| **RESPONSE** | (1) Throttle or block offending IP/user. (2) Activate WAF rules. (3) Alert operations team. (4) If data exfiltration detected — revoke access and audit. (5) Document in audit trail. |

## T-09: Privilege Escalation

| Field | Value |
|-------|-------|
| **THREAT** | A user or service gains elevated permissions beyond their authorized role through vulnerability, misconfiguration, or token manipulation |
| **ATTACK SURFACE** | Authorization logic, RBAC/ABAC enforcement, token claims, admin endpoints, organization/country boundaries |
| **IMPACT** | Citizen accesses investigator data; investigator accesses another jurisdiction's data; admin functions exposed; data classification bypass |
| **MITIGATION** | (1) Zero Trust — every request re-evaluated (Constitution Article XII). (2) RBAC + ABAC enforcement on every endpoint. (3) Classification-aware access control. (4) Token claims validated server-side (never trust client). (5) No implicit role inheritance. (6) Just-in-time elevation for HIGHLY_RESTRICTED. (7) Principle of least privilege. |
| **DETECTION** | (1) Access attempt to unauthorized resource. (2) Role change without authorization. (3) Token with unexpected claims. (4) Access pattern outside role norms. (5) Security testing (Module 36). |
| **RESPONSE** | (1) Immediately revoke user tokens. (2) Audit all access by the user. (3) Assess what unauthorized data was accessed. (4) Fix vulnerability. (5) Document in audit trail. (6) Incident response. |

## T-10: Insider Threat

| Field | Value |
|-------|-------|
| **THREAT** | A trusted user (administrator, investigator, analyst) intentionally misuses their access to exfiltrate data, tamper with evidence, or compromise investigations |
| **ATTACK SURFACE** | All authenticated endpoints, admin functions, evidence vault, audit system, configuration |
| **IMPACT** | Data exfiltration (intelligence, evidence, citizen data); evidence tampering; investigation compromise; configuration changes weakening security; audit trail manipulation |
| **MITIGATION** | (1) Least privilege — minimum permissions per role. (2) Just-in-time access for sensitive operations. (3) Dual authorization for HIGHLY_RESTRICTED access. (4) Immutable audit trail (append-only). (5) Separation of duties — no single person can both modify evidence and audit logs. (6) DLP on sensitive data. (7) Background checks (organizational policy). (8) Time-limited access grants. |
| **DETECTION** | (1) Unusual access patterns — bulk data export, off-hours access, access outside normal scope. (2) Anomaly detection on query patterns. (3) SIEM correlation across user actions. (4) Audit trail review — gaps or modifications. (5) DLP alerts on sensitive data movement. (6) Behavioral baseline deviation. |
| **RESPONSE** | (1) Immediately revoke access. (2) Full forensic audit of all actions. (3) Assess exfiltrated data scope. (4) Notify law enforcement if criminal. (5) Recover and verify evidence integrity. (6) Review and strengthen access controls. (7) Document in immutable audit trail. |

## T-11: Cross-Tenant Data Leakage

| Field | Value |
|-------|-------|
| **THREAT** | Data from one organization or tenant becomes accessible to another through query bugs, caching errors, or misconfigured access controls |
| **ATTACK SURFACE** | Entity queries, search results, cache (shared cache keys), graph queries, API responses |
| **IMPACT** | Organization A sees Organization B's intelligence; police jurisdiction data leakage; citizen data exposed to other citizens; GDPR violation |
| **MITIGATION** | (1) Tenant isolation enforced at data level (organization_id on every record). (2) Classification-aware query filtering. (3) Per-tenant cache namespacing. (4) Authorization check on every query result. (5) No shared mutable state between tenants. (6) Field-level access control. |
| **DETECTION** | (1) Query results containing records from other organizations. (2) Cache key collision detection. (3) Authorization failure on cross-tenant access. (4) Security testing — tenant isolation tests (Module 36). |
| **RESPONSE** | (1) Immediately fix isolation bug. (2) Audit all affected data access. (3) Notify affected organizations. (4) Review all queries for similar bugs. (5) Document in audit trail. |

## T-12: Cross-Country Data Leakage

| Field | Value |
|-------|-------|
| **THREAT** | Data from one country's jurisdiction becomes accessible to users in another country without going through the formal cross-border request workflow |
| **ATTACK SURFACE** | Federation protocol, global entity index, search service, graph queries, police API |
| **IMPACT** | Sovereignty violation; legal liability; loss of police organization trust; GDPR/directive violation; diplomatic incident |
| **MITIGATION** | (1) Jurisdiction tagging on every record. (2) Classification-aware access control includes jurisdiction check. (3) Federation protocol only shares permitted metadata. (4) Cross-border request workflow with explicit approval. (5) Data residency enforcement at node level. (6) Global index stores only metadata, not case data. |
| **DETECTION** | (1) Access to foreign-jurisdiction data without request record. (2) Query results containing foreign-jurisdiction records. (3) Federation sync anomalies. (4) Audit trail review. (5) Compliance policy tests (Module 33). |
| **RESPONSE** | (1) Immediately block access. (2) Full audit of what was accessed and by whom. (3) Notify both jurisdictions' authorities. (4) Legal counsel engaged (L-02, L-06). (5) Fix isolation/control bug. (6) Incident response. (7) Document in audit trail. |

## T-13: Evidence Tampering

| Field | Value |
|-------|-------|
| **THREAT** | An attacker or insider modifies, deletes, or fabricates evidence in the evidence vault to alter investigation outcomes |
| **ATTACK SURFACE** | Evidence vault storage, evidence API, content hashing process, chain of custody records |
| **IMPACT** | Investigation outcomes altered; wrongful accusations; evidence inadmissible; platform integrity destroyed; legal liability |
| **MITIGATION** | (1) Content hashing (SHA-256) on every evidence item. (2) WORM storage for immutable evidence (Layer B). (3) Chain of custody maintained from acquisition to storage. (4) No silent modification — all changes logged in audit trail. (5) Evidence ID integrity — IDs are immutable. (6) Hash verification on retrieval. (7) Access policy on evidence (classification-aware). |
| **DETECTION** | (1) Content hash mismatch on retrieval. (2) Evidence modification in audit trail without authorization. (3) Gap in chain of custody. (4) Evidence ID reuse or collision. (5) Periodic integrity verification. |
| **RESPONSE** | (1) Immediately quarantine affected evidence. (2) Forensic investigation. (3) Notify legal counsel. (4) Assess impact on ongoing investigations. (5) Restore from backup if available. (6) Document in audit trail. (7) If insider — revoke access and escalate. |

## T-14: AI Hallucination

| Field | Value |
|-------|-------|
| **THREAT** | The AI produces fabricated claims, sources, relationships, or evidence that do not exist, presenting them as factual |
| **ATTACK SURFACE** | AI investigation orchestrator, citizen AI assistant, fraud detection, campaign analysis, risk assessment |
| **IMPACT** | False fraud accusations; wrongful investigation direction; citizen misinformed; platform credibility destroyed; potential legal liability |
| **MITIGATION** | (1) Every AI claim must map to: CLAIM → EVIDENCE_ID → SOURCE → TIMESTAMP → CONFIDENCE (Constitution Article XIV). (2) Claims without evidence IDs marked UNVERIFIED. (3) Critical claims require human review. (4) AI evaluation suite tracks hallucination rate (Module 37). (5) Structured output enforcement. (6) Deterministic rules cross-check AI outputs. (7) If evidence insufficient — return UNKNOWN or INSUFFICIENT_DATA. |
| **DETECTION** | (1) AI output references non-existent evidence IDs. (2) AI output contradicts stored evidence. (3) Hallucination rate exceeds threshold. (4) AI output with no evidence references. (5) Periodic AI evaluation runs. |
| **RESPONSE** | (1) Discard hallucinated output. (2) Mark affected analysis as UNVERIFIED. (3) Human review of affected claims. (4) AI model regression test. (5) Update evaluation thresholds if needed. (6) Document in audit trail. |

## T-15: Model Manipulation

| Field | Value |
|-------|-------|
| **THREAT** | An attacker manipulates AI model behavior through adversarial inputs, training data poisoning, or exploiting model biases to produce desired outputs |
| **ATTACK SURFACE** | AI model inputs (crawled content, reports, messages), model gateway configuration, training data (if fine-tuning), prompt engineering |
| **IMPACT** | AI systematically misclassifies fraud; certain fraud types undetected; risk scores manipulated; specific entities protected or targeted |
| **MITIGATION** | (1) No user-provided training data without validation. (2) Adversarial input testing (Module 37). (3) Model version pinning and regression testing. (4) Deterministic rules as cross-check. (5) Multiple model agreement for critical decisions. (6) Human review for critical claims. (7) Model evaluation on adversarial datasets. |
| **DETECTION** | (1) AI output distribution anomaly — unusual classification pattern. (2) Model performance degradation on evaluation suite. (3) Specific entity types consistently misclassified. (4) Adversarial input patterns detected. (5) Comparison between model versions. |
| **RESPONSE** | (1) Roll back to previous model version. (2) Quarantine affected analysis. (3) Investigate source of manipulation. (4) Re-train or reconfigure model. (5) Run full evaluation suite. (6) Document in audit trail. |

## T-16: Crawler Compromise

| Field | Value |
|-------|-------|
| **THREAT** | The crawler service is compromised through malicious content execution, supply-chain vulnerability, or direct attack, allowing the attacker to inject false data or disrupt discovery |
| **ATTACK SURFACE** | Crawler service, page fetch pipeline, content extraction, crawler queue, crawler credentials |
| **IMPACT** | False entities and observations injected directly into pipeline; crawler used to attack external sites; discovery disruption; evidence contamination |
| **MITIGATION** | (1) Sandboxed crawler environment — no content execution. (2) Crawler runs with minimal privileges. (3) Network segmentation — crawler isolated from core services. (4) Content hashing before processing. (5) Source policy enforcement per domain. (6) Rate limiting and crawl policy enforcement. (7) No persistent connections to crawled sites. |
| **DETECTION** | (1) Crawler health monitoring (CPU, memory, network anomalies). (2) Unusual entities being created by crawler. (3) Crawler accessing unexpected URLs. (4) Crawler process anomaly (unexpected child processes). (5) Content hash anomalies. (6) Security scanning of crawler environment. |
| **RESPONSE** | (1) Immediately stop crawler service. (2) Quarantine all data produced during compromise period. (3) Forensic analysis of crawler environment. (4) Patch vulnerability. (5) Re-crawl affected sources from clean state. (6) Document in audit trail. |

## T-17: Supply-Chain Attacks

| Field | Value |
|-------|-------|
| **THREAT** | A dependency (Python package, Go module, Docker image, container base) is compromised with malicious code that exfiltrates data, creates backdoors, or disrupts operations |
| **ATTACK SURFACE** | pip dependencies, Go modules, Docker base images, CI/CD pipeline, pre-commit hooks |
| **IMPACT** | Data exfiltration through dependency; backdoor in application; CI/CD compromise; supply-chain-wide vulnerability; credential theft |
| **MITIGATION** (1) Dependency evaluation before introduction (Constitution Article XXXIII). (2) Dependency scanning (pip-audit, safety) in CI. (3) Minimal dependencies. (4) Trusted container registries. (5) Image scanning. (6) Signed artifacts. (7) Secret scanning in CI. (8) Least-privilege CI. (9) Lock files for reproducible builds. (10) Regular dependency audits. |
| **DETECTION** | (1) Dependency scan finds vulnerability. (2) Package behavior anomaly (unexpected network calls). (3) Container image scan finds issue. (4) CI pipeline behavior change. (5) SBOM (software bill of materials) review. |
| **RESPONSE** | (1) Immediately remove compromised dependency. (2) Replace with safe alternative. (3) Audit all systems that ran the dependency. (4) Rotate any credentials that may have been exposed. (5) Rebuild images from clean base. (6) Document in audit trail. |

## T-18: Denial of Service

| Field | Value |
|-------|-------|
| **THREAT** | An attacker floods the platform with traffic or resource-intensive requests to make it unavailable to legitimate users |
| **ATTACK SURFACE** | API Gateway, search endpoints, graph queries, report submission, AI orchestrator (expensive LLM calls) |
| **IMPACT** | Platform unavailable to citizens and investigators; investigation delays; AI cost explosion; resource exhaustion |
| **MITIGATION** | (1) Rate limiting per IP, per user, per organization. (2) Request size limits. (3) Query complexity limits. (4) AI cost controls (per-request, per-day). (5) Circuit breakers. (6) WAF (Layer B). (7) Autoscaling (Layer B). (8) CDN for static content (Layer B). (9) Connection pooling limits. (10) Graceful degradation — non-critical features disabled under load. |
| **DETECTION** | (1) Request rate exceeds thresholds. (2) Error rate spike. (3) Resource exhaustion (CPU, memory, connections). (4) Latency increase. (5) AI cost spike. (6) Service health check failures. |
| **RESPONSE** | (1) Activate rate limiting escalation. (2) Block offending IPs. (3) Scale up resources (Layer B). (4) Degrade non-critical features. (5) Alert operations team. (6) Post-incident analysis. (7) Document in audit trail. |

## T-19: Ransomware

| Field | Value |
|-------|-------|
| **THREAT** | An attacker encrypts or destroys platform data and demands payment for restoration |
| **ATTACK SURFACE** | Database, evidence vault, file systems, backups, infrastructure configuration |
| **IMPACT** | Complete data loss; platform shutdown; evidence destruction; investigation compromise; financial extortion; reputational damage |
| **MITIGATION** | (1) Immutable backups (offline copies). (2) Immutable snapshots (Layer B). (3) Evidence in WORM storage (cannot be encrypted/modified). (4) Audit trail in append-only storage. (5) Network segmentation limits lateral movement. (6) Least privilege limits access to backup systems. (7) Regular backup testing (Module 35). (8) No credentials on the systems that could be compromised. |
| **DETECTION** | (1) Mass file modification/encryption detected. (2) Backup system access anomaly. (3) Database abnormal modification pattern. (4) File integrity monitoring alerts. (5) Service health check failures. (6) Ransom note or extortion communication. |
| **RESPONSE** | (1) Immediately isolate affected systems. (2) Activate incident response plan. (3) Assess scope of encryption/loss. (4) Restore from immutable/offline backups. (5) Do NOT pay ransom (policy). (6) Forensic analysis of attack vector. (7) Patch vulnerabilities. (8) Notify law enforcement. (9) Notify affected users/organizations. (10) Document in audit trail. |

## T-20: External Provider Compromise

| Field | Value |
|-------|-------|
| **THREAT** | An external provider (AI provider, DNS service, threat intelligence feed, cloud provider) is compromised, leading to data exposure, service disruption, or malicious data injection |
| **ATTACK SURFACE** | Model Gateway (AI provider), external API integrations, cloud infrastructure, DNS resolution, threat intelligence feeds |
| **IMPACT** | Data sent to AI provider exposed; AI provider unavailable; malicious data from compromised feed; cloud account compromise; DNS manipulation |
| **MITIGATION** | (1) Provider independence — Model Gateway with fallback (Constitution Article XV). (2) Data minimization — only necessary data sent to providers. (3) Classification-aware routing — restricted data stays local. (4) Provider health monitoring. (5) Multiple providers for critical functions. (6) No single provider as sole dependency. (7) Provider credentials in secrets management. (8) Contractual security requirements (DPAs). (9) Local fallback for core operations. |
| **DETECTION** | (1) Provider health check failure. (2) Unusual responses from provider. (3) Provider cost anomaly. (4) Data exposure notification from provider. (5) Provider service degradation. (6) Feed data quality anomaly. |
| **RESPONSE** | (1) Immediately switch to fallback provider. (2) Revoke compromised provider credentials. (3) Audit what data was sent to provider during compromise. (4) Assess data exposure impact. (5) Notify affected users if data was exposed. (6) Engage legal counsel if data breach. (7) Document in audit trail. |

---

## Threat Summary Matrix

| ID | Threat | Impact | Mitigation Status | Detection Status |
|----|--------|--------|-------------------|------------------|
| T-01 | Malicious users | MEDIUM | DESIGNED | DESIGNED |
| T-02 | Compromised citizen accounts | MEDIUM | DESIGNED | DESIGNED |
| T-03 | Compromised police accounts | CATASTROPHIC | DESIGNED | DESIGNED |
| T-04 | Malicious source content | HIGH | DESIGNED | DESIGNED |
| T-05 | Prompt injection | HIGH | DESIGNED | PARTIAL |
| T-06 | Data poisoning | HIGH | DESIGNED | DESIGNED |
| T-07 | Credential theft | HIGH | DESIGNED | DESIGNED |
| T-08 | API abuse | HIGH | DESIGNED | DESIGNED |
| T-09 | Privilege escalation | HIGH | DESIGNED | DESIGNED |
| T-10 | Insider threat | CATASTROPHIC | DESIGNED | DESIGNED |
| T-11 | Cross-tenant data leakage | HIGH | DESIGNED | DESIGNED |
| T-12 | Cross-country data leakage | CATASTROPHIC | DESIGNED | DESIGNED |
| T-13 | Evidence tampering | CATASTROPHIC | DESIGNED | DESIGNED |
| T-14 | AI hallucination | HIGH | DESIGNED | DESIGNED |
| T-15 | Model manipulation | HIGH | DESIGNED | PARTIAL |
| T-16 | Crawler compromise | HIGH | DESIGNED | DESIGNED |
| T-17 | Supply-chain attacks | HIGH | DESIGNED | DESIGNED |
| T-18 | Denial of service | HIGH | DESIGNED | DESIGNED |
| T-19 | Ransomware | CATASTROPHIC | DESIGNED | DESIGNED |
| T-20 | External provider compromise | HIGH | DESIGNED | DESIGNED |

**DESIGNED** = Mitigation/detection designed in architecture; implementation occurs in respective modules.
**PARTIAL** = Some aspects designed; additional design needed.
**TESTED** = Mitigation implemented and tested (none yet — implementation begins in Module 02+).

---

## Open Threat-Related Issues

| # | Issue | Status | Blocks |
|---|-------|--------|--------|
| TH-01 | Penetration testing not yet performed | PENDING | Module 36 |
| TH-02 | Red-team testing not yet performed | PENDING | Module 36 |
| TH-03 | Prompt injection detection patterns need refinement | PARTIAL | Module 22 |
| TH-04 | Adversarial input test suite not yet created | PENDING | Module 37 |
| TH-05 | Tenant isolation tests not yet written | PENDING | Module 36 |
| TH-06 | Cross-jurisdiction isolation tests not yet written | PENDING | Module 33 |
| TH-07 | RTO/RPO targets not validated | PENDING | Module 35 |
| TH-08 | Backup restoration not tested | PENDING | Module 35 |

**THREAT MODEL STATUS: REVIEW REQUIRED**
