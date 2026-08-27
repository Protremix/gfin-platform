# GFIN Hetzner Evaluation

**Document ID:** GFIN-HETZNER-001  
**Authority:** GPT Luna (GFIN-CEA) — LUNA-HETZNER-EVAL-001  
**Date:** 2026-08-26  
**For:** Rojs (Project Owner)  

---

## Verdict: Conditional Yes — Hybrid Recommended

Hetzner is technically viable for compute and storage at a fraction of AWS costs, but GFIN would assume full operational burden for 8 self-managed infrastructure components.

## Cost Comparison

| Environment | AWS/mo | Hetzner/mo | Savings |
|-------------|--------|------------|---------|
| Development | $4k–$6k | $0.8k–$1.5k | ~75% |
| Staging | $7k–$10k | $1.5k–$3k | ~70% |
| Pilot | $10k–$15k | $3k–$6k | ~60% |
| Production | $24k–$34k | $8k–$15k | ~55% |
| **All envs** | **$45k–$65k** | **$13k–$26k** | **~60%** |

**Year 1 savings (Hetzner vs AWS): ~$150k–$280k**

But: Hetzner requires 3-5 additional platform/SRE FTEs for self-managed ops. At ~$80k-120k/FTE/year, that's $240k-$600k/year in staffing — which can exceed the infrastructure savings.

## Hetzner Strengths

1. **Massive cost savings** — 60-75% cheaper than AWS for raw compute/storage
2. **EU data residency** — German data centers (Falkenstein, Nuremberg), Helsinki
3. **GDPR compliant** — ISO 27001, C5 (BSI) certified, standard DPA
4. **20 TB traffic included** per EU cloud server (vs AWS charging for all egress)
5. **S3-compatible object storage** — €5.99/TB (vs AWS ~$23/TB)
6. **Dedicated servers** from €59/mo — excellent for K8s nodes
7. **No egress surprise** — predictable costs

## Hetzner Weaknesses

1. **NO managed Kubernetes** — must self-manage (kubeadm, KubeOne, Cluster API)
2. **NO managed PostgreSQL** — must self-manage (Patroni, backups, replication)
3. **NO managed Kafka** — must self-manage (Strimzi on K8s or bare Kafka)
4. **NO managed Neo4j** — must self-manage
5. **NO managed OpenSearch** — must self-manage
6. **NO managed Redis** — must self-managed
7. **NO managed Vault** — must self-manage (same as AWS, actually)
8. **Price increases** — Hetzner raised prices 2-3x in June 2026

## Risk Profile: MEDIUM-HIGH

Self-managing 8 infrastructure components creates:
- Correlated failure risks (K8s upgrade breaks Kafka, which breaks event bus)
- Backup/restore risk (no managed PITR for PostgreSQL)
- Security patching across 8 components
- 24/7 on-call coverage needed
- DR drill complexity (all components must failover manually)

## Luna's Recommendation: HYBRID

| Layer | Host on | Rationale |
|-------|---------|-----------|
| Dev environment | Hetzner | Cheapest, lowest risk |
| Staging environment | Hetzner | Cost-efficient, can tolerate downtime |
| Pilot environment | Hetzner (compute) + AWS (managed DB) | Validate platform, reduce DB ops |
| Production (stateful) | AWS managed | PostgreSQL RDS, MSK Kafka, OpenSearch |
| Production (stateless) | Hetzner or AWS | API gateway, services, batch workers |

### Why hybrid:
- Stateful services (PostgreSQL, Kafka, Neo4j, OpenSearch) are the hardest to self-manage and the riskiest if they fail
- Stateless compute (18 GFIN services) can run anywhere — Hetzner is perfect for this
- Dev/staging on Hetzner saves ~75% with acceptable risk
- Production stateful on AWS provides managed HA, backups, monitoring

## Hetzner Pricing Reference (post-June 2026)

### Cloud (dedicated vCPU)
| Instance | vCPU | RAM | NVMe | Monthly |
|----------|------|-----|------|---------|
| CCX13 | 2 | 8 GB | 80 GB | €43.49 (~$51) |
| CCX23 | 4 | 16 GB | 160 GB | €86.49 (~$101) |
| CCX33 | 8 | 32 GB | 240 GB | €138.99 (~$163) |
| CCX43 | 16 | 64 GB | 360 GB | €279.49 (~$329) |

### Dedicated Servers (AX line)
| Server | Starting Price |
|--------|---------------|
| AX41 (AMD Ryzen 5) | €59/mo (~$69) |
| Higher specs available | €59-117/mo |

### Object Storage (S3-compatible)
| Component | Price |
|-----------|-------|
| Base (1 TB storage + 1 TB traffic) | €5.99/mo (~$7) |
| Additional storage | €5.99/TB |
| Additional traffic | €1.20/TB |
| Compare AWS S3 | ~$23/TB + $0.09/GB egress |

## Team Requirements

| Approach | Additional SRE/Platform FTEs | Annual Staffing Cost |
|----------|---------------------------|---------------------|
| AWS only | 0 (managed services) | $0 extra |
| Hetzner only | 3-5 FTEs | $240k-$600k/yr |
| Hybrid (Luna recommended) | 1-2 FTEs | $80k-$240k/yr |

## Final Decision Matrix

| Approach | Infra Cost/yr | Staffing Cost/yr | Total Year 1 | Risk |
|----------|-------------|-----------------|-------------|------|
| AWS only (with savings) | $230k-$310k | $0 | $230k-$310k | LOW |
| Hetzner only | $160k-$310k | $240k-$600k | $400k-$910k | MEDIUM-HIGH |
| Hybrid (recommended) | $180k-$260k | $80k-$240k | $260k-$500k | MEDIUM |

**Luna's recommendation: Hybrid approach. Start with Hetzner for dev/staging/pilot, use AWS managed services for production stateful components. Reassess Hetzner-only after pilot proves operational readiness.**
