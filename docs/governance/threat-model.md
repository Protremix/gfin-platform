# GFIN — Threat Model

**Version:** 1.0
**Date:** 2026-08-25
**Status:** APPROVED
**Source:** Constitution Articles XVII–XVIII, XXVII, Master Spec §45

---

## 1. Methodology

This threat model identifies assets, threat actors, attack surfaces, and mitigations. It follows a STRIDE-based approach (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) adapted for the GFIN platform's specific risks.

## 2. Assets

| Asset | Description | Classification |
|-------|-------------|---------------|
| Intelligence Graph | Entity/relationship/evidence data | RESTRICTED → HIGHLY_RESTRICTED |
| Evidence Vault | Stored evidence with chain of custody | HIGHLY_RESTRICTED |
| Citizen Reports | User-submitted fraud reports | COMMUNITY → RESTRICTED |
| Police Intelligence | Match metadata, observations, case references | LAW_ENFORCEMENT → HIGHLY_RESTRICTED |
| User PII | Citizen emails, phones, account data | RESTRICTED |
| AI Model Gateway | Provider credentials, routing config, logs | HIGHLY_RESTRICTED |
| Source Credentials | API keys, crawler auth tokens | HIGHLY_RESTRICTED |
| Audit Logs | Immutable action records | HIGHLY_RESTRICTED |
| Infrastructure Config | Kubernetes, Terraform, secrets | HIGHLY_RESTRICTED |
| Search Index | OpenSearch indices | RESTRICTED → LAW_ENFORCEMENT |

## 3. Threat Actors

| Actor | Motivation | Capability |
|-------|------------|------------|
| **Fraudster** | Evade detection, poison data, discredit reports | Low-medium technical; can submit false reports, create adversarial content on crawled pages |
| **Malicious Insider** | Exfiltrate data, manipulate evidence, bypass controls | Medium-high; has some legitimate access |
| **State-Sponsored Actor** | Disrupt platform, access intelligence, target investigators | High; advanced persistent threat capability |
| **Opportunistic Attacker** | Exploit vulnerabilities for financial gain | Medium; targets exposed APIs, credentials |
| **Compromised User** | Unwitting participant (phished credential theft) | Low-medium; access limited to their role |
| **AI Adversary** | Manipulate AI outputs via prompt injection, adversarial inputs | Medium; can craft malicious content for crawlers and reports |

## 4. Attack Surfaces and Threats

### 4.1 API Layer

| Threat (STRIDE) | Description | Mitigation |
|----------------|-------------|-----------|
| **Spoofing** | Stolen credentials used to access API | MFA, OIDC/OAuth2, token rotation, short-lived tokens |
| **Tampering** | Data manipulation via API | Input validation, schema enforcement, audit logging, immutable evidence |
| **Repudiation** | User denies action | Immutable audit trail, signed requests |
| **Information Disclosure** | Over-permissive API responses | Classification-aware access control, field-level filtering, least privilege |
| **Denial of Service** | API flooding | Rate limiting, quotas, WAF, autoscaling |
| **Elevation of Privilege** | Role escalation, broken access control | RBAC + ABAC, tenant isolation, classification enforcement |

### 4.2 Web Crawler

| Threat | Description | Mitigation |
|--------|-------------|-----------|
| **Prompt Injection** | Crawled pages contain AI manipulation instructions | Content treated as data, not authority; sandboxed processing; no execution of embedded instructions |
| **Malware Delivery** | Crawler downloads malicious content | Sandboxed crawler environment, no execution of downloaded content, content hashing before processing |
| **Rate Limit Evasion** | Crawler overwhelms target or evades detection | Per-source rate limits, robots.txt compliance, crawl policy enforcement |
| **Poisoned Data** | Adversary plants false information for crawling | Source reliability assessment, cross-correlation before trust, observation ≠ fact |
| **Legal Exposure** | Crawling prohibited content | Robots.txt/terms compliance, per-source policy, no auth bypass, provenance recording |

### 4.3 AI Systems

| Threat | Description | Mitigation |
|--------|-------------|-----------|
| **Prompt Injection** | External content manipulates AI reasoning | Content is data not authority; AI tools are sandboxed; no direct DB or internet access; controlled tool registry |
| **Hallucination** | AI fabricates sources, relationships, evidence | Claim → Evidence → Source → Timestamp → Confidence chain; UNVERIFIED marking; human review for critical claims |
| **Data Exfiltration via AI** | Sensitive data sent to external AI provider | Classification-aware routing; restricted data stays on local models; Model Gateway controls what is sent |
| **Provider Compromise** | AI provider account compromised | Provider credentials in secrets management; audit logging; provider health monitoring |
| **Model Degradation** | Updated model produces worse results | Regression testing, AI evaluation suite, version pinning |

### 4.4 Data Storage

| Threat | Description | Mitigation |
|--------|-------------|-----------|
| **Unauthorized Access** | Direct DB access bypassing API | Network segmentation, no public DB endpoints, encryption at rest, key management |
| **Data Tampering** | Evidence modification | WORM storage for evidence, content hashing, chain of custody, audit trail |
| **Data Exfiltration** | Bulk data extraction | DLP, access monitoring, anomaly detection, query rate limits |
| **Ransomware** | Data encryption by attacker | Backups, immutable snapshots, offline copies |

### 4.5 Federation / Police API

| Threat | Description | Mitigation |
|--------|-------------|-----------|
| **Unauthorized Cross-Border Access** | Organization accesses data outside their jurisdiction | Jurisdiction-aware access control, classification enforcement, request workflow with approvals |
| **Connector Compromise** | Police connector credentials stolen | Per-connector authentication, credential rotation, audit, anomaly detection |
| **Data Injection** | Malicious or compromised police source injects false intelligence | Source verification, confidence scoring, observation ≠ fact, cross-correlation |
| **Replay Attacks** | Intercepted requests replayed | Nonce, timestamps, request signing, TLS |

### 4.6 Supply Chain

| Threat | Description | Mitigation |
|--------|-------------|-----------|
| **Compromised Dependency** | Malicious or vulnerable dependency | Dependency evaluation (security, license, maintenance), dependency scanning, minimal dependencies |
| **Compromised Container Image** | Base image contains vulnerabilities or backdoors | Image scanning, trusted registries, minimal base images |
| **CI/CD Compromise** | Build pipeline attacked | Secret scanning, least-privilege CI, signed artifacts |

## 5. Security Controls

### 5.1 Mandatory Controls

| Control | Implementation |
|---------|--------------|
| Zero Trust | No implicit trust; every request authenticated and authorized |
| MFA | Required for all non-citizen users; optional but recommended for citizens |
| OIDC/OAuth2 | Identity provider integration, short-lived tokens |
| RBAC + ABAC | Role-based + attribute-based (classification, jurisdiction, organization) |
| Least Privilege | Minimum permissions per role |
| Encryption in transit | TLS 1.2+ everywhere |
| Encryption at rest | Database, object storage, backups |
| Key management | KMS/Vault; no keys in source code |
| Network segmentation | Services isolated; no public DB/cache endpoints |
| Secrets management | Vault/KMS; no secrets in repos, logs, or docs |
| Tenant isolation | Per-organization data isolation |
| Country isolation | Jurisdiction-aware data segregation |
| Immutable audit | Append-only audit logs |
| SIEM | Security information and event management |
| Anomaly detection | Behavioral monitoring for unusual access patterns |
| DLP | Data loss prevention for sensitive fields |
| Rate limiting | API, search, and query rate limits |
| API security | Schema validation, auth, audit, monitoring on all endpoints |
| Incident response | Defined response procedures and runbooks |

### 5.2 Evidence-Specific Controls

| Control | Implementation |
|---------|--------------|
| WORM storage | Immutable storage for evidence classes requiring immutability |
| Content hashing | SHA-256 hash on all evidence items |
| Chain of custody | Full provenance from acquisition to storage |
| Access policy | Classification-aware access control on evidence |
| Retention policy | Configurable retention with legal hold support |

## 6. Open Threats (Track in known-issues.md)

| # | Threat | Status | Mitigation Status |
|---|--------|--------|-------------------|
| T-01 | Legal framework for cross-border data sharing not validated | OPEN | Blocked on legal counsel (L-06) |
| T-02 | Retention period requirements not defined | OPEN | Blocked on legal counsel (L-07) |
| T-03 | AI provider data processing agreements not reviewed | OPEN | Blocked on legal review (L-05) |
| T-04 | Specific source terms for crawling not reviewed | OPEN | Blocked per-source review required |
| T-05 | Penetration testing not yet performed | PENDING | Module 36 (Security Testing) |
| T-06 | Red-team testing not yet performed | PENDING | Module 36 (Security Testing) |

## 7. Assumptions

1. The platform operates on cloud infrastructure with standard security capabilities (KMS, network policies, IAM)
2. All inter-service communication uses TLS
3. All databases are accessed through authenticated API layers only
4. The crawler runs in an isolated, sandboxed environment
5. AI providers are accessed only through the Model Gateway
6. All external content (crawled pages, documents, messages) is untrusted by default
