"""
GFIN Module API Routes — Batch 6
Crypto Intelligence, Temporal Intelligence, Infrastructure Intelligence
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch6_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 6 API routes."""

    # ============================================================
    # CRYPTO INTELLIGENCE
    # ============================================================
    try:
        from crypto_intelligence import CryptoIntelligenceService
        _crypto = CryptoIntelligenceService()
        _ci_loaded = True
    except Exception as e:
        _crypto = None
        _ci_loaded = False
        print(f"Warning: crypto_intelligence not loaded: {e}")

    class WalletRegisterRequest(BaseModel):
        address: str
        blockchain: str = "bitcoin"
        label: str = ""
        risk_level: str = "unknown"

    class TraceFundsRequest(BaseModel):
        address: str
        depth: int = 3
        blockchain: str = "bitcoin"

    @app.post("/api/crypto/wallet")
    async def crypto_register_wallet(req: WalletRegisterRequest):
        if not _ci_loaded:
            raise HTTPException(503, "Crypto intelligence not available")
        try:
            wallet = _crypto.register_wallet(req.address, req.blockchain, req.label)
            if req.risk_level != "unknown":
                _crypto.set_wallet_risk(req.address, req.risk_level)
            return {"status": "registered", "wallet": wallet.model_dump() if hasattr(wallet, 'model_dump') else wallet if isinstance(wallet, dict) else str(wallet)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/crypto/wallet/{address}")
    async def crypto_get_wallet(address: str):
        if not _ci_loaded:
            raise HTTPException(503, "Crypto intelligence not available")
        try:
            wallet = _crypto.get_wallet(address)
            if not wallet:
                raise HTTPException(404, "Wallet not found")
            return wallet.model_dump() if hasattr(wallet, 'model_dump') else wallet if isinstance(wallet, dict) else {"address": address}
        except HTTPException:
            raise
        except Exception as e:
            return {"address": address, "error": str(e)}

    @app.get("/api/crypto/wallets")
    async def crypto_list_wallets(limit: int = Query(20, le=100)):
        if not _ci_loaded:
            raise HTTPException(503, "Crypto intelligence not available")
        try:
            wallets = _crypto.list_wallets()
            return {"count": len(wallets) if isinstance(wallets, list) else _crypto.wallet_count(), "wallets": [w.model_dump() if hasattr(w, 'model_dump') else str(w) for w in (wallets if isinstance(wallets, list) else [])[:limit]]}
        except Exception as e:
            return {"count": 0, "wallets": [], "error": str(e)}

    @app.post("/api/crypto/trace")
    async def crypto_trace_funds(req: TraceFundsRequest):
        if not _ci_loaded:
            raise HTTPException(503, "Crypto intelligence not available")
        try:
            trace = _crypto.trace_funds(req.address, depth=req.depth) if hasattr(_crypto, 'trace_funds') else {}
            return {"address": req.address, "blockchain": req.blockchain, "trace": trace.model_dump() if hasattr(trace, 'model_dump') else trace if isinstance(trace, dict) else str(trace)}
        except Exception as e:
            return {"address": req.address, "error": str(e)}

    @app.post("/api/crypto/risk")
    async def crypto_assess_risk(address: str = Query(...)):
        if not _ci_loaded:
            raise HTTPException(503, "Crypto intelligence not available")
        try:
            risk = _crypto.assess_risk(address) if hasattr(_crypto, 'assess_risk') else {"address": address, "risk": "unknown"}
            return {"address": address, "risk_assessment": risk.model_dump() if hasattr(risk, 'model_dump') else risk if isinstance(risk, dict) else str(risk)}
        except Exception as e:
            return {"address": address, "error": str(e)}

    # ============================================================
    # TEMPORAL INTELLIGENCE
    # ============================================================
    try:
        from temporal_intelligence import TemporalIntelligenceService
        _temporal = TemporalIntelligenceService()
        _ti_loaded = True
    except Exception as e:
        _temporal = None
        _ti_loaded = False
        print(f"Warning: temporal_intelligence not loaded: {e}")

    @app.get("/api/temporal/timeline/{entity_id}")
    async def temporal_timeline(entity_id: str):
        if not _ti_loaded:
            raise HTTPException(503, "Temporal intelligence not available")
        try:
            timeline = _temporal.get_entity_timeline(entity_id) if hasattr(_temporal, 'get_entity_timeline') else []
            return {"entity_id": entity_id, "timeline": [t.model_dump() if hasattr(t, 'model_dump') else str(t) for t in (timeline if isinstance(timeline, list) else [])]}
        except Exception as e:
            return {"entity_id": entity_id, "error": str(e)}

    @app.get("/api/temporal/changes")
    async def temporal_changes(start: str = Query(...), end: str = Query(...)):
        if not _ti_loaded:
            raise HTTPException(503, "Temporal intelligence not available")
        try:
            changes = _temporal.get_changes_between(start, end) if hasattr(_temporal, 'get_changes_between') else []
            return {"count": len(changes) if isinstance(changes, list) else 0, "changes": changes if isinstance(changes, list) else str(changes)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/temporal/stats")
    async def temporal_stats():
        if not _ti_loaded:
            raise HTTPException(503, "Temporal intelligence not available")
        try:
            stats = _temporal.stats() if hasattr(_temporal, 'stats') else {}
            return stats if isinstance(stats, dict) else {"stats": str(stats)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/temporal/event")
    async def temporal_record_event(entity_id: str = Query(...), event_type: str = Query(...), data: dict = Body(default={})):
        if not _ti_loaded:
            raise HTTPException(503, "Temporal intelligence not available")
        try:
            result = _temporal.record_event(entity_id, event_type, **data) if hasattr(_temporal, 'record_event') else {}
            return {"status": "recorded", "result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ============================================================
    # INFRASTRUCTURE INTELLIGENCE
    # ============================================================
    try:
        from infrastructure_intelligence import InfrastructureIntelligenceService
        _infra = InfrastructureIntelligenceService()
        _ii_loaded = True
    except Exception as e:
        _infra = None
        _ii_loaded = False
        print(f"Warning: infrastructure_intelligence not loaded: {e}")

    @app.get("/api/infrastructure/domain/{domain}")
    async def infra_domain_profile(domain: str):
        if not _ii_loaded:
            raise HTTPException(503, "Infrastructure intelligence not available")
        try:
            profile = _infra.get_domain_profile(domain) if hasattr(_infra, 'get_domain_profile') else {}
            return profile.model_dump() if hasattr(profile, 'model_dump') else profile if isinstance(profile, dict) else {"domain": domain, "profile": str(profile)}
        except Exception as e:
            return {"domain": domain, "error": str(e)}

    @app.get("/api/infrastructure/dns/{domain}")
    async def infra_dns_records(domain: str):
        if not _ii_loaded:
            raise HTTPException(503, "Infrastructure intelligence not available")
        try:
            records = _infra.get_dns_records(domain) if hasattr(_infra, 'get_dns_records') else []
            return {"domain": domain, "records": [r.model_dump() if hasattr(r, 'model_dump') else str(r) for r in (records if isinstance(records, list) else [])]}
        except Exception as e:
            return {"domain": domain, "error": str(e)}

    @app.get("/api/infrastructure/ip/{ip}")
    async def infra_ip_info(ip: str):
        if not _ii_loaded:
            raise HTTPException(503, "Infrastructure intelligence not available")
        try:
            info = _infra.get_ip_info(ip) if hasattr(_infra, 'get_ip_info') else {}
            return info.model_dump() if hasattr(info, 'model_dump') else info if isinstance(info, dict) else {"ip": ip, "info": str(info)}
        except Exception as e:
            return {"ip": ip, "error": str(e)}

    @app.get("/api/infrastructure/metrics")
    async def infra_metrics():
        if not _ii_loaded:
            raise HTTPException(503, "Infrastructure intelligence not available")
        try:
            return _infra.get_metrics() if hasattr(_infra, 'get_metrics') else {}
        except Exception as e:
            return {"error": str(e)}

    print("   Batch 6 routes: crypto_intelligence(5), temporal_intelligence(4), infrastructure_intelligence(4) = 13 endpoints")
