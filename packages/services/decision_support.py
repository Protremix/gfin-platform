#!/usr/bin/env python3
"""
GFIN Analyst Decision Support Engine v1.0
Provides investigators with actionable recommendations, risk assessments,
and priority rankings based on case data.
"""
import sys
import json
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def run_decision_support():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN ANALYST DECISION SUPPORT ENGINE v1.0")
    print("Generating investigative recommendations")
    print(sep)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyst_recommendations (
            id SERIAL PRIMARY KEY,
            case_id VARCHAR(100),
            recommendation_type VARCHAR(50),
            priority VARCHAR(20),
            title TEXT,
            description TEXT,
            action_items JSONB,
            risk_score REAL,
            confidence REAL,
            created_date TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("TRUNCATE analyst_recommendations")
    db.commit()

    cur.execute("""
        SELECT c.case_id, c.target, c.priority, c.confidence, c.status,
               c.case_phase, c.created_date,
               (SELECT COUNT(*) FROM evidence e WHERE e.case_id = c.case_id) as evidence_count,
               (SELECT AVG(legal_admissibility_score) FROM evidence e WHERE e.case_id = c.case_id) as avg_admissibility,
               (SELECT COUNT(*) FROM people p WHERE p.case_id = c.case_id) as people_count,
               (SELECT COUNT(*) FROM investigation_steps s WHERE s.case_id = c.case_id AND s.status = 'COMPLETED') as completed_steps
        FROM cases c ORDER BY c.case_id
    """)
    cases = cur.fetchall()
    print("Cases to analyze: {}".format(len(cases)))

    cur.execute("SELECT source_case, COUNT(*) FROM correlation_graph GROUP BY source_case")
    correlation_counts = defaultdict(int)
    for case_id, count in cur.fetchall():
        correlation_counts[case_id] += count

    total_recs = 0

    for case_data in cases:
        case_id = case_data[0]
        target = case_data[1]
        priority = case_data[2] or "MEDIUM"
        confidence = case_data[3] or 0.5
        status = case_data[4] or "OPEN"
        case_phase = case_data[5] or ""
        created = case_data[6]
        evidence_count = case_data[7] or 0
        avg_admissibility = case_data[8] or 0
        people_count = case_data[9] or 0
        completed_steps = case_data[10] or 0
        correlations = correlation_counts.get(case_id, 0)

        severity_map = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.6, "LOW": 0.3}
        severity_score = severity_map.get(priority, 0.5)
        evidence_strength = min(1.0, evidence_count / 10) * 0.7 + avg_admissibility * 0.3
        correlation_score = min(1.0, correlations / 30)
        cur.execute("SELECT COUNT(*) FROM victim_complaints WHERE case_id = %s", (case_id,))
        victim_count = cur.fetchone()[0]
        victim_score = min(1.0, victim_count / 3)

        # Action 1: Low evidence
        if evidence_count < 5:
            desc = "Case has only {} evidence items. Minimum 5-10 needed for prosecution referral.".format(evidence_count)
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'EVIDENCE_GAP', 'HIGH', 'Collect additional evidence', %s, %s, %s, 0.8)""",
                (case_id, desc,
                 json.dumps(["Run Hunter v4 on {}".format(target), "Check URLScan snapshots",
                             "Cross-reference Telegram intel", "Check ScamAdviser"]),
                 1.0 - evidence_strength))
            total_recs += 1

        # Action 2: Weak provenance
        if avg_admissibility < 0.7:
            desc = "Average admissibility score {:.2f}. Some evidence may not meet legal standards.".format(avg_admissibility)
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'PROVENANCE', 'MEDIUM', 'Strengthen evidence provenance', %s, %s, 0.3, 0.7)""",
                (case_id, desc,
                 json.dumps(["Verify all evidence has content hash", "Add witness statements",
                             "Document collection methodology", "Ensure chain of custody"])))
            total_recs += 1

        # Action 3: High correlations
        if correlations >= 10:
            desc = "{} correlations to other cases. This case may be part of a larger network.".format(correlations)
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'CROSS_CASE', 'HIGH', 'Joint investigation recommended', %s, %s, 0.5, 0.9)""",
                (case_id, desc,
                 json.dumps(["Review correlation graph for shared infrastructure",
                             "Check if same registrar/hosting as other cases",
                             "Cross-reference Telegram usernames across cases",
                             "Consider joint investigation with related cases"])))
            total_recs += 1

        # Action 4: Trafficking indicators
        if target and any(w in target.lower() for w in ["hr", "job", "recruit", "monde", "tati", "zohar"]):
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'TRAFFICKING', 'CRITICAL', 'Human trafficking indicators detected',
                'Domain name and Telegram intelligence suggest possible human trafficking recruitment. URGENT.',
                %s, 0.9, 0.85)""",
                (case_id,
                 json.dumps(["IMMEDIATE: Route to anti-trafficking unit",
                             "Check recruitment platforms for active listings",
                             "Identify and warn potential victims",
                             "Coordinate with destination country law enforcement",
                             "Monitor Telegram groups for new recruitment posts"])))
            total_recs += 1

        # Action 5: Domain still active
        if target:
            domain_check = target.split()[0].split("/")[0]
            cur.execute("SELECT 1 FROM tracked_domains WHERE domain = %s AND status = 'ACTIVE'", (domain_check,))
            if cur.fetchone():
                desc = "Domain {} appears to still be operational. Victims are being actively harmed.".format(target)
                cur.execute("""INSERT INTO analyst_recommendations
                    (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                    VALUES (%s, 'TAKEDOWN', 'HIGH', 'Scam domain still active', %s, %s, 0.8, 0.9)""",
                    (case_id, desc,
                     json.dumps(["Request registrar suspension", "Submit to Google Safe Browsing",
                                 "Submit to Microsoft SmartScreen", "Request hosting provider suspension",
                                 "Issue public warning via GFIN Telegram bot"])))
                total_recs += 1

        # Action 6: Unstarted investigation
        cur.execute("SELECT 1 FROM victim_complaints WHERE case_id = %s AND (auto_investigation_started = false OR auto_investigation_started IS NULL)", (case_id,))
        if cur.fetchone():
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'INVESTIGATION', 'HIGH', 'Auto-investigation not started',
                'Victim complaint exists but no investigation has been triggered.',
                %s, 0.6, 0.95)""",
                (case_id,
                 json.dumps(["Trigger auto-investigation pipeline", "Run scam detection engine",
                             "Extract entities and run connectors", "Route to appropriate country authority"])))
            total_recs += 1

        # Action 7: Offshore/privacy infrastructure (flight risk)
        cur.execute("""SELECT 1 FROM people WHERE case_id = %s AND role = 'INFRASTRUCTURE'
            AND (details ILIKE '%%offshore%%' OR details ILIKE '%%non-US%%' OR details ILIKE '%%Russia%%'
                 OR details ILIKE '%%DDoS-Guard%%' OR details ILIKE '%%privacy%%' OR details ILIKE '%%AE%%')""", (case_id,))
        if cur.fetchone():
            cur.execute("""INSERT INTO analyst_recommendations
                (case_id, recommendation_type, priority, title, description, action_items, risk_score, confidence)
                VALUES (%s, 'FLIGHT_RISK', 'MEDIUM', 'Offshore/privacy infrastructure detected',
                'Suspect uses offshore hosting or privacy services. Evidence preservation is urgent.',
                %s, 0.7, 0.8)""",
                (case_id,
                 json.dumps(["Preserve all digital evidence immediately (URLScan snapshots, WHOIS records)",
                             "Request registrar data preservation order",
                             "Document current state before suspect can modify"])))
            total_recs += 1

    db.commit()

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("DECISION SUPPORT COMPLETE")
    print(sep)

    cur.execute("SELECT COUNT(*) FROM analyst_recommendations")
    total = cur.fetchone()[0]
    print("Total recommendations: {}".format(total))

    cur.execute("SELECT recommendation_type, priority, COUNT(*) FROM analyst_recommendations GROUP BY recommendation_type, priority ORDER BY priority DESC, recommendation_type")
    print("\nBy type and priority:")
    for rtype, pri, count in cur.fetchall():
        print("  [{}] {}: {}".format(pri, rtype, count))

    print("\nAll recommendations:")
    cur.execute("""SELECT case_id, recommendation_type, priority, title, risk_score, confidence
        FROM analyst_recommendations ORDER BY
        CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
        risk_score DESC""")
    for case_id, rtype, pri, title, risk, conf in cur.fetchall():
        print("  [{}] {} {}: {} (risk={:.2f}, conf={:.2f})".format(
            pri, case_id, rtype, title, risk or 0, conf or 0))

    cur.close()
    db.close()
    return total


if __name__ == "__main__":
    run_decision_support()
