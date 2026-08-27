"""SAST, dependency, and secret scanners for GFIN.

Per Luna Directive — Focus Area 4: Security and governance preparation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Finding:
    """A security finding from a scan."""

    scanner: str
    severity: Severity
    file: str
    line: int
    description: str
    remediation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "scanner": self.scanner,
            "severity": self.severity.value,
            "file": self.file,
            "line": str(self.line),
            "description": self.description,
            "remediation": self.remediation,
        }


# Pattern definitions
HARDCODED_PASSWORD_RE = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|api_key|apikey)\s*[=:]\s*['\"][^'\"]{4,}['\"]"
)
HARDCODED_API_KEY_RE = re.compile(
    r"(?i)(api_key|apikey|access_token|auth_token)\s*[=:]\s*['\"][^'\"]{10,}['\"]"
)
AWS_KEY_RE = re.compile(r"AKIA[0-9A-Z]{16}")
GITHUB_TOKEN_RE = re.compile(r"gh[pousr]_[A-Za-z0-9_]{36}")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----")
JWT_SECRET_RE = re.compile(r"(?i)jwt[_-]?secret\s*[=:]\s*['\"][^'\"]{8,}['\"]")

SQL_INJECTION_RE = re.compile(
    r"(?i)(f['\"].*\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(from|into|table|where)\b)"
)
COMMAND_INJECTION_RE = re.compile(r"os\.system\s*\(|subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True")
PICKLE_LOAD_RE = re.compile(r"pickle\.loads?\s*\(")
WEAK_CRYPTO_RE = re.compile(r"hashlib\.(md5|sha1)\s*\(")
PATH_TRAVERSAL_RE = re.compile(r"open\s*\(\s*['\"].*\$\{|open\s*\(\s*f['\"]")
DEBUG_MODE_RE = re.compile(r"(?i)debug\s*=\s*True")


class SASTScanner:
    """Static Application Security Testing scanner for Python code."""

    def scan_file(self, filepath: str) -> list[Finding]:
        """Scan a single file for vulnerabilities."""
        path = Path(filepath)
        if not path.exists() or path.suffix != ".py":
            return []

        findings: list[Finding] = []
        lines = path.read_text().splitlines()

        for i, line in enumerate(lines, 1):
            # Hardcoded passwords
            if HARDCODED_PASSWORD_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.HIGH,
                    file=filepath,
                    line=i,
                    description="Hardcoded password or secret detected",
                    remediation="Move secrets to environment variables or Vault",
                ))

            # Hardcoded API keys
            if HARDCODED_API_KEY_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.CRITICAL,
                    file=filepath,
                    line=i,
                    description="Hardcoded API key detected",
                    remediation="Use environment variables or Vault for API keys",
                ))

            # SQL injection
            if SQL_INJECTION_RE.search(line) and "execute" in line.lower():
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.HIGH,
                    file=filepath,
                    line=i,
                    description="Potential SQL injection — raw SQL with string formatting",
                    remediation="Use parameterized queries",
                ))

            # Command injection
            if COMMAND_INJECTION_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.CRITICAL,
                    file=filepath,
                    line=i,
                    description="Command injection risk — os.system or subprocess with shell=True",
                    remediation="Use subprocess with shell=False and argument lists",
                ))

            # Unsafe deserialization
            if PICKLE_LOAD_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.HIGH,
                    file=filepath,
                    line=i,
                    description="Unsafe deserialization — pickle.loads can execute arbitrary code",
                    remediation="Use json.loads or restrict pickle to trusted sources",
                ))

            # Weak crypto
            if WEAK_CRYPTO_RE.search(line) and "password" in line.lower():
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.MEDIUM,
                    file=filepath,
                    line=i,
                    description="Weak hash algorithm (MD5/SHA1) used for passwords",
                    remediation="Use bcrypt, argon2, or PBKDF2 for password hashing",
                ))

            # Path traversal
            if PATH_TRAVERSAL_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.MEDIUM,
                    file=filepath,
                    line=i,
                    description="Potential path traversal — open with user input",
                    remediation="Validate and sanitize file paths",
                ))

            # Debug mode
            if DEBUG_MODE_RE.search(line):
                findings.append(Finding(
                    scanner="SAST",
                    severity=Severity.LOW,
                    file=filepath,
                    line=i,
                    description="Debug mode enabled in code",
                    remediation="Disable debug mode in production",
                ))

        return findings

    def scan_directory(self, dirpath: str) -> list[Finding]:
        """Scan all Python files in a directory."""
        findings: list[Finding] = []
        for py_file in Path(dirpath).rglob("*.py"):
            findings.extend(self.scan_file(str(py_file)))
        return findings


class SecretScanner:
    """Scans for hardcoded secrets and credentials."""

    def scan_file(self, filepath: str) -> list[Finding]:
        """Scan a file for hardcoded secrets."""
        path = Path(filepath)
        if not path.exists():
            return []

        findings: list[Finding] = []
        lines = path.read_text().splitlines()

        for i, line in enumerate(lines, 1):
            if AWS_KEY_RE.search(line):
                findings.append(Finding(
                    scanner="SECRET",
                    severity=Severity.CRITICAL,
                    file=filepath,
                    line=i,
                    description="AWS access key detected",
                    remediation="Remove key from code and rotate in AWS console",
                ))

            if GITHUB_TOKEN_RE.search(line):
                findings.append(Finding(
                    scanner="SECRET",
                    severity=Severity.CRITICAL,
                    file=filepath,
                    line=i,
                    description="GitHub token detected",
                    remediation="Revoke token and use GitHub Actions secrets",
                ))

            if PRIVATE_KEY_RE.search(line):
                findings.append(Finding(
                    scanner="SECRET",
                    severity=Severity.CRITICAL,
                    file=filepath,
                    line=i,
                    description="Private key detected in source code",
                    remediation="Remove private key and store in Vault",
                ))

            if JWT_SECRET_RE.search(line):
                findings.append(Finding(
                    scanner="SECRET",
                    severity=Severity.HIGH,
                    file=filepath,
                    line=i,
                    description="JWT secret detected in source code",
                    remediation="Move JWT secret to environment variable",
                ))

        return findings


class DependencyScanner:
    """Scans requirements.txt for known vulnerable packages."""

    # Known vulnerable packages (simplified CVE database)
    KNOWN_VULNERABILITIES = {
        "requests": {"min_safe": "2.32.0", "cve": "CVE-2024-35195", "description": "Session verification bypass"},
        "cryptography": {"min_safe": "42.0.0", "cve": "CVE-2024-26130", "description": "NULL pointer dereference in PKCS12"},
        "pyyaml": {"min_safe": "5.4.0", "cve": "CVE-2020-14343", "description": "Arbitrary code execution via yaml.load"},
        "jinja2": {"min_safe": "3.1.3", "cve": "CVE-2024-22195", "description": "XSS vulnerability"},
        "aiohttp": {"min_safe": "3.9.4", "cve": "CVE-2024-30251", "description": "HTTP request smuggling"},
    }

    def scan_requirements(self, filepath: str = "requirements.txt") -> list[Finding]:
        """Scan requirements file for vulnerable packages."""
        path = Path(filepath)
        if not path.exists():
            return []

        findings: list[Finding] = []
        lines = path.read_text().splitlines()

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse package name and version
            if "==" in line:
                name, version = line.split("==", 1)
                name = name.strip().lower()
            elif ">=" in line:
                name = line.split(">=")[0].strip().lower()
                version = line.split(">=")[1].strip()
            else:
                continue

            if name in self.KNOWN_VULNERABILITIES:
                vuln = self.KNOWN_VULNERABILITIES[name]
                safe_version = vuln["min_safe"]
                if self._is_vulnerable(version, safe_version):
                    findings.append(Finding(
                        scanner="DEPENDENCY",
                        severity=Severity.HIGH,
                        file=filepath,
                        line=i,
                        description=f"Vulnerable package: {name}=={version} ({vuln['cve']}: {vuln['description']})",
                        remediation=f"Upgrade to {name}>={safe_version}",
                    ))

        return findings

    def _is_vulnerable(self, current: str, safe: str) -> bool:
        """Check if current version is below safe version."""
        try:
            current_parts = [int(x) for x in current.split(".")]
            safe_parts = [int(x) for x in safe.split(".")]
            return current_parts < safe_parts
        except (ValueError, IndexError):
            return False
