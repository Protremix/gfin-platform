import psycopg2, json
conn = psycopg2.connect("dbname=gfin user=gfin password=GfinSecure2026! host=localhost")
cur = conn.cursor()

# Get columns of cases table
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='cases' ORDER BY ordinal_position")
cols_list = [r[0] for r in cur.fetchall()]
print("CASES TABLE COLUMNS:", cols_list)
print("=" * 80)

# Get all cases
cur.execute("SELECT * FROM cases ORDER BY created_date DESC")
cols = [d[0] for d in cur.description]
rows = cur.fetchall()

print(f"TOTAL CASES: {len(rows)}")
print("=" * 80)

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
    
    case_id = case.get('case_id', 'NO ID')
    target = case.get('target', 'NONE')
    target_type = case.get('target_type', 'NONE')
    status = case.get('status', 'NONE')
    confidence = case.get('confidence', 'NONE')
    summary = (case.get('summary') or 'NONE')[:120]
    victim_count = case.get('victim_count', 0)
    victim_loss = case.get('victim_loss', 0)
    
    print(f"\n[{case_id}]")
    print(f"  Target: {target}")
    print(f"  Type: {target_type}")
    print(f"  Status: {status}")
    print(f"  Confidence: {confidence}")
    print(f"  Evidence items: {ev_count}")
    print(f"  Scam indicators: {ind_count}")
    print(f"  Victims: {victim_count}, Loss: {victim_loss}")
    print(f"  Summary: {summary}")
    
    if ev_count > 0:
        ev_types = []
        for e in evidence_chain[:5]:
            if isinstance(e, dict):
                ev_types.append(e.get('type', e.get('step', '?')))
            else:
                ev_types.append(str(e)[:30])
        print(f"  Evidence: {ev_types}")
    
    # Classify
    has_real_evidence = ev_count >= 3
    has_investigation = ev_count >= 3 and ind_count >= 3
    is_just_domain = target_type in ['DOMAIN', 'URL'] and ev_count < 3
    
    if has_investigation:
        verdict = "REAL CASE - KEEP"
    elif is_just_domain:
        verdict = "BARE DOMAIN - MOVE TO DOMAIN DB, DELETE FROM CASES"
    elif ev_count == 0:
        verdict = "NO EVIDENCE - DELETE"
    else:
        verdict = "WEAK CASE - REVIEW"
    
    print(f"  >> VERDICT: {verdict}")

cur.close()
conn.close()
