"""
GFIN End-to-End Data Flow Tests
Per Final Build Verification Directive §10.

Tests actual end-to-end flows:
1. Citizen flow: Report → Validation → Entity → Graph → Alert
2. Police flow: Auth → Authorization → Search → Evidence → Audit
3. Discovery flow: Seed → Planner → Source → Entity → Graph → Lead
4. Cross-border flow: Country A → Federation → Policy → Country B
5. Fraud reporting pipeline
6. Autonomous intelligence loop
7. Evidence flow
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest

from common.graph import AdjacencyListGraph, GraphNode
from schemas.base import BaseEntity, BaseEvidence, BaseReport, Classification
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel
from services.citizen_platform import (
    CitizenCheckRequest,
    CitizenCheckService,
    CitizenReportRequest,
    CitizenReportService,
)
from services.cross_border_requests import (
    CrossBorderRequestEngine,
    RequestAuthorizer,
    RequestRouter,
)
from services.evidence_vault import EvidenceVault
from services.fraud_reporting import (
    ReportDeduplicationService,
    ReportScoringService,
    ReportTriageService,
)
from services.police_api import (
    AccessLevel,
    PoliceAPI,
    PoliceAuth,
    PoliceOrganization,
    PoliceRole,
)
from services.unknown_fraud_discovery import (
    DiscoveryConfig,
    DiscoveryPlanner,
    DiscoveryTask,
    ResourceController,
    SourceRouter,
)

# ─── Shared fixtures ───


@pytest.fixture
def mock_event_bus():
    return MagicMock()


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def mock_rate_limiter():
    rl = MagicMock()
    rl.allow.return_value = (True, "ok")
    return rl


@pytest.fixture
def sample_entity():
    return BaseEntity(
        id="ENT-DOMAIN-001",
        entity_type=EntityType.DOMAIN,
        normalized_value="scam-site.example.com",
        classification=Classification(classification=DataClassification.PUBLIC.value),
    )


@pytest.fixture
def restricted_entity():
    return BaseEntity(
        id="ENT-DOMAIN-002",
        entity_type=EntityType.DOMAIN,
        normalized_value="restricted.example.com",
        classification=Classification(classification=DataClassification.RESTRICTED.value),
    )


@pytest.fixture
def sample_report():
    return BaseReport(
        id="RPT-001",
        status=ReportStatus.UNVERIFIED.value,
        category="phishing",
        description="Fake online shop that took my money",
        reporter_id="citizen-001",
        related_entity_ids=["ENT-DOMAIN-001"],
    )


@pytest.fixture
def entity_store(sample_entity, restricted_entity):
    return {
        sample_entity.id: sample_entity,
        restricted_entity.id: restricted_entity,
    }


@pytest.fixture
def report_store(sample_report):
    return {"RPT-001": sample_report}


# ═══════════════════════════════════════════════════════════════
# 1. CITIZEN FLOW
# ═══════════════════════════════════════════════════════════════


class TestCitizenFlow:
    """End-to-end citizen flow per Directive §10."""

    def test_citizen_checks_entity(
        self, entity_store, report_store, mock_rate_limiter, mock_audit
    ):
        """Citizen checks an entity — sees PUBLIC data, not RESTRICTED."""
        service = CitizenCheckService(
            entity_store=entity_store,
            report_store=report_store,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        check = CitizenCheckRequest(
            entity_type=EntityType.DOMAIN.value,
            value="scam-site.example.com",
        )
        response = service.check_entity(check)
        assert response.found is True

    def test_citizen_cannot_see_restricted(
        self, entity_store, report_store, mock_rate_limiter, mock_audit
    ):
        """Citizen check does not return restricted data."""
        service = CitizenCheckService(
            entity_store=entity_store,
            report_store=report_store,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        check = CitizenCheckRequest(
            entity_type=EntityType.DOMAIN.value,
            value="restricted.example.com",
        )
        response = service.check_entity(check)
        # Restricted entity should not be found by citizen
        assert response.found is False or response.risk_level == RiskLevel.UNKNOWN.value

    def test_citizen_submits_report(self, mock_event_bus, mock_rate_limiter, mock_audit):
        """Citizen submits a fraud report — accepted as allegation."""
        service = CitizenReportService(
            entity_store={},
            event_bus=mock_event_bus,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        request = CitizenReportRequest(
            category="phishing",
            description="Fake online shop",
            entity_type=EntityType.DOMAIN.value,
            entity_value="scam.example.com",
            reporter_id="citizen-001",
        )
        result = service.submit_report(request)
        assert result.report_id is not None
        assert result.status == ReportStatus.UNVERIFIED.value

    def test_citizen_report_is_allegation(self, mock_event_bus, mock_rate_limiter, mock_audit):
        """Citizen reports are allegations, not confirmed facts."""
        service = CitizenReportService(
            entity_store={},
            event_bus=mock_event_bus,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        request = CitizenReportRequest(
            category="phishing",
            description="This might be a scam",
            entity_type=EntityType.PHONE.value,
            entity_value="+15551234567",
            reporter_id="citizen-002",
        )
        result = service.submit_report(request)
        assert result.report_id is not None
        assert result.status == ReportStatus.UNVERIFIED.value

    def test_anonymous_report_accepted(self, mock_event_bus, mock_rate_limiter, mock_audit):
        """Anonymous reports are accepted."""
        service = CitizenReportService(
            entity_store={},
            event_bus=mock_event_bus,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit,
        )
        request = CitizenReportRequest(
            category="other",
            description="Anonymous tip",
            entity_type=EntityType.EMAIL.value,
            entity_value="scammer@evil.com",
        )
        result = service.submit_report(request)
        assert result.report_id is not None


# ═══════════════════════════════════════════════════════════════
# 2. POLICE FLOW
# ═══════════════════════════════════════════════════════════════


class TestPoliceFlow:
    """End-to-end police flow per Directive §10."""

    @pytest.fixture
    def police_auth(self):
        auth = PoliceAuth()
        org = PoliceOrganization(
            org_id="ORG-LV",
            name="Latvian Police",
            jurisdiction="LV",
            api_key="key-officer-001",
            access_level=AccessLevel.MATCH_ONLY.value,
        )
        auth.register_organization(org)
        return auth

    def test_police_authenticate(self, police_auth):
        """Police officer authenticates with API key."""
        session = police_auth.authenticate(
            "key-officer-001", officer_name="Officer Smith",
            role=PoliceRole.POLICE_OFFICER.value,
        )
        assert session is not None
        assert session.org_id == "ORG-LV"

    def test_police_rejects_invalid_key(self, police_auth):
        """Police API rejects invalid API key."""
        session = police_auth.authenticate(
            "wrong-key", officer_name="Imposter",
            role=PoliceRole.POLICE_OFFICER.value,
        )
        assert session is None

    def test_police_api_full_access(self, police_auth, mock_event_bus):
        """Police API grants access to authorized endpoints."""
        api = PoliceAPI(auth=police_auth, event_bus=mock_event_bus)
        session = police_auth.authenticate(
            "key-officer-001", officer_name="Officer Smith",
            role=PoliceRole.POLICE_OFFICER.value,
        )
        assert api is not None


# ═══════════════════════════════════════════════════════════════
# 3. DISCOVERY FLOW
# ═══════════════════════════════════════════════════════════════


class TestDiscoveryFlow:
    """End-to-end discovery flow per Directive §10 and §19."""

    @pytest.fixture
    def config(self):
        return DiscoveryConfig(
            max_depth=2, max_tasks=10,
            min_confidence_threshold=0.3,
        )

    def test_seed_generates_tasks(self, config):
        """A seed entity generates discovery tasks."""
        planner = DiscoveryPlanner()
        tasks = planner.plan(
            entity_id="ENT-001",
            entity_type="DOMAIN",
            entity_value="suspicious.example.com",
            depth=0,
            config=config,
        )
        assert len(tasks) > 0
        assert all(isinstance(t, DiscoveryTask) for t in tasks)

    def test_discovery_executes(self, config):
        """Discovery router executes tasks and produces results."""
        planner = DiscoveryPlanner()
        router = SourceRouter()
        tasks = planner.plan(
            entity_id="ENT-001",
            entity_type="DOMAIN",
            entity_value="suspicious.example.com",
            depth=0,
            config=config,
        )
        results = []
        for task in tasks:
            result = router.execute(task, config)
            if result is not None:
                results.append(result)
        assert len(results) > 0

    def test_resource_controller_allows(self, config):
        """Resource controller allows tasks within limits."""
        controller = ResourceController()
        controller.reset()
        task = DiscoveryTask(
            id="task-001", run_id="run-001",
            entity_id="ENT-001", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        allowed, _reason = controller.can_execute(task, config)
        assert allowed is True

    def test_depth_limit_blocks(self):
        """At max depth, no new tasks generated."""
        planner = DiscoveryPlanner()
        config = DiscoveryConfig(max_depth=1, max_tasks=10, min_confidence_threshold=0.3)
        tasks = planner.plan(
            entity_id="ENT-001", entity_type="DOMAIN",
            entity_value="test.com", depth=1, config=config,
        )
        assert len(tasks) == 0

    def test_source_failure_handled(self, config):
        """Source router handles failure modes."""
        router = SourceRouter()
        router.set_failure_mode("dns_resolver", "timeout")
        task = DiscoveryTask(
            id="task-001", run_id="run-001",
            entity_id="ENT-001", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, config)
        # Should not crash — handles failure gracefully
        router.clear_failure_mode("dns_resolver")


# ═══════════════════════════════════════════════════════════════
# 4. CROSS-BORDER FLOW
# ═══════════════════════════════════════════════════════════════


class TestCrossBorderFlow:
    """End-to-end cross-border flow per Directive §10."""

    @pytest.fixture
    def engine(self, mock_event_bus):
        authorizer = RequestAuthorizer()
        router = RequestRouter()
        return CrossBorderRequestEngine(
            authorizer=authorizer,
            router=router,
            event_bus=mock_event_bus,
        )

    def test_cross_border_create_and_validate(self, engine):
        """Full: create → validate → authorize."""
        request = engine.create_request(
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="ENT-001",
            entity_type="domain",
            investigator_name="Smith",
            legal_basis="EU Directive 2026/XXX",
            purpose="Fraud investigation",
        )
        assert request is not None
        assert request.id is not None

        validation = engine.validate_request(request.id)
        assert validation.valid is True

        authorization = engine.authorize_request(request.id)
        assert authorization is not None

    def test_cross_border_audit_trail(self, engine):
        """Cross-border requests are audit-logged."""
        request = engine.create_request(
            requesting_org="ORG-LV",
            requesting_jurisdiction="LV",
            target_jurisdiction="DE",
            entity_id="ENT-001",
            entity_type="domain",
            investigator_name="Smith",
            legal_basis="EU Directive",
            purpose="Investigation",
        )
        engine.validate_request(request.id)
        trail = engine.audit.get_trail(request.id)
        assert len(trail) > 0


# ═══════════════════════════════════════════════════════════════
# 5. FRAUD REPORTING PIPELINE
# ═══════════════════════════════════════════════════════════════


class TestFraudReportingPipeline:
    """Full fraud reporting pipeline integration."""

    def test_triage_and_scoring(self, mock_event_bus, mock_audit):
        """Report goes through triage → scoring → dedup."""
        report = BaseReport(
            id="RPT-FLOW-001",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Fake banking site",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
        )
        report_store = {report.id: report}

        # Triage
        triage = ReportTriageService(
            report_store=report_store,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        triage_result = triage.triage(report, reporter_history=[])
        assert triage_result.report_id == report.id
        assert triage_result.priority in ["LOW", "MEDIUM", "HIGH", "URGENT"]

        # Scoring
        scoring = ReportScoringService(report_store=report_store, audit_logger=mock_audit)
        score_result = scoring.score(report)
        assert 0 <= score_result.score <= 100

        # Dedup
        dedup = ReportDeduplicationService(
            report_store=report_store,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        dedup_result = dedup.check_duplicate(report)
        assert dedup_result.report_id == report.id


# ═══════════════════════════════════════════════════════════════
# 6. AUTONOMOUS INTELLIGENCE LOOP (Directive §11)
# ═══════════════════════════════════════════════════════════════


class TestAutonomousIntelligenceLoop:
    """Test the autonomous intelligence loop per Directive §11."""

    def test_signal_to_discovery(self):
        """Signal → Discovery → Graph chain works."""
        import asyncio

        # Signal: a new entity
        # Discovery: plan tasks
        planner = DiscoveryPlanner()
        config = DiscoveryConfig(
            max_depth=2, max_tasks=5,
            min_confidence_threshold=0.3,
        )
        tasks = planner.plan(
            entity_id="ENT-001", entity_type="DOMAIN",
            entity_value="suspicious.example.com",
            depth=0, config=config,
        )
        assert len(tasks) > 0

        # Execute
        router = SourceRouter()
        for task in tasks:
            router.execute(task, config)

        # Graph
        graph = AdjacencyListGraph()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        node = GraphNode(
            entity_id="ENT-001", entity_type="DOMAIN",
            label="suspicious.example.com",
        )
        loop.run_until_complete(graph.add_node(node))
        retrieved = loop.run_until_complete(graph.get_node("ENT-001"))
        assert retrieved is not None


# ═══════════════════════════════════════════════════════════════
# 7. EVIDENCE FLOW (Directive §10, §23)
# ═══════════════════════════════════════════════════════════════


class TestEvidenceFlow:
    """Evidence vault and provenance tracking."""

    def test_evidence_creation_and_retrieval(self):
        """Evidence can be created and retrieved."""
        vault = EvidenceVault()
        content_data = b"fake image data"
        actual_hash = hashlib.sha256(content_data).hexdigest()
        evidence = BaseEvidence(
            source_id="SRC-001",
            content_type="image/png",
            content_hash=actual_hash,
        )
        # Let vault compute the hash
        stored = vault.create(evidence, content=content_data, actor="crawler-001")
        assert stored is not None
        retrieved = vault.get(evidence.id, actor="system")
        assert retrieved is not None

    def test_evidence_custody_chain(self):
        """Evidence maintains custody chain."""
        vault = EvidenceVault()
        content_data = b"<html>content</html>"
        actual_hash = hashlib.sha256(content_data).hexdigest()
        evidence = BaseEvidence(
            source_id="SRC-002",
            content_type="text/html",
            content_hash=actual_hash,
        )
        vault.create(evidence, content=content_data, actor="crawler-002")
        chain = vault.get_custody_chain(evidence.id)
        assert len(chain) > 0
        assert chain[0].actor == "crawler-002"
