#!/usr/bin/env python3
"""Fix column names in favorites SQL queries"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Fix the SQL query in get_favorites
old_sql = """SELECT cf.case_id, cf.created_at as favorited_at,
                      c.title, c.status, c.confidence, c.priority, c.target,
                      c.scam_types, c.victim_count, c.total_loss"""

new_sql = """SELECT cf.case_id, cf.created_at as favorited_at,
                      c.summary as title, c.status, c.confidence, c.priority, c.target,
                      c.scam_patterns as scam_types, c.victim_count, c.total_loss_usd as total_loss"""

content = content.replace(old_sql, new_sql)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Fixed column names in favorites SQL")
