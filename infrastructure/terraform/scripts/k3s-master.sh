#!/bin/bash
# K3s master node bootstrap — GFIN hybrid cloud
set -euo pipefail

export CLUSTER_NAME="${cluster_name}"

# Install K3s server (no Traefik, no ServicelB — we use nginx)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable traefik \
  --disable servicelb \
  --flannel-backend=vxlan \
  --tls-san $(hostname -I | awk '{print $1}') \
  --write-kubeconfig-mode 644" sh -

# Wait for K3s to be ready
sleep 10

# Extract node token for workers
K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
echo "K3S_TOKEN=$K3S_TOKEN" > /tmp/k3s-token

# Apply NetworkPolicy + RBAC baseline
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl apply -f - << 'POLICY'
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
POLICY

echo "K3s master ready: $(kubectl get nodes -o wide | tail -1)"
