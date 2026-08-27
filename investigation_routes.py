#!/usr/bin/env python3
"""
GFIN Investigation Workbench Routes
Provides APIs for the investigator dashboard:
- Case board with progress tracking
- Unified intel feed (Telegram + Hunter)
- Evidence management
- Telegram monitoring
- Hunter control
- Investigation steps
"""
import asyncio
import asyncpg
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query, Body
from fastapi.responses import JSONResponse

router = APIRouter()

# DB config will be injected
DB_CONFIG = None
_police_auth = None

def init(db_config, police_auth_module):
    global DB_CONFIG, _police_auth
    DB_CONFIG = db_config
    _police_auth = police_auth_module

def _safe_json(val):
    """Safely parse JSONB value."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except:
            return val
    return val


# ==================== OVERVIEW ====================

@router.get("/api/inv/overview")
async def investigation_overview():
    """Dashboard overview stats for investigator workbench."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Case stats
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases")
        active_cases = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE status IN ('NEW','INVESTIGATING','ESCALATED')")
        critical_cases = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE priority = 'CRITICAL'")
        resolved_cases = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE status = 'CLOSED'")
        
        # Evidence stats
        total_evidence = await conn.fetchval("SELECT COUNT(*) FROM evidence")
        
        # Telegram stats
        telegram_intel_count = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence")
        telegram_groups_count = await conn.fetchval("SELECT COUNT(*) FROM telegram_groups WHERE is_monitored = true")
        telegram_wallets = await conn.fetchval("SELECT COUNT(*) FROM telegram_wallets")
        telegram_domains = await conn.fetchval("SELECT COUNT(*) FROM telegram_domains")
        
        # Tracked domains
        tracked_domains = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains")
        high_risk_domains = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains WHERE risk_level IN ('HIGH','CRITICAL')")
        
        # Victim stats
        total_victims = await conn.fetchval("SELECT COUNT(*) FROM victims")
        total_complaints = await conn.fetchval("SELECT COUNT(*) FROM victim_complaints")
        
        # Recent activity (last 24h)
        recent_evidence = await conn.fetchval(
            "SELECT COUNT(*) FROM evidence WHERE created_date > NOW() - INTERVAL '24 hours'"
        )
        recent_intel = await conn.fetchval(
            "SELECT COUNT(*) FROM telegram_intelligence WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        
        # Officer count
        officer_count = await conn.fetchval("SELECT COUNT(*) FROM police_officers WHERE is_active = true")
        
        return {
            "cases": {
                "total": total_cases,
                "active": active_cases,
                "critical": critical_cases,
                "resolved": resolved_cases
            },
            "evidence": {
                "total": total_evidence,
                "recent_24h": recent_evidence
            },
            "telegram": {
                "intel_items": telegram_intel_count,
                "groups_monitored": telegram_groups_count,
                "wallets_tracked": telegram_wallets,
                "domains_tracked": telegram_domains,
                "recent_24h": recent_intel
            },
            "domains": {
                "tracked": tracked_domains,
                "high_risk": high_risk_domains
            },
            "victims": {
                "total": total_victims,
                "complaints": total_complaints
            },
            "officers": officer_count
        }
    finally:
        await conn.close()


# ==================== CASE BOARD ====================

@router.get("/api/inv/board")
async def case_board():
    """Case board with evidence counts, progress, and last activity."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        cases = await conn.fetch("""
            SELECT c.*,
                (SELECT COUNT(*) FROM evidence e WHERE e.case_id = c.case_id) as evidence_count,
                (SELECT COUNT(*) FROM alerts a WHERE a.case_id = c.case_id) as alert_count,
                (SELECT MAX(created_date) FROM evidence e WHERE e.case_id = c.case_id) as last_evidence_date,
                (SELECT COUNT(*) FROM case_notes cn WHERE cn.case_id = c.case_id) as note_count,
                (SELECT name FROM police_officers po WHERE po.id::text = c.assigned_to_officer) as assigned_name
            FROM cases c
            ORDER BY c.created_date DESC
        """)
        
        result = []
        for row in cases:
            case = dict(row)
            # Calculate progress based on evidence phases
            evidence_phases = await conn.fetch(
                "SELECT DISTINCT phase FROM evidence WHERE case_id = $1", case["case_id"]
            )
            phases_covered = len([p for p in evidence_phases if p["phase"]])
            # Standard investigation phases
            standard_phases = ["SCAM_DETECTION", "ENTITY_EXTRACTION", "CONNECTOR_SEARCH", "COUNTRY_ROUTING", 
                             "FAVICON_FINGERPRINT", "TECH_STACK", "DOMAIN_INTEL", "REDIRECT_CHAIN",
                             "FORM_DETECTION", "PAGE_METADATA", "TYPO_SQUATTING", "WALLET_ANALYSIS"]
            progress = min(100, int((phases_covered / max(len(standard_phases), 1)) * 100)) if phases_covered > 0 else 0
            
            case["evidence_count"] = case.get("evidence_count", 0)
            case["alert_count"] = case.get("alert_count", 0)
            case["note_count"] = case.get("note_count", 0)
            case["progress"] = progress
            case["phases_covered"] = [p["phase"] for p in evidence_phases if p["phase"]]
            case["scam_indicators"] = _safe_json(case.get("scam_indicators"))
            case["evidence_chain"] = _safe_json(case.get("evidence_chain"))
            case["physical_locations"] = _safe_json(case.get("physical_locations"))
            case["financial_indicators"] = _safe_json(case.get("financial_indicators"))
            case["digital_identifiers"] = _safe_json(case.get("digital_identifiers"))
            result.append(case)
        
        return {"cases": result, "total": len(result)}
    finally:
        await conn.close()


# ==================== CASE DETAIL ====================

@router.get("/api/inv/case/{case_id}")
async def case_detail(case_id: str):
    """Full case detail with all linked investigation data."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Case
        case = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        case = dict(case)
        for k in ["scam_indicators", "evidence_chain", "physical_locations", "financial_indicators", "digital_identifiers"]:
            case[k] = _safe_json(case.get(k))
        
        # Evidence grouped by phase
        evidence = await conn.fetch(
            "SELECT * FROM evidence WHERE case_id=$1 ORDER BY created_date DESC", case_id
        )
        evidence_by_phase = {}
        evidence_timeline = []
        for e in evidence:
            ed = dict(e)
            phase = ed.get("phase") or "UNCATEGORIZED"
            if phase not in evidence_by_phase:
                evidence_by_phase[phase] = []
            evidence_by_phase[phase].append(ed)
            evidence_timeline.append({
                "id": ed["id"],
                "evidence_id": ed["evidence_id"],
                "phase": phase,
                "finding": ed["finding"],
                "source": ed.get("source_provider"),
                "confidence": ed.get("confidence"),
                "timestamp": ed.get("timestamp").isoformat() if ed.get("timestamp") else None
            })
        
        # People
        people = await conn.fetch("SELECT * FROM people WHERE case_id=$1", case_id)
        
        # Alerts
        alerts = await conn.fetch("SELECT * FROM alerts WHERE case_id=$1 ORDER BY created_date DESC", case_id)
        
        # Notes
        notes = await conn.fetch("""
            SELECT cn.*, po.email as officer_email, po.name as officer_name
            FROM case_notes cn
            LEFT JOIN police_officers po ON cn.officer_id = po.id
            WHERE cn.case_id = $1 ORDER BY cn.created_date DESC
        """, case_id)
        
        # Files
        files = await conn.fetch("SELECT * FROM case_files WHERE case_id=$1 ORDER BY uploaded_date DESC", case_id)
        
        # Audit trail
        audit = await conn.fetch("SELECT * FROM audit_log WHERE case_id=$1 ORDER BY timestamp DESC LIMIT 50", case_id)
        
        # Complaints linked to this case
        complaints = await conn.fetch("""
            SELECT vc.reference_number, vc.scam_type, vc.incident_date, vc.created_date,
                   v.name as victim_name, v.country as victim_country, v.email as victim_email
            FROM victim_complaints vc
            LEFT JOIN victims v ON vc.victim_id = v.id
            WHERE vc.case_id = $1 ORDER BY vc.created_date DESC
        """, case_id)
        
        # Telegram intel linked by domain match
        target = case.get("target", "")
        telegram_intel = []
        if target:
            telegram_intel = await conn.fetch(
                """SELECT * FROM telegram_intelligence 
                   WHERE domains::text ILIKE $1 OR message_text ILIKE $2
                   ORDER BY created_at DESC LIMIT 20""",
                f"%{target}%", f"%{target}%"
            )
        
        # Tracked domains matching case target
        tracked = await conn.fetch(
            "SELECT * FROM tracked_domains WHERE domain ILIKE $1 ORDER BY first_seen DESC",
            f"%{target}%"
        )
        
        return {
            "case": case,
            "evidence": {
                "by_phase": evidence_by_phase,
                "timeline": evidence_timeline,
                "total": len(evidence)
            },
            "people": [dict(p) for p in people],
            "alerts": [dict(a) for a in alerts],
            "notes": [dict(n) for n in notes],
            "files": [dict(f) for f in files],
            "audit": [dict(a) for a in audit],
            "complaints": [dict(c) for c in complaints],
            "telegram_intel": [dict(t) for t in telegram_intel],
            "tracked_domains": [dict(t) for t in tracked],
            "investigation_steps": _extract_steps(evidence_timeline)
        }
    finally:
        await conn.close()


def _extract_steps(evidence_timeline):
    """Extract investigation steps from evidence phases."""
    steps = []
    seen_phases = set()
    phase_order = [
        "SCAM_DETECTION", "ENTITY_EXTRACTION", "CONNECTOR_SEARCH", "COUNTRY_ROUTING",
        "FAVICON_FINGERPRINT", "ANALYTICS_ID", "REDIRECT_CHAIN", "TECH_STACK",
        "FORM_DETECTION", "DOMAIN_INTEL", "TYPO_SQUATTING", "PAGE_METADATA",
        "DOMAIN_AGE", "WALLET_ANALYSIS", "EVIDENCE_COLLECTION", "POLICE_ROUTING"
    ]
    for item in evidence_timeline:
        phase = item.get("phase", "")
        if phase not in seen_phases:
            seen_phases.add(phase)
            steps.append({
                "step": phase,
                "label": phase.replace("_", " ").title(),
                "status": "COMPLETED",
                "timestamp": item.get("timestamp"),
                "finding": item.get("finding", "")[:200]
            })
    # Sort by phase order
    def sort_key(s):
        try:
            return phase_order.index(s["step"])
        except ValueError:
            return len(phase_order)
    steps.sort(key=sort_key)
    return steps


# ==================== ADD EVIDENCE ====================

@router.post("/api/inv/case/{case_id}/evidence")
async def add_evidence(case_id: str, request: Request):
    """Add manual evidence to a case."""
    # Verify auth
    if _police_auth:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("gfin_police_token", "")
        payload = _police_auth.verify_token(token)
        if not payload:
            raise HTTPException(401, "Authentication required")
    
    body = await request.json()
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check case exists
        case = await conn.fetchrow("SELECT case_id FROM cases WHERE case_id=$1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        
        evidence_id = f"E-MAN-{int(time.time())}"
        await conn.execute(
            """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            case_id, evidence_id,
            body.get("phase", "MANUAL"),
            body.get("finding", ""),
            body.get("source_provider", "OFFICER_MANUAL"),
            body.get("source_url", ""),
            body.get("source_type", "MANUAL"),
            body.get("confidence", "MEDIUM")
        )
        
        # Update case
        await conn.execute(
            "UPDATE cases SET updated_date = NOW() WHERE case_id = $1", case_id
        )
        
        # Audit log
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "EVIDENCE_ADDED", payload.get("agency", "OFFICER") if _police_auth else "OFFICER",
            "MANUAL", body.get("phase", "MANUAL"), "SUCCESS"
        )
        
        return {"status": "created", "evidence_id": evidence_id}
    finally:
        await conn.close()


# ==================== ADD NOTE ====================

@router.post("/api/inv/case/{case_id}/note")
async def add_note(case_id: str, request: Request):
    """Add investigation note to a case."""
    if _police_auth:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("gfin_police_token", "")
        payload = _police_auth.verify_token(token)
        if not payload:
            raise HTTPException(401, "Authentication required")
    
    body = await request.json()
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        officer_id = int(payload.get("oid", 0)) if _police_auth else 0
        await conn.execute(
            """INSERT INTO case_notes (case_id, officer_id, note, is_public)
               VALUES ($1, $2, $3, $4)""",
            case_id, officer_id, body.get("note", ""), body.get("is_public", True)
        )
        await conn.execute("UPDATE cases SET updated_date = NOW() WHERE case_id = $1", case_id)
        return {"status": "created"}
    finally:
        await conn.close()


# ==================== UPDATE CASE STATUS ====================

@router.patch("/api/inv/case/{case_id}/status")
async def update_case_status(case_id: str, request: Request):
    """Update case status."""
    if _police_auth:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("gfin_police_token", "")
        payload = _police_auth.verify_token(token)
        if not payload:
            raise HTTPException(401, "Authentication required")
    
    body = await request.json()
    new_status = body.get("status")
    if new_status not in ["NEW", "INVESTIGATING", "FORWARDED", "CLOSED", "ESCALATED"]:
        raise HTTPException(400, "Invalid status")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute("UPDATE cases SET status=$1, updated_date=NOW() WHERE case_id=$2", new_status, case_id)
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "STATUS_CHANGED", payload.get("agency", "OFFICER") if _police_auth else "OFFICER",
            "MANUAL", f"->{new_status}", "SUCCESS"
        )
        return {"status": "updated", "new_status": new_status}
    finally:
        await conn.close()


# ==================== INTEL FEED ====================

@router.get("/api/inv/intel-feed")
async def intel_feed(limit: int = 50, source: str = "all", offset: int = 0):
    """Unified intelligence feed — Telegram + Hunter + Domains."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        items = []
        
        if source in ("all", "telegram"):
            # Recent telegram intel
            tg = await conn.fetch("""
                SELECT id, group_name, sender_name, sender_username, message_text,
                       wallets, domains, phones, scam_type, risk_level, is_victim, created_at,
                       'telegram' as source
                FROM telegram_intelligence
                ORDER BY created_at DESC LIMIT $1 OFFSET $2
            """, limit, offset)
            for row in tg:
                d = dict(row)
                d["wallets"] = _safe_json(d.get("wallets"))
                d["domains"] = _safe_json(d.get("domains"))
                d["phones"] = _safe_json(d.get("phones"))
                d["timestamp"] = d["created_at"].isoformat() if d.get("created_at") else None
                items.append(d)
        
        if source in ("all", "hunter"):
            # Recent hunter evidence (auto-investigations)
            he = await conn.fetch("""
                SELECT id, case_id, evidence_id, phase, finding, source_provider, source_type,
                       confidence, timestamp, 'hunter' as source
                FROM evidence
                WHERE case_id LIKE 'GFIN-AUTO-%'
                ORDER BY created_date DESC LIMIT $1 OFFSET $2
            """, limit, offset)
            for row in he:
                d = dict(row)
                d["timestamp"] = d["timestamp"].isoformat() if d.get("timestamp") else None
                items.append(d)
        
        if source in ("all", "domains"):
            # Recent tracked domains
            td = await conn.fetch("""
                SELECT id, domain, source, risk_level, risk_score, confidence, patterns,
                       evidence_summary, first_seen, status, 'domain' as source
                FROM tracked_domains
                ORDER BY first_seen DESC LIMIT $1 OFFSET $2
            """, limit, offset)
            for row in td:
                d = dict(row)
                d["timestamp"] = d["first_seen"].isoformat() if d.get("first_seen") else None
                items.append(d)
        
        # Sort by timestamp
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "items": items[:limit],
            "total": len(items),
            "offset": offset
        }
    finally:
        await conn.close()


# ==================== TELEGRAM GROUPS ====================

@router.get("/api/inv/telegram/groups")
async def telegram_groups_stats():
    """Monitored Telegram groups with statistics."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        groups = await conn.fetch("""
            SELECT g.*,
                (SELECT COUNT(*) FROM telegram_intelligence ti WHERE ti.group_id = g.group_id) as intel_count,
                (SELECT COUNT(*) FROM telegram_intelligence ti WHERE ti.group_id = g.group_id AND ti.risk_level = 'CRITICAL') as critical_count,
                (SELECT COUNT(*) FROM telegram_intelligence ti WHERE ti.group_id = g.group_id AND ti.risk_level = 'HIGH') as high_count,
                (SELECT MAX(created_at) FROM telegram_intelligence ti WHERE ti.group_id = g.group_id) as last_intel
            FROM telegram_groups g
            WHERE g.is_monitored = true
            ORDER BY g.member_count DESC
        """)
        
        return {
            "groups": [dict(g) for g in groups],
            "total": len(groups),
            "total_members": sum(g["member_count"] for g in groups if g["member_count"])
        }
    finally:
        await conn.close()


# ==================== TELEGRAM INTEL ====================

@router.get("/api/inv/telegram/intel")
async def telegram_intel(limit: int = 50, group_id: Optional[int] = None, risk: str = "all", offset: int = 0):
    """Telegram intelligence items with entity extraction."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        query = "SELECT * FROM telegram_intelligence"
        conditions = []
        params = []
        idx = 1
        
        if group_id:
            conditions.append(f"group_id = ${idx}")
            params.append(group_id)
            idx += 1
        if risk != "all":
            conditions.append(f"risk_level = ${idx}")
            params.append(risk.upper())
            idx += 1
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}"
        params.extend([limit, offset])
        
        items = await conn.fetch(query, *params)
        
        result = []
        for row in items:
            d = dict(row)
            d["wallets"] = _safe_json(d.get("wallets"))
            d["domains"] = _safe_json(d.get("domains"))
            d["phones"] = _safe_json(d.get("phones"))
            d["ips"] = _safe_json(d.get("ips"))
            d["usernames"] = _safe_json(d.get("usernames"))
            d["scam_indicators"] = _safe_json(d.get("scam_indicators"))
            d["victim_patterns"] = _safe_json(d.get("victim_patterns"))
            result.append(d)
        
        return {"items": result, "total": len(result), "offset": offset}
    finally:
        await conn.close()


# ==================== EVIDENCE VAULT ====================

@router.get("/api/inv/evidence")
async def evidence_vault(
    case_id: Optional[str] = None,
    phase: Optional[str] = None,
    source_type: Optional[str] = None,
    confidence: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """All evidence, filterable."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        query = "SELECT * FROM evidence"
        conditions = []
        params = []
        idx = 1
        
        if case_id:
            conditions.append(f"case_id = ${idx}")
            params.append(case_id)
            idx += 1
        if phase:
            conditions.append(f"phase = ${idx}")
            params.append(phase)
            idx += 1
        if source_type:
            conditions.append(f"source_type = ${idx}")
            params.append(source_type)
            idx += 1
        if confidence:
            conditions.append(f"confidence = ${idx}")
            params.append(confidence)
            idx += 1
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) as subq"
        total = await conn.fetchval(count_query, *params)
        
        query += f" ORDER BY created_date DESC LIMIT ${idx} OFFSET ${idx+1}"
        params.extend([limit, offset])
        
        items = await conn.fetch(query, *params)
        
        # Get phase distribution
        phase_dist = await conn.fetch(
            "SELECT phase, COUNT(*) as count FROM evidence GROUP BY phase ORDER BY count DESC"
        )
        
        return {
            "items": [dict(e) for e in items],
            "total": total,
            "offset": offset,
            "phase_distribution": [{"phase": p["phase"], "count": p["count"]} for p in phase_dist]
        }
    finally:
        await conn.close()


# ==================== HUNTER ACTIVITY ====================

@router.get("/api/inv/hunter/activity")
async def hunter_activity(limit: int = 30):
    """Recent Hunter investigations — auto cases with evidence."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Get auto-investigation cases (GFIN-AUTO-*)
        auto_cases = await conn.fetch("""
            SELECT 
                e.case_id,
                MIN(e.created_date) as started_at,
                MAX(e.created_date) as last_activity,
                COUNT(*) as evidence_count,
                STRING_AGG(DISTINCT e.phase, ', ') as phases,
                MAX(e.finding) as latest_finding
            FROM evidence e
            WHERE e.case_id LIKE 'GFIN-AUTO-%'
            GROUP BY e.case_id
            ORDER BY started_at DESC
            LIMIT $1
        """, limit)
        
        # Also get regular cases with hunter evidence
        regular_cases = await conn.fetch("""
            SELECT 
                e.case_id,
                c.target,
                c.status,
                c.confidence,
                MIN(e.created_date) as started_at,
                MAX(e.created_date) as last_activity,
                COUNT(*) as evidence_count,
                STRING_AGG(DISTINCT e.phase, ', ') as phases
            FROM evidence e
            JOIN cases c ON e.case_id = c.case_id
            WHERE e.source_type = 'AUTOMATED_OSINT'
            GROUP BY e.case_id, c.target, c.status, c.confidence
            ORDER BY started_at DESC
            LIMIT $1
        """, limit)
        
        return {
            "auto_investigations": [dict(a) for a in auto_cases],
            "case_investigations": [dict(r) for r in regular_cases],
            "total_auto": len(auto_cases)
        }
    finally:
        await conn.close()


# ==================== PROMOTE DOMAIN TO CASE ====================

@router.post("/api/inv/promote")
async def promote_to_case(request: Request):
    """Promote a tracked domain to a full case."""
    if _police_auth:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("gfin_police_token", "")
        payload = _police_auth.verify_token(token)
        if not payload:
            raise HTTPException(401, "Authentication required")
    
    body = await request.json()
    domain = body.get("domain")
    if not domain:
        raise HTTPException(400, "Domain required")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if case already exists for this domain
        existing = await conn.fetchrow("SELECT case_id FROM cases WHERE target = $1", domain)
        if existing:
            return {"status": "exists", "case_id": existing["case_id"]}
        
        # Get domain intel
        td = await conn.fetchrow("SELECT * FROM tracked_domains WHERE domain = $1", domain)
        if not td:
            raise HTTPException(404, "Domain not found in tracked domains")
        
        # Create case
        case_id = f"GFIN-CASE-{int(time.time())}"
        patterns = td["patterns"] or []
        if isinstance(patterns, str):
            patterns = [patterns]
        
        await conn.execute(
            """INSERT INTO cases (case_id, target, target_type, trigger, status, confidence,
                   scam_patterns, subject_reason, evidence_chain)
               VALUES ($1, $2, 'DOMAIN', 'OFFICER_PROMOTION', 'NEW', $3, $4, $5, '[]'::jsonb)""",
            case_id, domain, td["confidence"] or 0.5,
            patterns, f"Promoted from tracked domains. Risk: {td['risk_level']}, Source: {td['source']}"
        )
        
        # Move evidence from auto-investigation to this case
        auto_case_id = f"GFIN-AUTO-%{domain}%"
        await conn.execute(
            "UPDATE evidence SET case_id=$1 WHERE case_id LIKE $2",
            case_id, auto_case_id
        )
        
        # Update tracked domain status
        await conn.execute("UPDATE tracked_domains SET status='PROMOTED' WHERE domain=$1", domain)
        
        # Audit
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "DOMAIN_PROMOTED", payload.get("agency", "OFFICER") if _police_auth else "OFFICER",
            "MANUAL", domain, "SUCCESS"
        )
        
        return {"status": "created", "case_id": case_id, "domain": domain}
    finally:
        await conn.close()


# ==================== TRIGGER HUNTER ====================

@router.post("/api/inv/hunter/run")
async def trigger_hunter(request: Request):
    """Trigger Hunter investigation on a target."""
    if _police_auth:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("gfin_police_token", "")
        payload = _police_auth.verify_token(token)
        if not payload:
            raise HTTPException(401, "Authentication required")
    
    body = await request.json()
    target = body.get("target")
    if not target:
        raise HTTPException(400, "Target required")
    
    # Use existing playbook investigate endpoint logic
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if already being investigated
        existing = await conn.fetchrow("SELECT case_id, status FROM cases WHERE target = $1", target)
        if existing and existing["status"] in ("NEW", "INVESTIGATING"):
            return {"status": "already_investigating", "case_id": existing["case_id"]}
        
        # Create or update case
        case_id = existing["case_id"] if existing else f"GFIN-CASE-{int(time.time())}"
        if not existing:
            await conn.execute(
                """INSERT INTO cases (case_id, target, target_type, trigger, status, confidence)
                   VALUES ($1, $2, 'DOMAIN', $3, 'INVESTIGATING', 0.5)""",
                case_id, target, body.get("trigger_reason", "OFFICER_TRIGGERED")
            )
        
        # Trigger playbook investigation (import from gfin_server)
        import sys
        sys.path.insert(0, "/gfin")
        try:
            from intelligence_playbook import IntelligencePlaybook
            playbook = IntelligencePlaybook()
            result = playbook.investigate(target, "DOMAIN", "OFFICER_TRIGGERED")
            
            # Store evidence
            for step in result.get("evidence_chain", []):
                evidence_id = f"E-HUNT-{int(time.time())}-{step.get('step', 'X')}"
                await conn.execute(
                    """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                       ON CONFLICT (evidence_id) DO NOTHING""",
                    case_id, evidence_id,
                    step.get("step", "HUNTER"),
                    step.get("finding", ""),
                    step.get("source", "GFIN Hunter"),
                    step.get("url", ""),
                    "AUTOMATED_OSINT",
                    "HIGH" if step.get("confidence", 0) > 0.7 else "MEDIUM"
                )
            
            # Update case confidence
            confidence = result.get("confidence", 0.5)
            await conn.execute(
                "UPDATE cases SET confidence=$1, updated_date=NOW() WHERE case_id=$2",
                confidence, case_id
            )
            
            return {
                "status": "completed",
                "case_id": case_id,
                "evidence_steps": len(result.get("evidence_chain", [])),
                "confidence": confidence
            }
        except ImportError:
            return {"status": "hunter_unavailable", "case_id": case_id}
    finally:
        await conn.close()


# ==================== SEARCH EVIDENCE ====================

@router.get("/api/inv/search")
async def search_evidence(q: str = "", limit: int = 50):
    """Search across evidence, cases, and telegram intel."""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        results = {"evidence": [], "cases": [], "telegram": [], "domains": []}
        
        if q and len(q) >= 2:
            # Search evidence
            evidence = await conn.fetch(
                """SELECT * FROM evidence WHERE finding ILIKE $1 OR source_provider ILIKE $1
                   ORDER BY created_date DESC LIMIT $2""",
                f"%{q}%", limit
            )
            results["evidence"] = [dict(e) for e in evidence]
            
            # Search cases
            cases = await conn.fetch(
                """SELECT case_id, target, status, confidence, summary FROM cases
                   WHERE target ILIKE $1 OR summary ILIKE $1 OR case_id ILIKE $1
                   ORDER BY created_date DESC LIMIT $2""",
                f"%{q}%", limit
            )
            results["cases"] = [dict(c) for c in cases]
            
            # Search telegram
            tg = await conn.fetch(
                """SELECT id, group_name, message_text, scam_type, risk_level, created_at FROM telegram_intelligence
                   WHERE message_text ILIKE $1 OR group_name ILIKE $1
                   ORDER BY created_at DESC LIMIT $2""",
                f"%{q}%", limit
            )
            results["telegram"] = [dict(t) for t in tg]
            
            # Search domains
            domains = await conn.fetch(
                """SELECT domain, source, risk_level, status, first_seen FROM tracked_domains
                   WHERE domain ILIKE $1
                   ORDER BY first_seen DESC LIMIT $2""",
                f"%{q}%", limit
            )
            results["domains"] = [dict(d) for d in domains]
        
        results["total"] = sum(len(v) for v in results.values())
        return results
    finally:
        await conn.close()
