#!/usr/bin/env python3
"""Fix the MIDAS alert bridge to use globals instead of parameters"""

# Fix the bridge file to import db_pool and midas_pipeline at runtime
with open("/gfin/midas_alert_bridge.py", "r") as f:
    bridge_code = f.read()

# Replace the function signature to not take db_pool as parameter
# Instead, import it as a global at runtime
old_sig = "async def midas_alert_bridge(db_pool, midas_pipeline):"
new_sig = """async def midas_alert_bridge():
    \"\"\"Background task: check MIDAS anomalies and create GFIN alerts.\"\"\"
    # Import globals at runtime (they're initialized in server startup)
    import gfin_server
    db_pool = gfin_server.db_pool
    from gfin_midas import midas_pipeline"""

if old_sig in bridge_code:
    bridge_code = bridge_code.replace(old_sig, new_sig, 1)
    with open("/gfin/midas_alert_bridge.py", "w") as f:
        f.write(bridge_code)
    print("Updated bridge to use runtime globals")
else:
    print("Bridge signature not found")

# Fix the startup call in gfin_server.py
with open("/gfin/gfin_server.py", "r") as f:
    server_code = f.read()

old_call = "asyncio.create_task(midas_alert_bridge(db_pool, midas_pipeline))"
new_call = "asyncio.create_task(midas_alert_bridge())"

if old_call in server_code:
    server_code = server_code.replace(old_call, new_call, 1)
    with open("/gfin/gfin_server.py", "w") as f:
        f.write(server_code)
    print("Updated server startup call")
else:
    print("Startup call not found")
