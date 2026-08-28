#!/usr/bin/env python3
"""
GFIN Investigation Enhancement Suite v1.0
Seven modules to drive investigations from evidence collection toward prosecution.

1. Timeline Reconstruction — chronological crime timeline per case
2. Evidence Cross-Case Correlation — same wallet/phone/IP across cases
3. Gap Analysis — per-case prosecution readiness checklist
4. Quality Score — per-case investigation quality metric
5. Victim Follow-up Questions — auto-generated based on scam type
6. Chain of Custody — formal legal custody records
7. Multi-Jurisdiction Tracker — country notification status
"""
import sys
import json
import hashlib
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, "/gfin")
import psycopg2

DB = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def get_db():
    return psycopg2.connect(**DB)


# ============================================================
# 1. TIMELINE RECONSTRUCTION
# ============================================================
def build_timeline(case_id, cur):
    """Build a chronological crime timeline from all evidence and case data."""
    events = []

    # Domain registration date
    cur.execute("SELECT target FROM cases WHERE case_id = %s", (case_id,))
    target = (cur.fetchone() or [""])[0]

    cur.execute("""
        SELECT finding, content_hash, timestamp, source_provider
        FROM evidence WHERE case_id = %s AND phase IN ('WHOIS', 'INTEL_CONTEXT', 'INFRA', 'CONTENT', 'RISK_ASSESSMENT')
        ORDER BY timestamp
    """, (case_id,))
    for finding, ch, ts, provider in cur.fetchall():
        events.append({
            "date": ts.isoformat() if ts else None,
            "type": "EVIDENCE",
            "source": provider or "GFIN",
            "description": (finding or "")[:200],
            "hash": ch,
        })

    # Investigation steps
    cur.execute("SELECT step_name, status, result, created_date FROM investigation_steps WHERE case_id = %s ORDER BY created_date", (case_id,))
    for step_name, status, result, created in cur.fetchall():
        events.append({
            "date": created.isoformat() if created else None,
            "type": "INVESTIGATION_STEP",
            "source": "GFIN-Investigator",
            "description": "{} ({})".format(step_name, status),
        })

    # Victim complaints
    cur.execute("SELECT reference_number, scam_type, created_date FROM victim_complaints WHERE case_id = %s ORDER BY created_date", (case_id,))
    for ref, scam_type, created in cur.fetchall():
        events.append({
            "date": created.isoformat() if created else None,
            "type": "VICTIM_REPORT",
            "source": "Victim Portal",
            "description": "Victim complaint {}: {}".format(ref, scam_type or "Unknown"),
        })

    # Telegram intelligence
    cur.execute("""
        SELECT created_at, group_name, scam_type, risk_level
        FROM telegram_intelligence
        WHERE domains::text ILIKE %s
        ORDER BY created_at
    """, (f"%{target}%",))
    for created_at, group, scam_type, risk in cur.fetchall():
        events.append({
            "date": created_at.isoformat() if created_at else None,
            "type": "TELEGRAM_INTEL",
            "source": group or "Telegram",
            "description": "Telegram mention: {} ({})".format(scam_type or "Unknown", risk or "?"),
        })

    # Sort by date
    events.sort(key=lambda e: e["date"] or "9999")
    return events


# ============================================================
# 2. EVIDENCE CROSS-CASE CORRELATION
# ============================================================
def cross_case_evidence_correlation(cur):
    """Find evidence items that share wallets, phones, IPs, or emails across cases."""
    correlations = []

    # Get all evidence with their findings
    cur.execute("SELECT case_id, evidence_id, finding, phase FROM evidence ORDER BY case_id")
    all_ev = cur.fetchall()

    # Extract identifiers from findings
    import re
    identifier_map = defaultdict(list)  # identifier -> [(case_id, evidence_id)]

    patterns = {
        "WALLET": r'(?:bc1[a-z0-9]{39,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40}|T[A-Za-z1-9]{33})',
        "IP": r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
        "EMAIL": r'[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}',
        "PHONE": r'\+\d{6,15}',
    }

    for case_id, ev_id, finding, phase in all_ev:
        if not finding:
            continue
        for id_type, pattern in patterns.items():
            matches = re.findall(pattern, finding)
            for m in matches:
                identifier_map[(id_type, m)].append((case_id, ev_id))

    # Find identifiers appearing in multiple cases
    for (id_type, identifier), locations in identifier_map.items():
        unique_cases = set(c for c, e in locations)
        if len(unique_cases) >= 2:
            correlations.append({
                "type": id_type,
                "identifier": identifier[:20] + "..." if len(identifier) > 20 else identifier,
                "cases": list(unique_cases),
                "evidence_items": [{"case_id": c, "evidence_id": e} for c, e in locations],
                "correlation_strength": "STRONG" if len(unique_cases) >= 3 else "MEDIUM",
            })

    return correlations


# ============================================================
# 3. GAP ANALYSIS — Prosecution Readiness Checklist
# ============================================================
def gap_analysis(case_id, cur):
    """Per-case checklist of what's missing for prosecution referral."""
    checklist = []

    # Evidence count
    cur.execute("SELECT COUNT(*) FROM evidence WHERE case_id = %s", (case_id,))
    ev_count = cur.fetchone()[0]
    if ev_count < 5:
        checklist.append({"item": "Minimum 5 evidence items", "status": "MISSING", "current": ev_count, "target": 5})
    elif ev_count < 10:
        checklist.append({"item": "Minimum 5 evidence items", "status": "MET", "current": ev_count, "target": 5})
        checklist.append({"item": "Recommended 10+ evidence items", "status": "PARTIAL", "current": ev_count, "target": 10})
    else:
        checklist.append({"item": "Evidence count (10+)", "status": "MET", "current": ev_count, "target": 10})

    # Provenance quality
    cur.execute("SELECT AVG(legal_admissibility_score) FROM evidence WHERE case_id = %s", (case_id,))
    avg_score = cur.fetchone()[0] or 0
    if avg_score >= 0.9:
        checklist.append({"item": "Evidence provenance quality (avg admissibility)", "status": "MET", "current": round(avg_score, 3), "target": 0.9})
    elif avg_score >= 0.7:
        checklist.append({"item": "Evidence provenance quality", "status": "PARTIAL", "current": round(avg_score, 3), "target": 0.9})
    else:
        checklist.append({"item": "Evidence provenance quality", "status": "MISSING", "current": round(avg_score, 3), "target": 0.9})

    # Entity types covered
    cur.execute("SELECT COUNT(DISTINCT role) FROM people WHERE case_id = %s", (case_id,))
    entity_types = cur.fetchone()[0]
    if entity_types >= 4:
        checklist.append({"item": "Entity coverage (4+ types: domain, person, wallet, infra)", "status": "MET", "current": entity_types, "target": 4})
    elif entity_types >= 2:
        checklist.append({"item": "Entity coverage (4+ types)", "status": "PARTIAL", "current": entity_types, "target": 4})
    else:
        checklist.append({"item": "Entity coverage (4+ types)", "status": "MISSING", "current": entity_types, "target": 4})

    # Victim count
    cur.execute("SELECT COUNT(*) FROM victim_complaints WHERE case_id = %s", (case_id,))
    victim_count = cur.fetchone()[0]
    if victim_count >= 1:
        checklist.append({"item": "At least 1 victim complaint", "status": "MET", "current": victim_count, "target": 1})
    else:
        checklist.append({"item": "At least 1 victim complaint", "status": "MISSING", "current": 0, "target": 1})

    # Wallet identification
    cur.execute("SELECT 1 FROM evidence WHERE case_id = %s AND finding ILIKE '%%wallet%%'", (case_id,))
    has_wallet = cur.fetchone() is not None
    checklist.append({"item": "Crypto wallet identified", "status": "MET" if has_wallet else "MISSING", "current": 1 if has_wallet else 0, "target": 1})

    # Physical location
    cur.execute("SELECT 1 FROM people WHERE case_id = %s AND role = 'INFRASTRUCTURE' AND details ILIKE '%%country%%'", (case_id,))
    has_location = cur.fetchone() is not None
    checklist.append({"item": "Physical hosting location identified", "status": "MET" if has_location else "MISSING", "current": 1 if has_location else 0, "target": 1})

    # Country routing
    cur.execute("SELECT routed_to_countries FROM cases WHERE case_id = %s", (case_id,))
    routed = cur.fetchone()
    has_routing = routed and routed[0] and len(routed[0]) > 0
    checklist.append({"item": "Country routing completed", "status": "MET" if has_routing else "MISSING", "current": 1 if has_routing else 0, "target": 1})

    # Investigation steps
    cur.execute("SELECT COUNT(*) FROM investigation_steps WHERE case_id = %s AND status = 'COMPLETED'", (case_id,))
    steps_done = cur.fetchone()[0]
    if steps_done >= 4:
        checklist.append({"item": "Investigation steps completed (4+)", "status": "MET", "current": steps_done, "target": 4})
    else:
        checklist.append({"item": "Investigation steps completed (4+)", "status": "PARTIAL", "current": steps_done, "target": 4})

    # Calculate readiness
    met = sum(1 for c in checklist if c["status"] == "MET")
    partial = sum(1 for c in checklist if c["status"] == "PARTIAL")
    missing = sum(1 for c in checklist if c["status"] == "MISSING")
    total = len(checklist)
    readiness = int((met + partial * 0.5) / total * 100) if total > 0 else 0

    return {
        "checklist": checklist,
        "met": met,
        "partial": partial,
        "missing": missing,
        "total": total,
        "readiness_score": readiness,
        "prosecution_ready": readiness >= 80 and missing == 0,
    }


# ============================================================
# 4. INVESTIGATION QUALITY SCORE
# ============================================================
def quality_score(case_id, cur):
    """Per-case investigation quality metric."""
    # Evidence count (0-25)
    cur.execute("SELECT COUNT(*) FROM evidence WHERE case_id = %s", (case_id,))
    ev_count = cur.fetchone()[0]
    evidence_score = min(25, ev_count * 2.5)

    # Provenance quality (0-20)
    cur.execute("SELECT AVG(legal_admissibility_score) FROM evidence WHERE case_id = %s", (case_id,))
    avg_admiss = cur.fetchone()[0] or 0
    provenance_score = avg_admiss * 20

    # Entity coverage (0-15)
    cur.execute("SELECT COUNT(DISTinct role) FROM people WHERE case_id = %s", (case_id,))
    entity_count = cur.fetchone()[0]
    entity_score = min(15, entity_count * 3.75)

    # Victim count (0-15)
    cur.execute("SELECT COUNT(*) FROM victim_complaints WHERE case_id = %s", (case_id,))
    victim_count = cur.fetchone()[0]
    victim_score = min(15, victim_count * 7.5)

    # Correlation density (0-15)
    cur.execute("SELECT COUNT(*) FROM correlation_graph WHERE source_case = %s OR target_case = %s", (case_id, case_id))
    corr_count = cur.fetchone()[0]
    corr_score = min(15, corr_count * 1.5)

    # Investigation steps (0-10)
    cur.execute("SELECT COUNT(*) FROM investigation_steps WHERE case_id = %s AND status = 'COMPLETED'", (case_id,))
    steps = cur.fetchone()[0]
    step_score = min(10, steps * 2.5)

    total = evidence_score + provenance_score + entity_score + victim_score + corr_score + step_score

    return {
        "evidence": round(evidence_score, 1),
        "provenance": round(provenance_score, 1),
        "entity_coverage": round(entity_score, 1),
        "victim_count": round(victim_score, 1),
        "correlation_density": round(corr_score, 1),
        "investigation_steps": round(step_score, 1),
        "total": round(total, 1),
        "grade": "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D" if total >= 20 else "F",
    }


# ============================================================
# 5. AUTOMATED VICTIM FOLLOW-UP QUESTIONS
# ============================================================
VICTIM_QUESTIONS = {
    "INVESTMENT_FRAUD": [
        "What platform or website did you use to make the investment?",
        "How were you first contacted? (social media, phone, email, friend)",
        "What was the name of the person who recruited you?",
        "Did you communicate on Telegram, WhatsApp, or another messaging app?",
        "What crypto wallet address did you send funds to?",
        "What was the promised return on investment?",
        "Did you receive any initial payouts before losing money?",
        "Do you have screenshots of conversations or the trading platform?",
        "What dates did the transactions occur?",
        "Did the platform require you to pay 'withdrawal fees' or 'taxes'?",
    ],
    "RECOVERY_SCAM": [
        "Who contacted you offering to recover your lost funds?",
        "Did they claim to be from a government agency or law firm?",
        "How much did they ask you to pay upfront?",
        "What was their phone number or email address?",
        "Did they mention any specific case number or reference?",
        "Have you already filed a complaint with law enforcement about the original scam?",
        "Did they ask for remote access to your computer or bank account?",
    ],
    "ROMANCE_SCAM": [
        "What dating platform did you meet the person on?",
        "What name and photos did they use?",
        "How long did you communicate before money was requested?",
        "What was the reason given for needing money?",
        "Did they ask you to send money via crypto, wire transfer, or gift cards?",
        "Did they ever agree to meet in person or make video calls?",
        "Do you have their phone number and any photos they sent?",
    ],
    "JOB_SCAM": [
        "What job title or position were you offered?",
        "Where did you see the job posting?",
        "Were you asked to pay any upfront fees for equipment or training?",
        "Were you asked to provide your bank account or SSN?",
        "Did they ask you to receive and forward packages or money?",
        "What company name did they claim to represent?",
        "Were you asked to travel to another country for the job?",
    ],
    "PHISHING": [
        "What website or email looked suspicious?",
        "Did you enter your login credentials on the site?",
        "What account was compromised (bank, email, social media)?",
        "Did you receive any unauthorized transactions?",
        "Have you changed your passwords since the incident?",
        "Did the site have a padlock/HTTPS icon?",
    ],
    "DEFAULT": [
        "Describe what happened in as much detail as possible.",
        "When did the incident occur?",
        "How much money did you lose?",
        "How were you first contacted?",
        "What names, phone numbers, or email addresses were used?",
        "Do you have any screenshots, emails, or messages as evidence?",
        "Have you reported this to any other authority?",
    ],
}


def generate_questions(scam_type):
    """Generate follow-up questions based on scam type."""
    key = scam_type.upper().replace(" ", "_") if scam_type else "DEFAULT"
    return VICTIM_QUESTIONS.get(key, VICTIM_QUESTIONS["DEFAULT"])


# ============================================================
# 6. CHAIN OF CUSTODY
# ============================================================
def create_custody_records(cur):
    """Create formal chain of custody records for all evidence."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chain_of_custody (
            id SERIAL PRIMARY KEY,
            evidence_id VARCHAR(100),
            case_id VARCHAR(100),
            custodian VARCHAR(200),
            custody_purpose VARCHAR(200),
            received_date TIMESTAMP DEFAULT NOW(),
            custody_hash TEXT,
            notes TEXT
        )
    """)

    cur.execute("""
        SELECT id, case_id, evidence_id, provenance_source, provenance_provider,
               provenance_collector, provenance_content_hash, content_hash, timestamp
        FROM evidence WHERE provenance_complete = true
    """)
    all_ev = cur.fetchall()
    created = 0

    for eid, case_id, ev_id, source, provider, collector, p_hash, c_hash, ts in all_ev:
        # Check if custody record already exists
        cur.execute("SELECT 1 FROM chain_of_custody WHERE evidence_id = %s", (ev_id,))
        if cur.fetchone():
            continue

        # Create initial custody record (collection)
        custody_hash = hashlib.sha256("{}|{}|{}|{}".format(ev_id, collector or "GFIN", ts or datetime.utcnow(), c_hash or p_hash).encode()).hexdigest()

        cur.execute("""INSERT INTO chain_of_custody
            (evidence_id, case_id, custodian, custody_purpose, received_date, custody_hash, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (ev_id, case_id, collector or "GFIN Automated Collector",
             "Initial collection and preservation",
             ts or datetime.utcnow(),
             custody_hash,
             "Collected by {} from {} via {}. Hash: {}".format(collector or "GFIN", source or "Unknown", provider or "Unknown", (c_hash or p_hash or "")[:16])))

        # Create second custody record (analysis)
        cur.execute("""INSERT INTO chain_of_custody
            (evidence_id, case_id, custodian, custody_purpose, received_date, custody_hash, notes)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s)""",
            (ev_id, case_id, "GFIN Investigation Pipeline",
             "Automated analysis and correlation",
             hashlib.sha256("{}|analysis|{}".format(ev_id, custody_hash).encode()).hexdigest(),
             "Processed through GFIN investigation pipeline for entity extraction and correlation"))

        created += 2

    return created


# ============================================================
# 7. MULTI-JURISDICTION TRACKER
# ============================================================
def jurisdiction_tracker(cur):
    """Track which countries have been notified and their response status."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jurisdiction_notifications (
            id SERIAL PRIMARY KEY,
            case_id VARCHAR(100),
            country_code VARCHAR(10),
            country_name VARCHAR(100),
            agency_name VARCHAR(200),
            agency_email VARCHAR(200),
            notification_status VARCHAR(50) DEFAULT 'PENDING',
            notification_date TIMESTAMP,
            response_date TIMESTAMP,
            response_notes TEXT,
            created_date TIMESTAMP DEFAULT NOW()
        )
    """)

    # Get all cases with routing info
    cur.execute("SELECT case_id, routed_to_countries, affected_countries FROM cases WHERE routed_to_countries IS NOT NULL")
    cases = cur.fetchall()
    created = 0

    for case_id, routed, affected in cases:
        if not routed:
            continue
        countries = routed if isinstance(routed, list) else json.loads(routed)

        for country in countries:
            if isinstance(country, dict):
                code = country.get("code", "")
                name = country.get("name", "")
                agency = country.get("agency", "")
                email = country.get("email", "")
            else:
                code = str(country)[:10]
                name = str(country)
                agency = ""
                email = ""

            # Check if already exists
            cur.execute("SELECT 1 FROM jurisdiction_notifications WHERE case_id = %s AND country_code = %s", (case_id, code))
            if cur.fetchone():
                continue

            cur.execute("""INSERT INTO jurisdiction_notifications
                (case_id, country_code, country_name, agency_name, agency_email, notification_status)
                VALUES (%s, %s, %s, %s, %s, 'PENDING')""",
                (case_id, code, name, agency, email))
            created += 1

    return created


# ============================================================
# MAIN
# ============================================================
def run_all():
    db = get_db()
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN INVESTIGATION ENHANCEMENT SUITE v1.0")
    print("7 modules to drive investigations toward prosecution")
    print(sep)

    # Get all cases
    cur.execute("SELECT case_id, target, priority FROM cases ORDER BY case_id")
    cases = cur.fetchall()
    print("Cases: {}".format(len(cases)))

    # ============================================================
    # 1. TIMELINE RECONSTRUCTION
    # ============================================================
    print("\n--- 1. TIMELINE RECONSTRUCTION ---")
    cur.execute("CREATE TABLE IF NOT EXISTS case_timelines (id SERIAL PRIMARY KEY, case_id VARCHAR(100), event_date TIMESTAMP, event_type VARCHAR(50), source VARCHAR(200), description TEXT, created_date TIMESTAMP DEFAULT NOW())")
    cur.execute("TRUNCATE case_timelines")
    total_events = 0
    for case_id, target, priority in cases:
        events = build_timeline(case_id, cur)
        for ev in events:
            cur.execute("INSERT INTO case_timelines (case_id, event_date, event_type, source, description) VALUES (%s, %s, %s, %s, %s)",
                (case_id, ev["date"], ev["type"], ev["source"], ev["description"]))
        total_events += len(events)
        if events:
            print("  {}: {} events".format(case_id, len(events)))
    db.commit()
    print("Total timeline events: {}".format(total_events))

    # ============================================================
    # 2. CROSS-CASE EVIDENCE CORRELATION
    # ============================================================
    print("\n--- 2. CROSS-CASE EVIDENCE CORRELATION ---")
    correlations = cross_case_evidence_correlation(cur)
    cur.execute("CREATE TABLE IF NOT EXISTS evidence_cross_case (id SERIAL PRIMARY KEY, identifier_type VARCHAR(50), identifier VARCHAR(200), cases JSONB, evidence_items JSONB, correlation_strength VARCHAR(20), created_date TIMESTAMP DEFAULT NOW())")
    cur.execute("TRUNCATE evidence_cross_case")
    for corr in correlations:
        cur.execute("INSERT INTO evidence_cross_case (identifier_type, identifier, cases, evidence_items, correlation_strength) VALUES (%s, %s, %s, %s, %s)",
            (corr["type"], corr["identifier"], json.dumps(corr["cases"]), json.dumps(corr["evidence_items"]), corr["correlation_strength"]))
    db.commit()
    print("Cross-case correlations: {}".format(len(correlations)))
    for c in correlations[:5]:
        print("  [{}] {} appears in {} cases: {}".format(c["type"], c["identifier"], len(c["cases"]), ", ".join(c["cases"])))

    # ============================================================
    # 3. GAP ANALYSIS
    # ============================================================
    print("\n--- 3. GAP ANALYSIS (Prosecution Readiness) ---")
    cur.execute("CREATE TABLE IF NOT EXISTS prosecution_gaps (id SERIAL PRIMARY KEY, case_id VARCHAR(100), checklist JSONB, met_count INT, partial_count INT, missing_count INT, readiness_score INT, prosecution_ready BOOLEAN, created_date TIMESTAMP DEFAULT NOW())")
    # Fix: column name length
    cur.execute("DROP TABLE IF EXISTS prosecution_gaps")
    cur.execute("CREATE TABLE IF NOT EXISTS prosecution_gaps (id SERIAL PRIMARY KEY, case_id VARCHAR(100), checklist JSONB, met_count INT, partial_count INT, missing_count INT, readiness_score INT, prosecution_ready BOOLEAN, created_date TIMESTAMP DEFAULT NOW())")
    cur.execute("TRUNCATE prosecution_gaps")
    for case_id, target, priority in cases:
        gaps = gap_analysis(case_id, cur)
        cur.execute("INSERT INTO prosecution_gaps (case_id, checklist, met_count, partial_count, missing_count, readiness_score, prosecution_ready) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (case_id, json.dumps(gaps["checklist"]), gaps["met"], gaps["partial"], gaps["missing"], gaps["readiness_score"], gaps["prosecution_ready"]))
        status = "READY" if gaps["prosecution_ready"] else "{}% ({} missing)".format(gaps["readiness_score"], gaps["missing"])
        print("  {}: {} - met={} partial={} missing={}".format(case_id, status, gaps["met"], gaps["partial"], gaps["missing"]))
    db.commit()

    # ============================================================
    # 4. QUALITY SCORE
    # ============================================================
    print("\n--- 4. INVESTIGATION QUALITY SCORE ---")
    cur.execute("CREATE TABLE IF NOT EXISTS investigation_quality (id SERIAL PRIMARY KEY, case_id VARCHAR(100), evidence_score REAL, provenance_score REAL, entity_score REAL, victim_score REAL, correlation_score REAL, step_score REAL, total_score REAL, grade VARCHAR(5), created_date TIMESTAMP DEFAULT NOW())")
    cur.execute("TRUNCATE investigation_quality")
    for case_id, target, priority in cases:
        qs = quality_score(case_id, cur)
        cur.execute("INSERT INTO investigation_quality (case_id, evidence_score, provenance_score, entity_score, victim_score, correlation_score, step_score, total_score, grade) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (case_id, qs["evidence"], qs["provenance"], qs["entity_coverage"], qs["victim_count"], qs["correlation_density"], qs["investigation_steps"], qs["total"], qs["grade"]))
        print("  {}: {:.1f}/100 [{}] - ev={:.1f} prov={:.1f} ent={:.1f} vic={:.1f} corr={:.1f} step={:.1f}".format(
            case_id, qs["total"], qs["grade"], qs["evidence"], qs["provenance"], qs["entity_coverage"], qs["victim_count"], qs["correlation_density"], qs["investigation_steps"]))
    db.commit()

    # ============================================================
    # 5. VICTIM FOLLOW-UP QUESTIONS
    # ============================================================
    print("\n--- 5. VICTIM FOLLOW-UP QUESTIONS ---")
    cur.execute("SELECT reference_number, scam_type, case_id FROM victim_complaints")
    complaints = cur.fetchall()
    cur.execute("CREATE TABLE IF NOT EXISTS victim_questions (id SERIAL PRIMARY KEY, reference_number VARCHAR(100), case_id VARCHAR(100), scam_type VARCHAR(100), questions JSONB, created_date TIMESTAMP DEFAULT NOW())")
    cur.execute("TRUNCATE victim_questions")
    q_count = 0
    for ref, scam_type, case_id in complaints:
        questions = generate_questions(scam_type)
        cur.execute("INSERT INTO victim_questions (reference_number, case_id, scam_type, questions) VALUES (%s, %s, %s, %s)",
            (ref, case_id, scam_type or "Unknown", json.dumps(questions)))
        print("  {} [{}]: {} questions".format(ref[:20], scam_type or "Unknown", len(questions)))
        q_count += 1
    db.commit()
    print("Question sets generated: {}".format(q_count))

    # ============================================================
    # 6. CHAIN OF CUSTODY
    # ============================================================
    print("\n--- 6. CHAIN OF CUSTODY RECORDS ---")
    custody_count = create_custody_records(cur)
    db.commit()
    print("Custody records created: {}".format(custody_count))

    # ============================================================
    # 7. MULTI-JURISDICTION TRACKER
    # ============================================================
    print("\n--- 7. MULTI-JURISDICTION TRACKER ---")
    jur_count = jurisdiction_tracker(cur)
    db.commit()
    print("Jurisdiction notifications tracked: {}".format(jur_count))

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("INVESTIGATION ENHANCEMENT COMPLETE")
    print(sep)
    print("1. Timeline events: {}".format(total_events))
    print("2. Cross-case correlations: {}".format(len(correlations)))
    print("3. Gap analysis: {} cases assessed".format(len(cases)))
    print("4. Quality scores: {} cases graded".format(len(cases)))
    print("5. Victim question sets: {}".format(q_count))
    print("6. Custody records: {}".format(custody_count))
    print("7. Jurisdiction notifications: {}".format(jur_count))

    # Show quality grade distribution
    cur.execute("SELECT grade, COUNT(*) FROM investigation_quality GROUP BY grade ORDER BY grade")
    print("\nQuality grade distribution:")
    for grade, count in cur.fetchall():
        print("  {}: {} cases".format(grade, count))

    # Show prosecution readiness
    cur.execute("SELECT COUNT(*) FROM prosecution_gaps WHERE prosecution_ready = true")
    ready = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prosecution_gaps WHERE readiness_score >= 60")
    near_ready = cur.fetchone()[0]
    print("\nProsecution readiness:")
    print("  Ready for referral: {}".format(ready))
    print("  Near ready (60%+): {}".format(near_ready))

    cur.close()
    db.close()


if __name__ == "__main__":
    run_all()
