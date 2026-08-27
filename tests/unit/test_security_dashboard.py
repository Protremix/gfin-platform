"""
Tests for the GFIN Security Dashboard Model.
Per Master Security Directive §44.
"""


from services.security_dashboard import (
    ScanStatus,
    SecurityDashboard,
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)


class TestSecurityDashboard:
    """Test the security dashboard model."""

    def test_create_empty_dashboard(self):
        """Dashboard can be created with defaults."""
        dashboard = SecurityDashboard()
        assert dashboard.critical_vulnerabilities == []
        assert dashboard.high_vulnerabilities == []
        assert dashboard.medium_vulnerabilities == []
        assert dashboard.low_vulnerabilities == []
        assert dashboard.dependency_status == ScanStatus.PASS
        assert dashboard.secret_scan_status == ScanStatus.PASS
        assert dashboard.ci_status == ScanStatus.PASS
        assert dashboard.infrastructure_status == ScanStatus.REQUIRES_INFRASTRUCTURE

    def test_add_vulnerability_by_severity(self):
        """Vulnerabilities are added to the correct severity list."""
        dashboard = SecurityDashboard()

        dashboard.add_vulnerability(Vulnerability(
            vid="TEST-001",
            severity=VulnerabilitySeverity.CRITICAL,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))
        assert len(dashboard.critical_vulnerabilities) == 1
        assert len(dashboard.high_vulnerabilities) == 0

        dashboard.add_vulnerability(Vulnerability(
            vid="TEST-002",
            severity=VulnerabilitySeverity.HIGH,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))
        assert len(dashboard.high_vulnerabilities) == 1

        dashboard.add_vulnerability(Vulnerability(
            vid="TEST-003",
            severity=VulnerabilitySeverity.MEDIUM,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))
        assert len(dashboard.medium_vulnerabilities) == 1

        dashboard.add_vulnerability(Vulnerability(
            vid="TEST-004",
            severity=VulnerabilitySeverity.LOW,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))
        assert len(dashboard.low_vulnerabilities) == 1

    def test_get_open_vulnerabilities(self):
        """Get all open vulnerabilities across severities."""
        dashboard = SecurityDashboard()

        for i, severity in enumerate([
            VulnerabilitySeverity.CRITICAL,
            VulnerabilitySeverity.HIGH,
            VulnerabilitySeverity.MEDIUM,
            VulnerabilitySeverity.LOW,
        ]):
            dashboard.add_vulnerability(Vulnerability(
                vid=f"OPEN-{i}",
                severity=severity,
                component="test",
                description="test",
                exploitability="test",
                impact="test",
                remediation="test",
                status=VulnerabilityStatus.OPEN,
            ))
            dashboard.add_vulnerability(Vulnerability(
                vid=f"FIXED-{i}",
                severity=severity,
                component="test",
                description="test",
                exploitability="test",
                impact="test",
                remediation="test",
                status=VulnerabilityStatus.REMEDIATED,
            ))

        open_vulns = dashboard.get_open_vulnerabilities()
        assert len(open_vulns) == 4

    def test_get_blocking_vulnerabilities(self):
        """Blocking vulnerabilities are critical/high and open."""
        dashboard = SecurityDashboard()

        # Critical open — blocks
        dashboard.add_vulnerability(Vulnerability(
            vid="BLK-001",
            severity=VulnerabilitySeverity.CRITICAL,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))

        # High open — blocks
        dashboard.add_vulnerability(Vulnerability(
            vid="BLK-002",
            severity=VulnerabilitySeverity.HIGH,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))

        # High accepted — does not block
        dashboard.add_vulnerability(Vulnerability(
            vid="BLK-003",
            severity=VulnerabilitySeverity.HIGH,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.ACCEPTED,
        ))

        # Medium open — does not block
        dashboard.add_vulnerability(Vulnerability(
            vid="BLK-004",
            severity=VulnerabilitySeverity.MEDIUM,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))

        blocking = dashboard.get_blocking_vulnerabilities()
        assert len(blocking) == 2
        assert all(v.vid.startswith("BLK") for v in blocking)
        assert all(v.status == VulnerabilityStatus.OPEN for v in blocking)

    def test_is_production_ready_false_with_blocking(self):
        """Production ready is False when blocking vulnerabilities exist."""
        dashboard = SecurityDashboard()
        dashboard.add_vulnerability(Vulnerability(
            vid="BLK-001",
            severity=VulnerabilitySeverity.CRITICAL,
            component="test",
            description="test",
            exploitability="test",
            impact="test",
            remediation="test",
            status=VulnerabilityStatus.OPEN,
        ))
        assert not dashboard.is_production_ready()

    def test_is_production_ready_false_no_infrastructure(self):
        """Production ready is False when infrastructure not deployed."""
        dashboard = SecurityDashboard()
        # No blocking vulnerabilities, but infrastructure not ready
        assert not dashboard.is_production_ready()

    def test_is_production_ready_false_no_backup(self):
        """Production ready is False when backup not tested."""
        dashboard = SecurityDashboard()
        dashboard.infrastructure_status = ScanStatus.PASS
        # Backup not run
        assert not dashboard.is_production_ready()

    def test_is_production_ready_true(self):
        """Production ready is True when all conditions met."""
        dashboard = SecurityDashboard()
        dashboard.infrastructure_status = ScanStatus.PASS
        dashboard.backup_status = ScanStatus.PASS
        dashboard.dr_status = ScanStatus.PASS
        # No blocking vulnerabilities
        assert dashboard.is_production_ready()

    def test_summary(self):
        """Summary contains all required fields."""
        dashboard = SecurityDashboard()
        summary = dashboard.summary()

        assert "critical" in summary
        assert "critical_open" in summary
        assert "high" in summary
        assert "high_open" in summary
        assert "medium" in summary
        assert "medium_open" in summary
        assert "low" in summary
        assert "low_open" in summary
        assert "dependency_status" in summary
        assert "secret_scan_status" in summary
        assert "ci_status" in summary
        assert "infrastructure_status" in summary
        assert "backup_status" in summary
        assert "dr_status" in summary
        assert "certificate_status" in summary
        assert "credential_rotation_status" in summary
        assert "security_test_status" in summary
        assert "production_ready" in summary
        assert "last_updated" in summary

    def test_layer_a_default(self):
        """Layer A default dashboard has known vulnerabilities."""
        dashboard = SecurityDashboard.create_layer_a_default()

        # Should have 3 critical, 5 high, 5 medium, 3 low
        assert len(dashboard.critical_vulnerabilities) == 3
        assert len(dashboard.high_vulnerabilities) == 5
        assert len(dashboard.medium_vulnerabilities) == 5
        assert len(dashboard.low_vulnerabilities) == 3

        # Should not be production ready
        assert not dashboard.is_production_ready()

        # Summary should show the right counts
        summary = dashboard.summary()
        assert summary["critical"] == 3
        assert summary["high"] == 5
        assert summary["medium"] == 5
        assert summary["low"] == 3
        assert summary["production_ready"] is False
        assert summary["infrastructure_status"] == "requires_external_infrastructure"

    def test_vulnerability_statuses(self):
        """All vulnerability statuses work correctly."""
        for status in VulnerabilityStatus:
            dashboard = SecurityDashboard()
            dashboard.add_vulnerability(Vulnerability(
                vid=f"TEST-{status.value}",
                severity=VulnerabilitySeverity.MEDIUM,
                component="test",
                description="test",
                exploitability="test",
                impact="test",
                remediation="test",
                status=status,
            ))
            assert len(dashboard.medium_vulnerabilities) == 1

    def test_scan_statuses(self):
        """All scan status values work correctly."""
        for status in ScanStatus:
            dashboard = SecurityDashboard()
            dashboard.dependency_status = status
            assert dashboard.dependency_status == status

    def test_remediated_vulnerability_has_test_id(self):
        """Remediated vulnerabilities can reference regression tests."""
        dashboard = SecurityDashboard()
        dashboard.add_vulnerability(Vulnerability(
            vid="FIXED-001",
            severity=VulnerabilitySeverity.HIGH,
            component="auth",
            description="SQL injection in login",
            exploitability="High",
            impact="Data breach",
            remediation="Parameterized queries",
            status=VulnerabilityStatus.REMEDIATED,
            test_id="test_sql_injection_regression",
        ))
        assert dashboard.high_vulnerabilities[0].test_id == "test_sql_injection_regression"

    def test_accepted_risk_does_not_block(self):
        """Formally accepted risks do not block production."""
        dashboard = SecurityDashboard()
        dashboard.add_vulnerability(Vulnerability(
            vid="ACCEPT-001",
            severity=VulnerabilitySeverity.CRITICAL,
            component="legacy",
            description="Legacy component with known issue",
            exploitability="Low (isolated)",
            impact="Limited",
            remediation="Replace in next cycle",
            status=VulnerabilityStatus.ACCEPTED,
        ))
        dashboard.infrastructure_status = ScanStatus.PASS
        dashboard.backup_status = ScanStatus.PASS
        dashboard.dr_status = ScanStatus.PASS
        # Accepted risk should not block
        assert dashboard.is_production_ready()
