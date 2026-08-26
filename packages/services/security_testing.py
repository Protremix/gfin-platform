"""GFIN Security Testing — Module 36.

Security test framework: vulnerability scanning, penetration test tracking,
security checklist verification, and threat model validation.

Layer A: In-memory security test tracking
Layer B: Automated security scanning, penetration testing tools (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityTestType(str, Enum):
    VULNERABILITY_SCAN = "VULNERABILITY_SCAN"
    PENETRATION_TEST = "PENETRATION_TEST"
    SECURITY_CHECKLIST = "SECURITY_CHECKLIST"
    THREAT_MODEL_VALIDATION = "THREAT_MODEL_VALIDATION"
    CODE_AUDIT = "CODE_AUDIT"


class SecurityTestStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SeverityLevel(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_ORDER: dict[str, int] = {
    SeverityLevel.INFO.value: 1,
    SeverityLevel.LOW.value: 2,
    SeverityLevel.MEDIUM.value: 3,
    SeverityLevel.HIGH.value: 4,
    SeverityLevel.CRITICAL.value: 5,
}


class SecurityFinding(BaseModel):
    """A security finding from a test."""

    id: str
    test_id: str
    title: str
    severity: str = SeverityLevel.INFO.value
    description: str = ""
    component: str = ""
    remediation: str = ""
    status: str = "OPEN"  # OPEN, REMEDIATED, ACCEPTED, FALSE_POSITIVE
    found_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    remediated_at: datetime | None = None

    def remediate(self) -> None:
        self.status = "REMEDIATED"
        self.remediated_at = datetime.now(UTC)

    def accept_risk(self) -> None:
        self.status = "ACCEPTED"

    def mark_false_positive(self) -> None:
        self.status = "FALSE_POSITIVE"


class SecurityTest(BaseModel):
    """A security test execution."""

    id: str
    name: str
    test_type: str
    status: str = SecurityTestStatus.PENDING.value
    component: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    findings_count: int = 0
    passed: bool = False
    description: str = ""

    def start(self) -> None:
        self.status = SecurityTestStatus.RUNNING.value
        self.started_at = datetime.now(UTC)

    def complete(self, passed: bool, findings_count: int = 0) -> None:
        self.status = SecurityTestStatus.PASSED.value if passed else SecurityTestStatus.FAILED.value
        self.completed_at = datetime.now(UTC)
        self.passed = passed
        self.findings_count = findings_count


class SecurityChecklistItem(BaseModel):
    """A security checklist item."""

    id: str
    category: str
    description: str
    required: bool = True
    verified: bool = False
    notes: str = ""


class SecurityTestService:
    """Service for managing security tests and findings.

    Per Directive §14: Security is paramount.
    """

    def __init__(self) -> None:
        self._tests: dict[str, SecurityTest] = {}
        self._findings: list[SecurityFinding] = []
        self._checklist: dict[str, SecurityChecklistItem] = {}
        self._test_counter = 0
        self._finding_counter = 0
        self._checklist_counter = 0
        self._init_checklist()

    def _init_checklist(self) -> None:
        """Initialize default security checklist."""
        defaults = [
            ("AUTH", "OIDC/OAuth2 authentication implemented"),
            ("AUTH", "Rate limiting on all API endpoints"),
            ("AUTH", "Role-based access control (RBAC) enforced"),
            ("DATA", "Data classification levels defined"),
            ("DATA", "Encryption at rest for sensitive data"),
            ("DATA", "Encryption in transit (TLS)"),
            ("DATA", "PII fields filtered in responses"),
            ("AUDIT", "Audit logging on all sensitive operations"),
            ("AUDIT", "Audit log immutability ensured"),
            ("INPUT", "All external input treated as untrusted"),
            ("INPUT", "Input validation on all endpoints"),
            ("INPUT", "SQL injection prevention"),
            ("INPUT", "XSS prevention"),
            ("FEDERATION", "Cross-border data minimization enforced"),
            ("FEDERATION", "Policy filtering on federation messages"),
        ]
        for category, desc in defaults:
            self._checklist_counter += 1
            item = SecurityChecklistItem(
                id=f"SC-{self._checklist_counter:04d}",
                category=category,
                description=desc,
            )
            self._checklist[item.id] = item

    def create_test(
        self, name: str, test_type: str, component: str = "", description: str = ""
    ) -> SecurityTest:
        self._test_counter += 1
        test = SecurityTest(
            id=f"ST-{self._test_counter:06d}",
            name=name,
            test_type=test_type,
            component=component,
            description=description,
        )
        self._tests[test.id] = test
        return test

    def run_test(
        self, test_id: str, passed: bool, findings: list[dict[str, Any]] | None = None
    ) -> SecurityTest | None:
        """Run a security test and record findings."""
        test = self._tests.get(test_id)
        if test is None:
            return None

        test.start()
        finding_count = 0

        if findings:
            for f in findings:
                self._finding_counter += 1
                finding = SecurityFinding(
                    id=f"SF-{self._finding_counter:06d}",
                    test_id=test_id,
                    title=f.get("title", "Unknown"),
                    severity=f.get("severity", SeverityLevel.INFO.value),
                    description=f.get("description", ""),
                    component=f.get("component", test.component),
                    remediation=f.get("remediation", ""),
                )
                self._findings.append(finding)
                finding_count += 1

        test.complete(passed=passed, findings_count=finding_count)
        return test

    def get_test(self, test_id: str) -> SecurityTest | None:
        return self._tests.get(test_id)

    def list_tests(
        self, status: str | None = None, test_type: str | None = None
    ) -> list[SecurityTest]:
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        if test_type:
            tests = [t for t in tests if t.test_type == test_type]
        return tests

    def get_finding(self, finding_id: str) -> SecurityFinding | None:
        for f in self._findings:
            if f.id == finding_id:
                return f
        return None

    def list_findings(
        self,
        severity: str | None = None,
        status: str | None = None,
        test_id: str | None = None,
    ) -> list[SecurityFinding]:
        findings = list(self._findings)
        if severity:
            findings = [f for f in findings if f.severity == severity]
        if status:
            findings = [f for f in findings if f.status == status]
        if test_id:
            findings = [f for f in findings if f.test_id == test_id]
        return findings

    def remediate_finding(self, finding_id: str) -> bool:
        f = self.get_finding(finding_id)
        if f is None:
            return False
        f.remediate()
        return True

    def accept_finding_risk(self, finding_id: str) -> bool:
        f = self.get_finding(finding_id)
        if f is None:
            return False
        f.accept_risk()
        return True

    def mark_false_positive(self, finding_id: str) -> bool:
        f = self.get_finding(finding_id)
        if f is None:
            return False
        f.mark_false_positive()
        return True

    def get_checklist(self) -> list[SecurityChecklistItem]:
        return list(self._checklist.values())

    def verify_checklist_item(self, item_id: str, notes: str = "") -> bool:
        item = self._checklist.get(item_id)
        if item is None:
            return False
        item.verified = True
        item.notes = notes
        return True

    def get_checklist_summary(self) -> dict[str, Any]:
        items = list(self._checklist.values())
        return {
            "total": len(items),
            "verified": sum(1 for i in items if i.verified),
            "unverified": sum(1 for i in items if not i.verified),
            "required_unverified": sum(1 for i in items if i.required and not i.verified),
        }

    def get_security_summary(self) -> dict[str, Any]:
        """Get overall security summary."""
        findings = list(self._findings)
        open_findings = [f for f in findings if f.status == "OPEN"]
        critical = [f for f in open_findings if f.severity == SeverityLevel.CRITICAL.value]
        high = [f for f in open_findings if f.severity == SeverityLevel.HIGH.value]
        checklist = self.get_checklist_summary()
        return {
            "total_tests": len(self._tests),
            "passed_tests": sum(1 for t in self._tests.values() if t.passed),
            "failed_tests": sum(
                1
                for t in self._tests.values()
                if not t.passed and t.status == SecurityTestStatus.FAILED.value
            ),
            "total_findings": len(findings),
            "open_findings": len(open_findings),
            "critical_findings": len(critical),
            "high_findings": len(high),
            "checklist": checklist,
        }

    @property
    def test_count(self) -> int:
        return len(self._tests)

    @property
    def finding_count(self) -> int:
        return len(self._findings)
