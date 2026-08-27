# GFIN Workload Sizing Document

**Document ID:** GFIN-WS-001  
**Date:** 2026-08-26  
**For:** Cloud cost estimation and infrastructure sizing  
**Directive:** LUNA-EXTERNAL-GUIDANCE-002  

---

## 1. Performance Targets (from G11 gate + benchmarks)

| Metric | Target | Source |
|--------|--------|--------|
| API throughput | 5,000 req/sec sustained | Gate G11 |
| API p99 latency | < 200ms | Gate G11, SLO definitions |
| Event bus throughput | 5,000+ events/sec | SLO test |
| Entity create p99 | < 10ms | MODULE-39 budget |
| Entity read p99 | < 20ms | Benchmark test |
| Entity resolution p99 | < 100ms | SLO test |
| Graph 1-hop query p99 | < 50ms | MODULE-39 budget |
| Graph 2-hop query p99 | < 200ms | MODULE-39 budget |
| Evidence create p99 | < 50ms | SLO test |
| Search query p99 | < 300ms | SLO test |
| AI gateway call p99 | < 5,000ms | SLO test |
| Cache get p99 | < 1ms | Benchmark test |
| Error rate | 0% | Gate G11 |

---

## 2. Service Inventory (18 core services)

| # | Service | CPU (est.) | Memory (est.) | Replicas | Storage |
|---|---------|-----------|---------------|----------|---------|
| 1 | API Gateway | 2 vCPU | 4 GB | 3 | — |
| 2 | Auth Service | 1 vCPU | 2 GB | 2 | — |
| 3 | Entity Resolution | 2 vCPU | 4 GB | 3 | — |
| 4 | Event Bus (Kafka) | 3 vCPU | 8 GB | 3 | 500 GB SSD |
| 5 | Evidence Vault | 1 vCPU | 2 GB | 2 | 1 TB S3 |
| 6 | Search Service | 2 vCPU | 8 GB | 2 | 100 GB SSD |
| 7 | Web Discovery | 1 vCPU | 2 GB | 2 | — |
| 8 | Fraud Detection | 2 vCPU | 4 GB | 3 | — |
| 9 | Campaign Engine | 2 vCPU | 4 GB | 2 | — |
| 10 | Alert Engine | 1 vCPU | 2 GB | 2 | — |
| 11 | AI Gateway | 2 vCPU | 4 GB | 2 | — |
| 12 | AI Investigation | 4 vCPU | 8 GB | 2 | — |
| 13 | Police API | 1 vCPU | 2 GB | 2 | — |
| 14 | Federation Service | 1 vCPU | 2 GB | 2 | — |
| 15 | Crypto Intelligence | 2 vCPU | 4 GB | 2 | — |
| 16 | Analytics | 2 vCPU | 4 GB | 2 | 50 GB SSD |
| 17 | Observability | 2 vCPU | 8 GB | 2 | 200 GB SSD |
| 18 | Compliance | 1 vCPU | 2 GB | 2 | — |

---

## 3. Infrastructure Components Sizing

### 3.1 Kubernetes Cluster

| Environment | Node Count | Node Type | Total vCPU | Total Memory | Notes |
|-------------|-----------|-----------|------------|-------------|-------|
| Dev | 2 | small (4 vCPU, 16 GB) | 8 | 32 GB | Single AZ, cost-optimized |
| Staging | 3 | medium (8 vCPU, 32 GB) | 24 | 96 GB | Multi-AZ, production-like |
| Pilot | 3 | medium (8 vCPU, 32 GB) | 24 | 96 GB | Production-like, limited data |
| Production | 5-8 | large (16 vCPU, 64 GB) | 80-128 | 320-512 GB | Multi-AZ, auto-scaling |

### 3.2 PostgreSQL

| Environment | Instance Type | Storage | HA | Read Replicas | IOPS |
|-------------|---------------|---------|-----|-------------|------|
| Dev | 2 vCPU, 8 GB | 50 GB SSD | No | 0 | 3,000 |
| Staging | 4 vCPU, 16 GB | 100 GB SSD | Yes (1 replica) | 1 | 6,000 |
| Pilot | 4 vCPU, 16 GB | 200 GB SSD | Yes (1 replica) | 1 | 6,000 |
| Production | 8 vCPU, 32 GB | 500 GB SSD | Yes (2 replicas) | 2 | 12,000 |

### 3.3 Kafka (Strimzi on K8s or MSK)

| Environment | Brokers | Broker Size | Topics | Partitions | Retention | Storage |
|-------------|---------|-------------|--------|------------|-----------|---------|
| Dev | 1 | 2 vCPU, 4 GB | 14 | 1 each | 24h | 20 GB |
| Staging | 3 | 4 vCPU, 8 GB | 14 | 3 each | 7d | 100 GB each |
| Pilot | 3 | 4 vCPU, 8 GB | 14 | 3 each | 7d | 100 GB each |
| Production | 3-5 | 8 vCPU, 16 GB | 14 | 6 each | 30d | 300 GB each |

### 3.4 Neo4j

| Environment | Instance Type | Storage | HA Mode | Notes |
|-------------|---------------|---------|---------|-------|
| Dev | 2 vCPU, 4 GB | 20 GB SSD | Single | — |
| Staging | 4 vCPU, 16 GB | 100 GB SSD | Causal Cluster (3) | — |
| Pilot | 4 vCPU, 16 GB | 200 GB SSD | Causal Cluster (3) | — |
| Production | 8 vCPU, 32 GB | 500 GB SSD | Causal Cluster (3) | Read replicas |

### 3.5 OpenSearch

| Environment | Nodes | Node Size | Storage | Shards | Replicas |
|-------------|-------|-----------|---------|--------|----------|
| Dev | 1 | 2 vCPU, 4 GB | 20 GB SSD | 1 | 0 |
| Staging | 3 | 4 vCPU, 16 GB | 100 GB SSD | 5 | 1 |
| Pilot | 3 | 4 vCPU, 16 GB | 100 GB SSD | 5 | 1 |
| Production | 5 | 8 vCPU, 32 GB | 300 GB SSD | 10 | 2 |

### 3.6 Redis

| Environment | Node Size | HA Mode | Cache Size |
|-------------|-----------|---------|------------|
| Dev | 1 vCPU, 2 GB | Single | 1 GB |
| Staging | 2 vCPU, 4 GB | Sentinel (3) | 4 GB |
| Pilot | 2 vCPU, 4 GB | Sentinel (3) | 4 GB |
| Production | 4 vCPU, 16 GB | Cluster (6) | 16 GB |

### 3.7 S3 / Object Storage (Evidence Vault)

| Environment | Storage | Requests | Lifecycle | Versioning | Encryption |
|-------------|---------|----------|-----------|------------|------------|
| Dev | 10 GB | Low | None | No | SSE-S3 |
| Staging | 100 GB | Medium | 30d → IA | Yes | SSE-KMS |
| Pilot | 500 GB | Medium | 90d → IA | Yes | SSE-KMS |
| Production | 2-10 TB | High | 90d → IA, 365d → Glacier | Yes | SSE-KMS + CMEK |

### 3.8 HashiCorp Vault

| Environment | Mode | Storage | HA | Notes |
|-------------|------|---------|-----|-------|
| Dev | dev mode | — | No | In-memory, dev token |
| Staging | Raft (3) | 10 GB SSD | Yes | Integrated storage |
| Pilot | Raft (3) | 10 GB SSD | Yes | Integrated storage |
| Production | Raft (5) | 50 GB SSD | Yes | Integrated storage, auto-unseal (KMS) |

---

## 4. Network & Security

| Component | Requirement | Notes |
|-----------|-----------|-------|
| VPC/VNet | Private subnets, 3 AZs | EU region |
| Load Balancer | Application LB (HTTPS), 5,000 req/sec | TLS termination |
| NAT Gateway | For outbound traffic | 2 per AZ |
| Private endpoints | For all managed services | Prevent public exposure |
| DDoS Protection | Shield/Cloud Armor | For public endpoints |
| WAF | Rules for API protection | SQLi, XSS, rate limiting |
| DNS | Private hosted zone | Internal service discovery |

---

## 5. Monitoring Stack

| Component | Sizing | Storage | Notes |
|-----------|--------|---------|-------|
| Prometheus | 2 vCPU, 8 GB | 200 GB SSD | 15-day retention |
| Grafana | 1 vCPU, 2 GB | 10 GB | 6 dashboards |
| AlertManager | 1 vCPU, 1 GB | 5 GB | Slack/email/PagerDuty |
| Loki (logs) | 2 vCPU, 4 GB | 100 GB | 30-day retention |

---

## 6. Estimated Resource Summary (Production)

| Resource | Production Total |
|----------|-----------------|
| K8s nodes | 5-8 nodes (80-128 vCPU, 320-512 GB RAM) |
| PostgreSQL | 8 vCPU, 32 GB, 500 GB + 2 replicas |
| Kafka | 3-5 brokers (24-40 vCPU, 48-80 GB, 900 GB-1.5 TB) |
| Neo4j | 3 nodes (24 vCPU, 96 GB, 1.5 TB) |
| OpenSearch | 5 nodes (40 vCPU, 160 GB, 1.5 TB) |
| Redis | 6 nodes (24 vCPU, 96 GB) |
| S3 | 2-10 TB |
| Vault | 5 nodes (10 vCPU, 20 GB, 250 GB) |
| Monitoring | 6 vCPU, 15 GB, 315 GB |
| **Total storage** | ~5-8 TB (SSD) + 2-10 TB (S3) |
| **Total compute** | ~220-360 vCPU |
| **Total memory** | ~800 GB - 1.2 TB |

---

## 7. Data Volume Estimates

| Data Type | Initial | Year 1 | Year 3 | Notes |
|-----------|---------|--------|--------|-------|
| Entities (PostgreSQL) | 100K records | 1M | 10M | 30+ entity types |
| Relationships (Neo4j) | 50K edges | 500K | 5M | 20+ relationship types |
| Evidence (S3) | 10 GB | 500 GB | 5 TB | Hash-verified files |
| Search index (OpenSearch) | 10 GB | 200 GB | 2 TB | Full-text index |
| Events (Kafka retention) | 30 GB | 300 GB | 1 TB | 30-day retention |
| Audit logs (Loki) | 5 GB | 100 GB | 500 GB | 30-day retention |
| Cache (Redis) | 1 GB | 8 GB | 16 GB | Hot entity data |
| **Total** | ~56 GB | ~1.1 TB | ~9 TB | |

---

## 8. Bandwidth Estimates

| Traffic Type | Daily | Monthly | Notes |
|-------------|-------|----------|-------|
| API requests | 432M req/day (5K/sec × 86K sec) | ~13B req/month | At peak throughput |
| Kafka events | 432M events/day | ~13B events/month | At peak throughput |
| Web discovery | 10 GB/day | 300 GB/month | Crawling outbound |
| Cross-border federation | 1 GB/day | 30 GB/month | Inter-node communication |
| Backups | 5 GB/day | 150 GB/month | Incremental |
| **Total egress** | ~15 GB/day | ~500 GB/month | — |
