#!/usr/bin/env python3
"""Add POST /api/evidence endpoint to allow officers to add evidence with tracking"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Find the GET evidence endpoint and add POST after it
old_evidence = '''@app.get("/api/evidence/{case_id}")
async def get_evidence(case_id: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1", case_id)
    return [dict(r) for r in rows]'''

new_evidence = old_evidence + '''

@app.post("/api/evidence/{case_id}")
async def add_evidence(request: Request, case_id: str,
    finding: str = Body(..., embed=True),
    phase: str = Body("MANUAL", embed=True),
    source_provider: str = Body("OFFICER", embed=True),
    source_url: str = Body("", embed=True),
    source_type: str = Body("MANUAL", embed=True),
    confidence: str = Body("MEDIUM", embed=True),
    content_hash: str = Body("", embed=True)):
    """Add evidence to a case — requires police auth. Tracks which officer added it."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Get officer name
    officer = await conn.fetchrow("SELECT name, agency FROM police_officers WHERE id=$1", officer_id)
    officer_name = officer["name"] if officer else "UNKNOWN"
    
    evidence_id = f"EVID-{int(time.time())}-{case_id}"
    
    await conn.execute("""
        INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, 
                             source_type, confidence, content_hash, added_by_officer, added_by_officer_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """, case_id, evidence_id, phase, finding, source_provider, source_url,
        source_type, confidence.upper(), content_hash if content_hash else None, 
        officer_name, officer_id)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "ADD_EVIDENCE", officer_name, "DASHBOARD", f"Manual evidence: {finding[:80]}", 
        f"evidence_id={evidence_id}"
    )
    
    # Update case updated_date
    await conn.execute("UPDATE cases SET updated_date=NOW() WHERE case_id=$1", case_id)
    
    await conn.close()
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "added_by": officer_name,
        "officer_id": officer_id,
        "message": f"Evidence added to {case_id} by {officer_name}"
    }

@app.delete("/api/evidence/{evidence_id}")
async def delete_evidence(request: Request, evidence_id: str):
    """Delete evidence — requires police auth. Tracks who deleted it."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    officer_name = payload.get("agency", "UNKNOWN")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Get the evidence before deleting
    row = await conn.fetchrow("SELECT case_id, finding FROM evidence WHERE evidence_id=$1", evidence_id)
    if not row:
        await conn.close()
        return {"success": False, "message": "Evidence not found"}
    
    case_id = row["case_id"]
    
    await conn.execute("DELETE FROM evidence WHERE evidence_id=$1", evidence_id)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "DELETE_EVIDENCE", officer_name, "DASHBOARD", f"Delete evidence {evidence_id}",
        "deleted"
    )
    
    await conn.close()
    
    return {"success": True, "message": f"Evidence {evidence_id} deleted by {officer_name}"}'''

content = content.replace(old_evidence, new_evidence)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Added POST/DELETE evidence endpoints with officer tracking")
