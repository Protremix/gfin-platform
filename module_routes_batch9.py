"""
GFIN Module API Routes — Batch 9 (Future-Tier)
Dark Web Monitor, AI Summaries, WebSocket Hub
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Any
import json
import asyncio


def register_batch9_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 9 (future-tier) API routes."""

    # ============================================================
    # DARK WEB MONITOR
    # ============================================================
    try:
        from dark_web_monitor import DarkWebMonitor
        _dark_web = DarkWebMonitor()
        _dw_loaded = True
    except Exception as e:
        _dark_web = None
        _dw_loaded = False
        print(f"Warning: dark_web_monitor not loaded: {e}")

    class DarkWebTargetRequest(BaseModel):
        entity: str
        entity_type: str = "email"  # email, wallet, domain, phone

    @app.post("/api/dark-web/target")
    async def dw_add_target(req: DarkWebTargetRequest):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        target = _dark_web.add_target(req.entity, req.entity_type)
        return {"status": "monitoring", "target_id": target.id, "entity": req.entity}

    @app.delete("/api/dark-web/target/{target_id}")
    async def dw_remove_target(target_id: str):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        if _dark_web.remove_target(target_id):
            return {"status": "removed", "target_id": target_id}
        raise HTTPException(404, "Target not found")

    @app.get("/api/dark-web/targets")
    async def dw_list_targets(active: bool = Query(True)):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        targets = _dark_web.list_targets(active_only=active)
        return {"count": len(targets), "targets": [{"id": t.id, "entity": t.entity, "entity_type": t.entity_type, "findings_count": t.findings_count, "last_checked": t.last_checked} for t in targets]}

    @app.post("/api/dark-web/scan/{target_id}")
    async def dw_scan_target(target_id: str):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        findings = _dark_web.scan_target(target_id)
        return {"target_id": target_id, "new_findings": len(findings), "findings": [f.to_dict() for f in findings]}

    @app.post("/api/dark-web/scan-all")
    async def dw_scan_all():
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        result = _dark_web.scan_all_targets()
        return result

    @app.get("/api/dark-web/findings")
    async def dw_findings(threat_level: str = Query(None), source: str = Query(None), entity: str = Query(None)):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        findings = _dark_web.list_findings(threat_level=threat_level, source=source, entity=entity)
        return {"count": len(findings), "findings": [f.to_dict() for f in findings]}

    @app.get("/api/dark-web/finding/{finding_id}")
    async def dw_get_finding(finding_id: str):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        finding = _dark_web.get_finding(finding_id)
        if not finding:
            raise HTTPException(404, "Finding not found")
        return finding.to_dict()

    @app.post("/api/dark-web/verify/{finding_id}")
    async def dw_verify_finding(finding_id: str, verified: bool = Query(True)):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        finding = _dark_web.verify_finding(finding_id, verified)
        if not finding:
            raise HTTPException(404, "Finding not found")
        return {"status": "verified" if verified else "unverified", "finding_id": finding_id}

    @app.get("/api/dark-web/exposure/{entity}")
    async def dw_exposure_report(entity: str):
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        return _dark_web.get_exposure_report(entity)

    @app.get("/api/dark-web/summary")
    async def dw_summary():
        if not _dw_loaded:
            raise HTTPException(503, "Dark web monitor not available")
        return _dark_web.get_summary()

    @app.get("/api/dark-web/tor-status")
    async def dw_tor_status():
        """Get Tor proxy status for dark web monitoring (Layer B)."""
        try:
            from tor_dark_web_scanner import get_tor_status
            return get_tor_status()
        except ImportError:
            return {"tor_enabled": False, "layer": "A", "note": "Tor scanner not installed"}
        except Exception as e:
            return {"tor_enabled": False, "error": str(e), "layer": "A"}

    # ============================================================
    # AI SUMMARIES
    # ============================================================
    try:
        from ai_summaries import AISummaryService, SummaryRequest
        _ai_summary = AISummaryService()
        _ais_loaded = True
    except Exception as e:
        _ai_summary = None
        _ais_loaded = False
        print(f"Warning: ai_summaries not loaded: {e}")

    class AISummaryRequest(BaseModel):
        summary_type: str = "case"  # case, evidence, pattern, investigation, risk
        case_id: str = ""
        data: dict = {}
        target_language: str = "en"
        max_tokens: int = 2000

    @app.post("/api/ai/summary")
    async def ai_generate_summary(req: AISummaryRequest):
        if not _ais_loaded:
            raise HTTPException(503, "AI summary service not available")
        summary_req = SummaryRequest(
            summary_type=req.summary_type,
            case_id=req.case_id,
            data=req.data,
            target_language=req.target_language,
            max_tokens=req.max_tokens
        )
        result = await _ai_summary.generate_summary(summary_req)
        return result.to_dict()

    @app.get("/api/ai/summaries")
    async def ai_list_summaries(summary_type: str = Query(None), case_id: str = Query(None)):
        if not _ais_loaded:
            raise HTTPException(503, "AI summary service not available")
        summaries = _ai_summary.list_summaries(summary_type=summary_type, case_id=case_id)
        return {"count": len(summaries), "summaries": [s.to_dict() for s in summaries]}

    @app.get("/api/ai/summary/{summary_id}")
    async def ai_get_summary(summary_id: str):
        if not _ais_loaded:
            raise HTTPException(503, "AI summary service not available")
        summary = _ai_summary.get_summary_by_id(summary_id)
        if not summary:
            raise HTTPException(404, "Summary not found")
        return summary.to_dict()

    @app.get("/api/ai/summary-stats")
    async def ai_summary_stats():
        if not _ais_loaded:
            raise HTTPException(503, "AI summary service not available")
        return _ai_summary.get_summary_stats()

    # ============================================================
    # WEBSOCKET HUB (REST endpoints for stats/info)
    # ============================================================
    try:
        from websocket_hub import WebSocketHub
        _ws_hub = WebSocketHub()
        _ws_loaded = True
    except Exception as e:
        _ws_hub = None
        _ws_loaded = False
        print(f"Warning: websocket_hub not loaded: {e}")

    @app.get("/api/ws/channels")
    async def ws_channels():
        if not _ws_loaded:
            raise HTTPException(503, "WebSocket hub not available")
        return {"channels": _ws_hub.get_available_channels()}

    @app.get("/api/ws/stats")
    async def ws_stats():
        if not _ws_loaded:
            raise HTTPException(503, "WebSocket hub not available")
        return _ws_hub.get_stats()

    @app.get("/api/ws/history/{channel}")
    async def ws_history(channel: str, limit: int = Query(50, le=200)):
        if not _ws_loaded:
            raise HTTPException(503, "WebSocket hub not available")
        return {"channel": channel, "messages": _ws_hub.get_channel_history(channel, limit)}

    @app.get("/api/ws/channel/{channel}")
    async def ws_channel_info(channel: str):
        if not _ws_loaded:
            raise HTTPException(503, "WebSocket hub not available")
        return _ws_hub.get_channel_info(channel)

    # ============================================================
    # WEBSOCKET ENDPOINT (actual WS connection)
    # ============================================================
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        if not _ws_loaded:
            await websocket.close(code=1003, reason="WebSocket hub not available")
            return

        client_id = await _ws_hub.manager.connect(websocket)
        subscribed_channels = []

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    action = msg.get("action", "")

                    if action == "subscribe":
                        channel = msg.get("channel", "")
                        if channel in _ws_hub.CHANNELS:
                            _ws_hub.manager.subscribe(client_id, channel)
                            subscribed_channels.append(channel)
                            await websocket.send_text(json.dumps({
                                "status": "subscribed",
                                "channel": channel,
                                "subscribers": _ws_hub.manager.get_subscriber_count(channel)
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                "error": f"Unknown channel: {channel}",
                                "available": _ws_hub.CHANNELS
                            }))

                    elif action == "unsubscribe":
                        channel = msg.get("channel", "")
                        _ws_hub.manager.unsubscribe(client_id, channel)
                        if channel in subscribed_channels:
                            subscribed_channels.remove(channel)
                        await websocket.send_text(json.dumps({
                            "status": "unsubscribed",
                            "channel": channel
                        }))

                    elif action == "history":
                        channel = msg.get("channel", "")
                        history = _ws_hub.get_channel_history(channel, limit=msg.get("limit", 50))
                        await websocket.send_text(json.dumps({
                            "channel": channel,
                            "history": history
                        }))

                    elif action == "ping":
                        await websocket.send_text(json.dumps({"status": "pong", "timestamp": str(datetime.now(UTC))}))

                    else:
                        await websocket.send_text(json.dumps({
                            "error": f"Unknown action: {action}",
                            "actions": ["subscribe", "unsubscribe", "history", "ping"]
                        }))

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"error": "Invalid JSON"}))

        except WebSocketDisconnect:
            _ws_hub.manager.unsubscribe(client_id)
            pass

    # Publish endpoints (for internal services to publish events)
    class WSPublishRequest(BaseModel):
        channel: str
        event_type: str
        data: dict = {}

    @app.post("/api/ws/publish")
    async def ws_publish(req: WSPublishRequest):
        if not _ws_loaded:
            raise HTTPException(503, "WebSocket hub not available")
        msg = await _ws_hub.manager.broadcast(req.channel, req.event_type, req.data)
        return {"status": "published", "message": msg}

    print("   Batch 9 routes: dark_web(9), ai_summaries(4), websocket(5) = 18 endpoints + WS /ws")
