#!/usr/bin/env python3
"""
GFIN Entity Resolution Engine v1.0
Merges duplicate identities across cases and links related entities.
"""
import sys
import json
import re
from collections import defaultdict

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def extract_social_media(text):
    """Extract social media handles from OSINT text."""
    sm = {}
    if not text:
        return sm
    for pattern, key in [
        (r'telegram\s*\(@(\w+)\)', 'telegram'),
        (r'instagram\s*\(@([\w.]+)\)', 'instagram'),
        (r'facebook\s*\(@([\w.]+)\)', 'facebook'),
        (r'twitter\s*\(@(\w+)\)', 'twitter'),
    ]:
        m = re.search(pattern, text)
        if m:
            sm[key] = "@" + m.group(1)
    em = re.search(r'Contact email:\s*([\w@.]+)', text)
    if em:
        sm["email"] = em.group(1)
    ph = re.search(r'\+\d{10,15}', text)
    if ph:
        sm["phone"] = ph.group(0)
    return sm


def run_entity_resolution():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN ENTITY RESOLUTION ENGINE v1.0")
    print("Merging identities and linking entities")
    print(sep)

    # Create resolved_entities table (all JSONB for arrays)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resolved_entities (
            id SERIAL PRIMARY KEY,
            canonical_id VARCHAR(200) UNIQUE,
            entity_type VARCHAR(50),
            primary_name TEXT,
            aliases JSONB,
            linked_cases JSONB,
            telegram_usernames JSONB,
            domains JSONB,
            social_media JSONB,
            evidence_count INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.5,
            description TEXT,
            created_date TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("TRUNCATE resolved_entities")
    db.commit()

    # ============================================================
    # 1. LINK: "Unknown operator of X" + "@username" = SAME PERSON
    # ============================================================
    print("\n--- 1. LINKING SUSPECTS TO TELEGRAM IDENTITIES ---")

    cur.execute("""
        SELECT case_id, name, details FROM people
        WHERE role = 'SUSPECT' AND name LIKE 'Unknown operator of%'
    """)
    unknown_operators = cur.fetchall()
    print("Unknown operators to resolve: {}".format(len(unknown_operators)))

    cur.execute("""
        SELECT case_id, name, details FROM people
        WHERE source = 'TELEGRAM_INTELLIGENCE' AND entity_type = 'PSEUDONYMOUS'
    """)
    telegram_users = cur.fetchall()

    cur.execute("""
        SELECT case_id, name, details FROM people
        WHERE role = 'SUSPECT' AND entity_type = 'ORGANIZATION'
    """)
    org_suspects = cur.fetchall()

    resolved_count = 0
    for case_id, op_name, op_details in unknown_operators:
        domain = op_name.replace("Unknown operator of ", "").strip()

        # Find matching Telegram user in same case
        tg_match = None
        for tg_case, tg_name, tg_details in telegram_users:
            if tg_case == case_id and domain.lower() in (tg_details or "").lower():
                tg_match = (tg_name, tg_details)
                break

        if tg_match:
            tg_username, tg_details = tg_match
            canonical_id = "ENT-{}-{}".format(case_id, domain.replace(".", "-").upper()[:15])
            social_media = extract_social_media(op_details)

            cur.execute("""INSERT INTO resolved_entities
                (canonical_id, entity_type, primary_name, aliases, linked_cases,
                 telegram_usernames, domains, social_media, evidence_count, confidence, description)
                VALUES (%s, 'SUSPECT', %s, %s, %s, %s, %s, %s, 2, 0.9, %s)
                ON CONFLICT (canonical_id) DO NOTHING""",
                (canonical_id, tg_username,
                 json.dumps([op_name]),
                 json.dumps([case_id]),
                 json.dumps([tg_username]),
                 json.dumps([domain]),
                 json.dumps(social_media),
                 "RESOLVED: Website operator ({}) linked to Telegram recruiter ({}) promoting same domain.".format(domain, tg_username)))

            print("  RESOLVED: {} -> {} [{}]".format(domain, tg_username, case_id))
            if social_media:
                print("    Social media: {}".format(social_media))
            resolved_count += 1
        else:
            canonical_id = "ENT-{}-{}".format(case_id, domain.replace(".", "-").upper()[:15])
            social_media = extract_social_media(op_details)

            cur.execute("""INSERT INTO resolved_entities
                (canonical_id, entity_type, primary_name, aliases, linked_cases,
                 telegram_usernames, domains, social_media, evidence_count, confidence, description)
                VALUES (%s, 'SUSPECT', %s, %s, %s, %s, %s, %s, 1, 0.5, %s)
                ON CONFLICT (canonical_id) DO NOTHING""",
                (canonical_id, op_name,
                 json.dumps([]),
                 json.dumps([case_id]),
                 json.dumps([]),
                 json.dumps([domain]),
                 json.dumps(social_media),
                 "UNRESOLVED: Website operator identity unknown. Real name requires legal process."))

            if social_media:
                print("  PARTIAL: {} has social media: {}".format(domain, social_media))

    # ============================================================
    # 2. RESOLVE: Organization suspects with social media
    # ============================================================
    print("\n--- 2. RESOLVING ORGANIZATION SUSPECTS ---")

    for case_id, org_name, org_details in org_suspects:
        cur.execute("SELECT 1 FROM resolved_entities WHERE primary_name = %s AND linked_cases @> %s::jsonb",
                    (org_name, json.dumps([case_id])))
        if cur.fetchone():
            continue

        social_media = extract_social_media(org_details)
        domain = ""
        dm = re.search(r'Website operator of ([\w.]+)', org_details or "")
        if dm:
            domain = dm.group(1)

        canonical_id = "ENT-{}-{}".format(case_id, org_name.replace(" ", "").upper()[:15])
        cur.execute("""INSERT INTO resolved_entities
            (canonical_id, entity_type, primary_name, aliases, linked_cases,
             telegram_usernames, domains, social_media, evidence_count, confidence, description)
            VALUES (%s, 'SUSPECT', %s, %s, %s, %s, %s, %s, 1, 0.7, %s)
            ON CONFLICT (canonical_id) DO NOTHING""",
            (canonical_id, org_name,
             json.dumps([]), json.dumps([case_id]),
             json.dumps([social_media.get("telegram", "")] if social_media.get("telegram") else []),
             json.dumps([domain] if domain else []),
             json.dumps(social_media),
             "ORGANIZATION: Named entity with OSINT social media presence."))

        print("  ORG: {} [{}] social={}".format(org_name, case_id, social_media))
        resolved_count += 1

    # ============================================================
    # 3. MERGE: Cross-case entity linking via correlation graph
    # ============================================================
    print("\n--- 3. CROSS-CASE ENTITY MERGING ---")

    cur.execute("""
        SELECT source_case, target_case, entity_value
        FROM correlation_graph
        WHERE correlation_type = 'SHARED_INFRASTRUCTURE'
        AND entity_value != 'Telegram (Meta/FBI Legal)'
    """)
    infra_links = cur.fetchall()
    print("Infrastructure links to merge: {}".format(len(infra_links)))

    infra_groups = defaultdict(set)
    for src, tgt, entity in infra_links:
        infra_groups[entity].add(src)
        infra_groups[entity].add(tgt)

    for entity, all_cases in infra_groups.items():
        if len(all_cases) >= 2:
            canonical_id = "ENT-INFRA-{}".format(entity.replace(" ", "").replace(".", "").upper()[:20])
            cur.execute("""INSERT INTO resolved_entities
                (canonical_id, entity_type, primary_name, aliases, linked_cases,
                 telegram_usernames, domains, social_media, evidence_count, confidence, description)
                VALUES (%s, 'INFRASTRUCTURE', %s, %s, %s, %s, %s, %s, %s, 0.95, %s)
                ON CONFLICT (canonical_id) DO NOTHING""",
                (canonical_id, entity,
                 json.dumps([]),
                 json.dumps(sorted(list(all_cases))),
                 json.dumps([]), json.dumps([]), json.dumps({}),
                 len(all_cases),
                 "SHARED across {} cases: {} linking multiple operations.".format(len(all_cases), entity)))

            print("  INFRA: {} shared by {} cases: {}".format(
                entity, len(all_cases), ", ".join(sorted(list(all_cases)))))

    # ============================================================
    # 4. CROSS-CASE TELEGRAM NETWORK
    # ============================================================
    print("\n--- 4. TELEGRAM RECRUITMENT NETWORK ---")

    cur.execute("""
        SELECT canonical_id, primary_name, linked_cases, telegram_usernames
        FROM resolved_entities
        WHERE entity_type = 'SUSPECT' AND telegram_usernames::text != '[]'
    """)
    tg_suspects = cur.fetchall()
    print("Telegram-linked suspects: {}".format(len(tg_suspects)))

    network_links = 0
    for i in range(len(tg_suspects)):
        for j in range(i + 1, len(tg_suspects)):
            ci_cases = json.loads(tg_suspects[i][2]) if isinstance(tg_suspects[i][2], str) else tg_suspects[i][2]
            cj_cases = json.loads(tg_suspects[j][2]) if isinstance(tg_suspects[j][2], str) else tg_suspects[j][2]
            for case_i in ci_cases:
                for case_j in cj_cases:
                    cur.execute("""SELECT 1 FROM correlation_graph
                        WHERE (source_case = %s AND target_case = %s)
                        OR (source_case = %s AND target_case = %s)""",
                        (case_i, case_j, case_j, case_i))
                    if cur.fetchone():
                        network_links += 1
                        break

    print("Network links between Telegram suspects: {}".format(network_links))

    db.commit()

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("ENTITY RESOLUTION COMPLETE")
    print(sep)

    cur.execute("SELECT COUNT(*) FROM resolved_entities")
    total = cur.fetchone()[0]
    print("Total resolved entities: {}".format(total))

    cur.execute("SELECT entity_type, COUNT(*) FROM resolved_entities GROUP BY entity_type")
    for etype, count in cur.fetchall():
        print("  {}: {}".format(etype, count))

    cur.execute("SELECT COUNT(*) FROM resolved_entities WHERE confidence >= 0.9")
    high = cur.fetchone()[0]
    print("High confidence (>=0.9): {}".format(high))

    cur.execute("""SELECT canonical_id, primary_name, confidence,
        telegram_usernames::text, social_media::text, linked_cases::text
        FROM resolved_entities WHERE confidence >= 0.9 ORDER BY confidence DESC""")
    print("\nResolved identities:")
    for cid, name, conf, tg, sm, cases in cur.fetchall():
        print("  [{}] {} (conf={:.2f})".format(cid, name, conf))
        if tg and tg != "[]":
            print("    Telegram: {}".format(tg))
        if sm and sm != "{}":
            print("    Social: {}".format(sm))
        print("    Cases: {}".format(cases))

    cur.close()
    db.close()
    return total


if __name__ == "__main__":
    run_entity_resolution()
