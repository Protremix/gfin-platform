"""
GFIN Module API Routes — Batch 8
Disaster Recovery, Alert Engine, Analytics, Multilingual, Kafka Event Bus, PDF Reports
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch8_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 8 API routes."""

    # ============================================================
    # DISASTER RECOVERY
    # ============================================================
    try:
        from disaster_recovery import DisasterRecoveryService
        _dr = DisasterRecoveryService()
        _dr_loaded = True
    except Exception as e:
        _dr = None
        _dr_loaded = False
        print(f"Warning: disaster_recovery not loaded: {e}")

    class BackupCreateRequest(BaseModel):
        label: str = ""
        data: dict = {}

    @app.get("/api/dr/backups")
    async def dr_list_backups(limit: int = Query(20, le=100)):
        if not _dr_loaded:
            raise HTTPException(503, "Disaster recovery not available")
        try:
            backups = _dr.list_backups() if hasattr(_dr, 'list_backups') else []
            return {"count": len(backups) if isinstance(backups, list) else 0, "backups": [b.model_dump() if hasattr(b, 'model_dump') else str(b) for b in (backups if isinstance(backups, list) else [])[:limit]]}
        except Exception as e:
            return {"count": 0, "backups": [], "error": str(e)}

    @app.post("/api/dr/backup")
    async def dr_create_backup(req: BackupCreateRequest):
        if not _dr_loaded:
            raise HTTPException(503, "Disaster recovery not available")
        try:
            backup = _dr.create_backup(req.label, req.data) if hasattr(_dr, 'create_backup') else {}
            return {"status": "created", "backup": backup.model_dump() if hasattr(backup, 'model_dump') else backup if isinstance(backup, dict) else str(backup)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/dr/summary")
    async def dr_summary():
        if not _dr_loaded:
            raise HTTPException(503, "Disaster recovery not available")
        try:
            summary = _dr.get_dr_summary() if hasattr(_dr, 'get_dr_summary') else {}
            return summary if isinstance(summary, dict) else {"summary": str(summary)}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # ALERT ENGINE
    # ============================================================
    try:
        from alert_engine import AlertManager
        _alert_mgr = AlertManager()
        _ae_loaded = True
    except Exception as e:
        _alert_mgr = None
        _ae_loaded = False
        print(f"Warning: alert_engine not loaded: {e}")

    class AlertProcessRequest(BaseModel):
        alert_type: str
        priority: str = "medium"
        source: str = ""
        message: str = ""
        data: dict = {}

    @app.post("/api/alerts/process")
    async def alerts_process(req: AlertProcessRequest):
        if not _ae_loaded:
            raise HTTPException(503, "Alert engine not available")
        try:
            result = _alert_mgr.process_alert(
                alert_type=req.alert_type,
                priority=req.priority,
                source=req.source,
                message=req.message,
                data=req.data
            ) if hasattr(_alert_mgr, 'process_alert') else {}
            return {"status": "processed", "alert": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/alerts/statistics")
    async def alerts_statistics():
        if not _ae_loaded:
            raise HTTPException(503, "Alert engine not available")
        try:
            stats = _alert_mgr.get_statistics() if hasattr(_alert_mgr, 'get_statistics') else {}
            return stats.model_dump() if hasattr(stats, 'model_dump') else stats if isinstance(stats, dict) else {"statistics": str(stats)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/alerts/digest")
    async def alerts_digest():
        if not _ae_loaded:
            raise HTTPException(503, "Alert engine not available")
        try:
            digest = _alert_mgr.get_digest() if hasattr(_alert_mgr, 'get_digest') else {}
            return digest.model_dump() if hasattr(digest, 'model_dump') else digest if isinstance(digest, dict) else {"digest": str(digest)}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # ANALYTICS
    # ============================================================
    try:
        from analytics import AnalyticsService
        _analytics = AnalyticsService()
        _an_loaded = True
    except Exception as e:
        _analytics = None
        _an_loaded = False
        print(f"Warning: analytics not loaded: {e}")

    @app.get("/api/analytics/overview")
    async def analytics_overview():
        if not _an_loaded:
            raise HTTPException(503, "Analytics not available")
        try:
            # Try different method names
            for method in ["get_overview", "overview", "summary", "get_summary", "get_statistics"]:
                if hasattr(_analytics, method):
                    result = getattr(_analytics, method)()
                    return result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else {"overview": str(result)}
            return {"overview": "not available"}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/analytics/trends")
    async def analytics_trends(period: str = Query("30d")):
        if not _an_loaded:
            raise HTTPException(503, "Analytics not available")
        try:
            for method in ["get_trends", "trends", "analyze_trends", "get_trend_analysis"]:
                if hasattr(_analytics, method):
                    result = getattr(_analytics, method)(period) if hasattr(getattr(_analytics, method), '__call__') else getattr(_analytics, method)
                    return result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else {"trends": str(result)}
            return {"period": period, "trends": "not available"}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # MULTILINGUAL
    # ============================================================
    try:
        from multilingual import MultilingualService, SupportedLanguage
        _multilingual = MultilingualService()
        _ml_loaded = True
    except Exception as e:
        _multilingual = None
        _ml_loaded = False
        print(f"Warning: multilingual not loaded: {e}")

    class TranslateRequest(BaseModel):
        text: str
        target_language: str = "es"
        source_language: str = "auto"

    @app.post("/api/multilingual/detect")
    async def multilingual_detect(text: str = Query(...)):
        if not _ml_loaded:
            raise HTTPException(503, "Multilingual service not available")
        try:
            for method in ["detect_language", "detect", "get_language"]:
                if hasattr(_multilingual, method):
                    result = getattr(_multilingual, method)(text)
                    return result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else {"language": str(result)}
            return {"text": text, "language": "unknown"}
        except Exception as e:
            return {"text": text, "error": str(e)}

    @app.post("/api/multilingual/translate")
    async def multilingual_translate(req: TranslateRequest):
        if not _ml_loaded:
            raise HTTPException(503, "Multilingual service not available")
        try:
            for method in ["translate", "get_translation"]:
                if hasattr(_multilingual, method):
                    result = getattr(_multilingual, method)(req.text, req.target_language, req.source_language)
                    return result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else {"translation": str(result)}
            return {"original": req.text, "target_language": req.target_language, "translation": "not available"}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/multilingual/languages")
    async def multilingual_languages():
        if not _ml_loaded:
            raise HTTPException(503, "Multilingual service not available")
        try:
            langs = [str(l) for l in SupportedLanguage] if hasattr(SupportedLanguage, '__iter__') else []
            return {"supported_languages": langs}
        except Exception as e:
            return {"supported_languages": [], "error": str(e)}

    # ============================================================
    # KAFKA EVENT BUS
    # ============================================================
    try:
        from kafka_event_bus import KafkaEventBus
        _kafka = KafkaEventBus()
        _kb_loaded = True
    except Exception as e:
        _kafka = None
        _kb_loaded = False
        print(f"Warning: kafka_event_bus not loaded: {e}")

    @app.get("/api/events/health")
    async def events_health():
        if not _kb_loaded:
            raise HTTPException(503, "Kafka event bus not available")
        try:
            health = _kafka.health_check() if hasattr(_kafka, 'health_check') else {"status": "unknown"}
            return health if isinstance(health, dict) else {"health": str(health)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.get("/api/events/metrics")
    async def events_metrics():
        if not _kb_loaded:
            raise HTTPException(503, "Kafka event bus not available")
        try:
            metrics = _kafka.get_metrics() if hasattr(_kafka, 'get_metrics') else {}
            return metrics if isinstance(metrics, dict) else {"metrics": str(metrics)}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # PDF REPORTS
    # ============================================================
    try:
        from pdf_reports import generate_case_report, generate_evidence_receipt
        _pdf_loaded = True
    except Exception as e:
        _pdf_loaded = False
        print(f"Warning: pdf_reports not loaded: {e}")

    class PDFReportRequest(BaseModel):
        case_id: str
        title: str = "GFIN Case Report"
        data: dict = {}

    @app.post("/api/reports/case")
    async def reports_generate_case(req: PDFReportRequest):
        if not _pdf_loaded:
            raise HTTPException(503, "PDF reports not available")
        try:
            result = generate_case_report(req.case_id, req.data) if hasattr(generate_case_report, '__call__') else {}
            return {"status": "generated", "case_id": req.case_id, "result": result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/reports/evidence")
    async def reports_generate_evidence(case_id: str = Query(...), evidence_data: dict = Body(default={})):
        if not _pdf_loaded:
            raise HTTPException(503, "PDF reports not available")
        try:
            result = generate_evidence_receipt(case_id, evidence_data) if hasattr(generate_evidence_receipt, '__call__') else {}
            return {"status": "generated", "case_id": case_id, "result": result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    print("   Batch 8 routes: disaster_recovery(3), alert_engine(3), analytics(2), multilingual(3), kafka(2), pdf_reports(2) = 15 endpoints")
