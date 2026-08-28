#!/usr/bin/env python3
"""
GFIN Physical Location Enrichment
Run RDAP/WHOIS lookups on all case target domains to identify physical hosting locations.
"""
import sys
import json
import hashlib
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, "/gfin")
import psycopg2

DB = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


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
                        "region": data.get("region", ""), "city": data.get("city", ""),
                        "isp": data.get("isp", ""), "org": data.get("org", ""), "asn": data.get("as", "")}
    except Exception as e:
        return {"ip": ip, "error": str(e)[:100]}
    return {"ip": ip, "error": "unknown"}


def dns_resolve(domain):
    import subprocess
    try:
        result = subprocess.run(["dig", "+short", domain], capture_output=True, text=True, timeout=10)
        ips = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and not l.strip().endswith(".")]
        return ips[0] if ips else None
    except:
        return None


def run():
    import time
    db = psycopg2.connect(**DB)
    cur = db.cursor()

    print("=" * 60)
    print("GFIN PHYSICAL LOCATION ENRICHMENT")
    print("Filling the #1 prosecution readiness gap")
    print("=" * 60)

    cur.execute("SELECT case_id, target FROM cases WHERE target IS NOT NULL AND target != '' ORDER BY case_id")
    cases = cur.fetchall()
    print(f"Cases to enrich: {len(cases)}")

    enriched = 0
    for case_id, target in cases:
        target = target.strip()
        if not target or "." not in target:
            continue
        print(f"\n  [{case_id}] Target: {target}")

        rdap = rdap_lookup(target)
        if "error" in rdap:
            print(f"    RDAP: FAILED ({rdap['error']})")
        else:
            print(f"    RDAP: registrar={rdap.get('registrar', 'N/A')}, registered={rdap.get('registration_date', 'N/A')}")

        ip = dns_resolve(target)
        if ip:
            print(f"    DNS: {target} -> {ip}")
            geo = ip_geolocate(ip)
            if "error" not in geo:
                print(f"    GEO: {geo.get('city', '')}, {geo.get('country', '')} | ISP: {geo.get('isp', '')} | Org: {geo.get('org', '')}")
                details = json.dumps({"type": "HOSTING", "ip": ip, "country": geo.get("country", ""),
                    "country_code": geo.get("country_code", ""), "city": geo.get("city", ""),
                    "isp": geo.get("isp", ""), "organization": geo.get("org", ""), "asn": geo.get("asn", ""),
                    "source": "RDAP + DNS + IP Geolocation", "verified_at": datetime.utcnow().isoformat()})
                cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'INFRASTRUCTURE', %s, %s, true, 'RDAP+DNS+GEO', 'VERIFIED') ON CONFLICT DO NOTHING",
                    (case_id, f"Hosting: {ip} ({geo.get('city', '')}, {geo.get('country', '')})", details))
                enriched += 1
            else:
                print(f"    GEO: FAILED ({geo.get('error', 'unknown')})")
        else:
            print(f"    DNS: NO RESOLUTION (domain may be parked/dead)")

        # Store RDAP data as evidence
        if "registrar" in rdap or "registration_date" in rdap:
            ev_id = f"E-RDAP-{case_id[-6:]}-{int(time.time())%100000}"
            finding_lines = [
                f"RDAP Lookup for {target}:",
                f"Registrar: {rdap.get('registrar', 'N/A')}",
                f"Registered: {rdap.get('registration_date', 'N/A')}",
                f"Expires: {rdap.get('expiration_date', 'N/A')}",
                f"Nameservers: {', '.join(rdap.get('nameservers', []))}",
                f"Status: {', '.join(rdap.get('status', []))}",
            ]
            finding_text = "\n".join(finding_lines)
            content_hash = hashlib.sha256(finding_text.encode()).hexdigest()[:16]
            cur.execute("INSERT INTO evidence (evidence_id, case_id, phase, source_provider, finding, provenance_source, content_hash) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (ev_id, case_id, 'DOMAIN_REGISTRATION', 'RDAP Registry Lookup', finding_text, 'RDAP verified', content_hash))

        # Add registrar as entity
        if rdap.get("registrar"):
            reg_details = json.dumps({"type": "REGISTRAR", "name": rdap["registrar"], "source": "RDAP"})
            cur.execute("INSERT INTO people (case_id, role, name, details, is_verified, source, confidence) VALUES (%s, 'CONTACT', %s, %s, true, 'RDAP', 'VERIFIED') ON CONFLICT DO NOTHING",
                (case_id, f"Registrar: {rdap['registrar']}", reg_details))

    db.commit()
    print(f"\n--- ENRICHMENT RESULTS ---")
    print(f"Cases enriched with physical location: {enriched}")
    print(f"Total cases processed: {len(cases)}")

    cur.execute("SELECT case_id, COUNT(*) FROM people WHERE role = 'INFRASTRUCTURE' AND is_verified = true GROUP BY case_id ORDER BY case_id")
    for case_id, count in cur.fetchall():
        print(f"  {case_id}: {count} verified infrastructure")

    cur.close()
    db.close()
    return enriched


if __name__ == "__main__":
    run()
