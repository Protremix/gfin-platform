# GFIN Infrastructure Deployment Runbook
**Version:** 1.0  
**Date:** 2026-08-26  
**Status:** REQUIRES EXTERNAL INFRASTRUCTURE  
**Classification:** PUBLIC  

---

## 1. Overview

This runbook covers the provisioning of the GFIN hybrid cloud architecture:
- **Hetzner Cloud (Nuremberg)** — Stateless compute (K3s cluster)
- **AWS Frankfurt (eu-central-1)** — Stateful managed services (RDS, MSK, OpenSearch, ElastiCache, S3)

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    Internet                              │
│                        │                                 │
│         ┌─────────────┴─────────────┐                   │
│         │  Hetzner Cloud (nbg1)      │                   │
│         │  ┌─────────────────────┐   │                   │
│         │  │ K3s Master (cpx21) │   │                   │
│         │  │  ┌───────┐ ┌──────┐│   │                   │
│         │  │  │Worker1│ │Worker2││   │                   │
│         │  │  │cpx31  │ │cpx31 ││   │                   │
│         │  │  └───────┘ └──────┘│   │                   │
│         │  └─────────────────────┘   │                   │
│         │  Private: 10.0.1.0/24       │                   │
│         └─────────────┬─────────────┘                   │
│                       │ TLS/Tunnel                       │
│         ┌─────────────┴─────────────┐                   │
│         │  AWS Frankfurt (eu-central-1)│                │
│         │  ┌──────────────────────┐   │                │
│         │  │ VPC 172.16.0.0/16     │   │                │
│         │  │  RDS PostgreSQL 16   │   │                │
│         │  │  MSK Kafka 3.7.1     │   │                │
│         │  │  OpenSearch 2.18    │   │                │
│         │  │  ElastiCache Redis 7│   │                │
│         │  │  S3 Evidence (WORM) │   │                │
│         │  └──────────────────────┘   │                │
│         └─────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites

### 2.1 Credentials Required
| Credential | Source | Environment Variable |
|---|---|---|
| Hetzner Cloud API Token | https://console.hetzner.cloud | `TF_VAR_hetzner_token` |
| AWS Access Key + Secret | AWS IAM Console | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` |
| OpenAI API Key | https://platform.openai.com | `OPENAI_PROJECT_KEY` |

### 2.2 Tools Required
- Terraform >= 1.5.0
- kubectl >= 1.28
- Helm >= 3.13
- OpenSSL (for TLS cert generation)
- jq

### 2.3 SSH Key Pair
```bash
ssh-keygen -t ed25519 -f ~/.ssh/gfin_cluster -C "gfin-cluster"
# The public key is referenced in hetzner.tf
```

---

## 3. Deployment Sequence

### Phase 1: Terraform State Backend (Manual, One-Time)

The S3 bucket and DynamoDB table for Terraform state must exist before `terraform init`.

```bash
# Create from AWS CLI
aws s3api create-bucket \
  --bucket gfin-terraform-state \
  --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1

aws s3api put-bucket-versioning \
  --bucket gfin-terraform-state \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name gfin-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-central-1
```

> **Note:** These resources are also defined in `aws-stateful.tf` but cannot bootstrap themselves. Create manually first, then import:
> ```bash
> terraform import aws_s3_bucket.terraform_state gfin-terraform-state
> terraform import aws_dynamodb_table.terraform_locks gfin-terraform-locks
> ```

---

### Phase 2: Terraform Plan + Apply

```bash
cd infrastructure/terraform

# ─── Set Credentials ───
export TF_VAR_hetzner_token="hcloud-token-here"
export TF_VAR_db_password="$(openssl rand -base64 32)"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

# ─── Initialize ───
terraform init

# ─── Plan (review all changes) ───
terraform plan -out gfin-plan.tfplan

# ─── Apply ───
terraform apply gfin-plan.tfplan

# ─── Save Outputs ───
terraform output -json > /tmp/gfin-outputs.json
```

**Expected Resources Created:**
| Resource | Count | Provider |
|---|---|---|
| Hetzner servers (1 master + 3 workers) | 4 | hcloud |
| Hetzner firewall | 1 | hcloud |
| Hetzner private network + subnet | 2 | hcloud |
| AWS VPC + subnets | 1 module | aws |
| RDS PostgreSQL 16 | 1 | aws |
| MSK Kafka 3.7.1 (3 brokers) | 1 | aws |
| OpenSearch 2.18 (3 nodes) | 1 | aws |
| ElastiCache Redis 7.1 | 1 | aws |
| S3 buckets (evidence + logs) | 2 | aws |
| KMS key | 1 | aws |
| Security groups | 4 | aws |
| CloudWatch log groups | 2 | aws |

**Estimated Provisioning Time:** 25-45 minutes  
(MSK is the longest — ~20 min. RDS ~10 min. OpenSearch ~15 min.)

---

### Phase 3: K3s Cluster Verification

After Terraform completes, the Hetzner nodes auto-bootstrap K3s via user_data scripts. Verify:

```bash
# Get master IP from Terraform output
MASTER_IP=$(terraform output -raw hetzner_master_ip)

# SSH to master and verify cluster
ssh root@$MASTER_IP

# On master:
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get nodes
# EXPECT: 4 nodes (1 master + 3 workers), all Ready

kubectl get pods -A
# EXPECT: CoreDNS, metrics-server, local-path-provisioner running

kubectl get networkpolicy -A
# EXPECT: gfin-default-deny in default namespace
```

---

### Phase 4: Configure K8s Secrets for AWS Services

```bash
# On K3s master — create secrets with AWS service endpoints
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Read Terraform outputs (run from your local machine, copy values to master)
POSTGRES_ENDPOINT=$(terraform output -raw postgres_endpoint)
KAFKA_BROKERS=$(terraform output -raw kafka_bootstrap_brokers)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
EVIDENCE_BUCKET=$(terraform output -raw evidence_bucket)

# Create Kubernetes secrets
kubectl create namespace gfin

kubectl create secret generic gfin-db-config \
  --from-literal=POSTGRES_HOST="$POSTGRES_ENDPOINT" \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=gfin \
  --from-literal=POSTGRES_USER=gfin_admin \
  --from-literal=POSTGRES_PASSWORD="$TF_VAR_db_password" \
  -n gfin

kubectl create secret generic gfin-kafka-config \
  --from-literal=KAFKA_BROKERS="$KAFKA_BROKERS" \
  --from-literal=KAFKA_TLS=true \
  -n gfin

kubectl create secret generic gfin-search-config \
  --from-literal=OPENSEARCH_URL="https://$OPENSEARCH_ENDPOINT" \
  -n gfin

kubectl create secret generic gfin-redis-config \
  --from-literal=REDIS_HOST="$REDIS_ENDPOINT" \
  --from-literal=REDIS_PORT=6379 \
  --from-literal=REDIS_TLS=true \
  -n gfin

kubectl create secret generic gfin-storage-config \
  --from-literal=S3_BUCKET="$EVIDENCE_BUCKET" \
  --from-literal=S3_REGION=eu-central-1 \
  -n gfin
```

---

### Phase 5: Deploy GFIN Application Services

```bash
# Apply GFIN Kubernetes manifests (from repo)
kubectl apply -f infrastructure/kubernetes/ -n gfin

# Verify all pods running
kubectl get pods -n gfin -w
# EXPECT: All pods Running within 2-3 minutes

# Check service endpoints
kubectl get svc -n gfin
```

---

### Phase 6: TLS Certificate Setup

```bash
# Option A: Let's Encrypt via cert-manager (production)
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - << 'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: gfin-letsencrypt
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@gfin.example
    privateKeySecretRef:
      name: gfin-letsencrypt-key
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

# Option B: Self-signed (staging only)
openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -keyout /tmp/gfin-tls.key -out /tmp/gfin-tls.crt \
  -subj "/CN=gfin.example" -addext "subjectAltName=DNS:gfin.example"

kubectl create secret tls gfin-tls \
  --cert=/tmp/gfin-tls.crt --key=/tmp/gfin-tls.key -n gfin
```

---

### Phase 7: Run Infrastructure Acceptance Tests

```bash
# On the cluster (or any machine with access to all services)
cd /gfin
export GFIN_RUN_INTEGRATION=1
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
export OPENAI_PROJECT_KEY="..."

python3 -m pytest tests/production/test_deployment_acceptance.py -v
# EXPECT: 12/12 PASSED

python3 -m pytest tests/production/test_go_no_go_gates.py -v
# EXPECT: 6/6 PASSED

python3 -m pytest tests/production/test_terraform_iac.py -v
# EXPECT: 26/26 PASSED
```

---

## 4. Go/No-Go Gates

Before declaring production-ready, all 12 gates must pass:

| Gate | Name | Owner | Status |
|------|------|-------|--------|
| G1 | Legal/Compliance Review | Legal Team | BLOCKED |
| G2 | Infrastructure Provisioned | DevOps | BLOCKED |
| G3 | Security Penetration Test | Security Team | BLOCKED |
| G4 | Performance Benchmarks | Engineering | PASSING (14/14) |
| G5 | Data Protection Audit | DPO | BLOCKED |
| G6 | Federation Protocol Test | Engineering | PASSING |
| G7 | Disaster Recovery Drill | DevOps | BLOCKED |
| G8 | Monitoring & Alerting | SRE | PASSING |
| G9 | Documentation Complete | Engineering | PASSING |
| G10 | Pilot Program Success | Product | BLOCKED |
| G11 | API Contract Validation | Engineering | PASSING (37/37) |
| G12 | Code Security Scan | Security | PASSING |

---

## 5. Rollback Procedure

```bash
# Terraform rollback (destroy all cloud resources)
cd infrastructure/terraform
terraform destroy

# K3s rollback (on each Hetzner node)
/usr/local/bin/k3s-uninstall.sh

# Data preservation:
# - RDS: automated snapshots retained for 7 days (staging) / 30 days (prod)
# - S3 evidence: WORM-locked, cannot be deleted until retention expires
# - Kafka: MSK retains data for 7 days by default
```

---

## 6. Disaster Recovery

| Scenario | RTO | RPO | Procedure |
|---|---|---|---|
| Hetzner node failure | 5 min | 0 | K3s auto-reschedules pods to healthy nodes |
| RDS failure | 15 min | 5 min | Failover to standby (multi-AZ in production) |
| MSK broker failure | 0 | 0 | Auto-replication factor 3, no data loss |
| OpenSearch node failure | 5 min | 0 | Replication factor 2, auto-recovery |
| Redis failure | 1 min | 0 | Multi-AZ failover (production) |
| S3 data loss | N/A | 0 | WORM + versioning, 11x9s durability |
| Full region failure | 4 hrs | 15 min | Restore from cross-region snapshots |

---

## 7. Cost Estimates (Monthly)

### Staging
| Service | Specification | Est. Cost |
|---|---|---|
| Hetzner: 1 master + 3 workers | cpx21 + 3x cpx31 | €48/mo |
| RDS PostgreSQL | db.t3.medium, 100GB | €72/mo |
| MSK Kafka | 3x kafka.m5.large | €240/mo |
| OpenSearch | 3x r6g.large.search | €210/mo |
| ElastiCache Redis | cache.t3.medium | €35/mo |
| S3 + CloudWatch | 50GB + logs | €10/mo |
| **Total Staging** | | **~€615/mo** |

### Production (estimated)
| Service | Specification | Est. Cost |
|---|---|---|
| Hetzner: 1 master + 5 workers | cpx21 + 5x cpx31 | €72/mo |
| RDS PostgreSQL (multi-AZ) | db.r6g.large, 200GB | €220/mo |
| MSK Kafka | 3x kafka.m5.xlarge | €480/mo |
| OpenSearch (dedicated masters) | 3x r6g.2xlarge.search + 3 masters | €520/mo |
| ElastiCache Redis (3 nodes) | 3x cache.r6g.large | €210/mo |
| S3 + CloudWatch + KMS | 500GB + logs | €45/mo |
| **Total Production** | | **~€1,547/mo** |

---

## 8. Troubleshooting

### K3s worker can't join cluster
```bash
# Check if master is reachable
nc -zv <master_ip> 6443

# Check node token on master
cat /var/lib/rancher/k3s/server/node-token

# Re-run worker bootstrap
curl -sfL https://get.k3s.io | K3S_URL="https://<master>:6443" K3S_TOKEN="<token>" sh -
```

### RDS connection refused
```bash
# Check security group allows Hetzner IPs
# Get Hetzner node IPs:
terraform output hetzner_worker_ips

# Add to allowed_cidr_blocks variable
# Re-apply: terraform apply -var="allowed_cidr_blocks=[\"<ip>/32\"]"
```

### MSK Kafka TLS connection issues
```bash
# MSK uses TLS by default — ensure client trusts AWS CA
# Download MSK CA cert:
aws kafka describe-cluster --cluster-arn <arn> --query 'ClusterInfo' | jq -r '.BrokerNodeGroupInfo'

# Test connectivity:
openssl s_client -connect <broker>:9094 -showcerts
```

### OpenSearch domain not responding
```bash
# Check domain status
aws opensearch describe-domain --domain-name gfin-staging

# Check security group allows Hetzner IPs on port 443
# Check VPC peering or Transit Gateway if cross-cloud
```

---

## 9. Post-Deployment Checklist

- [ ] All 44 acceptance tests pass
- [ ] All 12 go/no-go gates evaluated
- [ ] TLS certificates valid and not expired
- [ ] NetworkPolicies enforced in K8s
- [ ] RBAC roles configured
- [ ] Backup verification (RDS snapshot test)
- [ ] Monitoring dashboards accessible
- [ ] Alert rules configured in Prometheus
- [ ] Log aggregation working (CloudWatch)
- [ ] Secrets stored in K8s secrets (not env vars)
- [ ] No hardcoded credentials in code
- [ ] DNS records configured
- [ ] Load balancer health checks passing

---

**Document End**  
**Next Review:** After pilot program completion  
**Owner:** GFIN-CEA (GPT Luna)
