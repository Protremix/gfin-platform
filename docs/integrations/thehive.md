# GFIN — TheHive Evaluation (REJECTION)

**Version:** 1.0
**Status:** REJECTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

TheHive has been evaluated for case management integration with GFIN and **rejected**. This document records the evaluation findings and rationale.

## Official Sources

| Resource | URL |
|----------|-----|
| Repository (ARCHIVED) | https://github.com/TheHive-Project/TheHive |
| Website | https://strangebee.com |
| Documentation | https://docs.strangebee.com/thehive/ |
| Python SDK | https://github.com/TheHive-Project/thehive4py |

## License

- **TheHive v4:** AGPLv3 (open source, repository archived Dec 5, 2025)
- **TheHive v5:** Commercial/Proprietary (StrangeBee, freemium model)

## Rejection Rationale

### 1. Repository Archived

The TheHive open-source repository was officially archived on **December 5, 2025**. TheHive 5 is now closed-source commercial software. This eliminates the open-source path and introduces commercial license dependencies.

### 2. Domain Mismatch

| Dimension | TheHive | GFIN |
|-----------|---------|------|
| Domain | Cybersecurity incident response (SOC/CSIRT) | Financial crime, AML, fraud detection |
| Core primitives | IOCs, MITRE ATT&CK, network observables | Bank accounts, transactions, compliance workflows |
| Entity model | IP, hash, URL, file | Person, phone, domain, crypto wallet, payment ID |
| Workflow | Alert → Case → Task → Observable → Cortex | Report → Entity → Campaign → Alert → Police API |
| Regulatory | None | SAR/STR filing, jurisdiction compliance |

### 3. Infrastructure Overhead

TheHive requires Apache Cassandra + Elasticsearch/OpenSearch + S3 storage. This is a heavy, resource-intensive stack (16-64 GB RAM) that creates unnecessary operational overhead alongside GFIN's existing infrastructure.

### 4. Feature Redundancy

GFIN's planned case management model (Module 12: Case Management) already covers investigation workflows natively. Integrating TheHive would create duplication and schema shoehorning.

### 5. Commercial Lock-in

TheHive 5's freemium model limits: 1 organization, 2 analyst profiles, single MISP/Cortex connection. Enterprise features require paid licensing. This is incompatible with GFIN's multi-organization, federation-first architecture.

## Alternative

GFIN builds its own domain-native case management model (Module 12) that natively represents:
- Financial entities (bank accounts, transactions, crypto wallets)
- Fraud-specific workflows (report → triage → investigation → police referral)
- Regulatory compliance (SAR/STR, jurisdiction, classification)
- GFIN's entity graph and campaign model

## Conclusion

**Recommendation: REJECT.** Do not integrate TheHive. The domain mismatch, infrastructure overhead, archived open-source repository, and commercial lock-in make it unsuitable for GFIN.

## Status

| Component | Status |
|-----------|--------|
| Evaluation | COMPLETE |
| Decision | REJECTED |
| ADR | ADR-010 (REJECTED) |
