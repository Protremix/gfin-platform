#!/usr/bin/env python3
"""Fix MIDAS endpoints to return JSON-serializable types"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Fix internal endpoint
old_internal = '''    result = midas_pipeline.midas.add_edge(src, dst)
    return result

@app.post("/api/midas/edge")'''

new_internal = '''    result = midas_pipeline.midas.add_edge(src, dst)
    # Convert numpy types to native Python for JSON serialization
    if isinstance(result, dict):
        result = {k: bool(v) if hasattr(v, 'item') else v for k, v in result.items()}
    return result

@app.post("/api/midas/edge")'''

if old_internal in code:
    code = code.replace(old_internal, new_internal, 1)
    print("Fixed internal endpoint")
else:
    print("Internal endpoint block not found")

# Fix the authenticated endpoint too
old_auth = """    result = midas_pipeline.midas.add_edge(src, dst)
    return result

@app.get("/api/midas/status")"""

new_auth = """    result = midas_pipeline.midas.add_edge(src, dst)
    if isinstance(result, dict):
        result = {k: bool(v) if hasattr(v, 'item') else v for k, v in result.items()}
    return result

@app.get("/api/midas/status")"""

if old_auth in code:
    code = code.replace(old_auth, new_auth, 1)
    print("Fixed authenticated endpoint")
else:
    print("Auth endpoint block not found")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print("Done")
