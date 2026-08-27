# GFIN Infrastructure Mobilization Package

**Document ID:** GFIN-IMP-001  
**Directive:** Luna Strategic Directive — Step 2: Infrastructure Mobilization  
**Status:** DRAFT — REQUIRES EXTERNAL INFRASTRUCTURE  
**Date:** 2026-08-26  

---

## 1. Purpose

This document converts the Layer B infrastructure definitions into an actionable mobilization package for the external infrastructure team. It defines ownership, environment specifications, IaC structure, configuration contracts, and provisioning requirements.

**All infrastructure described herein is REQUIRES EXTERNAL INFRASTRUCTURE — not deployed, not claimed as deployed.**

---

## 2. Ownership Matrix

### 2.1 Infrastructure Component Owners

| Component | Technology | Primary Owner | Backup Owner | Provisioning Method | Target Environment |
|-----------|-----------|---------------|--------------|---------------------|-------------------|
| Kubernetes Cluster | K8s v1.28+ | Platform Team | DevOps | EKS/GKE Terraform module | All envs |
| Secrets Management | HashiCorp Vault HA | Security Team | Platform | Helm + Raft cluster | staging, prod |
| Relational DB | PostgreSQL 16 | Data Team | DevOps | Terraform RDS module | All envs |
| Graph DB | Neo4j 5.x | Data Team | DevOps | Helm chart | staging, prod |
| Search | OpenSearch 2.x | Data Team | DevOps | Terraform module | staging, prod |
| Cache | Redis 7.x | Platform Team | DevOps | Helm chart | All envs |
| Object Storage | S3 / MinIO | Platform Team | DevOps | Terraform S3 module | All envs |
| Event Streaming | Strimzi Kafka | Platform Team | DevOps | Helm + CRDs | staging, prod |
| Monitoring | Prometheus + Grafana | DevOps | Platform | Helm stack | All envs |
| Tracing | OpenTelemetry Collector | DevOps | Platform | Helm chart | All envs |

### 2.2 Application Service Owners

| Service | Module | Owner | Dependencies |
|---------|--------|-------|-------------|
| API Gateway | 01 | Platform | K8s, Vault, Redis |
| Auth Service | 01 | Security | Vault, PostgreSQL, Redis |
| Entity Resolution | 04 | Data | PostgreSQL, Neo4j, Kafka |
| Event Bus | 05 | Platform | Kafka |
| Evidence Vault | 06 | Data | S3, PostgreSQL, Kafka |
| Search Service | 07 | Data | OpenSearch, PostgreSQL |
| Web Discovery | 08 | Data | Kafka, S3, Redis |
| Infra Intelligence | 09 | Data | PostgreSQL, Kafka |
| Domain Intel | 10 | Data | PostgreSQL, Neo4j |
| Citizen Platform | 13 | App | PostgreSQL, Redis, Kafka |
| Fraud Reporting | 14 | App | PostgreSQL, Kafka, Neo4j |
| Fraud Detection | 15 | App | Kafka, PostgreSQL, AI Gateway |
| Campaign Engine | 16 | App | Neo4j, Kafka, PostgreSQL |
| Continuous Monitoring | 17 | App | Kafka, PostgreSQL |
| Alert Engine | 18 | App | Kafka, Redis, PostgreSQL |
| AI Model Gateway | 19-20 | AI | OpenAI API, Local AI |
| Local AI | 21 | AI | GPU nodes (prod) |
| AI Investigation | 22 | AI | AI Gateway, Neo4j, Evidence |
| Police API | 23 | Security | PostgreSQL, Audit, Kafka |
| Police Connector SDK | 24 | Integration | External systems, Kafka |
| Global Matching | 25 | Federation | Neo4j, Kafka, PostgreSQL |
| Cross-Border Requests | 26 | Federation | PostgreSQL, Audit, Kafka |
| Police Console | 27 | App | PostgreSQL, Redis |
| Crypto Intelligence | 28 | Data | External APIs, PostgreSQL |
| Multilingual | 29 | App | AI Gateway, Redis |
| Analytics | 30 | App | PostgreSQL, Redis |
| Global Early Warning | 31 | App | Kafka, PostgreSQL, Alert Engine |
| Federation | 32 | Federation | Kafka, PostgreSQL, mTLS |
| Compliance | 33 | Security | PostgreSQL, Redis |
| Observability | 34 | DevOps | Prometheus, Grafana, OTel |
| Disaster Recovery | 35 | DevOps | All storage components |

---

## 3. Environment Specifications

### 3.1 Environment Tiers

| Environment | Purpose | K8s | Vault | Kafka | Neo4j | OpenSearch | Redis | PostgreSQL | S3 |
|-------------|---------|-----|-------|-------|-------|-----------|-------|-----------|---|
| **dev** | Developer testing | single-node | dev | embedded | embedded | embedded | single | single | MinIO |
| **staging** | Integration testing | 3-node | HA (3) | 3-broker | single | 2-node | sentinel | primary+replica | MinIO |
| **pilot** | Limited production | 3-node | HA (3) | 3-broker | HA (3) | 3-node | cluster | primary+2rep | S3 |
| **production** | Full deployment | 5+ node | HA (5) | 5+ broker | HA (3+) | 3+ node | cluster | primary+3rep | S3 |

### 3.2 Environment Configuration Contracts

#### dev (Layer A equivalent)
```yaml
environment: dev
mode: in-memory
persistence: none
kafka: embedded (in-memory pub/sub)
database: in-memory repositories
search: in-memory index
graph: in-memory adjacency list
cache: in-memory dict
storage: local filesystem
ai_gateway: mock responses
```

#### staging
```yaml
environment: staging
mode: hybrid (Layer A + B)
persistence: real
kafka: 3-broker Strimzi
database: PostgreSQL 16 primary+replica
search: OpenSearch 2-node
graph: Neo4j single
cache: Redis sentinel
storage: MinIO
ai_gateway: OpenAI (test key)
monitoring: full stack
tracing: OpenTelemetry → Jaeger
```

#### pilot
```yaml
environment: pilot
mode: production-like
kafka: 3-broker Strimzi with TLS
database: PostgreSQL 16 primary+2 replicas
search: OpenSearch 3-node
graph: Neo4j HA (3 core)
cache: Redis cluster (6 nodes)
storage: S3 with encryption
ai_gateway: OpenAI (production key)
monitoring: full stack + alerting
tracing: OpenTelemetry → Jaeger
security: mTLS, network policies, OPA
```

#### production
```yaml
environment: production
mode: full production
kafka: 5+ broker Strimzi with TLS + mTLS
database: PostgreSQL 16 primary+3 replicas + connection pooling
search: OpenSearch 3+ node with dedicated masters
graph: Neo4j HA (3+ core, read replicas)
cache: Redis cluster (6+ nodes, persistence)
storage: S3 with KMS encryption + lifecycle policies
ai_gateway: OpenAI + Local AI (GPU nodes)
monitoring: full stack + PagerDuty integration
tracing: OpenTelemetry → Tempo
security: mTLS, network policies, OPA, Falco, admission controllers
backup: automated daily + continuous WAL
dr: cross-region replication
```

---

## 4. IaC Repository Structure

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── eks-cluster/          # K8s cluster provisioning
│   │   ├── vault/                # HashiCorp Vault HA
│   │   ├── rds-postgres/         # PostgreSQL RDS
│   │   ├── opensearch/           # OpenSearch cluster
│   │   ├── elasticache-redis/    # Redis cluster
│   │   ├── s3-bucket/            # S3 storage with encryption
│   │   └── networking/           # VPC, subnets, security groups
│   ├── environments/
│   │   ├── dev/                  # Dev environment TF vars
│   │   ├── staging/              # Staging environment TF vars
│   │   ├── pilot/                # Pilot environment TF vars
│   │   └── production/           # Production TF vars
│   └── shared/
│       └── modules.tf            # Shared module definitions
├── helm/
│   ├── gfin-core/                # Core services Helm chart
│   ├── gfin-data/                # Data services Helm chart
│   ├── gfin-security/            # Security services Helm chart
│   ├── strimzi-kafka/            # Kafka operator + cluster
│   ├── neo4j/                    # Neo4j Helm chart
│   ├── opensearch/               # OpenSearch Helm chart
│   ├── vault/                    # Vault Helm chart
│   ├── monitoring/               # Prometheus + Grafana stack
│   └── opentelemetry/            # OTel collector
├── kubernetes/
│   ├── namespace.yaml             # GFIN namespace
│   ├── rbac.yaml                  # ServiceAccounts + RBAC roles
│   ├── network-policies.yaml     # Zone isolation policies
│   ├── api-gateway.yaml           # Ingress + API Gateway
│   ├── secrets.yaml              # External secrets (Vault integration)
│   ├── poddisruptionbudgets.yaml # PDBs for HA
│   └── hpa.yaml                   # Horizontal Pod Autoscalers
├── strimzi/
│   ├── kafka-cluster.yaml         # Kafka cluster CRD
│   ├── kafka-topics.yaml          # 14 topic definitions
│   ├── kafka-users.yaml          # SCRAM users per service
│   └── kafka-connectors.yaml      # Connectors for external systems
└── scripts/
    ├── deploy.sh                  # Orchestrated deployment script
    ├── verify.sh                  # Post-deployment verification
    ├── rollback.sh                # Rollback procedure
    └── rotate-secrets.sh          # Secret rotation
```

---

## 5. Network Architecture

### 5.1 Zone Model

```
┌─────────────────────────────────────────────────────────────┐
│                     GFIN Network Zones                       │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Public    │  │  Private    │  │   Data      │        │
│  │   Zone      │  │   Zone      │  │   Zone      │        │
│  │             │  │             │  │             │        │
│  │ - API GW    │  │ - Auth Svc  │  │ - Postgres  │        │
│  │ - Citizen   │  │ - Entity    │  │ - Neo4j     │        │
│  │   Portal    │  │   Resolver  │  │ - OpenSearch│        │
│  │ - CDN       │  │ - Evidence  │  │ - Redis     │        │
│  │             │  │ - Search    │  │ - S3/MinIO  │        │
│  │             │  │ - Alert Eng │  │ - Kafka     │        │
│  │             │  │ - AI GW     │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                 │               │
│         └────────────────┼─────────────────┘               │
│                          │                                 │
│                    ┌─────┴─────┐                           │
│                    │  Security │                           │
│                    │   Zone    │                           │
│                    │           │                           │
│                    │ - Vault   │                           │
│                    │ - Audit   │                           │
│                    │ - OPA     │                           │
│                    │ - Falco   │                           │
│                    └───────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Network Policies

| Source Zone | Destination Zone | Allowed Ports | Protocol |
|-------------|-----------------|---------------|----------|
| Public | Private | 8080 (API GW) | HTTPS |
| Private | Data | 5432, 7687, 9200, 6379, 9092, 443 | mTLS |
| Private | Security | 8200 (Vault), 9000 (Audit) | mTLS |
| Data | Data | inter-cluster ports | mTLS |
| Security | All | 8200 (Vault), audit ports | mTLS |
| External | Public | 443 only | HTTPS + WAF |

### 5.3 mTLS Requirements

- All inter-service communication uses mTLS with certificates from Vault PKI
- Certificate rotation: 90 days auto-rotation
- Certificate revocation: CRL + OCSP via Vault
- External ingress: TLS 1.3 termination at API Gateway

---

## 6. Secrets Management

### 6.1 Vault Configuration

| Secret Path | Purpose | Rotation | Access |
|-------------|---------|----------|--------|
| `gfin/database/creds` | PostgreSQL credentials | 30 days | auth-svc, entity-svc |
| `gfin/kafka/users` | SCRAM credentials per service | 90 days | all Kafka producers/consumers |
| `gfin/neo4j/creds` | Neo4j auth | 90 days | graph-svc, entity-svc |
| `gfin/opensearch/creds` | OpenSearch auth | 90 days | search-svc |
| `gfin/redis/creds` | Redis auth | 90 days | cache-svc, all services |
| `gfin/s3/creds` | S3 access keys | 365 days | evidence-svc, storage-svc |
| `gfin/openai/apikey` | OpenAI API key | on-demand | ai-gateway only |
| `gfin/tls/certs` | mTLS certificates | 90 days | all services |
| `gfin/federation/keys` | Federation signing keys | 365 days | federation-svc |
| `gfin/encryption/keys` | Data encryption keys (envelope) | 90 days | evidence-svc, compliance-svc |

### 6.2 Secret Access Rules

- Services authenticate to Vault via Kubernetes ServiceAccount tokens
- Each secret path has a Vault policy scoped to the specific service
- No service has read access to secrets it doesn't own
- All secret access is audit-logged in Vault and forwarded to GFIN audit log
- Secret rotation triggers a Kubernetes rollout of affected deployments

---

## 7. Storage & Retention Requirements

### 7.1 Storage Allocation

| Component | Dev | Staging | Pilot | Production |
|-----------|-----|---------|-------|------------|
| PostgreSQL | 10GB | 100GB | 500GB | 2TB+ (auto-expand) |
| Neo4j | 5GB | 50GB | 200GB | 1TB+ |
| OpenSearch | 5GB | 50GB | 200GB | 1TB+ |
| Kafka (log retention) | 1GB | 10GB | 100GB | 500GB+ (7-day retention) |
| S3 (Evidence) | 5GB | 50GB | 200GB | 10TB+ (lifecycle to Glacier) |
| Redis | 1GB | 5GB | 20GB | 50GB+ |
| Backups | N/A | 100GB | 500GB | 5TB+ (cross-region) |

### 7.2 Backup Strategy

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Continuous WAL + daily snapshot | 30 days | pgBackRest + S3 |
| Neo4j | Daily snapshot | 14 days | neo4j-admin dump + S3 |
| OpenSearch | Daily snapshot | 14 days | ISM policy + S3 repository |
| Kafka | N/A (event log) | 7-day retention | Topic retention config |
| S3 (Evidence) | Cross-region replication | Per retention policy | S3 CRR |
| Redis | Daily snapshot | 7 days | RDB snapshot + S3 |
| Vault | Daily snapshot | 30 days | Raft snapshot + S3 |

### 7.3 Data Retention Policies

| Data Type | Retention | Action | Authority |
|-----------|-----------|--------|-----------|
| Evidence (PUBLIC) | 7 years | Archive to Glacier | Compliance Module 33 |
| Evidence (RESTRICTED) | 3 years | Delete after retention | Compliance Module 33 |
| Evidence (HIGHLY_RESTRICTED) | 1 year | Delete after retention | Compliance Module 33 |
| Audit logs | 7 years | Immutable, WORM | Article 22 |
| Fraud reports | 10 years | Archive then delete | Module 14 |
| Campaign data | 5 years | Archive then delete | Module 16 |
| Monitoring metrics | 90 days | Downsample then delete | Module 34 |
| Traces | 30 days | Delete | Module 34 |
| DSAR/deletion requests | 3 years | Audit trail | Article 22, Module 33 |

---

## 8. Observability Requirements

### 8.1 Monitoring Stack

| Component | Metrics | Dashboards | Alerts |
|-----------|---------|------------|--------|
| API Gateway | req/s, latency, errors | API Overview, Error Rate | p99 > 200ms, 5xx > 1% |
| Auth Service | auth/s, failures, token rotations | Auth Dashboard | failure rate > 5% |
| Entity Resolution | resolves/s, merge rate, dedup rate | Entity Dashboard | resolution p99 > 100ms |
| Event Bus | pub/s, sub lag, DLQ depth | Event Bus Dashboard | DLQ > 100, consumer lag > 10s |
| Evidence Vault | creates/s, verification failures | Evidence Dashboard | hash mismatch, vault full |
| Search | queries/s, latency, index size | Search Dashboard | p99 > 300ms |
| AI Gateway | requests/s, tokens, latency, errors | AI Dashboard | error rate > 10%, empty content retries |
| Kafka | broker health, partition lag, ISR | Kafka Dashboard | ISR < RF, under-replicated partitions |
| PostgreSQL | connections, slow queries, replication lag | DB Dashboard | replication lag > 5s, connection pool exhausted |
| Redis | hit rate, memory, evictions | Cache Dashboard | memory > 80%, eviction rate spike |
| Neo4j | query latency, store size, transactions | Graph Dashboard | query p99 > 200ms |
| OpenSearch | index size, query latency, indexing rate | Search Infra Dashboard | query p99 > 300ms |

### 8.2 Alert Routing

| Severity | Channel | Response Time |
|----------|---------|---------------|
| CRITICAL | PagerDuty + Slack #gfin-incident | 5 min |
| HIGH | Slack #gfin-alerts | 30 min |
| MEDIUM | Slack #gfin-alerts | 4 hours |
| LOW | Daily digest email | 24 hours |

### 8.3 SLO Targets

| Service | SLO | Target |
|---------|-----|--------|
| API Gateway | Availability | 99.9% |
| Entity Resolution | p99 latency | < 100ms |
| Search | p99 latency | < 300ms |
| Evidence Vault | p99 create latency | < 50ms |
| Event Bus | publish throughput | > 5000/s |
| AI Gateway | availability | 99.5% |

---

## 9. Provisioning Package

### 9.1 Access Request Checklist

- [ ] K8s cluster admin access for platform team
- [ ] AWS/GCP console access for infrastructure team
- [ ] DNS management access for domain configuration
- [ ] TLS certificate authority access (or Let's Encrypt)
- [ ] OpenAI API key procurement
- [ ] External OSINT API keys (WHOIS, RDAP, DNS, certificate transparency)
- [ ] Federation partner credentials (Interpol, Europol)
- [ ] PagerDuty account for alerting
- [ ] Slack workspace for notifications

### 9.2 Provisioning Sequence

1. **Week 1:** K8s cluster + networking + DNS + TLS certificates
2. **Week 2:** Vault HA + external secrets operator + PKI
3. **Week 3:** PostgreSQL + Redis + S3 (core storage)
4. **Week 4:** Strimzi Kafka + Neo4j + OpenSearch
5. **Week 5:** Monitoring stack (Prometheus, Grafana, OTel)
6. **Week 6:** GFIN application services deployment (staging)
7. **Week 7:** Integration testing + performance validation (staging)
8. **Week 8:** Security validation + pentest preparation

### 9.3 Named Owner Assignments (TO BE FILLED)

| Component | Owner Name | Due Date | Status |
|-----------|-----------|----------|--------|
| K8s Cluster | ____________ | ____________ | NOT STARTED |
| Vault HA | ____________ | ____________ | NOT STARTED |
| PostgreSQL | ____________ | ____________ | NOT STARTED |
| Redis | ____________ | ____________ | NOT STARTED |
| S3 / MinIO | ____________ | ____________ | NOT STARTED |
| Strimzi Kafka | ____________ | ____________ | NOT STARTED |
| Neo4j | ____________ | ____________ | NOT STARTED |
| OpenSearch | ____________ | ____________ | NOT STARTED |
| Monitoring Stack | ____________ | ____________ | NOT STARTED |
| Network Security | ____________ | ____________ | NOT STARTED |

---

## 10. Go/No-Go Gates Integration

This mobilization package maps to the 12 go/no-go gates defined in `packages/production/go_no_go_gates.py`:

| Gate | Requirement | This Document Section |
|------|------------|----------------------|
| G1: K8s Cluster | K8s v1.28+ provisioned | §3.1, §9.2 |
| G2: Vault | Vault HA with Raft | §6.1, §9.2 |
| G3: Database | PostgreSQL 16 with replicas | §3.1, §9.2 |
| G4: Kafka | Strimzi with 14 topics | §3.1, §9.2 |
| G5: Neo4j | Neo4j 5.x with HA | §3.1, §9.2 |
| G6: OpenSearch | OpenSearch 2.x cluster | §3.1, §9.2 |
| G7: Redis | Redis 7.x with sentinel/cluster | §3.1, §9.2 |
| G8: S3 | S3 with encryption | §3.1, §9.2 |
| G9: Monitoring | Prometheus + Grafana + OTel | §8.1, §9.2 |
| G10: Network Security | mTLS + network policies | §5.2, §5.3 |
| G11: Backup/DR | Cross-region backup + DR | §7.2 |
| G12: Legal/Governance | DPA + MLAT evidence | External (REQUIRES LEGAL REVIEW) |

---

## 11. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| K8s cluster sizing insufficient | Medium | High | Start with pilot sizing, auto-scale enabled |
| Vault HA quorum loss | Low | Critical | 5-node Raft in production, regular snapshots |
| Kafka topic misconfiguration | Medium | High | Topic CRDs version-controlled, verified on deploy |
| Neo4j memory pressure | Medium | Medium | Dedicated nodes, JVM tuning, read replicas |
| OpenSearch shard imbalance | Low | Medium | ISM policies, shard count planning |
| S3 cost overrun | Medium | Low | Lifecycle policies (Hot → Glacier), storage monitoring |
| Certificate rotation failure | Low | Critical | Vault auto-rotation, monitoring alerts |
| Federation mTLS handshake failure | Low | High | Pre-deployment mTLS validation, cert pinning |
| AI gateway rate limiting | High | Medium | Request queuing, circuit breaker, Local AI fallback |
| Legal review delay | High | High | Start legal review immediately, parallel to infra |

---

## 12. Acceptance Criteria

This mobilization package is ACCEPTED when:

1. [ ] All infrastructure components have named owners with due dates (§9.3)
2. [ ] IaC repository structure is created and reviewed (§4)
3. [ ] Terraform modules are written and validated (dev environment)
4. [ ] Helm charts are written and validated (dev environment)
5. [ ] Network policies are defined and reviewed (§5)
6. [ ] Vault policies and secret paths are defined (§6)
7. [ ] Backup and retention policies are documented and reviewed (§7)
8. [ ] Monitoring dashboards and alert rules are defined (§8)
9. [ ] All 12 go/no-go gates have a documented path to satisfaction (§10)
10. [ ] Risk register is reviewed and accepted (§11)

**Status: DRAFT — Awaiting infrastructure team assignment and legal review initiation.**
