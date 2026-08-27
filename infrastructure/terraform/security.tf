# ═══════════════════════════════════════════════════════════════════
# Security Groups — AWS Stateful Services
# Access restricted to Hetzner compute nodes via allowed_cidr_blocks
# ═══════════════════════════════════════════════════════════════════

# ─── RDS Security Group ───
resource "aws_security_group" "rds" {
  name        = "gfin-rds-${var.environment}"
  description = "GFIN PostgreSQL — restricted to Hetzner cluster"
  vpc_id      = module.vpc.vpc_id

  dynamic "ingress" {
    for_each = length(var.allowed_cidr_blocks) > 0 ? [1] : [0]
    content {
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── MSK Kafka Security Group ───
resource "aws_security_group" "kafka" {
  name        = "gfin-kafka-${var.environment}"
  description = "GFIN MSK Kafka — restricted to Hetzner cluster"
  vpc_id      = module.vpc.vpc_id

  dynamic "ingress" {
    for_each = length(var.allowed_cidr_blocks) > 0 ? [1] : [0]
    content {
      from_port   = 9094
      to_port     = 9094
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── OpenSearch Security Group ───
resource "aws_security_group" "opensearch" {
  name        = "gfin-opensearch-${var.environment}"
  description = "GFIN OpenSearch — restricted to Hetzner cluster"
  vpc_id      = module.vpc.vpc_id

  dynamic "ingress" {
    for_each = length(var.allowed_cidr_blocks) > 0 ? [1] : [0]
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── ElastiCache Redis Security Group ───
resource "aws_security_group" "redis" {
  name        = "gfin-redis-${var.environment}"
  description = "GFIN ElastiCache Redis — restricted to Hetzner cluster"
  vpc_id      = module.vpc.vpc.id

  dynamic "ingress" {
    for_each = length(var.allowed_cidr_blocks) > 0 ? [1] : [0]
    content {
      from_port   = 6379
      to_port     = 6379
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}
