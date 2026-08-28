#!/usr/bin/env python3
"""
GFIN Entity Enrichment Engine v1.0
Extracts additional entity types from existing evidence to fill gap analysis coverage.

Current problem: Most cases only have SUSPECT + INFRASTRUCTURE (2 types).
Need 4+ types for prosecution: DOMAIN, WALLET, PHONE, EMAIL, SUSPECT, INFRASTRUCTURE, VICTIM.
"""
import sys
import re
import json
from datetime import datetime

sys.path.insert(0, "/gfin")
import psycopg2

DB = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

# Entity extraction patterns
PATTERNS = {
    "WALLET": [
        (r'(?:bc1[a-z0-9]{39,59})', "BTC (Bech32)"),
        (r'(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34})', "BTC (Legacy)"),
        (r'(?:0x[a-fA-F0-9]{40})', "ETH/EVM"),
        (r'(?:T[A-Za-z1-9]{33})', "TRON"),
    ],
    "IP": [
        (r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', "IP Address"),
    ],
    "EMAIL": [
        (r'[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}', "Email"),
    ],
    "PHONE": [
        (r'\+\d{6,15}', "Phone"),
    ],
    "DOMAIN": [
        (r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|net|org|io|co|me|app|xyz|info|biz|ru|su|tk|cc|ws|au|uk|de|fr|it|nl|pl|se|no|fi|dk|tr|gr|cy|mt|ee|lv|lt))\b', "Domain"),
    ],
}


def extract_entities(text):
    """Extract all entity types from text."""
    if not text:
        return []
    found = []
    for entity_type, patterns in PATTERNS.items():
        for pattern, description in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                # Skip common false positives
                if entity_type == "IP" and (m.startswith("0.") or m.startswith("127.") or m == "0.0.0.0"):
                    continue
                if entity_type == "DOMAIN" and m in ("example.com", "localhost"):
                    continue
                found.append({"type": entity_type, "value": m, "description": description})
    # Deduplicate
    seen = set()
    unique = []
    for e in found:
        key = (e["type"], e["value"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def enrich_case(case_id, cur):
    """Extract entities from all evidence for a case and insert as people entries."""
    added = 0

    # Get all evidence findings for this case
    cur.execute("SELECT evidence_id, finding, phase, content_hash FROM evidence WHERE case_id = %s", (case_id,))
    evidence_items = cur.fetchall()

    # Get existing entities to avoid duplicates
    cur.execute("SELECT role, details FROM people WHERE case_id = %s", (case_id,))
    existing = set()
    for role, details in cur.fetchall():
        if details:
            try:
                d = json.loads(details) if isinstance(details, str) else details
                if "value" in d:
                    existing.add((role, d["value"]))
                elif "name" in d:
                    existing.add((role, d["name"]))
            except:
                pass

    # Also check telegram intel for this case
    cur.execute("SELECT target FROM cases WHERE case_id = %s", (case_id,))
    target = (cur.fetchone() or [""])[0]

    cur.execute("""
        SELECT wallets::text, phones::text, usernames::text, domains::text
        FROM telegram_intelligence
        WHERE domains::text ILIKE %s OR message_text ILIKE %s
    """, (f"%{target}%", f"%{target}%"))
    tg_data = cur.fetchall()

    # Extract from evidence findings
    for ev_id, finding, phase, ch in evidence_items:
        entities = extract_entities(finding)
        for e in entities:
            entity_key = (e["type"], e["value"])
            if entity_key in existing:
                continue

            # Map entity type to role
            entity_role_map = {
                "WALLET": "WALLET",
                "IP": "INFRASTRUCTURE",
                "EMAIL": "CONTACT",
                "PHONE": "CONTACT",
                "DOMAIN": "DOMAIN",
            }
            role = entity_role_map.get(e["type"], "ENTITY")

            # Insert as people entry
            details = json.dumps({
                "type": e["type"],
                "value": e["value"],
                "source": f"Evidence {ev_id}",
                "phase": phase or "Unknown",
                "description": e["description"],
            })

            cur.execute("""INSERT INTO people (case_id, role, name, details, created_date)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING""",
                (case_id, role, e["value"][:100], details))
            existing.add(entity_key)
            added += 1

    # Extract from Telegram intelligence
    for wallets, phones, usernames, domains in tg_data:
        for field, role, type_name in [
            (wallets, "WALLET", "WALLET"),
            (phones, "CONTACT", "PHONE"),
            (usernames, "SOCIAL", "TELEGRAM_ACCOUNT"),
            (domains, "DOMAIN", "DOMAIN"),
        ]:
            if not field:
                continue
            try:
                items = json.loads(field) if isinstance(field, str) else field
            except:
                continue
            if not isinstance(items, list):
                continue
            for item in items:
                if not item or not isinstance(item, str):
                    continue
                entity_key = (type_name, item)
                if entity_key in existing:
                    continue
                details = json.dumps({"type": type_name, "value": item, "source": "Telegram Intelligence"})
                cur.execute("""INSERT INTO people (case_id, role, name, details, created_date)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING""",
                    (case_id, role_map(role), item[:100], details))
                existing.add(entity_key)
                added += 1

    # Add VICTIM entities from complaints
    cur.execute("SELECT reference_number, scam_type FROM victim_complaints WHERE case_id = %s", (case_id,))
    for ref, scam_type in cur.fetchall():
        entity_key = ("VICTIM", ref)
        if entity_key in existing:
            continue
        details = json.dumps({"type": "VICTIM", "value": ref, "scam_type": scam_type or "Unknown", "source": "Victim Portal"})
        cur.execute("""INSERT INTO people (case_id, role, name, details, created_date)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING""",
            (case_id, "VICTIM", ref[:100], details))
        existing.add(entity_key)
        added += 1

    return added


def role_map(role):
    """Map role to proper entity role."""
    mapping = {
        "WALLET": "WALLET",
        "CONTACT": "CONTACT",
        "SOCIAL": "SOCIAL",
        "DOMAIN": "DOMAIN",
        "VICTIM": "VICTIM",
    }
    return mapping.get(role, role)


def run():
    db = psycopg2.connect(**DB)
    cur = db.cursor()

    print("=" * 60)
    print("GFIN ENTITY ENRICHMENT ENGINE v1.0")
    print("Extracting entities from evidence to fill coverage gaps")
    print("=" * 60)

    # Get all cases
    cur.execute("SELECT case_id, target FROM cases ORDER BY case_id")
    cases = cur.fetchall()
    print(f"Cases to enrich: {len(cases)}")

    total_added = 0
    for case_id, target in cases:
        added = enrich_case(case_id, cur)
        total_added += added
        if added > 0:
            print(f"  {case_id}: +{added} entities")

    db.commit()

    # Show updated entity coverage
    print(f"\n--- ENTITY COVERAGE AFTER ENRICHMENT ---")
    cur.execute("SELECT case_id, role, COUNT(*) FROM people GROUP BY case_id, role ORDER BY case_id, role")
    results = cur.fetchall()
    case_roles = {}
    for case_id, role, count in results:
        if case_id not in case_roles:
            case_roles[case_id] = set()
        case_roles[case_id].add(role)

    print(f"\nEntity type coverage per case:")
    for case_id in sorted(case_roles.keys()):
        roles = case_roles[case_id]
        print(f"  {case_id}: {len(roles)} types — {', '.join(sorted(roles))}")

    # Show improvement
    four_plus = sum(1 for roles in case_roles.values() if len(roles) >= 4)
    two_only = sum(1 for roles in case_roles.values() if len(roles) < 4)
    print(f"\n4+ entity types: {four_plus} cases (was ~0 before enrichment)")
    print(f"Still <4 types: {two_only} cases")
    print(f"\nTotal entities added: {total_added}")

    print("\n" + "=" * 60)
    print("ENTITY ENRICHMENT COMPLETE")
    print("=" * 60)

    cur.close()
    db.close()
    return total_added


if __name__ == "__main__":
    run()
