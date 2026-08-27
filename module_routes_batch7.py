"""
GFIN Module API Routes — Batch 7
Evidence Explainability, Cross-Border Requests, Federation, Unknown Fraud Discovery
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch7_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 7 API routes."""

    # ============================================================
    # EVIDENCE EXPLAINABILITY
    # ============================================================
    try:
        from evidence_explainability import EvidenceExplainabilityEngine
        _explainer = EvidenceExplainabilityEngine()
        _ee_loaded = True
    except Exception as e:
        _explainer = None
        _ee_loaded = False
        print(f"Warning: evidence_explainability not loaded: {e}")

    @app.get("/api/explainability/chain/{entity_id}")
    async def explainability_chain(entity_id: str):
        if not _ee_loaded:
            raise HTTPException(503, "Evidence explainability not available")
        try:
            chains = _explainer.get_entity_chains(entity_id) if hasattr(_explainer, 'get_entity_chains') else []
            return {"entity_id": entity_id, "chains": [c.model_dump() if hasattr(c, 'model_dump') else str(c) for c in (chains if isinstance(chains, list) else [])]}
        except Exception as e:
            return {"entity_id": entity_id, "error": str(e)}

    @app.get("/api/explainability/entity/{entity_id}")
    async def explainability_entity(entity_id: str):
        if not _ee_loaded:
            raise HTTPException(503, "Evidence explainability not available")
        try:
            explanation = _explainer.explain_entity(entity_id) if hasattr(_explainer, 'explain_entity') else {}
            return explanation.model_dump() if hasattr(explanation, 'model_dump') else explanation if isinstance(explanation, dict) else {"entity_id": entity_id, "explanation": str(explanation)}
        except Exception as e:
            return {"entity_id": entity_id, "error": str(e)}

    @app.get("/api/explainability/stats")
    async def explainability_stats():
        if not _ee_loaded:
            raise HTTPException(503, "Evidence explainability not available")
        try:
            return _explainer.stats() if hasattr(_explainer, 'stats') else {}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # CROSS-BORDER REQUESTS
    # ============================================================
    try:
        from cross_border_requests import CrossBorderRequestEngine
        _cross_border = CrossBorderRequestEngine()
        _cb_loaded = True
    except Exception as e:
        _cross_border = None
        _cb_loaded = False
        print(f"Warning: cross_border_requests not loaded: {e}")

    class CrossBorderCreateRequest(BaseModel):
        requesting_jurisdiction: str
        target_jurisdiction: str
        subject: str
        subject_type: str = "domain"
        urgency: str = "standard"
        description: str = ""

    class CrossBorderDecisionRequest(BaseModel):
        request_id: str
        decision: str = "approved"  # approved, rejected, more_info
        reason: str = ""
        reviewer: str = "system"

    @app.post("/api/cross-border/create")
    async def cross_border_create(req: CrossBorderCreateRequest):
        if not _cb_loaded:
            raise HTTPException(503, "Cross-border request engine not available")
        try:
            result = _cross_border.create_request(
                requesting_jurisdiction=req.requesting_jurisdiction,
                target_jurisdiction=req.target_jurisdiction,
                subject=req.subject,
                subject_type=req.subject_type,
                urgency=req.urgency,
                description=req.description
            )
            return {"status": "created", "request": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/cross-border/{request_id}")
    async def cross_border_get(request_id: str):
        if not _cb_loaded:
            raise HTTPException(503, "Cross-border request engine not available")
        try:
            req = _cross_border.get_request(request_id) if hasattr(_cross_border, 'get_request') else None
            if not req:
                raise HTTPException(404, "Request not found")
            return req.model_dump() if hasattr(req, 'model_dump') else req if isinstance(req, dict) else str(req)
        except HTTPException:
            raise
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/cross-border/route")
    async def cross_border_route(request_id: str = Query(...)):
        if not _cb_loaded:
            raise HTTPException(503, "Cross-border request engine not available")
        try:
            result = _cross_border.route_request(request_id) if hasattr(_cross_border, 'route_request') else {}
            return {"request_id": request_id, "routing": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/cross-border/decide")
    async def cross_border_decide(req: CrossBorderDecisionRequest):
        if not _cb_loaded:
            raise HTTPException(503, "Cross-border request engine not available")
        try:
            result = _cross_border.make_decision(
                request_id=req.request_id,
                decision=req.decision,
                reason=req.reason,
                reviewer=req.reviewer
            ) if hasattr(_cross_border, 'make_decision') else {}
            return {"status": "decided", "result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ============================================================
    # FEDERATION
    # ============================================================
    try:
        from federation import FederationNetwork
        _federation = FederationNetwork()
        _fed_loaded = True
    except Exception as e:
        _federation = None
        _fed_loaded = False
        print(f"Warning: federation not loaded: {e}")

    class FederationMessageRequest(BaseModel):
        from_jurisdiction: str
        to_jurisdiction: str
        message_type: str = "information_request"
        payload: dict = {}

    class FederationNodeRequest(BaseModel):
        jurisdiction: str
        endpoint: str = ""
        status: str = "active"
        capabilities: list = []

    @app.get("/api/federation/nodes")
    async def federation_nodes():
        if not _fed_loaded:
            raise HTTPException(503, "Federation not available")
        try:
            nodes = _federation.list_nodes() if hasattr(_federation, 'list_nodes') else []
            return {"count": len(nodes) if isinstance(nodes, list) else 0, "nodes": [n.model_dump() if hasattr(n, 'model_dump') else str(n) for n in (nodes if isinstance(nodes, list) else [])]}
        except Exception as e:
            return {"count": 0, "nodes": [], "error": str(e)}

    @app.get("/api/federation/topology")
    async def federation_topology():
        if not _fed_loaded:
            raise HTTPException(503, "Federation not available")
        try:
            topo = _federation.get_topology() if hasattr(_federation, 'get_topology') else {}
            return topo if isinstance(topo, dict) else {"topology": str(topo)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/federation/message")
    async def federation_send_message(req: FederationMessageRequest):
        if not _fed_loaded:
            raise HTTPException(503, "Federation not available")
        try:
            msg = _federation.send_message(
                from_jurisdiction=req.from_jurisdiction,
                to_jurisdiction=req.to_jurisdiction,
                message_type=req.message_type,
                payload=req.payload
            ) if hasattr(_federation, 'send_message') else {}
            return {"status": "sent", "message": msg.model_dump() if hasattr(msg, 'model_dump') else msg if isinstance(msg, dict) else str(msg)}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ============================================================
    # UNKNOWN FRAUD DISCOVERY
    # ============================================================
    try:
        from unknown_fraud_discovery import DiscoveryOrchestrator
        _discovery = DiscoveryOrchestrator()
        _ufd_loaded = True
    except Exception as e:
        _discovery = None
        _ufd_loaded = False
        print(f"Warning: unknown_fraud_discovery not loaded: {e}")

    class DiscoveryRunRequest(BaseModel):
        seed_entities: list = []
        sources: list = []
        depth: int = 2

    @app.post("/api/discovery-unknown/run")
    async def discovery_run(req: DiscoveryRunRequest):
        if not _ufd_loaded:
            raise HTTPException(503, "Unknown fraud discovery not available")
        try:
            result = _discovery.run(seed_entities=req.seed_entities, sources=req.sources) if hasattr(_discovery, 'run') else {}
            return {"result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/discovery-unknown/confirm")
    async def discovery_confirm_lead(lead_id: str = Query(...)):
        if not _ufd_loaded:
            raise HTTPException(503, "Unknown fraud discovery not available")
        try:
            result = _discovery.confirm_lead(lead_id) if hasattr(_discovery, 'confirm_lead') else {}
            return {"lead_id": lead_id, "status": "confirmed", "result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"lead_id": lead_id, "error": str(e)}

    print("   Batch 7 routes: evidence_explainability(3), cross_border(4), federation(3), unknown_fraud_discovery(2) = 12 endpoints")
