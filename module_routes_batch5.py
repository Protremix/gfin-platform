"""
GFIN Module API Routes — Batch 5
GDPR Compliance, Security Dashboard, Local AI, Investigation Copilot, Citizen Platform
"""
import sys
sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
sys.path.insert(0, '/gfin/packages')

from fastapi import HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Any
import time


def register_batch5_routes(app, auth_police, auth_police_admin, rate_limiter):
    """Register Batch 5 API routes."""

    # ============================================================
    # GDPR COMPLIANCE
    # ============================================================
    try:
        from gdpr_compliance import GDPRComplianceService
        _gdpr = GDPRComplianceService()
        _gdpr_loaded = True
    except Exception as e:
        _gdpr = None
        _gdpr_loaded = False
        print(f"Warning: gdpr_compliance not loaded: {e}")

    class DSRRequest(BaseModel):
        request_type: str = "access"  # access, erasure, rectification, restriction, portability, objection
        subject_name: str
        subject_email: str
        subject_identifier: str = ""
        description: str = ""

    class ConsentRequest(BaseModel):
        subject_email: str
        purpose: str
        processing_details: str = ""

    class ProcessingActivityRequest(BaseModel):
        name: str
        purpose: str
        data_categories: list = []
        legal_basis: str = "legitimate_interest"
        recipients: list = []
        retention_days: int = 365

    class BreachRequest(BaseModel):
        description: str
        severity: str = "medium"  # low, medium, high, critical
        affected_records: int = 0

    @app.post("/api/gdpr/request")
    async def gdpr_create_request(req: DSRRequest):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        try:
            dsr = _gdpr.create_request(
                request_type=req.request_type,
                subject_name=req.subject_name,
                subject_email=req.subject_email,
                subject_identifier=req.subject_identifier,
                description=req.description
            )
            return {"status": "created", "request": dsr.to_dict()}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get("/api/gdpr/requests")
    async def gdpr_list_requests(status: str = Query(None)):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        requests = _gdpr.list_requests(status=status)
        return {"count": len(requests), "requests": [r.to_dict() for r in requests]}

    @app.get("/api/gdpr/request/{request_id}")
    async def gdpr_get_request(request_id: str):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        req = _gdpr.get_request(request_id)
        if not req:
            raise HTTPException(404, "Request not found")
        return req.to_dict()

    @app.post("/api/gdpr/consent")
    async def gdpr_grant_consent(req: ConsentRequest):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        consent = _gdpr.grant_consent(
            subject_email=req.subject_email,
            purpose=req.purpose,
            processing_details=req.processing_details
        )
        return {"status": "granted", "consent": consent.to_dict()}

    @app.delete("/api/gdpr/consent/{consent_id}")
    async def gdpr_withdraw_consent(consent_id: str):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        consent = _gdpr.withdraw_consent(consent_id)
        if not consent:
            raise HTTPException(404, "Consent not found")
        return {"status": "withdrawn", "consent": consent.to_dict()}

    @app.get("/api/gdpr/consents")
    async def gdpr_list_consents(subject_email: str = Query(None)):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        consents = _gdpr.list_consents(subject_email=subject_email)
        return {"count": len(consents), "consents": [c.to_dict() for c in consents]}

    @app.post("/api/gdpr/breach")
    async def gdpr_report_breach(req: BreachRequest):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        breach = _gdpr.report_breach(
            description=req.description,
            severity=req.severity,
            affected_records=req.affected_records
        )
        return {"status": "reported", "breach": breach.to_dict()}

    @app.get("/api/gdpr/breaches")
    async def gdpr_list_breaches(status: str = Query(None)):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        breaches = _gdpr.list_breaches(status=status)
        return {"count": len(breaches), "breaches": [b.to_dict() for b in breaches]}

    @app.post("/api/gdpr/processing-activity")
    async def gdpr_register_activity(req: ProcessingActivityRequest):
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        activity = _gdpr.register_processing_activity(
            name=req.name,
            purpose=req.purpose,
            data_categories=req.data_categories,
            legal_basis=req.legal_basis,
            recipients=req.recipients,
            retention_days=req.retention_days
        )
        return {"status": "registered", "activity": activity.to_dict()}

    @app.get("/api/gdpr/summary")
    async def gdpr_summary():
        if not _gdpr_loaded:
            raise HTTPException(503, "GDPR service not available")
        return _gdpr.get_summary()

    # ============================================================
    # SECURITY DASHBOARD
    # ============================================================
    try:
        from security_dashboard import SecurityDashboard
        _sec_dashboard = SecurityDashboard()
        _sd_loaded = True
    except Exception as e:
        _sec_dashboard = None
        _sd_loaded = False
        print(f"Warning: security_dashboard not loaded: {e}")

    @app.get("/api/security/summary")
    async def security_summary():
        if not _sd_loaded:
            raise HTTPException(503, "Security dashboard not available")
        try:
            return _sec_dashboard.summary() if hasattr(_sec_dashboard, 'summary') else {}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/security/infrastructure")
    async def security_infrastructure():
        if not _sd_loaded:
            raise HTTPException(503, "Security dashboard not available")
        try:
            return _sec_dashboard.infrastructure_status() if hasattr(_sec_dashboard, 'infrastructure_status') else {}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/security/production-ready")
    async def security_production_ready():
        if not _sd_loaded:
            raise HTTPException(503, "Security dashboard not available")
        try:
            return {"production_ready": _sec_dashboard.is_production_ready() if hasattr(_sec_dashboard, 'is_production_ready') else False}
        except Exception as e:
            return {"production_ready": False, "error": str(e)}

    @app.get("/api/security/vulnerabilities")
    async def security_vulnerabilities():
        if not _sd_loaded:
            raise HTTPException(503, "Security dashboard not available")
        try:
            vulns = _sec_dashboard.get_open_vulnerabilities() if hasattr(_sec_dashboard, 'get_open_vulnerabilities') else []
            return {"open_vulnerabilities": len(vulns), "vulnerabilities": vulns}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # LOCAL AI
    # ============================================================
    try:
        from local_ai import LocalAIGateway, ClassificationService, LanguageDetector, EmbeddingService
        _ai_gateway = LocalAIGateway()
        _classifier = ClassificationService()
        _lang_detector = LanguageDetector()
        _ai_loaded = True
    except Exception as e:
        _ai_gateway = None
        _ai_loaded = False
        print(f"Warning: local_ai not loaded: {e}")

    class ClassifyRequest(BaseModel):
        text: str
        model: str = "default"

    class LanguageRequest(BaseModel):
        text: str

    @app.post("/api/ai/classify")
    async def ai_classify(req: ClassifyRequest):
        if not _ai_loaded:
            raise HTTPException(503, "Local AI not available")
        try:
            result = _classifier.classify(req.text) if hasattr(_classifier, 'classify') else {}
            return {"classification": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/ai/language")
    async def ai_detect_language(req: LanguageRequest):
        if not _ai_loaded:
            raise HTTPException(503, "Local AI not available")
        try:
            result = _lang_detector.detect(req.text) if hasattr(_lang_detector, 'detect') else {}
            return {"language": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/ai/models")
    async def ai_models():
        if not _ai_loaded:
            raise HTTPException(503, "Local AI not available")
        try:
            models = _ai_gateway.list_models() if hasattr(_ai_gateway, 'list_models') else []
            return {"models": models}
        except Exception as e:
            return {"models": [], "error": str(e)}

    @app.get("/api/ai/health")
    async def ai_health():
        if not _ai_loaded:
            raise HTTPException(503, "Local AI not available")
        try:
            health = _ai_gateway.health_check() if hasattr(_ai_gateway, 'health_check') else {"status": "ok"}
            return health
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ============================================================
    # INVESTIGATION COPILOT
    # ============================================================
    try:
        from investigation_copilot import InvestigationCopilot
        _copilot = InvestigationCopilot()
        _ic_loaded = True
    except Exception as e:
        _copilot = None
        _ic_loaded = False
        print(f"Warning: investigation_copilot not loaded: {e}")

    class CopilotRequest(BaseModel):
        seed_type: str = "domain"
        seed_value: str = ""
        objective: str = "Investigate the target for fraud indicators"

    @app.post("/api/copilot/investigate")
    async def copilot_investigate(req: CopilotRequest):
        if not _ic_loaded:
            raise HTTPException(503, "Investigation copilot not available")
        try:
            result = _copilot.investigate(
                seed_type=req.seed_type,
                seed_value=req.seed_value,
                objective=req.objective
            )
            return {"result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/copilot/seeds")
    async def copilot_seeds():
        if not _ic_loaded:
            raise HTTPException(503, "Investigation copilot not available")
        return {"allowed_seed_types": _copilot.ALLOWED_SEED_TYPES if hasattr(_copilot, 'ALLOWED_SEED_TYPES') else ["domain", "ip", "wallet", "phone", "email"]}

    # ============================================================
    # CITIZEN PLATFORM
    # ============================================================
    try:
        from citizen_platform import CitizenReportService, CitizenCheckService, CitizenAlertService
        _citizen_reports = CitizenReportService()
        _citizen_checks = CitizenCheckService()
        _citizen_alerts = CitizenAlertService()
        _cp_loaded = True
    except Exception as e:
        _cp_loaded = False
        print(f"Warning: citizen_platform not loaded: {e}")

    class CitizenReportRequest(BaseModel):
        reporter_name: str
        reporter_email: str = ""
        target: str
        scam_type: str
        description: str
        country: str = ""
        evidence_urls: list = []

    class CitizenCheckRequest(BaseModel):
        entity: str
        entity_type: str = "domain"

    @app.post("/api/citizen/report")
    async def citizen_report(req: CitizenReportRequest):
        if not _cp_loaded:
            raise HTTPException(503, "Citizen platform not available")
        try:
            result = _citizen_reports.submit_report(
                reporter_name=req.reporter_name,
                reporter_email=req.reporter_email,
                target=req.target,
                scam_type=req.scam_type,
                description=req.description,
                country=req.country
            )
            return {"status": "submitted", "report": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/api/citizen/check")
    async def citizen_check(req: CitizenCheckRequest):
        if not _cp_loaded:
            raise HTTPException(503, "Citizen platform not available")
        try:
            result = _citizen_checks.check(req.entity, req.entity_type) if hasattr(_citizen_checks, 'check') else {"entity": req.entity, "status": "unknown"}
            return {"entity": req.entity, "result": result.model_dump() if hasattr(result, 'model_dump') else result if isinstance(result, dict) else str(result)}
        except Exception as e:
            return {"entity": req.entity, "error": str(e)}

    @app.get("/api/citizen/reports")
    async def citizen_reports(limit: int = Query(20, le=100)):
        if not _cp_loaded:
            raise HTTPException(503, "Citizen platform not available")
        try:
            reports = _citizen_reports.list_reports() if hasattr(_citizen_reports, 'list_reports') else []
            return {"count": len(reports), "reports": [r.model_dump() if hasattr(r, 'model_dump') else str(r) for r in reports[:limit]]}
        except Exception as e:
            return {"count": 0, "reports": [], "error": str(e)}

    @app.get("/api/citizen/alerts")
    async def citizen_alerts():
        if not _cp_loaded:
            raise HTTPException(503, "Citizen platform not available")
        try:
            alerts = _citizen_alerts.list_alerts() if hasattr(_citizen_alerts, 'list_alerts') else []
            return {"count": len(alerts), "alerts": [a.model_dump() if hasattr(a, 'model_dump') else str(a) for a in alerts]}
        except Exception as e:
            return {"count": 0, "alerts": [], "error": str(e)}

    print("   Batch 5 routes: gdpr(10), security_dashboard(4), local_ai(4), copilot(2), citizen_platform(4) = 24 endpoints")
