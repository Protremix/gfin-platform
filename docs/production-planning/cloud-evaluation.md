# GFIN Cloud Provider Evaluation Matrix

**Document ID:** GFIN-CPE-001  
**Date:** 2026-08-26  
**For:** Rojs (Project Owner) — decision input  
**Directive:** LUNA-EXTERNAL-GUIDANCE-002  

---

## Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Data residency (GDPR) | CRITICAL | EU data center availability, GDPR compliance, data sovereignty |
| Managed K8s | HIGH | EKS/GKE/AKS quality, pricing, auto-scaling |
| Managed PostgreSQL | HIGH | HA, backups, read replicas, point-in-time recovery |
| Managed Kafka | HIGH | MSK/Confluent/Event Hubs — reduces ops burden |
| Managed Neo4j | MEDIUM | AuraDB availability or self-managed on K8s |
| Managed OpenSearch | MEDIUM | Managed service vs self-hosted |
| Object storage (S3) | HIGH | Durability, lifecycle, versioning, encryption |
| Redis | MEDIUM | Managed vs self-hosted |
| Secrets management | MEDIUM | Managed Vault or self-hosted |
| Monitoring | LOW | Prometheus/Grafana — self-hosted regardless |
| Network security | HIGH | VPC, private endpoints, DDoS protection, WAF |
| Cost (estimated) | HIGH | See workload sizing (GFIN-WS-001) |
| Team familiarity | MEDIUM | Existing expertise reduces ramp-up time |
| EU region availability | CRITICAL | Frankfurt, Paris, Amsterdam, Ireland |
| Compliance certifications | HIGH | SOC 2, ISO 27001, FedRAMP, criminal justice data |

---

## Provider Comparison

### AWS

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Data residency (GDPR) | ✅ EXCELLENT | eu-central-1 (Frankfurt), eu-west-1 (Ireland), GDPR DPA available |
| Managed K8s (EKS) | ✅ EXCELLENT | Mature, auto-scaling, Spot instances, well-documented |
| Managed PostgreSQL (RDS) | ✅ EXCELLENT | HA, read replicas, automated backups, PITR |
| Managed Kafka (MSK) | ✅ GOOD | Fully managed, but Strimzi on EKS is also viable |
| Managed Neo4j | ⚠️ SELF-MANAGED | AuraDB is separate SaaS, not integrated; self-host on EKS |
| Managed OpenSearch | ✅ GOOD | Managed OpenSearch Service (was Elasticsearch) |
| Object storage (S3) | ✅ EXCELLENT | Industry standard, lifecycle, versioning, KMS encryption |
| Redis (ElastiCache) | ✅ GOOD | Managed Redis with clustering |
| Secrets (Secrets Manager) | ⚠️ ADEQUATE | AWS Secrets Manager works, but Vault self-hosted is preferred |
| Network security | ✅ EXCELLENT | VPC, PrivateLink, WAF, Shield, Security Groups |
| Compliance | ✅ EXCELLENT | SOC 2, ISO 27001, many certifications |
| Cost | ⚠️ MODERATE-HIGH | Pay-as-you-go, can be expensive at scale; Savings Plans help |
| Team familiarity | TBD | — |

### Google Cloud Platform (GCP)

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Data residency (GDPR) | ✅ EXCELLENT | europe-west3 (Frankfurt), europe-west1 (Belgium), GDPR terms |
| Managed K8s (GKE) | ✅ EXCELLENT | Best-in-class managed K8s, autopilot mode, cost-efficient |
| Managed PostgreSQL (Cloud SQL) | ✅ GOOD | HA, read replicas, automated backups |
| Managed Kafka | ⚠️ LIMITED | Pub/Sub is NOT Kafka; Confluent Cloud on GCP is an option |
| Managed Neo4j | ⚠️ SELF-MANAGED | AuraDB available on GCP Marketplace; self-host on GKE |
| Managed OpenSearch | ⚠️ SELF-MANAGED | No managed service; self-host on GKE |
| Object storage (GCS) | ✅ EXCELLENT | Nearline/Coldline, lifecycle, versioning, CMEK |
| Redis (Memorystore) | ✅ GOOD | Managed Redis |
| Secrets (Secret Manager) | ⚠️ ADEQUATE | GCP Secret Manager works; Vault self-hosted preferred |
| Network security | ✅ EXCELLENT | VPC, Cloud Armor, private endpoints |
| Compliance | ✅ GOOD | SOC 2, ISO 27001 |
| Cost | ✅ MODERATE | Often cheaper than AWS; sustained-use discounts |
| Team familiarity | TBD | — |

### Microsoft Azure

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Data residency (GDPR) | ✅ EXCELLENT | West Europe (Netherlands), North Europe (Ireland), GDPR terms |
| Managed K8s (AKS) | ✅ GOOD | Solid managed K8s, auto-scaling |
| Managed PostgreSQL (Azure DB) | ✅ GOOD | Flexible Server, HA, read replicas |
| Managed Kafka | ⚠️ LIMITED | Event Hubs is NOT Kafka (Kafka-compatible API); Confluent on Azure |
| Managed Neo4j | ⚠️ SELF-MANAGED | Self-host on AKS |
| Managed OpenSearch | ⚠️ SELF-MANAGED | No managed service; self-host on AKS |
| Object storage (Blob) | ✅ EXCELLENT | Hot/Cool/Archive tiers, lifecycle, encryption |
| Redis (Azure Cache) | ✅ GOOD | Managed Redis |
| Secrets (Key Vault) | ⚠️ ADEQUATE | Key Vault works; Vault self-hosted preferred |
| Network security | ✅ EXCELLENT | VNet, Private Link, DDoS Protection, WAF |
| Compliance | ✅ EXCELLENT | SOC 2, ISO 27001, strong enterprise compliance |
| Cost | ⚠️ MODERATE-HIGH | Comparable to AWS; enterprise agreements can reduce |
| Team familiarity | TBD | — |

### On-Premises

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Data residency (GDPR) | ✅ EXCELLENT | Full control, data never leaves premises |
| Managed K8s | ❌ SELF-MANAGED | Full ops burden — kubeadm/Rancher/OpenShift |
| Managed PostgreSQL | ❌ SELF-MANAGED | Full ops burden — Patroni, backups, replication |
| Managed Kafka | ❌ SELF-MANAGED | Full ops burden — Strimzi or bare Kafka |
| Managed Neo4j | ❌ SELF-MANAGED | Full ops burden |
| Managed OpenSearch | ❌ SELF-MANAGED | Full ops burden |
| Object storage | ❌ SELF-MANAGED | MinIO or similar |
| Redis | ❌ SELF-MANAGED | Full ops burden |
| Secrets | ❌ SELF-MANAGED | Vault self-hosted (same as cloud) |
| Network security | ✅ GOOD | Full control, physical isolation |
| Compliance | ⚠️ VARIES | Must self-certify; dependent on facility |
| Cost | ⚠️ HIGH UPFRONT | CapEx (hardware) + OpEx (staffing, power, cooling, space) |
| Team familiarity | TBD | — |

---

## Scoring Matrix

| Criterion | Weight | AWS | GCP | Azure | On-Prem |
|-----------|--------|-----|-----|-------|---------|
| Data residency (GDPR) | CRITICAL | 5 | 5 | 5 | 5 |
| Managed K8s | HIGH | 5 | 5 | 4 | 1 |
| Managed PostgreSQL | HIGH | 5 | 4 | 4 | 1 |
| Managed Kafka | HIGH | 4 | 2 | 2 | 1 |
| Managed Neo4j | MEDIUM | 2 | 2 | 2 | 1 |
| Managed OpenSearch | MEDIUM | 4 | 1 | 1 | 1 |
| Object storage | HIGH | 5 | 5 | 5 | 2 |
| Redis | MEDIUM | 4 | 4 | 4 | 1 |
| Secrets management | MEDIUM | 3 | 3 | 3 | 3 |
| Monitoring | LOW | 3 | 3 | 3 | 3 |
| Network security | HIGH | 5 | 5 | 5 | 4 |
| Cost | HIGH | 3 | 4 | 3 | 2 |
| Compliance | HIGH | 5 | 4 | 5 | 2 |
| **Weighted Score** | | **4.3** | **3.9** | **3.7** | **1.9** |

---

## Recommendation

**Primary: AWS** (highest managed-service coverage for GFIN's stack)
- EKS, RDS PostgreSQL, MSK (or Strimzi on EKS), OpenSearch Service, S3, ElastiCache
- Strongest managed OpenSearch and managed Kafka options
- Best compliance certification coverage
- Vault self-hosted on EKS (standard pattern)

**Alternative: GCP** (best K8s, cost-efficient, but Kafka gap)
- GKE is best-in-class, cost-efficient
- Gap: no managed Kafka or OpenSearch — would need Confluent Cloud + self-hosted OpenSearch
- Good if team has GCP expertise and Kafka can be outsourced to Confluent

**Not recommended: On-premises** for initial deployment
- Full ops burden for 8+ infrastructure components
- Only viable if data sovereignty requirements mandate it
- Revisit if GFIN has strict air-gap requirements for police data

**Not recommended: Azure** for this stack
- Kafka gap (Event Hubs is not Kafka)
- No managed OpenSearch
- Only choose if existing enterprise agreement or team expertise

---

## Next Steps

1. Confirm team familiarity with each provider
2. Get pricing quotes for the workload sizing (GFIN-WS-001)
3. Check data residency requirements with legal team
4. Decide within Week 1 of externalization phase
