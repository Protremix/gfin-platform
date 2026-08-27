#!/usr/bin/env python3
"""Move MIDAS bridge startup from on_event to lifespan"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Find the lifespan function and add bridge startup
old_lifespan = """async def lifespan(app: FastAPI):
    await init_db()"""

new_lifespan = """async def lifespan(app: FastAPI):
    await init_db()
    # Start MIDAS Alert Bridge background task
    asyncio.create_task(midas_alert_bridge())"""

if old_lifespan in code:
    code = code.replace(old_lifespan, new_lifespan, 1)
    print("Added bridge startup to lifespan")
else:
    print("Lifespan block not found")

# Remove the old on_event startup
old_event = """# Start MIDAS Alert Bridge background task
@app.on_event("startup")
async def start_midas_alert_bridge():
    \"\"\"Background task: check MIDAS for new anomalies every 60s and create GFIN alerts\"\"\"
    asyncio.create_task(midas_alert_bridge())

if __name__ == "__main__":"""

new_event = """if __name__ == "__main__":"""

if old_event in code:
    code = code.replace(old_event, new_event, 1)
    print("Removed old on_event startup")
else:
    print("Old event block not found")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print("Done")
