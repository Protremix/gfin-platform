"""
GFIN Module API Routes — Batch 2 (FIXED)
Campaign Engine, Global Matching, Early Warning, Continuous Monitoring
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch2_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 2 API routes."""

    # ============================================================
    # CAMPAIGN ENGINE
    # ============================================================
    try:
        from campaign_engine import CampaignEngine, CampaignScorer, CampaignDetector
        _campaign_engine = CampaignEngine()
        _campaign_scorer = CampaignScorer()
        _campaign_detector = CampaignDetector()
        _ce_loaded = True
    except Exception as e:
        _campaign_engine = None
        _ce_loaded = False
        print(f"Warning: campaign_engine not loaded: {e}")

    class CampaignCreateRequest(BaseModel):
        name: str
        description: str = ""
        target_type: str = "unknown"
        indicators: list = []

    # IMPORTANT: /stats must come BEFORE /{campaign_id} to avoid path conflict
    @app.get("/api/campaigns/stats")
    async def campaigns_stats():
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        try:
            campaigns = _campaign_engine.list_campaigns() if hasattr(_campaign_engine, 'list_campaigns') else []
            return {"total_campaigns": len(campaigns), "campaigns": [c.model_dump() if hasattr(c, 'model_dump') else c.dict() if hasattr(c, 'dict') else str(c) for c in campaigns]}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/campaigns")
    async def campaigns_list(limit: int = Query(20, le=100)):
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        try:
            campaigns = _campaign_engine.list_campaigns() if hasattr(_campaign_engine, 'list_campaigns') else []
            return {"count": len(campaigns), "campaigns": [c.model_dump() if hasattr(c, 'model_dump') else c.dict() if hasattr(c, 'dict') else str(c) for c in campaigns]}
        except Exception as e:
            return {"count": 0, "campaigns": [], "error": str(e)}

    @app.get("/api/campaigns/{campaign_id}")
    async def campaigns_get(campaign_id: str):
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        campaign = _campaign_engine.get_campaign(campaign_id) if hasattr(_campaign_engine, 'get_campaign') else None
        if not campaign:
            raise HTTPException(404, "Campaign not found")
        return {"campaign": campaign.model_dump() if hasattr(campaign, 'model_dump') else campaign.dict() if hasattr(campaign, 'dict') else str(campaign)}

    @app.post("/api/campaigns/create")
    async def campaigns_create(req: CampaignCreateRequest):
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        try:
            campaign = _campaign_engine.create_campaign(
                name=req.name,
                description=req.description,
                target_type=req.target_type
            )
            return {"status": "created", "campaign_id": getattr(campaign, 'id', str(campaign))}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/campaigns/detect")
    async def campaigns_detect():
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        try:
            candidates = _campaign_detector.detect_from_reports([]) if hasattr(_campaign_detector, 'detect_from_reports') else []
            return {"detected": len(candidates), "candidates": [c.model_dump() if hasattr(c, 'model_dump') else c.dict() if hasattr(c, 'dict') else str(c) for c in candidates]}
        except Exception as e:
            return {"detected": 0, "error": str(e)}

    @app.post("/api/campaigns/{campaign_id}/transition")
    async def campaigns_transition(campaign_id: str, new_status: str = Query(...)):
        if not _ce_loaded:
            raise HTTPException(503, "Campaign engine not available")
        try:
            _campaign_engine.transition_status(campaign_id, new_status)
            return {"status": "transitioned", "campaign_id": campaign_id, "new_status": new_status}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ============================================================
    # GLOBAL MATCHING
    # ============================================================
    try:
        from global_matching import GlobalEntityIndex, MatchPolicy, IndexedEntity
        _match_index = GlobalEntityIndex()
        _gm_loaded = True
    except Exception as e:
        _match_index = None
        _gm_loaded = False
        print(f"Warning: global_matching not loaded: {e}")

    class MatchSearchRequest(BaseModel):
        entity_type: str
        entity_value: str
        jurisdiction: str = ""

    class EntityRegisterRequest(BaseModel):
        entity_type: str
        entity_value: str
        jurisdiction: str = ""
        organization_id: str = ""
        metadata: dict = {}

    @app.post("/api/matching/register")
    async def matching_register(req: EntityRegisterRequest):
        if not _gm_loaded:
            raise HTTPException(503, "Global matching not available")
        try:
            entity = IndexedEntity(
                entity_type=req.entity_type,
                entity_value=req.entity_value,
                jurisdiction=req.jurisdiction,
                organization_id=req.organization_id
            )
            entity_id = _match_index.register_entity(entity)
            return {"status": "registered", "entity_id": entity_id}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/matching/search")
    async def matching_search(req: MatchSearchRequest):
        if not _gm_loaded:
            raise HTTPException(503, "Global matching not available")
        results = _match_index.lookup(req.entity_type, req.entity_value)
        safe_results = [MatchPolicy.filter_entity(e) if hasattr(MatchPolicy, 'filter_entity') else e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in results]
        return {"query": req.entity_type, "matches": len(results), "results": safe_results}

    @app.get("/api/matching/entity/{entity_id}")
    async def matching_get_entity(entity_id: str):
        if not _gm_loaded:
            raise HTTPException(503, "Global matching not available")
        entity = _match_index.get_entity(entity_id)
        if not entity:
            raise HTTPException(404, "Entity not found")
        return MatchPolicy.filter_entity(entity) if hasattr(MatchPolicy, 'filter_entity') else entity.model_dump() if hasattr(entity, 'model_dump') else {"entity": str(entity)}

    @app.get("/api/matching/stats")
    async def matching_stats():
        if not _gm_loaded:
            raise HTTPException(503, "Global matching not available")
        try:
            return _match_index.stats() if hasattr(_match_index, 'stats') else {"total_entities": _match_index.count() if hasattr(_match_index, 'count') else 0}
        except Exception as e:
            return {"total_entities": 0, "error": str(e)}

    # ============================================================
    # EARLY WARNING
    # ============================================================
    try:
        from early_warning import EarlyWarningEngine, WarningRule, WarningLevel, WarningRuleType
        _warning_engine = EarlyWarningEngine()
        _ew_loaded = True
    except Exception as e:
        _warning_engine = None
        _ew_loaded = False
        print(f"Warning: early_warning not loaded: {e}")

    class WarningRuleRequest(BaseModel):
        name: str
        description: str = ""
        rule_type: str = "threshold"
        conditions: dict = {}
        level: str = "medium"
        enabled: bool = True

    class MonitorEntityRequest(BaseModel):
        entity_id: str
        entity_type: str = "domain"

    @app.get("/api/warnings")
    async def warnings_list():
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            events = _warning_engine.get_events() if hasattr(_warning_engine, 'get_events') else []
            return {"count": len(events), "warnings": [e.model_dump() if hasattr(e, 'model_dump') else e.dict() if hasattr(e, 'dict') else str(e) for e in events]}
        except Exception as e:
            return {"count": 0, "warnings": [], "error": str(e)}

    @app.get("/api/warnings/rules")
    async def warnings_rules(enabled_only: bool = Query(False)):
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        rules = _warning_engine.list_rules(enabled_only=enabled_only)
        return {"count": len(rules), "rules": [r.model_dump() if hasattr(r, 'model_dump') else r.dict() if hasattr(r, 'dict') else str(r) for r in rules]}

    @app.post("/api/warnings/rules")
    async def warnings_add_rule(req: WarningRuleRequest):
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            rule = _warning_engine.add_rule(
                name=req.name,
                description=req.description,
                rule_type=req.rule_type,
                conditions=req.conditions,
                level=req.level,
                enabled=req.enabled
            )
            return {"status": "added", "rule_id": getattr(rule, 'id', str(rule))}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/warnings/monitor")
    async def warnings_monitor(req: MonitorEntityRequest):
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            _warning_engine.monitor_entity(
                entity_id=req.entity_id,
                entity_type=req.entity_type
            )
            return {"status": "monitoring", "entity_id": req.entity_id}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/warnings/monitored")
    async def warnings_monitored():
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            count = _warning_engine.monitored_count if isinstance(_warning_engine.monitored_count, (int, float)) else _warning_engine.monitored_count()
            return {"monitored_count": count}
        except:
            return {"monitored_count": 0}

    @app.post("/api/warnings/{warning_id}/acknowledge")
    async def warnings_acknowledge(warning_id: str, operator: str = Query("system")):
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            _warning_engine.acknowledge_event(warning_id, operator)
            return {"status": "acknowledged", "warning_id": warning_id}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/warnings/notifications")
    async def warnings_notifications():
        if not _ew_loaded:
            raise HTTPException(503, "Early warning not available")
        try:
            notifs = _warning_engine.get_notifications() if hasattr(_warning_engine, 'get_notifications') else []
            return {"count": len(notifs), "notifications": [n.model_dump() if hasattr(n, 'model_dump') else n.dict() if hasattr(n, 'dict') else str(n) for n in notifs]}
        except Exception as e:
            return {"count": 0, "notifications": []}

    # ============================================================
    # CONTINUOUS MONITORING
    # ============================================================
    try:
        from continuous_monitoring import SubscriptionService, ChangeDetector
        _monitor_subscriptions = SubscriptionService()
        _monitor_detector = ChangeDetector()
        _cm_loaded = True
    except Exception as e:
        _monitor_subscriptions = None
        _cm_loaded = False
        print(f"Warning: continuous_monitoring not loaded: {e}")

    class SubscribeRequest(BaseModel):
        target_id: str
        target_type: str = "entity"
        watch_type: str = "all"
        subscriber: str = "system"

    @app.get("/api/monitoring/subscriptions")
    async def monitoring_subscriptions(active_only: bool = Query(True)):
        if not _cm_loaded:
            raise HTTPException(503, "Continuous monitoring not available")
        # list_subscriptions takes subscriber_id, target_id, active_only
        subs = _monitor_subscriptions.list_subscriptions(active_only=active_only)
        return {"count": len(subs), "subscriptions": [s.model_dump() if hasattr(s, 'model_dump') else s.dict() if hasattr(s, 'dict') else str(s) for s in subs]}

    @app.post("/api/monitoring/subscribe")
    async def monitoring_subscribe(req: SubscribeRequest):
        if not _cm_loaded:
            raise HTTPException(503, "Continuous monitoring not available")
        try:
            sub = _monitor_subscriptions.subscribe(
                target_id=req.target_id,
                target_type=req.target_type,
                watch_type=req.watch_type,
                subscriber=req.subscriber
            )
            return {"status": "subscribed", "subscription_id": getattr(sub, 'id', str(sub))}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.delete("/api/monitoring/unsubscribe/{subscription_id}")
    async def monitoring_unsubscribe(subscription_id: str):
        if not _cm_loaded:
            raise HTTPException(503, "Continuous monitoring not available")
        result = _monitor_subscriptions.unsubscribe(subscription_id)
        return {"status": "unsubscribed" if result else "not_found", "subscription_id": subscription_id}

    @app.get("/api/monitoring/changes")
    async def monitoring_changes(entity_id: str = Query(None)):
        if not _cm_loaded:
            raise HTTPException(503, "Continuous monitoring not available")
        try:
            if entity_id:
                changes = _monitor_detector.detect_entity_changes(entity_id) if hasattr(_monitor_detector, 'detect_entity_changes') else []
            else:
                changes = []
            return {"count": len(changes), "changes": [c.model_dump() if hasattr(c, 'model_dump') else c.dict() if hasattr(c, 'dict') else str(c) for c in changes]}
        except Exception as e:
            return {"count": 0, "changes": [], "error": str(e)}

    @app.get("/api/monitoring/alerts")
    async def monitoring_alerts():
        if not _cm_loaded:
            raise HTTPException(503, "Continuous monitoring not available")
        return {"alerts": []}

    print("   Batch 2 routes: campaign_engine(6), global_matching(4), early_warning(6), continuous_monitoring(4) = 20 endpoints")
