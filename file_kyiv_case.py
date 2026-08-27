#!/usr/bin/env python3
"""File GFIN case for the Kyiv scam call center recruitment operation."""
import psycopg2, secrets, hashlib

conn = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!", port=5432)
cur = conn.cursor()

# Register intelligence reporter
email = "intel-kyiv-callcenter@gfin-spy.local"
pwd_hash = hashlib.sha256(secrets.token_hex(8).encode()).hexdigest()
cur.execute(
    "INSERT INTO victims (email, name, password_hash, country, phone) VALUES (%s, %s, %s, %s, %s) RETURNING id",
    (email, "GFIN Intel — Kyiv Call Center Operation", pwd_hash, "UA", "")
)
victim_id = cur.fetchone()[0]
ref = f"GFIN-2026-{secrets.token_hex(4).upper()}"

description = """AUTOMATED INTELLIGENCE REPORT — SCAM CALL CENTER RECRUITMENT

GROUP: ВАКАНСИИ • CRYPTO - FOREX (t.me/work_crypto_fx)
Group ID: -1002978302504
Messages analyzed: 121 (all from group admin account)
Status: ACTIVE RECRUITMENT

OPERATION LOCATION: KYIV, UKRAINE
RECRUITER: @Kira13MK (Telegram)
PHONE: +380 966 344 929 (Ukraine, Kyiv)

POSITIONS BEING RECRUITED:
1. RETENTION MANAGER (ENG DESK) — $2000-3000/month + 7-14% bonuses
   - Targets: USA ("Гео: Юса")
   - Hours: 14:00-23:00 Kyiv time (= 7am-10am EST, US business hours)
   - English B2 required
   - Duties: "Звонки клиентам" (calls to clients/victims), CRM management, "Сопровождение клиента на всех этапах" (accompanying client at all stages = preventing withdrawal)

2. RETENTION MANAGER CHARGE (ENG DESK) — $1300/month + 8-15% bonuses
   - Targets: USA ("Гео: ENG USA")
   - Hours: 20:00-05:00 or 16:00-23:00 (night shift = US daytime)
   - Age requirement: 18-35 years
   - Duties: Calls to victims, CRM, victim retention through all stages

3. SALES MANAGER (RU DESK) — $1000-1500/month + bonuses
   - Targets: Russian speakers ("Гео: РУ РУ")
   - Hours: 09:00-18:00
   - "Quality traffic" provided (victim leads supplied)

4. SALES MANAGER CRYPTO (RU DESK) — $1000-1200/month + bonuses
   - Targets: Russian speakers
   - Hours: 09:00-18:00
   - Duties: "Доведение клиента до сделки" (bringing client to deal = convincing victim to deposit)

ANALYSIS:
- "Retention Manager" = person who prevents scam victims from withdrawing their money
- "Sales Manager" = person who cold-calls victims to deposit into fake trading platforms
- "Quality traffic" = victim lead data provided to workers
- "CRM" = system for tracking victim interactions and maximizing deposits
- All positions based in KYIV, UKRAINE
- ENG desk targets USA victims (hours aligned with US timezone)
- RU desk targets Russian-speaking victims
- Age restriction 18-35 suggests preference for young, trainable operators

KEY IDENTIFIERS:
- Recruiter Telegram: @Kira13MK
- Phone: +380 966 344 929 (Kyiv, Ukraine)
- Location: Kyiv, Ukraine
- Group: t.me/work_crypto_fx (121 recruitment messages)

CLASSIFICATION: ORGANIZED FRAUD — SCAM CALL CENTER OPERATION
RISK LEVEL: HIGH
COUNTRY: Ukraine (operation), USA (primary victim target), Russia (secondary target)
SOURCE: GFIN Telegram Spy (autonomous surveillance)"""

cur.execute(
    """INSERT INTO victim_complaints 
       (reference_number, victim_id, scam_type, target, incident_date, financial_loss, description, country, investigation_stage)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'RECEIVED')""",
    (ref, victim_id, "Investment Fraud", "Kyiv scam call center — t.me/work_crypto_fx, @Kira13MK, +380966344929",
     "2026-08-27", "Unknown — operational intelligence", description, "UA")
)

cur.execute(
    "INSERT INTO audit_log (action, actor, tool, query, result) VALUES (%s, %s, %s, %s, %s)",
    ("INTEL_CASE_FILED", "telegram_spy:autonomous", "telegram_intel_pipeline",
     "t.me/work_crypto_fx @Kira13MK +380966344929", f"Ref: {ref}, Type: Investment Fraud, Operation: Kyiv scam call center")
)

conn.commit()
conn.close()

print(f"CASE FILED: {ref}")
print(f"Target: Kyiv scam call center recruitment operation")
print(f"Recruiter: @Kira13MK (+380 966 344 929)")
print(f"Location: Kyiv, Ukraine")
print(f"Positions: Retention Manager (ENG/RU), Sales Manager (ENG/RU)")
print(f"Victims targeted: USA (ENG desk), Russian speakers (RU desk)")
