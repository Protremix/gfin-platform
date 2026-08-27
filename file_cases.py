#!/usr/bin/env python3
"""File GFIN cases directly into the database from Telegram intelligence."""
import psycopg2, json, secrets, hashlib, time
from datetime import datetime, timezone

def get_db():
    return psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!", port=5432)

cases = [
    {
        "name": "Vlad — Organized Investment Fraud Network",
        "email": "intel-vlad@gfin-spy.local",
        "scam_type": "Investment Fraud",
        "target": "neex.com (promoted by Vlad across 4 Telegram scam groups)",
        "description": "AUTOMATED INTELLIGENCE REPORT\n\nTelegram user 'Vlad' posted 139 messages across 4 fraud-focused Telegram groups promoting investment fraud. Uses geographic targeting lists (Serbia, Greece, Albania, Ukraine, Dominican Republic, Ecuador) — likely recruitment for scam call centers. Cross-referenced with neex.com (forex trading platform, hosted on AWS CloudFront US). Pattern matches organized investment fraud operation.\n\nGroups active: Forex|Crypto|Jobs|Work, Crypto Forex Jobs, Forex|Crypto|Solutions|Affiliate|Jobs, Forex|Crypto|Jobs|Solutions\nScam classification: INVESTMENT_FRAUD\nRisk level: HIGH\nConfidence: MEDIUM\nSource: GFIN Telegram Spy (autonomous)",
        "country": "RS",
        "loss": "Unknown — operational intelligence",
    },
    {
        "name": "TFT-Evelyn — TeamForce Technologies (Cyprus)",
        "email": "intel-tft-evelyn@gfin-spy.local",
        "scam_type": "Investment Fraud",
        "target": "teamforcetechnologies.com (+357 9636 7698 Cyprus)",
        "description": "AUTOMATED INTELLIGENCE REPORT\n\nTelegram user 'TFT - Evelyn' posted 8 messages across 3 groups promoting teamforcetechnologies.com. Domain registered 2025-02-18, behind Cloudflare (hiding origin IP). LinkedIn: teamforcetechnologies. Phone: +357 9636 7698 (Cyprus). TeamForce Technologies appears to be a fraudulent forex/crypto jobs recruitment front.\n\nGroups active: Forex Jobs in Moldova, Forex|Crypto|Jobs|Work, Forex|Crypto|Solutions|Affiliate|Jobs\nDomain age: ~18 months\nHosting: Cloudflare (AS13335)\nScam classification: INVESTMENT_FRAUD\nRisk level: HIGH\nPhone: +357 9636 7698 (CYPRUS)\nSource: GFIN Telegram Spy (autonomous)",
        "country": "CY",
        "loss": "Unknown — operational intelligence",
    },
    {
        "name": "REVERSE ENGINEER — Scam Service Provider (Lead Extraction)",
        "email": "intel-reverse-eng@gfin-spy.local",
        "scam_type": "Recovery Scam",
        "target": "Telegram user 'REVERSE ENGINEER' — extraction services for scam operations",
        "description": "AUTOMATED INTELLIGENCE REPORT\n\nTelegram user 'REVERSE ENGINEER' posted 64 messages across 5 groups (highest cross-group presence). Advertising 'extraction services' — offering to extract leads/traffic from crypto, investment, and casino/gambling websites. This is a SERVICE PROVIDER to the scam ecosystem — providing infrastructure (lead databases, traffic extraction) that enables other scammers.\n\nGroups active: Crypto Forex Jobs, Forex Jobs in Moldova, Forex|Crypto|Jobs|Solutions, Forex|Crypto|Jobs|Work, Forex|Crypto|Solutions|Affiliate|Jobs\nScam classification: RECOVERY_SCAM\nRisk level: HIGH\nRole: SERVICE PROVIDER to scam ecosystem\nSource: GFIN Telegram Spy (autonomous)",
        "country": "GB",
        "loss": "Unknown — operational intelligence",
    },
    {
        "name": "Monde HR — Retention Agent Recruitment / Human Trafficking (Armenia)",
        "email": "intel-monde-hr@gfin-spy.local",
        "scam_type": "Recovery Scam",
        "target": "Telegram user 'Monde HR' — recruiting 'Retention Agents' for relocation to Armenia",
        "description": "AUTOMATED INTELLIGENCE REPORT — HUMAN TRAFFICKING INDICATOR\n\nTelegram user 'Monde HR' posted 11 messages across 3 groups recruiting 'Portuguese Retention Agents' and 'Spanish retention' agents for relocation to Armenia with 'full relocation package'. This is a RECRUITMENT operation for scam call centers — 'retention agents' are people who call scam victims and prevent them from withdrawing their money. The relocation to Armenia with full package is a HUMAN TRAFFICKING INDICATOR.\n\nGroups active: Forex Jobs in Moldova, Forex|Crypto|Jobs|Solutions, Forex|Crypto|Jobs|Work\nScam classification: RECOVERY_SCAM\nRisk level: HIGH\nHUMAN TRAFFICKING INDICATOR: YES\nTarget countries: Armenia (operation), Portugal/Spain (recruitment)\nSource: GFIN Telegram Spy (autonomous)",
        "country": "AM",
        "loss": "Unknown — operational intelligence",
    },
    {
        "name": "RS Database House — Victim Database Selling (US Phone)",
        "email": "intel-rs-database@gfin-spy.local",
        "scam_type": "Investment Fraud",
        "target": "Telegram user 'RS Database House' — selling victim databases (+1 440 589 8670)",
        "description": "AUTOMATED INTELLIGENCE REPORT\n\nTelegram user 'RS Database House' selling databases of leads/contacts for scam operations. Posted 10 messages across 2 groups. Uses US phone number +1 440 589 8670 and pm.me link. Promotes crypto.com. This is a DATA BROKER for the scam ecosystem — selling contact lists that enable other scammers to target victims.\n\nGroups active: Forex|Crypto|Solutions|Affiliate|Jobs, Forex|Crypto|Jobs|Solutions\nPhone: +1 440 589 8670 (USA)\nScam classification: INVESTMENT_FRAUD\nRisk level: HIGH\nRole: DATA BROKER for scam ecosystem\nSource: GFIN Telegram Spy (autonomous)",
        "country": "US",
        "loss": "Unknown — operational intelligence",
    },
    {
        "name": "Tati — FX Agent Recruitment / Relocation (Cyprus, Nigeria)",
        "email": "intel-tati@gfin-spy.local",
        "scam_type": "Recovery Scam",
        "target": "Telegram user '𝐓𝐚𝐭𝐢' — recruiting 'FX agents' with relocation to Cyprus and Nigeria",
        "description": "AUTOMATED INTELLIGENCE REPORT — HUMAN TRAFFICKING INDICATOR\n\nTelegram user '𝐓𝐚𝐭𝐢' posted 13 messages across 6 groups (highest group count). Hiring 'experienced FX agents with relocation support' to Cyprus and Nigeria. This is RECRUITMENT for scam call center operations. The relocation support across multiple countries is a HUMAN TRAFFICKING INDICATOR.\n\nGroups active: Crypto Forex Jobs, Forex Jobs in Moldova, Forex|Crypto|Jobs|Solutions, Forex|Crypto|Jobs|Work, Forex|Crypto|Solutions|Affiliate|Jobs, Работа FOREX RETENTION CONVERSION\nScam classification: RECOVERY_SCAM\nRisk level: HIGH\nHUMAN TRAFFICKING INDICATOR: YES\nTarget countries: Cyprus, Nigeria (operation); Worldwide (recruitment)\nSource: GFIN Telegram Spy (autonomous)",
        "country": "CY",
        "loss": "Unknown — operational intelligence",
    },
]

conn = get_db()
cur = conn.cursor()

filed = 0
for case in cases:
    # Register a victim/intelligence reporter
    pwd_hash = hashlib.sha256(secrets.token_hex(8).encode()).hexdigest()
    cur.execute(
        "INSERT INTO victims (email, name, password_hash, country, phone) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (case["email"].lower(), case["name"], pwd_hash, case["country"], "")
    )
    victim_id = cur.fetchone()[0]
    
    # Generate reference number
    ref = f"GFIN-2026-{secrets.token_hex(4).upper()}"
    
    # File complaint
    cur.execute(
        """INSERT INTO victim_complaints 
           (reference_number, victim_id, scam_type, target, incident_date, financial_loss, description, country, investigation_stage)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'RECEIVED')""",
        (ref, victim_id, case["scam_type"], case["target"], "2026-08-27", case["loss"], case["description"], case["country"])
    )
    
    # Log audit
    cur.execute(
        "INSERT INTO audit_log (action, actor, tool, query, result) VALUES (%s, %s, %s, %s, %s)",
        ("INTEL_CASE_FILED", f"telegram_spy:autonomous", "telegram_intel_pipeline",
         case["target"][:100], f"Ref: {ref}, Type: {case['scam_type']}")
    )
    
    print(f"  FILED: {ref} — {case['name']}")
    filed += 1

conn.commit()
conn.close()

print(f"\n{filed} GFIN intelligence cases filed successfully")
print("All cases will be auto-investigated by the GFIN pipeline")
