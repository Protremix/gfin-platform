#!/usr/bin/env python3
"""Move favorites routes before /api/cases/{case_id} to fix route ordering"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Extract the favorites block
fav_marker = "# ==================== CASE FAVORITES API ===================="
fav_end_marker = 'return {"is_favorite": row is not None}\n    except:\n        return {"is_favorite": False}\n'

fav_start_idx = content.index(fav_marker)
# Find the end of the favorites block - it's right before the graph stats
fav_end_idx = content.index("\n\n@app.get(\"/api/graph/stats\")", fav_start_idx)

fav_block = content[fav_start_idx:fav_end_idx]
# Remove the favorites block from its current position
content_no_fav = content[:fav_start_idx] + "\n" + content[fav_end_idx:]

# Find the insertion point - right before @app.get("/api/cases/{case_id}")
insert_marker = '@app.get("/api/cases/{case_id}")'
insert_idx = content_no_fav.index(insert_marker)

# Insert favorites block before the parameterized route
new_content = content_no_fav[:insert_idx] + fav_block + "\n\n" + content_no_fav[insert_idx:]

with open("/gfin/gfin_server.py", "w") as f:
    f.write(new_content)
print("Moved favorites routes before /api/cases/{case_id}")
