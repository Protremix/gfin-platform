"""
Clean up the cases table:
1. Move all bare-domain entries (0 victims, 0 scam_indicators) to tracked_domains table
2. Delete them from cases table
3. Only keep cases with real evidence (victims, scam indicators, or manual investigation)
"""
import psycopg2, json
from datetime import datetime, timezone

conn = psycopg2.connect("dbname=gfin user=gfin password= host=localhost")
cur = conn.cursor()

# Create tracked_domains table if it doesn't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS tracked_domains (
    id SERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    source TEXT,
    risk_level TEXT,
    risk_score INTEGER,
    confidence REAL,
    patterns TEXT[],
    evidence_summary TEXT,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_checked TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'TRACKED',
    created_date TIMESTAMP DEFAULT NOW()
)
""")
conn.commit()

# Get all cases
cur.execute("SELECT * FROM cases ORDER BY created_date DESC")
cols = [d[0] for d in cur.description]
rows = cur.fetchall()

real_cases = []
bare_domains = []

for row in rows:
    case = dict(zip(cols, row))
    
    evidence_chain = case.get('evidence_chain', [])
    if isinstance(evidence_chain, str):
        try:
            evidence_chain = json.loads(evidence_chain)
        except:
            evidence_chain = []
    
    scam_indicators = case.get('scam_indicators', [])
    if isinstance(scam_indicators, str):
        try:
            scam_indicators = json.loads(scam_indicators)
        except:
            scam_indicators = []
    
    ev_count = len(evidence_chain) if isinstance(evidence_chain, list) else 0
    ind_count = len(scam_indicators) if isinstance(scam_indicators, list) else 0
    victim_count = case.get('victim_count', 0) or 0
    
    # Real case = has victims OR has scam indicators OR has manual trigger
    trigger = case.get('trigger', '') or ''
    is_auto = 'OPENPHISH' in trigger or 'URLHAUS' in trigger or 'Autonomous' in trigger
    is_auto_domain = is_auto and case.get('target_type') == 'DOMAIN'
    
    has_victims = victim_count > 0
    has_indicators = ind_count > 0
    has_real_trigger = trigger in ['PUBLIC_REPORT', 'MANUAL', 'TELEGRAM_SURVEILLANCE', 'COMPLAINT']
    
    if is_auto_domain and not has_victims and not has_indicators:
        # This is a bare domain — move to tracked_domains
        bare_domains.append(case)
    else:
        real_cases.append(case)

print(f"REAL CASES (keeping): {len(real_cases)}")
for rc in real_cases:
    print(f"  - {rc.get('case_id')}: {rc.get('target', 'NONE')[:50]}")

print(f"\nBARE DOMAINS (moving to tracked_domains): {len(bare_domains)}")

# Move bare domains to tracked_domains
moved = 0
for bd in bare_domains:
    domain = bd.get('target', '')
    summary = bd.get('summary', '') or ''
    
    # Extract risk info from summary
    risk_level = 'UNKNOWN'
    risk_score = 0
    if 'CRITICAL' in summary:
        risk_level = 'CRITICAL'
        risk_score = 75
    elif 'HIGH' in summary:
        risk_level = 'HIGH'
        risk_score = 60
    elif 'MEDIUM' in summary:
        risk_level = 'MEDIUM'
        risk_score = 30
    elif 'MINIMAL' in summary:
        risk_level = 'MINIMAL'
        risk_score = 0
    
    # Extract patterns from summary
    patterns = []
    if 'CRYPTO_FRAUD' in summary:
        patterns.append('CRYPTO_FRAUD')
    if 'INVESTMENT_FRAUD' in summary:
        patterns.append('INVESTMENT_FRAUD')
    if 'BRAND_IMPERSONATION' in summary:
        patterns.append('BRAND_IMPERSONATION')
    
    source = 'URLHAUS' if 'URLHAUS' in summary else 'OPENPHISH' if 'OPENPHISH' in summary else 'AUTO'
    
    cur.execute("""
        INSERT INTO tracked_domains (domain, source, risk_level, risk_score, confidence, patterns, evidence_summary, first_seen, last_checked, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'TRACKED')
        ON CONFLICT DO NOTHING
    """, (
        domain,
        source,
        risk_level,
        risk_score,
        bd.get('confidence', 0),
        patterns,
        summary[:500],
        bd.get('created_date', datetime.now(timezone.utc)),
        bd.get('updated_date', datetime.now(timezone.utc))
    ))
    moved += 1

print(f"Moved {moved} domains to tracked_domains table")

# Delete bare domain cases from cases table
case_ids_to_delete = [bd.get('id') for bd in bare_domains]
if case_ids_to_delete:
    cur.execute("DELETE FROM cases WHERE id = ANY(%s)", (case_ids_to_delete,))
    print(f"Deleted {len(case_ids_to_delete)} bare-domain entries from cases table")

conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM cases")
remaining = cur.fetchone()[0]
print(f"\nRemaining cases in cases table: {remaining}")

cur.execute("SELECT COUNT(*) FROM tracked_domains")
tracked = cur.fetchone()[0]
print(f"Domains in tracked_domains table: {tracked}")

# Show what's left
cur.execute("SELECT case_id, target, target_type, victim_count, status FROM cases ORDER BY created_date DESC")
print("\nREMAINING CASES:")
for r in cur.fetchall():
    print(f"  - {r[0]}: {r[1][:50]} ({r[2]}) victims={r[3]} status={r[4]}")

cur.close()
conn.close()
