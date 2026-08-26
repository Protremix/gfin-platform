"""Tests for Security Testing — Module 36."""

import pytest

from services.security_testing import (
    SecurityFinding,
    SecurityTest,
    SecurityTestService,
    SecurityTestStatus,
    SecurityTestType,
    SeverityLevel,
)


@pytest.fixture
def service():
    return SecurityTestService()


# ─── SecurityFinding Tests ───


class TestSecurityFinding:
    def test_remediate(self):
        f = SecurityFinding(id="F1", test_id="T1", title="XSS vulnerability")
        f.remediate()
        assert f.status == "REMEDIATED"
        assert f.remediated_at is not None

    def test_accept_risk(self):
        f = SecurityFinding(id="F1", test_id="T1", title="Low risk")
        f.accept_risk()
        assert f.status == "ACCEPTED"

    def test_mark_false_positive(self):
        f = SecurityFinding(id="F1", test_id="T1", title="False alarm")
        f.mark_false_positive()
        assert f.status == "FALSE_POSITIVE"


# ─── SecurityTest Tests ───


class TestSecurityTest:
    def test_start(self):
        t = SecurityTest(id="T1", name="Test", test_type=SecurityTestType.VULNERABILITY_SCAN.value)
        t.start()
        assert t.status == SecurityTestStatus.RUNNING.value
        assert t.started_at is not None

    def test_complete_passed(self):
        t = SecurityTest(id="T1", name="Test", test_type=SecurityTestType.VULNERABILITY_SCAN.value)
        t.start()
        t.complete(passed=True, findings_count=0)
        assert t.status == SecurityTestStatus.PASSED.value
        assert t.passed is True

    def test_complete_failed(self):
        t = SecurityTest(id="T1", name="Test", test_type=SecurityTestType.VULNERABILITY_SCAN.value)
        t.start()
        t.complete(passed=False, findings_count=3)
        assert t.status == SecurityTestStatus.FAILED.value
        assert t.findings_count == 3


# ─── SecurityTestService Tests ───


class TestSecurityTestService:
    def test_create_test(self, service):
        t = service.create_test("Vuln Scan", SecurityTestType.VULNERABILITY_SCAN.value)
        assert t.id.startswith("ST-")
        assert service.test_count == 1

    def test_run_test_passed(self, service):
        t = service.create_test("Check", SecurityTestType.SECURITY_CHECKLIST.value)
        result = service.run_test(t.id, passed=True)
        assert result.status == SecurityTestStatus.PASSED.value

    def test_run_test_with_findings(self, service):
        t = service.create_test("Pen Test", SecurityTestType.PENETRATION_TEST.value)
        result = service.run_test(
            t.id,
            passed=False,
            findings=[
                {
                    "title": "SQL Injection",
                    "severity": SeverityLevel.HIGH.value,
                    "component": "api",
                },
                {"title": "XSS", "severity": SeverityLevel.MEDIUM.value, "component": "web"},
            ],
        )
        assert result.status == SecurityTestStatus.FAILED.value
        assert result.findings_count == 2
        assert service.finding_count == 2

    def test_run_nonexistent_test(self, service):
        assert service.run_test("nonexistent", True) is None

    def test_get_test(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        assert service.get_test(t.id) is not None
        assert service.get_test("nonexistent") is None

    def test_list_tests(self, service):
        service.create_test("A", SecurityTestType.VULNERABILITY_SCAN.value)
        service.create_test("B", SecurityTestType.PENETRATION_TEST.value)
        assert len(service.list_tests()) == 2
        assert len(service.list_tests(test_type=SecurityTestType.VULNERABILITY_SCAN.value)) == 1

    def test_list_tests_by_status(self, service):
        t = service.create_test("A", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(t.id, True)
        t2 = service.create_test("B", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(t2.id, False)
        passed = service.list_tests(status=SecurityTestStatus.PASSED.value)
        failed = service.list_tests(status=SecurityTestStatus.FAILED.value)
        assert len(passed) == 1
        assert len(failed) == 1


class TestFindings:
    def test_get_finding(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id, False, findings=[{"title": "XSS", "severity": SeverityLevel.HIGH.value}]
        )
        findings = service.list_findings()
        assert service.get_finding(findings[0].id) is not None
        assert service.get_finding("nonexistent") is None

    def test_list_findings_by_severity(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id,
            False,
            findings=[
                {"title": "Low", "severity": SeverityLevel.LOW.value},
                {"title": "High", "severity": SeverityLevel.HIGH.value},
                {"title": "Critical", "severity": SeverityLevel.CRITICAL.value},
            ],
        )
        high = service.list_findings(severity=SeverityLevel.HIGH.value)
        assert len(high) == 1

    def test_list_findings_open(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id, False, findings=[{"title": "XSS", "severity": SeverityLevel.HIGH.value}]
        )
        open_findings = service.list_findings(status="OPEN")
        assert len(open_findings) == 1

    def test_remediate_finding(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id, False, findings=[{"title": "XSS", "severity": SeverityLevel.HIGH.value}]
        )
        f = service.list_findings()[0]
        assert service.remediate_finding(f.id) is True
        assert f.status == "REMEDIATED"
        assert len(service.list_findings(status="OPEN")) == 0

    def test_accept_finding_risk(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id, False, findings=[{"title": "Low", "severity": SeverityLevel.LOW.value}]
        )
        f = service.list_findings()[0]
        assert service.accept_finding_risk(f.id) is True
        assert f.status == "ACCEPTED"

    def test_mark_false_positive(self, service):
        t = service.create_test("Test", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(
            t.id, False, findings=[{"title": "False", "severity": SeverityLevel.INFO.value}]
        )
        f = service.list_findings()[0]
        assert service.mark_false_positive(f.id) is True
        assert f.status == "FALSE_POSITIVE"

    def test_remediate_nonexistent(self, service):
        assert service.remediate_finding("nonexistent") is False


class TestChecklist:
    def test_default_checklist_exists(self, service):
        items = service.get_checklist()
        assert len(items) >= 15

    def test_verify_checklist_item(self, service):
        items = service.get_checklist()
        assert service.verify_checklist_item(items[0].id, "Verified") is True
        assert items[0].verified is True

    def test_verify_nonexistent(self, service):
        assert service.verify_checklist_item("nonexistent") is False

    def test_checklist_summary(self, service):
        summary = service.get_checklist_summary()
        assert summary["total"] >= 15
        assert summary["verified"] == 0
        assert summary["unverified"] >= 15
        assert summary["required_unverified"] >= 15

    def test_checklist_after_verification(self, service):
        items = service.get_checklist()
        service.verify_checklist_item(items[0].id)
        summary = service.get_checklist_summary()
        assert summary["verified"] == 1


class TestSecuritySummary:
    def test_summary(self, service):
        t1 = service.create_test("Test1", SecurityTestType.VULNERABILITY_SCAN.value)
        service.run_test(t1.id, True)
        t2 = service.create_test("Test2", SecurityTestType.PENETRATION_TEST.value)
        service.run_test(
            t2.id,
            False,
            findings=[
                {"title": "Critical Vuln", "severity": SeverityLevel.CRITICAL.value},
                {"title": "High Vuln", "severity": SeverityLevel.HIGH.value},
            ],
        )
        summary = service.get_security_summary()
        assert summary["total_tests"] == 2
        assert summary["passed_tests"] == 1
        assert summary["failed_tests"] == 1
        assert summary["total_findings"] == 2
        assert summary["open_findings"] == 2
        assert summary["critical_findings"] == 1
        assert summary["high_findings"] == 1

    def test_summary_empty(self, service):
        summary = service.get_security_summary()
        assert summary["total_tests"] == 0
        assert summary["total_findings"] == 0
