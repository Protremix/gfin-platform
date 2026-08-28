#!/usr/bin/env python3
"""
GFIN Evidence Wallet Extraction + OSINT for weak cases.

1. Scan ALL evidence findings for crypto wallet addresses
2. Create WALLET entities for any found
3. Run OSINT (RDAP + DNS + Geo) on aurum.foundation and gothix.online
4. Search Telegram intel for @Karl_Fx
"""
import sys
import json
import re
import hashlib
import urllib.request
from datetime import datetime

sys.path.insert(0, "/gfin")
import psycopg2

DB = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

# Wallet regex patterns
WALLET_PATTERNS = {
    "BTC": [
        r'\b(bc1[a-z0-9]{39,59})\b',  # Bech32
        r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b',  # Legacy/P2SH
    ],
    "ETH": [
        r'\b(0x[a-fA-F0-9]{40})\b',
    ],
    "TRON": [
        r'\b(T[A-Za-z1-9]{33})\b',
    ],
    "XRP": [
        r'\b(r[a-zA-Z0-9]{24,34})\b',
    ],
    "SOLANA": [
        r'\b([1-9A-HJ-NP-Za-km-z]{32,44})\b',  # Base58, but very broad - only use if explicitly mentioned as solana
    ],
}


def extract_wallets_from_text(text):
    """Extract all wallet addresses from text."""
    if not text:
        return []
    wallets = []
    for wtype, patterns in WALLET_PATTERNS.items():
        if wtype == "SOLANA":
            continue  # Too broad, skip
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for addr in matches:
                # Filter out very short matches that are likely not wallets
                if wtype == "BTC" and len(addr) < 26:
                    continue
                if wtype == "TRON" and len(addr) != 34:
                    continue
                wallets.append({"type": wtype, "address": addr})
    # Deduplicate
    seen = set()
    unique = []
    for w in wallets:
        key = f"{w['type']}:{w['address']}"
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def run_wallet_extraction():
    """Scan all evidence for wallet addresses and create entities."""
    db = psycopg2.connect(**DB)
    cur = db.cursor()

    print("=" * 60)
    print("WALLET EXTRACTION FROM EVIDENCE")
    print("=" * 60)

    cur.execute("SELECT evidence_id, case_id, finding FROM evidence")
    all_evidence = cur.fetchall()
    print(f"Evidence items to scan: {len(all_evidence)}")

    wallets_found = {}  # (type, address) -> {cases: set, evidence: list}

    for ev_id, case_id, finding in all_evidence:
        wallets = extract_wallets_from_text(finding)
        for w in wallets:
            key = f"{w['type']}:{w['address']}"
            if key not in wallets_found:
                wallets_found[key] = {"type": w["type"], "address": w["address"], "cases": set(), "evidence": []}
            wallets_found[key]["cases"].add(case_id)
            wallets_found[key]["evidence"].append(ev_id)

    # Also scan Telegram intelligence
    cur.execute("SELECT id, wallets::text, scam_type FROM telegram_intelligence WHERE wallets::text != '[]' AND wallets::text != 'null'")
    tg_rows = cur.fetchall()
    for tg_id, wallets_json, scam_type in tg_rows:
        try:
            wallets_data = json.loads(wallets_json) if isinstance(wallets_json, str) else wallets_json
            if isinstance(wallets_data, list):
                for w in wallets_data:
                    if isinstance(w, dict):
                        addr = w.get("address", "")
                        wtype = w.get("type", "")
                        if addr and wtype:
                            key = f"{wtype}:{addr}"
                            if key not in wallets_found:
                                wallets_found[key] = {"type": wtype, "address": addr, "cases": set(), "evidence": []}
            elif isinstance(wallets_data, str):
                wallets = extract_wallets_from_text(wallets_data)
                for w in wallets:
                    key = f"{w['type']}:{w['address']}"
                    if key not in wallets_found:
                        wallets_found[key] = {"type": w["type"], "address": w["address"], "cases": set(), "evidence": []}
        except:
            continue

    # Also scan scam_websites table
    cur.execute("SELECT domain, wallet_addresses::text FROM scam_websites WHERE wallet_addresses::text != '[]' AND wallet_addresses::text != 'null'")
    sw_rows = cur.fetchall()
    for domain, wallets_json in sw_rows:
        try:
            wallets_data = json.loads(wallets_json) if isinstance(wallets_json, str) else wallets_json
            if isinstance(wallets_data, list):
                for w in wallets_data:
                    if isinstance(w, str):
                        wallets = extract_wallets_from_text(w)
                        for wl in wallets:
                            key = f"{wl['type']}:{wl['address']}"
                            if key not in wallets_found:
                                wallets_found[key] = {"type": wl["type"], "address": wl["address"], "cases": set(), "evidence": []}
        except:
            continue

    print(f"Unique wallets found: {len(wallets_found)}")

    # Also scan people table details for wallet addresses
    cur.execute("SELECT name, details::text, case_id FROM people")
    people_rows = cur.fetchall()
    for name, details, case_id in people_rows:
        wallets = extract_wallets_from_text(name)
        wallets.extend(extract_wallets_from_text(details))
        for w in wallets:
            key = f"{w['type']}:{w['address']}"
            if key not in wallets_found:
                wallets_found[key] = {"type": w["type"], "address": w["address"], "cases": set([case_id]), "evidence": []}

    print(f"Total unique wallets after full scan: {len(wallets_found)}")

    # Create WALLET entities
    created = 0
    for key, info in wallets_found.items():
        addr = info["address"]
        wtype = info["type"]
        cases = info["cases"]

        details = json.dumps({
            "type": wtype,
            "address": addr,
            "source": "Evidence text extraction",
            "found_in_evidence": len(info["evidence"]),
            "extracted_at": datetime.utcnow().isoformat(),
        })

        for case_id in cases:
            cur.execute("SELECT 1 FROM people WHERE case_id = %s AND name = %s AND role = 'WALLET'", (case_id, addr))
            if not cur.fetchone():
                cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'WALLET', %s, %s, true, 'Evidence extraction', 'VERIFIED')",
                    (case_id, addr, details))
                created += 1

        # If wallet found but no specific case, link to first case with evidence
        if not cases and info["evidence"]:
            cur.execute("SELECT case_id FROM evidence WHERE evidence_id = %s", (info["evidence"][0],))
            case_row = cur.fetchone()
            if case_row:
                cur.execute("SELECT 1 FROM people WHERE case_id = %s AND name = %s AND role = 'WALLET'", (case_row[0], addr))
                if not cur.fetchone():
                    cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'WALLET', %s, %s, true, 'Evidence extraction', 'VERIFIED')",
                        (case_row[0], addr, details))
                    created += 1

        print(f"  {wtype} {addr[:20]}... -> cases: {','.join(cases) or 'via evidence'}")

    db.commit()
    print(f"\nWallet entities created: {created}")
    cur.close()
    db.close()
    return created, wallets_found


def rdap_lookup(domain):
    try:
        url = f"https://rdap.org/domain/{domain}"
        req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0", "Accept": "application/rdap+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        registrar = ""
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                vcard = entity.get("vcardArray", [None])[1] if len(entity.get("vcardArray", [])) > 1 else []
                for entry in vcard:
                    if entry[0] == "fn":
                        registrar = entry[3]
        reg_date = exp_date = None
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                reg_date = ev.get("eventDate", "")[:10]
            elif ev.get("eventAction") == "expiration":
                exp_date = ev.get("eventDate", "")[:10]
        nameservers = [ns.get("ldhName", "") for ns in data.get("nameservers", [])]
        status = data.get("status", [])
        return {"registrar": registrar, "registration_date": reg_date, "expiration_date": exp_date, "nameservers": nameservers, "status": status}
    except Exception as e:
        return {"error": str(e)[:100]}


def ip_geolocate(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,city,isp,org,as,query"
        req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                return {"ip": ip, "country": data.get("country", ""), "country_code": data.get("countryCode", ""),
                        "city": data.get("city", ""), "isp": data.get("isp", ""), "org": data.get("org", ""), "asn": data.get("as", "")}
    except:
        pass
    return None


def dns_resolve(domain):
    import subprocess
    try:
        result = subprocess.run(["dig", "+short", domain], capture_output=True, text=True, timeout=10)
        ips = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and not l.strip().endswith(".")]
        return ips[0] if ips else None
    except:
        return None


def urlscan_lookup(domain):
    """Query URLScan.io for domain scan results."""
    try:
        url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=5"
        req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for result in data.get("results", [])[:5]:
            page = result.get("page", {})
            results.append({
                "url": page.get("url", ""),
                "ip": page.get("ip", ""),
                "server": page.get("server", ""),
                "title": page.get("title", ""),
                "status": page.get("status", 0),
                "scan_date": result.get("task", {}).get("time", ""),
            })
        return results
    except:
        return []


def run_osint_for_case(case_id, domain, cur, db):
    """Run full OSINT investigation for a case."""
    import time
    print(f"\n  [{case_id}] OSINT on: {domain}")

    evidence_items = []

    # 1. RDAP
    rdap = rdap_lookup(domain)
    if "error" not in rdap:
        ev_id = f"E-RDAP-{case_id[-6:]}-{int(time.time())%100000}"
        finding = "\n".join([
            f"RDAP Lookup for {domain}:",
            f"Registrar: {rdap.get('registrar', 'N/A')}",
            f"Registered: {rdap.get('registration_date', 'N/A')}",
            f"Expires: {rdap.get('expiration_date', 'N/A')}",
            f"Nameservers: {', '.join(rdap.get('nameservers', []))}",
            f"Status: {', '.join(rdap.get('status', []))}",
        ])
        content_hash = hashlib.sha256(finding.encode()).hexdigest()[:16]
        cur.execute("INSERT INTO evidence (evidence_id, case_id, phase, source_provider, finding, provenance_source, content_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (ev_id, case_id, 'DOMAIN_REGISTRATION', 'RDAP Registry', finding, 'RDAP verified', content_hash))
        evidence_items.append(("DOMAIN_REGISTRATION", finding))
        print(f"    RDAP: {rdap.get('registrar', 'N/A')}, registered {rdap.get('registration_date', 'N/A')}")

        # Add registrar entity
        if rdap.get("registrar"):
            cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'CONTACT', %s, %s, true, 'RDAP', 'VERIFIED') ON CONFLICT DO NOTHING",
                (case_id, f"Registrar: {rdap['registrar']}", json.dumps({"type": "REGISTRAR", "name": rdap["registrar"]})))
    else:
        print(f"    RDAP: FAILED")

    # 2. DNS + Geo
    ip = dns_resolve(domain)
    if ip:
        geo = ip_geolocate(ip)
        if geo:
            print(f"    GEO: {geo.get('city', '')}, {geo.get('country', '')} | ISP: {geo.get('isp', '')}")
            ev_id = f"E-GEO-{case_id[-6:]}-{int(time.time())%100000}"
            finding = f"DNS Resolution: {domain} -> {ip}\nGeolocation: {geo.get('city', '')}, {geo.get('country', '')} ({geo.get('country_code', '')})\nISP: {geo.get('isp', '')}\nOrganization: {geo.get('org', '')}\nASN: {geo.get('asn', '')}"
            content_hash = hashlib.sha256(finding.encode()).hexdigest()[:16]
            cur.execute("INSERT INTO evidence (evidence_id, case_id, phase, source_provider, finding, provenance_source, content_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (ev_id, case_id, 'INFRASTRUCTURE', 'DNS + IP Geolocation', finding, 'DNS+GEO verified', content_hash))
            evidence_items.append(("INFRASTRUCTURE", finding))

            cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'INFRASTRUCTURE', %s, %s, true, 'DNS+GEO', 'VERIFIED') ON CONFLICT DO NOTHING",
                (case_id, f"Hosting: {ip} ({geo.get('city', '')}, {geo.get('country', '')})", json.dumps({"type": "HOSTING", "ip": ip, "country": geo.get("country", ""), "city": geo.get("city", ""), "isp": geo.get("isp", "")})))
        else:
            print(f"    GEO: FAILED")
    else:
        print(f"    DNS: NO RESOLUTION")

    # 3. URLScan
    scans = urlscan_lookup(domain)
    if scans:
        print(f"    URLScan: {len(scans)} results")
        for scan in scans[:3]:
            ev_id = f"E-USCAN-{case_id[-6:]}-{int(time.time())%100000}-{scan.get('scan_date', '')[-5:]}"
            finding = f"URLScan.io Result:\nURL: {scan.get('url', '')}\nIP: {scan.get('ip', '')}\nServer: {scan.get('server', '')}\nPage Title: {scan.get('title', '')}\nHTTP Status: {scan.get('status', 0)}\nScan Date: {scan.get('scan_date', '')}"
            content_hash = hashlib.sha256(finding.encode()).hexdigest()[:16]
            cur.execute("INSERT INTO evidence (evidence_id, case_id, phase, source_provider, finding, provenance_source, content_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (ev_id, case_id, 'WEB_SCAN', 'URLScan.io', finding, 'URLScan public API', content_hash))
            evidence_items.append(("WEB_SCAN", finding))
    else:
        print(f"    URLScan: No results")

    # 4. Add investigation steps
    for phase, _ in evidence_items:
        cur.execute("INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, result, officer_name, order_num) VALUES (%s, %s, %s, %s, %s, %s, %s, 99) ON CONFLICT DO NOTHING",
            (case_id, phase, phase + " OSINT", "OSINT", "COMPLETED", json.dumps({"finding": finding[:500], "source": "GFIN-OSINT-AUTO"}), "GFIN-OSINT-AUTO"))
    db.commit()
    return len(evidence_items)


def search_telegram_user(username, cur, db):
    """Search Telegram intelligence for a specific user."""
    print(f"\n  Telegram search for: {username}")
    # Clean the username
    clean = username.lstrip("@")
    cur.execute("SELECT id, message_text, scam_type, wallets::text, phones::text, domains::text, group_name FROM telegram_intelligence WHERE message_text ILIKE %s OR domains::text ILIKE %s ORDER BY id LIMIT 20",
        (f"%{clean}%", f"%{clean}%"))
    rows = cur.fetchall()
    print(f"    Found {len(rows)} Telegram messages mentioning {username}")
    return rows


def run():
    db = psycopg2.connect(**DB)
    cur = db.cursor()

    # 1. Wallet extraction
    wallet_count, wallets = run_wallet_extraction()

    # 2. OSINT on zero-evidence cases
    print("\n" + "=" * 60)
    print("OSINT INVESTIGATION FOR WEAK CASES")
    print("=" * 60)

    # Extract domains from URL targets
    weak_cases = [
        ("GFIN-CASE-208DA2", "aurum.foundation"),
        ("GFIN-CASE-763EA3", "gothix.online"),
    ]

    total_ev = 0
    for case_id, domain in weak_cases:
        total_ev += run_osint_for_case(case_id, domain, cur, db)

    # 3. Telegram search for @Karl_Fx
    print("\n--- TELEGRAM INTEL: @Karl_Fx ---")
    tg_messages = search_telegram_user("Karl_Fx", cur, db)
    if tg_messages:
        for msg_id, text, scam_type, wallets, phones, domains, group_name in tg_messages[:5]:
            print(f"  [{msg_id}] {group_name}: {scam_type}")
            print(f"    Text: {(text or '')[:80]}...")

            # Create evidence from Telegram intel
            ev_id = f"E-TG-LAUDR002-{msg_id}"
            finding = f"Telegram Intelligence (Group: {group_name}):\nMessage: {text}\nScam Type: {scam_type}\nWallets: {wallets}\nDomains: {domains}\nPhones: {phones}"
            content_hash = hashlib.sha256(finding.encode()).hexdigest()[:16]
            cur.execute("INSERT INTO evidence (evidence_id, case_id, phase, source_provider, finding, provenance_source, content_hash) VALUES (%s, 'GFIN-LAUDR-002', 'INTEL_CONTEXT', 'Telegram Intelligence', %s, 'Telegram monitoring', %s) ON CONFLICT DO NOTHING",
                (ev_id, finding, content_hash))
            total_ev += 1
        db.commit()

    # 4. Summary
    print(f"\n{'=' * 60}")
    print("ENRICHMENT COMPLETE")
    print(f"{'=' * 60}")
    print(f"Wallet entities created: {wallet_count}")
    print(f"Evidence items added: {total_ev}")

    # Show updated evidence counts
    cur.execute("SELECT case_id, COUNT(*) FROM evidence GROUP BY case_id ORDER BY COUNT(*) DESC")
    print("\nEvidence per case:")
    for case_id, count in cur.fetchall():
        print(f"  {case_id}: {count}")

    # Show wallet entities
    cur.execute("SELECT case_id, name FROM people WHERE role = 'WALLET' ORDER BY case_id")
    wallet_entities = cur.fetchall()
    print(f"\nWallet entities: {len(wallet_entities)}")
    for case_id, name in wallet_entities:
        print(f"  {case_id}: {name[:30]}")

    cur.close()
    db.close()


if __name__ == "__main__":
    run()
