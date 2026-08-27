"""
GFIN Module API Routes — Batch 4
Campaign DNA (Clustering), Web Discovery (Social Monitoring), 
Proactive ScamHunter, Domain Intelligence, Pattern Engine
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch4_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 4 API routes."""

    # ============================================================
    # CAMPAIGN DNA (Clustering)
    # ============================================================
    try:
        from campaign_dna import CampaignDNAEngine, CampaignSignature
        _dna_engine = CampaignDNAEngine()
        _dna_loaded = True
    except Exception as e:
        _dna_engine = None
        _dna_loaded = False
        print(f"Warning: campaign_dna not loaded: {e}")

    class CampaignFeatureRequest(BaseModel):
        campaign_id: str
        reports: list = []
        entities: list = []
        metadata: dict = {}

    class SimilarityRequest(BaseModel):
        campaign_id_a: str
        campaign_id_b: str

    @app.post("/api/dna/extract")
    async def dna_extract_features(req: CampaignFeatureRequest):
        if not _dna_loaded:
            raise HTTPException(503, "Campaign DNA engine not available")
        try:
            features = _dna_engine.extract_features(
                campaign_id=req.campaign_id,
                reports=req.reports,
                entities=req.entities,
                metadata=req.metadata
            )
            return {"campaign_id": req.campaign_id, "features": features}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/dna/signature")
    async def dna_generate_signature(req: CampaignFeatureRequest):
        if not _dna_loaded:
            raise HTTPException(503, "Campaign DNA engine not available")
        try:
            features = _dna_engine.extract_features(
                campaign_id=req.campaign_id,
                reports=req.reports,
                entities=req.entities,
                metadata=req.metadata
            )
            signature = _dna_engine.generate_signature(req.campaign_id, features)
            return {"signature": signature.to_dict() if hasattr(signature, 'to_dict') else str(signature)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/dna/similarity")
    async def dna_compute_similarity(req: SimilarityRequest):
        if not _dna_loaded:
            raise HTTPException(503, "Campaign DNA engine not available")
        try:
            similarity = _dna_engine.compute_similarity(req.campaign_id_a, req.campaign_id_b)
            return {"campaign_a": req.campaign_id_a, "campaign_b": req.campaign_id_b, "similarity": similarity}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/dna/similar/{campaign_id}")
    async def dna_find_similar(campaign_id: str, threshold: float = Query(0.7, ge=0.0, le=1.0)):
        if not _dna_loaded:
            raise HTTPException(503, "Campaign DNA engine not available")
        try:
            similar = _dna_engine.find_similar_campaigns(campaign_id, threshold=threshold)
            return {"campaign_id": campaign_id, "similar_campaigns": similar}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/dna/explain")
    async def dna_explain_similarity(req: SimilarityRequest):
        if not _dna_loaded:
            raise HTTPException(503, "Campaign DNA engine not available")
        try:
            explanation = _dna_engine.explain_similarity(req.campaign_id_a, req.campaign_id_b)
            return explanation if isinstance(explanation, dict) else {"explanation": str(explanation)}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ============================================================
    # WEB DISCOVERY (Social/Web Monitoring)
    # ============================================================
    try:
        from web_discovery import WebDiscoveryEngine
        _web_discovery = WebDiscoveryEngine()
        _wd_loaded = True
    except Exception as e:
        _web_discovery = None
        _wd_loaded = False
        print(f"Warning: web_discovery not loaded: {e}")

    class SeedRequest(BaseModel):
        url: str
        priority: int = 5
        depth: int = 1
        metadata: dict = {}

    @app.post("/api/discovery/seed")
    async def discovery_submit_seed(req: SeedRequest):
        if not _wd_loaded:
            raise HTTPException(503, "Web discovery not available")
        try:
            job = _web_discovery.submit_seed(req.url, priority=req.priority)
            return {"status": "queued", "job": job.model_dump() if hasattr(job, 'model_dump') else str(job)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/discovery/process")
    async def discovery_process():
        if not _wd_loaded:
            raise HTTPException(503, "Web discovery not available")
        try:
            results = _web_discovery.process_all()
            return {"processed": len(results), "results": [r.model_dump() if hasattr(r, 'model_dump') else str(r) for r in results]}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/discovery/job/{job_id}")
    async def discovery_get_job(job_id: str):
        if not _wd_loaded:
            raise HTTPException(503, "Web discovery not available")
        job = _web_discovery.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {"job": job.model_dump() if hasattr(job, 'model_dump') else str(job)}

    @app.get("/api/discovery/metrics")
    async def discovery_metrics():
        if not _wd_loaded:
            raise HTTPException(503, "Web discovery not available")
        metrics = _web_discovery.get_metrics()
        return metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics if isinstance(metrics, dict) else {"metrics": str(metrics)}

    # ============================================================
    # PROACTIVE SCAMHUNTER (Social Monitoring)
    # ============================================================
    try:
        from proactive_scam_hunter import ProactiveScamHunter
        _scam_hunter = ProactiveScamHunter()
        _sh_loaded = True
    except Exception as e:
        _scam_hunter = None
        _sh_loaded = False
        print(f"Warning: proactive_scam_hunter not loaded: {e}")

    @app.post("/api/scamhunter/scan-telegram")
    async def scamhunter_scan_telegram(query: str = Query(...), limit: int = Query(20, le=100)):
        if not _sh_loaded:
            raise HTTPException(503, "ScamHunter not available")
        try:
            results = _scam_hunter.scan_telegram_for_scams(query, limit=limit) if hasattr(_scam_hunter, 'scan_telegram_for_scams') else []
            return {"query": query, "results": len(results) if isinstance(results, list) else 0, "data": results}
        except Exception as e:
            return {"query": query, "results": 0, "error": str(e)}

    @app.post("/api/scamhunter/scan-domain")
    async def scamhunter_scan_domain(domain: str = Query(...)):
        if not _sh_loaded:
            raise HTTPException(503, "ScamHunter not available")
        try:
            result = _scam_hunter.check_new_domain(domain) if hasattr(_scam_hunter, 'check_new_domain') else {}
            return {"domain": domain, "result": result}
        except Exception as e:
            return {"domain": domain, "error": str(e)}

    @app.post("/api/scamhunter/proactive")
    async def scamhunter_proactive_scan():
        if not _sh_loaded:
            raise HTTPException(503, "ScamHunter not available")
        try:
            result = _scam_hunter.proactive_scan() if hasattr(_scam_hunter, 'proactive_scan') else {}
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/scamhunter/trends")
    async def scamhunter_trends():
        if not _sh_loaded:
            raise HTTPException(503, "ScamHunter not available")
        try:
            trends = _scam_hunter.analyze_trends() if hasattr(_scam_hunter, 'analyze_trends') else {}
            return {"trends": trends}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/scamhunter/investigate")
    async def scamhunter_investigate(target: str = Query(...)):
        if not _sh_loaded:
            raise HTTPException(503, "ScamHunter not available")
        try:
            result = _scam_hunter.full_investigation(target) if hasattr(_scam_hunter, 'full_investigation') else {}
            return {"target": target, "result": result}
        except Exception as e:
            return {"target": target, "error": str(e)}

    # ============================================================
    # DOMAIN INTELLIGENCE
    # ============================================================
    try:
        from domain_intelligence import DomainIntelligenceService
        _domain_intel = DomainIntelligenceService()
        _di_loaded = True
    except Exception as e:
        _domain_intel = None
        _di_loaded = False
        print(f"Warning: domain_intelligence not loaded: {e}")

    @app.get("/api/domain/profile/{domain}")
    async def domain_profile(domain: str):
        if not _di_loaded:
            raise HTTPException(503, "Domain intelligence not available")
        try:
            profile = _domain_intel.get_domain_profile(domain)
            return profile.model_dump() if hasattr(profile, 'model_dump') else profile if isinstance(profile, dict) else {"domain": domain, "profile": str(profile)}
        except Exception as e:
            return {"domain": domain, "error": str(e)}

    @app.post("/api/domain/rdap")
    async def domain_register_rdap(domain: str = Query(...), rdap_data: dict = Body(default={})):
        if not _di_loaded:
            raise HTTPException(503, "Domain intelligence not available")
        try:
            result = _domain_intel.register_rdap_info(domain, rdap_data)
            return {"status": "registered", "domain": domain, "result": result.model_dump() if hasattr(result, 'model_dump') else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/domain/related")
    async def domain_add_related(domain: str = Query(...), related_domain: str = Query(...)):
        if not _di_loaded:
            raise HTTPException(503, "Domain intelligence not available")
        try:
            _domain_intel.add_related_domain(domain, related_domain)
            return {"status": "linked", "domain": domain, "related": related_domain}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/domain/metrics")
    async def domain_metrics():
        if not _di_loaded:
            raise HTTPException(503, "Domain intelligence not available")
        try:
            return _domain_intel.get_metrics() if hasattr(_domain_intel, 'get_metrics') else {"metrics": "not available"}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # PATTERN ENGINE
    # ============================================================
    try:
        from pattern_engine import PatternEngine
        _pattern_engine = PatternEngine()
        _pe_loaded = True
    except Exception as e:
        _pattern_engine = None
        _pe_loaded = False
        print(f"Warning: pattern_engine not loaded: {e}")

    class PatternDetectRequest(BaseModel):
        entities: list = []
        reports: list = []
        check_type: str = "all"  # shared_infrastructure, contact_reuse, payment_correlation, similar_content

    @app.post("/api/patterns/detect")
    async def patterns_detect(req: PatternDetectRequest):
        if not _pe_loaded:
            raise HTTPException(503, "Pattern engine not available")
        try:
            results = {}
            checks = [req.check_type] if req.check_type != "all" else [
                "shared_infrastructure", "contact_reuse", "payment_correlation", "similar_content"
            ]
            method_map = {
                "shared_infrastructure": "detect_shared_infrastructure",
                "contact_reuse": "detect_contact_reuse",
                "payment_correlation": "detect_payment_correlation",
                "similar_content": "detect_similar_content",
            }
            for check in checks:
                method = method_map.get(check)
                if method and hasattr(_pattern_engine, method):
                    fn = getattr(_pattern_engine, method)
                    result = fn(req.entities if check != "similar_content" else req.reports)
                    results[check] = result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)
            return {"detected_patterns": results}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/patterns/fraud-network")
    async def patterns_fraud_network(req: PatternDetectRequest):
        if not _pe_loaded:
            raise HTTPException(503, "Pattern engine not available")
        try:
            result = _pattern_engine.detect_potential_fraud_network(req.entities) if hasattr(_pattern_engine, 'detect_potential_fraud_network') else {}
            return {"fraud_network": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/patterns/explain")
    async def patterns_explain(pattern_id: str = Query(...)):
        if not _pe_loaded:
            raise HTTPException(503, "Pattern engine not available")
        try:
            result = _pattern_engine.explain_pattern(pattern_id) if hasattr(_pattern_engine, 'explain_pattern') else {}
            return {"explanation": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/patterns/infrastructure-cluster")
    async def patterns_infra_cluster():
        if not _pe_loaded:
            raise HTTPException(503, "Pattern engine not available")
        try:
            result = _pattern_engine.detect_infrastructure_cluster([]) if hasattr(_pattern_engine, 'detect_infrastructure_cluster') else []
            return {"clusters": len(result) if isinstance(result, list) else 0, "data": result}
        except Exception as e:
            return {"error": str(e)}

    print("   Batch 4 routes: campaign_dna(5), web_discovery(4), scamhunter(5), domain_intel(4), pattern_engine(4) = 22 endpoints")
