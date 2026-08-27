# GFIN Hybrid Cloud Architecture

**Document ID:** GFIN-HYBRID-001  
**Authority:** GPT Luna (GFIN-CEA) — LUNA-HYBRID-ARCH-001  
**Date:** 2026-08-26  
**For:** Rojs (Project Owner)  

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GFIN Production                        │
│                                                          │
│  ┌──────────────────────┐    ┌───────────────────────┐  │
│  │   HETZNER (Germany)   │    │   AWS (Frankfurt)     │  │
│  │                       │    │     eu-central-1      │  │
│  │  ┌─────────────────┐  │    │  ┌─────────────────┐  │  │
│  │  │ K8s Cluster     │  │    │  │ RDS PostgreSQL   │  │  │
│  │  │ (self-managed)  │  │    │  │ (Multi-AZ, PITR) │  │  │
│  │  │                 │  │    │  └─────────────────┘  │  │
│  │  │ 17 GFIN services│◄─┼───►│  ┌─────────────────┐  │  │
│  │  │ (stateless)    │  │VPN │  │ MSK Kafka        │  │  │
│  │  │                 │  │IPsec│ │ (3 brokers)     │  │  │
│  │  │ Vault HA (3)    │  │    │  └─────────────────┘  │  │
│  │  └─────────────────┘  │    │  ┌─────────────────┐  │  │
│  │                       │    │  │ OpenSearch Svc   │  │  │
│  │  Hetzner S3 (dev only)│    │  └─────────────────┘  │  │
│  └──────────────────────┘    │  ┌─────────────────┐  │  │
│                              │  │ ElastiCache Redis│  │  │
│                              │  └─────────────────┘  │  │
│                              │  ┌─────────────────┐  │  │
│                              │  │ S3 (evidence)   │  │  │
│                              │  │ SSE-KMS, Lock   │  │  │
│                              │  └─────────────────┘  │  │
│                              │  ┌─────────────────┐  │  │
│                              │  │ EKS warm standby│  │  │
│                              │  │ (DR only)       │  │  │
│                              │  └─────────────────┘  │  │
│                              └───────────────────────┘  │
│                                                          │
│  DNS: Route 53 (health-checked) → Hetzner LB (primary)   │
│                                   → AWS EKS (failover)   │
└─────────────────────────────────────────────────────────┘
```

## 1. Environment Placement

| Environment | Provider | K8s | Stateful Services | Storage |
|-------------|----------|-----|-------------------|---------|
| Dev | Hetzner | Self-managed (kubeadm/KubeOne) | All self-managed | Hetzner S3 |
| Staging | Hetzner | Self-managed | All self-managed | Hetzner S3 |
| Pilot | Hetzner | Self-managed | All self-managed | Hetzner S3 |
| Production | Hybrid | Hetzner (primary) + AWS EKS (DR standby) | AWS managed | AWS S3 |

## 2. Production Service Placement

### Hetzner (all 17 stateless GFIN services)

| Service | Replicas | Instance | Notes |
|---------|----------|----------|-------|
| API Gateway | 3 | CCX33 (8 vCPU, 32 GB) | Front door, TLS termination |
| Auth Service | 2 | Shared node | JWT, RBAC, audit |
| Entity Resolution | 3 | CCX33 | CPU-intensive matching |
| Evidence Vault | 2 | Shared node | S3 access via VPN to AWS |
| Search Service | 2 | Shared node | OpenSearch access via VPN to AWS |
| Web Discovery | 2 | Shared node | Crawling, low CPU |
| Fraud Detection | 3 | CCX33 | Signal processing |
| Campaign Engine | 2 | Shared node | Campaign grouping |
| Alert Engine | 2 | Shared node | Alert dispatch |
| AI Gateway | 2 | CCX23 | Model routing |
| AI Investigation | 2 | CCX33 | 15 AI tools, CPU-heavy |
| Police API | 2 | Shared node | Police console backend |
| Federation Service | 2 | Shared node | Cross-border messaging |
| Crypto Intelligence | 2 | Shared node | Wallet analysis |
| Analytics | 2 | Shared node | Metrics aggregation |
| Observability | 2 | CCX33 | Prometheus, Grafana |
| Compliance | 2 | Shared node | GDPR, retention |

**Hetzner production cluster:** ~6-8 CCX33/CCX43 nodes + 2-3 dedicated AX servers

### AWS (managed stateful services)

| Component | Service | Config | Notes |
|-----------|---------|--------|-------|
| PostgreSQL | RDS Multi-AZ | 8 vCPU, 32 GB, 500 GB | PITR, 2 read replicas |
| Kafka | MSK | 3 brokers, t3.large | 14 topics, 6 partitions each |
| OpenSearch | OpenSearch Service | 5 nodes, r6g.large | 1.5 TB, 2 replicas |
| Redis | ElastiCache | 3 nodes, cache.r6g.large | HA, cluster mode |
| S3 (evidence) | S3 Standard + IA | 2-10 TB | SSE-KMS, Object Lock |
| Vault backup | S3 | Encrypted backup | Vault runs on Hetzner |
| EKS standby | EKS (small) | 2-3 nodes | DR warm standby only |

## 3. Network Topology

```
Hetzner (Falkenstein/Nuremberg)
    │
    ├── VPN Tunnel 1 (IPsec/WireGuard) ──► AWS Transit Gateway
    ├── VPN Tunnel 2 (redundant)        ──► AWS Transit Gateway
    │
    ▼
AWS eu-central-1 (Frankfurt)
    ├── Private Subnet AZ-a (RDS primary, MSK broker 1)
    ├── Private Subnet AZ-b (RDS standby, MSK broker 2)
    └── Private Subnet AZ-c (RDS read replica, MSK broker 3)
```

- **2 redundant IPsec/WireGuard tunnels** between Hetzner and AWS Transit Gateway
- **BGP or static routes** with automatic tunnel failover
- **mTLS** between all services across the VPN
- **Security groups/NACLs** in AWS, **Hetzner firewalls** on Hetzner side
- **No public exposure** for databases or Kafka
- **NAT gateways** for outbound traffic

## 4. Cross-Cloud Latency

Hetzner (Falkenstein) to AWS (Frankfurt): ~5-15ms RTT over VPN

| Operation | Path | Est. Latency Impact |
|-----------|------|-------------------|
| Entity CRUD → PostgreSQL | Hetzner → AWS RDS via VPN | +5-10ms per query |
| Event publish → Kafka | Hetzner → AWS MSK via VPN | +5-10ms per event |
| Search query → OpenSearch | Hetzner → AWS via VPN | +5-15ms per query |
| Evidence read → S3 | Hetzner → AWS S3 via VPN | +10-20ms per object |
| Cache get → Redis | Hetzner → AWS ElastiCache | +5-10ms |

**Mitigation:**
- Connection pooling (reuse DB connections, avoid per-request overhead)
- Redis caching for hot data (reduces DB calls)
- Batched Kafka operations (publish in batches, not individual events)
- Asynchronous workflows (webhook processing, analytics — latency tolerant)
- Pre-signed S3 URLs (client downloads directly from S3, not through VPN)

**⚠️ CRITICAL:** Must load-test at 5,000 req/sec before production. If VPN adds >20ms p99, consider moving latency-sensitive services to AWS EKS.

## 5. DNS & Load Balancing

| Component | Provider | Config |
|-----------|----------|--------|
| DNS | AWS Route 53 | Latency + health-check routing |
| Primary LB | Hetzner Load Balancer | Hetzner ingress controller |
| Failover LB | AWS ALB → EKS | Activated on health check failure |
| TLS | Let's Encrypt or ACM | Wildcard cert for *.gfin.example |
| Internal DNS | CoreDNS (K8s) | Service discovery within cluster |

## 6. Monitoring

| Metric Source | Collector | Storage | Dashboard |
|---------------|-----------|---------|-----------|
| Hetzner K8s | Prometheus agent | Local Prometheus + remote write | Grafana |
| AWS services | CloudWatch + OTel | CloudWatch + OpenSearch | Grafana |
| VPN health | Prometheus + custom probe | Prometheus | Grafana alert |
| Cross-cloud latency | OTel tracer | OpenSearch (AWS) | Grafana |

**Alerts:** VPN health, p99 latency, Kafka lag, DB saturation, error rate, replication status, tunnel failover

## 7. S3 Evidence Storage Strategy

| Environment | Storage | Access |
|-------------|---------|--------|
| Dev | Hetzner S3 | Direct (same provider) |
| Staging | Hetzner S3 | Direct |
| Pilot | Hetzner S3 | Direct |
| Production | AWS S3 (SSE-KMS, Object Lock) | Via VPN from Hetzner, pre-signed URLs |

Evidence Vault service on Hetzner generates short-lived pre-signed URLs for client downloads — clients download directly from AWS S3, not through the VPN.

## 8. Kafka Access Strategy

Hetzner services connect to AWS MSK through the VPN using TLS + SASL/IAM or mTLS. Settings:
- Idempotent producers (prevent duplicates on network issues)
- Replication factor 3 (across 3 AWS AZs)
- Local buffering on Hetzner side (handle VPN jitter)
- Back-pressure if Kafka lag exceeds threshold
- Consumer groups per service, offset management per service

## 9. Cost Estimate (Production, Monthly)

### Hetzner (compute)

| Component | Qty | Instance | Monthly |
|-----------|-----|----------|---------|
| K8s nodes (CCX33) | 6 | 8 vCPU, 32 GB, 240 GB | $163 × 6 = $978 |
| K8s nodes (CCX43) | 2 | 16 vCPU, 64 GB, 360 GB | $329 × 2 = $658 |
| Dedicated AX (K8s workers) | 2 | AMD Ryzen, 64 GB | $69 × 2 = $138 |
| Load Balancer | 1 | Hetzner LB | ~$15 |
| Vault cluster (3 × CCX23) | 3 | 4 vCPU, 16 GB | $101 × 3 = $303 |
| **Hetzner subtotal** | | | **~$2,092** |

### AWS (managed stateful)

| Component | Service | Monthly |
|-----------|---------|---------|
| RDS PostgreSQL Multi-AZ | 8 vCPU, 32 GB, 500 GB | ~$1,800 |
| MSK Kafka (3 brokers) | t3.large × 3 + storage | ~$900 |
| OpenSearch Service (5 nodes) | r6g.large × 5 + 1.5 TB | ~$1,500 |
| ElastiCache Redis (3 nodes) | cache.r6g.large × 3 | ~$600 |
| S3 (evidence, 2 TB) | Standard + IA | ~$50 |
| EKS standby (2 nodes) | t3.large × 2 | ~$200 |
| NAT Gateway | 2 (HA) | ~$130 |
| Route 53 | Health checks | ~$10 |
| VPN/Transit Gateway | TGW + data transfer | ~$300 |
| **AWS subtotal** | | **~$5,490** |

### Cross-cloud

| Component | Monthly |
|-----------|---------|
| VPN tunnels (Hetzner → AWS) | ~$0 (Hetzner side) + TGW charges (above) |
| Cross-cloud data transfer | ~$200-400 (500 GB egress through AWS) |
| **Cross-cloud subtotal** | **~$300** |

### Production Total

| Category | Monthly |
|----------|---------|
| Hetzner (compute) | ~$2,100 |
| AWS (managed stateful) | ~$5,500 |
| Cross-cloud | ~$300 |
| **Production total** | **~$7,900/mo** |

### All Environments

| Environment | Monthly |
|-------------|---------|
| Dev (Hetzner only) | ~$800 |
| Staging (Hetzner only) | ~$1,800 |
| Pilot (Hetzner only) | ~$3,500 |
| Production (hybrid) | ~$7,900 |
| **Total** | **~$14,000/mo** |

### Comparison

| Approach | Monthly | Annual |
|----------|---------|--------|
| AWS only (all envs) | $45k-$65k | $540k-$780k |
| Hetzner only (all envs) | $13k-$26k | $160k-$310k (+SRE staffing) |
| **Hybrid (recommended)** | **~$14k** | **~$170k** (minimal extra SRE) |

**The hybrid approach costs ~$14k/month — saving ~$31k-$51k/month vs AWS-only, while avoiding the 3-5 extra SRE FTEs needed for Hetzner-only.**

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| VPN latency exceeds 20ms p99 | HIGH | Load test early; move latency-sensitive services to AWS EKS if needed |
| VPN tunnel failure | HIGH | 2 redundant tunnels, BGP failover, alert on tunnel health |
| Cross-cloud data transfer costs | MEDIUM | Cache aggressively, use pre-signed URLs, batch operations |
| Self-managed K8s on Hetzner | MEDIUM | Use KubeOne or Cluster API for managed upgrades, maintain runbooks |
| Self-managed Vault on Hetzner | MEDIUM | 3-node Raft HA, auto-unseal via AWS KMS, encrypted backup to S3 |
| Neo4j self-managed on AWS | MEDIUM | Run on EKS with Causal Cluster, automated backups to S3 |
| Split-brain across providers | LOW | Route 53 health checks, DNS failover, tested DR procedure |

## 11. Implementation Steps

1. **Week 1:** Provision Hetzner cloud account, AWS account, set up VPN tunnels
2. **Week 2:** Deploy self-managed K8s on Hetzner (dev), deploy EKS standby on AWS
3. **Week 3:** Provision AWS managed services (RDS, MSK, OpenSearch, ElastiCache, S3)
4. **Week 4:** Deploy Vault HA on Hetzner, configure KMS auto-unseal
5. **Week 5:** Deploy GFIN services to Hetzner K8s, configure cross-cloud access
6. **Week 6:** Set up monitoring, alerting, DNS, load balancing
7. **Week 7:** Staging deployment + load test at 5,000 req/sec
8. **Week 8:** DR drill, pentest prep, go/no-go review
