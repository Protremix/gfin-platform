import psycopg2, json
conn = psycopg2.connect("dbname=gfin user=gfin password=GfinSecure2026! host=localhost")
cur = conn.cursor()

# Check the 4 test cases
cur.execute("SELECT case_id, target, target_type, trigger, summary, evidence_chain, scam_indicators, scam_patterns, victim_count, victim_loss FROM cases WHERE case_id LIKE 'GFIN-AUTO-1787814%' OR case_id LIKE 'GFIN-AUTO-1787811%' ORDER BY created_date DESC")
cols = [d[0] for d in cur.description]
for row in cur.fetchall():
    case = dict(zip(cols, row))
    ev = case.get('evidence_chain', [])
    if isinstance(ev, str):
        try: ev = json.loads(ev)
        except: ev = []
    
    print(f"\n[{case['case_id']}]")
    print(f"  Target: {case['target']}")
    print(f"  Trigger: {case['trigger']}")
    print(f"  Victims: {case['victim_count']}, Loss: {case['victim_loss']}")
    print(f"  Evidence: {len(ev)} items")
    print(f"  Summary: {(case.get('summary') or 'NONE')[:200]}")
    
    # Is this a real investigation or test?
    target = case.get('target', '').lower()
    is_test = any(t in target for t in ['test', 'evil-phishing', 'api-test', 'scam-test', 'example'])
    print(f"  TEST DATA: {is_test}")

cur.close()
conn.close()
