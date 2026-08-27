#!/usr/bin/env python3
"""Fix the indentation of hunter endpoints in gfin_server.py"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Find and replace the hunter endpoints section
old_start = "# ============================================================\n# AUTONOMOUS HUNTER ENDPOINTS"
old_end = "\nif __name__"

# Find the positions
start_idx = content.find(old_start)
end_idx = content.find(old_end, start_idx)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Could not find hunter endpoints")
    exit(1)

# Build properly indented hunter endpoints
new_hunter = '''# ============================================================
# AUTONOMOUS HUNTER ENDPOINTS
# ============================================================

@app.get("/api/hunter/status")
async def hunter_status():
    """Get autonomous hunter status and statistics."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as total, "
            "COUNT(CASE WHEN created_date > NOW() - interval '1 hour' THEN 1 END) as last_hour, "
            "COUNT(CASE WHEN created_date > NOW() - interval '24 hours' THEN 1 END) as last_24h, "
            "AVG(confidence) as avg_confidence "
            "FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        countries = await conn.fetch(
            "SELECT DISTINCT unnest(affected_countries) as country FROM cases "
            "WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        patterns = await conn.fetch(
            "SELECT DISTINCT unnest(scam_patterns) as pattern FROM cases "
            "WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        recent = await conn.fetch(
            "SELECT case_id, target, affected_countries, confidence, scam_patterns, created_date "
            "FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' "
            "ORDER BY created_date DESC LIMIT 10"
        )

    import subprocess
    try:
        result = subprocess.run(["systemctl", "is-active", "gfin-hunter"], capture_output=True, text=True, timeout=5)
        hunter_active = result.stdout.strip() == "active"
    except:
        hunter_active = False

    return {
        "status": "ACTIVE" if hunter_active else "INACTIVE",
        "service_running": hunter_active,
        "total_cases": row["total"] if row else 0,
        "cases_last_hour": row["last_hour"] if row else 0,
        "cases_last_24h": row["last_24h"] if row else 0,
        "avg_confidence": round(float(row["avg_confidence"] or 0), 2),
        "countries_involved": [r["country"] for r in countries if r["country"]],
        "scam_patterns_detected": [r["pattern"] for r in patterns if r["pattern"]],
        "recent_cases": [
            {
                "case_id": r["case_id"],
                "target": r["target"],
                "countries": r["affected_countries"],
                "confidence": r["confidence"],
                "patterns": r["scam_patterns"],
                "created": r["created_date"].isoformat() if r["created_date"] else None,
            }
            for r in recent
        ],
    }


@app.get("/api/hunter/recent")
async def hunter_recent(limit: int = 20):
    """Get recent cases created by the autonomous hunter."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT c.case_id, c.target, c.status, c.confidence, c.affected_countries, "
            "c.routed_to_countries, c.scam_patterns, c.digital_identifiers, "
            "c.physical_locations, c.created_date, "
            "COUNT(e.id) as evidence_count "
            "FROM cases c LEFT JOIN evidence e ON e.case_id = c.case_id "
            "WHERE c.created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' "
            "GROUP BY c.case_id ORDER BY c.created_date DESC LIMIT $1",
            limit
        )

    return [
        {
            "case_id": r["case_id"],
            "target": r["target"],
            "status": r["status"],
            "confidence": r["confidence"],
            "affected_countries": r["affected_countries"],
            "routed_to_countries": r["routed_to_countries"],
            "scam_patterns": r["scam_patterns"],
            "entity_count": len(r["digital_identifiers"]) if r["digital_identifiers"] else 0,
            "location_count": len(r["physical_locations"]) if r["physical_locations"] else 0,
            "evidence_count": r["evidence_count"],
            "created_date": r["created_date"].isoformat() if r["created_date"] else None,
        }
        for r in rows
    ]

'''

# Replace the old hunter section with the new one
content = content[:start_idx] + new_hunter + content[end_idx:]

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)

print("Fixed hunter endpoints indentation")
