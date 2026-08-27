# GFIN Production Deployment Planning Document
## Target Architecture, Trust Boundaries, and Migration Strategy

**Document ID:** GFIN-PDP-001
**Author:** GPT Luna (GFIN-CEA)
**Directive:** Final Build Verification §35 → Luna Strategic Assessment
**Status:** DRAFT — REQUIRES EXTERNAL INFRASTRUCTURE
**Date:** 2026-08-26

---

## 1. Executive Summary

GFIN Layer A (in-memory MVP) is fully implemented with 2,011 passing tests and 93.57% coverage. This document defines the production deployment architecture (Layer B) required to transition from sandbox MVP to a live, federated fraud intelligence platform.

**All infrastructure described herein is REQUIRES EXTERNAL INFRASTRUCTURE — not deployed, not claimed as deployed.**

---

## 2. Target Architecture

### 2.1 High-Level Topology

```
                    ┌─────────────────────────────────────────────────┐
                    │              GFIN Production Cluster             │
                    │                                                 │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
                    │  │  API     │  │  Citizen  │  │  Police   │     │
                    │  │  Gateway │  │  Portal   │  │  Portal   │     │
                    │  └────┬─────┘  └─────┬─────┘  └─────┬────┘     │
                    │       │              │              │           │
                    │       ▼              ▼              ▼           │
                    │  ┌─────────────────────────────────────────┐   │
                    │  │         FastAPI Application Layer         │   │
                    │  │  (Auth · RBAC · Compliance · Audit)      │   │
                    │  └──────────────────┬──────────────────────┘   │
                    │                     │                          │
                    │  ┌─────┬──────┬──────┼──────┬──────┬──────┐   │
                    │  │     │      │      │      │      │      │   │
                    │  ▼     ▼      ▼      ▼      ▼      ▼      ▼   │
                    │ Kafka  Neo4j  OpenS.  Redis  S3    AI    Disc. │
                    │ (bus)  (graph)(search)(cache)(vault)(GW)  (OSINT)│
                    └─────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Federation      │
                    │   (Interpol/       │
                    │    Europol/MLAT)   │
                    └───────────────────┘
```

### 2.2 Component Inventory

| Component | Technology | Purpose | Scaling Strategy |
|-----------|-----------|---------|------------------|
| API Gateway | Nginx + FastAPI | TLS termination, rate limiting, request routing | Horizontal, behind LB |
| Citizen Portal | React/Next.js | Public-facing report submission | CDN-cached static |
| Police Portal | React/Next.js | Authenticated law enforcement access | Behind VPN/mTLS |
| Application Layer | Python/FastAPI | Business logic, auth, RBAC, compliance | Horizontal, stateless |
| Event Bus | Apache Kafka | Async event distribution, pub/sub | 3+ broker cluster |
| Graph Store | Neo4j 5.x | Entity relationships, path finding | Causal cluster (3 nodes) |
| Search Engine | OpenSearch | Full-text, faceted search | 3-node cluster |
| Cache | Redis 7.x | Session, hot data, rate limit | Sentinel or Cluster |
| Object Storage | S3-compatible (MinIO) | Evidence vault, backups | Erasure coding |
| AI Model Gateway | Python service | Provider routing, fallback, audit | Horizontal, stateless |
| Discovery Service | Python + Go | OSINT source management | Horizontal per source |
| Database | PostgreSQL 16 | Entity records, audit, config | Primary + 2 replicas |
| Observability | OpenTelemetry → Prometheus/Grafana | Metrics, traces, logs | Central collector |

---

## 3. Trust Boundaries

### 3.1 Trust Zones

```
Zone 0: Public Internet (UNTRUSTED)
  │
  ▼ [TLS 1.3, WAF, DDoS protection]
Zone 1: DMZ (API Gateway, Load Balancer)
  │
  ▼ [mTLS, OIDC/OAuth2]
Zone 2: Application Layer (FastAPI workers)
  │
  ▼ [Network policies, service mesh mTLS]
Zone 3: Data Layer (Kafka, Neo4j, OpenSearch, Redis, S3, PostgreSQL)
  │
  ▼ [VPN, IP allowlist, audit logging]
Zone 4: Federation (Interpol/Europol/Partner APIs)
  │
  ▼ [MLAT, bilateral agreements, per-tenant encryption]
Zone 5: Management/Operations (Bastion, CI/CD, Monitoring)
```

### 3.2 Boundary Controls

| Boundary | Control | Enforcement |
|----------|---------|-------------|
| Internet → DMZ | TLS 1.3, WAF rules, rate limit, DDoS | Nginx + CloudFlare |
| DMZ → App | mTLS, OIDC token validation, request size limit | Service mesh (Istio/Linkerd) |
| App → Data | Network policy (allowlist), mTLS, connection pooling | K8s NetworkPolicy + mesh |
| App → Federation | VPN tunnel, signed requests, data minimization | Per-partner VPN + API signing |
| Data → Storage | Encryption at rest (AES-256), encryption in transit | Provider-native + KMS |
| Operations → All | Bastion host, MFA, audit log, session recording | SSH bastion + auditd |

### 3.3 Data Classification Enforcement

| Classification | Allowed Zone | AI Routing | Storage | Federation |
|---------------|--------------|------------|---------|------------|
| PUBLIC | 0-4 | OpenAI (external) | Standard | Permitted |
| COMMUNITY | 1-4 | OpenAI (authorized) | Standard | Permitted (aggregated) |
| RESTRICTED | 2-3 | OpenAI (authorized, logged) | Encrypted | Bilateral only |
| LAW_ENFORCEMENT | 2-3 | LOCAL only | Encrypted, access-logged | MLAT required |
| HIGHLY_RESTRICTED | 3 only | LOCAL only | Encrypted, isolated | Explicit consent |

---

## 4. Secrets Management

### 4.1 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Developer  │────▶│  Vault (HA)  │────▶│  K8s Secrets     │
│  CI/CD      │     │  (HashiCorp) │     │  (mounted)      │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴──────┐
                    │  Dynamic    │
                    │  Secrets    │
                    │  (DB creds, │
                    │   API keys) │
                    └─────────────┘
```

### 4.2 Secret Categories

| Secret | Source | Rotation | Storage |
|--------|--------|----------|--------|
| OpenAI API Key | OpenAI console | 90 days | Vault dynamic secret |
| Database credentials | Vault dynamic | 24 hours | Vault DB engine |
| Kafka SASL credentials | Vault dynamic | 7 days | Vault Kafka engine |
| Neo4j password | Initial bootstrap | 30 days | Vault KV v2 |
| OIDC client secrets | IdP admin | 90 days | Vault KV v2 |
| Federation partner keys | Bilateral exchange | Per agreement | Vault KV v2, per-tenant |
| TLS certificates | Let's Encrypt / internal CA | 90 days | cert-manager |
| S3/MinIO access keys | Vault dynamic | 24 hours | Vault AWS engine |

### 4.3 Principles

- **No static secrets in code or config files** — all secrets from Vault at runtime
- **Dynamic secrets where possible** — short-lived, auto-rotated
- **Secret access audited** — every Vault read logged
- **No secrets in logs or error messages** — redaction at application layer
- **Secrets never cross trust boundaries unencrypted** — mTLS everywhere

---

## 5. Network Isolation

### 5.1 Kubernetes Network Policies

```yaml
# Default: deny all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

# API gateway: allow from LB only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-gateway-ingress
spec:
  podSelector:
    matchLabels:
      app: gfin-api-gateway
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 443

# App layer: allow from API gateway only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-layer-ingress
spec:
  podSelector:
    matchLabels:
      layer: application
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gfin-api-gateway
    ports:
    - protocol: TCP
      port: 8000

# Data layer: allow from app layer only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-layer-ingress
spec:
  podSelector:
    matchLabels:
      layer: data
  ingress:
  - from:
    - podSelector:
        matchLabels:
          layer: application
```

### 5.2 Egress Controls

| Service | Allowed Egress | Denied |
|---------|---------------|--------|
| API Gateway | App layer, health checks | Direct data access |
| App Layer | Data layer, AI Gateway, OIDC | Direct internet |
| AI Gateway | OpenAI API (443), Local AI | Data layer |
| Discovery | Approved OSINT sources only | Internal services |
| Data Layer | Replication peers only | Any external |

---

## 6. Backup and Restore

### 6.1 Backup Strategy

| Component | Method | Frequency | Retention | RPO |
|-----------|--------|-----------|-----------|-----|
| PostgreSQL | pg_dump + WAL archiving | Continuous WAL + daily snapshot | 30 days | < 1 min |
| Neo4j | neo4j-admin dump + Causal Cluster | Hourly snapshot | 7 days | < 1 hour |
| OpenSearch | Snapshot to S3 | Every 6 hours | 7 days | < 6 hours |
| Redis | RDB snapshot + AOF | Every 10 min | 24 hours | < 10 min |
| S3/MinIO | Versioning + cross-region replication | Continuous | 90 days | 0 (eventual) |
| Kafka | Tiered storage + snapshot | Daily snapshot | 7 days | < 24 hours |
| Vault | Raft snapshot | Every 6 hours | 90 days | < 6 hours |
| Config (GitOps) | Git repository | Every commit | Permanent | 0 |

### 6.2 Restore Procedures

**PostgreSQL PITR (Point-in-Time Recovery):**
1. Restore base backup from S3
2. Replay WAL files to target timestamp
3. Verify consistency with `pg_checksums`
4. Switch DNS to restored instance
5. RTO: < 30 minutes

**Neo4j Cluster Recovery:**
1. Identify healthy seed
2. `neo4j-admin database restore`
3. Resync cluster members
4. RTO: < 1 hour

**Full Disaster Recovery:**
1. Provision new Kubernetes cluster
2. Apply GitOps manifests
3. Restore Vault from snapshot
4. Restore PostgreSQL from PITR
5. Restore Neo4j from dump
6. Restore OpenSearch from snapshot
7. Rebuild Kafka topics from tiered storage
8. Reindex search from PostgreSQL
9. Verify data integrity
10. RTO: < 4 hours (full cold start)

---

## 7. Disaster Recovery

### 7.1 RTO/RPO Targets

| Scenario | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| Single pod failure | < 30s | 0 | K8s auto-restart |
| Single node failure | < 2min | 0 | K8s rescheduling |
| Data store failure | < 30min | < 1min | Replica failover |
| AZ failure | < 15min | < 1min | Multi-AZ deployment |
| Region failure | < 4hr | < 1hr | Warm standby + restore |
| Total cluster loss | < 8hr | < 24hr | Cold start from backups |

### 7.2 DR Architecture

```
Primary Region (eu-central-1)
  ├── Active cluster (all services)
  └── S3 backup target

DR Region (eu-west-1)
  ├── Warm standby (minimal cluster)
  ├── Synced S3 backups (cross-region)
  └── DNS failover target
```

### 7.3 Failover Decision Matrix

| Condition | Action | Authority |
|-----------|--------|-----------|
| Pod crash | Auto-restart | Kubernetes |
| Node failure | Auto-reschedule | Kubernetes |
| Data store failover | Auto-promote replica | Cluster manager |
| AZ isolation | Manual cordon + drain | SRE on-call |
| Region failover | Manual DNS switch | CTO + SRE lead |

---

## 8. Monitoring and Observability

### 8.1 Monitoring Stack

```
Application → OpenTelemetry SDK
  │
  ├──▶ Prometheus (metrics, 15s scrape)
  ├──▶ Loki (logs, structured JSON)
  ├──▶ Jaeger (distributed traces)
  └──▶ Grafana (dashboards, alerting)
```

### 8.2 Key Metrics (SLO-aligned)

| Metric | SLO Target | Alert Threshold |
|--------|-----------|-----------------|
| API latency p99 | < 200ms | > 500ms for 5 min |
| API error rate | < 0.1% | > 1% for 2 min |
| Entity resolution latency p99 | < 100ms | > 300ms for 5 min |
| Graph query latency p99 | < 200ms | > 500ms for 5 min |
| Search latency p99 | < 300ms | > 1s for 5 min |
| Event bus lag | < 10s | > 60s for 5 min |
| AI gateway latency p99 | < 5s | > 15s for 5 min |
| Kafka consumer lag | < 1000 msgs | > 10000 for 5 min |
| Disk usage | < 80% | > 90% |
| Memory usage | < 80% | > 90% |

### 8.3 Alert Routing

| Severity | Channels | Response Time |
|----------|---------|---------------|
| Critical (P1) | PagerDuty + Slack #gfin-ops | < 5 min |
| Warning (P2) | Slack #gfin-ops | < 30 min |
| Info (P3) | Slack #gfin-monitoring | Best effort |

### 8.4 Dashboards

1. **GFIN Overview** — request rate, error rate, latency, active users
2. **Data Layer** — DB connections, query latency, replication lag, disk usage
3. **Event Bus** — publish rate, consumer lag, DLQ depth, partition health
4. **AI Gateway** — request rate, token usage, provider health, latency
5. **Security** — auth failures, rate limit hits, classification violations, audit events
6. **Discovery** — source health, crawl rate, entity creation rate, error rate

---

## 9. Migration Plan

### 9.1 Phase Sequence

```
Phase 1: Infrastructure Provisioning (Weeks 1-2)
  ├── Provision Kubernetes cluster (multi-AZ)
  ├── Deploy Vault, cert-manager, ingress controller
  ├── Configure network policies
  └── Set up monitoring stack

Phase 2: Data Layer Deployment (Weeks 3-4)
  ├── Deploy PostgreSQL (primary + 2 replicas)
  ├── Deploy Neo4j Causal Cluster (3 nodes)
  ├── Deploy OpenSearch cluster (3 nodes)
  ├── Deploy Redis (Sentinel)
  ├── Deploy MinIO (S3-compatible)
  └── Deploy Kafka (3 brokers)

Phase 3: Application Deployment (Weeks 5-6)
  ├── Deploy API Gateway + Nginx
  ├── Deploy FastAPI application workers
  ├── Deploy AI Model Gateway service
  ├── Deploy Discovery service
  ├── Configure OIDC/OAuth2 (Keycloak/Auth0)
  └── Deploy citizen + police portals

Phase 4: Data Migration (Week 7)
  ├── Export Layer A data (if any production data exists)
  ├── Import to production stores
  ├── Verify data integrity
  ├── Run parity tests
  └── Switch DNS

Phase 5: Validation & Go-Live (Week 8)
  ├── Run full test suite against production
  ├── Execute load tests
  ├── Execute DR drill
  ├── Security penetration test
  ├── Sign-off from legal/governance
  └── Go-live
```

### 9.2 Rollback Strategy

- **GitOps** — every deployment is a Git commit; rollback = revert commit
- **Database** — blue-green schema migrations, forward-only with expand/contract
- **Configuration** — all config in Git, no manual changes
- **DNS** — TTL 60s during migration, instant rollback

### 9.3 Go-Live Gates

| Gate | Criteria | Owner |
|------|---------|-------|
| Security | Pen test passed, no Critical/High findings | CISO |
| Legal | DPA signed, MLAT framework approved | Legal |
| Performance | Load test meets SLOs | SRE Lead |
| DR | DR drill passed within RTO | SRE Lead |
| Compliance | GDPR audit passed, data retention configured | DPO |
| Federation | Partner integration tested | Engineering Lead |

---

## 10. Integration Contracts — External OSINT Systems

### 10.1 Contract Template

Each external OSINT integration (MISP, OpenCTI, SpiderFoot, Cortex) must define:

```yaml
integration:
  name: <system-name>
  type: <push|pull|bidirectional>
  auth:
    method: <api_key|oauth2|mtls>
    rotation: <interval>
    storage: vault
  
  data_minimization:
    fields_sent: [<explicit list>]
    fields_received: [<explicit list>]
    classification_filter: <max classification>
  
  provenance:
    source_id_format: "SRC-<system>-<uuid>"
    evidence_required: true
    audit_trail: true
  
  failure_behavior:
    timeout: 30s
    retry: 3 attempts, exponential backoff
    circuit_breaker: activate after 10 failures
    fallback: degraded mode, log warning
  
  rate_limit:
    requests_per_minute: <limit>
    burst: <burst_limit>
  
  security:
    encryption_in_transit: TLS 1.3
    encryption_at_rest: AES-256
    ip_allowlist: [<explicit IPs>]
    data_residency: <region>
```

### 10.2 Per-System Contracts

| System | Type | Auth | Classification Filter | Status |
|--------|------|------|----------------------|--------|
| MISP | Pull | API key | PUBLIC, COMMUNITY | REQUIRES EXTERNAL INFRASTRUCTURE |
| OpenCTI | Bidirectional | OAuth2 | PUBLIC, COMMUNITY, RESTRICTED | REQUIRES EXTERNAL INFRASTRUCTURE |
| SpiderFoot | Pull | API key | PUBLIC | REQUIRES EXTERNAL INFRASTRUCTURE |
| Cortex | Push/Pull | API key | PUBLIC, COMMUNITY | REQUIRES EXTERNAL INFRASTRUCTURE |
| Interpol I-24/7 | Bidirectional | mTLS + bilateral | LAW_ENFORCEMENT | REQUIRES LEGAL REVIEW |
| Europol SIENA | Bidirectional | mTLS + bilateral | LAW_ENFORCEMENT | REQUIRES LEGAL REVIEW |

### 10.3 Threat Model for Integrations

| Threat | Mitigation |
|--------|-----------|
| Malicious OSINT data injection | Validate all inputs, classify as UNVERIFIED, require corroboration |
| API key compromise | Vault dynamic secrets, short TTL, rotation |
| Data exfiltration via integration | Data minimization, classification filter, audit logging |
| Denial of service | Rate limiting, circuit breaker, timeout |
| Supply chain compromise | Pin dependencies, scan containers, signed images |
| Man-in-the-middle | TLS 1.3, certificate pinning for federation |
| Privilege escalation | Per-integration service account, minimal RBAC |

---

## 11. Kafka Layer B — Event Bus Production Definition

### 11.1 Cluster Configuration

```yaml
kafka:
  version: "3.7"
  brokers: 3  # minimum for quorum
  replication_factor: 3
  min_in_sync_replicas: 2
  
  config:
    log.retention.hours: 168          # 7 days
    log.segment.bytes: 1073741824      # 1GB segments
    auto.create.topics.enable: false   # explicit topic creation
    compression.type: lz4
   unclean.leader.election.enable: false # data safety
  
  tls:
    enabled: true
    client_auth: required
  
  sasl:
    mechanism: SCRAM-SHA-512
    jaas_config: ${vault:kafka-jaas}
```

### 11.2 Topic Schema

| Topic | Partitions | Retention | Key | Purpose |
|-------|-----------|----------|-----|---------|
| gfin.events.entity | 12 | 7d | entity_id | Entity lifecycle events |
| gfin.events.report | 6 | 30d | report_id | Report lifecycle events |
| gfin.events.evidence | 6 | 90d | evidence_id | Evidence lifecycle events |
| gfin.events.alert | 6 | 30d | alert_id | Alert events |
| gfin.events.discovery | 12 | 7d | source_id | Discovery results |
| gfin.events.audit | 6 | 365d | audit_id | Audit trail |
| gfin.events.federation | 3 | 90d | federation_id | Federation sync events |
| gfin.dlq.entity | 3 | 30d | original_key | Dead letter queue |
| gfin.dlq.report | 3 | 30d | original_key | Dead letter queue |
| gfin.dlq.evidence | 3 | 30d | original_key | Dead letter queue |

### 11.3 Consumer Groups

| Group | Topics | Max Poll | Processing |
|-------|--------|----------|------------|
| gfin-entity-resolver | gfin.events.entity | 100 | Synchronous, idempotent |
| gfin-alert-engine | gfin.events.entity, gfin.events.report | 50 | Async, stateful |
| gfin-discovery-worker | gfin.events.discovery | 200 | Async, batched |
| gfin-audit-writer | gfin.events.audit | 500 | Batched, append-only |
| gfin-federation-sync | gfin.events.federation | 10 | Synchronous, transactional |

### 11.4 Reliability Guarantees

| Guarantee | Implementation | Verification |
|------------|---------------|-------------|
| Idempotency | Producer ID + sequence number, consumer dedup by event_id | Test: publish same event twice, verify single processing |
| Ordering | Partition by entity_id, single consumer per partition | Test: publish events out-of-order to different keys, verify per-key ordering |
| Replay | Kafka committed offset + seek to timestamp | Test: replay from 1 hour ago, verify all events reprocessed |
| Dead Letter Queue | Retry 3x with exponential backoff, then DLQ topic | Test: poison message, verify it lands in DLQ after 3 retries |
| Exactly-once | Transactional producer + consumer (Kafka Streams) | Test: crash consumer mid-processing, verify no duplicate |
| Encryption | TLS 1.3 in transit, AES-256 at rest (KMS) | Test: verify TLS handshake, verify at-rest encryption |
| Access control | SASL SCRAM-SHA-512, per-topic ACL | Test: unauthorized consumer rejected, authorized consumer accepted |
| Observability | Consumer lag metrics, throughput metrics, error rate | Test: verify metrics exported to Prometheus |

---

## 12. Acceptance Criteria for Production Readiness

| # | Criterion | Verification | Status |
|---|-----------|-------------|--------|
| 1 | All services deployed with health checks | kubectl get pods, all healthy | REQUIRES EXTERNAL INFRASTRUCTURE |
| 2 | Network policies enforced | nmap scan from pod, denied | REQUIRES EXTERNAL INFRASTRUCTURE |
| 3 | Secrets in Vault, not in code | grep for secrets in repo, none found | VERIFIED (code), REQUIRES EXTERNAL INFRASTRUCTURE (deployment) |
| 4 | TLS everywhere, no plaintext | ssl-scan all endpoints | REQUIRES EXTERNAL INFRASTRUCTURE |
| 5 | Backup and restore tested | DR drill completed within RTO | REQUIRES EXTERNAL INFRASTRUCTURE |
| 6 | Monitoring covers all SLOs | Grafana dashboards live, alerts firing | REQUIRES EXTERNAL INFRASTRUCTURE |
| 7 | Load test meets SLOs | k6/load test report, all pass | REQUIRES EXTERNAL INFRASTRUCTURE |
| 8 | Security pen test passed | Report, no Critical/High | REQUIRES EXTERNAL INFRASTRUCTURE |
| 9 | Compliance audit passed | GDPR, DPA signed | REQUIRES LEGAL REVIEW |
| 10 | Federation contracts tested | Integration tests with partners | REQUIRES EXTERNAL INFRASTRUCTURE |
| 11 | Kafka idempotency verified | Replay test, no duplicates | REQUIRES EXTERNAL INFRASTRUCTURE |
| 12 | Kafka ordering verified | Per-key ordering test | REQUIRES EXTERNAL INFRASTRUCTURE |
| 13 | Kafka DLQ verified | Poison message test | REQUIRES EXTERNAL INFRASTRUCTURE |
| 14 | DR drill completed | Full failover within RTO | REQUIRES EXTERNAL INFRASTRUCTURE |
| 15 | Go-live gates signed | All owners signed | REQUIRES EXTERNAL INFRASTRUCTURE |

---

## 13. Status Summary

| Area | Status | Blocker |
|------|--------|---------|
| Architecture definition | COMPLETE | None |
| Trust boundary definition | COMPLETE | None |
| Secrets management plan | COMPLETE | Requires Vault deployment |
| Network isolation plan | COMPLETE | Requires K8s deployment |
| Backup/restore plan | COMPLETE | Requires infrastructure |
| DR plan | COMPLETE | Requires infrastructure |
| Monitoring plan | COMPLETE | Requires Prometheus/Grafana |
| Migration plan | COMPLETE | Requires infrastructure |
| Integration contracts | DEFINED | Requires partner agreements |
| Kafka Layer B definition | COMPLETE | Requires Kafka deployment |
| Load testing | IN PROGRESS | Sub-agent building tests |
| AI evaluation | IN PROGRESS | Sub-agent building tests |
| Production deployment | NOT STARTED | Requires infrastructure |

**This document is a planning artifact. No infrastructure is deployed. All production components are marked REQUIRES EXTERNAL INFRASTRUCTURE.**

---

*End of document — GFIN-PDP-001*
