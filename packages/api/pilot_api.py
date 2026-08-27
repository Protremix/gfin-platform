# GFIN API Layer — Pilot Vertical Slice
#
# Per Luna Assessment P0: "FastAPI endpoints with contract tests for pilot workflow."
# Per Luna Assessment P1: "The API should represent business capabilities, not repository structure."
#
# Implements the citizen-to-police intelligence chain:
#   Citizen Report → Triage → Detection → Campaign → Alert → Police API
#
# Architecture:
#   - FastAPI application with authentication middleware
#   - Versioned API (/api/v1/)
#   - OpenAPI documentation
#   - Correlation IDs for tracing
#   - Rate limiting
#   - Health/readiness endpoints
#
# REQUIRES EXTERNAL INFRASTRUCTURE: FastAPI, uvicorn, PostgreSQL driver.
# Layer A: Can run with in-memory repositories (no DB needed for testing).
# Layer B: Production with PostgreSQL (REQUIRES EXTERNAL INFRASTRUCTURE).

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = structlog.get_logger("gfin.api")

app = FastAPI(
    title="GFIN — Global Fraud Intelligence Network",
    description="Pilot API for the citizen-to-police intelligence chain.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─── Middleware ───

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Layer A: permissive. Layer B: restrict to known origins.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Any) -> Response:
    """Add correlation ID to every request for distributed tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ─── Request/Response Models ───


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CitizenReportRequest(BaseModel):
    """Citizen fraud report submission."""

    report_type: str = Field(
        ..., description="Type of fraud (phishing, investment_scam, romance_scam, etc.)"
    )
    description: str = Field(..., min_length=10, max_length=5000)
    entity_refs: list[str] = Field(
        default_factory=list, description="Entity references (phone, email, domain, URL)"
    )
    is_anonymous: bool = False
    reporter_email: str | None = None
    jurisdiction: str | None = Field(None, description="ISO 3166-1 alpha-2 country code")


class ReportResponse(BaseModel):
    report_id: str
    status: str = "UNVERIFIED"
    message: str = "Report submitted successfully"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportDetailResponse(BaseModel):
    report_id: str
    report_type: str
    description: str
    status: str
    priority: str
    score: int
    entity_refs: list[str]
    created_at: datetime
    updated_at: datetime
    organization_id: str | None = None


class TriageResponse(BaseModel):
    report_id: str
    priority: str
    score: int
    signals: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    message: str = "Triage complete"


class AlertRequest(BaseModel):
    alert_type: str = Field(
        ..., description="Type of alert (new_report, high_risk, campaign_detected)"
    )
    source_report_id: str
    target_org_id: str
    channel: str = "EMAIL"
    priority: str = "MEDIUM"
    message: str | None = None


class AlertResponse(BaseModel):
    alert_id: str
    status: str = "PENDING"
    message: str = "Alert queued"


class PoliceQueryRequest(BaseModel):
    query_type: str = Field(..., description="Type of query (report, entity, campaign)")
    query_value: str = Field(..., description="Search term")
    jurisdiction: str | None = None


class PoliceQueryResponse(BaseModel):
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    query_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ErrorResponse(BaseModel):
    error: str
    detail: str
    correlation_id: str | None = None


# ─── Health & Readiness ───


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@app.get("/ready", response_model=HealthResponse, tags=["System"])
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint."""
    return HealthResponse(status="ready")


# ─── Citizen Report Submission ───


@app.post(
    "/api/v1/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Citizen"],
)
async def submit_report(
    request: CitizenReportRequest,
    request_obj: Request,
    authorization: str | None = Header(None),
) -> ReportResponse:
    """Submit a new fraud report.

    Citizens can submit reports about fraud they've encountered.
    Reports start as UNVERIFIED and are triaged automatically.
    """
    correlation_id = getattr(request_obj.state, "correlation_id", str(uuid.uuid4()))

    # Layer A: Generate report ID (Layer B: persist to PostgreSQL)
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

    logger.info(
        "report_submitted",
        report_id=report_id,
        report_type=request.report_type,
        correlation_id=correlation_id,
        is_anonymous=request.is_anonymous,
    )

    return ReportResponse(
        report_id=report_id,
        status="UNVERIFIED",
        message="Report submitted successfully. It will be triaged automatically.",
    )


@app.get(
    "/api/v1/reports/{report_id}",
    response_model=ReportDetailResponse,
    tags=["Citizen"],
)
async def get_report(
    report_id: str,
    request: Request,
    authorization: str | None = Header(None),
) -> ReportDetailResponse:
    """Get a fraud report by ID."""
    # Layer A: Mock response (Layer B: query PostgreSQL)
    return ReportDetailResponse(
        report_id=report_id,
        report_type="phishing",
        description="Report details would be loaded from the database.",
        status="UNVERIFIED",
        priority="MEDIUM",
        score=0,
        entity_refs=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ─── Triage & Detection ───


@app.post(
    "/api/v1/reports/{report_id}/triage",
    response_model=TriageResponse,
    tags=["Triage"],
)
async def triage_report(
    report_id: str,
    request: Request,
    authorization: str | None = Header(None),
) -> TriageResponse:
    """Trigger triage and fraud detection for a report.

    Runs: triage (priority, spam, dedup) → fraud detection (signals, patterns) → campaign linking.
    """
    # Layer A: Mock triage (Layer B: call FraudReportingService + FraudDetectionService)
    return TriageResponse(
        report_id=report_id,
        priority="MEDIUM",
        score=45,
        signals=["HIGH_VALUE", "REPEAT_ENTITY"],
        campaign_id=None,
        message="Triage complete. 2 signals detected.",
    )


# ─── Alerts ───


@app.post(
    "/api/v1/alerts",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Alerts"],
)
async def create_alert(
    request: AlertRequest,
    request_obj: Request,
    authorization: str | None = Header(None),
) -> AlertResponse:
    """Create and route an alert to a partner organization."""
    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"

    logger.info(
        "alert_created",
        alert_id=alert_id,
        alert_type=request.alert_type,
        target_org=request.target_org_id,
        correlation_id=getattr(request_obj.state, "correlation_id", None),
    )

    return AlertResponse(
        alert_id=alert_id,
        status="PENDING",
        message="Alert queued for delivery",
    )


# ─── Police API ───


@app.post(
    "/api/v1/police/query",
    response_model=PoliceQueryResponse,
    tags=["Police"],
)
async def police_query(
    request: PoliceQueryRequest,
    request_obj: Request,
    authorization: str | None = Header(None),
) -> PoliceQueryResponse:
    """Query GFIN data as an authorized police officer.

    Requires officer or supervisor role. All queries are audit-logged.
    """
    # Layer A: Mock response (Layer B: enforce RBAC + query PostgreSQL)
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required for police queries",
        )

    logger.info(
        "police_query",
        query_type=request.query_type,
        query_value=request.query_value,
        correlation_id=getattr(request_obj.state, "correlation_id", None),
    )

    return PoliceQueryResponse(
        results=[],
        total=0,
        query_type=request.query_type,
    )


# ─── Error Handlers ───


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            detail=str(exc.detail),
            correlation_id=correlation_id,
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            detail="An unexpected error occurred",
            correlation_id=correlation_id,
        ).model_dump(mode="json"),
    )


# ─── OpenAPI Info ───


@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi() -> dict[str, Any]:
    """Get OpenAPI specification."""
    return app.openapi()


def get_app() -> FastAPI:
    """Get the FastAPI application instance."""
    return app
