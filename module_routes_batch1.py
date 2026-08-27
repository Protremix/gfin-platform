"""
GFIN Module API Routes — Batch 1 (FIXED)
Evidence Vault, Fraud Graph, Search Platform, Compliance
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch1_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 1 API routes."""

    # ============================================================
    # EVIDENCE VAULT
    # ============================================================
    try:
        from evidence_vault import EvidenceVault
        _evidence_vault = EvidenceVault()
        _ev_loaded = True
    except Exception as e:
        _evidence_vault = None
        _ev_loaded = False
        print(f"Warning: evidence_vault not loaded: {e}")

    class EvidenceCreateRequest(BaseModel):
        case_id: str
        evidence_type: str = "document"
        content_hash: str = ""
        source: str = "manual"
        description: str = ""
        collected_by: str = "system"

    @app.post("/api/evidence/store")
    async def evidence_store(req: EvidenceCreateRequest):
        if not _ev_loaded:
            raise HTTPException(503, "Evidence vault not available")
        try:
            evidence = _evidence_vault.create(
                case_id=req.case_id,
                evidence_type=req.evidence_type,
                content_hash=req.content_hash,
                source=req.source,
                description=req.description,
                collected_by=req.collected_by
            )
            return {"status": "stored", "evidence_id": getattr(evidence, 'id', str(evidence)), "case_id": req.case_id}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/evidence/list/{case_id}")
    async def evidence_list(case_id: str):
        if not _ev_loaded:
            raise HTTPException(503, "Evidence vault not available")
        # list() takes source_id, content_type, classification — NOT case_id
        results = _evidence_vault.list(source_id=case_id)
        return {"case_id": case_id, "count": len(results), "evidence": [e.model_dump() if hasattr(e, 'model_dump') else e.dict() if hasattr(e, 'dict') else str(e) for e in results]}

    @app.get("/api/evidence/verify/{evidence_id}")
    async def evidence_verify(evidence_id: str):
        if not _ev_loaded:
            raise HTTPException(503, "Evidence vault not available")
        result = _evidence_vault.verify(evidence_id)
        return result.model_dump() if hasattr(result, 'model_dump') else result.dict() if hasattr(result, 'dict') else {"result": str(result)}

    @app.get("/api/evidence/chain/{evidence_id}")
    async def evidence_chain(evidence_id: str):
        if not _ev_loaded:
            raise HTTPException(503, "Evidence vault not available")
        chain = _evidence_vault.get_custody_chain(evidence_id)
        return {"evidence_id": evidence_id, "chain_length": len(chain), "events": [e.model_dump() if hasattr(e, 'model_dump') else e.dict() if hasattr(e, 'dict') else str(e) for e in chain]}

    # ============================================================
    # FRAUD GRAPH
    # ============================================================
    try:
        from fraud_graph import FraudGraph, GraphNode, GraphEdge
        _fraud_graph = FraudGraph()
        _fg_loaded = True
    except Exception as e:
        _fraud_graph = None
        _fg_loaded = False
        print(f"Warning: fraud_graph not loaded: {e}")

    class AddNodeRequest(BaseModel):
        node_id: str
        node_type: str = "entity"
        label: str = ""
        properties: dict = {}

    class AddEdgeRequest(BaseModel):
        source_id: str
        target_id: str
        edge_type: str = "related"
        properties: dict = {}

    @app.get("/api/graph/stats")
    async def graph_stats():
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        return _fraud_graph.get_stats()

    @app.get("/api/graph/nodes/{node_id}")
    async def graph_get_node(node_id: str):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        node = _fraud_graph.get_node(node_id)
        if not node:
            raise HTTPException(404, "Node not found")
        return {"node": node.__dict__ if hasattr(node, '__dict__') else str(node)}

    @app.post("/api/graph/add-node")
    async def graph_add_node(req: AddNodeRequest):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        node = GraphNode(id=req.node_id, type=req.node_type, label=req.label, properties=req.properties)
        result = _fraud_graph.add_node(node)
        return {"status": "added", "node_id": result}

    @app.post("/api/graph/add-edge")
    async def graph_add_edge(req: AddEdgeRequest):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        edge = GraphEdge(source=req.source_id, target=req.target_id, type=req.edge_type, properties=req.properties)
        result = _fraud_graph.add_edge(edge)
        return {"status": "added", "edge_id": result}

    @app.get("/api/graph/neighbors/{node_id}")
    async def graph_neighbors(node_id: str, max_depth: int = Query(1, ge=1, le=5)):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        neighbors = _fraud_graph.get_neighbors(node_id, max_depth=max_depth)
        return {"node_id": node_id, "neighbors": neighbors}

    @app.get("/api/graph/traverse")
    async def graph_traverse(start: str = Query(...), end: str = Query(None), max_depth: int = Query(3, le=10)):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        if end:
            path = _fraud_graph.find_path(start, end, max_depth=max_depth)
            return {"start": start, "end": end, "path": path}
        result = _fraud_graph.traverse(start, max_depth=max_depth)
        return {"start": start, "traversal": result.__dict__ if hasattr(result, '__dict__') else str(result)}

    @app.get("/api/graph/central")
    async def graph_central(top_n: int = Query(10, le=50)):
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        nodes = _fraud_graph.find_central_nodes(top_n=top_n)
        return {"central_nodes": [{"node_id": n[0], "degree": n[1]} for n in nodes]}

    @app.get("/api/graph/export")
    async def graph_export():
        if not _fg_loaded:
            raise HTTPException(503, "Fraud graph not available")
        return _fraud_graph.export_graph()

    # ============================================================
    # SEARCH PLATFORM
    # ============================================================
    try:
        from search_platform import EnhancedSearchService, SearchType, SearchQueryV2
        _search = EnhancedSearchService()
        _search_loaded = True
    except Exception as e:
        _search = None
        _search_loaded = False
        print(f"Warning: search_platform not loaded: {e}")

    @app.get("/api/search")
    async def search_query(
        q: str = Query(..., min_length=1),
        type: str = Query("entity"),
        limit: int = Query(20, le=100)
    ):
        """Full-text search across all entities. Valid types: exact, normalized, fuzzy, semantic, entity, graph_assisted, campaign, infrastructure, report"""
        if not _search_loaded:
            raise HTTPException(503, "Search platform not available")
        try:
            query = SearchQueryV2(query=q, search_type=type, limit=limit)
            results = _search.search(query)
            return results.model_dump() if hasattr(results, 'model_dump') else results.dict() if hasattr(results, 'dict') else {"results": str(results)}
        except Exception as e:
            return {"query": q, "results": [], "error": str(e)}

    class AdvancedSearchRequest(BaseModel):
        query: str
        search_type: str = "entity"
        limit: int = 20
        filters: dict = {}

    @app.post("/api/search/advanced")
    async def search_advanced(req: AdvancedSearchRequest):
        if not _search_loaded:
            raise HTTPException(503, "Search platform not available")
        try:
            query = SearchQueryV2(query=req.query, search_type=req.search_type, limit=req.limit)
            results = _search.search(query)
            return results.model_dump() if hasattr(results, 'model_dump') else results.dict() if hasattr(results, 'dict') else {"results": str(results)}
        except Exception as e:
            return {"query": req.query, "results": [], "error": str(e)}

    # ============================================================
    # COMPLIANCE
    # ============================================================
    try:
        from compliance import ComplianceService, DataClassification, AccessorRole
        _compliance = ComplianceService()
        _comp_loaded = True
    except Exception as e:
        _compliance = None
        _comp_loaded = False
        print(f"Warning: compliance not loaded: {e}")

    @app.get("/api/compliance/check")
    async def compliance_check(
        accessor_role: str = Query(...),
        data_classification: str = Query(...)
    ):
        if not _comp_loaded:
            raise HTTPException(503, "Compliance service not available")
        result = _compliance.check_access(accessor_role, data_classification)
        return result.model_dump() if hasattr(result, 'model_dump') else result.dict() if hasattr(result, 'dict') else {"check": str(result)}

    @app.get("/api/compliance/retention/{classification}")
    async def compliance_retention(classification: str):
        if not _comp_loaded:
            raise HTTPException(503, "Compliance service not available")
        policy = _compliance.get_retention_policy(classification)
        return policy.model_dump() if policy and hasattr(policy, 'model_dump') else policy.dict() if policy and hasattr(policy, 'dict') else {"classification": classification, "policy": None}

    @app.get("/api/compliance/violations")
    async def compliance_violations(resolved: bool = Query(False)):
        if not _comp_loaded:
            raise HTTPException(503, "Compliance service not available")
        violations = _compliance.get_violations()
        return {"count": len(violations), "violations": [v.model_dump() if hasattr(v, 'model_dump') else v.dict() if hasattr(v, 'dict') else str(v) for v in violations]}

    @app.get("/api/compliance/stats")
    async def compliance_stats():
        if not _comp_loaded:
            raise HTTPException(503, "Compliance service not available")
        # These are PROPERTIES, not methods
        return {
            "checks": _compliance.check_count,
            "violations": _compliance.violation_count,
            "unresolved": _compliance.unresolved_violation_count
        }

    print("   Batch 1 routes: evidence_vault(4), fraud_graph(8), search_platform(2), compliance(4) = 18 endpoints")
