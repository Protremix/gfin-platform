"""
1. Delete test cases from cases table
2. Fix auto-investigation pipeline: domains go to tracked_domains, NOT cases
3. Only create a case when: real victim complaint with evidence, OR manual investigation, OR high-confidence scam with multiple indicators
"""
import psycopg2, json

conn = psycopg2.connect("dbname=gfin user=gfin password= host=localhost")
cur = conn.cursor()

# Delete the 4 test cases (keep only GFIN-CASE-001)
test_case_ids = [
    "GFIN-AUTO-1787814962",  # romance-scam-test.com — health check test
    "GFIN-AUTO-1787814892",  # crypto-invest-scam.com — API test
    "GFIN-AUTO-1787814721",  # api-test-scam.com — API test
    "GFIN-AUTO-1787811633",  # evil-phishing-site.com — test complaint
]

for case_id in test_case_ids:
    cur.execute("DELETE FROM cases WHERE case_id = %s", (case_id,))
    print(f"Deleted test case: {case_id}")

conn.commit()

# Verify what's left
cur.execute("SELECT case_id, target, target_type, victim_count, victim_loss, status FROM cases ORDER BY created_date DESC")
print("\nREMAINING CASES IN SERVER DB:")
for r in cur.fetchall():
    print(f"  - {r[0]}: {r[1]} ({r[2]}) victims={r[3]} loss={r[4]} status={r[5]}")

cur.execute("SELECT COUNT(*) FROM cases")
print(f"\nTotal real cases: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM tracked_domains")
print(f"Total tracked domains: {cur.fetchone()[0]}")

cur.close()
conn.close()
