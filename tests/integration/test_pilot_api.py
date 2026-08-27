"""Integration tests for the pilot vertical slice — API contract tests.

Tests the citizen-to-police intelligence chain through the FastAPI API layer.
Uses httpx AsyncClient with the FastAPI TestClient (no external server needed).

Layer A: Runs against in-memory API (no DB required).
Layer B: Would run against real PostgreSQL + API (REQUIRES EXTERNAL INFRASTRUCTURE).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from api.pilot_api import app


@pytest.fixture
async def client():
    """Async HTTP client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    """Health and readiness endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        resp = await client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestCitizenReport:
    """Citizen fraud report submission and retrieval."""

    @pytest.mark.asyncio
    async def test_submit_report(self, client):
        resp = await client.post(
            "/api/v1/reports",
            json={
                "report_type": "phishing",
                "description": "Received a suspicious email claiming to be from my bank asking for credentials.",
                "entity_refs": ["phishing@fake-bank.com"],
                "is_anonymous": False,
                "reporter_email": "citizen@example.com",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_id"].startswith("RPT-")
        assert data["status"] == "UNVERIFIED"
        assert "successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_submit_report_minimal(self, client):
        resp = await client.post(
            "/api/v1/reports",
            json={
                "report_type": "investment_scam",
                "description": "Was contacted about a fake investment opportunity.",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "UNVERIFIED"

    @pytest.mark.asyncio
    async def test_submit_report_anonymous(self, client):
        resp = await client.post(
            "/api/v1/reports",
            json={
                "report_type": "romance_scam",
                "description": "Met someone online who asked for money.",
                "is_anonymous": True,
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_report_validation_short_description(self, client):
        resp = await client.post(
            "/api/v1/reports",
            json={
                "report_type": "phishing",
                "description": "short",  # < 10 chars
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_report_validation_missing_type(self, client):
        resp = await client.post(
            "/api/v1/reports",
            json={
                "description": "A valid description of the incident.",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_report(self, client):
        resp = await client.get("/api/v1/reports/RPT-TEST1234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == "RPT-TEST1234"


class TestTriage:
    """Report triage and fraud detection."""

    @pytest.mark.asyncio
    async def test_triage_report(self, client):
        resp = await client.post("/api/v1/reports/RPT-TEST001/triage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == "RPT-TEST001"
        assert "priority" in data
        assert "score" in data
        assert isinstance(data["signals"], list)


class TestAlerts:
    """Alert creation and routing."""

    @pytest.mark.asyncio
    async def test_create_alert(self, client):
        resp = await client.post(
            "/api/v1/alerts",
            json={
                "alert_type": "new_report",
                "source_report_id": "RPT-TEST001",
                "target_org_id": "ORG-POLICE-001",
                "channel": "EMAIL",
                "priority": "HIGH",
                "message": "High-risk report detected",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["alert_id"].startswith("ALT-")
        assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_create_alert_minimal(self, client):
        resp = await client.post(
            "/api/v1/alerts",
            json={
                "alert_type": "high_risk",
                "source_report_id": "RPT-001",
                "target_org_id": "ORG-001",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_alert_validation_missing_field(self, client):
        resp = await client.post(
            "/api/v1/alerts",
            json={
                "source_report_id": "RPT-001",
                "target_org_id": "ORG-001",
            },
        )
        assert resp.status_code == 422


class TestPoliceAPI:
    """Police officer queries — requires authorization."""

    @pytest.mark.asyncio
    async def test_police_query_unauthorized(self, client):
        resp = await client.post(
            "/api/v1/police/query",
            json={
                "query_type": "report",
                "query_value": "phishing",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_police_query_authorized(self, client):
        resp = await client.post(
            "/api/v1/police/query",
            json={
                "query_type": "report",
                "query_value": "phishing",
            },
            headers={"Authorization": "Bearer test-officer-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query_type"] == "report"
        assert "results" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_police_query_entity(self, client):
        resp = await client.post(
            "/api/v1/police/query",
            json={
                "query_type": "entity",
                "query_value": "phishing@fake-bank.com",
            },
            headers={"Authorization": "Bearer test-officer-token"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_police_query_campaign(self, client):
        resp = await client.post(
            "/api/v1/police/query",
            json={
                "query_type": "campaign",
                "query_value": "phishing wave",
            },
            headers={"Authorization": "Bearer test-officer-token"},
        )
        assert resp.status_code == 200


class TestCorrelationID:
    """Correlation ID middleware for distributed tracing."""

    @pytest.mark.asyncio
    async def test_correlation_id_generated(self, client):
        resp = await client.get("/health")
        assert "X-Correlation-ID" in resp.headers
        assert resp.headers["X-Correlation-ID"]  # not empty

    @pytest.mark.asyncio
    async def test_correlation_id_preserved(self, client):
        test_id = "test-correlation-123"
        resp = await client.get(
            "/health",
            headers={"X-Correlation-ID": test_id},
        )
        assert resp.headers["X-Correlation-ID"] == test_id

    @pytest.mark.asyncio
    async def test_correlation_id_on_error(self, client):
        resp = await client.post(
            "/api/v1/police/query",
            json={"query_type": "report", "query_value": "test"},
        )
        assert resp.status_code == 401
        assert "X-Correlation-ID" in resp.headers


class TestOpenAPI:
    """OpenAPI specification and documentation."""

    @pytest.mark.asyncio
    async def test_openapi_json(self, client):
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "GFIN — Global Fraud Intelligence Network"
        assert "/api/v1/reports" in spec.get("paths", {})

    @pytest.mark.asyncio
    async def test_docs_available(self, client):
        resp = await client.get("/api/docs")
        assert resp.status_code == 200
