# GFIN Police Server Migration Architecture

**Document ID:** GFIN-POLICE-001  
**Authority:** GPT Luna (GFIN-CEA) — LUNA-POLICE-ARCH-001  
**Date:** 2026-08-26  
**For:** Rojs (Project Owner)  
**Strategy:** Temporary Hetzner → Police-owned servers  

---

## Architecture Overview

```
PHASE 1: TEMPORARY (HETZNER)              PHASE 2: TARGET (POLICE SERVERS)
┌────────────────────────────┐            ┌────────────────────────────┐
│  Hetzner (Germany)         │            │  Police Data Center         │
│                            │            │                             │
│  3 × AX62 dedicated nodes  │  MIGRATE   │  3+ bare metal servers      │
│  Self-managed K8s (k3s)    │ ────────►  │  Same K8s manifests          │
│                            │            │  Same containers            │
│  ALL in containers:        │            │  Same Helm charts           │
│  ├── 18 GFIN services      │            │  ├── 18 GFIN services       │
│  ├── PostgreSQL (Patroni)  │            │  ├── PostgreSQL (Patroni)   │
│  ├── Kafka (Strimzi)       │            │  ├── Kafka (Strimzi)       │
│  ├── Neo4j                 │            │  ├── Neo4j                  │
│  ├── OpenSearch            │            │  ├── OpenSearch             │
│  ├── Redis                 │            │  ├── Redis                  │
│  ├── MinIO (S3-compat)     │            │  ├── MinIO (S3-compat)      │
│  ├── Vault                 │            │  ├── Vault                  │
│  └── Monitoring stack      │            │  └── Monitoring stack       │
│                            │            │                             │
│  Everything self-managed   │            │  Same setup, different iron  │
│  Everything containerized  │            │  Police-controlled network   │
│  Zero cloud lock-in        │            │  Full data sovereignty       │
└────────────────────────────┘            └────────────────────────────┘
```

## Key Principle: Zero Cloud Lock-In

NO managed services. Everything runs in containers with standard upstream images. The migration from Hetzner to police servers is a lift-and-shift of containers + data export/import.

---

## 1. Temporary Hetzner Setup

### Hardware (buy now)

| Component | Qty | Spec | Monthly Cost |
|-----------|-----|------|-------------|
| AX62 dedicated servers | 3 | AMD Ryzen 9, 64+ GB RAM, 1+ TB NVMe | ~€100-150/mo each |
| Hetzner Object Storage | 2-5 TB | S3-compatible | ~€12-30/mo |
| Private network | 1 | vSwitch | Free |
| Load Balancer | 1 | Hetzner LB | ~€10/mo |
| **Total** | | | **~€350-490/mo (~$400-575/mo)** |

### Software stack (all self-managed, all containerized)

| Component | Container | Helm Chart | Notes |
|-----------|-----------|------------|-------|
| Kubernetes | k3s or kubeadm | — | Lightweight, portable |
| PostgreSQL | postgres:16 + Patroni | bitnami/postgresql-ha | HA, replication, PITR via WAL archiving to MinIO |
| Kafka | Strimzi operator | strimzi-kafka | 3 brokers on K8s |
| Neo4j | neo4j:5 | neo4j helm | Causal cluster (3 nodes) |
| OpenSearch | opensearch:2 | opensearch-helm | 3 nodes, 1 replica |
| Redis | redis:7 + Sentinel | bitnami/redis-ha | HA cluster |
| MinIO | minio/minio | minio helm | S3-compatible, replace with police storage later |
| Vault | vault:1.18 + Raft | hashicorp/vault | 3 nodes, auto-unseal optional |
| Monitoring | prometheus + grafana + loki | kube-prometheus-stack | All in K8s |
| Ingress | nginx-ingress or traefik | standard | TLS termination |

### Portability rules

- All services as OCI container images (pinned versions)
- All config via environment variables + K8s ConfigMaps/Secrets
- All persistent data on mounted volumes (no cloud-specific storage APIs)
- All infrastructure as Helm charts or K8s manifests
- No Hetzner-specific APIs in application code
- Database versions pinned (PostgreSQL 16, Neo4j 5, OpenSearch 2, Redis 7)

---

## 2. Police Server Target Architecture

### What to ask police IT to prepare:

| Requirement | Spec | Priority |
|-------------|------|----------|
| Server hardware | 3+ servers, 16+ vCPU each, 128+ GB RAM each, 2+ TB NVMe each | CRITICAL |
| Network | Internal VLANs, firewall, VPN access for engineers | CRITICAL |
| OS | Ubuntu 22.04 LTS or RHEL 9 (for K8s) | CRITICAL |
| Container runtime | containerd (ships with K8s) | CRITICAL |
| Kubernetes | v1.28+ (k3s or kubeadm) | CRITICAL |
| Storage | Hardware RAID or Ceph/Longhorn for K8s volumes | CRITICAL |
| Load balancer | Hardware LB or HAProxy/NGINX on dedicated node | HIGH |
| DNS | Internal DNS for service discovery | HIGH |
| Identity | OIDC/OAuth2 integration (police directory) | HIGH |
| Backup storage | 5+ TB for database dumps, WAL archives, snapshots | HIGH |
| SIEM | Log integration with police security operations | MEDIUM |
| Certificate authority | Internal CA for mTLS or Let's Encrypt | MEDIUM |
| Air-gap capability | If required for classified data | DEPENDS |
| Data residency | Confirm all data stays within jurisdiction | CRITICAL |

### Target server sizing (police)

| Role | Servers | Spec each | Total |
|------|---------|-----------|-------|
| K8s control plane | 3 | 8 vCPU, 32 GB, 500 GB | Small, dedicated |
| K8s worker nodes | 5-8 | 16 vCPU, 64 GB, 2 TB NVMe | Runs all services + infra |
| **Total** | 8-11 | | ~140-160 vCPU, 416-576 GB, 11-17 TB |

---

## 3. Data Migration Plan

### Step-by-step: Hetzner → Police Servers

```
Week 1: PREPARE
  ├── Deploy K8s on police servers (same manifests as Hetzner)
  ├── Deploy all infrastructure containers (same Helm charts)
  ├── Configure networking, firewall, VPN, DNS
  └── Verify: all pods running, health checks pass

Week 2: TEST MIGRATION
  ├── Export from Hetzner:
  │   ├── PostgreSQL: pg_dumpall (schema + data)
  │   ├── Neo4j: neo4j-admin dump
  │   ├── OpenSearch: snapshot to MinIO/S3
  │   ├── Kafka: topic configs + MirrorMaker 2 replay
  │   ├── MinIO: rclone sync to police storage
  │   └── Vault: raft snapshot
  ├── Transfer over encrypted VPN or physical media
  ├── Restore on police servers
  ├── Validate: record counts, checksums, sample queries
  └── Fix: any issues, document procedures

Week 3: CUTOVER
  ├── Enable maintenance mode on Hetzner (stop writes)
  ├── Take final incremental exports
  ├── Transfer + restore final data
  ├── Validate: full reconciliation (counts, checksums, integrity)
  ├── Switch DNS/load balancer to police servers
  ├── Monitor: error rate, latency, throughput for 24h
  └── Keep Hetzner read-only as fallback for 7 days

Week 4: VERIFY + DECOMMISSION
  ├── Run full test suite on police servers
  ├── Load test at target throughput
  ├── Security scan
  ├── DR drill on police infrastructure
  ├── Get signed acceptance from police IT
  └── Decommission Hetzner (cancel servers, wipe data)
```

### Export formats (all standard, no lock-in)

| Component | Export Method | Restore Method | Est. Time (1 TB) |
|-----------|---------------|----------------|-------------------|
| PostgreSQL | `pg_dumpall` or `pg_basebackup` | `psql` restore or PITR | 2-4 hours |
| Neo4j | `neo4j-admin database dump` | `neo4j-admin database load` | 1-2 hours |
| OpenSearch | Snapshot to repository (S3/MinIO) | Restore from repository | 1-3 hours |
| Kafka | MirrorMaker 2 or topic export | Replay or import | 2-6 hours |
| MinIO/S3 | `rclone sync` or `aws s3 sync` | `rclone sync` to target | 3-8 hours |
| Vault | `vault operator raft snapshot save` | `vault operator raft snapshot restore` | < 1 hour |

---

## 4. Cost Summary

### Temporary (Hetzner) — until police servers ready

| Component | Monthly |
|-----------|---------|
| 3 × AX62 servers | ~$300-450 |
| Object storage (5 TB) | ~$30 |
| Load balancer | ~$10 |
| Backups (off-site) | ~$20 |
| **Total** | **~$360-510/mo** |

### One-time migration cost

| Item | Cost |
|------|------|
| Migration engineer time | 2-3 weeks of work |
| Physical media (if air-gapped) | ~$200-500 |
| VPN setup | ~$0 (self-managed) |
| Test environment on police servers | Included in police IT budget |
| **Total** | **~$0 (if team does it) or $5k-15k (if contracted)** |

### Police servers (ongoing)

| Component | Cost |
|-----------|------|
| Hardware (if new purchase) | $30k-80k one-time (8-11 servers) |
| Hardware (if existing) | $0 |
| Power + cooling + space | Included in police facility |
| Network/internet | Included in police network |
| **Monthly operational** | **~$0 (no cloud fees — it's their hardware)** |

---

## 5. What to Buy NOW (Hetzner)

| Item | Qty | Cost | Action |
|------|-----|------|--------|
| AX62 dedicated server | 3 | ~€120/mo each | Order from hetzner.com |
| Hetzner Object Storage | 5 TB | ~€30/mo | Enable in Hetzner Console |
| Hetzner Load Balancer | 1 | ~€10/mo | Enable in Hetzner Console |
| Domain name | 1 | ~€10/year | For DNS + TLS |
| WireGuard VPN | — | Free | Configure between nodes |
| **Total setup** | | **~€400/mo** | Same day |

### First 24 hours after ordering:
1. SSH into 3 AX62 servers
2. Install k3s (one-liner: `curl -sfL https://get.k3s.io | sh -`)
3. Join all 3 nodes to cluster
4. Install Helm
5. Deploy GFIN infrastructure Helm charts
6. Deploy GFIN services
7. Configure MinIO for evidence storage
8. Set up backups to Hetzner Object Storage
9. Run health checks

---

## 6. What to Ask Police IT NOW

Send this checklist to the police IT department:

```
GFIN INFRASTRUCTURE REQUIREMENTS — POLICE SERVERS

Please confirm availability of:

□ 3+ physical servers (16+ vCPU, 128+ GB RAM, 2+ TB NVMe each)
□ Internal network with VLANs and firewall
□ VPN access for engineering team
□ Ubuntu 22.04 LTS or RHEL 9 installed
□ Container runtime (containerd)
□ 5+ TB backup storage
□ Internal DNS resolution
□ Certificate authority (internal CA or Let's Encrypt)
□ OIDC/OAuth2 identity provider integration
□ SIEM log integration endpoint
□ Approved container registry (or Harbor/Artifactory)
□ Data residency confirmation (all data within [jurisdiction])
□ Air-gap requirements (if applicable)
□ Approved software list (confirm K8s, PostgreSQL, Kafka, Neo4j, Redis, OpenSearch)
□ Migration test window (1 week for test, 1 week for cutover)
□ Acceptance criteria and sign-off authority

Target date for police server readiness: ___________
```
