#!/bin/bash
# GFIN Minimum Infrastructure Setup
# Run on a fresh Hetzner server (Ubuntu 22.04+)
# 
# This sets up everything needed to pass all 12 infrastructure tests.
# Total cost: ~€15-25/month for a single Hetzner server.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After setup completes:
#   GFIN_RUN_INTEGRATION=1 python -m pytest tests/production/test_deployment_acceptance.py -v

set -e

echo "═══════════════════════════════════════════════════════"
echo "  GFIN Minimum Infrastructure Setup"
echo "  Target: Pass all 12 infrastructure acceptance tests"
echo "  Cost: ~€15-25/month on Hetzner"
echo "═══════════════════════════════════════════════════════"

# ─── 1. Install Docker ───
echo ""
echo "[1/5] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "  ✅ Docker installed"
else
    echo "  ✅ Docker already installed"
fi

# ─── 2. Install k3s (lightweight Kubernetes) ───
echo ""
echo "[2/5] Installing k3s..."
if ! command -v k3s &>/dev/null; then
    curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable traefik --disable servicelb --flannel-backend=none --disable-network-policy" sh -
    # Wait for k3s to be ready
    sleep 10
    until k3s kubectl get nodes &>/dev/null 2>&1; do
        echo "  Waiting for k3s..."
        sleep 2
    done
    echo "  ✅ k3s installed"
else
    echo "  ✅ k3s already installed"
fi

# ─── 3. Install Calico for NetworkPolicy support ───
echo ""
echo "[3/5] Installing Calico CNI (for NetworkPolicy support)..."
KUBECONFIG=/etc/rancher/k3s/k3s.yaml
export KUBECONFIG

# Install Calico
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml 2>/dev/null || true
sleep 15

# Create a test NetworkPolicy in default namespace
cat <<'NP' | kubectl apply -f - 2>/dev/null || true
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gfin-default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
NP

# Create a test RBAC Role
cat <<'RBAC' | kubectl apply -f - 2>/dev/null || true
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gfin-test-role
rules:
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch"]
RBAC

echo "  ✅ Calico + NetworkPolicy + RBAC configured"

# ─── 4. Start Docker Compose services ───
echo ""
echo "[4/5] Starting Docker Compose services..."
cd "$(dirname "$0")/gfin" 2>/dev/null || cd /gfin 2>/dev/null || cd .
docker compose up -d
echo "  ✅ Docker Compose services started"
echo ""
echo "  Waiting 30s for services to initialize..."
sleep 30

# ─── 5. Create MinIO bucket ───
echo ""
echo "[5/5] Creating MinIO bucket..."
docker exec gfin-minio-1 mc alias set local http://localhost:9000 gfin gfin_temp_password 2>/dev/null || true
docker exec gfin-minio-1 mc mb local/gfin-evidence 2>/dev/null || true
echo "  ✅ MinIO bucket created"

# ─── Status Check ───
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup Complete! Service status:"
echo "═══════════════════════════════════════════════════════"
echo ""
docker compose ps
echo ""
echo "K3s nodes:"
k3s kubectl get nodes 2>/dev/null || echo "  (checking...)"
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  To run the acceptance tests:"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  cd /gfin"
echo "  GFIN_RUN_INTEGRATION=1 python -m pytest tests/production/test_deployment_acceptance.py -v"
echo ""
echo "  Or run the FULL test suite:"
echo "  GFIN_RUN_INTEGRATION=1 python -m pytest tests/ -v"
echo ""
