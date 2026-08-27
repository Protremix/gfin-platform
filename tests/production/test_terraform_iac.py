"""
GFIN Terraform IaC Validation Tests.
Validates the hybrid cloud Terraform configuration without requiring cloud credentials.
Checks: file structure, variable definitions, resource declarations, security posture.
"""

import re
from pathlib import Path

import pytest

TF_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "terraform"


def _content(filename):
    return (TF_DIR / filename).read_text()


def _flat(filename):
    return _content(filename).replace("\n", " ")


def _has(pattern, text):
    return re.search(pattern, text) is not None


# ─── File Structure ───

REQUIRED_TF_FILES = [
    "main.tf", "variables.tf", "aws-stateful.tf",
    "hetzner.tf", "security.tf", "outputs.tf",
]


@pytest.mark.parametrize("filename", REQUIRED_TF_FILES)
def test_terraform_files_exist(filename):
    assert (TF_DIR / filename).exists(), f"Missing: {filename}"


def test_k3s_scripts_exist():
    assert (TF_DIR / "scripts" / "k3s-master.sh").exists()
    assert (TF_DIR / "scripts" / "k3s-worker.sh").exists()


def test_terraform_required_version():
    assert _has(r"required_version.*>=\s*1\.5", _content("main.tf"))


# ─── Provider Configuration ───

def test_aws_provider_configured():
    content = _content("main.tf")
    assert 'provider "aws"' in content
    assert "eu-central-1" in content


def test_hetzner_provider_configured():
    assert 'provider "hcloud"' in _content("main.tf")


def test_s3_backend_configured():
    content = _content("main.tf")
    assert 'backend "s3"' in content
    assert "encrypt" in content
    assert "dynamodb_table" in content


# ─── AWS Stateful Services ───

def test_rds_postgres_defined():
    f = _flat("aws-stateful.tf")
    assert "aws_db_instance" in f
    assert _has(r'engine\s*=\s*"postgres"', f)
    assert _has(r'engine_version\s*=\s*"16', f)
    assert "storage_encrypted" in f and "true" in f
    assert "multi_az" in f
    assert "backup_retention_period" in f


def test_msk_kafka_defined():
    f = _flat("aws-stateful.tf")
    assert "aws_msk_cluster" in f
    assert _has(r'kafka_version\s*=\s*"3', f)
    assert _has(r"number_of_broker_nodes\s*=\s*3", f)
    assert "encryption_at_rest" in f
    assert "TLS" in f


def test_opensearch_defined():
    f = _flat("aws-stateful.tf")
    assert "aws_opensearch_domain" in f
    assert "encrypt_at_rest" in f
    assert "enforce_https" in f
    assert "tls_security_policy" in f
    assert "Min-TLS-1-2" in f


def test_elasticache_redis_defined():
    f = _flat("aws-stateful.tf")
    assert "aws_elasticache_replication_group" in f
    assert "at_rest_encryption_enabled" in f
    assert "transit_encryption_enabled" in f


def test_s3_evidence_worm_compliance():
    f = _flat("aws-stateful.tf")
    assert "aws_s3_bucket" in f and "evidence" in f
    assert "object_lock" in f
    assert "COMPLIANCE" in f
    assert "2555" in f
    assert "server_side_encryption" in f
    assert "public_access_block" in f


def test_kms_key_defined():
    f = _flat("aws-stateful.tf")
    assert "aws_kms_key" in f
    assert "enable_key_rotation" in f


# ─── Hetzner Compute ───

def test_hetzner_master_node():
    f = _flat("hetzner.tf")
    assert _has(r'hcloud_server.*master', f)
    assert "ubuntu-22.04" in f
    assert "hcloud_firewall" in f


def test_hetzner_worker_nodes():
    f = _flat("hetzner.tf")
    assert _has(r'hcloud_server.*workers', f)
    assert _has(r"count\s*=\s*var\.hetzner_node_count", f)


def test_hetzner_private_network():
    f = _flat("hetzner.tf")
    assert "hcloud_network" in f
    assert "hcloud_network_subnet" in f
    assert "hcloud_server_network" in f


def test_hetzner_firewall_rules():
    f = _content("hetzner.tf")
    assert "6443" in f
    assert "443" in f
    assert "10250" in f
    assert "2379" in f
    assert "2380" in f


# ─── Security ───

def test_security_groups_restrict_access():
    f = _flat("security.tf")
    assert "aws_security_group" in f and "rds" in f
    assert "aws_security_group" in f and "kafka" in f
    assert "aws_security_group" in f and "opensearch" in f
    assert "aws_security_group" in f and "redis" in f
    assert "allowed_cidr_blocks" in f


def test_no_hardcoded_secrets():
    for tf_file in TF_DIR.glob("*.tf"):
        content = tf_file.read_text()
        assert "AKIA" not in content, f"AWS key in {tf_file.name}"
        assert not re.search(r'sk-[a-zA-Z0-9]{20}', content), f"API key in {tf_file.name}"


# ─── Variables ───

def test_sensitive_variables_marked():
    f = _flat("variables.tf")
    assert _has(r"sensitive\s*=\s*true", f)
    assert "hetzner_token" in f
    assert "db_password" in f


# ─── Outputs ───

def test_outputs_defined():
    content = _content("outputs.tf")
    for out in ["postgres_endpoint", "kafka_bootstrap_brokers", "opensearch_endpoint",
                "redis_endpoint", "evidence_bucket", "hetzner_master_ip"]:
        assert f'output "{out}"' in content, f"Missing output: {out}"


def test_sensitive_outputs_marked():
    f = _flat("outputs.tf")
    assert _has(r"sensitive\s*=\s*true", f)
