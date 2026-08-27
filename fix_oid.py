#!/usr/bin/env python3
"""Fix officer_id -> oid in favorites code"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Replace officer_id extraction in favorites code
content = content.replace(
    'officer_id = payload.get("officer_id")',
    'officer_id = payload.get("oid") or payload.get("officer_id")'
)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Fixed officer_id -> oid")
