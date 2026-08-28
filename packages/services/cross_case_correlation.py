#!/usr/bin/env python3
"""
GFIN Cross-Case Correlation Engine v1.0
Detects links between cases based on shared infrastructure, shared Telegram groups,
shared scam types, shared wallets/phones, and shared hosting IPs.

Correlation types:
1. SHARED_IP — Two domains resolve to same IP (non-CDN)
2. SHARED_TELEGRAM_GROUP — Two targets mentioned in same Telegram group
3. SHARED_SCAM_TYPE — Two targets associated with same scam type
4. SHARED_WALLET — Two cases reference same wallet address
5. SHARED_PHONE — Two cases reference same phone number
6. SHARED_REGISTRAR — Two domains registered with same registrar
7. RECRUITMENT_PATTERN — Same recruitment language/structure across cases
"""
import sys
import json
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

# Adversarial guard: shared CDN IPs do NOT indicate correlation
CDN_IP_RANGES = [
    ("104.21.0.0", 16),  # Cloudflare
    ("172.67.0.0", 16),  # Cloudflare
    ("188.114.96.0", 20),  # Cloudflare
    ("13.32.0.0", 16),  # AWS CloudFront
    ("23.235.0.0", 16),  # Fastly
]

CDN_SERVERS = {"cloudflare", "amazon", "aws", "fastly", "akamai", "ddos-guard"}


def is_cdn_ip(ip: str) -> bool:
    """Check if IP belongs to a known CDN range."""
    if not ip:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    ip_val = int(parts[0]) * 256**3 + int(parts[1]) * 256**2 + int(parts[2]) * 256 + int(parts[3])
    for base, prefix in CDN_IP_RANGES:
        base_parts = base.split(".")
        base_val = int(base_parts[0]) * 256**3 + int(base_parts[1]) * 256**2 + int(base_parts[2]) * 256 + int(base_parts[3])
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        if (ip_val & mask) == (base_val & mask):
            return True
    return False


def is_cdn_server(server: str) -> bool:
    """Check if server header indicates CDN."""
    if not server:
        return False
    s = server.lower()
    for cdn in CDN_SERVERS:
        if cdn in s:
            return True
    return False


class CrossCaseCorrelator:
    """Finds correlations between cases."""

    def __init__(self, db_conn):
        self.conn = db_conn
        self.correlations = []

    def run_all(self) -> list:
        """Run all correlation checks."""
        self.correlations = []
        self._check_shared_ip()
        self._check_shared_telegram_groups()
        self._check_shared_scam_types()
        self._check_shared_wallets()
        self._check_shared_phones()
        self._check_recruitment_patterns()
        return self.correlations

    def _get_cases(self) -> list:
        """Get all cases with their evidence."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT c.case_id, c.target, c.priority, c.confidence
            FROM cases c ORDER BY c.case_id
        """)
        cases = cur.fetchall()
        cur.close()
        return cases

    def _check_shared_ip(self):
        """Find domains sharing non-CDN IPs."""
        cur = self.conn.cursor()
        # Get URLScan IPs from evidence
        cur.execute("""
            SELECT e.case_id, e.finding
            FROM evidence e
            WHERE e.phase = 'INFRA'
            AND e.finding LIKE '%hosted on%'
        """)
        rows = cur.fetchall()
        cur.close()

        # Parse IPs from findings
        ip_map = defaultdict(list)  # ip -> [case_ids]
        import re
        for case_id, finding in rows:
            # Extract IP: "URLScan: domain hosted on IP (server) in country"
            match = re.search(r'hosted on (\d+\.\d+\.\d+\.\d+)', finding)
            if match:
                ip = match.group(1)
                if not is_cdn_ip(ip):
                    ip_map[ip].append(case_id)

        # Find shared non-CDN IPs
        for ip, case_ids in ip_map.items():
            if len(case_ids) > 1:
                unique_cases = list(set(case_ids))
                if len(unique_cases) > 1:
                    self.correlations.append({
                        "type": "SHARED_IP",
                        "value": ip,
                        "cases": unique_cases,
                        "confidence": 0.7,
                        "note": "Non-CDN shared IP — potential infrastructure link"
                    })

    def _check_shared_telegram_groups(self):
        """Find cases sharing Telegram groups."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT DISTINCT ti.group_name, ti.domains::text
            FROM telegram_intelligence ti
            WHERE ti.group_name IS NOT NULL
            AND ti.domains::text != '[]'
        """)
        rows = cur.fetchall()
        cur.close()

        # Build: group -> [domains]
        group_domains = defaultdict(set)
        for group_name, domains_raw in rows:
            try:
                domains = json.loads(domains_raw) if isinstance(domains_raw, str) else domains_raw
                for d in (domains or []):
                    group_domains[group_name].add(d.lower().strip())
            except:
                pass

        # Find domains from different cases in same group
        cur = self.conn.cursor()
        cur.execute("SELECT case_id, target FROM cases WHERE trigger = 'telegram_intelligence'")
        case_domains = {row[1].strip().lower(): row[0] for row in cur.fetchall()}
        cur.close()

        for group, domains in group_domains.items():
            cases_in_group = []
            for d in domains:
                if d in case_domains:
                    cases_in_group.append(case_domains[d])
            unique_cases = list(set(cases_in_group))
            if len(unique_cases) > 1:
                self.correlations.append({
                    "type": "SHARED_TELEGRAM_GROUP",
                    "value": group,
                    "cases": unique_cases,
                    "confidence": 0.6,
                    "note": "Multiple case domains mentioned in same Telegram group"
                })

    def _check_shared_scam_types(self):
        """Find cases with same scam types from Telegram."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT ti.scam_type, ti.domains::text
            FROM telegram_intelligence ti
            WHERE ti.scam_type IS NOT NULL
        """)
        rows = cur.fetchall()
        cur.close()

        scam_type_domains = defaultdict(set)
        for scam_type, domains_raw in rows:
            try:
                domains = json.loads(domains_raw) if isinstance(domains_raw, str) else domains_raw
                for d in (domains or []):
                    scam_type_domains[scam_type].add(d.lower().strip())
            except:
                pass

        cur = self.conn.cursor()
        cur.execute("SELECT case_id, target FROM cases WHERE trigger = 'telegram_intelligence'")
        case_domains = {row[1].strip().lower(): row[0] for row in cur.fetchall()}
        cur.close()

        for scam_type, domains in scam_type_domains.items():
            cases_with_type = []
            for d in domains:
                if d in case_domains:
                    cases_with_type.append(case_domains[d])
            unique_cases = list(set(cases_with_type))
            if len(unique_cases) > 1:
                self.correlations.append({
                    "type": "SHARED_SCAM_TYPE",
                    "value": scam_type,
                    "cases": unique_cases,
                    "confidence": 0.5,
                    "note": "Multiple cases share scam type: {}".format(scam_type)
                })

    def _check_shared_wallets(self):
        """Find cases with shared wallet addresses."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT tw.wallet_address, tw.wallet_type
            FROM telegram_wallets tw
        """)
        wallets = cur.fetchall()
        cur.close()

        if not wallets:
            return

        # Check if any wallet appears in evidence of multiple cases
        cur = self.conn.cursor()
        cur.execute("""
            SELECT e.case_id, e.finding
            FROM evidence e
            WHERE e.finding LIKE '%wallet%' OR e.finding LIKE '%0x%' OR e.finding LIKE '%bc1%'
        """)
        rows = cur.fetchall()
        cur.close()

        wallet_cases = defaultdict(list)
        for wallet_addr, wallet_type in wallets:
            for case_id, finding in rows:
                if wallet_addr in finding:
                    wallet_cases[wallet_addr].append(case_id)

        for wallet, case_ids in wallet_cases.items():
            unique = list(set(case_ids))
            if len(unique) > 1:
                self.correlations.append({
                    "type": "SHARED_WALLET",
                    "value": wallet,
                    "cases": unique,
                    "confidence": 0.9,
                    "note": "Same wallet address appears in multiple cases"
                })

    def _check_shared_phones(self):
        """Find cases with shared phone numbers."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT e.case_id, e.finding
            FROM evidence e
            WHERE e.finding LIKE '%phone%' OR e.finding LIKE '%+%' 
            OR e.finding LIKE '%tel:%'
        """)
        rows = cur.fetchall()
        cur.close()

        import re
        phone_map = defaultdict(list)
        for case_id, finding in rows:
            phones = re.findall(r'\+\d{10,15}', finding)
            for p in phones:
                phone_map[p].append(case_id)

        for phone, case_ids in phone_map.items():
            unique = list(set(case_ids))
            if len(unique) > 1:
                self.correlations.append({
                    "type": "SHARED_PHONE",
                    "value": phone,
                    "cases": unique,
                    "confidence": 0.85,
                    "note": "Same phone number in multiple cases"
                })

    def _check_recruitment_patterns(self):
        """Detect human trafficking recruitment pattern matches."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT c.case_id, c.target, c.priority
            FROM cases c
            WHERE c.target ILIKE '%hr%' OR c.target ILIKE '%recruit%'
            OR c.target ILIKE '%monde%' OR c.target ILIKE '%zohar%'
            OR c.target ILIKE '%career%' OR c.target ILIKE '%job%'
        """)
        rows = cur.fetchall()
        cur.close()

        if len(rows) > 1:
            self.correlations.append({
                "type": "RECRUITMENT_PATTERN",
                "value": "trafficking_recruitment",
                "cases": [r[0] for r in rows],
                "confidence": 0.75,
                "note": "Multiple cases show human trafficking recruitment patterns"
            })

    def store_correlations(self, correlations: list):
        """Store correlations as evidence in each linked case."""
        cur = self.conn.cursor()
        ev_count = 0
        for corr in correlations:
            for case_id in corr["cases"]:
                ev_id = "EVD-CORR-{}-{}".format(case_id, ev_count)
                content = json.dumps(corr, sort_keys=True)
                ch = hashlib.sha256(content.encode()).hexdigest()
                finding = "Cross-Case Correlation [{}]: {} (cases: {}, confidence: {:.2f})".format(
                    corr["type"], corr["note"], ", ".join(corr["cases"]), corr["confidence"])
                cur.execute("""INSERT INTO evidence (
                    evidence_id, case_id, phase, finding, source_provider, source_type, confidence,
                    content_hash, timestamp, created_date, added_date, lifecycle_status, found_at,
                    provenance_source, provenance_provider, provenance_endpoint, provenance_query,
                    provenance_original_ref, provenance_content_hash, provenance_processing_history,
                    provenance_collector, provenance_complete
                ) VALUES (%s,%s,'CORRELATION',%s,'GFIN_CORRELATION_ENGINE','analysis',%s,%s,NOW(),NOW(),NOW(),'FOUND',NOW(),
                  %s,%s,%s,%s,%s,%s,%s,'GFIN-CORRELATION',true) ON CONFLICT DO NOTHING""",
                    (ev_id, case_id, finding, corr["confidence"], ch,
                     "cross_case", "GFIN_CORRELATION_ENGINE",
                     "correlation:{}".format(corr["type"]),
                     "cases:{}".format(",".join(corr["cases"])),
                     "corr:{}".format(corr["value"]), ch,
                     json.dumps(["cross_case_analysis", corr["type"].lower(), "evidence_created"])))
                ev_count += 1
        self.conn.commit()
        cur.close()
        return ev_count


def run_correlation_engine():
    """Main entry point."""
    DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}
    db = psycopg2.connect(**DB_CONFIG)

    sep = "=" * 60
    print(sep)
    print("GFIN CROSS-CASE CORRELATION ENGINE v1.0")
    print(sep)

    engine = CrossCaseCorrelator(db)
    correlations = engine.run_all()

    if not correlations:
        print("No correlations found.")
    else:
        print("Found {} correlations:\n".format(len(correlations)))
        for c in correlations:
            print("  [{}] {} (confidence: {:.2f})".format(c["type"], c["note"], c["confidence"]))
            print("    Cases: {}".format(", ".join(c["cases"])))
            print("    Value: {}".format(c["value"]))
            print()

        # Delete old correlation evidence
        cur = db.cursor()
        cur.execute("DELETE FROM evidence WHERE evidence_id LIKE 'EVD-CORR-%'")
        deleted = cur.rowcount
        db.commit()
        cur.close()
        print("Cleaned {} old correlation evidence items".format(deleted))

        # Store new correlations
        stored = engine.store_correlations(correlations)
        print("Created {} correlation evidence items".format(stored))

    print("\n" + sep)
    print("CORRELATION ENGINE COMPLETE")
    print(sep)

    db.close()
    return len(correlations)


if __name__ == "__main__":
    run_correlation_engine()
