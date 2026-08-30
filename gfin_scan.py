#!/usr/bin/env python3
"""
GFIN Security Scanner — Core scanning engine for GitHub Actions.
Scans codebases for fraud patterns, security vulnerabilities, and suspicious code.
Part of the Global Fraud Intelligence Network (GFIN) by Protremix Technology.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Severity levels
SEVERITY_ORDER = ['low', 'medium', 'high', 'critical']

# Fraud patterns database
FRAUD_PATTERNS = [
    {
        'id': 'GFIN-001',
        'name': 'Hardcoded Credentials',
        'pattern': r'(password|passwd|pwd|secret|api_key|apikey|token|auth)\s*[=:]\s*["\'][^"\']{8,}["\']',
        'severity': 'high',
        'description': 'Hardcoded credential detected in source code',
        'category': 'credential-exposure'
    },
    {
        'id': 'GFIN-002',
        'name': 'Suspicious Money Pattern',
        'pattern': r'(amount|transfer|payment|deposit|withdraw)\s*[=:]\s*\d{6,}',
        'severity': 'medium',
        'description': 'Large hardcoded transaction amount detected',
        'category': 'fraud-pattern'
    },
    {
        'id': 'GFIN-003',
        'name': 'SQL Injection Vector',
        'pattern': r'(execute|query|raw)\s*\(\s*["\'].*\+.*["\']\s*\)',
        'severity': 'high',
        'description': 'Potential SQL injection via string concatenation',
        'category': 'injection'
    },
    {
        'id': 'GFIN-004',
        'name': 'Weak Crypto Usage',
        'pattern': r'(md5|sha1|des|rc4)\s*\(',
        'severity': 'medium',
        'description': 'Weak cryptographic algorithm detected',
        'category': 'crypto'
    },
    {
        'id': 'GFIN-005',
        'name': 'Debug Code Left in Production',
        'pattern': r'(print|console\.log|debugger|breakpoint)\s*\(',
        'severity': 'low',
        'description': 'Debug code found — should be removed for production',
        'category': 'code-quality'
    },
    {
        'id': 'GFIN-006',
        'name': 'Unsafe Eval Usage',
        'pattern': r'(eval|exec)\s*\(',
        'severity': 'high',
        'description': 'Use of eval/exec can lead to code injection',
        'category': 'injection'
    },
    {
        'id': 'GFIN-007',
        'name': 'Exposed Private Key',
        'pattern': r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+)?PRIVATE\s+KEY-----',
        'severity': 'critical',
        'description': 'Private key material found in repository',
        'category': 'credential-exposure'
    },
    {
        'id': 'GFIN-008',
        'name': 'Suspicious URL Redirect',
        'pattern': r'redirect\s*(\(\s*)?["\']https?://(?!localhost|127\.0\.0\.1)',
        'severity': 'medium',
        'description': 'External redirect detected — verify destination',
        'category': 'fraud-pattern'
    },
    {
        'id': 'GFIN-009',
        'name': 'Hardcoded IP Address',
        'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'severity': 'low',
        'description': 'Hardcoded IP address found',
        'category': 'info'
    },
    {
        'id': 'GFIN-010',
        'name': 'Money Laundering Pattern',
        'pattern': r'(launder|mix|tumble|wash)\s*(money|funds|coins|btc|eth)',
        'severity': 'critical',
        'description': 'Potential money laundering code pattern detected',
        'category': 'fraud-pattern'
    },
    {
        'id': 'GFIN-011',
        'name': 'Insecure HTTP',
        'pattern': r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)',
        'severity': 'medium',
        'description': 'Insecure HTTP protocol used instead of HTTPS',
        'category': 'network-security'
    },
    {
        'id': 'GFIN-012',
        'name': 'Dangerous File Permission',
        'pattern': r'chmod\s+777',
        'severity': 'medium',
        'description': 'World-writable file permission set',
        'category': 'permission'
    },
]

# File extensions to scan
SCAN_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
    '.rb', '.php', '.c', '.cpp', '.h', '.sh', '.yml', '.yaml',
    '.json', '.xml', '.sql', '.env', '.cfg', '.conf', '.ini',
    '.html', '.vue', '.svelte'
}

# Max file size to scan (1MB)
MAX_FILE_SIZE = 1024 * 1024


class GFINScanner:
    def __init__(self, path, scan_type='full', severity_threshold='medium', 
                 output_format='sarif', exclude_patterns=None, ai_analysis=False):
        self.path = Path(path).resolve()
        self.scan_type = scan_type
        self.severity_threshold = severity_threshold
        self.output_format = output_format
        self.exclude_patterns = exclude_patterns or []
        self.ai_analysis = ai_analysis
        self.findings = []
        self.scanned_files = 0
        self.start_time = datetime.utcnow()
    
    def should_scan_file(self, filepath):
        """Check if a file should be scanned."""
        rel_path = str(filepath.relative_to(self.path))
        
        # Check exclusions
        for pattern in self.exclude_patterns:
            if pattern.strip() and pattern.strip() in rel_path:
                return False
        
        # Check extension
        ext = filepath.suffix.lower()
        if ext not in SCAN_EXTENSIONS:
            return False
        
        # Check file size
        try:
            size = filepath.stat().st_size
            if size > MAX_FILE_SIZE:
                return False
        except OSError:
            return False
        
        return True
    
    def scan_file(self, filepath):
        """Scan a single file for fraud patterns."""
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return
        
        rel_path = str(filepath.relative_to(self.path))
        
        for pattern_def in FRAUD_PATTERNS:
            # Filter by scan type
            if self.scan_type == 'code' and pattern_def['category'] in ['fraud-pattern']:
                continue
            if self.scan_type == 'fraud-patterns' and pattern_def['category'] != 'fraud-pattern':
                continue
            
            # Skip if below severity threshold
            if SEVERITY_ORDER.index(pattern_def['severity']) < SEVERITY_ORDER.index(self.severity_threshold):
                continue
            
            matches = re.finditer(pattern_def['pattern'], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                self.findings.append({
                    'id': pattern_def['id'],
                    'name': pattern_def['name'],
                    'severity': pattern_def['severity'],
                    'description': pattern_def['description'],
                    'category': pattern_def['category'],
                    'file': rel_path,
                    'line': line_num,
                    'snippet': match.group()[:100],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                })
        
        self.scanned_files += 1
    
    def scan_dependencies(self):
        """Scan dependency files for known vulnerable packages."""
        dep_files = [
            'requirements.txt', 'package.json', 'package-lock.json',
            'Pipfile', 'go.mod', 'Cargo.toml', 'pom.xml'
        ]
        
        for dep_file in dep_files:
            filepath = self.path / dep_file
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    rel_path = str(filepath.relative_to(self.path))
                    
                    # Check for common red flags in dependencies
                    if 'requirements.txt' in dep_file:
                        # Check for unpinned versions
                        for i, line in enumerate(content.split('\n'), 1):
                            if '==' not in line and line.strip() and not line.startswith('#'):
                                if SEVERITY_ORDER.index('low') >= SEVERITY_ORDER.index(self.severity_threshold):
                                    self.findings.append({
                                        'id': 'GFIN-DEP-001',
                                        'name': 'Unpinned Dependency',
                                        'severity': 'low',
                                        'description': f'Dependency without version pin: {line.strip()}',
                                        'category': 'dependency',
                                        'file': rel_path,
                                        'line': i,
                                        'snippet': line.strip()[:100],
                                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                                    })
                except Exception:
                    pass
    
    def run(self):
        """Run the full scan."""
        # Walk the directory
        for filepath in self.path.rglob('*'):
            if filepath.is_file() and self.should_scan_file(filepath):
                self.scan_file(filepath)
        
        # Scan dependencies if requested
        if self.scan_type in ('full', 'dependencies'):
            self.scan_dependencies()
        
        return self.findings
    
    def generate_report(self):
        """Generate report in the specified format."""
        if self.output_format == 'json':
            return self._generate_json()
        elif self.output_format == 'sarif':
            return self._generate_sarif()
        elif self.output_format == 'markdown':
            return self._generate_markdown()
        elif self.output_format == 'html':
            return self._generate_html()
        else:
            return self._generate_sarif()
    
    def _generate_json(self):
        return json.dumps({
            'scanner': 'GFIN Security Scanner',
            'version': '1.0.0',
            'scan_date': self.start_time.isoformat() + 'Z',
            'path': str(self.path),
            'files_scanned': self.scanned_files,
            'total_findings': len(self.findings),
            'findings_by_severity': {
                'critical': len([f for f in self.findings if f['severity'] == 'critical']),
                'high': len([f for f in self.findings if f['severity'] == 'high']),
                'medium': len([f for f in self.findings if f['severity'] == 'medium']),
                'low': len([f for f in self.findings if f['severity'] == 'low']),
            },
            'findings': self.findings
        }, indent=2)
    
    def _generate_sarif(self):
        """Generate SARIF 2.1.0 format report."""
        results = []
        for finding in self.findings:
            results.append({
                'ruleId': finding['id'],
                'level': {
                    'critical': 'error',
                    'high': 'error',
                    'medium': 'warning',
                    'low': 'note'
                }.get(finding['severity'], 'warning'),
                'message': {
                    'text': f"{finding['name']}: {finding['description']}"
                },
                'locations': [{
                    'physicalLocation': {
                        'artifactLocation': {
                            'uri': finding['file']
                        },
                        'region': {
                            'startLine': finding['line']
                        }
                    }
                }],
                'partialFingerprints': {
                    'primaryLocationLineHash': finding['snippet'][:50]
                }
            })
        
        sarif = {
            '$schema': 'https://docs.oasis-open.org/sarif/sarif/v2.1.0/cos02/sarif-schema-2.1.0.json',
            'version': '2.1.0',
            'runs': [{
                'tool': {
                    'driver': {
                        'name': 'GFIN Security Scanner',
                        'version': '1.0.0',
                        'informationUri': 'https://github.com/Protremix/gfin-platform',
                        'rules': [
                            {
                                'id': p['id'],
                                'name': p['name'],
                                'shortDescription': {'text': p['description']},
                                'properties': {
                                    'severity': p['severity'],
                                    'category': p['category']
                                }
                            }
                            for p in FRAUD_PATTERNS
                        ]
                    }
                },
                'results': results
            }]
        }
        return json.dumps(sarif, indent=2)
    
    def _generate_markdown(self):
        """Generate Markdown report."""
        lines = [
            '# GFIN Security Scanner Report',
            '',
            f'**Scan Date:** {self.start_time.isoformat()}Z',
            f'**Path:** `{self.path}`',
            f'**Files Scanned:** {self.scanned_files}',
            f'**Total Findings:** {len(self.findings)}',
            '',
            '## Summary',
            '',
            '| Severity | Count |',
            '|----------|-------|',
            f'| 🔴 Critical | {len([f for f in self.findings if f["severity"] == "critical"])} |',
            f'| 🟠 High | {len([f for f in self.findings if f["severity"] == "high"])} |',
            f'| 🟡 Medium | {len([f for f in self.findings if f["severity"] == "medium"])} |',
            f'| 🔵 Low | {len([f for f in self.findings if f["severity"] == "low"])} |',
            '',
            '## Findings',
            ''
        ]
        
        for finding in sorted(self.findings, key=lambda f: SEVERITY_ORDER.index(f['severity']), reverse=True):
            emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}.get(finding['severity'], '⚪')
            lines.extend([
                f'### {emoji} {finding["id"]}: {finding["name"]}',
                f'- **File:** `{finding["file"]}:{finding["line"]}`',
                f'- **Severity:** {finding["severity"]}',
                f'- **Category:** {finding["category"]}',
                f'- **Description:** {finding["description"]}',
                f'- **Snippet:** `{finding["snippet"]}`',
                ''
            ])
        
        return '\n'.join(lines)
    
    def _generate_html(self):
        """Generate HTML report."""
        findings_html = []
        for f in self.findings:
            color = {'critical': '#dc2626', 'high': '#ea580c', 'medium': '#ca8a04', 'low': '#2563eb'}.get(f['severity'], '#6b7280')
            findings_html.append(f"""
            <tr>
                <td><span style="color:{color};font-weight:bold">{f['severity'].upper()}</span></td>
                <td>{f['id']}</td>
                <td>{f['name']}</td>
                <td><code>{f['file']}:{f['line']}</code></td>
                <td>{f['description']}</td>
            </tr>""")
        
        return f"""<!DOCTYPE html>
<html>
<head><title>GFIN Security Report</title>
<style>
body {{ font-family: sans-serif; margin: 40px; background: #0d1117; color: #c9d1d9; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; }}
tr:nth-child(even) {{ background: #161b22; }}
</style></head>
<body>
<h1>🛡️ GFIN Security Scanner Report</h1>
<p>Scan Date: {self.start_time.isoformat()}Z | Files Scanned: {self.scanned_files} | Findings: {len(self.findings)}</p>
<table>
<tr><th>Severity</th><th>ID</th><th>Name</th><th>Location</th><th>Description</th></tr>
{''.join(findings_html)}
</table>
</body></html>"""


def main():
    scan_type = os.environ.get('INPUT_SCAN-TYPE', os.environ.get('INPUT_SCAN_TYPE', 'full'))
    severity_threshold = os.environ.get('INPUT_SEVERITY-THRESHOLD', os.environ.get('INPUT_SEVERITY_THRESHOLD', 'medium'))
    path = os.environ.get('INPUT_PATH', '.')
    output_format = os.environ.get('INPUT_OUTPUT-FORMAT', os.environ.get('INPUT_OUTPUT_FORMAT', 'sarif'))
    fail_on_findings = os.environ.get('INPUT_FAIL-ON-FINDINGS', os.environ.get('INPUT_FAIL_ON_FINDINGS', 'true')).lower() == 'true'
    exclude_patterns = os.environ.get('INPUT_EXCLUDE-PATTERNS', os.environ.get('INPUT_EXCLUDE_PATTERNS', 'node_modules,venv,.git,dist,build')).split(',')
    
    print(f"🛡️  GFIN Security Scanner v1.0.0")
    print(f"   Path: {path}")
    print(f"   Scan type: {scan_type}")
    print(f"   Severity threshold: {severity_threshold}")
    print(f"   Output format: {output_format}")
    print()
    
    scanner = GFINScanner(
        path=path,
        scan_type=scan_type,
        severity_threshold=severity_threshold,
        output_format=output_format,
        exclude_patterns=exclude_patterns
    )
    
    findings = scanner.run()
    
    # Print summary
    critical = len([f for f in findings if f['severity'] == 'critical'])
    high = len([f for f in findings if f['severity'] == 'high'])
    medium = len([f for f in findings if f['severity'] == 'medium'])
    low = len([f for f in findings if f['severity'] == 'low'])
    
    print(f"📊 Scan Results:")
    print(f"   Files scanned: {scanner.scanned_files}")
    print(f"   Total findings: {len(findings)}")
    print(f"   🔴 Critical: {critical}")
    print(f"   🟠 High: {high}")
    print(f"   🟡 Medium: {medium}")
    print(f"   🔵 Low: {low}")
    print()
    
    # Generate report
    report = scanner.generate_report()
    report_path = f"gfin-report.{output_format}"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"📄 Report saved: {report_path}")
    
    # Set output
    github_output = os.environ.get('GITHUB_OUTPUT', '/dev/null')
    with open(github_output, 'a') as f:
        f.write(f"findings-count={len(findings)}\n")
        f.write(f"critical-count={critical}\n")
        f.write(f"report-path={report_path}\n")
    
    # Exit code
    if fail_on_findings and (critical > 0 or high > 0):
        print(f"\n❌ Scan failed: {critical + high} high/critical findings detected")
        sys.exit(1)
    elif findings:
        print(f"\n⚠️  Scan completed with {len(findings)} findings")
    else:
        print(f"\n✅ Scan completed: No findings")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
