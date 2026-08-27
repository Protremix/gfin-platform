#!/usr/bin/env python3
"""Batch investigate all uninvestigated Telegram domains via Hunter Playbook."""
import psycopg2, json, urllib.request, urllib.parse, ssl, time, sys

def get_db():
    return psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="", port=5432)

def investigate_domain(domain):
    params = urllib.parse.urlencode({
        "identifier": domain,
        "identifier_type": "DOMAIN",
        "trigger": "TELEGRAM_INTEL",
        "trigger_reason": f"Batch investigation of Telegram-detected domain",
        "operator": "GFIN_SPY",
    })
    url = f"https://gfin-system.com/api/playbook/investigate?{params}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    resp = urllib.request.urlopen(url, timeout=45, context=ctx)
    return json.loads(resp.read())

# Fake domain patterns to skip (like "1.serbia", "2.greece", etc.)
import re
def is_real_domain(domain):
    # Skip numbered country patterns
    if re.match(r'^\d+\.', domain):
        return False
    # Skip common false positives
    fake = {"authorize.net", "crypto.com", "id.me", "pm.me", "wa.link", "services.all", "erica.chan"}
    if domain in fake:
        return False
    # Must have at least one dot and valid TLD
    parts = domain.split(".")
    if len(parts) < 2:
        return False
    if len(parts[-1]) < 2:
        return False
    return True

conn = get_db()
cur = conn.cursor()
cur.execute("SELECT domain, first_seen_group, first_seen_sender, mention_count FROM telegram_domains WHERE investigated = FALSE ORDER BY mention_count DESC")
rows = cur.fetchall()
conn.close()

print(f"Found {len(rows)} uninvestigated domains")
real_domains = [(r[0], r[1], r[2], r[3]) for r in rows if is_real_domain(r[0])]
print(f"Real domains to investigate: {len(real_domains)}")
for d in real_domains:
    print(f"  {d[0]} (mentions: {d[3]}, from: {d[1]})")

print()
for i, (domain, group, sender, mentions) in enumerate(real_domains):
    print(f"[{i+1}/{len(real_domains)}] Investigating {domain}...")
    try:
        result = investigate_domain(domain)
        if result:
            confidence = result.get("confidence", 0)
            accusation = result.get("accusation_level", "UNKNOWN")
            locations = result.get("physical_locations", [])
            evidence_count = len(result.get("evidence_chain", []))
            
            risk = "CRITICAL" if confidence > 0.7 else "HIGH" if confidence > 0.4 else "MEDIUM" if confidence > 0.2 else "LOW"
            
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE telegram_domains 
                SET investigated = TRUE, scam_detected = %s, risk_level = %s
                WHERE domain = %s
            """, (confidence > 0.5, risk, domain))
            conn.commit()
            conn.close()
            
            print(f"  -> confidence={confidence}, accusation={accusation}, risk={risk}")
            print(f"     evidence_steps={evidence_count}, locations={len(locations)}")
            for loc in locations[:2]:
                city = loc.get("city", "?")
                country = loc.get("country", "?")
                print(f"     LOCATION: {city}, {country}")
        else:
            print(f"  -> No result")
    except Exception as e:
        print(f"  -> Error: {e}")
    
    time.sleep(1)  # Be gentle

print("\nBatch investigation complete")
