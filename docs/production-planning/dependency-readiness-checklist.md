# GFIN Infrastructure Dependency Readiness Checklist

**Document ID:** GFIN-DRC-001  
**Project:** Global Fraud Intelligence Network (GFIN)  
**Status:** DRAFT — REQUIRES EXTERNAL INFRASTRUCTURE  
**Last Updated:** 2026-08-26  

---

## 1. Overview & Architecture Strategy

This document details the dependency readiness checklist required to transition GFIN from Layer A (in-memory MVP) to Layer B (live production infrastructure).

All infrastructure components listed below are currently **NOT DEPLOYED** and require external infrastructure provisioning, Kubernetes deployment, and validation before application services can be enabled.

---

## 2. Dependency Order & Critical Path

### 2.1 Dependency Ordering Matrix

Deploying GFIN infrastructure must strictly follow a sequence based on prerequisite dependencies:

```
Step 1: Core Platform Infrastructure
  └── Kubernetes (K8s Cluster & Namespace)
       │
       ├──► Step 2: Secrets Management & Security Infrastructure
       │      └── HashiCorp Vault (HA Raft Cluster)
       │           │
       │           ├──► Step 3: Core Storage & Caching Layer
       │           │      ├── PostgreSQL 16 (Primary + Replicas)
       │           │      ├── Redis 7.x (Sentinel / Cluster)
       │           │      └── MinIO / S3 Object Storage
       │           │
       │           └──► Step 4: Distributed Streaming & Search Infrastructure
       │                  ├── Strimzi Kafka Operator & Cluster (14 Topics)
       │                  ├── Neo4j 5.x Graph Database
       │                  └── OpenSearch 2.x Cluster
       │
       └──► Step 5: Observability & Application Layer
              ├── Prometheus & Grafana Monitoring Stack
              └── GFIN Application Microservices
```

### 2.2 Critical Path Identification

The critical path for deployment blocking all application workload startup is:
`Kubernetes Cluster -> HashiCorp Vault -> PostgreSQL & Redis -> Strimzi Kafka Operator -> Kafka Topics -> Application Services`

- **Primary Bottleneck:** HashiCorp Vault. No application or database component can start without Vault initializing database credentials, TLS certificates, and API tokens.
- **Secondary Bottleneck:** Strimzi Kafka Operator. Event-driven components (Alert Engine, Entity Resolver, Audit Writer, Federation Sync) cannot start without Kafka topic CRDs initialized.

---

## 3. Infrastructure Component Checklists

---

### 3.1 Kubernetes (K8s) Cluster

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Kubernetes cluster v1.28+ provisioned (EKS, GKE, or Bare Metal)
- Minimum 3 worker nodes (8 vCPU, 32GB RAM per node)
- `kubectl` and `helm` v3+ configured with cluster admin rights
- Ingress controller (NGINX or AWS ALB Controller) installed
- Cert-Manager installed for automated TLS provisioning

#### Deployment Steps
1. Apply GFIN namespace definition: `kubectl apply -f infrastructure/kubernetes/namespace.yaml`
2. Configure Network Policies for zone isolation.
3. Apply ServiceAccounts and RBAC roles: `kubectl apply -f infrastructure/kubernetes/rbac.yaml`
4. Deploy API Gateway ingress: `kubectl apply -f infrastructure/kubernetes/api-gateway.yaml`

#### Verification Steps
- Confirm namespace `gfin` exists and active.
- Confirm all nodes are in `Ready` state.
- Confirm ingress controller is assigned an external IP / DNS name.

#### Health Check Commands
```bash
kubectl get nodes -o wide
kubectl get ns gfin
kubectl get pods -n gfin
kubectl auth can-i create pods --as=system:serviceaccount:gfin:gfin-app -n gfin
```

#### Rollback Procedure
```bash
kubectl delete -f infrastructure/kubernetes/api-gateway.yaml
kubectl delete -f infrastructure/kubernetes/namespace.yaml
```

#### Go / No-Go Checklist
- [ ] Cluster node status is 100% Ready across all nodes.
- [ ] Ingress controller active with ingress IP allocated.
- [ ] Namespace `gfin` created with resource quotas applied.
- [ ] RBAC policies restrict non-admin access.

---

### 3.2 HashiCorp Vault

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Kubernetes cluster ready (`gfin` namespace active).
- StorageClass supporting persistent volume claims (PVC) with high IOPS.
- Vault Helm repository added (`helm repo add hashicorp https://helm.releases.hashicorp.com`).

#### Deployment Steps
1. Deploy HA Vault cluster using Raft storage backend via Helm.
2. Initialize Vault cluster and securely store unseal keys and root token in Key Management Service (KMS).
3. Unseal Vault pods.
4. Enable KV v2 secret engine at `gfin/data/` and database dynamic secrets engine.
5. Configure Vault Kubernetes Authentication method for `gfin` service accounts.

#### Verification Steps
- Check Vault status shows initialized and unsealed (`vault status`).
- Retrieve test secret via Vault CLI or REST API using Kubernetes Auth token.

#### Health Check Commands
```bash
kubectl exec -it vault-0 -n gfin -- vault status
curl -s http://vault.gfin.svc.cluster.local:8200/v1/sys/health | jq .
```

#### Rollback Procedure
```bash
helm uninstall vault -n gfin
kubectl delete pvc -l app.kubernetes.io/name=vault -n gfin
```

#### Go / No-Go Checklist
- [ ] Vault quorum active across 3 replicas.
- [ ] Vault unsealed and auto-unseal configured via KMS.
- [ ] Kubernetes auth method enabled and verified.
- [ ] Database dynamic secret engine configured.

---

### 3.3 Apache Kafka & Strimzi Operator

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Vault active and issuing SASL credentials.
- Strimzi Custom Resource Definitions (CRDs) installed (`v0.38+`).
- StorageClass capable of allocating persistent volumes for Kafka brokers.

#### Deployment Steps
1. Deploy Strimzi Kafka Operator in `gfin` namespace.
2. Deploy Kafka Cluster custom resource (`gfin-kafka`, 3 brokers, SCRAM-SHA-512 authentication, TLS encryption).
3. Apply topic definitions from `infrastructure/kafka/kafka-topics.yaml` (14 topics).
4. Apply KafkaUser definitions for service authorization.

#### Verification Steps
- Verify 3 Kafka broker pods and Zookeeper/KRaft pods are `Running`.
- Verify all 14 topics are created (`kubectl get kafkatopic -n gfin`).
- Test producing and consuming a message using test KafkaUser credentials.

#### Health Check Commands
```bash
kubectl get kafka -n gfin
kubectl get kafkatopic -n gfin --no-headers | wc -l # Must equal 14
kubectl get kafkauser -n gfin
```

#### Rollback Procedure
```bash
kubectl delete -f infrastructure/kafka/kafka-topics.yaml -n gfin
kubectl delete kafka gfin-kafka -n gfin
helm uninstall strimzi-kafka-operator -n gfin
```

#### Go / No-Go Checklist
- [ ] Strimzi operator running with 0 restarts.
- [ ] Kafka cluster state is `Ready` with 3 brokers online.
- [ ] Exactly 14 Kafka topics (7 event topics, 7 DLQ topics) exist and report `Ready`.
- [ ] KafkaUser authentication via SCRAM-SHA-512 verified.

---

### 3.4 PostgreSQL 16

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Vault dynamic secrets enabled for PostgreSQL.
- Fast NVMe StorageClass for database data directories.

#### Deployment Steps
1. Deploy PostgreSQL operator (e.g., CloudNativePG or Zalando Postgres Operator) or HA Helm chart.
2. Provision Primary PostgreSQL 16 instance with 2 read replicas.
3. Configure WAL archiving to S3 for Point-in-Time Recovery (PITR).
4. Execute Alembic schema migrations: `alembic upgrade head`.

#### Verification Steps
- Connect to primary PostgreSQL and verify read/write access.
- Check schema tables exist (`users`, `reports`, `audit_logs`, `entities`, etc.).
- Verify replication status across read replicas.

#### Health Check Commands
```bash
kubectl exec -it gfin-postgres-1 -n gfin -- pg_isready -U gfin_admin
kubectl exec -it gfin-postgres-1 -n gfin -- psql -U gfin_admin -d gfin -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

#### Rollback Procedure
```bash
kubectl delete postgresql gfin-postgres -n gfin
# Restore snapshot from S3 if performing rollback during upgrade
```

#### Go / No-Go Checklist
- [ ] Primary database accepts connections and reads/writes.
- [ ] 2 read replicas synchronized with replication lag < 10ms.
- [ ] Database schema migrations applied up to latest revision.
- [ ] Automated continuous WAL archiving to S3 operational.

---

### 3.5 Neo4j 5.x Graph Database

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Persistent storage provisioned.
- Vault password secret populated at `gfin/data/neo4j`.

#### Deployment Steps
1. Deploy Neo4j 5.x Causal Cluster (3 core nodes) via Helm or K8s StatefulSet.
2. Initialize APOC (Awesome Procedures on Cypher) plugin and GDS (Graph Data Science) library.
3. Apply graph constraints and indexes for entity resolution (e.g., `Campaign`, `Entity`, `Indicator` nodes).

#### Verification Steps
- Access Cypher shell on `neo4j-0` pod.
- Execute test write query: `CREATE (n:TestNode {id: 'check'}) RETURN n;`
- Execute cleanup query: `MATCH (n:TestNode) DELETE n;`

#### Health Check Commands
```bash
kubectl exec -it neo4j-0 -n gfin -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "SHOW DB;"
curl -s -I http://neo4j.gfin.svc.cluster.local:7474
```

#### Rollback Procedure
```bash
helm uninstall neo4j -n gfin
kubectl delete pvc -l app=neo4j -n gfin
```

#### Go / No-Go Checklist
- [ ] Neo4j Causal Cluster fully formed (3 nodes in consensus).
- [ ] APOC and GDS plugins loaded and functional.
- [ ] Entity graph uniqueness constraints and indexes initialized.
- [ ] Cypher query latency within target (< 20ms for 2-hop traversal).

---

### 3.6 OpenSearch 2.x Cluster

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- StorageClass supporting high write IOPS.
- Vault credentials configured for OpenSearch index management.

#### Deployment Steps
1. Deploy OpenSearch 2.x 3-node cluster with Security Plugin enabled.
2. Configure cluster settings and heap memory allocations.
3. Create GFIN search index templates and lifecycle management policies (`gfin-reports`, `gfin-entities`, `gfin-audit`).

#### Verification Steps
- Query OpenSearch cluster health REST endpoint (`GET /_cluster/health`).
- Verify index creation and mapping accuracy.
- Test indexing a sample document and executing a search query.

#### Health Check Commands
```bash
curl -k -u admin:"$OPENSEARCH_PASSWORD" https://opensearch.gfin.svc.cluster.local:9200/_cluster/health?pretty
curl -k -u admin:"$OPENSEARCH_PASSWORD" https://opensearch.gfin.svc.cluster.local:9200/_cat/indices
```

#### Rollback Procedure
```bash
helm uninstall opensearch -n gfin
kubectl delete pvc -l app=opensearch -n gfin
```

#### Go / No-Go Checklist
- [ ] Cluster status is `GREEN` with 3 nodes active.
- [ ] Search indices created with correct mappings and aliases.
- [ ] Security plugin active with TLS enforcement.
- [ ] Automated snapshot repository connected to S3.

---

### 3.7 Redis 7.x Cache & Rate Limiter

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- Persistent storage for RDB/AOF persistence.
- Vault secret at `gfin/data/redis` containing password.

#### Deployment Steps
1. Deploy Redis 7.x Sentinel or Cluster mode (3 master / 3 replica topology).
2. Configure maxmemory policies (`volatile-lru`) and persistence (AOF everysec).
3. Secure Redis with TLS and password authentication.

#### Verification Steps
- Execute `PING` command via `redis-cli` with auth password.
- Test key SET/GET and EXPIRE operations.

#### Health Check Commands
```bash
kubectl exec -it redis-0 -n gfin -- redis-cli -a "$REDIS_PASSWORD" ping
kubectl exec -it redis-0 -n gfin -- redis-cli -a "$REDIS_PASSWORD" info replication
```

#### Rollback Procedure
```bash
helm uninstall redis -n gfin
kubectl delete pvc -l app=redis -n gfin
```

#### Go / No-Go Checklist
- [ ] Redis Sentinel / Cluster reporting healthy quorum.
- [ ] Master-replica replication latency < 1ms.
- [ ] Rate limiting key eviction policy (`volatile-lru`) confirmed.
- [ ] Authenticated connection via TLS verified.

---

### 3.8 S3-Compatible Object Storage (MinIO / AWS S3)

- [ ] Status: NOT DEPLOYED

#### Prerequisites
- S3 access key and secret key in Vault (`gfin/data/s3`).
- Bucket lifecycle policies defined for evidence preservation.

#### Deployment Steps
1. Provision S3 buckets or deploy MinIO Enterprise operator on Kubernetes.
2. Provision buckets: `gfin-evidence-vault`, `gfin-backups`, `gfin-audit-archive`.
3. Enable Object Locking (WORM — Write Once Read Many) on `gfin-evidence-vault`.
4. Enable KMS encryption at rest (SSE-KMS / SSE-S3).

#### Verification Steps
- Upload test object to `gfin-evidence-vault`.
- Download test object and verify hash match.
- Attempt object deletion/overwrite on locked bucket and verify refusal.

#### Health Check Commands
```bash
aws --endpoint-url https://s3.gfin.svc.cluster.local s3 ls s3://gfin-evidence-vault
curl -s -I https://s3.gfin.svc.cluster.local/minio/health/live
```

#### Rollback Procedure
```bash
# Clean up test buckets if dry run, otherwise preserve data
aws --endpoint-url https://s3.gfin.svc.cluster.local s3 rb s3://gfin-evidence-vault --force
```

#### Go / No-Go Checklist
- [ ] Buckets `gfin-evidence-vault`, `gfin-backups`, `gfin-audit-archive` initialized.
- [ ] Object Locking (WORM) enabled on evidence vault.
- [ ] Server-Side Encryption (SSE) active.
- [ ] Cross-region replication or offline backup sync operational.

---

## 4. Overall Deployment Readiness Go / No-Go Summary

Before executing application service startup (`gfin-api`, `gfin-worker`, `gfin-alert-engine`), all 8 infrastructure component checklists must be 100% complete and signed off:

| Component | Status | Required Criteria | Sign-Off |
| :--- | :--- | :--- | :--- |
| Kubernetes | NOT DEPLOYED | Nodes ready, RBAC active, namespace quotas set | `[ ]` |
| Vault | NOT DEPLOYED | Unsealed, HA raft quorum, K8s auth active | `[ ]` |
| Kafka / Strimzi | NOT DEPLOYED | 3 brokers, 14 topics ready, SCRAM-SHA-512 auth | `[ ]` |
| PostgreSQL | NOT DEPLOYED | Primary + 2 replicas, Alembic migrations done | `[ ]` |
| Neo4j | NOT DEPLOYED | 3 core nodes, Cypher shell ready, constraints set | `[ ]` |
| OpenSearch | NOT DEPLOYED | 3 nodes GREEN, index templates loaded | `[ ]` |
| Redis | NOT DEPLOYED | Master-replica quorum, TLS & Auth verified | `[ ]` |
| S3 Object Storage | NOT DEPLOYED | Buckets ready, Object Locking enabled | `[ ]` |

**Final Decision:** **NO-GO** (Pending infrastructure provisioning)
