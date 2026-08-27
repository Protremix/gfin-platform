# ═══════════════════════════════════════════════════════════════════
# GFIN Hybrid Cloud Infrastructure — Terraform Configuration
# Layer B: REQUIRES EXTERNAL INFRASTRUCTURE
#
# Architecture:
#   Hetzner Cloud (Nuremberg)  — Stateless compute (K3s/K8s worker nodes)
#   AWS Frankfurt (eu-central-1) — Stateful managed services (RDS, MSK, 
#                                  OpenSearch, ElastiCache, S3)
#
# Usage:
#   export TF_VAR_hetzner_token="..."
#   export TF_VAR_db_password="..."
#   terraform init
#   terraform plan
#   terraform apply
# ═══════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend — local for bootstrap, switch to S3 after credentials
  backend "local" {
    path = "/gfin/infrastructure/terraform/terraform.tfstate"
  }
}

# ─── Provider: AWS Frankfurt ───
provider "aws" {
  region = var.aws_region
}

# ─── Provider: Hetzner Cloud ───
provider "hcloud" {
  token = var.hetzner_token
}
