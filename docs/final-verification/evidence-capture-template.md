# GFIN Infrastructure Deployment — Evidence Capture Template

**Document ID:** GFIN-TEMPLATE-EVD-001  
**Project:** Global Fraud Intelligence Network (GFIN)  
**Target Suite:** `tests/production/test_deployment_acceptance.py`  
**Purpose:** Formatted template for recording execution evidence, logs, metrics, terminal outputs, and screenshots during physical infrastructure deployment and acceptance testing.

---

## 1. Deployment Execution Run Metadata

| Field | Record / Value |
|---|---|
| **Target Environment** | `[ ] Staging  [ ] Production  [ ] Sandbox` |
| **Deployment Execution Date** | `YYYY-MM-DD HH:MM:SS UTC` |
| **Lead Deployment Engineer** | `Name / Title` |
| **Verification Authority** | `Security / QA Lead` |
| **Git Commit Hash** | `Full Commit Hash (e.g. 7a8b9c1d...)` |
| **Cluster Endpoint / Domain** | `e.g., infra.gfin.production.local` |
| **Kubernetes Context** | `e.g., gfin-prod-cluster-us-east-1` |

---

## 2. Infrastructure Environment Variable Configuration

Record the active environment variables configured during this verification run:

```bash
export GFIN_INFRA_HOST="____________________________________"
export K8S_API_URL="____________________________________"
export VAULT_URL="____________________________________"
export KAFKA_HOST="____________________________________"
export KAFKA_PORT="____________________________________"
export POSTGRES_HOST="____________________________________"
export POSTGRES_PORT="____________________________________"
export NEO4J_HOST="____________________________________"
export NEO4J_HTTP_PORT="____________________________________"
export OPENSEARCH_URL="____________________________________"
export REDIS_HOST="____________________________________"
export REDIS_PORT="____________________________________"
export S3_URL="____________________________________"
export PROMETHEUS_URL="____________________________________"
export GRAFANA_URL="____________________________________"
export GFIN_TLS_HOST="____________________________________"
export GFIN_TLS_PORT="____________________________________"
```

---

## 3. Evidence Recording Sheets by Infrastructure Test

### Test 1: Kubernetes Cluster Health (`test_k8s_cluster_health`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 1.1: Pre-Flight CLI Verification
```bash
# Command Executed: kubectl cluster-info && kubectl get nodes -o wide
# OUTPUT:
[PASTE TERMINAL OUTPUT HERE]
```

#### Evidence Capture Block 1.2: Endpoint Health Response
```http
# Command Executed: curl -k -i ${K8S_API_URL}/healthz
# RESP:
[PASTE HTTP HEADER AND BODY RESPONSE HERE]
```

#### Evidence Capture Block 1.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_k8s_cluster_health -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Screenshot Artifact Reference:** `docs/final-verification/evidence/k8s_cluster_health.png`
- **Quantitative Metrics Captured:**
  - Response Time: `______ ms` (Threshold: < 5000 ms)
  - HTTP Status Code: `______` (Expected: 200)
  - Response Body: `______` (Expected: "ok")

---

### Test 2: HashiCorp Vault Connectivity (`test_vault_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 2.1: Vault CLI Status
```bash
# Command Executed: vault status -address=${VAULT_URL}
# OUTPUT:
[PASTE TERMINAL OUTPUT HERE]
```

#### Evidence Capture Block 2.2: Health API JSON Payload
```json
# Command Executed: curl -s ${VAULT_URL}/v1/sys/health | jq .
# PAYLOAD:
[PASTE JSON PAYLOAD HERE]
```

#### Evidence Capture Block 2.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_vault_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Screenshot Artifact Reference:** `docs/final-verification/evidence/vault_status.png`
- **Quantitative Metrics Captured:**
  - `initialized`: `[ ] true   [ ] false` (Expected: true)
  - `sealed`: `[ ] true   [ ] false` (Expected: false)
  - HTTP Status Code: `______` (Expected: 200)

---

### Test 3: Kafka Topics Created (`test_kafka_topics_created`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 3.1: Socket Connectivity Probe
```bash
# Command Executed: nc -zv ${KAFKA_HOST} ${KAFKA_PORT}
# OUTPUT:
[PASTE TERMINAL OUTPUT HERE]
```

#### Evidence Capture Block 3.2: Topic Listing Output
```bash
# Command Executed: kafka-topics.sh --bootstrap-server ${KAFKA_HOST}:${KAFKA_PORT} --list
# OUTPUT (Must include all 14 topics):
[PASTE TOPIC LIST HERE]
```

#### Evidence Capture Block 3.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_kafka_topics_created -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Topic Verification Matrix:**
  - [ ] `gfin-events-entity`
  - [ ] `gfin-events-report`
  - [ ] `gfin-events-evidence`
  - [ ] `gfin-events-alert`
  - [ ] `gfin-events-discovery`
  - [ ] `gfin-events-audit`
  - [ ] `gfin-events-federation`
  - [ ] `gfin-dlq-entity`
  - [ ] `gfin-dlq-report`
  - [ ] `gfin-dlq-evidence`
  - [ ] `gfin-dlq-alert`
  - [ ] `gfin-dlq-discovery`
  - [ ] `gfin-dlq-audit`
  - [ ] `gfin-dlq-federation`

---

### Test 4: PostgreSQL Connectivity (`test_postgresql_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 4.1: Database Server Readiness
```bash
# Command Executed: pg_isready -h ${POSTGRES_HOST} -p ${POSTGRES_PORT}
# OUTPUT:
[PASTE TERMINAL OUTPUT HERE]
```

#### Evidence Capture Block 4.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_postgresql_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - Socket connect_ex Code: `______` (Expected: 0)
  - Connection latency: `______ ms`

---

### Test 5: Neo4j Connectivity (`test_neo4j_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 5.1: HTTP Response Header
```http
# Command Executed: curl -I http://${NEO4J_HOST}:${NEO4J_HTTP_PORT}
# RESP:
[PASTE HTTP HEADER HERE]
```

#### Evidence Capture Block 5.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_neo4j_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - HTTP Status Code: `______` (Expected: 200)

---

### Test 6: OpenSearch Connectivity (`test_opensearch_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 6.1: OpenSearch Cluster Health JSON
```json
# Command Executed: curl -s ${OPENSEARCH_URL}/_cluster/health | jq .
# PAYLOAD:
[PASTE JSON PAYLOAD HERE]
```

#### Evidence Capture Block 6.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_opensearch_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - Cluster Status: `[ ] green   [ ] yellow   [ ] red` (Expected: green or yellow)
  - Number of Nodes: `______`

---

### Test 7: Redis Connectivity (`test_redis_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 7.1: Redis CLI Ping
```bash
# Command Executed: redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} PING
# OUTPUT:
[PASTE TERMINAL OUTPUT HERE]
```

#### Evidence Capture Block 7.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_redis_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - Socket connect_ex Code: `______` (Expected: 0)
  - Redis PING response: `______` (Expected: PONG)

---

### Test 8: S3 Evidence Vault Connectivity (`test_s3_connectivity`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 8.1: MinIO Health Check Response
```http
# Command Executed: curl -i ${S3_URL}/minio/health/live
# RESP:
[PASTE HTTP RESPONSE HERE]
```

#### Evidence Capture Block 8.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_s3_connectivity -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - HTTP Status Code: `______` (Expected: 200)

---

### Test 9: TLS Certificates Validation (`test_tls_certificates_valid`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 9.1: OpenSSL Certificate Inspection
```text
# Command Executed: openssl s_client -connect ${GFIN_TLS_HOST}:${GFIN_TLS_PORT} -servername ${GFIN_TLS_HOST} < /dev/null | openssl x509 -noout -dates -subject -issuer
# OUTPUT:
[PASTE OPENSSL CERTIFICATE DETAILS HERE]
```

#### Evidence Capture Block 9.2: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_tls_certificates_valid -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

- **Quantitative Metrics Captured:**
  - OpenSSL Verify Code: `______` (Expected: 0 (ok))
  - Certificate Expiration Date: `YYYY-MM-DD`

---

### Test 10: Network Isolation Policies Enforced (`test_network_policies_enforced`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 10.1: Applied NetworkPolicies List
```bash
# Command Executed: kubectl get netpol -n gfin-system -o yaml
# OUTPUT:
[PASTE KUBECTL OUTPUT HERE]
```

#### Evidence Capture Block 10.2: Probe Command & Refusal Log
```bash
# Command Executed: kubectl run netpol-probe --image=busybox --restart=Never -n default -- nc -zv -w 3 postgres.gfin-system.svc.cluster.local 5432
# OUTPUT:
[PASTE PROBE TIMEOUT/REFUSAL OUTPUT HERE]
```

#### Evidence Capture Block 10.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_network_policies_enforced -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

---

### Test 11: RBAC Security Roles Configured (`test_rbac_configured`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 11.1: RBAC Resources Summary
```bash
# Command Executed: kubectl get sa,roles,rolebindings -n gfin-system
# OUTPUT:
[PASTE KUBECTL OUTPUT HERE]
```

#### Evidence Capture Block 11.2: ServiceAccount Authorization Checks
```bash
# Command Executed: kubectl auth can-i get secrets --as=system:serviceaccount:gfin-system:gfin-api-sa -n gfin-system
# OUTPUT:
[PASTE AUTHORIZATION CHECK MATRIX HERE]
```

#### Evidence Capture Block 11.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_rbac_configured -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

---

### Test 12: Monitoring Stack Availability (`test_monitoring_stack`)

- **Execution Timestamp:** `YYYY-MM-DD HH:MM:SS UTC`
- **Executor Name:** `________________________________`
- **Status:** `[ ] PASSED    [ ] FAILED    [ ] SKIPPED / BLOCKED`

#### Evidence Capture Block 12.1: Prometheus Health Check
```http
# Command Executed: curl -i ${PROMETHEUS_URL}/-/healthy
# RESP:
[PASTE PROMETHEUS RESPONSE HERE]
```

#### Evidence Capture Block 12.2: Grafana API Health Check
```json
# Command Executed: curl -i ${GRAFANA_URL}/api/health
# RESP:
[PASTE GRAFANA RESPONSE HERE]
```

#### Evidence Capture Block 12.3: Pytest Execution Log
```text
# Command Executed: python -m pytest tests/production/test_deployment_acceptance.py -k test_monitoring_stack -v
# LOG:
[PASTE PYTEST TERMINAL OUTPUT HERE]
```

---

## 4. Summary Verdict & Production Go / No-Go Decision Gate

### 4.1 Test Execution Verdict Matrix

| # | Test Component | Status | Evaluator Sign-Off | Notes / Anomalies |
|---|---|---|---|---|
| 1 | Kubernetes API | `[ ] PASS [ ] FAIL` | `____________` | |
| 2 | HashiCorp Vault | `[ ] PASS [ ] FAIL` | `____________` | |
| 3 | Apache Kafka | `[ ] PASS [ ] FAIL` | `____________` | |
| 4 | PostgreSQL | `[ ] PASS [ ] FAIL` | `____________` | |
| 5 | Neo4j | `[ ] PASS [ ] FAIL` | `____________` | |
| 6 | OpenSearch | `[ ] PASS [ ] FAIL` | `____________` | |
| 7 | Redis | `[ ] PASS [ ] FAIL` | `____________` | |
| 8 | MinIO / S3 | `[ ] PASS [ ] FAIL` | `____________` | |
| 9 | TLS Certificates | `[ ] PASS [ ] FAIL` | `____________` | |
| 10 | Network Policies | `[ ] PASS [ ] FAIL` | `____________` | |
| 11 | K8s RBAC Roles | `[ ] PASS [ ] FAIL` | `____________` | |
| 12 | Monitoring Stack | `[ ] PASS [ ] FAIL` | `____________` | |

### 4.2 Production Readiness Gate Sign-Off

```text
===============================================================================
PRODUCTION INFRASTRUCTURE ACCEPTANCE GATE DECISION
===============================================================================

[ ] APPROVED FOR PRODUCTION DEPLOYMENT
    All 12 infrastructure acceptance tests executed and passed.
    Evidence captured and validated against security and performance baselines.

[ ] REJECTED / REMEDIATION REQUIRED
    One or more infrastructure acceptance tests failed.
    Remediation required prior to production sign-off.

Lead Systems Engineer Signature: _______________________ Date: _______________
Security Officer Signature:      _______________________ Date: _______________
QA Lead Signature:              _______________________ Date: _______________
===============================================================================
```
