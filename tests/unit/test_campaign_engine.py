"""Tests for Campaign Engine — Module 16.

Tests cover:
- CampaignEngine: create, update, lifecycle, linking, scoring
- CampaignDetector: report clustering, entity clustering
- CampaignScorer: score calculation, bands
- CampaignLinker: report/entity linking
- Integration: full pipeline detect → create → score → link
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from schemas.base import AuditMetadata, BaseEntity, BaseReport, Classification
from schemas.entities import CampaignEntity
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel
from services.campaign_engine import (
    CampaignDetector,
    CampaignEngine,
    CampaignLinker,
    CampaignScorer,
)

# ─── Fixtures ───


@pytest.fixture
def now():
    return datetime.now(UTC)


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def engine(mock_event_bus, mock_audit):
    return CampaignEngine(
        event_bus=mock_event_bus,
        audit_logger=mock_audit,
    )


@pytest.fixture
def reports_for_campaign(now):
    """6 reports sharing ENT-001 and ENT-002, all phishing."""
    reports = {}
    for i in range(6):
        reports[f"RPT-C{i:02d}"] = BaseReport(
            id=f"RPT-C{i:02d}",
            status=ReportStatus.CORROBORATED.value if i < 3 else ReportStatus.UNVERIFIED.value,
            category="phishing",
            description=f"Phishing report {i}.",
            reporter_id=f"citizen-{i}",
            related_entity_ids=["ENT-001", "ENT-002"],
            country=f"Country{i % 3}" if i < 4 else None,
            audit=AuditMetadata(created_at=now - timedelta(days=i)),
        )
    return reports


@pytest.fixture
def entities_with_infra():
    return {
        "ENT-001": BaseEntity(
            id="ENT-001",
            entity_type=EntityType.URL,
            value="https://scam1.test",
            normalized_value="https://scam1.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
            metadata={"ip_addresses": ["1.2.3.4"], "asn": "AS12345"},
        ),
        "ENT-002": BaseEntity(
            id="ENT-002",
            entity_type=EntityType.URL,
            value="https://scam2.test",
            normalized_value="https://scam2.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
            metadata={"ip_addresses": ["1.2.3.4"], "asn": "AS12345"},
        ),
        "ENT-003": BaseEntity(
            id="ENT-003",
            entity_type=EntityType.URL,
            value="https://clean.test",
            normalized_value="https://clean.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
            metadata={"ip_addresses": ["9.8.7.6"]},
        ),
    }


# ─── Campaign Engine Tests ───


class TestCampaignEngine:
    def test_create_campaign(self, engine):
        camp = engine.create_campaign(name="Test Campaign", fraud_type="phishing")
        assert camp.name == "Test Campaign"
        assert camp.campaign_status == "DRAFT"
        assert camp.fraud_type == "phishing"
        assert camp in engine.list_campaigns()

    def test_create_campaign_with_entities(self, engine):
        camp = engine.create_campaign(
            name="Test",
            entity_ids=["ENT-001", "ENT-002"],
        )
        assert camp.entity_count == 2
        assert "ENT-001" in camp.related_entity_ids

    def test_create_campaign_event(self, engine, mock_event_bus):
        engine.create_campaign(name="Test")
        mock_event_bus.publish.assert_called()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "campaign.created"

    def test_create_campaign_audit(self, engine, mock_audit):
        engine.create_campaign(name="Test")
        mock_audit.log.assert_called()

    def test_create_campaign_default_restricted(self, engine):
        camp = engine.create_campaign(name="Test")
        # Campaigns default to RESTRICTED classification
        assert camp.classification.classification == DataClassification.RESTRICTED.value

    def test_update_campaign(self, engine):
        camp = engine.create_campaign(name="Original")
        updated = engine.update_campaign(camp.id, {"name": "Updated", "fraud_type": "crypto_fraud"})
        assert updated.name == "Updated"
        assert updated.fraud_type == "crypto_fraud"

    def test_update_nonexistent(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.update_campaign("NONEXISTENT", {"name": "X"})

    def test_activate_campaign(self, engine):
        camp = engine.create_campaign(name="Test")
        activated = engine.activate_campaign(camp.id)
        assert activated.campaign_status == "ACTIVE"

    def test_dismantle_campaign(self, engine):
        camp = engine.create_campaign(name="Test")
        engine.activate_campaign(camp.id)
        dismantled = engine.dismantle_campaign(camp.id)
        assert dismantled.campaign_status == "DISMANTLED"
        assert dismantled.end_date is not None

    def test_reactivate_campaign(self, engine):
        camp = engine.create_campaign(name="Test")
        engine.activate_campaign(camp.id)
        engine.transition_status(camp.id, "DORMANT")
        reactivated = engine.reactivate_campaign(camp.id)
        assert reactivated.campaign_status == "ACTIVE"

    def test_invalid_transition(self, engine):
        camp = engine.create_campaign(name="Test")
        # DRAFT → DISMANTLED is not valid
        with pytest.raises(ValueError, match="Invalid transition"):
            engine.dismantle_campaign(camp.id)

    def test_dismantled_is_terminal(self, engine):
        camp = engine.create_campaign(name="Test")
        engine.activate_campaign(camp.id)
        engine.dismantle_campaign(camp.id)
        with pytest.raises(ValueError, match="Invalid transition"):
            engine.reactivate_campaign(camp.id)

    def test_dismantle_event(self, engine, mock_event_bus):
        camp = engine.create_campaign(name="Test")
        engine.activate_campaign(camp.id)
        mock_event_bus.reset_mock()
        engine.dismantle_campaign(camp.id)
        # Find the dismantled event
        topics = [c.kwargs["topic"] for c in mock_event_bus.publish.call_args_list]
        assert "campaign.dismantled" in topics

    def test_link_entity(self, engine):
        camp = engine.create_campaign(name="Test")
        engine.link_entity(camp.id, "ENT-001")
        assert "ENT-001" in camp.related_entity_ids
        assert camp.entity_count == 1

    def test_link_entity_no_duplicate(self, engine):
        camp = engine.create_campaign(name="Test", entity_ids=["ENT-001"])
        engine.link_entity(camp.id, "ENT-001")
        assert camp.related_entity_ids.count("ENT-001") == 1

    def test_unlink_entity(self, engine):
        camp = engine.create_campaign(name="Test", entity_ids=["ENT-001", "ENT-002"])
        engine.unlink_entity(camp.id, "ENT-001")
        assert "ENT-001" not in camp.related_entity_ids
        assert camp.entity_count == 1

    def test_link_report(self, engine):
        camp = engine.create_campaign(name="Test")
        engine.link_report(camp.id, "RPT-001")
        assert "RPT-001" in engine.get_campaign_reports(camp.id)

    def test_link_report_no_duplicate(self, engine):
        camp = engine.create_campaign(name="Test", report_ids=["RPT-001"])
        engine.link_report(camp.id, "RPT-001")
        assert engine.get_campaign_reports(camp.id).count("RPT-001") == 1

    def test_get_campaign(self, engine):
        camp = engine.create_campaign(name="Test")
        assert engine.get_campaign(camp.id) is not None

    def test_get_nonexistent(self, engine):
        assert engine.get_campaign("NONEXISTENT") is None

    def test_list_campaigns_by_status(self, engine):
        c1 = engine.create_campaign(name="Draft")
        c2 = engine.create_campaign(name="Active")
        engine.activate_campaign(c2.id)
        active = engine.list_campaigns(status="ACTIVE")
        assert len(active) == 1
        assert active[0].name == "Active"

    def test_score_campaign(self, engine, reports_for_campaign):
        camp = engine.create_campaign(
            name="Phishing Wave",
            entity_ids=["ENT-001", "ENT-002"],
            report_ids=list(reports_for_campaign.keys()),
        )
        engine._reports = reports_for_campaign
        engine._scorer = CampaignScorer(report_store=reports_for_campaign)
        result = engine.score_campaign(camp.id)
        assert 0 <= result.score <= 100
        assert result.severity in (
            RiskLevel.LOW.value,
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        )

    def test_score_nonexistent(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.score_campaign("NONEXISTENT")


# ─── Campaign Detector Tests ───


class TestCampaignDetector:
    def test_detect_from_reports(self, now):
        reports = []
        for i in range(5):
            reports.append(
                BaseReport(
                    id=f"RPT-D{i}",
                    status=ReportStatus.UNVERIFIED.value,
                    category="phishing",
                    description=f"Phishing {i}.",
                    reporter_id=f"citizen-{i}",
                    related_entity_ids=["ENT-SHARED"],
                    audit=AuditMetadata(created_at=now),
                )
            )
        # Add an isolated report
        reports.append(
            BaseReport(
                id="RPT-ISO",
                status=ReportStatus.UNVERIFIED.value,
                category="other",
                description="Isolated.",
                reporter_id="citizen-iso",
                related_entity_ids=["ENT-ISO"],
                audit=AuditMetadata(created_at=now),
            )
        )
        detector = CampaignDetector()
        candidates = detector.detect_from_reports(reports)
        assert len(candidates) >= 1
        assert candidates[0].fraud_type == "phishing"
        assert len(candidates[0].entity_ids) >= 1
        assert len(candidates[0].report_ids) >= 3

    def test_detect_below_threshold(self, now):
        reports = []
        for i in range(2):  # Only 2 reports — below threshold of 3
            reports.append(
                BaseReport(
                    id=f"RPT-S{i}",
                    status=ReportStatus.UNVERIFIED.value,
                    category="phishing",
                    description=f"Phishing {i}.",
                    reporter_id=f"citizen-{i}",
                    related_entity_ids=["ENT-S"],
                    audit=AuditMetadata(created_at=now),
                )
            )
        detector = CampaignDetector()
        candidates = detector.detect_from_reports(reports)
        assert len(candidates) == 0

    def test_detect_multiple_categories(self, now):
        reports = []
        for i in range(4):
            reports.append(
                BaseReport(
                    id=f"RPT-M{i}",
                    status=ReportStatus.UNVERIFIED.value,
                    category="phishing" if i < 2 else "investment_fraud",
                    description=f"Report {i}.",
                    reporter_id=f"citizen-{i}",
                    related_entity_ids=[f"ENT-{i}"],  # No shared entities
                    audit=AuditMetadata(created_at=now),
                )
            )
        detector = CampaignDetector()
        candidates = detector.detect_from_reports(reports)
        # No shared entities → no clusters
        assert len(candidates) == 0

    def test_detect_from_entities(self, entities_with_infra):
        detector = CampaignDetector()
        candidates = detector.detect_from_entities(entities_with_infra)
        # ENT-001 and ENT-002 share IP 1.2.3.4 and ASN AS12345
        assert len(candidates) >= 1
        assert any("1.2.3.4" in c.detection_reason for c in candidates)

    def test_detect_from_entities_no_overlap(self):
        entities = {
            "ENT-001": BaseEntity(
                id="ENT-001",
                entity_type=EntityType.URL,
                value="https://a.test",
                normalized_value="https://a.test",
                classification=Classification(classification=DataClassification.PUBLIC.value),
                metadata={"ip_addresses": ["1.1.1.1"]},
            ),
            "ENT-002": BaseEntity(
                id="ENT-002",
                entity_type=EntityType.URL,
                value="https://b.test",
                normalized_value="https://b.test",
                classification=Classification(classification=DataClassification.PUBLIC.value),
                metadata={"ip_addresses": ["2.2.2.2"]},
            ),
        }
        detector = CampaignDetector()
        candidates = detector.detect_from_entities(entities)
        assert len(candidates) == 0


# ─── Campaign Scorer Tests ───


class TestCampaignScorer:
    def test_score_low(self, now):
        campaign = CampaignEntity(
            id="CAMP-LOW",
            name="Low Campaign",
            related_entity_ids=["ENT-001"],
            affected_countries=["CountryA"],
        )
        scorer = CampaignScorer()
        result = scorer.score(campaign, report_ids=["RPT-001"])
        assert result.score <= 25
        assert result.severity == RiskLevel.LOW.value

    def test_score_high(self, reports_for_campaign):
        campaign = CampaignEntity(
            id="CAMP-HIGH",
            name="High Campaign",
            related_entity_ids=["ENT-001", "ENT-002", "ENT-003"],
            affected_countries=["CountryA", "CountryB", "CountryC"],
        )
        scorer = CampaignScorer(report_store=reports_for_campaign)
        result = scorer.score(campaign, report_ids=list(reports_for_campaign.keys()))
        # 6 reports (3 corroborated), 3 entities, 3 countries → high score
        assert result.score > 25

    def test_score_max_100(self, now):
        campaign = CampaignEntity(
            id="CAMP-MAX",
            name="Max Campaign",
            related_entity_ids=[f"ENT-{i}" for i in range(20)],
            affected_countries=[f"Country{i}" for i in range(20)],
        )
        report_ids = [f"RPT-{i}" for i in range(50)]
        # Create reports
        reports = {}
        for i in range(50):
            reports[f"RPT-{i}"] = BaseReport(
                id=f"RPT-{i}",
                status=ReportStatus.CORROBORATED.value,
                category="phishing",
                description=f"Report {i}.",
                reporter_id=f"citizen-{i}",
                related_entity_ids=["ENT-001"],
                audit=AuditMetadata(created_at=now),
            )
        scorer = CampaignScorer(report_store=reports)
        result = scorer.score(campaign, report_ids=report_ids)
        assert result.score <= 100

    def test_score_breakdown(self, now):
        campaign = CampaignEntity(
            id="CAMP-BD",
            name="Breakdown Test",
            related_entity_ids=["ENT-001", "ENT-002"],
            affected_countries=["CountryA", "CountryB"],
        )
        scorer = CampaignScorer()
        result = scorer.score(campaign, report_ids=["RPT-001", "RPT-002"])
        assert "entity_count" in result.breakdown
        assert "report_count" in result.breakdown
        assert "corroborated_count" in result.breakdown
        assert "affected_countries" in result.breakdown
        assert "infrastructure_overlap" in result.breakdown

    def test_score_updates_campaign_severity(self, now):
        campaign = CampaignEntity(
            id="CAMP-SEV",
            name="Severity Test",
            related_entity_ids=["ENT-001"],
            affected_countries=["CountryA"],
        )
        scorer = CampaignScorer()
        scorer.score(campaign, report_ids=["RPT-001"])
        assert campaign.severity in (
            RiskLevel.LOW.value,
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        )

    def test_get_score(self, now):
        campaign = CampaignEntity(id="CAMP-GET", name="Test")
        scorer = CampaignScorer()
        scorer.score(campaign)
        assert scorer.get_score("CAMP-GET") is not None


# ─── Campaign Linker Tests ───


class TestCampaignLinker:
    def test_link_by_entity(self, now):
        campaign = CampaignEntity(
            id="CAMP-001",
            name="Test Campaign",
            campaign_status="ACTIVE",
            fraud_type="phishing",
            related_entity_ids=["ENT-001", "ENT-002"],
        )
        linker = CampaignLinker(campaign_store={"CAMP-001": campaign})
        report = BaseReport(
            id="RPT-LINK",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Test report.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        matched = linker.link_report(report)
        assert "CAMP-001" in matched

    def test_link_by_fraud_type(self, now):
        campaign = CampaignEntity(
            id="CAMP-001",
            name="Test Campaign",
            campaign_status="ACTIVE",
            fraud_type="phishing",
            related_entity_ids=["ENT-DIFFERENT"],
        )
        linker = CampaignLinker(campaign_store={"CAMP-001": campaign})
        report = BaseReport(
            id="RPT-FT",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Test.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-NOMATCH"],
            audit=AuditMetadata(created_at=now),
        )
        matched = linker.link_report(report)
        assert "CAMP-001" in matched

    def test_no_link_dismantled(self, now):
        campaign = CampaignEntity(
            id="CAMP-001",
            name="Dismantled",
            campaign_status="DISMANTLED",
            fraud_type="phishing",
            related_entity_ids=["ENT-001"],
        )
        linker = CampaignLinker(campaign_store={"CAMP-001": campaign})
        report = BaseReport(
            id="RPT-NO",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Test.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        matched = linker.link_report(report)
        assert len(matched) == 0

    def test_no_match(self, now):
        campaign = CampaignEntity(
            id="CAMP-001",
            name="Test",
            campaign_status="ACTIVE",
            fraud_type="romance_scam",
            related_entity_ids=["ENT-001"],
        )
        linker = CampaignLinker(campaign_store={"CAMP-001": campaign})
        report = BaseReport(
            id="RPT-NM",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Test.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-999"],
            audit=AuditMetadata(created_at=now),
        )
        matched = linker.link_report(report)
        assert len(matched) == 0


# ─── Integration Tests ───


class TestIntegrationCampaign:
    def test_detect_create_score_pipeline(self, reports_for_campaign, mock_event_bus, mock_audit):
        engine = CampaignEngine(
            report_store=reports_for_campaign,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )

        # 1. Detect campaigns
        candidates = engine.detect_campaigns()
        assert len(candidates) >= 1

        # 2. Auto-create from detection
        created = engine.detect_and_create()
        assert len(created) >= 1

        # 3. Score the created campaign
        for camp in created:
            result = engine.score_campaign(camp.id)
            assert 0 <= result.score <= 100

    def test_link_report_to_campaigns(self, reports_for_campaign, mock_event_bus, mock_audit, now):
        engine = CampaignEngine(
            report_store=reports_for_campaign,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )

        # Create a campaign
        camp = engine.create_campaign(
            name="Phishing Wave",
            fraud_type="phishing",
            entity_ids=["ENT-001", "ENT-002"],
        )
        engine.activate_campaign(camp.id)

        # Link a new report
        new_report = BaseReport(
            id="RPT-NEW-LINK",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="New phishing report.",
            reporter_id="citizen-new",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        matched = engine.link_report_to_campaigns(new_report)
        assert camp.id in matched

    def test_full_lifecycle(self, engine, mock_event_bus):
        # Create
        camp = engine.create_campaign(name="Lifecycle Test", fraud_type="phishing")
        assert camp.campaign_status == "DRAFT"

        # Activate
        engine.activate_campaign(camp.id)
        assert camp.campaign_status == "ACTIVE"

        # Link entities
        engine.link_entity(camp.id, "ENT-001")
        engine.link_entity(camp.id, "ENT-002")

        # Go dormant
        engine.transition_status(camp.id, "DORMANT")
        assert camp.campaign_status == "DORMANT"

        # Reactivate
        engine.reactivate_campaign(camp.id)
        assert camp.campaign_status == "ACTIVE"

        # Dismantle
        engine.dismantle_campaign(camp.id)
        assert camp.campaign_status == "DISMANTLED"
        assert camp.end_date is not None

    def test_check_dormant(self, mock_event_bus, mock_audit, now):
        engine = CampaignEngine(
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        camp = engine.create_campaign(name="Old Campaign")
        engine.activate_campaign(camp.id)

        # Set last activity to 40 days ago
        camp.audit.created_at = now - timedelta(days=40)

        dormant = engine.check_dormant(now=now)
        assert camp.id in dormant
        assert camp.campaign_status == "DORMANT"

    def test_check_dormant_not_dormant(self, mock_event_bus, mock_audit, now):
        engine = CampaignEngine(
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        camp = engine.create_campaign(name="Recent Campaign")
        engine.activate_campaign(camp.id)
        camp.audit.created_at = now - timedelta(days=5)

        dormant = engine.check_dormant(now=now)
        assert camp.id not in dormant
        assert camp.campaign_status == "ACTIVE"
