#!/usr/bin/env python3
"""Fix bridge to use sys.modules['__main__'] instead of importing gfin_server"""

with open("/gfin/midas_alert_bridge.py", "r") as f:
    code = f.read()

old = """async def midas_alert_bridge():
    \"\"\"Background task: check MIDAS anomalies and create GFIN alerts.\"\"\"
    # Import globals at runtime (they're initialized in server startup)
    import gfin_server
    db_pool = gfin_server.db_pool
    from gfin_midas import midas_pipeline"""

new = """async def midas_alert_bridge():
    \"\"\"Background task: check MIDAS anomalies and create GFIN alerts.\"\"\"
    # Access globals from the running server (it runs as __main__)
    import sys
    main_mod = sys.modules.get('__main__')
    db_pool = getattr(main_mod, 'db_pool', None) if main_mod else None
    from gfin_midas import midas_pipeline"""

if old in code:
    code = code.replace(old, new, 1)
    with open("/gfin/midas_alert_bridge.py", "w") as f:
        f.write(code)
    print("Fixed bridge to use sys.modules['__main__']")
else:
    print("Block not found")
    # Show what's there
    idx = code.find("async def midas_alert_bridge")
    if idx >= 0:
        print("Context:", repr(code[idx:idx+300]))
