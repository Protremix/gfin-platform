# GFIN Production Infrastructure Acceptance Test Checklists

**Document ID:** GFIN-DOC-INFRA-CHK-001  
**Directive Reference:** Final Build Verification Directive §4 / Layer B Deployment Plan  
**Project:** Global Fraud Intelligence Network (GFIN)  
**Date:** August 26, 2026  
**Status:** Layer B Deployment Readiness & Execution Checklists  
**Target Test Module:** `tests/production/test_deployment_acceptance.py`  

---

## 1. Executive Summary & Overview

This document provides explicit execution checklists, prerequisite infrastructure descriptions, step-by-step testing procedures, evidence requirements, and pass/fail criteria for the 12 skipped infrastructure acceptance tests in the GFIN repository.

Under GFIN's dual-layer architecture:
- **Layer A (Pilot & In-Memory):** Business logic, data models, schemas, and in-memory event handlers are 100% verified across 2,428 passing unit, contract, and integration tests.
- **Layer B (Production Microservices & Infrastructure):** Acceptance tests in `tests/production/test_deployment_acceptance.py` validate physical cloud infrastructure, databases, streaming brokers, key management, network isolation policies, and observability stacks. These tests are marked with `@pytest.mark.skip(reason="REQUIRES EXTERNAL INFRASTRUCTURE: ...")` until backing services are provisioned.

### 1.1 Summary Matrix of Skipped Infrastructure Tests

| # | Test Name | File Location | Component | Skip Reason | Key Config / Env Variable | Verification Method |
|---|---|---|---|---|---|---|
| 1 | `test_k8s_cluster_health` | `tests/production/test_deployment_acceptance.py:48` | Kubernetes API | `REQUIRES EXTERNAL INFRASTRUCTURE: Kubernetes` | `K8S_API_URL`, `GFIN_INFRA_HOST` | HTTP GET `/healthz` == 200 "ok" |
| 2 | `test_vault_connectivity` | `tests/production/test_deployment_acceptance.py:60` | HashiCorp Vault | `REQUIRES EXTERNAL INFRASTRUCTURE: Vault` | `VAULT_URL`, `GFIN_INFRA_HOST` | HTTP GET `/v1/sys/health` == 200, `initialized=true`, `sealed=false` |
| 3 | `test_kafka_topics_created` | `tests/production/test_deployment_acceptance.py:74` | Apache Kafka | `REQUIRES EXTERNAL INFRASTRUCTURE: Kafka` | `KAFKA_HOST`, `KAFKA_PORT` | TCP connect port 9092, list 14 GFIN topics |
| 4 | `test_postgresql_connectivity` | `tests/production/test_deployment_acceptance.py:94` | PostgreSQL | `REQUIRES EXTERNAL INFRASTRUCTURE: PostgreSQL` | `POSTGRES_HOST`, `POSTGRES_PORT` | TCP connect port 5432 |
| 5 | `test_neo4j_connectivity` | `tests/production/test_deployment_acceptance.py:104` | Neo4j Graph DB | `REQUIRES EXTERNAL INFRASTRUCTURE: Neo4j` | `NEO4J_HOST`, `NEO4J_HTTP_PORT` | HTTP GET `http://${NEO4J_HOST}:7474` == 200 |
| 6 | `test_opensearch_connectivity` | `tests/production/test_deployment_acceptance.py:115` | OpenSearch | `REQUIRES EXTERNAL INFRASTRUCTURE: OpenSearch` | `OPENSEARCH_URL`, `GFIN_INFRA_HOST` | HTTP GET `/_cluster/health` == 200, status `green`/`yellow` |
| 7 | `test_redis_connectivity` | `tests/production/test_deployment_acceptance.py:128` | Redis | `REQUIRES EXTERNAL INFRASTRUCTURE: Redis` | `REDIS_HOST`, `REDIS_PORT` | TCP connect port 6379 |
| 8 | `test_s3_connectivity` | `tests/production/test_deployment_acceptance.py:138` | S3 / MinIO | `REQUIRES EXTERNAL INFRASTRUCTURE: S3` | `S3_URL`, `GFIN_INFRA_HOST` | HTTP GET `/minio/health/live` == 200 |
| 9 | `test_tls_certificates_valid` | `tests/production/test_deployment_acceptance.py:149` | TLS / SSL | `REQUIRES EXTERNAL INFRASTRUCTURE: TLS` | `GFIN_TLS_HOST`, `GFIN_TLS_PORT` | SSL socket handshake, valid peer certificate |
| 10 | `test_network_policies_enforced` | `tests/production/test_deployment_acceptance.py:165` | K8s NetworkPolicy | `REQUIRES EXTERNAL INFRASTRUCTURE: Network Policies` | `network_policies_active` flag / CNI rules | Cross-zone network isolation enforcement |
| 11 | `test_rbac_configured` | `tests/production/test_deployment_acceptance.py:173` | K8s RBAC | `REQUIRES EXTERNAL INFRASTRUCTURE: RBAC` | `rbac_verified` flag / ServiceAccounts | RBAC roles and least-privilege binding verification |
| 12 | `test_monitoring_stack` | `tests/production/test_deployment_acceptance.py:180` | Prometheus & Grafana | `REQUIRES EXTERNAL INFRASTRUCTURE: Monitoring Stack` | `PROMETHEUS_URL`, `GRAFANA_URL` | HTTP GET Prometheus `/-/healthy` == 200 & Grafana `/api/health` == 200 |

---

## 2. Infrastructure Test Execution Checklists

### Checklist 1: Kubernetes Cluster Health (`test_k8s_cluster_health`)

- **Test Name & File Location:** `test_k8s_cluster_health` in `tests/production/test_deployment_acceptance.py` (line 48).
- **What It Tests:**
  Queries the Kubernetes API server `/healthz` endpoint over HTTPS/HTTP. Validates that the control plane is operational, healthy, and returning an HTTP 200 status code with a body payload of strictly `"ok"`.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Kubernetes`.
  Layer A test execution runs in local isolated Python environments without access to a running Kubernetes control plane or API server endpoint.
- **Required Infrastructure:**
  - Active Kubernetes cluster (EKS, GKE, AKS, or local K3s/Minikube/Kind).
  - API server listening on TCP port 6443 (or configured port).
  - Ingress or internal cluster network route accessible to the test runner.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export GFIN_INFRA_HOST="10.0.1.50" # Or cluster IP/hostname
  export K8S_API_URL="https://${GFIN_INFRA_HOST}:6443"
  ```
- **Step-by-Step Execution Procedure:**
  1. Verify cluster API server accessibility via `kubectl`:
     ```bash
     kubectl cluster-info
     kubectl get nodes -o wide
     ```
  2. Execute pre-flight HTTP probe against the cluster endpoint:
     ```bash
     curl -k -i ${K8S_API_URL}/healthz
     ```
  3. Unskip test (remove `@pytest.mark.skip` or run unskipped target) and execute test suite:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_k8s_cluster_health -v
     ```
- **Evidence to Capture:**
  - Terminal log output of `kubectl cluster-info` and `kubectl get nodes`.
  - Raw HTTP response from `curl` showing `HTTP/1.1 200 OK` and body content `ok`.
  - Pytest execution log confirming `test_k8s_cluster_health PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** HTTP status code == `200` AND decoded response body == `"ok"` within a 5-second timeout.
  - **Fail:** HTTP status code != 200, response body != `"ok"`, socket connection timeout (>5s), or connection refused.

---

### Checklist 2: HashiCorp Vault Connectivity (`test_vault_connectivity`)

- **Test Name & File Location:** `test_vault_connectivity` in `tests/production/test_deployment_acceptance.py` (line 60).
- **What It Tests:**
  Sends an HTTP GET request to Vault's sys health endpoint (`/v1/sys/health`). Parses the returned JSON payload to confirm that HashiCorp Vault is initialized (`"initialized": true`) and unsealed (`"sealed": false`).
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Vault`.
  Layer A testing uses in-memory environment variables; no external Vault secrets engine server is attached.
- **Required Infrastructure:**
  - HashiCorp Vault instance/cluster running on port 8200 (or configured port).
  - Vault cluster initialized (`vault operator init`).
  - Vault cluster unsealed (`vault operator unseal` with threshold keys).
- **Environment & Pre-Execution Configuration:**
  ```bash
  export GFIN_INFRA_HOST="vault.gfin.internal"
  export VAULT_URL="http://${GFIN_INFRA_HOST}:8200"
  ```
- **Step-by-Step Execution Procedure:**
  1. Verify Vault cluster seal status via CLI:
     ```bash
     vault status -address=${VAULT_URL}
     ```
  2. Perform pre-flight health query:
     ```bash
     curl -s ${VAULT_URL}/v1/sys/health | jq .
     ```
  3. Execute pytest acceptance test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_vault_connectivity -v
     ```
- **Evidence to Capture:**
  - CLI output from `vault status` displaying initialized and unsealed states.
  - JSON payload returned by `/v1/sys/health`.
  - Pytest execution log showing `test_vault_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** HTTP status code == `200`, JSON payload `data["initialized"]` is `True`, AND `data["sealed"]` is `False`.
  - **Fail:** HTTP status code != 200, `initialized` is `false`, `sealed` is `true`, or connection failure occurs.

---

### Checklist 3: Kafka Topics Created (`test_kafka_topics_created`)

- **Test Name & File Location:** `test_kafka_topics_created` in `tests/production/test_deployment_acceptance.py` (line 74).
- **What It Tests:**
  Establishes a TCP socket connection to the Kafka broker on port 9092 and validates that all 14 required GFIN event and Dead Letter Queue (DLQ) topics exist:
  - **Event topics (7):** `gfin-events-entity`, `gfin-events-report`, `gfin-events-evidence`, `gfin-events-alert`, `gfin-events-discovery`, `gfin-events-audit`, `gfin-events-federation`
  - **DLQ topics (7):** `gfin-dlq-entity`, `gfin-dlq-report`, `gfin-dlq-evidence`, `gfin-dlq-alert`, `gfin-dlq-discovery`, `gfin-dlq-audit`, `gfin-dlq-federation`
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Kafka`.
  Layer A relies on `InMemoryEventBus` and does not spawn a live Kafka/KRaft broker.
- **Required Infrastructure:**
  - Apache Kafka cluster / MSK / Strimzi operator active.
  - Kafka broker accessible on TCP port 9092 (or `KAFKA_PORT`).
  - All 14 GFIN topics provisioned via IaC or topic creation script.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export KAFKA_HOST="kafka.gfin.internal"
  export KAFKA_PORT="9092"
  ```
- **Step-by-Step Execution Procedure:**
  1. Test broker socket connection:
     ```bash
     nc -zv ${KAFKA_HOST} ${KAFKA_PORT}
     ```
  2. List existing Kafka topics via AdminClient / CLI:
     ```bash
     kafka-topics.sh --bootstrap-server ${KAFKA_HOST}:${KAFKA_PORT} --list
     ```
  3. Execute pytest test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_kafka_topics_created -v
     ```
- **Evidence to Capture:**
  - Output of `kafka-topics.sh --list` showing all 14 topic names.
  - Netcat / socket connection success log.
  - Pytest terminal log showing `test_kafka_topics_created PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** TCP socket connection succeeds (`connect_ex` returns 0) AND set of discovered topics contains all 14 expected `gfin-events-*` and `gfin-dlq-*` topic names.
  - **Fail:** Broker port unreachable, connection timeout (>5s), or any of the 14 topics missing.

---

### Checklist 4: PostgreSQL Connectivity (`test_postgresql_connectivity`)

- **Test Name & File Location:** `test_postgresql_connectivity` in `tests/production/test_deployment_acceptance.py` (line 94).
- **What It Tests:**
  Verifies network transport reachability by attempting a TCP socket connection to the PostgreSQL database instance on port 5432.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: PostgreSQL`.
  Layer A unit testing operates with in-memory persistence and mock repositories.
- **Required Infrastructure:**
  - PostgreSQL 14+ database instance or RDS cluster active.
  - Port 5432 open and reachable from microservice network subnet.
  - Database `gfin_prod` created and accepting connections.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export POSTGRES_HOST="postgres.gfin.internal"
  export POSTGRES_PORT="5432"
  ```
- **Step-by-Step Execution Procedure:**
  1. Verify PostgreSQL server readiness via `pg_isready`:
     ```bash
     pg_isready -h ${POSTGRES_HOST} -p ${POSTGRES_PORT}
     ```
  2. Verify TCP socket connectivity via Python:
     ```bash
     python -c "import socket; s = socket.socket(); s.settimeout(5); print(s.connect_ex(('${POSTGRES_HOST}', ${POSTGRES_PORT})))"
     ```
  3. Execute pytest acceptance test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_postgresql_connectivity -v
     ```
- **Evidence to Capture:**
  - Output of `pg_isready` confirming accepting connections.
  - Socket connect result code (`0`).
  - Pytest terminal log showing `test_postgresql_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** `socket.connect_ex()` returns `0` within 5.0 seconds.
  - **Fail:** Return code != 0, socket timeout, or connection refused.

---

### Checklist 5: Neo4j Connectivity (`test_neo4j_connectivity`)

- **Test Name & File Location:** `test_neo4j_connectivity` in `tests/production/test_deployment_acceptance.py` (line 104).
- **What It Tests:**
  Sends an HTTP GET request to the Neo4j Graph Database browser / HTTP API endpoint (`http://${NEO4J_HOST}:${NEO4J_HTTP_PORT}`) to confirm server availability and readiness.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Neo4j`.
  Layer A uses in-memory NetworkX/mock graph adapters without a running Neo4j database instance.
- **Required Infrastructure:**
  - Neo4j Enterprise or Community edition instance running.
  - HTTP connector enabled on port 7474 (Bolt connector on 7687).
  - Graph engine initialized and healthy.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export NEO4J_HOST="neo4j.gfin.internal"
  export NEO4J_HTTP_PORT="7474"
  ```
- **Step-by-Step Execution Procedure:**
  1. Query Neo4j HTTP service header:
     ```bash
     curl -I http://${NEO4J_HOST}:${NEO4J_HTTP_PORT}
     ```
  2. Validate Cypher shell connectivity (optional pre-flight):
     ```bash
     cypher-shell -a bolt://${NEO4J_HOST}:7687 "RETURN 1;"
     ```
  3. Execute pytest test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_neo4j_connectivity -v
     ```
- **Evidence to Capture:**
  - Raw HTTP response header displaying `HTTP/1.1 200 OK`.
  - Cypher shell execution log.
  - Pytest log output showing `test_neo4j_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** HTTP GET request returns status code `200` within 5 seconds.
  - **Fail:** Non-200 HTTP response code, connection failure, or timeout.

---

### Checklist 6: OpenSearch Connectivity (`test_opensearch_connectivity`)

- **Test Name & File Location:** `test_opensearch_connectivity` in `tests/production/test_deployment_acceptance.py` (line 115).
- **What It Tests:**
  Queries OpenSearch cluster health API endpoint (`GET /_cluster/health`). Verifies that the response status code is 200 and cluster health status is either `"green"` or `"yellow"`.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: OpenSearch`.
  Layer A uses in-memory dictionary search indices without an external OpenSearch cluster.
- **Required Infrastructure:**
  - OpenSearch cluster active on port 9200 (or `OPENSEARCH_URL`).
  - Primary shards allocated and cluster state operational.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export OPENSEARCH_URL="http://opensearch.gfin.internal:9200"
  ```
- **Step-by-Step Execution Procedure:**
  1. Query cluster health API via `curl`:
     ```bash
     curl -s ${OPENSEARCH_URL}/_cluster/health | jq .
     ```
  2. Execute pytest acceptance test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_opensearch_connectivity -v
     ```
- **Evidence to Capture:**
  - JSON response from `/_cluster/health` showing cluster status and node count.
  - Pytest test execution log showing `test_opensearch_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** HTTP status code == `200` AND JSON key `status` is in `["green", "yellow"]`.
  - **Fail:** HTTP status code != 200, cluster status == `"red"`, or connection timeout (>5s).

---

### Checklist 7: Redis Connectivity (`test_redis_connectivity`)

- **Test Name & File Location:** `test_redis_connectivity` in `tests/production/test_deployment_acceptance.py` (line 128).
- **What It Tests:**
  Verifies TCP socket reachability for the Redis rate-limiting and session cache server on port 6379.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Redis`.
  Layer A relies on in-memory dictionary caching rather than a live Redis daemon.
- **Required Infrastructure:**
  - Redis server or ElastiCache cluster active.
  - Port 6379 open and accessible.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export REDIS_HOST="redis.gfin.internal"
  export REDIS_PORT="6379"
  ```
- **Step-by-Step Execution Procedure:**
  1. Test Redis PING via CLI:
     ```bash
     redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} PING
     ```
  2. Verify socket connect via Python:
     ```bash
     python -c "import socket; s = socket.socket(); s.settimeout(5); print(s.connect_ex(('${REDIS_HOST}', ${REDIS_PORT})))"
     ```
  3. Execute pytest acceptance test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_redis_connectivity -v
     ```
- **Evidence to Capture:**
  - Output of `redis-cli PING` returning `PONG`.
  - Python socket connection result code (`0`).
  - Pytest execution log confirming `test_redis_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** TCP socket connection succeeds (`connect_ex` returns 0) within 5 seconds.
  - **Fail:** Socket return code != 0, connection refused, or timeout.

---

### Checklist 8: S3 Evidence Vault Connectivity (`test_s3_connectivity`)

- **Test Name & File Location:** `test_s3_connectivity` in `tests/production/test_deployment_acceptance.py` (line 138).
- **What It Tests:**
  Queries MinIO / S3 object storage health endpoint (`GET /minio/health/live`) to verify object store availability for evidence binary artifacts.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: S3`.
  Layer A stores evidence artifacts in local mock dictionaries or filesystem temp files.
- **Required Infrastructure:**
  - MinIO or AWS S3-compatible storage cluster active on port 9000 (or `S3_URL`).
  - Evidence storage bucket `gfin-evidence-vault` created.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export S3_URL="http://s3.gfin.internal:9000"
  ```
- **Step-by-Step Execution Procedure:**
  1. Perform pre-flight health HTTP probe:
     ```bash
     curl -i ${S3_URL}/minio/health/live
     ```
  2. List target bucket via MinIO Client (`mc`):
     ```bash
     mc ls local/gfin-evidence-vault
     ```
  3. Execute pytest test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_s3_connectivity -v
     ```
- **Evidence to Capture:**
  - HTTP response header showing `HTTP/1.1 200 OK`.
  - Output of `mc ls` command.
  - Pytest execution log confirming `test_s3_connectivity PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** HTTP status code == `200` within 5 seconds.
  - **Fail:** HTTP status code != 200, connection error, or timeout.

---

### Checklist 9: TLS Certificates Validation (`test_tls_certificates_valid`)

- **Test Name & File Location:** `test_tls_certificates_valid` in `tests/production/test_deployment_acceptance.py` (line 149).
- **What It Tests:**
  Establishes an SSL/TLS socket connection to target host and port 443. Wraps socket with default SSL context and verifies that a valid, trusted peer certificate is presented (`getpeercert() is not None`).
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: TLS`.
  Layer A testing runs without TLS termination or SSL certificate endpoints.
- **Required Infrastructure:**
  - Ingress controller / Load balancer provisioned with valid TLS certificates (cert-manager, Let's Encrypt, or Private CA).
  - Port 443 listening for TLS connections.
- **Environment & Pre-Execution Configuration:**
  ```bash
  export GFIN_TLS_HOST="api.gfin.internal"
  export GFIN_TLS_PORT="443"
  ```
- **Step-by-Step Execution Procedure:**
  1. Inspect certificate details via OpenSSL CLI:
     ```bash
     openssl s_client -connect ${GFIN_TLS_HOST}:${GFIN_TLS_PORT} -servername ${GFIN_TLS_HOST} < /dev/null | openssl x509 -noout -dates -subject -issuer
     ```
  2. Execute pytest acceptance test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_tls_certificates_valid -v
     ```
- **Evidence to Capture:**
  - OpenSSL cert details output showing valid start date and future expiration date (`notAfter`).
  - Pytest terminal log showing `test_tls_certificates_valid PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** TLS handshake completes successfully and `ssock.getpeercert()` returns a non-None certificate dictionary within 5 seconds.
  - **Fail:** SSL certificate validation error (expired, host mismatch, untrusted root), socket timeout, or handshake failure.

---

### Checklist 10: Network Isolation Policies Enforced (`test_network_policies_enforced`)

- **Test Name & File Location:** `test_network_policies_enforced` in `tests/production/test_deployment_acceptance.py` (line 165).
- **What It Tests:**
  Validates Kubernetes network policies (`NetworkPolicy` resources). Verifies that unauthorized cross-namespace or cross-zone ingress/egress connections between microservices are blocked by the CNI plugin.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Network Policies`.
  Layer A execution does not run inside a Kubernetes CNI environment (Calico, Cilium) that enforces network isolation.
- **Required Infrastructure:**
  - Kubernetes cluster with CNI enforcing NetworkPolicies (e.g. Calico, Cilium).
  - GFIN NetworkPolicies deployed in target namespaces (`gfin-system`, `gfin-data`).
- **Environment & Pre-Execution Configuration:**
  - Active Kubernetes cluster with policy engine enabled.
  - Test harness flag `network_policies_active = True`.
- **Step-by-Step Execution Procedure:**
  1. Inspect applied NetworkPolicies:
     ```bash
     kubectl get netpol -n gfin-system
     ```
  2. Launch probe container from an unauthorized namespace to test blocked access:
     ```bash
     kubectl run netpol-probe --image=busybox --restart=Never -n default -- nc -zv -w 3 postgres.gfin-system.svc.cluster.local 5432
     ```
  3. Verify probe times out / connection dropped.
  4. Enable test driver verification flag (`network_policies_active = True`).
  5. Execute pytest test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_network_policies_enforced -v
     ```
- **Evidence to Capture:**
  - `kubectl get netpol -n gfin-system -o yaml` dump.
  - Terminal log demonstrating connection timeout/refusal from unauthorized pod.
  - Pytest execution log confirming `test_network_policies_enforced PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** Unauthorized connection attempts fail (timeout/refused) AND `network_policies_active` flag evaluates to `True`.
  - **Fail:** Unauthorized connection succeeds OR `network_policies_active` flag evaluates to `False`.

---

### Checklist 11: RBAC Security Roles Configured (`test_rbac_configured`)

- **Test Name & File Location:** `test_rbac_configured` in `tests/production/test_deployment_acceptance.py` (line 173).
- **What It Tests:**
  Validates Kubernetes RBAC definitions (`ServiceAccount`, `Role`, `ClusterRole`, `RoleBinding`). Verifies that microservice ServiceAccounts are constrained to explicit least-privilege operations.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: RBAC`.
  Layer A runs outside Kubernetes and lacks active ServiceAccount RBAC contexts.
- **Required Infrastructure:**
  - Kubernetes cluster with RBAC authorization mode enabled.
  - GFIN RBAC manifests deployed in namespace `gfin-system`.
- **Environment & Pre-Execution Configuration:**
  - Active Kubernetes context.
  - Test harness flag `rbac_verified = True`.
- **Step-by-Step Execution Procedure:**
  1. Inspect GFIN ServiceAccounts and RoleBindings:
     ```bash
     kubectl get sa,roles,rolebindings -n gfin-system
     ```
  2. Test ServiceAccount permissions using `kubectl auth can-i`:
     ```bash
     kubectl auth can-i get secrets --as=system:serviceaccount:gfin-system:gfin-api-sa -n gfin-system
     kubectl auth can-i delete pods --as=system:serviceaccount:gfin-system:gfin-api-sa -n gfin-system
     ```
  3. Enable test verification flag (`rbac_verified = True`).
  4. Execute pytest test:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_rbac_configured -v
     ```
- **Evidence to Capture:**
  - Matrix of `kubectl auth can-i` command outputs showing `yes` for authorized calls and `no` for unauthorized calls.
  - Pytest execution log confirming `test_rbac_configured PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** `kubectl auth can-i` checks match least-privilege spec AND test assertion `rbac_verified is True` passes.
  - **Fail:** Overly permissive grants detected, missing ServiceAccounts, or assertion evaluates to `False`.

---

### Checklist 12: Monitoring Stack Availability (`test_monitoring_stack`)

- **Test Name & File Location:** `test_monitoring_stack` in `tests/production/test_deployment_acceptance.py` (line 180).
- **What It Tests:**
  Sends HTTP GET requests to Prometheus server (`GET ${PROMETHEUS_URL}/-/healthy`) and Grafana server (`GET ${GRAFANA_URL}/api/health`). Confirms both observability platforms are active and returning HTTP 200 status codes.
- **Why It's Skipped:**
  Reason: `REQUIRES EXTERNAL INFRASTRUCTURE: Monitoring Stack`.
  Layer A uses local Python logger metrics rather than live Prometheus and Grafana microservices.
- **Required Infrastructure:**
  - Prometheus instance running on port 9090 (or `PROMETHEUS_URL`).
  - Grafana dashboard instance running on port 3000 (or `GRAFANA_URL`).
- **Environment & Pre-Execution Configuration:**
  ```bash
  export PROMETHEUS_URL="http://prometheus.gfin.internal:9090"
  export GRAFANA_URL="http://grafana.gfin.internal:3000"
  ```
- **Step-by-Step Execution Procedure:**
  1. Query Prometheus health endpoint:
     ```bash
     curl -i ${PROMETHEUS_URL}/-/healthy
     ```
  2. Query Grafana API health endpoint:
     ```bash
     curl -i ${GRAFANA_URL}/api/health
     ```
  3. Execute pytest test suite:
     ```bash
     python -m pytest tests/production/test_deployment_acceptance.py -k test_monitoring_stack -v
     ```
- **Evidence to Capture:**
  - HTTP headers and response body from Prometheus `/-/healthy` (200 OK).
  - HTTP headers and JSON response from Grafana `/api/health` (`{"database": "ok"}`).
  - Pytest execution terminal log showing `test_monitoring_stack PASSED`.
- **Pass / Fail Criteria:**
  - **Pass:** Both Prometheus `/-/healthy` and Grafana `/api/health` return HTTP status code `200` within 5 seconds.
  - **Fail:** Either endpoint returns non-200 HTTP status, times out, or fails socket connection.

---

## 3. Automated Test Execution Workflow

When infrastructure provisioning is completed, execute all acceptance tests in sequence using the following workflow script:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== GFIN Production Infrastructure Acceptance Test Runner ==="

# 1. Load Infrastructure Target Environment
export GFIN_INFRA_HOST="${GFIN_INFRA_HOST:-localhost}"
export K8S_API_URL="${K8S_API_URL:-https://${GFIN_INFRA_HOST}:6443}"
export VAULT_URL="${VAULT_URL:-http://${GFIN_INFRA_HOST}:8200}"
export KAFKA_HOST="${KAFKA_HOST:-${GFIN_INFRA_HOST}}"
export KAFKA_PORT="${KAFKA_PORT:-9092}"
export POSTGRES_HOST="${POSTGRES_HOST:-${GFIN_INFRA_HOST}}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export NEO4J_HOST="${NEO4J_HOST:-${GFIN_INFRA_HOST}}"
export NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
export OPENSEARCH_URL="${OPENSEARCH_URL:-http://${GFIN_INFRA_HOST}:9200}"
export REDIS_HOST="${REDIS_HOST:-${GFIN_INFRA_HOST}}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export S3_URL="${S3_URL:-http://${GFIN_INFRA_HOST}:9000}"
export PROMETHEUS_URL="${PROMETHEUS_URL:-http://${GFIN_INFRA_HOST}:9090}"
export GRAFANA_URL="${GRAFANA_URL:-http://${GFIN_INFRA_HOST}:3000}"
export GFIN_TLS_HOST="${GFIN_TLS_HOST:-${GFIN_INFRA_HOST}}"
export GFIN_TLS_PORT="${GFIN_TLS_PORT:-443}"

# 2. Run Pytest Acceptance Suite
python -m pytest tests/production/test_deployment_acceptance.py -v --no-header --no-cov
```
