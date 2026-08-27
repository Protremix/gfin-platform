"""
GFIN Module API Routes — Batch 3 (FIXED v2)
Investigation Orchestrator, Police Console, Entity Resolution
Uses shared investigation_store for cross-module integration.
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch3_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 3 API routes."""

    # Import shared investigation store
    try:
        from investigation_store import investigation_store
    except Exception as e:
        print(f"Warning: investigation_store not loaded: {e}")
        investigation_store = None

    # ============================================================
    # INVESTIGATION ORCHESTRATOR
    # ============================================================
    try:
        from investigation_orchestrator import (
            InvestigationTool, InvestigationPlan, InvestigationResult,
            InvestigationStep, Evidence, Claim, StepStatus, UserRole
        )
        _io_loaded = True
    except Exception as e:
        _io_loaded = False
        print(f"Warning: investigation_orchestrator not loaded: {e}")

    class InvestigationStartRequest(BaseModel):
        case_id: str
        subject: str
        subject_type: str = "domain"
        operator_id: str = "system"

    class InvestigationStepRequest(BaseModel):
        step_name: str
        tool_name: str = "search_web"
        params: dict = {}

    @app.get("/api/investigation/list")
    async def investigation_list(limit: int = Query(20, le=100)):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        if investigation_store:
            results = investigation_store.list(limit=limit)
            return {"count": len(results), "investigations": results}
        return {"count": 0, "investigations": []}

    @app.post("/api/investigation/start")
    async def investigation_start(req: InvestigationStartRequest):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        investigation_id = f"INV-{int(time.time())}-{req.case_id[-6:]}"
        plan = InvestigationPlan(
            id=investigation_id,
            target=req.subject,
            objective=f"Investigate {req.subject_type}: {req.subject} for case {req.case_id}"
        )
        if investigation_store:
            record = investigation_store.create(
                investigation_id=investigation_id,
                case_id=req.case_id,
                subject=req.subject,
                subject_type=req.subject_type,
                operator=req.operator_id
            )
            record["plan"] = plan.model_dump() if hasattr(plan, 'model_dump') else str(plan)
            return {"status": "started", "investigation_id": investigation_id, "plan": record["plan"]}
        return {"status": "started", "investigation_id": investigation_id, "plan": str(plan)}

    @app.get("/api/investigation/{investigation_id}")
    async def investigation_get(investigation_id: str):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        if investigation_store:
            inv = investigation_store.get(investigation_id)
            if not inv:
                raise HTTPException(404, "Investigation not found")
            return inv
        raise HTTPException(503, "Investigation store not available")

    @app.post("/api/investigation/{investigation_id}/step")
    async def investigation_add_step(investigation_id: str, req: InvestigationStepRequest):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        if investigation_store:
            step = investigation_store.add_step(
                investigation_id=investigation_id,
                step_name=req.step_name,
                tool_name=req.tool_name,
                params=req.params
            )
            if step:
                return {"status": "added", "step": step}
        raise HTTPException(404, "Investigation not found")

    @app.get("/api/investigation/{investigation_id}/evidence")
    async def investigation_evidence(investigation_id: str):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        if investigation_store:
            inv = investigation_store.get(investigation_id)
            if inv:
                return {"investigation_id": investigation_id, "evidence_count": len(inv["evidence"]), "evidence": inv["evidence"]}
        raise HTTPException(404, "Investigation not found")

    @app.post("/api/investigation/{investigation_id}/synthesize")
    async def investigation_synthesize(investigation_id: str):
        if not _io_loaded:
            raise HTTPException(503, "Investigation orchestrator not available")
        if investigation_store:
            inv = investigation_store.get(investigation_id)
            if inv:
                inv["status"] = "synthesized"
                return {
                    "investigation_id": investigation_id,
                    "status": "synthesized",
                    "total_steps": len(inv["steps"]),
                    "total_evidence": len(inv["evidence"]),
                    "total_claims": len(inv["claims"]),
                    "synthesis": "Investigation synthesized — see steps and evidence for details"
                }
        raise HTTPException(404, "Investigation not found")

    # ============================================================
    # POLICE CONSOLE
    # ============================================================
    try:
        from police_console import (
            PoliceConsoleService, ConsoleSession, InvestigationWorkspace,
            ConsoleAuditLogger, ObservationSubmission, ConsoleRole
        )
        _console_service = PoliceConsoleService()
        _pc_loaded = True
    except Exception as e:
        _console_service = None
        _pc_loaded = False
        print(f"Warning: police_console not loaded: {e}")

    class ConsoleSessionRequest(BaseModel):
        officer_id: str
        officer_name: str = ""
        role: str = "investigator"

    class WorkspaceCreateRequest(BaseModel):
        case_id: str
        name: str = ""
        officer_id: str = "system"

    class ObservationRequest(BaseModel):
        workspace_id: str
        observation: str
        author: str = "system"

    @app.post("/api/console/session")
    async def console_create_session(req: ConsoleSessionRequest):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        try:
            session = _console_service.create_session(
                officer_id=req.officer_id,
                officer_name=req.officer_name,
                role=req.role
            )
            return {"status": "session_created", "session": session.model_dump() if hasattr(session, 'model_dump') else session.dict() if hasattr(session, 'dict') else {"officer_id": req.officer_id}}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/console/dashboard")
    async def console_dashboard():
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        try:
            return {
                "sessions": _console_service.session_count if isinstance(_console_service.session_count, (int, float)) else _console_service.session_count(),
                "workspaces": _console_service.workspace_count if isinstance(_console_service.workspace_count, (int, float)) else _console_service.workspace_count(),
                "observations": _console_service.observation_count if isinstance(_console_service.observation_count, (int, float)) else _console_service.observation_count(),
                "investigations": investigation_store.count() if investigation_store else 0
            }
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/console/cases")
    async def console_cases(limit: int = Query(20, le=100)):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        return {"count": 0, "cases": []}

    @app.post("/api/console/workspace")
    async def console_create_workspace(req: WorkspaceCreateRequest):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        try:
            workspace = _console_service.create_workspace(
                case_id=req.case_id,
                name=req.name,
                officer_id=req.officer_id
            )
            return {"status": "created", "workspace": workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.dict() if hasattr(workspace, 'dict') else {"case_id": req.case_id}}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/console/workspace/{workspace_id}")
    async def console_get_workspace(workspace_id: str):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        workspace = _console_service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(404, "Workspace not found")
        return {"workspace": workspace.model_dump() if hasattr(workspace, 'model_dump') else workspace.dict() if hasattr(workspace, 'dict') else str(workspace)}

    @app.post("/api/console/observation")
    async def console_add_observation(req: ObservationRequest):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        try:
            _console_service.submit_observation(
                workspace_id=req.workspace_id,
                observation=req.observation,
                author=req.author
            )
            return {"status": "submitted", "workspace_id": req.workspace_id}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/console/audit")
    async def console_audit(limit: int = Query(50, le=200)):
        if not _pc_loaded:
            raise HTTPException(503, "Police console not available")
        try:
            audit = _console_service.audit()
            entries = audit.get_entries(limit=limit) if hasattr(audit, 'get_entries') else []
            return {"count": len(entries), "entries": [e.model_dump() if hasattr(e, 'model_dump') else e.dict() if hasattr(e, 'dict') else str(e) for e in entries]}
        except Exception as e:
            return {"count": 0, "entries": [], "error": str(e)}

    # ============================================================
    # ENTITY RESOLUTION
    # ============================================================
    try:
        from entity_resolution import (
            normalize_phone, normalize_email, normalize_domain,
            normalize_url, normalize_ip, normalize_crypto_address,
            normalize_telegram, normalize_social_account
        )
        _er_loaded = True
    except Exception as e:
        _er_loaded = False
        print(f"Warning: entity_resolution not loaded: {e}")

    class NormalizeRequest(BaseModel):
        value: str
        type: str = "auto"
        platform: str = ""
        blockchain: str = ""

    @app.post("/api/entity/normalize")
    async def entity_normalize(req: NormalizeRequest):
        if not _er_loaded:
            raise HTTPException(503, "Entity resolution not available")
        results = {}
        try:
            if req.type in ("auto", "phone"):
                results["phone"] = normalize_phone(req.value)
            if req.type in ("auto", "email"):
                results["email"] = normalize_email(req.value)
            if req.type in ("auto", "domain"):
                results["domain"] = normalize_domain(req.value)
            if req.type in ("auto", "url"):
                results["url"] = normalize_url(req.value)
            if req.type in ("auto", "ip"):
                results["ip"] = normalize_ip(req.value)
            if req.type in ("auto", "crypto"):
                results["crypto"] = normalize_crypto_address(req.value, req.blockchain or "bitcoin")
            if req.type in ("auto", "telegram"):
                results["telegram"] = normalize_telegram(req.value)
            if req.type in ("auto", "social"):
                results["social"] = normalize_social_account(req.value, req.platform or "telegram")
        except Exception as e:
            results["error"] = str(e)
        return {"input": req.value, "normalized": results}

    @app.get("/api/entity/types")
    async def entity_types():
        if not _er_loaded:
            raise HTTPException(503, "Entity resolution not available")
        return {
            "types": ["phone", "email", "domain", "url", "ip", "crypto", "telegram", "social"],
            "blockchains": ["bitcoin", "ethereum", "tron", "solana", "ton", "litecoin", "dogecoin"],
            "social_platforms": ["telegram", "facebook", "twitter", "instagram", "linkedin"]
        }

    print("   Batch 3 routes: investigation_orchestrator(5), police_console(6), entity_resolution(2) = 13 endpoints")
