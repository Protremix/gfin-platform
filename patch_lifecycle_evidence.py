#!/usr/bin/env python3
"""Patch investigation_lifecycle.py to add officer tracking for evidence and entities."""

with open("/gfin/investigation_lifecycle.py", "r") as f:
    content = f.read()

# 1. Add evidence endpoints with officer tracking — insert before the dashboard endpoint
evidence_endpoints = '''

# ============================================================
# EVIDENCE MANAGEMENT — with officer tracking
# ============================================================

@router.get("/case/{case_id}/evidence")
async def get_case_evidence(case_id: str):
    """Get all evidence for a case, including who added each piece."""
    conn = await get_db()
    try:
        evidence = await conn.fetch(
            """SELECT e.*, o.full_name as officer_full_name, o.agency as officer_agency, o.country as officer_country
               FROM evidence e
               LEFT JOIN police_officers o ON e.added_by_officer_id = o.id
               WHERE e.case_id = $1
               ORDER BY e.created_date DESC""",
            case_id
        )
        return {"evidence": [dict(e) for e in evidence], "total": len(evidence)}
    finally:
        await conn.close()

@router.post("/case/{case_id}/evidence")
async def add_case_evidence(case_id: str, request: Request):
    """Add evidence to a case. Tracks which officer added it."""
    body = await request.json()
    officer_name = body.get("officer_name", "SYSTEM")
    officer_id = body.get("officer_id")
    
    conn = await get_db()
    try:
        case = await conn.fetchrow("SELECT case_id FROM cases WHERE case_id = $1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        
        # Generate evidence ID
        count = await conn.fetchval("SELECT COUNT(*) FROM evidence WHERE case_id = $1", case_id)
        evidence_id = f"E-{count + 1:03d}"
        
        evidence = await conn.fetchrow(
            """INSERT INTO evidence 
               (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, 
                confidence, content_hash, added_by_officer, added_by_officer_id, added_date)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
               RETURNING *""",
            case_id, evidence_id,
            body.get("phase", "ACTIVE_INVESTIGATION"),
            body.get("finding", ""),
            body.get("source_provider", "MANUAL"),
            body.get("source_url", ""),
            body.get("source_type", "INVESTIGATOR"),
            body.get("confidence", "MEDIUM"),
            body.get("content_hash", ""),
            officer_name, officer_id
        )
        
        await add_timeline_event(
            conn, case_id, "EVIDENCE_ADDED",
            f"Evidence added: {evidence_id}",
            body.get("finding", "")[:200],
            {"evidence_id": evidence_id, "finding": body.get("finding", "")[:200], "phase": body.get("phase")},
            officer_name
        )
        
        return dict(evidence)
    finally:
        await conn.close()

@router.delete("/case/{case_id}/evidence/{evidence_id}")
async def delete_case_evidence(case_id: str, evidence_id: str, request: Request):
    """Delete evidence from a case."""
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM evidence WHERE case_id = $1 AND evidence_id = $2", case_id, evidence_id)
        await add_timeline_event(
            conn, case_id, "EVIDENCE_REMOVED",
            f"Evidence removed: {evidence_id}",
            None, {"evidence_id": evidence_id}, "SYSTEM"
        )
        return {"status": "ok"}
    finally:
        await conn.close()

'''

# Insert before the dashboard endpoint
marker = '@router.get("/dashboard")'
content = content.replace(evidence_endpoints + '\n' + marker, marker)  # Avoid double insert
if "@router.get(\"/case/{case_id}/evidence\")" not in content:
    content = content.replace(marker, evidence_endpoints + '\n' + marker)

# 2. Update the entity endpoint to store officer info
old_entity_insert = '''        entity = await conn.fetchrow(
            """INSERT INTO case_entities 
               (case_id, entity_type, entity_value, entity_metadata, source, confidence, status)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
               RETURNING *""",
            case_id, entity_type, entity_value,
            json.dumps(body.get("metadata", {})),
            body.get("source", "MANUAL"),
            body.get("confidence", "MEDIUM"),
            body.get("status", "IDENTIFIED")
        )'''

new_entity_insert = '''        entity = await conn.fetchrow(
            """INSERT INTO case_entities 
               (case_id, entity_type, entity_value, entity_metadata, source, confidence, status,
                added_by_officer, added_by_officer_id)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
               RETURNING *""",
            case_id, entity_type, entity_value,
            json.dumps(body.get("metadata", {})),
            body.get("source", "MANUAL"),
            body.get("confidence", "MEDIUM"),
            body.get("status", "IDENTIFIED"),
            body.get("officer_name", "SYSTEM"),
            body.get("officer_id")
        )'''

content = content.replace(old_entity_insert, new_entity_insert)

# 3. Update the entity timeline event to include officer
old_entity_timeline = '''        await add_timeline_event(
            conn, case_id, "ENTITY_FOUND",
            f"New {entity_type}: {entity_value}",
            body.get("metadata", {}).get("description", ""),
            {"entity_type": entity_type, "entity_value": entity_value},
            body.get("officer_name", "SYSTEM")
        )'''

new_entity_timeline = '''        await add_timeline_event(
            conn, case_id, "ENTITY_FOUND",
            f"New {entity_type}: {entity_value}",
            body.get("metadata", {}).get("description", ""),
            {"entity_type": entity_type, "entity_value": entity_value, "added_by": body.get("officer_name", "SYSTEM")},
            body.get("officer_name", "SYSTEM")
        )'''

content = content.replace(old_entity_timeline, new_entity_timeline)

# 4. Update the case detail endpoint to join officer info for entities
old_entities_query = '''        # Case entities
        entities = await conn.fetch(
            "SELECT * FROM case_entities WHERE case_id = $1 ORDER BY entity_type, created_date", case_id
        )'''

new_entities_query = '''        # Case entities — with officer info
        entities = await conn.fetch(
            """SELECT ce.*, po.full_name as officer_full_name, po.agency as officer_agency, po.country as officer_country
               FROM case_entities ce
               LEFT JOIN police_officers po ON ce.added_by_officer_id = po.id
               WHERE ce.case_id = $1 ORDER BY ce.entity_type, ce.created_date""",
            case_id
        )'''

content = content.replace(old_entities_query, new_entities_query)

# 5. Also fetch evidence with officer info in the case detail endpoint
old_actions_query = '''        # Case actions
        actions = await conn.fetch(
            "SELECT * FROM case_actions WHERE case_id = $1 ORDER BY created_date DESC", case_id
        )'''

new_actions_query = '''        # Case actions
        actions = await conn.fetch(
            "SELECT * FROM case_actions WHERE case_id = $1 ORDER BY created_date DESC", case_id
        )

        # Evidence — with officer info
        evidence_rows = await conn.fetch(
            """SELECT e.*, po.full_name as officer_full_name, po.agency as officer_agency, po.country as officer_country
               FROM evidence e
               LEFT JOIN police_officers po ON e.added_by_officer_id = po.id
               WHERE e.case_id = $1 ORDER BY e.created_date DESC""",
            case_id
        )'''

content = content.replace(old_actions_query, new_actions_query)

# 6. Add evidence to the return dict
old_return = '''        return {
            "case": dict(case),
            "phases": INVESTIGATION_PHASES,'''

new_return = '''        return {
            "case": dict(case),
            "evidence": [dict(e) for e in evidence_rows],
            "phases": INVESTIGATION_PHASES,'''

content = content.replace(old_return, new_return)

with open("/gfin/investigation_lifecycle.py", "w") as f:
    f.write(content)
print("Patched — evidence endpoints + officer tracking added")
