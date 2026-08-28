#!/usr/bin/env python3
"""
GFIN Cross-Case Correlation Engine v1.0
Finds hidden links between cases that a human investigator would miss.

Links detected:
1. SHARED INFRASTRUCTURE - same registrar, hosting provider, CDN
2. SHARED TELEGRAM PRESENCE - same groups, same usernames mentioned across cases
3. SHARED ENTITIES - same domains, wallets, phones appearing in multiple cases
4. SHARED PATTERNS - same scam type, same recruitment language, same targeting
5. INFRASTRUCTURE CHAIN - same registrar + same hosting = likely same operator

Output: correlation_graph table + alerts for high-confidence links
"""
import sys
import json
import re
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def run_correlation_engine():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN CROSS-CASE CORRELATION ENGINE v1.0")
    print("Finding hidden links between cases")
    print(sep)

    # Create correlation_graph table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS correlation_graph (
            id SERIAL PRIMARY KEY,
            source_case VARCHAR(100),
            target_case VARCHAR(100),
            correlation_type VARCHAR(100),
            entity_value TEXT,
            entity_type VARCHAR(50),
            confidence REAL,
            description TEXT,
            created_date TIMESTAMP DEFAULT NOW()
        )
    """)
    # Clear old correlations
    cur.execute("TRUNCATE correlation_graph")
    db.commit()

    # ============================================================
    # 1. SHARED INFRASTRUCTURE
    # ============================================================
    print("\n--- 1. SHARED INFRASTRUCTURE ---")

    # Find people (infrastructure) shared across cases
    cur.execute("""
        SELECT name, entity_type, array_agg(DISTINCT case_id) as cases
        FROM people
        WHERE role = 'INFRASTRUCTURE'
        GROUP BY name, entity_type
        HAVING count(DISTINCT case_id) > 1
        ORDER BY count(DISTINCT case_id) DESC
    """)
    shared_infra = cur.fetchall()
    print("Shared infrastructure providers: {}".format(len(shared_infra)))

    for name, entity_type, cases in shared_infra:
        confidence = 0.9 if len(cases) >= 3 else 0.7
        desc = "Cases share {} {} '{}' - may indicate same operator or infrastructure pattern".format(
            entity_type, name, ", ".join(cases))
        print("  {} ({}): {} -> {}".format(name, entity_type, len(cases), ", ".join(cases)))

        # Create pairwise correlations
        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                cur.execute("""INSERT INTO correlation_graph
                    (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                    VALUES (%s, %s, 'SHARED_INFRASTRUCTURE', %s, %s, %s, %s)""",
                    (cases[i], cases[j], name, entity_type, confidence, desc))

    # ============================================================
    # 2. SHARED TELEGRAM GROUPS
    # ============================================================
    print("\n--- 2. SHARED TELEGRAM GROUPS ---")

    # For each case, find which Telegram groups mention its domain
    cur.execute("SELECT case_id, target FROM cases WHERE target IS NOT NULL")
    all_cases = cur.fetchall()

    case_groups = defaultdict(set)
    for case_id, target in all_cases:
        domain = target.strip()
        if "." not in domain:
            continue
        cur.execute("""
            SELECT DISTINCT group_name FROM telegram_intelligence
            WHERE domains::text ILIKE %s OR message_text ILIKE %s
        """, ("%" + domain + "%", "%" + domain + "%"))
        for (group,) in cur.fetchall():
            if group:
                case_groups[case_id].add(group)

    # Find cases that share Telegram groups
    case_list = list(case_groups.keys())
    shared_group_links = 0
    for i in range(len(case_list)):
        for j in range(i + 1, len(case_list)):
            shared = case_groups[case_list[i]] & case_groups[case_list[j]]
            if shared:
                confidence = 0.8 if len(shared) >= 3 else 0.6
                desc = "Cases mentioned in same Telegram groups: {}".format(", ".join(shared))
                cur.execute("""INSERT INTO correlation_graph
                    (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                    VALUES (%s, %s, 'SHARED_TELEGRAM_GROUP', %s, 'TELEGRAM_GROUP', %s, %s)""",
                    (case_list[i], case_list[j], ", ".join(shared), confidence, desc))
                shared_group_links += 1
                print("  {} <-> {}: {} shared groups".format(case_list[i], case_list[j], len(shared)))

    print("Shared Telegram group links: {}".format(shared_group_links))

    # ============================================================
    # 3. SHARED TELEGRAM USERNAMES
    # ============================================================
    print("\n--- 3. SHARED TELEGRAM USERNAMES ---")

    # Find Telegram usernames that appear in multiple cases
    cur.execute("""
        SELECT name, array_agg(DISTINCT case_id) as cases
        FROM people
        WHERE source = 'TELEGRAM_INTELLIGENCE' AND entity_type = 'PSEUDONYMOUS'
        GROUP BY name
        HAVING count(DISTINCT case_id) > 1
    """)
    shared_users = cur.fetchall()
    for name, cases in shared_users:
        desc = "Same Telegram username ({}) appears in multiple cases".format(name)
        print("  {}: {}".format(name, ", ".join(cases)))
        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                cur.execute("""INSERT INTO correlation_graph
                    (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                    VALUES (%s, %s, 'SHARED_TELEGRAM_USER', %s, 'PSEUDONYMOUS', 0.85, %s)""",
                    (cases[i], cases[j], name, desc))

    # Also check Telegram intelligence for usernames mentioned across case domains
    case_usernames = defaultdict(set)
    for case_id, target in all_cases:
        domain = target.strip()
        if "." not in domain:
            continue
        cur.execute("""
            SELECT DISTINCT usernames::text FROM telegram_intelligence
            WHERE (domains::text ILIKE %s OR message_text ILIKE %s)
            AND usernames::text != '[]'
        """, ("%" + domain + "%", "%" + domain + "%"))
        for (usernames_raw,) in cur.fetchall():
            try:
                unames = json.loads(usernames_raw) if isinstance(usernames_raw, str) else (usernames_raw or [])
                for u in unames:
                    if u and u.lower() not in ("admin", "support", "bot", "info"):
                        case_usernames[case_id].add(u)
            except:
                pass

    # Find shared usernames across cases
    all_usernames = set()
    for case_id, unames in case_usernames.items():
        all_usernames.update(unames)

    for username in all_usernames:
        cases_with = [cid for cid, unames in case_usernames.items() if username in unames]
        if len(cases_with) > 1:
            desc = "Telegram user @{} mentioned in multiple case domains".format(username)
            print("  @{}: {} cases".format(username, len(cases_with)))
            for i in range(len(cases_with)):
                for j in range(i + 1, len(cases_with)):
                    cur.execute("""INSERT INTO correlation_graph
                        (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                        VALUES (%s, %s, 'SHARED_TELEGRAM_USER', %s, 'PSEUDONYMOUS', 0.75, %s)
                        ON CONFLICT DO NOTHING""",
                        (cases_with[i], cases_with[j], "@" + username, desc))

    # ============================================================
    # 4. SHARED DOMAINS IN TELEGRAM INTELLIGENCE
    # ============================================================
    print("\n--- 4. SHARED DOMAINS IN TELEGRAM INTELLIGENCE ---")

    # Find domains that appear in Telegram messages referencing multiple case targets
    case_domains_telegram = defaultdict(set)
    for case_id, target in all_cases:
        domain = target.strip()
        if "." not in domain:
            continue
        cur.execute("""
            SELECT DISTINCT domains::text FROM telegram_intelligence
            WHERE message_text ILIKE %s AND domains::text != '[]'
        """, ("%" + domain + "%",))
        for (domains_raw,) in cur.fetchall():
            try:
                doms = json.loads(domains_raw) if isinstance(domains_raw, str) else (domains_raw or [])
                for d in doms:
                    if d and d != domain:
                        case_domains_telegram[case_id].add(d)
            except:
                pass

    # Find domains that appear in messages about multiple cases
    all_tg_domains = set()
    for cid, doms in case_domains_telegram.items():
        all_tg_domains.update(doms)

    for domain in all_tg_domains:
        cases_with = [cid for cid, doms in case_domains_telegram.items() if domain in doms]
        if len(cases_with) > 1:
            desc = "Domain {} appears in Telegram messages about multiple cases".format(domain)
            print("  {}: {} cases".format(domain, len(cases_with)))
            for i in range(len(cases_with)):
                for j in range(i + 1, len(cases_with)):
                    cur.execute("""INSERT INTO correlation_graph
                        (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                        VALUES (%s, %s, 'SHARED_DOMAIN_MENTION', %s, 'DOMAIN', 0.7, %s)
                        ON CONFLICT DO NOTHING""",
                        (cases_with[i], cases_with[j], domain, desc))

    # ============================================================
    # 5. SHARED SCAM TYPE / PATTERN
    # ============================================================
    print("\n--- 5. SHARED SCAM PATTERNS ---")

    # Group cases by scam type from investigation steps
    cur.execute("""
        SELECT case_id, result::text FROM investigation_steps
        WHERE step_name LIKE '5.%%' AND status = 'COMPLETED'
    """)
    case_crimes = {}
    for case_id, result_text in cur.fetchall():
        try:
            result = json.loads(result_text) if isinstance(result_text, str) else result_text
            crime = result.get("primary_crime", "Unknown")
            case_crimes[case_id] = crime
        except:
            pass

    # Find cases with same crime
    crime_groups = defaultdict(list)
    for case_id, crime in case_crimes.items():
        crime_groups[crime].append(case_id)

    for crime, cases in crime_groups.items():
        if len(cases) > 1 and crime != "Unknown":
            print("  {}: {} cases -> {}".format(crime, len(cases), ", ".join(cases)))
            for i in range(len(cases)):
                for j in range(i + 1, len(cases)):
                    cur.execute("""INSERT INTO correlation_graph
                        (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                        VALUES (%s, %s, 'SHARED_SCAM_TYPE', %s, 'PATTERN', 0.5, %s)
                        ON CONFLICT DO NOTHING""",
                        (cases[i], cases[j], crime, "Both cases classified as: " + crime))

    # ============================================================
    # 6. INFRASTRUCTURE CHAIN (same registrar + same hosting)
    # ============================================================
    print("\n--- 6. INFRASTRUCTURE CHAIN CORRELATION ---")

    # Get registrar + hosting for each case
    case_infra = {}
    for case_id, target in all_cases:
        cur.execute("""
            SELECT name, entity_type FROM people
            WHERE case_id = %s AND role = 'INFRASTRUCTURE'
        """, (case_id,))
        registrar = None
        hosting = None
        for name, etype in cur.fetchall():
            if etype == "REGISTRAR":
                registrar = name
            elif etype == "HOSTING":
                hosting = name
        case_infra[case_id] = {"registrar": registrar, "hosting": hosting}

    # Find cases with BOTH same registrar AND same hosting
    case_list = list(case_infra.keys())
    chain_links = 0
    for i in range(len(case_list)):
        for j in range(i + 1, len(case_list)):
            ci = case_infra[case_list[i]]
            cj = case_infra[case_list[j]]
            if (ci["registrar"] and ci["registrar"] == cj["registrar"] and
                ci["hosting"] and ci["hosting"] == cj["hosting"]):
                desc = "SAME registrar ({}) AND SAME hosting ({}) - strong indicator of same operator".format(
                    ci["registrar"], ci["hosting"])
                cur.execute("""INSERT INTO correlation_graph
                    (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                    VALUES (%s, %s, 'INFRASTRUCTURE_CHAIN', %s, 'COMBINED', 0.85, %s)
                    ON CONFLICT DO NOTHING""",
                    (case_list[i], case_list[j],
                     ci["registrar"] + " + " + ci["hosting"], desc))
                chain_links += 1
                print("  {} <-> {}: {} + {}".format(case_list[i], case_list[j], ci["registrar"], ci["hosting"]))

    print("Infrastructure chain links: {}".format(chain_links))

    # ============================================================
    # 7. RECRUITMENT NETWORK CORRELATION
    # ============================================================
    print("\n--- 7. RECRUITMENT NETWORK CORRELATION ---")

    # Cases that have recruitment indicators are likely connected through the same recruitment network
    cur.execute("""
        SELECT case_id, result::text FROM investigation_steps
        WHERE step_name LIKE '5.%%' AND status = 'COMPLETED'
        AND result::text ILIKE '%%recruitment%%'
    """)
    recruitment_cases = [row[0] for row in cur.fetchall()]
    if len(recruitment_cases) > 1:
        print("Recruitment cases: {} -> {}".format(len(recruitment_cases), ", ".join(recruitment_cases)))
        for i in range(len(recruitment_cases)):
            for j in range(i + 1, len(recruitment_cases)):
                cur.execute("""INSERT INTO correlation_graph
                    (source_case, target_case, correlation_type, entity_value, entity_type, confidence, description)
                    VALUES (%s, %s, 'RECRUITMENT_NETWORK', 'TRAFFICKING_INDICATOR', 'PATTERN', 0.7,
                    'Both cases show human trafficking / recruitment indicators - may be part of same network')
                    ON CONFLICT DO NOTHING""",
                    (recruitment_cases[i], recruitment_cases[j]))

    db.commit()

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("CORRELATION ENGINE COMPLETE")
    print(sep)

    # Summary stats
    cur.execute("SELECT correlation_type, COUNT(*) FROM correlation_graph GROUP BY correlation_type ORDER BY count DESC")
    print("\nCorrelations by type:")
    for ctype, count in cur.fetchall():
        print("  {}: {}".format(ctype, count))

    cur.execute("SELECT COUNT(*) FROM correlation_graph")
    total = cur.fetchone()[0]
    print("\nTotal correlations: {}".format(total))

    # High confidence links
    cur.execute("""SELECT source_case, target_case, correlation_type, entity_value, confidence, LEFT(description, 100)
        FROM correlation_graph WHERE confidence >= 0.8 ORDER BY confidence DESC""")
    high_conf = cur.fetchall()
    print("High confidence links (>=0.8): {}".format(len(high_conf)))
    for sc, tc, ct, ev, conf, desc in high_conf[:15]:
        print("  {} <-> {} [{}] {} (conf={:.2f})".format(sc, tc, ct, ev, conf))

    # Most connected cases
    cur.execute("""
        SELECT case_id, COUNT(*) as links FROM (
            SELECT source_case as case_id FROM correlation_graph
            UNION ALL
            SELECT target_case as case_id FROM correlation_graph
        ) t GROUP BY case_id ORDER BY links DESC LIMIT 10
    """)
    print("\nMost connected cases:")
    for case_id, links in cur.fetchall():
        print("  {}: {} correlations".format(case_id, links))

    cur.close()
    db.close()
    return total


if __name__ == "__main__":
    run_correlation_engine()
