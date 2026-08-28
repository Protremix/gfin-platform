#!/usr/bin/env python3
"""
GFIN Unified Taxonomy Engine v1.0
Aligns scam type classifications across all GFIN modules.

Before: 5 different naming conventions for the same scam types:
- Scam Engine v3: INVESTMENT_FRAUD, CRYPTO_FRAUD, BRAND_IMPERSONATION (snake_case)
- Telegram Intel: ADVANCE_FEE, IMPERSONATION, INVESTMENT_FRAUD (snake_case, fewer types)
- Victim Complaints: "Investment Fraud", "Recovery Scam", "investment_fraud" (mixed case!)
- Scam Websites: IMPERSONATION, INVESTMENT_FRAUD, RECOVERY_SCAM, Unknown
- Police Pipeline: "Advance Fee Fraud", "Investment Fraud / Wire Fraud" (Title Case)

After: One canonical taxonomy. All modules use the same types.
"""
import sys
import json
import re
from collections import defaultdict

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

# ============================================================
# UNIFIED TAXONOMY — the canonical scam types for GFIN
# ============================================================
UNIFIED_TAXONOMY = {
    "INVESTMENT_FRAUD": {
        "canonical": "INVESTMENT_FRAUD",
        "description": "Fraudulent investment platforms, fake trading, forex/crypto investment scams",
        "aliases": [
            "investment_fraud", "Investment Fraud", "Investment Fraud / Wire Fraud",
            "INVESTMENT_FRAUD", "CRYPTO_FRAUD", "PAYMENT_FRAUD", "forex scam",
            "crypto scam", "trading scam", "Ponzi scheme",
        ],
        "severity": "HIGH",
        "common_indicators": ["guaranteed returns", "trading platform", "deposit required", "withdrawal blocked"],
    },
    "RECOVERY_SCAM": {
        "canonical": "RECOVERY_SCAM",
        "description": "Scammers claiming to recover lost funds for victims of previous scams",
        "aliases": [
            "RECOVERY_SCAM", "Recovery Scam", "recovery_scam",
            "fund recovery", "chargeback scam", "hack recovery",
        ],
        "severity": "HIGH",
        "common_indicators": ["recover your funds", "hack and recover", "chargeback", "I can help you get your money back"],
    },
    "JOB_SCAM": {
        "canonical": "JOB_SCAM",
        "description": "Fake job offers, recruitment fraud, human trafficking via employment",
        "aliases": [
            "JOB_SCAM", "Job Scam", "job_scam",
            "recruitment fraud", "employment scam", "human trafficking recruitment",
            "forex job", "call center recruitment", "work from home scam",
        ],
        "severity": "CRITICAL",
        "common_indicators": ["easy money", "work from home", "crypto job", "forex job", "relocation package", "retention bonus"],
    },
    "IMPERSONATION": {
        "canonical": "IMPERSONATION",
        "description": "Impersonating legitimate brands, government agencies, or known companies",
        "aliases": [
            "IMPERSONATION", "BRAND_IMPERSONATION", "Impersonation",
            "Criminal Impersonation / Identity Fraud",
            "identity fraud", "brand impersonation",
        ],
        "severity": "HIGH",
        "common_indicators": ["official sounding name", "fake agency", "clone website", "impersonating government"],
    },
    "PHISHING": {
        "canonical": "PHISHING",
        "description": "Credential theft via fake login pages, fake verification, account takeover",
        "aliases": [
            "PHISHING", "Phishing", "phishing",
            "credential theft", "account takeover", "fake login",
        ],
        "severity": "MEDIUM",
        "common_indicators": ["verify your account", "login page", "enter password", "confirm identity"],
    },
    "ADVANCE_FEE": {
        "canonical": "ADVANCE_FEE",
        "description": "Requesting upfront payment for promised services that never materialize",
        "aliases": [
            "ADVANCE_FEE", "Advance Fee Fraud", "advance_fee",
            "upfront payment", "processing fee", "release fee",
        ],
        "severity": "HIGH",
        "common_indicators": ["pay first", "processing fee", "release fee", "upfront payment required"],
    },
    "ROMANCE_SCAM": {
        "canonical": "ROMANCE_SCAM",
        "description": "Emotional manipulation via fake romantic relationships for financial gain",
        "aliases": [
            "ROMANCE_SCAM", "Romance Scam", "romance_scam",
            "dating scam", "catfishing",
        ],
        "severity": "HIGH",
        "common_indicators": ["love confession", "video call refusal", "emergency money request", "military romance"],
    },
    "SOCIAL_ENGINEERING": {
        "canonical": "SOCIAL_ENGINEERING",
        "description": "Manipulation tactics exploiting trust, urgency, or authority",
        "aliases": [
            "SOCIAL_ENGINEERING", "Social Engineering", "social_engineering",
            "URGENCY", "AUTHORITY_CLAIM", "SCARCITY", "SOCIAL_PROOF",
        ],
        "severity": "MEDIUM",
        "common_indicators": ["act now", "limited time", "official request", "everyone is doing it"],
    },
    "MONEY_LAUNDERING": {
        "canonical": "MONEY_LAUNDERING",
        "description": "Services for converting, transferring, or cleaning illicit funds",
        "aliases": [
            "MONEY_LAUNDERING", "Money Laundering", "money_laundering",
            "USDT supplier", "flash crypto", "fund conversion", "crypto cleaning",
        ],
        "severity": "CRITICAL",
        "common_indicators": ["USDT supplier", "accept various funds", "global accounts", "flash crypto", "transferable flash coin"],
    },
    "TECH_SUPPORT_SCAM": {
        "canonical": "TECH_SUPPORT_SCAM",
        "description": "Fake tech support claiming computer is infected or needs repair",
        "aliases": [
            "TECH_SUPPORT_SCAM", "Tech Support Scam", "tech_support_scam",
            "Microsoft support", "virus removal",
        ],
        "severity": "MEDIUM",
        "common_indicators": ["your computer is infected", "Microsoft support", "remote access"],
    },
    "LOTTERY_SCAM": {
        "canonical": "LOTTERY_SCAM",
        "description": "Fake lottery or prize notification requiring fees to claim winnings",
        "aliases": [
            "LOTTERY_SCAM", "Lottery Scam", "lottery_scam",
            "prize notification", "sweepstakes",
        ],
        "severity": "MEDIUM",
        "common_indicators": ["you won", "claim your prize", "processing fee for winnings"],
    },
    "UNKNOWN": {
        "canonical": "UNKNOWN",
        "description": "Unclassified or insufficient evidence to categorize",
        "aliases": ["Unknown", "unknown", "UNKNOWN", "", None],
        "severity": "LOW",
        "common_indicators": [],
    },
}

# Build reverse lookup: alias -> canonical
ALIAS_MAP = {}
for canonical, info in UNIFIED_TAXONOMY.items():
    for alias in info["aliases"]:
        ALIAS_MAP[str(alias).lower().strip()] = canonical
    ALIAS_MAP[canonical.lower()] = canonical


def normalize_scam_type(raw_type):
    """Convert any scam type variant to the canonical type."""
    if not raw_type:
        return "UNKNOWN"
    raw_lower = raw_type.lower().strip()
    if raw_lower in ALIAS_MAP:
        return ALIAS_MAP[raw_lower]
    # Try partial match
    for alias, canonical in ALIAS_MAP.items():
        if alias in raw_lower or raw_lower in alias:
            return canonical
    # If it contains "investment" or "trading" or "forex" or "crypto"
    if any(w in raw_lower for w in ["invest", "trad", "forex", "crypto", "ponzi"]):
        return "INVESTMENT_FRAUD"
    if any(w in raw_lower for w in ["recover", "chargeback", "hack"]):
        return "RECOVERY_SCAM"
    if any(w in raw_lower for w in ["job", "recruit", "employ", "work from", "traffick"]):
        return "JOB_SCAM"
    if any(w in raw_lower for w in ["imperson", "brand", "identity"]):
        return "IMPERSONATION"
    if any(w in raw_lower for w in ["phish", "credential", "login"]):
        return "PHISHING"
    if any(w in raw_lower for w in ["advance", "upfront", "processing fee"]):
        return "ADVANCE_FEE"
    if any(w in raw_lower for w in ["romance", "dating", "catfish"]):
        return "ROMANCE_SCAM"
    if any(w in raw_lower for w in ["launder", "usdt supplier", "flash"]):
        return "MONEY_LAUNDERING"
    return "UNKNOWN"


def run_taxonomy_alignment():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN UNIFIED TAXONOMY ENGINE v1.0")
    print("Aligning scam types across all modules")
    print(sep)

    print("\nCanonical taxonomy: {} types".format(len(UNIFIED_TAXONOMY)))
    for t, info in UNIFIED_TAXONOMY.items():
        print("  {} [{}] - {} aliases".format(t, info["severity"], len(info["aliases"])))

    # ============================================================
    # 1. ALIGN TELEGRAM INTELLIGENCE
    # ============================================================
    print("\n--- 1. ALIGNING TELEGRAM INTELLIGENCE ---")

    cur.execute("SELECT DISTINCT scam_type FROM telegram_intelligence")
    tg_types = [row[0] for row in cur.fetchall()]
    print("Current types: {}".format(tg_types))

    updates = 0
    for raw_type in tg_types:
        canonical = normalize_scam_type(raw_type)
        if canonical != raw_type:
            cur.execute("UPDATE telegram_intelligence SET scam_type = %s WHERE scam_type = %s",
                        (canonical, raw_type))
            count = cur.rowcount
            print("  {} -> {} ({} records)".format(raw_type, canonical, count))
            updates += count

    # Add new types that don't exist in Telegram yet
    # Check for MONEY_LAUNDERING patterns in messages
    cur.execute("""
        SELECT id, message_text FROM telegram_intelligence
        WHERE scam_type = 'INVESTMENT_FRAUD'
        AND (message_text ILIKE '%USDT supplier%' OR message_text ILIKE '%flash%crypto%'
             OR message_text ILIKE '%accept various funds%' OR message_text ILIKE '%global accounts%')
    """)
    laundering_msgs = cur.fetchall()
    for msg_id, text in laundering_msgs:
        cur.execute("UPDATE telegram_intelligence SET scam_type = 'MONEY_LAUNDERING' WHERE id = %s", (msg_id,))
        updates += 1
    if laundering_msgs:
        print("  Reclassified {} messages as MONEY_LAUNDERING".format(len(laundering_msgs)))

    # Check for JOB_SCAM patterns
    cur.execute("""
        SELECT id, message_text FROM telegram_intelligence
        WHERE scam_type = 'INVESTMENT_FRAUD'
        AND (message_text ILIKE '%recruit%' OR message_text ILIKE '%job%' OR message_text ILIKE '%hiring%'
             OR message_text ILIKE '%career%' OR message_text ILIKE '%work from home%'
             OR message_text ILIKE '%retention%' OR message_text ILIKE '%relocation%')
    """)
    job_msgs = cur.fetchall()
    for msg_id, text in job_msgs:
        cur.execute("UPDATE telegram_intelligence SET scam_type = 'JOB_SCAM' WHERE id = %s", (msg_id,))
        updates += 1
    if job_msgs:
        print("  Reclassified {} messages as JOB_SCAM".format(len(job_msgs)))

    # ============================================================
    # 2. ALIGN VICTIM COMPLAINTS
    # ============================================================
    print("\n--- 2. ALIGNING VICTIM COMPLAINTS ---")

    cur.execute("SELECT DISTINCT scam_type FROM victim_complaints")
    vc_types = [row[0] for row in cur.fetchall()]
    print("Current types: {}".format(vc_types))

    for raw_type in vc_types:
        canonical = normalize_scam_type(raw_type)
        if canonical != raw_type:
            cur.execute("UPDATE victim_complaints SET scam_type = %s WHERE scam_type = %s",
                        (canonical, raw_type))
            count = cur.rowcount
            print("  '{}' -> '{}' ({} records)".format(raw_type, canonical, count))
            updates += count

    # ============================================================
    # 3. ALIGN SCAM WEBSITES
    # ============================================================
    print("\n--- 3. ALIGNING SCAM WEBSITES ---")

    cur.execute("SELECT DISTINCT scam_type FROM scam_websites")
    sw_types = [row[0] for row in cur.fetchall()]
    print("Current types: {}".format(sw_types))

    for raw_type in sw_types:
        canonical = normalize_scam_type(raw_type)
        if canonical != raw_type:
            cur.execute("UPDATE scam_websites SET scam_type = %s WHERE scam_type = %s",
                        (canonical, raw_type))
            count = cur.rowcount
            print("  {} -> {} ({} records)".format(raw_type, canonical, count))
            updates += count

    # ============================================================
    # 4. ALIGN INVESTIGATION STEPS (Police Pipeline)
    # ============================================================
    print("\n--- 4. ALIGNING INVESTIGATION STEP CRIME TYPES ---")

    cur.execute("""
        SELECT id, result::text FROM investigation_steps
        WHERE step_name LIKE '5.%%' AND status = 'COMPLETED'
    """)
    steps = cur.fetchall()
    print("Investigation steps to check: {}".format(len(steps)))

    for step_id, result_text in steps:
        try:
            result = json.loads(result_text) if isinstance(result_text, str) else result_text
            crime = result.get("primary_crime", "")
            if crime:
                canonical = normalize_scam_type(crime)
                if canonical != crime and canonical != "UNKNOWN":
                    result["primary_crime"] = canonical
                    result["original_crime"] = crime
                    cur.execute("UPDATE investigation_steps SET result = %s WHERE id = %s",
                                (json.dumps(result), step_id))
                    print("  '{}' -> '{}'".format(crime, canonical))
                    updates += 1
        except:
            pass

    # ============================================================
    # 5. ALIGN COMPLAINT TABLE
    # ============================================================
    print("\n--- 5. ALIGNING COMPLAINTS ---")

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'complaints' AND column_name = 'scam_type'")
    if cur.fetchone():
        cur.execute("SELECT DISTINCT scam_type FROM complaints")
        cp_types = [row[0] for row in cur.fetchall()]
        print("Current types: {}".format(cp_types))
        for raw_type in cp_types:
            canonical = normalize_scam_type(raw_type)
            if canonical != raw_type:
                cur.execute("UPDATE complaints SET scam_type = %s WHERE scam_type = %s",
                            (canonical, raw_type))
                count = cur.rowcount
                print("  {} -> {} ({} records)".format(raw_type, canonical, count))
                updates += count
    else:
        print("  Complaints table has no scam_type column")

    db.commit()

    # ============================================================
    # 6. CREATE TAXONOMY MAPPING TABLE
    # ============================================================
    print("\n--- 6. CREATING TAXONOMY MAPPING TABLE ---")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS taxonomy_mapping (
            canonical_type VARCHAR(100) PRIMARY KEY,
            description TEXT,
            severity VARCHAR(20),
            aliases JSONB,
            common_indicators JSONB
        )
    """)
    cur.execute("TRUNCATE taxonomy_mapping")

    for canonical, info in UNIFIED_TAXONOMY.items():
        cur.execute("""INSERT INTO taxonomy_mapping
            (canonical_type, description, severity, aliases, common_indicators)
            VALUES (%s, %s, %s, %s, %s)""",
            (canonical, info["description"], info["severity"],
             json.dumps(info["aliases"]), json.dumps(info["common_indicators"])))

    db.commit()

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("TAXONOMY ALIGNMENT COMPLETE")
    print(sep)
    print("Total records updated: {}".format(updates))

    # Verify alignment
    print("\n--- VERIFICATION ---")
    for table in ["telegram_intelligence", "victim_complaints", "scam_websites"]:
        cur.execute("SELECT DISTINCT scam_type FROM {} ORDER BY scam_type".format(table))
        types = [row[0] for row in cur.fetchall()]
        unknown = [t for t in types if t and normalize_scam_type(t) == "UNKNOWN" and t != "UNKNOWN"]
        status = "ALIGNED" if not unknown else "NEEDS REVIEW: {}".format(unknown)
        print("  {}: {} types - {}".format(table, len(types), status))
        for t in types:
            print("    - {}".format(t))

    cur.close()
    db.close()
    return updates


if __name__ == "__main__":
    run_taxonomy_alignment()
