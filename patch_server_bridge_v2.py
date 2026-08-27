#!/usr/bin/env python3
"""Add MIDAS bridge startup task to gfin_server.py"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

if "start_midas_alert_bridge" in code:
    print("Bridge startup already present")
    exit(0)

# Insert before if __name__ == "__main__"
main_idx = code.find('if __name__ == "__main__":')
if main_idx < 0:
    print("Could not find __main__")
    exit(1)

bridge_code = '''# Start MIDAS Alert Bridge background task
@app.on_event("startup")
async def start_midas_alert_bridge():
    """Background task: check MIDAS for new anomalies every 60s and create GFIN alerts"""
    asyncio.create_task(midas_alert_bridge(db_pool, midas_pipeline))

'''

code = code[:main_idx] + bridge_code + code[main_idx:]

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print(f"Added MIDAS bridge startup task. Size: {len(code)} bytes")
