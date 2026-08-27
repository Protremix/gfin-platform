#!/usr/bin/env python3
"""Patch gfin_server.py to start MIDAS alert bridge on startup"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# 1. Add import for the bridge
import_marker = "from gfin_midas import midas_pipeline"
if import_marker in code and "midas_alert_bridge" not in code:
    bridge_import = """from gfin_midas import midas_pipeline
from midas_alert_bridge import midas_alert_bridge"""
    code = code.replace(import_marker, bridge_import, 1)
    print("1. Added bridge import")
else:
    print("1. Bridge import already present or marker not found")

# 2. Add startup task to launch the bridge
# Find the startup event
startup_marker = "@app.on_event(\"startup\")"
if startup_marker in code and "midas_alert_bridge" not in code.split(startup_marker)[1][:500]:
    # Find the end of the startup function to add the bridge task
    # Look for the async def startup line after the decorator
    startup_idx = code.find(startup_marker)
    # Find the next "async def" after startup
    async_def_idx = code.find("async def", startup_idx)
    # Find a good insertion point — after the startup function body
    # Insert right after the startup decorator+function start
    # Better: find @app.on_event("startup") and add task creation in the startup body
    
    # Find a line like "pass" or "return" or the end of the startup function
    # Simplest: add the bridge task right after the startup function definition
    # Find the first line after startup that's at the same indentation level as @app
    
    # Alternative: add it at the end of the file before the last line
    if 'if __name__' in code:
        main_idx = code.find('if __name__')
        bridge_code = """# Start MIDAS Alert Bridge background task
@app.on_event("startup")
async def start_midas_alert_bridge():
    asyncio.create_task(midas_alert_bridge(db_pool, midas_pipeline))

"""
        code = code[:main_idx] + bridge_code + code[main_idx:]
        print("2. Added bridge startup task")
    else:
        print("2. Could not find insertion point")
else:
    print("2. Bridge startup already present or marker not found")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print(f"Done. Size: {len(code)} bytes")
