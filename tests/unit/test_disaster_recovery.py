"""Tests for Disaster Recovery — Module 35."""

import pytest

from services.disaster_recovery import (
    BackupRecord,
    BackupStatus,
    BackupType,
    DisasterRecoveryService,
    FailoverRecord,
    FailoverStatus,
    RecoveryRecord,
    RecoveryStatus,
)


@pytest.fixture
def service():
    return DisasterRecoveryService()


# ─── BackupRecord Tests ───


class TestBackupRecord:
    def test_mark_completed(self):
        b = BackupRecord(id="B1", backup_type=BackupType.FULL.value, component="db")
        b.mark_completed(1024, "sha256:abc")
        assert b.status == BackupStatus.COMPLETED.value
        assert b.size_bytes == 1024
        assert b.completed_at is not None

    def test_mark_failed(self):
        b = BackupRecord(id="B1", backup_type=BackupType.FULL.value, component="db")
        b.mark_failed()
        assert b.status == BackupStatus.FAILED.value


# ─── RecoveryRecord Tests ───


class TestRecoveryRecord:
    def test_mark_completed(self):
        r = RecoveryRecord(id="R1", backup_id="B1", component="db")
        r.mark_completed(verified=True)
        assert r.status == RecoveryStatus.COMPLETED.value
        assert r.verified is True

    def test_mark_failed(self):
        r = RecoveryRecord(id="R1", backup_id="B1", component="db")
        r.mark_failed()
        assert r.status == RecoveryStatus.FAILED.value


# ─── FailoverRecord Tests ───


class TestFailoverRecord:
    def test_mark_failover(self):
        f = FailoverRecord(id="F1", component="api", from_region="eu-west", to_region="us-east")
        f.mark_failover(rto_seconds=120, rpo_seconds=30)
        assert f.status == FailoverStatus.FAILOVER.value
        assert f.rto_seconds == 120
        assert f.rpo_seconds == 30

    def test_mark_failed_back(self):
        f = FailoverRecord(id="F1", component="api", from_region="eu", to_region="us")
        f.mark_failover()
        f.mark_failed_back()
        assert f.status == FailoverStatus.FAILED_BACK.value


# ─── DisasterRecoveryService Tests ───


class TestBackupService:
    def test_create_backup(self, service):
        service.store_data("db", {"users": [1, 2, 3]})
        b = service.create_backup("db")
        assert b.id.startswith("BKP-")
        assert b.status == BackupStatus.COMPLETED.value
        assert b.size_bytes > 0

    def test_create_backup_empty(self, service):
        b = service.create_backup("empty_component")
        assert b.status == BackupStatus.COMPLETED.value
        assert b.size_bytes >= 0

    def test_get_backup(self, service):
        b = service.create_backup("db")
        assert service.get_backup(b.id) is not None
        assert service.get_backup("nonexistent") is None

    def test_list_backups(self, service):
        service.create_backup("db")
        service.create_backup("api")
        assert len(service.list_backups()) == 2
        assert len(service.list_backups(component="db")) == 1

    def test_backup_count(self, service):
        service.create_backup("db")
        assert service.backup_count == 1

    def test_verify_backup(self, service):
        b = service.create_backup("db")
        assert service.verify_backup(b.id) is True

    def test_verify_nonexistent(self, service):
        assert service.verify_backup("nonexistent") is False


class TestRecoveryService:
    def test_restore_backup(self, service):
        b = service.create_backup("db")
        r = service.restore_backup(b.id)
        assert r is not None
        assert r.status == RecoveryStatus.COMPLETED.value
        assert r.verified is True

    def test_restore_nonexistent(self, service):
        assert service.restore_backup("nonexistent") is None

    def test_get_recovery(self, service):
        b = service.create_backup("db")
        r = service.restore_backup(b.id)
        assert service.get_recovery(r.id) is not None
        assert service.get_recovery("nonexistent") is None

    def test_list_recoveries(self, service):
        b1 = service.create_backup("db")
        b2 = service.create_backup("api")
        service.restore_backup(b1.id)
        service.restore_backup(b2.id)
        assert len(service.list_recoveries()) == 2
        assert len(service.list_recoveries(component="db")) == 1

    def test_recovery_count(self, service):
        b = service.create_backup("db")
        service.restore_backup(b.id)
        assert service.recovery_count == 1


class TestFailoverService:
    def test_initiate_failover(self, service):
        fo = service.initiate_failover("api", "eu-west-1", "us-east-1")
        assert fo.id.startswith("FO-")
        assert fo.status == FailoverStatus.FAILOVER.value
        assert fo.rto_seconds == service.PROPOSED_RTO_SECONDS

    def test_failback(self, service):
        fo = service.initiate_failover("api", "eu", "us")
        assert service.failback(fo.id) is True
        assert fo.status == FailoverStatus.FAILED_BACK.value

    def test_failback_nonexistent(self, service):
        assert service.failback("nonexistent") is False

    def test_get_failover(self, service):
        fo = service.initiate_failover("api", "eu", "us")
        assert service.get_failover(fo.id) is not None
        assert service.get_failover("nonexistent") is None

    def test_list_failovers(self, service):
        service.initiate_failover("api", "eu", "us")
        service.initiate_failover("db", "eu", "us")
        assert len(service.list_failovers()) == 2

    def test_failover_count(self, service):
        service.initiate_failover("api", "eu", "us")
        assert service.failover_count == 1


class TestDRSummary:
    def test_summary(self, service):
        service.store_data("db", {"key": "value"})
        b = service.create_backup("db")
        service.restore_backup(b.id)
        service.initiate_failover("api", "eu", "us")
        summary = service.get_dr_summary()
        assert summary["total_backups"] == 1
        assert summary["completed_backups"] == 1
        assert summary["total_recoveries"] == 1
        assert summary["verified_recoveries"] == 1
        assert summary["total_failovers"] == 1
        assert summary["proposed_rto_seconds"] == 300
        assert summary["proposed_rpo_seconds"] == 60

    def test_summary_empty(self, service):
        summary = service.get_dr_summary()
        assert summary["total_backups"] == 0
