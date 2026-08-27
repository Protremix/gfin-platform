#!/usr/bin/env python3
"""Fix dangling fragment in gfin_server.py"""
with open("/gfin/gfin_server.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == 'ge": str(e)}':
        continue
    new_lines.append(line)

with open("/gfin/gfin_server.py", "w") as f:
    f.writelines(new_lines)
print("Removed dangling fragment")
