#!/usr/bin/env python3
"""Fix truncated string in gfin_server.py"""
import sys

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Fix the truncated string
old = 'return {"status": "error", "messa\n# ==================== CASE FAVORITES API'
new = 'return {"status": "error", "message": str(e)}\n\n# ==================== CASE FAVORITES API'
content = content.replace(old, new)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Fixed truncated string")
