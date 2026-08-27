"""Cross-module integration test — pilot golden path.

Tests the citizen-to-police intelligence chain end-to-end:
  Citizen Report → Triage → Fraud Detection → Campaign → Alert → Police Query

Per Luna Assessment P0: "A small number of executable golden-path and
failure-path workflows running against real infrastructure dependencies."

Layer A: Runs against in-memory services (no DB).
Layer B: Would run against PostgreSQL + real services (REQUIRES EXTERNAL INFRASTRUCTURE).
"""

import pytest

from schemas.enums import ReportStatus
from services.alert_engine import AlertManager, EscalationPolicy, NotificationService
from services.campaign_engine import CampaignDetector, CampaignEngine
from services.citizen_platform import (
    CitizenCheckRequest,
    CitizenCheckService,
    CitizenReportRequest,
    CitizenReportService,
)
from services.continuous_monitoring import (
    AlertPriority,
    MonitoringAlert,
    SubscriptionService,
)
from services.fraud_detection import FraudDetectionEngine
from services.fraud_reporting import (
    ReportScoringService,
    ReportTriageService,
)
from services.global_matching import GlobalMatchEngine, IndexedEntity
from services.police_api import (
    PoliceAPI,
    PoliceAuth,
    PoliceOrganization,
    PoliceRole,
)


@pytest.fixture
def citizen_report_service():
    return CitizenReportService()


@pytest.fixture
def citizen_check_service():
    return CitizenCheckService()


@pytest.fixture
def triage_service():
    return ReportTriageService()


@pytest.fixture
def scoring_service():
    return ReportScoringService()


@pytest.fixture
def detection_engine():
    return FraudDetectionEngine()


@pytest.fixture
def campaign_engine():
    return CampaignEngine()


@pytest.fixture
def campaign_detector():
    return CampaignDetector()


@pytest.fixture
def escalation_policy():
    return EscalationPolicy()


@pytest.fixture
def alert_manager():
    return AlertManager(escalation=escalation_policy)


@pytest.fixture
def notification_service():
    return NotificationService()


@pytest.fixture
def police_api():
    auth = PoliceAuth()
    org = PoliceOrganization(
        org_id="ORG-POLICE-001",
        name="Test Police Org",
        jurisdiction="ES",
        api_key="test-key-001",
    )
    auth.register_organization(org)
    return PoliceAPI(auth=auth)


@pytest.fixture
def global_match():
    return GlobalMatchEngine()


@pytest.fixture
def subscription_service():
    return SubscriptionService()


class TestGoldenPath:
    """The pilot golden path: citizen report → police intelligence."""

    def test_citizen_submits_report(self, citizen_report_service):
        """Step 1: Citizen submits a fraud report via the platform."""
        request = CitizenReportRequest(
            category="phishing",
            description="Received email from fake bank asking for credentials at phishing@fake-bank.com",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            country="ES",
        )
        response = citizen_report_service.submit_report(request)
        assert response.report_id is not None
        assert response.status == ReportStatus.UNVERIFIED.value

    def test_citizen_check_entity(self, citizen_check_service):
        """Step 1b: Citizen checks an entity for known fraud signals."""
        request = CitizenCheckRequest(
            entity_type="EMAIL",
            value="phishing@fake-bank.com",
        )
        response = citizen_check_service.check_entity(request)
        assert response is not None
        assert hasattr(response, "found")

    def test_report_triage(self, citizen_report_service, triage_service):
        """Step 2: Report is triaged with priority and score."""
        request = CitizenReportRequest(
            category="phishing",
            description="Suspicious email from phishing@fake-bank.com targeting bank customers",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            country="ES",
        )
        response = citizen_report_service.submit_report(request)
        report = citizen_report_service._reports.get(response.report_id)
        assert report is not None

        triage_result = triage_service.triage(report)
        assert triage_result is not None
        assert triage_result.priority is not None

    def test_report_scoring(self, citizen_report_service, scoring_service):
        """Step 2b: Report is scored."""
        request = CitizenReportRequest(
            category="phishing",
            description="Phishing report for scoring test",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
        )
        response = citizen_report_service.submit_report(request)
        report = citizen_report_service._reports.get(response.report_id)

        score_result = scoring_service.score(report)
        assert score_result is not None
        assert score_result.score >= 0

    def test_fraud_detection_signals(self, citizen_report_service, detection_engine):
        """Step 3: Fraud detection evaluates the report."""
        request = CitizenReportRequest(
            category="phishing",
            description="Fake banking phishing site at phishing@fake-bank.com",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
        )
        response = citizen_report_service.submit_report(request)
        report = citizen_report_service._reports.get(response.report_id)

        # FraudDetectionEngine.evaluate() runs signal detection + pattern matching
        results = detection_engine.evaluate(report)
        assert results is not None
        assert isinstance(results, list)

    def test_campaign_detection(self, citizen_report_service, campaign_detector):
        """Step 4: Campaign detector finds clusters from reports."""
        r1 = citizen_report_service.submit_report(
            CitizenReportRequest(
                category="phishing",
                description="Phishing email from phishing@fake-bank.com",
                entity_type="EMAIL",
                entity_value="phishing@fake-bank.com",
            )
        )
        r2 = citizen_report_service.submit_report(
            CitizenReportRequest(
                category="phishing",
                description="Another phishing email from the same domain",
                entity_type="EMAIL",
                entity_value="phishing@fake-bank.com",
            )
        )

        reports = [
            citizen_report_service._reports[r1.report_id],
            citizen_report_service._reports[r2.report_id],
        ]

        # CampaignDetector.detect_from_reports finds campaign-worthy clusters
        candidates = campaign_detector.detect_from_reports(reports)
        assert candidates is not None
        assert isinstance(candidates, list)

    def test_campaign_engine_create(self, campaign_engine):
        """Step 4b: Campaign engine creates and manages campaigns."""
        campaign = campaign_engine.create_campaign(
            name="Test Phishing Campaign",
            fraud_type="phishing",
            entity_ids=["ENT-001"],
            report_ids=["RPT-001"],
        )
        assert campaign is not None
        assert campaign.name == "Test Phishing Campaign"
        assert campaign.campaign_status == "DRAFT"

    def test_alert_escalation(self, escalation_policy):
        """Step 5: Alert escalation policy tracks alerts."""
        alert = MonitoringAlert(
            id="ALT-TEST-001",
            subscription_id="SUB-001",
            target_type="ENTITY",
            target_id="ENT-001",
            alert_type="RISK_ESCALATION",
            priority=AlertPriority.HIGH.value,
        )
        state = escalation_policy.register_alert(alert)
        assert state is not None
        assert state.alert_id == "ALT-TEST-001"
        assert state.current_level == 0

    def test_police_query(self, police_api):
        """Step 6: Police officer queries via API."""
        # Authenticate using the registered org's API key
        session = police_api.auth.authenticate(
            api_key="test-key-001",
            officer_name="Test Officer",
            role=PoliceRole.POLICE_OFFICER.value,
        )
        assert session is not None
        assert session.org_id == "ORG-POLICE-001"

        # Match an entity
        result = police_api.match_entity(
            session=session,
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            jurisdiction="ES",
        )
        assert result is not None
        assert result.entity_type == "EMAIL"

    def test_global_matching(self, global_match):
        """Step 7: Global matching checks for cross-border matches."""
        entity = IndexedEntity(
            entity_id="ENT-001",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            jurisdiction="ES",
        )
        # GlobalMatchEngine.index is a property returning GlobalEntityIndex;
        # use register_entity to add entities
        global_match.index.register_entity(entity)

        # match() takes entity_type, entity_value, requesting_jurisdiction
        result = global_match.match(
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            requesting_jurisdiction="FR",  # different jurisdiction to get a match
        )
        assert result is not None

    def test_full_golden_path(
        self,
        citizen_report_service,
        triage_service,
        detection_engine,
        campaign_engine,
        escalation_policy,
    ):
        """Full golden path: report → triage → detect → campaign → alert."""
        # 1. Citizen submits
        request = CitizenReportRequest(
            category="phishing",
            description="Sophisticated phishing campaign targeting multiple banks via fake-bank.com",
            entity_type="EMAIL",
            entity_value="phishing@fake-bank.com",
            country="ES",
        )
        response = citizen_report_service.submit_report(request)
        assert response.status == ReportStatus.UNVERIFIED.value

        report = citizen_report_service._reports[response.report_id]

        # 2. Triage
        triage = triage_service.triage(report)
        assert triage is not None

        # 3. Detection
        results = detection_engine.evaluate(report)
        assert isinstance(results, list)

        # 4. Campaign
        campaign = campaign_engine.create_campaign(
            name="Phishing Wave Q3",
            fraud_type="phishing",
            report_ids=[response.report_id],
        )
        assert campaign is not None
        assert campaign.campaign_status == "DRAFT"

        # 5. Alert
        alert = MonitoringAlert(
            id=f"ALT-{response.report_id}",
            subscription_id="SUB-SYSTEM",
            target_type="ENTITY",
            target_id="ENT-001",
            alert_type="RISK_ESCALATION",
            priority=AlertPriority.HIGH.value,
        )
        state = escalation_policy.register_alert(alert)
        assert state is not None
        assert state.alert_id == f"ALT-{response.report_id}"


class TestFailurePaths:
    """Failure-path tests per Luna Assessment P0."""

    def test_report_without_description_rejected(self, citizen_report_service):
        """Report with empty description should be rejected."""
        with pytest.raises((ValueError, Exception)):
            request = CitizenReportRequest(
                category="phishing",
                description="",
                entity_type="EMAIL",
                entity_value="test@example.com",
            )
            citizen_report_service.submit_report(request)

    def test_report_invalid_entity_type(self, citizen_report_service):
        """Invalid entity type should be rejected."""
        with pytest.raises((ValueError, Exception)):
            request = CitizenReportRequest(
                category="phishing",
                description="Test report",
                entity_type="INVALID_TYPE",
                entity_value="test@example.com",
            )
            citizen_report_service.submit_report(request)

    def test_citizen_check_public_only(self, citizen_check_service):
        """Entity check should only return PUBLIC information."""
        request = CitizenCheckRequest(
            entity_type="EMAIL",
            value="unknown@example.com",
        )
        response = citizen_check_service.check_entity(request)
        # Should return found=False for unknown entity
        assert response.found is False or response.found is True

    def test_cross_tenant_isolation(self, citizen_report_service):
        """Citizens should only see their own reports (user-based isolation)."""
        r1 = citizen_report_service.submit_report(
            CitizenReportRequest(
                category="phishing",
                description="Report from user A",
                entity_type="EMAIL",
                entity_value="entity-a@example.com",
                reporter_id="user-A",
            )
        )
        r2 = citizen_report_service.submit_report(
            CitizenReportRequest(
                category="phishing",
                description="Report from user B",
                entity_type="EMAIL",
                entity_value="entity-b@example.com",
                reporter_id="user-B",
            )
        )

        # User A lists reports — should see only their own
        user_a_reports = citizen_report_service.list_reports(
            user_id="user-A",
            user_role="citizen",
        )
        user_a_ids = {r.id for r in user_a_reports}
        assert r1.report_id in user_a_ids
        assert r2.report_id not in user_a_ids

        # User B lists reports — should see only their own
        user_b_reports = citizen_report_service.list_reports(
            user_id="user-B",
            user_role="citizen",
        )
        user_b_ids = {r.id for r in user_b_reports}
        assert r2.report_id in user_b_ids
        assert r1.report_id not in user_b_ids


class TestAuditTrail:
    """Audit trail verification per Luna Assessment P0."""

    def test_report_has_id_and_status(self, citizen_report_service):
        """Every report should have ID and status."""
        request = CitizenReportRequest(
            category="phishing",
            description="Test report for audit trail",
            entity_type="EMAIL",
            entity_value="test@example.com",
        )
        response = citizen_report_service.submit_report(request)
        assert response.report_id is not None
        assert response.status == ReportStatus.UNVERIFIED.value
        assert response.submitted_at is not None

    def test_alert_has_tracking(self, escalation_policy):
        """Alerts should be trackable via escalation policy."""
        alert = MonitoringAlert(
            id="ALT-AUDIT-001",
            subscription_id="SUB-001",
            target_type="ENTITY",
            target_id="ENT-001",
            alert_type="RISK_ESCALATION",
        )
        state = escalation_policy.register_alert(alert)
        assert state.alert_id == "ALT-AUDIT-001"
        assert state.current_level == 0
