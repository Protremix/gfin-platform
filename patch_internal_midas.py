#!/usr/bin/env python3
"""Add internal MIDAS edge endpoint (localhost only, no auth) to gfin_server.py"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Add internal endpoint right before the existing /api/midas/edge
marker = '@app.post("/api/midas/edge")'
if marker in code and "/api/midas/internal/edge" not in code:
    internal_ep = '''@app.post("/api/midas/internal/edge")
async def midas_add_edge_internal(request: Request):
    """Internal endpoint for spy/monitor to stream edges (localhost only, no auth)"""
    client_ip = request.client.host if request.client else ""
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"error": "Internal only"})
    body = await request.json()
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        return {"error": "src and dst required"}
    result = midas_pipeline.midas.add_edge(src, dst)
    return result

'''
    code = code.replace(marker, internal_ep + marker, 1)
    with open("/gfin/gfin_server.py", "w") as f:
        f.write(code)
    print("Added internal MIDAS edge endpoint")
else:
    print("Internal endpoint already present or marker not found")

# Also update the spy to use the internal endpoint
with open("/gfin/telegram_spy.py", "r") as f:
    spy_code = f.read()

# Replace /api/midas/edge with /api/midas/internal/edge in the spy
spy_code = spy_code.replace("/api/midas/edge", "/api/midas/internal/edge")

with open("/gfin/telegram_spy.py", "w") as f:
    f.write(spy_code)
print("Updated spy to use internal endpoint")
