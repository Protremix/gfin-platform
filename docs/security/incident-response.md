# GFIN — Incident Response Plan & Playbooks

**Document Version:** 1.0  
**Status:** IMPLEMENTED (Layer A Core) / ARCHITECTURE SPECIFICATION (Layer B Production)  
**Last Updated:** 2026-08-26  
**Platform Architecture:** Python 3.11 / FastAPI Microservices System (Two-Layer Architecture)  

---

## Executive Summary & Architecture Notice

The Global Fraud Intelligence Network (GFIN) operates on a strict **Two-Layer Architecture Strategy**:
* **Layer A (In-Memory MVP — Currently Implemented):** Python/FastAPI microservice endpoints, in-memory data state, in-memory event bus/retry queues, dictionary-based graph & search execution, stdout JSON structured logging (`gfin.observability.logger`), in-memory audit logs (`AuditLogger`), local RBAC/ABAC role enforcement (`gfin.auth.rbac`), in-memory state snapshots (`DisasterRecoveryService`), and in-memory evidence vault custody tracking (`EvidenceVaultService`).
* **Layer B (Production Target — REQUIRES EXTERNAL INFRASTRUCTURE):** Production cloud infrastructure, Kubernetes (K8s) clusters, PostgreSQL multi-region database with Point-in-Time Recovery (PITR), Apache Kafka event streaming clusters, Redis clusters, OpenSearch enterprise search, Neo4j graph cluster, Cloud KMS, Web Application Firewalls (WAF), Security Information and Event Management (SIEM), Security Orchestration Automation and Response (SOAR), and Endpoint Detection & Response (EDR) agents.

> **CRITICAL COMPLIANCE DIRECTIVE:**  
> All incident response procedures documented herein explicitly distinguish between capabilities currently functioning within **Layer A** and those that depend on **Layer B infrastructure**. No security tool or infrastructure component marked `REQUIRES EXTERNAL INFRASTRUCTURE` is claimed as deployed or active in the current Layer A environment.

---

## 1. Incident Response Overview

### 1.1 Purpose & Objectives
The GFIN Incident Response Plan provides a structured, repeatable, and legal-standard framework for detecting, responding to, mitigating, and recovering from security incidents affecting the GFIN fraud intelligence platform. Given GFIN’s core mandate—handling cross-jurisdictional fraud intelligence, evidence vaults, and police agency telemetry—maintaining system integrity, confidentiality of restricted investigations, and continuous availability is paramount.

### 1.2 Two-Layer Architectural Context
Incident handling procedures adapt to the operational layer:
* **In Layer A (In-Memory MVP):** Incident response actions focus on FastAPI service process control, in-memory state snapshots, Python log filtering, API key/JWT token invalidation in memory, rate limit threshold updates in `gfin.auth.rate_limit`, and manual code/state inspection.
* **In Layer B (Production — REQUIRES EXTERNAL INFRASTRUCTURE):** Incident response actions expand to include automated SIEM/SOAR triggers, Kubernetes network policy isolation, cloud security group modifications, cloud storage bucket access revocation, database point-in-time restores, container image rebuilds, and automated EBS/volume forensic snapshotting.

### 1.3 Incident Response Lifecycle
GFIN follows the **NIST SP 800-61 Rev 2** and **ISO/IEC 27035** Incident Response Lifecycle:

```
+-------------------------------------------------------------------+
|                         1. PREPARATION                            |
|  Policy, Training, Layer A Logging/Audit, Layer B Infrastructure   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                     2. DETECTION & ANALYSIS                       |
|  Observability Logs, Rule Triggers, SIEM (B), Severity Triage     |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                        3. CONTAINMENT                             |
|  Short-term: Token Revocation, Rate Limits, Process Shutdown      |
|  Long-term: K8s Isolation (B), WAF Rules (B), DB Quarantine (B)   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       4. ERADICATION                              |
|  Account Termination, Secret Rotation, State Cleanup, Patching   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                         5. RECOVERY                               |
|  State Verification, Service Restoration, Monitoring Enforcement |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    6. POST-INCIDENT ACTIVITY                      |
|  Blameless Post-Mortem, 5 Whys, Threat Model Update, Ticket Audit |
+-------------------------------------------------------------------+
```

### 1.4 Incident Response Team (IRT) Roles & Responsibilities

| Role | Primary Responsibilities | Layer A Execution Context | Layer B Execution Context (REQUIRES EXTERNAL INFRASTRUCTURE) |
| :--- | :--- | :--- | :--- |
| **Incident Commander (IC)** | Leads overall incident execution, severity declaration, resource allocation, and communication strategy. | Directs manual FastAPI container/process actions and team coordination. | Activates enterprise IR war room, engages cloud provider support, signs off on automated SOAR actions. |
| **Lead Security Investigator** | Conducts technical analysis, log investigation, payload inspection, and evidence collection. | Queries stdout JSON logs, inspects `AuditLogger` memory logs, checks `EvidenceVaultService` hash chains. | Queries SIEM (Datadog/Splunk), executes EDR triage scripts, analyzes PCAP network logs. |
| **Infrastructure Lead** | Manages service availability, networking, system boundaries, and process control. | Restarts FastAPI processes, adjusts `pyproject.toml` or env variables, manages local Docker containers. | Manages K8s ingress/NetworkPolicies, rotates cloud IAM permissions, executes cloud infrastructure failover. |
| **Application & AI Lead** | Analyzes application code failures, LLM prompt injections, model gateway abuse, and data schema corruption. | Inspects FastAPI route definitions, `LocalAIGateway`, `OpenAIGateway`, and `InvestigationOrchestrator` pipelines. | Manages model deployment pipelines, isolated AI model gateway proxies, and vector search cluster indices. |
| **Communications Officer** | Handles internal status reports, citizen notifications, and public disclosures. | Uses `AlertEngineService` mock dispatch and standard communication channels. | Manages external status pages, automated customer alert broadcasts, media relations. |
| **Legal & Compliance Officer**| Assesses regulatory exposure (GDPR, NIS2), cross-border law enforcement agreements, and data privacy impact. | Evaluates data classification violations using `ComplianceService` policies. | Leads formal breach disclosures to Data Protection Authorities (DPAs) and national police oversight bodies. |

---

## 2. Detection Methods

Detection capabilities are divided between what is currently functional within the Layer A code base and what will be fulfilled by enterprise tooling upon Layer B production deployment.

### 2.1 Detection Channels

#### 1. Monitoring
* **Layer A (Implemented):** System metrics gathered via `gfin.packages.services.observability` (`ObservabilityService`), including memory usage counters, active HTTP request gauges, endpoint latency histograms, and system health checks (`/health` endpoints).
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Distributed monitoring across Kubernetes clusters via Prometheus, Grafana visualization dashboards, cloud node resource metrics, and container infrastructure health probes.

#### 2. Alerting
* **Layer A (Implemented):** Alert dispatch engine implemented in `gfin.packages.services.alert_engine` (`AlertEngineService`), capable of routing notification records across 5 delivery channels (Email, SMS, Webhook, Push, In-App), managing 4 escalation levels, generating digests, and logging alert statistics.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Real-time integration with PagerDuty / Opsgenie, SIEM correlation alert rules, CloudWatch / Datadog alarm routing, and automated SMS/Voice escalation trees.

#### 3. Log Analysis
* **Layer A (Implemented):** JSON structured logging output via `gfin.observability.logger` to stdout; immutable in-memory audit logs managed by `AuditLogger` in `gfin.auth.audit`, tracking user ID, action, resource, IP address, timestamp, status, and classification level.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Centralized log aggregation platform (Elasticsearch/Logstash/Kibana or Grafana Loki/Splunk), automated log parsing, long-term cold storage log retention, and real-time SIEM string search.

#### 4. Anomaly Detection
* **Layer A (Implemented):** Rule-based fraud and anomaly triggers in `gfin.packages.services.fraud_detection` (`FraudDetectionEngine`), pattern matching across report data, rate-limit threshold breach detection in `gfin.auth.rate_limit`, and cross-border request validation checks in `gfin.packages.services.cross_border_requests`.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Machine learning-based behavioral anomaly detection (UEBA), Cloudflare WAF bot/traffic anomaly detection, database query volume anomaly tracking, and automated network exfiltration detection.

### 2.2 Layer A Implementation vs Layer B Requirements Summary Matrix

| Detection Category | Layer A Capability (Implemented in Code) | Layer B Production Requirement | Status |
| :--- | :--- | :--- | :--- |
| **HTTP Request Audit** | JSON logging via `gfin.observability.logger` & FastAPI middleware | Centralized SIEM stream ingestion (Datadog / Splunk) | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **Authentication Failures** | Logged by `gfin.auth.middleware`; count tracked in memory | Brute-force correlation rules & automated IP bans via Cloud WAF | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **Rate Limit Violations** | In-memory token bucket tracking in `gfin.auth.rate_limit` | Distributed Redis rate limiting & automated edge blocking | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **Data Classification Violations** | Enforced by `ComplianceService` policy checks | Automated DLP (Data Loss Prevention) scanning on network egress | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **Evidence Vault Hash Mismatch** | Hash verification in `EvidenceVaultService` | Immutable WORM hardware storage & cryptographic timestamping | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **Container & Host Intrusions** | Local Python exception handling & health probes | EDR agents (CrowdStrike / Wazuh) & K8s Falco runtime security | **REQUIRES EXTERNAL INFRASTRUCTURE** |
| **AI Prompt Injection** | Input sanitization & detection in `gfin.packages.services.local_ai` | AI WAF / LLM proxy monitoring & real-time output filtering | **REQUIRES EXTERNAL INFRASTRUCTURE** |

---

## 3. Triage Process & Severity Classification

### 3.1 Severity Classification Matrix

Incident triage must be performed within **15 minutes** of initial alert or detection. Severity is classified into four tiers:

| Severity Level | Criteria & Impact | Response SLA | Escalation Target |
| :--- | :--- | :--- | :--- |
| **SEV-1 (CRITICAL)** | • Total service outage of GFIN platform.<br>• Confirmed breach of `LAW_ENFORCEMENT` or `HIGHLY_RESTRICTED` data.<br>• Active exfiltration of evidence vault data.<br>• Supply-chain execution compromise or active Ransomware.<br>• Compromise of cloud root/admin identity. | Immediate (< 15 mins) | Incident Commander, CISO, Executive Steering Board, Legal Counsel, Affected Police Agencies, Data Protection Authorities |
| **SEV-2 (HIGH)** | • Degradation of major service (e.g., Police API down, Model Gateway offline).<br>• Compromise of an elevated investigator account (`police_officer` or `supervisor`).<br>• Partial corruption of in-memory or persistent entity graph.<br>• AI Prompt Injection resulting in unverified evidence alteration in an active case. | < 30 mins | Incident Commander, Lead Security Investigator, Application/Dev Lead, Affected Department Heads |
| **SEV-3 (MEDIUM)** | • Isolated component failure (e.g., single background crawler loop stuck).<br>• Compromise of a standard citizen account.<br>• Low-impact rate limiting bypass or anomalous query spike.<br>• Minor compliance logging discrepancy. | < 2 hours | Lead Security Investigator, Infrastructure Lead, Dev Team |
| **SEV-4 (LOW)** | • Port scanning or automated reconnaissance against external endpoints.<br>• Isolated input validation errors or spam report submission.<br>• Minor documentation discrepancy or non-exploitable code warning. | < 24 hours | On-call Security Analyst |

### 3.2 5-Step Triage Workflow

```
  [Alert Received]
        |
        v
+------------------+     Verify authenticity; eliminate false positives via stdout logs &
| 1. VERIFICATION  | --> audit logs (`AuditLogger`).
+------------------+
        |
        v
+------------------+     Determine affected data classification level: PUBLIC, INTERNAL,
| 2. CLASSIFICATION| --> RESTRICTED, LAW_ENFORCEMENT, or HIGHLY_RESTRICTED per Module 33.
+------------------+
        |
        v
+------------------+     Determine blast radius: affected microservices, user accounts,
| 3. SCOPING       | --> external network connections, and data stores.
+------------------+
        |
        v
+------------------+     Assign SEV-1, SEV-2, SEV-3, or SEV-4 based on Matrix in Section 3.1.
| 4. ASSIGNMENT    | -->
+------------------+
        |
        v
+------------------+     Notify relevant personnel per SLA via `AlertEngineService` and
| 5. DISPATCH      | --> direct IR war room invocation.
+------------------+
```

### 3.3 Triage Scoping & Data Classification Integration
Triage must explicitly evaluate the sensitivity of compromised assets according to the 5 GFIN Data Classification Levels defined in `gfin.packages.services.compliance` (`ComplianceService`):
1. `PUBLIC`: General public statistics, published fraud advisory alerts.
2. `INTERNAL`: System telemetry, aggregate fraud metrics, internal service configurations.
3. `RESTRICTED`: Unverified citizen fraud reports, preliminary entity matching candidates.
4. `LAW_ENFORCEMENT`: Verified police case files, cross-border intelligence requests, officer identities.
5. `HIGHLY_RESTRICTED`: Active undercover intelligence, informant telemetry, cross-border intercept evidence.

---

## 4. Containment Procedures

Containment limits the blast radius of an active security incident.

### 4.1 Short-Term vs Long-Term Containment Strategies

* **Short-Term Containment:** Immediate operational measures to stop active data exfiltration or unauthorized execution without preserving full system functionality.
* **Long-Term Containment:** Sustainable isolation controls allowing core uncompromised components to resume business operations while compromised systems undergo forensic investigation.

### 4.2 Actionable Containment Steps

#### 1. API Token & Session Revocation
* **Layer A (Implemented):** Invalidate target tokens in memory by triggering session clearance in `gfin.auth.middleware`, calling `AuditLogger` to flag token revocation, and updating local user active flags.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Execute global token revocation in Keycloak / OIDC provider, flush Redis session token cache (`FLUSHDB` / target key deletion), and revoke AWS IAM temporary session credentials.

#### 2. Network & Service Isolation
* **Layer A (Implemented):** Stop affected FastAPI application container (`docker stop <container_id>`) or kill local Python process (`kill -9 <pid>`).
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Apply emergency Kubernetes `NetworkPolicy` to block ingress/egress for affected pods:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: isolate-compromised-pod
    namespace: gfin-prod
  spec:
    podSelector:
      matchLabels:
        app: police-api
    policyTypes:
    - Ingress
    - Egress
  ```
  Modify Cloud Security Groups to deny all incoming/outgoing traffic to compromised VM instances; update Cloudflare WAF rules to drop offending client IP blocks.

#### 3. Access Control Lockdown
* **Layer A (Implemented):** Call `ComplianceService.update_access_policy()` to temporarily restrict access to `LAW_ENFORCEMENT` and `HIGHLY_RESTRICTED` classification scopes across all roles.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Enforce temporary emergency ABAC lock in Cloud KMS and IAM roles, locking database connection strings to read-only service accounts.

#### 4. Rate Limiting Lockdown
* **Layer A (Implemented):** Modify rate limit thresholds in `gfin.auth.rate_limit` (`RateLimiter`) dynamically, lowering maximum allowed requests per minute per IP from 60 to 0 for target routes.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Deploy immediate edge-rate-limit rules at API Gateway / NGINX Ingress Controller / Cloudflare WAF.

#### 5. Data Flow Quarantine & Event Bus Isolation
* **Layer A (Implemented):** Pause event routing in `gfin.packages.common.event_bus` (`EventBusAdapter`), causing incoming events to accumulate in the local retry queue or dead-letter queue (DLQ) without downstream execution.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Revoke Kafka ACL consumer/producer permissions for compromised microservice client IDs, preventing topic consumption or publication.

---

## 5. Eradication Procedures

Eradication removes the root cause of the incident and eliminates all malicious artifacts.

### 5.1 Root Cause Removal & Malicious Artifact Scrubbing
* **Layer A (Implemented):** Flush corrupted in-memory data structures by restarting FastAPI services; purge contaminated in-memory caches and re-initialize state templates.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Terminate compromised Kubernetes pods, delete infected node instances, re-image virtual machines from golden base images, and destroy compromised persistent storage volumes after forensic image capture.

### 5.2 Compromised Identity Termination & Key Rotation
* Revoke compromised API keys, JWT signing keys, and database passwords.
* Rotate OpenAI API Gateway credentials in `.env` / environment variables.
* Rotate symmetric encryption keys used for evidence payload signing in `EvidenceVaultService`.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Execute automated key rotation via AWS Secrets Manager / HashiCorp Vault; force mandatory password resets and MFA re-enrollment across all OIDC identity providers.

### 5.3 Emergency Patching & Hotfix Deployment
1. Develop emergency hotfix in a dedicated git branch (`hotfix/INC-<ticket_id>`).
2. Run Module 36 Security Validation Suite (`pytest tests/security/`).
3. Build updated Python wheel package or local container image.
4. **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Trigger CI/CD pipeline, perform container image scan via Trivy/Clair, push signed container to Private Container Registry (ECR), and execute K8s rolling update (`kubectl rollout restart deployment/<service_name>`).

### 5.4 Graph & Database Data Remediation
* **Layer A (Implemented):** Re-load clear state snapshot via `DisasterRecoveryService.restore_backup()`.
* **Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):** Execute targeted SQL script transaction rollbacks on PostgreSQL; run Cypher remediation queries on Neo4j graph database to prune unauthorized node/edge additions; re-index OpenSearch indices from clean database state.

---

## 6. Recovery Procedures

Recovery safely restores affected services to full operational production status.

### 6.1 Integrity Verification & System Validation
Prior to reopening user access, the Incident Response Team must execute verification checks:
1. **Security Testing Suite:** Execute full test suite via `gfin.packages.services.security_testing` (`SecurityTestingService`), verifying 15 critical security controls.
2. **Audit Trail Verification:** Ensure `AuditLogger` is active and recording log lines with correct SHA-256 integrity hashes.
3. **Evidence Vault Verification:** Run `EvidenceVaultService.verify_vault_integrity()` to confirm zero evidence tampering or custody gap.
4. **Data Classification Validation:** Test `ComplianceService` privacy filters to verify sensitive fields (`LAW_ENFORCEMENT`, `HIGHLY_RESTRICTED`) are correctly redacted for non-privileged callers.

### 6.2 Staged System Restoration & Dependency Sequence
Services must be brought online strictly according to architectural dependency order:

```
Step 1: Core Storage & Auth (PostgreSQL [B], Redis [B], Audit Log [A/B])
   |
   v
Step 2: Event Bus & Messaging (Kafka Cluster [B], EventBusAdapter [A])
   |
   v
Step 3: Intelligence Engines (Entity Resolution [A], Evidence Vault [A], Graph DB [B])
   |
   v
Step 4: AI Gateways & Orchestrator (LocalAI [A], Model Gateway [A/B], Investigation Orchestrator [A])
   |
   v
Step 5: External APIs & Gateways (Police API [A], Citizen Platform [A], Police Console [A])
```

### 6.3 Post-Recovery Monitoring & Traffic Normalization
* Place restored services under **Enhanced Monitoring** for 72 hours.
* Set `ObservabilityService` metric sampling rate to maximum logging detail.
* Slowly lift rate limit restrictions in `gfin.auth.rate_limit`, monitoring request volume, error rates, and CPU/memory metrics.

---

## 7. Notification Requirements

GFIN handles multi-jurisdictional police data and citizen PII, triggering strict legal, regulatory, and contractual notification mandates.

### 7.1 Internal Stakeholder Escalation Matrix
* **SEV-1 (Critical):** Immediate alert within 15 minutes to IC, CISO, CEO, General Counsel, Engineering VP. Status updates every 30 minutes.
* **SEV-2 (High):** Notification within 30 minutes to IC, Engineering Leads, Product Manager. Status updates every 2 hours.
* **SEV-3 / SEV-4:** Digest notification to security team via internal channels.

### 7.2 External Stakeholder & Partner Law Enforcement Notifications
* **Police Agency Partners:** If an incident involves potential compromise of `LAW_ENFORCEMENT` data, police API tokens, or active cross-border requests (`CrossBorderRequestService`), formal notification must be delivered to affected law enforcement security contacts within **4 hours** of SEV-1 confirmation.
* **Federated National Nodes (Module 32):** Notify connected national nodes (ES, FR, DE, etc.) via `FederationService` broadcast messages if cross-border intelligence node integrity is threatened.

### 7.3 Regulatory Reporting Framework
* **EU GDPR (Article 33 / 34):** Confirmed personal data breaches must be reported to the Lead Supervisory Authority (e.g., AEPD, CNIL) within **72 hours** of becoming aware of the breach. If high risk to citizen rights exists, affected citizens must be notified without undue delay.
* **EU NIS2 Directive:** For platform entities classed as essential/important digital providers, an early warning alert must be submitted to the competent national CSIRT / authority within **24 hours**, followed by a formal incident notification within **72 hours**, and a final report within **1 month**.

### 7.4 Notification Timelines & Escalation SLA Summary Table

| Recipient Group | Trigger Condition | Mandatory SLA | Mandatory Information to Include |
| :--- | :--- | :--- | :--- |
| **GFIN Executive Board** | SEV-1 or SEV-2 Declaration | < 15 mins (SEV-1)<br>< 30 mins (SEV-2) | Nature of incident, affected systems, estimated downtime, containment posture. |
| **National CSIRTs / NIS2 Authorities** | Essential Service Disruption or SEV-1 Cloud/Infra Breach | < 24 hours (Early Warning)<br>< 72 hours (Full Initial) | Initial assessment, severity, indicator of compromise (IoC), cross-border impact. |
| **Data Protection Authorities (GDPR)** | Confirmed Breach of PII or Unverified Citizen Reports | < 72 hours | Nature of breach, categories/number of data subjects affected, contact details of DPO, likely consequences, measures taken. |
| **Partner Law Enforcement Agencies** | Compromise of `LAW_ENFORCEMENT` data or Police API | < 4 hours | Scope of compromised intelligence, affected agency case IDs, token revocation confirmation, remediation steps. |
| **Affected Citizens** | High-risk breach of citizen user accounts/PII | Without undue delay | Clear description of breach, recommended self-protection steps, support contact details. |

---

## 8. Evidence Preservation

Preserving evidence integrity is critical for legal proceedings, criminal prosecution of fraud actors, and internal forensic analysis.

### 8.1 Evidence Vault Integration & Chain of Custody
* All digital evidence items associated with an incident must be logged into the GFIN Evidence Vault via `gfin.packages.services.evidence_vault` (`EvidenceVaultService`).
* **Cryptographic Hash Tracking:** Every preserved log file, memory dump, or payload sample must have its SHA-256 hash computed immediately upon capture.
* **Custody Log:** `EvidenceVaultService` automatically records immutable custody entries containing timestamp, accessor ID, operation (`PRESERVE`, `EXPORT`, `INSPECT`), and SHA-256 validation hash.

### 8.2 Forensic Snapshotting & Memory Dumps

#### Layer A Preservation Procedures (Implemented)
1. **In-Memory State Backup:** Call `DisasterRecoveryService.create_backup()` to generate an in-memory JSON snapshot of current system entities, metrics, and state.
2. **Log File Export:** Redirect stdout JSON logs from `gfin.observability.logger` to a secure disk archive:
   ```bash
   docker logs gfin-api-container > /forensics/incidents/INC-$(date +%Y%m%d_%H%M%S)-stdout.log
   ```
3. **Compute Archive Hash:**
   ```bash
   sha256sum /forensics/incidents/INC-*-stdout.log > /forensics/incidents/checksums.sha256
   ```

#### Layer B Preservation Procedures (REQUIRES EXTERNAL INFRASTRUCTURE)
1. **EBS / Cloud Volume Snapshots:** Trigger automated AWS EBS / Cloud Disk snapshot via AWS CLI:
   ```bash
   aws ec2 create-snapshot --volume-id vol-0123456789abcdef0 --description "Forensic Snapshot INC-2026-08"
   ```
2. **Kubernetes Memory Core Dumps:** Capture live memory core dumps from target containers before pod termination using `gcore` or specialized forensic container sidecars.
3. **Database WAL Log Preservation:** Freeze PostgreSQL Write-Ahead Logs (WAL) and ship to isolated write-once-read-many (WORM) S3 buckets.
4. **Network PCAP Capture:** Enable VPC Flow Logs and capture raw network packet logs from container network interfaces.

### 8.3 Legal Admissibility Guarantees
To maintain legal admissibility in court:
* Evidence files must remain read-only (`chmod 400`).
* Writes must be verified against original SHA-256 hashes recorded in `EvidenceVaultService`.
* Investigators must log every inspection command in the incident timeline journal.

---

## 9. Post-Incident Review Process

The Post-Incident Review ensures continuous improvement of technical controls and incident response capabilities.

### 9.1 Blameless Post-Mortem Workflow & Timeline Reconstruction
Within **5 business days** of incident closure, the Incident Commander must convene a **Blameless Post-Mortem Meeting** with all IRT members and key engineering stakeholders.

**Post-Mortem Agenda:**
1. **Timeline Reconstruction:** Minute-by-minute accurate sequence of events (Initial compromise -> Detection -> Containment -> Eradication -> Recovery).
2. **What Went Well:** Identification of effective controls, rapid detections, or successful playbook execution.
3. **What Went Wrong:** Identification of delayed alerts, missing logs, containment friction, or procedural gaps.
4. **Where We Got Lucky:** Scenarios where fortuitous conditions prevented greater damage.

### 9.2 Root Cause Analysis (5 Whys Framework)
The team must apply the **5 Whys Methodology** to identify underlying systemic vulnerabilities rather than surface-level human errors:

```
[Incident: Unauthorized Police API Access]
  1. Why? Attacker obtained valid JWT token for police officer.
  2. Why? Token was leaked in plaintext within an application log output.
  3. Why? Log filter failed to redact header bearer tokens on route exception.
  4. Why? Exception handler bypassed standard `gfin.observability.logger` redaction pipeline.
  5. Why? New FastAPI custom exception middleware was added without security review.
  --> ROOT CAUSE: Lack of mandatory security middleware verification in CI/CD build pipeline.
```

### 9.3 Action Item Tracking, Security Testing Integration & Threat Model Updates
1. **Security Ticket Creation:** Register all post-incident action items in `gfin.packages.services.security_testing` (`SecurityTestingService`), categorizing findings by severity and tracking remediation status.
2. **Threat Model Updates:** Review and update `gfin/docs/threat-model.md` to reflect new threat vectors or updated attack surface definitions discovered during the incident.
3. **Detection Rule Tuning:** Update rule parameters in `FraudDetectionEngine`, `AlertEngineService`, and SIEM (Layer B) to ensure immediate future detection of similar attack signatures.

---

## 10. Incident Response Playbooks

---

### Playbook 1: Credential Compromise

#### 1. Detection Indicators
* Multiple failed login attempts followed by a successful authentication from an unexpected IP address or geography.
* Concurrent active sessions for the same user ID (`police_officer` or `admin`) originating from different subnet ranges.
* Anomaly alerts triggered by `gfin.auth.rate_limit` indicating abnormal request volume on user endpoints.
* Execution of high-privilege operations (e.g., cross-border data requests) outside normal operating hours.

#### 2. Immediate Actions (First 15 Minutes)
1. **Verify Compromise:** Query `AuditLogger` in `gfin.auth.audit` for the target user ID to review recent IP addresses, user agents, and accessed endpoints.
2. **Declare Incident:** Assign initial severity rating (SEV-2 for standard investigator account; SEV-1 if police supervisor or system admin account).
3. **Revoke Active User Tokens:**  
   * *Layer A (Implemented):* Execute in-memory session clearance via `gfin.auth.middleware` to reject all incoming requests presenting the compromised user's JWT token.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Call Keycloak OIDC API `/auth/admin/realms/gfin/users/{id}/logout` to revoke refresh tokens and purge active Redis session cache keys.

#### 3. Containment Steps
* **Disable User Account:** Set user `active_status = False` in identity store and update RBAC cache in `gfin.auth.rbac`.
* **Block Offending IP Addresses:**  
   * *Layer A (Implemented):* Add client IP to `gfin.auth.rate_limit` blocklist with 0 request quota.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Add IP address to Cloudflare WAF block rule and Kubernetes NGINX Ingress deny list.
* **Isolate Session Permissions:** Restrict overall system ABAC scope for target organization using `ComplianceService`.

#### 4. Eradication Steps
* **Credentials Reset:** Perform mandatory password reset and invalidate current API keys for the affected user account.
* **Secret & Signing Key Rotation:** If an admin account was compromised, rotate JWT signing secret keys (`JWT_SECRET_KEY`) used by FastAPI middleware.
* **Audit Trail Exfiltration Check:** Inspect stdout logs and `AuditLogger` history during the compromise window to map all accessed entities, cases, and evidence files.

#### 5. Recovery Steps
* **Re-Authenticate Account Owner:** Verify identity of user out-of-band (e.g., voice verification with police department supervisor) before re-enabling account.
* **Re-Enable Account with Enforced MFA:** Enable user account requiring compulsory MFA registration upon next login.
* **Monitor Session Activity:** Place account on 72-hour priority audit watch using `ContinuousMonitoringService`.

#### 6. Post-Incident Actions
* File security ticket in `SecurityTestingService` tracking credential leak root cause (phishing, credential stuffing, repo leak).
* Update `gfin/docs/threat-model.md` threat T-02 / T-03 mitigation effectiveness.
* Conduct post-mortem review and publish findings report.

---

### Playbook 2: Data Breach

#### 1. Detection Indicators
* Large volume query execution detected on `/api/v1/entities` or `/api/v1/evidence` endpoints.
* Anomaly alert from `FraudDetectionEngine` indicating mass export of `LAW_ENFORCEMENT` or `HIGHLY_RESTRICTED` records.
* Data Loss Prevention (DLP) egress alert (Layer B) or unusual outbound network traffic volume.
* Public report or external alert indicating GFIN intelligence data published on third-party forums.

#### 2. Immediate Actions (First 15 Minutes)
1. **Identify Exfiltration Source:** Inspect `AuditLogger` lines to identify performing client IP, user ID, API token, and API endpoint.
2. **Declare SEV-1 Incident:** Data breaches involving restricted fraud intelligence or PII automatically trigger SEV-1 status.
3. **Cut Exfiltration Vector:**  
   * *Layer A (Implemented):* Immediately lower endpoint rate limits in `gfin.auth.rate_limit` to 0 for affected routes; pause `EventBusAdapter` event dispatch.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Deploy emergency K8s `NetworkPolicy` blocking egress traffic from API gateway pods; revoke S3 / Cloud Storage bucket read policies.

#### 3. Containment Steps
* **Isolate Compromised Service & User:** Suspend target user account in `gfin.auth.rbac` and stop affected FastAPI worker processes.
* **Restructure Access Control Boundaries:** Update `ComplianceService` policy to enforce blanket restriction on data classification levels `LAW_ENFORCEMENT` and `HIGHLY_RESTRICTED`.
* **Lock Out External Connectors:**  
   * *Layer A (Implemented):* Disable Police Connector SDK sync routines (`PoliceConnectorSDK.suspend_all()`).  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Sever external VPN tunnels and mTLS connections to external partner agency nodes.

#### 4. Eradication Steps
* **Identify Complete Breach Scope:** Extract all audit logs covering the incident timeframe to compile an exact ledger of exfiltrated entity IDs, citizen reports, and evidence files.
* **Remediate Access Vulnerability:** Patch underlying authorization vulnerability (e.g., IDOR, missing ABAC check) in FastAPI route handlers.
* **Rotate All Accessible Data Secrets:** Rotate database credentials, API access tokens, and encryption keys.

#### 5. Recovery Steps
* **Verify System Patching:** Run `SecurityTestingService` automated test suite to verify authorization fixes.
* **Staged Service Re-Opening:** Incrementally re-enable API routes while monitoring request patterns via `ObservabilityService`.
* **Execute Regulatory & Stakeholder Reporting:** Trigger 72-hour GDPR notification and notify affected police agencies within 4 hours per Section 7 requirements.

#### 6. Post-Incident Actions
* Convene mandatory post-mortem meeting within 48 hours.
* Perform comprehensive audit of all historical data exports.
* Implement additional automated DLP scanning controls in Layer B design specifications.

---

### Playbook 3: Ransomware

#### 1. Detection Indicators
* Mass file modification/deletion errors or invalid cryptographic signatures in `EvidenceVaultService`.
* Database query execution failures due to missing tables, corrupted headers, or locked storage volumes.
* Detection of ransom notes (`READ_ME_NOW.txt`) or unauthorized file extensions on system storage.
* High CPU/IO disk usage alerts coupled with sudden storage growth (Layer B infrastructure).

#### 2. Immediate Actions (First 15 Minutes)
1. **Declare SEV-1 Incident:** Ransomware represents an immediate critical threat to system survival and evidence integrity.
2. **Halt System Persistence & Processes:**  
   * *Layer A (Implemented):* Immediately terminate FastAPI application processes (`killall uvicorn` or `docker stop`) to freeze in-memory data state and halt ongoing encryption routines.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Isolate Kubernetes node instances from network using Cloud Security Group rules; disconnect shared storage volumes (EBS/EFS).
3. **Preserve Forensic Snapshots:**  
   * *Layer A (Implemented):* Export current in-memory snapshot via `DisasterRecoveryService` to an isolated offline directory.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Take immediate read-only EBS disk volume snapshots via AWS CLI before power cycling.

#### 3. Containment Steps
* **Network Segment Quarantine:** Isolate storage servers, database nodes, and background worker containers.
* **Disable Automated Backups Synchronization:** Sever backup sync channels to prevent encrypted/corrupted data from overwriting clean offline backups.
* **Revoke All Infrastructure Credentials:** Invalidate all cloud IAM credentials, K8s service account tokens, and SSH keys.

#### 4. Eradication Steps
* **System Wipe:** Complete destruction and re-provisioning of affected virtual machines, container pods, and transient local storage.
* **Malware Root Cause Analysis:** Identify initial entry vector (e.g., compromised dependency, exposed management port, unpatched vulnerability).
* **Environment Re-building:** Rebuild environment cleanly using infrastructure-as-code (Terraform / K8s manifests) and clean container images.

#### 5. Recovery Steps
* **Data Restoration from Immutable Backups:**  
   * *Layer A (Implemented):* Restore in-memory data structures using `DisasterRecoveryService.restore_backup()` from known-good pre-incident state dump.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Execute PostgreSQL Point-in-Time Recovery (PITR) to a timestamp immediately prior to the ransomware execution; restore OpenSearch and Neo4j clusters from offline S3 snapshots.
* **Integrity Validation:** Run `EvidenceVaultService.verify_vault_integrity()` to verify restored evidence hash consistency.
* **Controlled Service Resume:** Re-enable system access following staged restoration sequence (Section 6.2).

#### 6. Post-Incident Actions
* Submit incident report to national cybersecurity authority (CSIRT / NIS2 authority).
* Audit backup architecture to ensure immutable offline (air-gapped) storage guarantees.
* Conduct full vulnerability scan using `SecurityTestingService`.

---

### Playbook 4: Malicious Insider

#### 1. Detection Indicators
* An investigator or police account searching for entities outside their assigned jurisdiction or active case scope.
* Repeated attempts to access `HIGHLY_RESTRICTED` data without authorization (logged as access denied by `ComplianceService`).
* Sudden spike in data export or search query activity by a single authenticated user.
* Off-hours logins accompanied by deletion of audit logs or evidence vault entries.

#### 2. Immediate Actions (First 15 Minutes)
1. **Verify Insider Activity:** Inspect `AuditLogger` lines in `gfin.auth.audit` to trace exact actions performed by the target user ID, cross-referencing assigned organization and jurisdiction permissions.
2. **Declare SEV-2 Incident** (Escalate to SEV-1 if `HIGHLY_RESTRICTED` law enforcement data was accessed or exfiltrated).
3. **Silent Session Termination:**  
   * *Layer A (Implemented):* Immediately revoke target user session in `gfin.auth.middleware` and set RBAC role permissions to `NONE` in `gfin.auth.rbac`.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Revoke OIDC active session tokens and disable account access across all police network gateways.

#### 3. Containment Steps
* **Freeze User Account & Audit Profile:** Freeze account status without notifying the user (to avoid evidence destruction if insider is still active on site).
* **Preserve User Audit Journal:** Export full immutable audit history for the user via `AuditLogger` and register archive hash in `EvidenceVaultService`.
* **Revoke Key Escrow & Encryption Access:** Invalidate user's personal encryption keys and mTLS client certificates.

#### 4. Eradication Steps
* **Identify Unauthorized Modifications:** Query `gfin.packages.services.entity_resolution` and evidence vault logs to detect any entity relationships, fraud reports, or evidence items added, altered, or deleted by the insider.
* **Data State Rollback:** Revert unauthorized changes by executing state rollback in Layer A or database transaction reversal in Layer B.
* **Legal & HR Coordination:** Freeze all physical and digital access badges, laptops, and remote VPN access in coordination with organizational HR and law enforcement internal affairs.

#### 5. Recovery Steps
* **Re-Validate Compromised Case Files:** Have an independent police supervisor re-examine all cases accessed by the insider during the threat window.
* **Restore Data Consistency:** Re-calculate entity confidence scores in `FraudDetectionEngine` following malicious entry removal.
* **Resume Operations:** Re-establish normal workflow for unaffected team members.

#### 6. Post-Incident Actions
* Prepare formal legal and forensic evidence packet for criminal prosecution or administrative disciplinary proceedings.
* Enhance Attribute-Based Access Control (ABAC) rules in `gfin.auth.rbac` to enforce tighter jurisdiction isolation.
* Conduct internal policy review regarding insider risk management and just-in-time privilege elevation.

---

### Playbook 5: Cloud Compromise

#### 1. Detection Indicators
* Unauthorized login alerts for Cloud Management Console or IAM root/admin accounts.
* Spurious cloud resource creation (e.g., deployment of unauthorized EC2 instances, GPU clusters, or unknown K8s namespaces).
* Unexpected changes to Cloud Security Groups, IAM Policies, or Network Gateways.
* Billing volume spikes or CloudTrail / GuardDuty anomaly security alerts (Layer B).

#### 2. Immediate Actions (First 15 Minutes)
1. **Declare SEV-1 Incident:** Cloud infrastructure compromise poses systemic threat to all hosted GFIN components and data layers.
2. **Identify Compromised Cloud Identity:** Analyze cloud API audit logs (AWS CloudTrail / Azure Activity Log) to locate compromised IAM user, role, or access key ID.
3. **Revoke Cloud Credentials:**  
   * *Layer A Context:* N/A (Layer A runs in local Python environment / local Docker).  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* De-authorize target IAM user/role immediately; attach inline deny-all policy (`AWSAdminNoAccess`); revoke active AWS CLI/SDK session keys.

#### 3. Containment Steps
* **Isolate Network VPC & Kubernetes Cluster:**  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Restrict Cloud Security Groups to deny access from public subnets; set Kubernetes API server ingress to private administrative IPs only.
* **Freeze IAM Policy Changes:** Lock IAM configuration to prevent unauthorized privilege escalation or backdoor creation.
* **Terminate Malicious Resources:** Terminate all unrecognized VM instances, container pods, and serverless functions deployed by the attacker.

#### 4. Eradication Steps
* **Cloud Infrastructure Audit:** Execute full security audit of CloudTrail logs, reviewing all API calls made within 30 days of the incident.
* **Root & Admin Key Rotation:** Rotate all AWS IAM access keys, SSH key pairs, KMS customer master keys, and K8s service account tokens.
* **Re-Deploy Clean Infrastructure:** Re-apply baseline infrastructure definitions via verified Terraform / CloudFormation scripts.

#### 5. Recovery Steps
* **Verify Cluster & Service Health:** Execute `ObservabilityService` health checks across all microservices.
* **Verify Persistence Layers:** Validate PostgreSQL database, OpenSearch cluster, and Redis cluster integrity.
* **Resume Production Ingress Traffic:** Re-enable Cloudflare WAF and load balancer routing.

#### 6. Post-Incident Actions
* Conduct root cause analysis on how cloud credentials were compromised (e.g., hardcoded secret in repo, missing MFA).
* Enforce mandatory MFA for all Cloud Management Console access.
* Deploy continuous cloud security posture management (CSPM) tools in Layer B target design.

---

### Playbook 6: Supply-Chain Compromise

#### 1. Detection Indicators
* Security scanner alert (e.g., GitHub Dependabot, Snyk, Gitleaks, or `gitleaks.toml` pipeline alert) identifying malicious dependency package or backdoored library.
* Unexplained outbound network calls originating from FastAPI Python worker processes to unknown IP addresses/domains.
* Hash validation failures on imported third-party wheels or container base images.
* Unexpected file system access or process execution initiated by third-party Python dependencies.

#### 2. Immediate Actions (First 15 Minutes)
1. **Identify Malicious Dependency:** Inspect `pyproject.toml`, `requirements.txt`, or build logs to isolate the exact package name, version, and import path.
2. **Declare Severity:** Assign SEV-1 if the compromised dependency ran in production or accessed secret keys; SEV-2 if caught in build/test CI pipeline.
3. **Halt CI/CD Pipelines & Deployments:** Immediately pause all automated build and deployment pipelines to prevent propagation of the backdoored code.
4. **Isolate Running Workers:**  
   * *Layer A (Implemented):* Terminate local Python process running the compromised package.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Terminate affected K8s pods and block outgoing process traffic via EDR/Wazuh agents.

#### 3. Containment Steps
* **Lock Network Egress:** Restrict outgoing internet access for application worker processes, permitting connections only to explicitly allowed AI gateways and partner API endpoints.
* **Quarantine Compromised Version:** Remove the affected library version from internal package mirrors and PyPI caches.
* **Revoke Build & Repository Tokens:** Invalidate PyPI tokens, GitHub Actions secrets, and container registry access keys.

#### 4. Eradication Steps
* **Dependency Pinning & Rollback:** Roll back `pyproject.toml` dependency version to a verified clean release, or remove the package entirely.
* **Audit Source Code & Package Integrity:** Run static analysis and file integrity checks across all project directories (`gfin/packages/`, `gfin/services/`).
* **Secret Rotation:** Rotate all environment secrets (`OPENAI_API_KEY`, DB passwords, JWT secrets) that were accessible within the runtime environment of the compromised package.

#### 5. Recovery Steps
* **Clean Build Verification:** Rebuild FastAPI application artifacts from scratch in an isolated build environment.
* **Execute Security Validation:** Run complete test suite using `SecurityTestingService` and execute `pytest tests/`.
* **Deploy Clean Patch:** Release updated application containers and resume staging/production traffic.

#### 6. Post-Incident Actions
* Mandate cryptographic dependency signature verification (`pip --require-hashes`) for all python packages.
* Integrate automated Software Bill of Materials (SBOM) tracking and vulnerability scanning into CI/CD pipeline.
* Share IoCs (package name, file hashes, C2 domains) with community threat intelligence feeds.

---

### Playbook 7: AI Data Leakage

#### 1. Detection Indicators
* Prompt injection detection triggered in `gfin.packages.services.local_ai` (`LocalAIGateway`) or `gfin.packages.services.investigation_orchestrator` (`InvestigationOrchestrator`).
* Outbound payload inspection showing sensitive `LAW_ENFORCEMENT` or `HIGHLY_RESTRICTED` data transmitted in external LLM gateway calls (`OpenAIGateway`).
* Unexpected model synthesis outputs containing leaked system instructions, API keys, or unrelated case data.
* High rate of unusual or structured adversarial prompts detected in web crawler inputs (`WebDiscoveryService`) or citizen report submissions.

#### 2. Immediate Actions (First 15 Minutes)
1. **Identify Leakage Channel:** Determine whether data leakage occurred via external LLM API call (`OpenAIGateway`), local AI output (`LocalAIGateway`), or orchestration agent tool execution.
2. **Declare Incident:** Declare SEV-2 (or SEV-1 if `HIGHLY_RESTRICTED` law enforcement intelligence or PII was transmitted to an unapproved external AI provider).
3. **Disable External AI Routing:**  
   * *Layer A (Implemented):* Force `ModelGateway` to route all AI traffic exclusively to local fallback models (`LocalAIAdapter`), severing connections to external OpenAI endpoints.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Block outgoing HTTPS requests to external AI provider IPs at the API Gateway / Egress Firewall.

#### 3. Containment Steps
* **Quarantine Prompt Sources:** Suspend user accounts, crawler jobs, or external report feeds that originated the adversarial prompt.
* **Sanitize Active Context:** Flush current in-memory conversation memory, orchestration step logs, and temporary prompt templates in `InvestigationOrchestrator`.
* **Enforce Classification Filter:** Verify that `ComplianceService.filter_privacy()` is applied to all data payloads prior to entering the AI gateway pipeline.

#### 4. Eradication Steps
* **Update Prompt Injection Filters:** Enhance pattern detection dictionaries and sanitization rules in `gfin.packages.services.local_ai` (`detect_prompt_injection()`).
* **Purge Remote Model Caches:** Request data/cache purging from external AI vendor support if sensitive data was inadvertently submitted in API calls.
* **Patch Model Gateway Enforcers:** Update `OpenAIGateway` logic to enforce mandatory client-side data redaction on all outbound payloads regardless of caller permissions.

#### 5. Recovery Steps
* **Validate Redaction Pipelines:** Run test suite verifying that PII, case IDs, officer names, and restricted flags are stripped before model ingestion.
* **Re-Enable AI Services:** Restore standard AI orchestration operations under heightened log sampling.
* **Re-Analyze Affected Cases:** Re-run investigation synthesis for cases impacted by poisoned AI outputs.

#### 6. Post-Incident Actions
* Conduct comprehensive review of AI safety guidelines (`gfin/docs/security/discovery-threat-model.md`).
* Update Module 20/21 test cases to include new adversarial prompt injection payloads.
* Report AI security incident details to GFIN AI Governance Committee.

---

### Playbook 8: Database Compromise

#### 1. Detection Indicators
* Unauthenticated database access alerts or failed authentication spikes on database ports (5432 PostgreSQL, 7687 Neo4j, 9200 OpenSearch).
* SQL injection (SQLi) attack patterns detected in FastAPI route parameters or stdout application logs.
* Unauthorized data modification, table dropping, or schema alteration detected during entity reads (`read_entities`).
* Discrepancy detected between database record checksums and `EvidenceVaultService` custody tracking logs.

#### 2. Immediate Actions (First 15 Minutes)
1. **Identify Attack Vector:** Determine whether access occurred via SQL injection in FastAPI route, compromised DB user credentials, or direct database network access.
2. **Declare SEV-1 Incident:** Database compromise threatens all persistent fraud intelligence, audit trails, and evidence chains.
3. **Isolate Database Access:**  
   * *Layer A (Implemented):* Terminate FastAPI processes to stop all application queries against in-memory repository structures.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Modify PostgreSQL `pg_hba.conf` / Security Groups to reject all connections except from dedicated forensic IP; revoke active DB connection pools in Redis/Bouncer.

#### 3. Containment Steps
* **Freeze Database Permissions:** Change database user passwords and alter database state to `READ ONLY`.
* **Isolate Network Subnet:** Disconnect database cluster subnets from public ingress subnets.
* **Preserve Database Logs:** Archive PostgreSQL Write-Ahead Logs (WAL), Neo4j transaction logs, and OpenSearch audit logs to secure read-only storage.

#### 4. Eradication Steps
* **Patch Vulnerable Application Code:** Fix underlying SQL injection or ORM vulnerability in application services (`gfin.packages.common.postgres_repository`).
* **Database Instance Purge:** Terminate compromised database instances and recreate database host nodes from clean machine images.
* **Secret & Certificate Rotation:** Rotate all database passwords, SSL/TLS server certificates, and application connection strings.

#### 5. Recovery Steps
* **Execute Point-in-Time Recovery (PITR):**  
   * *Layer A (Implemented):* Restore clean in-memory state snapshot using `DisasterRecoveryService.restore_backup()`.  
   * *Layer B (REQUIRES EXTERNAL INFRASTRUCTURE):* Perform PostgreSQL PITR restore to a precise transaction log timestamp immediately preceding the compromise; rebuild OpenSearch vector indices and Neo4j graph nodes from restored SQL state.
* **Data Integrity Audit:** Execute `EvidenceVaultService.verify_vault_integrity()` and run integrity verification scripts to ensure zero data corruption.
* **Restore Application Connections:** Re-enable application connection pools and resume normal API traffic.

#### 6. Post-Incident Actions
* Implement automated static code analysis (Bandit / Semgrep) in CI/CD pipeline to block SQL injection vulnerabilities.
* Enforce strict database least-privilege permissions (e.g., application user cannot execute DDL commands).
* Conduct full database security review and publish incident post-mortem report.

---

## 11. Maintenance & Review Schedule

This Incident Response Plan and associated playbooks must be maintained under strict revision control:
* **Quarterly Review:** Review and update contact lists, escalation matrix, and regulatory requirements.
* **Post-Incident Review:** Update relevant playbooks within 10 business days following any SEV-1 or SEV-2 security incident.
* **Annual Simulation:** Execute a full tabletop incident response exercise annually, testing both Layer A in-memory procedures and Layer B production infrastructure recovery plans.
