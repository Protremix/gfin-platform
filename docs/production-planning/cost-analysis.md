# GFIN Infrastructure Cost Analysis — Luna Assessment

**Document ID:** GFIN-COST-001  
**Authority:** GPT Luna (GFIN-CEA) — LUNA-COST-ANALYSIS-001  
**Date:** 2026-08-26  
**Basis:** GFIN-WS-001 (workload sizing), GFIN-CPE-001 (cloud evaluation)  
**Accuracy:** ±30% (2026 on-demand pricing, US region assumed)  

---

## Monthly Cost Estimates

| Environment | AWS/month | GCP/month |
|-------------|-----------|-----------|
| Development | $4,000–$6,000 | $5,000–$7,500 |
| Staging | $7,000–$10,000 | $8,500–$12,000 |
| Pilot | $10,000–$15,000 | $12,000–$18,000 |
| Production | $24,000–$34,000 | $29,000–$42,000 |
| **Total (all envs)** | **$45,000–$65,000** | **$54,500–$79,500** |

AWS is cheaper because managed Kafka (MSK) and managed OpenSearch reduce ops overhead vs GCP's self-managed alternatives.

## Top 3 Cost Components

1. **Kubernetes compute** (~25-35% of total)
   - 5-8 production nodes + 4 environments
   - Optimization: Graviton/ARM instances, autoscaling, Spot for stateless workers, smaller non-prod pools

2. **OpenSearch** (~12-18%)
   - 5 nodes, 1.5 TB SSD, replicas
   - Optimization: hot/warm tiers, rollover policies, compression, S3 archival

3. **Kafka** (~10-16%)
   - 3-5 brokers, up to 1.5 TB SSD
   - Optimization: reduce retention, compress messages, tier/archive older events

## Commitment Strategy

- Purchase Savings Plans/Reserved Instances for 60-70% of stable compute (1-year commit)
- Leave 30-40% flexible for growth and experimentation
- Commit production K8s, PostgreSQL, Redis, always-on data services first
- Spot instances only for fault-tolerant workloads
- Expected savings: 20-30% (AWS), 15-25% (GCP)

## Minimum Viable Pilot (cheapest option)

AWS only:
- 3 small K8s workers
- Single-AZ PostgreSQL
- 3 small Kafka brokers
- Single Neo4j node
- 3 small OpenSearch nodes
- 2 Redis nodes
- Single Vault instance
- Reduced monitoring

**Estimated: $6,000–$10,000/month**

⚠️ Does NOT provide production-grade HA or prove 5,000 req/sec + 0% error targets.

## 12-Month Cost Trajectory

| Period | Phase | Monthly Cost |
|--------|-------|-------------|
| Months 1-3 | Pilot only | $6k–$10k |
| Months 4-6 | Staging + pilot | $15k–$25k |
| Months 7-9 | Production launch | $30k–$45k |
| Months 10-12 | Scaled production | $45k–$65k |

Data growth: ~1.1 TB (Year 1) → ~9 TB (Year 3)

## With Savings Plans (estimated)

| Period | Without Savings | With 60-70% Committed | Savings |
|--------|----------------|----------------------|---------|
| Months 1-3 | $6k–$10k | $5k–$8k | ~15% |
| Months 4-6 | $15k–$25k | $12k–$20k | ~20% |
| Months 7-9 | $30k–$45k | $22k–$34k | ~25% |
| Months 10-12 | $45k–$65k | $32k–$49k | ~25-30% |

## Annual Cost Summary

| Scenario | Year 1 (ramp) | Year 2 (steady-state) |
|----------|--------------|----------------------|
| On-demand (AWS) | ~$300k–$400k | ~$540k–$780k |
| With Savings Plans (AWS) | ~$230k–$310k | ~$400k–$580k |
| On-demand (GCP) | ~$360k–$500k | ~$650k–$950k |

## Recommendations

1. **Start with AWS** — managed services for Kafka and OpenSearch save significant ops cost
2. **Pilot at $6-10k/month** — validate the platform before committing to full production
3. **Buy Savings Plans at Month 4** — once pilot validates, commit to 1-year reserved for production baseline
4. **Monitor OpenSearch and Kafka costs** — these scale with data; implement retention/archival early
5. **Use Spot for stateless services** — web discovery, analytics, non-critical workers
6. **Budget for Year 2: $400-580k** (AWS with savings) — this is the steady-state production cost

## Uncertainty Note

Luna marked these estimates as ±30% accuracy. Final pricing requires:
- Specific AWS region (Frankfurt vs Ireland pricing differs)
- Instance family selection (Graviton vs x86)
- Actual utilization patterns
- Provider quotations / enterprise discount negotiation
- Data transfer costs (cross-region, cross-AZ)
