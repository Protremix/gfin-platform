# ═══════════════════════════════════════════════════════════════════
# AWS Frankfurt — Stateful Managed Services Layer
# RDS PostgreSQL, MSK Kafka, OpenSearch, ElastiCache Redis, S3
# All GDPR-resident in eu-central-1 (Frankfurt)
# ═══════════════════════════════════════════════════════════════════

# ─── VPC ───
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "gfin-vpc-${var.environment}"
  cidr = "172.16.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["172.16.1.0/24", "172.16.2.0/24", "172.16.3.0/24"]
  public_subnets  = ["172.16.101.0/24", "172.16.102.0/24", "172.16.103.0/24"]

  enable_nat_gateway   = true
  enable_dns_hostnames  = true
  enable_dns_support    = true

  tags = {
    Environment = var.environment
    Project     = "gfin"
    ManagedBy   = "terraform"
  }
}

# ─── KMS Key (encryption at rest for all services) ───
resource "aws_kms_key" "gfin" {
  description             = "GFIN encryption key — ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── RDS PostgreSQL ───
resource "aws_db_subnet_group" "gfin" {
  name       = "gfin-${var.environment}"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
  count   = var.db_password == "" ? 1 : 0
}

resource "aws_db_instance" "postgres" {
  identifier     = "gfin-postgres-${var.environment}"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = var.aws_db_instance_class

  allocated_storage     = var.aws_db_allocated_storage
  max_allocated_storage = var.aws_db_allocated_storage * 5
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.gfin.arn

  db_name  = "gfin"
  username = "gfin_admin"
  password = var.db_password != "" ? var.db_password : random_password.db_password[0].result

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.gfin.name

  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az                = var.environment == "production"
  deletion_protection     = var.environment == "production"
  delete_automated_backups = var.environment != "production"

  enabled_loggings {
    enabled = true
    log_exports = ["postgresql", "upgrade"]
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── MSK Kafka ───
resource "aws_msk_cluster" "kafka" {
  cluster_name           = "gfin-kafka-${var.environment}"
  kafka_version          = "3.7.1"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = var.aws_msk_instance_type
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.kafka.id]

    storage_info {
      ebs_volume_size = 100
      provisioned_throughput {
        enabled           = false
        volume_throughput = 250
      }
    }

    connectivity_info {
      public_access {
        type = var.environment == "production" ? "DISABLED" : "SERVICE_PROVIDED_EIPS"
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.gfin.arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  enhanced_monitoring = "PER_TOPIC_PER_BROKER"
  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group  = aws_cloudwatch_log_group.kafka.name
      }
      s3 {
        enabled = true
        bucket  = aws_s3_bucket.logs.id
        prefix  = "kafka/"
      }
    }
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── OpenSearch ───
resource "aws_opensearch_domain" "gfin" {
  domain_name    = "gfin-${var.environment}"
  engine_version = "OpenSearch_2.18"

  cluster_config {
    instance_type          = var.aws_opensearch_instance_type
    instance_count         = var.aws_opensearch_instance_count
    dedicated_master_enabled = var.environment == "production"
    dedicated_master_type  = var.environment == "production" ? "r6g.large.search" : null
    dedicated_master_count = var.environment == "production" ? 3 : 0
    zone_awareness_enabled = true
    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 100
    volume_type = "gp3"
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.gfin.arn
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = var.environment == "production"
    internal_user_database_enabled = var.environment == "production"
  }

  node_to_node_encryption {
    enabled = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch.arn
    log_type                 = "SEARCH_SLOW_LOGS"
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── ElastiCache Redis ───
resource "aws_elasticache_subnet_group" "gfin" {
  name       = "gfin-${var.environment}"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id     = "gfin-redis-${var.environment}"
  description              = "GFIN Redis cache cluster"
  engine                  = "redis"
  engine_version          = "7.1"
  node_type               = var.aws_elasticache_node_type
  number_cache_clusters   = var.environment == "production" ? 3 : 1
  multi_az_enabled        = var.environment == "production"
  automatic_failover_enabled = var.environment == "production"

  subnet_group_name       = aws_elasticache_subnet_group.gfin.name
  security_group_ids      = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.db_password != "" ? var.db_password : random_password.db_password[0].result

  snapshot_retention_limit = 7
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:06:00"

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── S3: Evidence Storage (WORM compliance) ───
resource "aws_s3_bucket" "evidence" {
  bucket = "gfin-evidence-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = "gfin"
    DataClass   = "evidence"
  }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  object_lock_enabled = "Enabled"
  rule {
    default_retention {
      mode = "COMPLIANCE"  # WORM — cannot be deleted until retention expires
      days = 2555           # 7 years (legal evidence retention)
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.gfin.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── S3: Application Logs ───
resource "aws_s3_bucket" "logs" {
  bucket = "gfin-logs-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ─── S3: Terraform State ───
resource "aws_s3_bucket" "terraform_state" {
  bucket = "gfin-terraform-state"

  tags = {
    Project     = "gfin"
    Purpose     = "terraform-state"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "gfin-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Project = "gfin"
  }
}

# ─── CloudWatch Log Groups ───
resource "aws_cloudwatch_log_group" "kafka" {
  name              = "/gfin/kafka"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "opensearch" {
  name              = "/gfin/opensearch"
  retention_in_days = var.environment == "production" ? 90 : 14
}
