#!/usr/bin/env python3
"""
GFIN Victim Support Workflow Engine v1.0
Automates victim communication, status updates, and investigation triggers.
"""
import sys
import json
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

VICTIM_STAGE_MESSAGES = {
    "RECEIVED": {
        "title": "Complaint Received",
        "message": "Your complaint has been received and logged in our system. A case reference number has been assigned.",
        "eta": "Initial review within 48 hours",
    },
    "UNDER_REVIEW": {
        "title": "Under Review",
        "message": "Your case is being reviewed by our analysis team. We are gathering information about the reported entity.",
        "eta": "Analysis typically takes 5-10 business days",
    },
    "INVESTIGATING": {
        "title": "Investigation Active",
        "message": "An active investigation is underway. We are collecting evidence and working with relevant authorities.",
        "eta": "Investigations can take 30-90 days",
    },
    "EVIDENCE_COLLECTED": {
        "title": "Evidence Collected",
        "message": "We have collected sufficient evidence for your case. Preparing for referral to law enforcement.",
        "eta": "Referral preparation: 1-2 weeks",
    },
    "REFERRED": {
        "title": "Referred to Law Enforcement",
        "message": "Your case has been referred to the appropriate law enforcement agency.",
        "eta": "Law enforcement timeline varies by jurisdiction",
    },
    "CLOSED": {
        "title": "Case Closed",
        "message": "Your case has been closed. If you have new information, you can submit a new complaint.",
        "eta": "Case resolved",
    },
}


def run_victim_support():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN VICTIM SUPPORT WORKFLOW ENGINE v1.0")
    print("Processing victim complaints and generating updates")
    print(sep)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_updates (
            id SERIAL PRIMARY KEY,
            reference_number VARCHAR(100),
            stage VARCHAR(50),
            title TEXT,
            message TEXT,
            eta TEXT,
            created_date TIMESTAMP DEFAULT NOW(),
            victim_visible BOOLEAN DEFAULT true
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_timeline (
            id SERIAL PRIMARY KEY,
            reference_number VARCHAR(100),
            event_date TIMESTAMP,
            event_type VARCHAR(50),
            title TEXT,
            description TEXT,
            visible_to_victim BOOLEAN DEFAULT true
        )
    """)
    db.commit()

    # 1. AUTO-TRIGGER INVESTIGATIONS
    print("\n--- 1. AUTO-TRIGGERING INVESTIGATIONS ---")
    cur.execute("SELECT reference_number, scam_type, target, description, case_id FROM victim_complaints WHERE auto_investigation_started = false OR auto_investigation_started IS NULL")
    unstarted = cur.fetchall()
    print("Unstarted complaints: {}".format(len(unstarted)))

    triggered = 0
    for ref, scam_type, target, desc, case_id in unstarted:
        if not case_id:
            case_id = "GFIN-CASE-{}".format(ref.split("-")[-1][:6].upper())
            cur.execute("INSERT INTO cases (case_id, target, priority, confidence, status, created_date) VALUES (%s, %s, 'MEDIUM', 0.5, 'OPEN', NOW()) ON CONFLICT DO NOTHING", (case_id, target or "Unknown"))
            cur.execute("UPDATE victim_complaints SET case_id = %s WHERE reference_number = %s", (case_id, ref))

        cur.execute("UPDATE victim_complaints SET auto_investigation_started = true, investigation_stage = 'UNDER_REVIEW' WHERE reference_number = %s", (ref,))
        print("  Triggered: {} -> {} [{}]".format(ref, case_id, scam_type))
        triggered += 1

        steps = [
            ("1. Complaint Received", "COMPLETED", "Victim complaint logged"),
            ("2. Scam Analysis", "COMPLETED", "Scam type: {}".format(scam_type)),
            ("3. Entity Extraction", "COMPLETED", "Target: {}".format(target or "Unknown")),
            ("4. Country Routing", "IN_PROGRESS", "Determining jurisdiction"),
        ]
        for step_name, st, result in steps:
            cur.execute("INSERT INTO investigation_steps (case_id, phase, step_name, status, result, created_date) VALUES (%s, 'INTAKE', %s, %s, %s, NOW()) ON CONFLICT DO NOTHING", (case_id, step_name, st, json.dumps({"description": result})))

    db.commit()

    # 2. GENERATE VICTIM STATUS UPDATES
    print("\n--- 2. GENERATING VICTIM STATUS UPDATES ---")
    cur.execute("SELECT reference_number, investigation_stage, case_id FROM victim_complaints")
    all_complaints = cur.fetchall()

    updates_created = 0
    for ref, stage, case_id in all_complaints:
        stage = stage or "RECEIVED"
        if stage in VICTIM_STAGE_MESSAGES:
            msg = VICTIM_STAGE_MESSAGES[stage]
            cur.execute("SELECT 1 FROM victim_updates WHERE reference_number = %s AND stage = %s", (ref, stage))
            if not cur.fetchone():
                cur.execute("INSERT INTO victim_updates (reference_number, stage, title, message, eta, victim_visible) VALUES (%s, %s, %s, %s, %s, true)", (ref, stage, msg["title"], msg["message"], msg["eta"]))
                updates_created += 1
                print("  {} -> {} ({})".format(ref, stage, msg["title"]))
            cur.execute("INSERT INTO victim_timeline (reference_number, event_date, event_type, title, description, visible_to_victim) VALUES (%s, NOW(), %s, %s, %s, true) ON CONFLICT DO NOTHING", (ref, stage, msg["title"], msg["message"]))

    db.commit()
    print("Updates created: {}".format(updates_created))

    # 3. EVIDENCE-BASED UPDATES
    print("\n--- 3. EVIDENCE-BASED UPDATES ---")
    cur.execute("""
        SELECT v.reference_number, v.case_id, v.investigation_stage,
               (SELECT COUNT(*) FROM evidence e WHERE e.case_id = v.case_id) as evidence_count,
               (SELECT COUNT(*) FROM investigation_steps s WHERE s.case_id = v.case_id AND s.status = 'COMPLETED') as steps_done
        FROM victim_complaints v WHERE v.case_id IS NOT NULL
    """)
    for ref, case_id, stage, ev_count, steps_done in cur.fetchall():
        new_stage = stage or "RECEIVED"
        if ev_count >= 5 and steps_done >= 3:
            new_stage = "EVIDENCE_COLLECTED"
        elif steps_done >= 2:
            new_stage = "INVESTIGATING"
        elif steps_done >= 1:
            new_stage = "UNDER_REVIEW"

        if new_stage != stage:
            cur.execute("UPDATE victim_complaints SET investigation_stage = %s WHERE reference_number = %s", (new_stage, ref))
            if new_stage in VICTIM_STAGE_MESSAGES:
                msg = VICTIM_STAGE_MESSAGES[new_stage]
                cur.execute("SELECT 1 FROM victim_updates WHERE reference_number = %s AND stage = %s", (ref, new_stage))
                if not cur.fetchone():
                    cur.execute("INSERT INTO victim_updates (reference_number, stage, title, message, eta, victim_visible) VALUES (%s, %s, %s, %s, %s, true)", (ref, new_stage, msg["title"], msg["message"], msg["eta"]))
                    cur.execute("INSERT INTO victim_timeline (reference_number, event_date, event_type, title, description, visible_to_victim) VALUES (%s, NOW(), %s, %s, %s, true)", (ref, new_stage, msg["title"], msg["message"]))
                    print("  {} upgraded: {} -> {} (evidence={}, steps={})".format(ref, stage, new_stage, ev_count, steps_done))

    db.commit()

    # 4. NOTIFICATIONS
    print("\n--- 4. VICTIM NOTIFICATION MESSAGES ---")
    cur.execute("SELECT v.reference_number, v.scam_type, v.investigation_stage, v.case_id, v.target, (SELECT COUNT(*) FROM evidence e WHERE e.case_id = v.case_id) as evidence_count FROM victim_complaints v")
    notifications = []
    for ref, scam_type, stage, case_id, target, ev_count in cur.fetchall():
        stage = stage or "RECEIVED"
        msg_data = VICTIM_STAGE_MESSAGES.get(stage, VICTIM_STAGE_MESSAGES["RECEIVED"])
        notifications.append({
            "reference": ref, "scam_type": scam_type or "Unknown", "stage": stage,
            "title": msg_data["title"], "message": msg_data["message"], "eta": msg_data["eta"],
            "evidence_collected": ev_count, "case_active": case_id is not None,
        })

    print("Notifications generated: {}".format(len(notifications)))
    for n in notifications[:5]:
        print("  {}: {} [{}] - {} evidence items".format(n["reference"][:20], n["title"], n["scam_type"], n["evidence_collected"]))

    print("\n" + sep)
    print("VICTIM SUPPORT WORKFLOW COMPLETE")
    print(sep)
    print("Investigations triggered: {}".format(triggered))
    print("Status updates created: {}".format(updates_created))
    print("Notifications generated: {}".format(len(notifications)))

    cur.execute("SELECT reference_number, stage, title, created_date FROM victim_updates ORDER BY created_date DESC LIMIT 20")
    print("\nRecent victim updates:")
    for ref, stage, title, created in cur.fetchall():
        print("  {} [{}] {} ({})".format(ref[:20], stage, title, created.strftime("%Y-%m-%d %H:%M")))

    cur.execute("SELECT investigation_stage, COUNT(*) FROM victim_complaints GROUP BY investigation_stage ORDER BY investigation_stage")
    print("\nComplaint stage distribution:")
    for stage, count in cur.fetchall():
        print("  {}: {}".format(stage, count))

    cur.close()
    db.close()
    return triggered + updates_created


if __name__ == "__main__":
    run_victim_support()
