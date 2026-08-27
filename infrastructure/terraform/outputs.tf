# ═══════════════════════════════════════════════════════════════════
# GFIN Infrastructure Outputs
# ═══════════════════════════════════════════════════════════════════

# ─── Hetzner ───
output "hetzner_master_ip" {
  value = hcloud_server.master.ipv4_address
  description = "K3s master node public IP"
}

output "hetzner_worker_ips" {
  value = hcloud_server.workers[*].ipv4_address
  description = "K3s worker node public IPs"
}

output "hetzner_private_network" {
  value = hcloud_network.gfin.ip_range
  description = "Private network CIDR for inter-node communication"
}

# ─── AWS Stateful Services ───
output "postgres_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  description = "RDS PostgreSQL endpoint"
  sensitive   = true
}

output "kafka_bootstrap_brokers" {
  value     = aws_msk_cluster.kafka.bootstrap_brokers
  description = "MSK Kafka bootstrap brokers (TLS)"
  sensitive   = true
}

output "opensearch_endpoint" {
  value     = aws_opensearch_domain.gfin.endpoint
  description = "OpenSearch domain endpoint"
  sensitive   = true
}

output "redis_endpoint" {
  value     = aws_elasticache_replication_group.redis.primary_endpoint_address
  description = "ElastiCache Redis primary endpoint"
  sensitive   = true
}

# ─── S3 ───
output "evidence_bucket" {
  value = aws_s3_bucket.evidence.bucket
  description = "S3 evidence bucket name (WORM-compliant)"
}

output "logs_bucket" {
  value = aws_s3_bucket.logs.bucket
  description = "S3 logs bucket name"
}

# ─── Security ───
output "kms_key_arn" {
  value = aws_kms_key.gfin.arn
  description = "KMS key ARN for encryption"
}

# ─── VPC ───
output "vpc_id" {
  value = module.vpc.vpc_id
  description = "AWS VPC ID"
}

output "private_subnet_ids" {
  value = module.vpc.private_subnets
  description = "AWS private subnet IDs"
}
