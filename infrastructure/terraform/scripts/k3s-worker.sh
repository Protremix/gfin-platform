#!/bin/bash
# K3s worker node bootstrap — GFIN hybrid cloud
set -euo pipefail

MASTER_IP="${master_ip}"
CLUSTER_NAME="${cluster_name}"

# Wait for master to be reachable
echo "Waiting for K3s master at $MASTER_IP..."
until nc -z "$MASTER_IP" 6443 2>/dev/null; do
  sleep 2
done

# Fetch node token from master (requires SSH key)
K3S_TOKEN=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@$MASTER_IP "cat /var/lib/rancher/k3s/server/node-token" 2>/dev/null || echo "MANUAL_SETUP_REQUIRED")

if [ "$K3S_TOKEN" = "MANUAL_SETUP_REQUIRED" ]; then
  echo "WARNING: Could not fetch K3s token. Manual worker setup required."
  exit 0
fi

# Install K3s agent
curl -sfL https://get.k3s.io | K3S_URL="https://$MASTER_IP:6443" K3S_TOKEN="$K3S_TOKEN" sh -

echo "K3s worker joined to cluster at $MASTER_IP"
