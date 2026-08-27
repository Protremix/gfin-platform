#!/usr/bin/env python3
"""Fix the duplicate /case route and add auth check."""

with open("/gfin/gfin_server.py", "r") as f:
    lines = f.readlines()

# Find the SECOND @app.get("/case" route and remove it (and following lines)
new_lines = []
skip_next = 0
found_first = False
for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    if "@app.get(\"/case\", response_class=HTMLResponse)" in line:
        if found_first:
            # This is the second one — skip it and next 3 lines
            skip_next = 3
            continue
        found_first = True
    new_lines.append(line)

# Now add auth to the first /case route
content = "".join(new_lines)
old = """@app.get("/case", response_class=HTMLResponse)
def case_detail_page():
    with open("/gfin/web/case_detail.html") as f:
        return HTMLResponse(f.read())"""

new = """@app.get("/case", response_class=HTMLResponse)
async def case_detail_page(request: Request):
    if _police_auth:
        from urllib.parse import unquote
        token = unquote(request.cookies.get("gfin_police_token", ""))
        if not token:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
    with open("/gfin/web/case_detail.html") as f:
        return HTMLResponse(f.read())"""

content = content.replace(old, new)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Fixed — duplicate removed, auth added")
