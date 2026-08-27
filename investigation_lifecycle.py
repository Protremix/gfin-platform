"""
GFIN Investigation Lifecycle v2.0
Proper police-grade investigation workflow:
TRIGGER → TRIAGE → ACTIVE_INVESTIGATION → ATTRIBUTION → RISK_ASSESSMENT → LEA_ROUTING → ACTION → MONITORING → CLOSED

Each phase has structured steps, entity tracking, timeline events, and actions.
"""
import asyncpg
import json
import time
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/lifecycle")

# ============================================================
# PHASE DEFINITIONS — the investigation lifecycle
# ============================================================
INVESTIGATION_PHASES = [
    {
        "id": "TRIAGE",
        "label": "Triage & Evidence Gate",
        "description": "Is this real? Automated evidence validation before opening a full case.",
        "steps": [
            {"name": "Initial evidence assessment", "type": "AUTO"},
            {"name": "Evidence gate validation", "type": "AUTO"},
            {"name": "Duplicate check (existing cases)", "type": "AUTO"},
        ],
        "next": "ACTIVE_INVESTIGATION"
    },
    {
        "id": "ACTIVE_INVESTIGATION",
        "label": "Active Investigation",
        "description": "Deep dive: domain, financial, infrastructure, entity correlation.",
        "steps": [
            {"name": "Domain analysis (WHOIS, DNS, SSL, content)", "type": "AUTO"},
            {"name": "Financial tracing (wallet balances, transactions)", "type": "AUTO"},
            {"name": "Infrastructure mapping (hosting, registrar, CDN)", "type": "AUTO"},
            {"name": "Entity correlation (cross-case links)", "type": "AUTO"},
            {"name": "Manual investigator review", "type": "MANUAL"},
        ],
        "next": "ATTRIBUTION"
    },
    {
        "id": "ATTRIBUTION",
        "label": "Attribution",
        "description": "Who is behind this? Linking operators, infrastructure, and patterns.",
        "steps": [
            {"name": "Operator identification", "type": "AUTO"},
            {"name": "Attribution assessment", "type": "MANUAL"},
            {"name": "Confidence scoring", "type": "AUTO"},
        ],
        "next": "RISK_ASSESSMENT"
    },
    {
        "id": "RISK_ASSESSMENT",
        "label": "Risk Assessment",
        "description": "How bad is this? Victims, losses, severity, urgency.",
        "steps": [
            {"name": "Risk scoring (victims, loss, severity)", "type": "AUTO"},
            {"name": "Urgency classification", "type": "AUTO"},
            {"name": "Manual risk review", "type": "MANUAL"},
        ],
        "next": "LEA_ROUTING"
    },
    {
        "id": "LEA_ROUTING",
        "label": "LEA Routing",
        "description": "Which agency, what jurisdiction, what charges.",
        "steps": [
            {"name": "Jurisdiction analysis & routing", "type": "AUTO"},
            {"name": "Agency selection", "type": "MANUAL"},
            {"name": "Referral package preparation", "type": "MANUAL"},
        ],
        "next": "ACTION"
    },
    {
        "id": "ACTION",
        "label": "Action",
        "description": "Takedown, referral, public alert, prosecution package.",
        "steps": [
            {"name": "Action plan (takedown/referral/alert)", "type": "MANUAL"},
            {"name": "Execute actions", "type": "MANUAL"},
            {"name": "Track responses", "type": "MANUAL"},
        ],
        "next": "MONITORING"
    },
    {
        "id": "MONITORING",
        "label": "Monitoring",
        "description": "Keep watching — scammer may reappear with new infrastructure.",
        "steps": [
            {"name": "Continuous monitoring setup", "type": "AUTO"},
            {"name": "Change detection alerts", "type": "AUTO"},
        ],
        "next": "CLOSED"
    },
    {
        "id": "CLOSED",
        "label": "Closed",
        "description": "Case resolved or no longer active.",
        "steps": [],
        "next": None
    }
]

PHASE_ORDER = {p["id"]: i for i, p in enumerate(INVESTIGATION_PHASES)}

# ============================================================
# DATABASE HELPERS
# ============================================================
async def get_db():
    import os
    return await asyncpg.connect(
        host="localhost", port=5432,
        database="gfin", user="gfin",
        password=os.environ.get("DB_PASSWORD", "")
    )

async def add_timeline_event(conn, case_id, event_type, title, description, metadata=None, officer="SYSTEM"):
    await conn.execute(
        """INSERT INTO case_timeline (case_id, event_type, event_title, event_description, event_metadata, officer_name)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6)""",
        case_id, event_type, title, description or "",
        json.dumps(metadata or {}), officer
    )

async def update_entity_links(conn, entity_value, entity_type, case_id):
    """Track cross-case entity correlations."""
    existing = await conn.fetchrow(
        "SELECT id, case_ids FROM entity_links WHERE entity_value = $1 AND entity_type = $2",
        entity_value, entity_type
    )
    if existing:
        case_ids = list(existing["case_ids"])
        if case_id not in case_ids:
            case_ids.append(case_id)
            await conn.execute(
                "UPDATE entity_links SET case_ids = $1, mention_count = mention_count + 1, last_seen = now() WHERE id = $2",
                case_ids, existing["id"]
            )
    else:
        await conn.execute(
            "INSERT INTO entity_links (entity_value, entity_type, case_ids) VALUES ($1, $2, ARRAY[$3])",
            entity_value, entity_type, case_id
        )

# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/phases")
async def get_phases():
    """Return the investigation lifecycle phase definitions."""
    return {"phases": INVESTIGATION_PHASES}

@router.get("/case/{case_id}")
async def get_case_lifecycle(case_id: str):
    """Get full lifecycle data for a case — phases, steps, entities, timeline, actions."""
    conn = await get_db()
    try:
        # Case info
        case = await conn.fetchrow("SELECT * FROM cases WHERE case_id = $1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")

        # Investigation steps grouped by phase
        steps = await conn.fetch(
            "SELECT * FROM investigation_steps WHERE case_id = $1 ORDER BY order_num", case_id
        )
        steps_by_phase = {}
        for s in steps:
            phase = s["phase"]
            if phase not in steps_by_phase:
                steps_by_phase[phase] = []
            steps_by_phase[phase].append(dict(s))

        # Case entities — with officer info
        entities = await conn.fetch(
            """SELECT ce.*, po.name as officer_full_name, po.agency as officer_agency, po.country_code as officer_country
               FROM case_entities ce
               LEFT JOIN police_officers po ON ce.added_by_officer_id = po.id
               WHERE ce.case_id = $1 ORDER BY ce.entity_type, ce.created_date""",
            case_id
        )

        # Entity links (cross-case correlations)
        entity_links = []
        for e in entities:
            links = await conn.fetch(
                "SELECT * FROM entity_links WHERE entity_value = $1 AND entity_type = $2",
                e["entity_value"], e["entity_type"]
            )
            for link in links:
                if len(link["case_ids"]) > 1:  # Only show cross-case links
                    entity_links.append(dict(link))

        # Timeline events
        timeline = await conn.fetch(
            "SELECT * FROM case_timeline WHERE case_id = $1 ORDER BY created_date DESC LIMIT 50", case_id
        )

        # Case actions
        actions = await conn.fetch(
            "SELECT * FROM case_actions WHERE case_id = $1 ORDER BY created_date DESC", case_id
        )

        # Evidence — with officer info
        evidence_rows = await conn.fetch(
            """SELECT e.*, po.name as officer_full_name, po.agency as officer_agency, po.country_code as officer_country
               FROM evidence e
               LEFT JOIN police_officers po ON e.added_by_officer_id = po.id
               WHERE e.case_id = $1 ORDER BY e.created_date DESC""",
            case_id
        )

        # Case notes
        notes = await conn.fetch(
            "SELECT * FROM case_notes WHERE case_id = $1 ORDER BY created_date DESC", case_id
        )

        # Risk assessment
        risk = case.get("risk_assessment", {}) or {}
        
        # Attribution
        attribution = case.get("attribution_data", {}) or {}

        # Calculate phase progress
        phase_progress = {}
        for phase in INVESTIGATION_PHASES:
            phase_steps = steps_by_phase.get(phase["id"], [])
            if phase_steps:
                completed = sum(1 for s in phase_steps if s["status"] == "COMPLETED")
                total = len(phase_steps)
                phase_progress[phase["id"]] = {
                    "completed": completed,
                    "total": total,
                    "percentage": round((completed / total) * 100) if total > 0 else 0,
                    "status": "COMPLETED" if completed == total else ("IN_PROGRESS" if completed > 0 else "PENDING")
                }
            else:
                phase_progress[phase["id"]] = {"completed": 0, "total": 0, "percentage": 0, "status": "PENDING"}

        return {
            "case": dict(case),
            "evidence": [dict(e) for e in evidence_rows],
            "phases": INVESTIGATION_PHASES,
            "phase_progress": phase_progress,
            "steps_by_phase": steps_by_phase,
            "entities": [dict(e) for e in entities],
            "entity_links": entity_links,
            "timeline": [dict(t) for t in timeline],
            "actions": [dict(a) for a in actions],
            "notes": [dict(n) for n in notes],
            "risk_assessment": risk,
            "attribution": attribution,
            "current_phase": case.get("case_phase", "TRIAGE"),
            "priority": case.get("priority", "MEDIUM"),
        }
    finally:
        await conn.close()

@router.patch("/case/{case_id}/phase")
async def update_case_phase(case_id: str, request: Request):
    """Transition a case to a new phase in the investigation lifecycle."""
    body = await request.json()
    new_phase = body.get("phase")
    officer_name = body.get("officer_name", "SYSTEM")
    officer_id = body.get("officer_id")

    if new_phase not in PHASE_ORDER:
        raise HTTPException(400, f"Invalid phase. Must be one of: {list(PHASE_ORDER.keys())}")

    conn = await get_db()
    try:
        case = await conn.fetchrow("SELECT case_id, case_phase FROM cases WHERE case_id = $1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")

        old_phase = case["case_phase"]
        
        # Validate transition (can only go forward, or skip to CLOSED)
        if PHASE_ORDER.get(new_phase, 0) < PHASE_ORDER.get(old_phase, 0):
            if new_phase != "CLOSED":
                raise HTTPException(400, f"Cannot go backwards from {old_phase} to {new_phase}")

        await conn.execute(
            "UPDATE cases SET case_phase = $1, case_phase_updated = now(), updated_date = now() WHERE case_id = $2",
            new_phase, case_id
        )

        await add_timeline_event(
            conn, case_id, "PHASE_CHANGED",
            f"Phase: {old_phase} → {new_phase}",
            f"Investigation advanced from {old_phase} to {new_phase}",
            {"old_phase": old_phase, "new_phase": new_phase},
            officer_name
        )

        return {"status": "ok", "case_id": case_id, "old_phase": old_phase, "new_phase": new_phase}
    finally:
        await conn.close()

@router.patch("/case/{case_id}/priority")
async def update_case_priority(case_id: str, request: Request):
    """Set case priority (LOW, MEDIUM, HIGH, CRITICAL)."""
    body = await request.json()
    priority = body.get("priority", "MEDIUM")
    officer_name = body.get("officer_name", "SYSTEM")

    if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        raise HTTPException(400, "Priority must be LOW, MEDIUM, HIGH, or CRITICAL")

    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE cases SET priority = $1, updated_date = now() WHERE case_id = $2",
            priority, case_id
        )
        await add_timeline_event(
            conn, case_id, "PRIORITY_CHANGED",
            f"Priority set to {priority}",
            None, {"priority": priority}, officer_name
        )
        return {"status": "ok", "case_id": case_id, "priority": priority}
    finally:
        await conn.close()

@router.post("/case/{case_id}/step")
async def add_investigation_step(case_id: str, request: Request):
    """Add a manual investigation step to a case."""
    body = await request.json()
    conn = await get_db()
    try:
        max_order = await conn.fetchval(
            "SELECT COALESCE(MAX(order_num), 0) FROM investigation_steps WHERE case_id = $1", case_id
        )
        step = await conn.fetchrow(
            """INSERT INTO investigation_steps 
               (case_id, phase, step_name, step_type, status, officer_id, officer_name, order_num)
               VALUES ($1, $2, $3, 'MANUAL', 'PENDING', $4, $5, $6)
               RETURNING *""",
            case_id, body.get("phase", "ACTIVE_INVESTIGATION"),
            body.get("step_name", "Manual step"),
            body.get("officer_id"), body.get("officer_name", "SYSTEM"),
            max_order + 1
        )
        await add_timeline_event(
            conn, case_id, "STEP_ADDED",
            f"New step: {body.get('step_name')}",
            f"Added to phase {body.get('phase', 'ACTIVE_INVESTIGATION')}",
            {"step_name": body.get("step_name")},
            body.get("officer_name", "SYSTEM")
        )
        return dict(step)
    finally:
        await conn.close()

@router.patch("/case/{case_id}/step/{step_id}")
async def update_investigation_step(case_id: str, step_id: int, request: Request):
    """Update an investigation step (status, result, assignment)."""
    body = await request.json()
    conn = await get_db()
    try:
        updates = []
        params = [case_id, step_id]
        idx = 3
        
        if "status" in body:
            updates.append(f"status = ${idx}")
            params.append(body["status"])
            idx += 1
            if body["status"] == "COMPLETED":
                updates.append(f"completed_date = now()")
        
        if "result" in body:
            updates.append(f"result = ${idx}::jsonb")
            params.append(json.dumps(body["result"]))
            idx += 1

        if "officer_id" in body:
            updates.append(f"officer_id = ${idx}")
            params.append(body["officer_id"])
            idx += 1

        if "officer_name" in body:
            updates.append(f"officer_name = ${idx}")
            params.append(body["officer_name"])
            idx += 1

        if updates:
            set_clause = ", ".join(updates)
            query = f"UPDATE investigation_steps SET {set_clause} WHERE case_id = $1 AND id = $2"
            await conn.execute(query, *params)

        # Timeline event
        step = await conn.fetchrow(
            "SELECT step_name, status, phase FROM investigation_steps WHERE case_id = $1 AND id = $2",
            case_id, step_id
        )
        if step and "status" in body:
            await add_timeline_event(
                conn, case_id, "STEP_UPDATED",
                f"Step '{step['step_name']}' → {body['status']}",
                f"Phase: {step['phase']}",
                {"step_id": step_id, "step_name": step["step_name"], "new_status": body["status"]},
                body.get("officer_name", "SYSTEM")
            )

        return {"status": "ok", "step_id": step_id}
    finally:
        await conn.close()

@router.post("/case/{case_id}/entity")
async def add_case_entity(case_id: str, request: Request):
    """Add an entity (domain, IP, wallet, phone, person) to a case."""
    body = await request.json()
    entity_type = body.get("entity_type")
    entity_value = body.get("entity_value")

    if not entity_type or not entity_value:
        raise HTTPException(400, "entity_type and entity_value required")

    conn = await get_db()
    try:
        # Check if entity already exists for this case
        existing = await conn.fetchrow(
            "SELECT id FROM case_entities WHERE case_id = $1 AND entity_type = $2 AND entity_value = $3",
            case_id, entity_type, entity_value
        )
        if existing:
            return {"status": "exists", "id": existing["id"]}

        entity = await conn.fetchrow(
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
        )

        # Update cross-case links
        await update_entity_links(conn, entity_value, entity_type, case_id)

        await add_timeline_event(
            conn, case_id, "ENTITY_FOUND",
            f"New {entity_type}: {entity_value}",
            body.get("metadata", {}).get("description", ""),
            {"entity_type": entity_type, "entity_value": entity_value, "added_by": body.get("officer_name", "SYSTEM")},
            body.get("officer_name", "SYSTEM")
        )

        return dict(entity)
    finally:
        await conn.close()

@router.get("/case/{case_id}/entities")
async def get_case_entities(case_id: str):
    """Get all entities for a case, grouped by type."""
    conn = await get_db()
    try:
        entities = await conn.fetch(
            "SELECT * FROM case_entities WHERE case_id = $1 ORDER BY entity_type, created_date",
            case_id
        )
        by_type = {}
        for e in entities:
            etype = e["entity_type"]
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(dict(e))
        return {"entities": by_type, "total": len(entities)}
    finally:
        await conn.close()

@router.get("/case/{case_id}/timeline")
async def get_case_timeline(case_id: str, limit: int = 50):
    """Get chronological timeline of events for a case."""
    conn = await get_db()
    try:
        events = await conn.fetch(
            "SELECT * FROM case_timeline WHERE case_id = $1 ORDER BY created_date DESC LIMIT $2",
            case_id, limit
        )
        return {"events": [dict(e) for e in events], "total": len(events)}
    finally:
        await conn.close()

@router.post("/case/{case_id}/action")
async def create_case_action(case_id: str, request: Request):
    """Create a case action (takedown request, LEA referral, public alert, etc.)."""
    body = await request.json()
    conn = await get_db()
    try:
        action = await conn.fetchrow(
            """INSERT INTO case_actions
               (case_id, action_type, action_status, target_agency, target_contact, action_metadata, officer_id, officer_name)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
               RETURNING *""",
            case_id,
            body.get("action_type", "LEA_REFERRAL"),
            body.get("action_status", "PENDING"),
            body.get("target_agency", ""),
            body.get("target_contact", ""),
            json.dumps(body.get("metadata", {})),
            body.get("officer_id"),
            body.get("officer_name", "SYSTEM")
        )

        await add_timeline_event(
            conn, case_id, "ACTION_CREATED",
            f"Action: {body.get('action_type')} → {body.get('target_agency', 'N/A')}",
            body.get("description", ""),
            {"action_id": action["id"], "action_type": body.get("action_type")},
            body.get("officer_name", "SYSTEM")
        )

        return dict(action)
    finally:
        await conn.close()

@router.patch("/case/{case_id}/action/{action_id}")
async def update_case_action(case_id: str, action_id: int, request: Request):
    """Update a case action (mark as sent, acknowledged, completed, etc.)."""
    body = await request.json()
    conn = await get_db()
    try:
        updates = []
        params = [case_id, action_id]
        idx = 3

        if "action_status" in body:
            updates.append(f"action_status = ${idx}")
            params.append(body["action_status"])
            idx += 1

        if "response_notes" in body:
            updates.append(f"response_notes = ${idx}")
            params.append(body["response_notes"])
            idx += 1

        if body.get("action_status") in ("ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "FAILED"):
            updates.append("response_date = now()")

        if updates:
            set_clause = ", ".join(updates)
            query = f"UPDATE case_actions SET {set_clause} WHERE case_id = $1 AND id = $2"
            await conn.execute(query, *params)

        await add_timeline_event(
            conn, case_id, "ACTION_UPDATED",
            f"Action #{action_id} → {body.get('action_status', 'updated')}",
            body.get("response_notes", ""),
            {"action_id": action_id, "new_status": body.get("action_status")},
            body.get("officer_name", "SYSTEM")
        )

        return {"status": "ok", "action_id": action_id}
    finally:
        await conn.close()

@router.get("/case/{case_id}/correlations")
async def get_case_correlations(case_id: str):
    """Find cross-case correlations — entities shared between this case and others."""
    conn = await get_db()
    try:
        entities = await conn.fetch(
            "SELECT entity_value, entity_type FROM case_entities WHERE case_id = $1",
            case_id
        )
        
        correlations = []
        for e in entities:
            links = await conn.fetch(
                "SELECT * FROM entity_links WHERE entity_value = $1 AND entity_type = $2 AND array_length(case_ids, 1) > 1",
                e["entity_value"], e["entity_type"]
            )
            for link in links:
                other_cases = [c for c in link["case_ids"] if c != case_id]
                if other_cases:
                    # Get case summaries for correlated cases
                    case_summaries = []
                    for oc in other_cases:
                        oc_data = await conn.fetchrow(
                            "SELECT case_id, target, status, case_phase FROM cases WHERE case_id = $1",
                            oc
                        )
                        if oc_data:
                            case_summaries.append(dict(oc_data))
                    
                    correlations.append({
                        "entity_value": e["entity_value"],
                        "entity_type": e["entity_type"],
                        "link_type": link["link_type"],
                        "mention_count": link["mention_count"],
                        "correlated_cases": case_summaries
                    })

        return {"correlations": correlations, "total": len(correlations)}
    finally:
        await conn.close()

@router.patch("/case/{case_id}/risk")
async def update_risk_assessment(case_id: str, request: Request):
    """Update risk assessment data for a case."""
    body = await request.json()
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE cases SET risk_assessment = $1::jsonb, updated_date = now() WHERE case_id = $2",
            json.dumps(body.get("risk_data", {})), case_id
        )
        if body.get("total_loss_usd"):
            await conn.execute(
                "UPDATE cases SET total_loss_usd = $1 WHERE case_id = $2",
                float(body["total_loss_usd"]), case_id
            )
        await add_timeline_event(
            conn, case_id, "RISK_UPDATED",
            "Risk assessment updated",
            json.dumps(body.get("risk_data", {})),
            {"risk_data": body.get("risk_data", {})},
            body.get("officer_name", "SYSTEM")
        )
        return {"status": "ok"}
    finally:
        await conn.close()

@router.patch("/case/{case_id}/attribution")
async def update_attribution(case_id: str, request: Request):
    """Update attribution data — who is behind the scam."""
    body = await request.json()
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE cases SET attribution_data = $1::jsonb, updated_date = now() WHERE case_id = $2",
            json.dumps(body.get("attribution_data", {})), case_id
        )
        await add_timeline_event(
            conn, case_id, "ATTRIBUTION_UPDATED",
            "Attribution data updated",
            json.dumps(body.get("attribution_data", {})),
            {"attribution_data": body.get("attribution_data", {})},
            body.get("officer_name", "SYSTEM")
        )
        return {"status": "ok"}
    finally:
        await conn.close()

@router.patch("/case/{case_id}/assign")
async def assign_case(case_id: str, request: Request):
    """Assign a case to an officer."""
    body = await request.json()
    officer_id = body.get("officer_id")
    officer_name = body.get("officer_name", "SYSTEM")
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE cases SET assigned_to_officer = $1, assigned_to_officer_id = $2, updated_date = now() WHERE case_id = $3",
            officer_name, officer_id, case_id
        )
        await add_timeline_event(
            conn, case_id, "OFFICER_ASSIGNED",
            f"Assigned to {officer_name}",
            None, {"officer_id": officer_id, "officer_name": officer_name},
            officer_name
        )
        return {"status": "ok"}
    finally:
        await conn.close()



# ============================================================
# EVIDENCE MANAGEMENT — with officer tracking
# ============================================================

@router.get("/case/{case_id}/evidence")
async def get_case_evidence(case_id: str):
    """Get all evidence for a case, including who added each piece."""
    conn = await get_db()
    try:
        evidence = await conn.fetch(
            """SELECT e.*, o.name as officer_full_name, o.agency as officer_agency, o.country_code as officer_country
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


@router.get("/dashboard")
async def lifecycle_dashboard():
    """Dashboard showing all cases with their lifecycle phase, progress, and priority."""
    conn = await get_db()
    try:
        cases = await conn.fetch(
            """SELECT c.case_id, c.target, c.target_type, c.status, c.case_phase,
                      c.priority, c.victim_count, c.total_loss_usd, c.confidence,
                      c.scam_patterns, c.assigned_to_officer,
                      c.created_date, c.updated_date,
                      (SELECT COUNT(*) FROM investigation_steps WHERE case_id = c.case_id AND status = 'COMPLETED') as steps_completed,
                      (SELECT COUNT(*) FROM investigation_steps WHERE case_id = c.case_id) as steps_total,
                      (SELECT COUNT(*) FROM case_entities WHERE case_id = c.case_id) as entity_count,
                      (SELECT COUNT(*) FROM case_actions WHERE case_id = c.case_id) as action_count,
                      (SELECT COUNT(*) FROM case_timeline WHERE case_id = c.case_id) as timeline_count
               FROM cases c
               ORDER BY 
                   CASE c.priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                   c.updated_date DESC"""
        )
        
        phase_counts = {}
        for p in INVESTIGATION_PHASES:
            phase_counts[p["id"]] = 0
        for c in cases:
            phase = c["case_phase"] or "TRIAGE"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        return {
            "cases": [dict(c) for c in cases],
            "phase_summary": phase_counts,
            "total_cases": len(cases),
            "phases": INVESTIGATION_PHASES
        }
    finally:
        await conn.close()
