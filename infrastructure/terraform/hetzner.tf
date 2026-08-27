# ═══════════════════════════════════════════════════════════════════
# Hetzner Cloud — Stateless Compute Layer
# K3s cluster for GFIN application services
# ═══════════════════════════════════════════════════════════════════

# ─── SSH Key ───
resource "hcloud_ssh_key" "gfin" {
  name       = "gfin-cluster-key"
  public_key = file("~/.ssh/gfin_cluster.pub")
}

# ─── Firewall ───
resource "hcloud_firewall" "gfin" {
  name = "gfin-cluster-firewall"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "6443"
    source_ips = ["0.0.0.0/0", "::/0"]  # K8s API (tighten in production)
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]  # HTTPS ingress
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]  # HTTP (redirect)
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "10250"
    source_ips = ["10.0.0.0/8"]  # Kubelet — internal only
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "2379"
    source_ips = ["10.0.0.0/8"]  # etcd — internal only
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "2380"
    source_ips = ["10.0.0.0/8"]  # etcd peer — internal only
  }

  rule {
    direction = "in"
    protocol  = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# ─── K3s Master Node ───
resource "hcloud_server" "master" {
  name        = "${var.cluster_name}-master-01"
  image       = "ubuntu-22.04"
  server_type = var.hetzner_master_type
  location    = var.hetzner_location
  ssh_keys    = [hcloud_ssh_key.gfin.id]
  firewall_ids = [hcloud_firewall.gfin.id]

  labels = {
    environment = var.environment
    role        = "master"
    cluster     = var.cluster_name
  }

  user_data = templatefile("${path.module}/scripts/k3s-master.sh", {
    cluster_name = var.cluster_name
  })
}

# ─── K3s Worker Nodes ───
resource "hcloud_server" "workers" {
  count       = var.hetzner_node_count
  name        = "${var.cluster_name}-worker-${count.index + 1}"
  image       = "ubuntu-22.04"
  server_type = var.hetzner_node_type
  location    = var.hetzner_location
  ssh_keys    = [hcloud_ssh_key.gfin.id]
  firewall_ids = [hcloud_firewall.gfin.id]

  labels = {
    environment = var.environment
    role        = "worker"
    cluster     = var.cluster_name
  }

  user_data = templatefile("${path.module}/scripts/k3s-worker.sh", {
    master_ip    = hcloud_server.master.ipv4_address
    cluster_name = var.cluster_name
  })

  depends_on = [hcloud_server.master]
}

# ─── Private Network ───
resource "hcloud_network" "gfin" {
  name     = "${var.cluster_name}-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "gfin" {
  network_id   = hcloud_network.gfin.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

resource "hcloud_server_network" "master" {
  server_id  = hcloud_server.master.id
  network_id = hcloud_network.gfin.id
  ip         = "10.0.1.10"
}

resource "hcloud_server_network" "workers" {
  count      = var.hetzner_node_count
  server_id  = hcloud_server.workers[count.index].id
  network_id = hcloud_network.gfin.id
  ip         = "10.0.1.${count.index + 11}"
}
