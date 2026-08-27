#!/usr/bin/env python3
"""Fix wallet anomaly query — don't GROUP BY JSON column"""

with open("/gfin/gfin_anomaly_detector.py", "r") as f:
    code = f.read()

# Find and replace the wallet query section
old_block_start = "            # Get wallet data from telegram_intelligence"
old_block_end = "            LIMIT 500\n            \"\"\")"

idx_start = code.find(old_block_start)
if idx_start >= 0:
    idx_end = code.find(old_block_end, idx_start)
    if idx_end >= 0:
        idx_end = code.find("\n", idx_end + len(old_block_end)) + 1
        
        new_query = """            # Get wallet data from telegram_intelligence
            rows = await conn.fetch(\"\"\"
                SELECT group_name, wallets, scam_type, risk_level, created_at
                FROM telegram_intelligence
                WHERE wallets IS NOT NULL AND wallets != '' AND wallets != '[]'
                LIMIT 500
            \"\"\")
"""
        code = code[:idx_start] + new_query + code[idx_end:]
        print("Fixed wallet query")
    else:
        print("Could not find end of wallet query")
else:
    print("Could not find start of wallet query")

with open("/gfin/gfin_anomaly_detector.py", "w") as f:
    f.write(code)
print("Done")
