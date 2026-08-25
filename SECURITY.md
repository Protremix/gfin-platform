# Security Policy

## 🛡️ Commitment to Security

The Global Fraud Intelligence Network (GFIN) is a secure, evidence-based, digital fraud intelligence platform. Given the sensitivity of fraud intelligence and cross-jurisdictional telemetry, maintaining the highest standard of security is fundamental to our platform.

---

## 📋 Supported Versions

Security updates are actively maintained for the following versions:

| Version | Supported          | Notes                                    |
| ------- | ------------------ | ---------------------------------------- |
| v1.0.x  | :white_check_mark: | Current active release branch            |
| < 1.0   | :x:                | MVP / Pre-release versions unsupported   |

---

## 🚨 Reporting a Vulnerability

If you discover a potential security vulnerability within GFIN, please report it responsibly. **Do NOT open a public GitHub issue for security vulnerabilities.**

### Submission Process
1. **GitHub Security Advisories:**
   - Submit a private security advisory report directly via GitHub: navigate to the repository's **Security** tab -> **Advisories** -> **Report a vulnerability**.
2. **Security Contact:**
   - Security contact to be established — use GitHub Security Advisories for now.

### Report Contents
Please include as much detail as possible to help us reproduce and resolve the issue:
- Type of vulnerability (e.g., SQL injection, authentication bypass, remote code execution)
- Step-by-step instructions or proof-of-concept (PoC) script to reproduce the vulnerability
- Affected component, module, or package (e.g., Module 02 Model Gateway, Service API Gateway)
- Potential impact of the vulnerability
- Any suggested mitigations or patches if available

---

## ⏱️ Responsible Disclosure Timeline

GFIN maintainers adhere to a responsible disclosure policy:

- **Initial Acknowledgment:** Within 48 hours of receipt.
- **Triage & Assessment:** Within 5 business days, confirming vulnerability status and severity rating (CVSS).
- **Remediation & Patching:** Target resolution within 30 days for critical issues and 60 days for moderate/low issues.
- **Public Disclosure:** Public release of the advisory occurs only after a patch is released and deployed across supported releases.

---

## 🔒 Confidential & Restricted Information

Under no circumstances should sensitive operational, private, or law enforcement data be submitted in vulnerability reports or publicly disclosed.

The following information **must NEVER be publicly disclosed, committed to code, or included in test suites**:

1. **Credentials & Secrets:** Production API keys, database passwords, private cryptographic keys, JWT secrets, OAuth tokens.
2. **Citizen & Personal Data (PII):** Real identity details, passport/ID numbers, real phone numbers, real physical addresses.
3. **Police Case Data:** Active or historical law enforcement case files, judicial warrants, intelligence dossiers, or investigation records.
4. **Raw Evidence Data:** Live telemetry, intercepted financial transactions, unredacted fraud reports, or forensic evidence dumps.

Always use synthetic test identifiers (e.g., `TEST-PHONE-001`, `TEST-EMAIL-001`) in all public communication and bug reports.
