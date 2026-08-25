# GFIN Infrastructure — Terraform Configuration
# Layer B: REQUIRES EXTERNAL INFRASTRUCTURE
# 
# This is a scaffold. Real deployment requires:
# - Cloud provider credentials
# - Terraform backend configuration
# - Secret management integration
# 
# Usage: cd infrastructure/terraform && terraform init && terraform plan

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  # Backend configuration — set up per environment
  # backend "s3" {
  #   bucket = "gfin-terraform-state"
  #   key    = "gfin/terraform.tfstate"
  #   region = "eu-west-1"
  # }
}

# Variables
variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  default     = "staging"
}

variable "region" {
  description = "Primary region for deployment"
  type        = string
  default     = "eu-west-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "gfin-cluster"
}

# Provider configuration
provider "aws" {
  region = var.region
}

# ─── VPC ───
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "gfin-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b", "${var.region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = true

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── EKS Cluster ───
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      max_size     = 10
      desired_size = 3

      instance_types = ["t3.medium"]
    }
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── RDS (PostgreSQL) ───
# REQUIRES EXTERNAL INFRASTRUCTURE — provisioned via Terraform
resource "aws_db_instance" "gfin_postgres" {
  identifier     = "gfin-postgres-${var.environment}"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true

  db_name  = "gfin"
  username = "gfin_admin"
  password = "REPLACE_WITH_SECRET_MANAGER"  # Use AWS Secrets Manager in production

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.gfin.name

  backup_retention_period = 7
  multi_az                = true
  deletion_protection     = var.environment == "production"

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── MSK (Kafka) ───
# REQUIRES EXTERNAL INFRASTRUCTURE
resource "aws_msk_cluster" "gfin_kafka" {
  cluster_name           = "gfin-kafka-${var.environment}"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m5.large"
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.kafka.id]

    storage_info {
      ebs_volume_size = 100
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.gfin.arn
    encryption_in_transit {
      client_broker = "TLS"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── S3 (Evidence Storage) ───
resource "aws_s3_bucket" "evidence" {
  bucket = "gfin-evidence-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = "gfin"
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
      mode = "COMPLIANCE"  # WORM compliance
      days = 2555  # 7 years
    }
  }
}

# ─── KMS Key ───
resource "aws_kms_key" "gfin" {
  description             = "GFIN encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── Security Groups ───
resource "aws_security_group" "rds" {
  name        = "gfin-rds-${var.environment}"
  description = "GFIN PostgreSQL security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "kafka" {
  name        = "gfin-kafka-${var.environment}"
  description = "GFIN Kafka security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "gfin" {
  name       = "gfin-${var.environment}"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Project     = "gfin"
  }
}

# ─── Outputs ───
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "postgres_endpoint" {
  value = aws_db_instance.gfin_postgres.endpoint
}

output "kafka_bootstrap_brokers" {
  value = aws_msk_cluster.gfin_kafka.bootstrap_brokers
}

output "evidence_bucket" {
  value = aws_s3_bucket.evidence.bucket
}
