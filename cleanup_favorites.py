#!/usr/bin/env python3
"""Remove duplicate favorites API that was added with wrong auth pattern (psycopg2 vs asyncpg)"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Find and remove the duplicate favorites API block
# It starts with "# === FAVORITE CASES API ===" and ends before "# === OSINT" or "if __name__"
marker_start = "# === FAVORITE CASES API ==="
if marker_start in code:
    # Find the end — either "# === OSINT" or "if __name__"
    idx_start = code.index(marker_start)
    # Find the next section marker after it
    remaining = code[idx_start:]
    
    possible_ends = ["# === OSINT", "if __name__", "\n\n\n# ==="]
    end_idx = len(remaining)
    for pe in possible_ends:
        pos = remaining.find(pe, len(marker_start) + 10)
        if pos > 0 and pos < end_idx:
            end_idx = pos
    
    duplicate_block = remaining[:end_idx]
    code = code[:idx_start] + code[idx_start + end_idx:]
    print(f"Removed {len(duplicate_block)} chars of duplicate favorites API")
else:
    print("No duplicate favorites API found")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print("Server cleaned up")
