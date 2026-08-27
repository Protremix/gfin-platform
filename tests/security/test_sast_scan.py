"""Tests for SAST, dependency, and secret scanners."""

from __future__ import annotations

import sys
import tempfile

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from security.sast_scan import DependencyScanner, Finding, SASTScanner, SecretScanner, Severity


class TestSASTScanner:
    """Test SAST scanner for Python code vulnerabilities."""

    def test_detect_hardcoded_password(self):
        """Hardcoded password should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('password = "supersecretpassword"\n')
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 1
        assert findings[0].severity in (Severity.HIGH, Severity.CRITICAL)
        assert "password" in findings[0].description.lower()

    def test_detect_hardcoded_api_key(self):
        """Hardcoded API key should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"\n')
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) >= 1
        assert any(f.severity == Severity.CRITICAL for f in findings)

    def test_detect_command_injection(self):
        """Command injection should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import subprocess\nsubprocess.run(['cmd'], shell=True)\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert any("command injection" in f.description.lower() for f in findings)

    def test_detect_pickle_loads(self):
        """pickle.loads should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import pickle\ndata = pickle.loads(b'\\x80\\x04')\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert any("pickle" in f.description.lower() for f in findings)

    def test_detect_weak_crypto(self):
        """Weak crypto (MD5) for passwords should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import hashlib\nh = hashlib.md5(b'password123')\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert any("md5" in f.description.lower() or "weak" in f.description.lower() for f in findings)

    def test_detect_debug_mode(self):
        """Debug mode should be detected."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("app.run(debug=True)\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert any("debug" in f.description.lower() for f in findings)

    def test_clean_code_no_findings(self):
        """Clean code should have no findings."""
        scanner = SASTScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import os\nvalue = os.environ.get('SECRET')\nprint(value)\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 0

    def test_scan_nonexistent_file(self):
        """Scanning nonexistent file should return empty list."""
        scanner = SASTScanner()
        findings = scanner.scan_file("/nonexistent/file.py")
        assert findings == []

    def test_finding_to_dict(self):
        """Finding to_dict should include all fields."""
        finding = Finding(
            scanner="SAST",
            severity=Severity.HIGH,
            file="test.py",
            line=10,
            description="Test finding",
            remediation="Fix it",
        )
        d = finding.to_dict()
        assert d["scanner"] == "SAST"
        assert d["severity"] == "HIGH"
        assert d["line"] == "10"


class TestSecretScanner:
    """Test secret scanner for hardcoded credentials."""

    def test_detect_aws_key(self):
        """AWS access key should be detected."""
        scanner = SecretScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('aws_key = "AKIAIOSFODNN7EXAMPLE"\n')
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_detect_github_token(self):
        """GitHub token should be detected."""
        scanner = SecretScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"\n')
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_detect_private_key(self):
        """Private key should be detected."""
        scanner = SecretScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write('key = "-----BEGIN RSA PRIVATE KEY-----\\n"\n')
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_clean_code_no_secret_findings(self):
        """Code without secrets should have no findings."""
        scanner = SecretScanner()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import os\nkey = os.environ.get('AWS_KEY')\n")
            f.flush()
            findings = scanner.scan_file(f.name)
        assert len(findings) == 0


class TestDependencyScanner:
    """Test dependency scanner for vulnerable packages."""

    def test_scan_nonexistent_requirements(self):
        """Scanning nonexistent requirements file should return empty."""
        scanner = DependencyScanner()
        findings = scanner.scan_requirements("/nonexistent/requirements.txt")
        assert findings == []

    def test_scan_vulnerable_package(self):
        """Vulnerable package version should be detected."""
        scanner = DependencyScanner()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("requests==2.25.0\n")
            f.flush()
            findings = scanner.scan_requirements(f.name)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_scan_safe_package(self):
        """Safe package version should not trigger findings."""
        scanner = DependencyScanner()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("requests==2.32.0\n")
            f.flush()
            findings = scanner.scan_requirements(f.name)
        assert len(findings) == 0

    def test_scan_multiple_packages(self):
        """Multiple packages should all be scanned."""
        scanner = DependencyScanner()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("requests==2.25.0\npyyaml==5.3.0\njinja2==3.0.0\n")
            f.flush()
            findings = scanner.scan_requirements(f.name)
        assert len(findings) == 3

    def test_scan_ignores_comments(self):
        """Comments in requirements should be ignored."""
        scanner = DependencyScanner()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("# This is a comment\nrequests==2.32.0\n")
            f.flush()
            findings = scanner.scan_requirements(f.name)
        assert len(findings) == 0
