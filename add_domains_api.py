"""Add tracked domains API endpoint to the GFIN server."""
import re

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Add tracked domains endpoints before the hunter status section
tracked_domains_api = '''

# ==================== TRACKED DOMAINS (Domain Intelligence Database) ====================

@app.get("/api/domains")
async def list_tracked_domains(
    risk_level: str = None,
    source: str = None,
    limit: int = 100,
    offset: int = 0
):
    """List all tracked domains — these are NOT cases, just domain intelligence."""
    async with db_pool.acquire() as conn:
        query = "SELECT * FROM tracked_domains"
        params = []
        conditions = []
        if risk_level:
            conditions.append("risk_level = $%d" % (len(params) + 1))
            params.append(risk_level.upper())
        if source:
            conditions.append("source = $%d" % (len(params) + 1))
            params.append(source.upper())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY risk_score DESC, first_seen DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])
        
        domains = await conn.fetch(query, *params)
        total = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains")
        
        return {
            "total": total,
            "returned": len(domains),
            "domains": [dict(d) for d in domains]
        }


@app.get("/api/domains/{domain}")
async def get_tracked_domain(domain: str):
    """Get details for a specific tracked domain."""
    async with db_pool.acquire() as conn:
        d = await conn.fetchrow("SELECT * FROM tracked_domains WHERE domain = $1", domain)
        if not d:
            raise HTTPException(status_code=404, detail="Domain not found")
        return dict(d)


@app.get("/api/domains/stats")
async def domain_stats():
    """Get statistics for tracked domains."""
    async with db_pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains")
        by_risk = await conn.fetch("SELECT risk_level, COUNT(*) as count FROM tracked_domains GROUP BY risk_level ORDER BY count DESC")
        by_source = await conn.fetch("SELECT source, COUNT(*) as count FROM tracked_domains GROUP BY source ORDER BY count DESC")
        
        return {
            "total_domains": total,
            "by_risk": [{"level": r["risk_level"], "count": r["count"]} for r in by_risk],
            "by_source": [{"source": r["source"], "count": r["count"]} for r in by_source],
        }

'''

# Insert before hunter status
marker = '# ==================== AUTONOMOUS HUNTER'
if marker in code:
    code = code.replace(marker, tracked_domains_api + '\n' + marker)
else:
    # Fallback — insert before the health endpoint
    code = code.replace('@app.get("/health")', tracked_domains_api + '\n@app.get("/health")')

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)

print("Added tracked domains API: /api/domains, /api/domains/{domain}, /api/domains/stats")
