# ─── GFIN Hybrid Cloud Variables ───
# Hetzner (stateless compute) + AWS Frankfurt (stateful managed services)

variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  default     = "staging"
}

variable "aws_region" {
  description = "AWS region for stateful managed services"
  type        = string
  default     = "eu-central-1"  # Frankfurt — GDPR-resident
}

variable "hetzner_location" {
  description = "Hetzner Cloud location for compute nodes"
  type        = string
  default     = "nbg1"  # Nuremberg — closest to AWS Frankfurt
}

variable "cluster_name" {
  description = "GFIN cluster name"
  type        = string
  default     = "gfin"
}

# ─── Hetzner Variables ───
variable "hetzner_token" {
  description = "Hetzner Cloud API token (set via TF_VAR_hetzner_token)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "hetzner_node_type" {
  description = "Hetzner server type for K8s worker nodes"
  type        = string
  default     = "cpx31"  # 4 vCPU, 8GB RAM
}

variable "hetzner_master_type" {
  description = "Hetzner server type for K8s control plane"
  type        = string
  default     = "cpx21"  # 3 vCPU, 4GB RAM
}

variable "hetzner_node_count" {
  description = "Number of Hetzner worker nodes"
  type        = number
  default     = 3
}

# ─── AWS Variables ───
variable "aws_db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "aws_db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "aws_msk_instance_type" {
  description = "MSK broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "aws_opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "r6g.large.search"
}

variable "aws_opensearch_instance_count" {
  description = "OpenSearch node count (odd for quorum)"
  type        = number
  default     = 3
}

variable "aws_elasticache_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

# ─── Security Variables ───
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access stateful services (Hetzner node IPs)"
  type        = list(string)
  default     = []
}

variable "db_password" {
  description = "PostgreSQL master password (use AWS Secrets Manager in production)"
  type        = string
  sensitive   = true
  default     = ""
}
