"""Tests for Fraud Reporting Pipeline — Module 14.

Tests cover:
- ReportTriageService: priority, spam detection, overrides, volume spikes
- ReportEnrichmentService: entity linking, related reports, campaigns, infrastructure
- ReportScoringService: score calculation, bands, determinism, batch
- ReportDeduplicationService: duplicate detection, similarity, marking
- CampaignLinkingService: linking, no-match, active/inactive campaigns
- Integration: full pipeline triage → enrich → score → dedup → campaign
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from schemas.base import AuditMetadata, BaseEntity, BaseReport, Classification
from schemas.entities import CampaignEntity
from schemas.enums import DataClassification, EntityType, ReportStatus, RiskLevel
from services.fraud_reporting import (
    CampaignLinkingService,
    DeduplicationResult,
    EnrichmentResult,
    ReportDeduplicationService,
    ReportEnrichmentService,
    ReportScoringService,
    ReportTriageService,
)

# ─── Fixtures ───


@pytest.fixture
def now():
    return datetime.now(UTC)


@pytest.fixture
def audit_meta(now):
    return AuditMetadata(created_at=now)


@pytest.fixture
def phishing_report(now):
    return BaseReport(
        id="RPT-001",
        status=ReportStatus.UNVERIFIED.value,
        category="phishing",
        description="I received a suspicious email claiming to be from my bank asking for credentials.",
        reporter_id="citizen-001",
        related_entity_ids=["ENT-001"],
        related_evidence_ids=["EV-001", "EV-002"],
        risk_level=RiskLevel.UNKNOWN.value,
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def investment_report(now):
    return BaseReport(
        id="RPT-002",
        status=ReportStatus.UNVERIFIED.value,
        category="investment_fraud",
        description="They promised 10% returns on crypto investment and took my money.",
        reporter_id="citizen-002",
        related_entity_ids=["ENT-002"],
        related_evidence_ids=["EV-003"],
        risk_level=RiskLevel.HIGH.value,
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def corroborated_report(now):
    return BaseReport(
        id="RPT-003",
        status=ReportStatus.CORROBORATED.value,
        category="phishing",
        description="Phishing site impersonating bank.",
        reporter_id="citizen-003",
        related_entity_ids=["ENT-001"],
        related_evidence_ids=["EV-004", "EV-005", "EV-006"],
        risk_level=RiskLevel.HIGH.value,
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def short_report(now):
    return BaseReport(
        id="RPT-004",
        status=ReportStatus.UNVERIFIED.value,
        category="other",
        description="bad",
        reporter_id="citizen-004",
        related_entity_ids=["ENT-003"],
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def gibberish_report(now):
    return BaseReport(
        id="RPT-005",
        status=ReportStatus.UNVERIFIED.value,
        category="other",
        description="xqz wkj nvr plm bxc tgf",
        reporter_id="citizen-005",
        related_entity_ids=["ENT-004"],
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def duplicate_report(now):
    return BaseReport(
        id="RPT-006",
        status=ReportStatus.UNVERIFIED.value,
        category="phishing",
        description="I received a suspicious email claiming to be from my bank asking for credentials.",
        reporter_id="citizen-006",
        related_entity_ids=["ENT-001"],
        audit=AuditMetadata(created_at=now),
    )


@pytest.fixture
def active_campaign():
    return CampaignEntity(
        id="CAMP-001",
        name="Bank Phishing Wave 2026",
        campaign_status="ACTIVE",
        severity=RiskLevel.HIGH.value,
        fraud_type="phishing",
        related_entity_ids=["ENT-001"],
    )


@pytest.fixture
def inactive_campaign():
    return CampaignEntity(
        id="CAMP-002",
        name="Old Scam",
        campaign_status="DISMANTLED",
        fraud_type="phishing",
        related_entity_ids=["ENT-001"],
    )


@pytest.fixture
def entity_store():
    return {
        "ENT-001": BaseEntity(
            id="ENT-001",
            entity_type=EntityType.URL,
            value="https://phishing.test",
            normalized_value="https://phishing.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
            metadata={"ip_addresses": ["1.2.3.4"], "asn": "AS12345"},
        ),
        "ENT-002": BaseEntity(
            id="ENT-002",
            entity_type=EntityType.DOMAIN,
            value="scam.test",
            normalized_value="scam.test",
            classification=Classification(classification=DataClassification.PUBLIC.value),
        ),
    }


@pytest.fixture
def report_store(phishing_report, investment_report, corroborated_report):
    return {
        "RPT-001": phishing_report,
        "RPT-002": investment_report,
        "RPT-003": corroborated_report,
    }


@pytest.fixture
def campaign_store(active_campaign, inactive_campaign):
    return {
        "CAMP-001": active_campaign,
        "CAMP-002": inactive_campaign,
    }


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def triage_service(report_store, mock_event_bus, mock_audit):
    return ReportTriageService(
        report_store=report_store,
        event_bus=mock_event_bus,
        audit_logger=mock_audit,
    )


@pytest.fixture
def enrichment_service(entity_store, report_store, campaign_store, mock_event_bus, mock_audit):
    return ReportEnrichmentService(
        entity_store=entity_store,
        report_store=report_store,
        campaign_store=campaign_store,
        event_bus=mock_event_bus,
        audit_logger=mock_audit,
    )


@pytest.fixture
def scoring_service(report_store, mock_audit):
    return ReportScoringService(
        report_store=report_store,
        audit_logger=mock_audit,
    )


@pytest.fixture
def dedup_service(report_store, mock_event_bus, mock_audit):
    return ReportDeduplicationService(
        report_store=report_store,
        event_bus=mock_event_bus,
        audit_logger=mock_audit,
    )


@pytest.fixture
def campaign_service(campaign_store, mock_event_bus, mock_audit):
    return CampaignLinkingService(
        campaign_store=campaign_store,
        event_bus=mock_event_bus,
        audit_logger=mock_audit,
    )


# ─── Triage Tests ───


class TestReportTriage:
    def test_triage_phishing_high_priority(self, triage_service, phishing_report):
        result = triage_service.triage(phishing_report)
        assert result.priority in ("HIGH", "URGENT")
        assert result.is_spam is False

    def test_triage_other_low_priority(self, triage_service, now):
        report = BaseReport(
            id="RPT-X01",
            status=ReportStatus.UNVERIFIED.value,
            category="other",
            description="Something happened with this website.",
            reporter_id="citizen-x01",
            related_entity_ids=["ENT-X01"],
            audit=AuditMetadata(created_at=now),
        )
        result = triage_service.triage(report)
        assert result.priority == "LOW"

    def test_triage_investment_fraud_high(self, triage_service, investment_report):
        result = triage_service.triage(investment_report)
        assert result.priority in ("HIGH", "URGENT")

    def test_triage_spam_short_description(self, triage_service, short_report):
        result = triage_service.triage(short_report)
        assert result.is_spam is True
        assert "too short" in result.spam_reason.lower()

    def test_triage_spam_gibberish(self, triage_service, gibberish_report):
        result = triage_service.triage(gibberish_report)
        assert result.is_spam is True
        assert "gibberish" in result.spam_reason.lower()

    def test_triage_spam_marks_status(self, triage_service, short_report):
        triage_service.triage(short_report)
        assert short_report.status == "SPAM"

    def test_triage_repeat_reporter_boost(self, triage_service, now):
        """Reporter with 5+ reports should get priority boost."""
        history = []
        for i in range(5):
            history.append(
                BaseReport(
                    id=f"RPT-H{i:02d}",
                    status=ReportStatus.UNVERIFIED.value,
                    category="romance_scam",
                    description=f"Romance scam report number {i}.",
                    reporter_id="citizen-001",
                    related_entity_ids=["ENT-001"],
                    audit=AuditMetadata(created_at=now - timedelta(days=i + 1)),
                )
            )
        report = BaseReport(
            id="RPT-CUR",
            status=ReportStatus.UNVERIFIED.value,
            category="romance_scam",
            description="Another romance scam from the same person.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = triage_service.triage(report, reporter_history=history)
        # romance_scam is MEDIUM by default, repeat reporter should boost to HIGH
        assert result.priority == "HIGH"

    def test_triage_entity_risk_boost(self, triage_service, now):
        report = BaseReport(
            id="RPT-RISK",
            status=ReportStatus.UNVERIFIED.value,
            category="online_shop_fraud",
            description="The online shop never delivered my order.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            risk_level=RiskLevel.CRITICAL.value,
            audit=AuditMetadata(created_at=now),
        )
        result = triage_service.triage(report)
        # online_shop_fraud is MEDIUM, CRITICAL risk → boost
        assert result.priority == "HIGH"

    def test_triage_volume_spike(self, triage_service, now):
        """10+ reports for same category in 1 hour = URGENT."""
        # The report_store already has 2 phishing reports (RPT-001, RPT-003)
        # Add 8 more to trigger spike
        for i in range(8):
            triage_service._reports[f"RPT-SP{i:02d}"] = BaseReport(
                id=f"RPT-SP{i:02d}",
                status=ReportStatus.UNVERIFIED.value,
                category="phishing",
                description=f"Phishing report {i}.",
                reporter_id=f"citizen-{i}",
                related_entity_ids=["ENT-001"],
                audit=AuditMetadata(created_at=now),
            )
        spike_report = BaseReport(
            id="RPT-SPIKE",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Another phishing attempt detected today.",
            reporter_id="citizen-spike",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = triage_service.triage(spike_report)
        assert result.priority == "URGENT"

    def test_triage_event_published(self, triage_service, phishing_report, mock_event_bus):
        triage_service.triage(phishing_report)
        mock_event_bus.publish.assert_called_once()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "report.triaged"

    def test_triage_audit_logged(self, triage_service, phishing_report, mock_audit):
        triage_service.triage(phishing_report)
        mock_audit.log.assert_called_once()

    def test_triage_override_priority(self, triage_service, phishing_report):
        triage_service.triage(phishing_report)
        result = triage_service.override_priority(phishing_report.id, "URGENT", user_id="admin-001")
        assert result.priority == "URGENT"
        assert any("overridden" in n for n in result.notes)

    def test_triage_override_invalid_priority(self, triage_service, phishing_report):
        triage_service.triage(phishing_report)
        with pytest.raises(ValueError, match="Invalid priority"):
            triage_service.override_priority(phishing_report.id, "INVALID")

    def test_triage_override_nonexistent(self, triage_service):
        with pytest.raises(ValueError, match="No triage result"):
            triage_service.override_priority("NONEXISTENT", "HIGH")

    def test_triage_get_result(self, triage_service, phishing_report):
        triage_service.triage(phishing_report)
        result = triage_service.get_triage_result(phishing_report.id)
        assert result is not None
        assert result.report_id == phishing_report.id

    def test_triage_spam_repeat_same_reporter(self, triage_service, now):
        """Same reporter, same category within 24h = spam."""
        history = [
            BaseReport(
                id="RPT-PREV",
                status=ReportStatus.UNVERIFIED.value,
                category="phishing",
                description="Previous phishing report today.",
                reporter_id="citizen-001",
                related_entity_ids=["ENT-001"],
                audit=AuditMetadata(created_at=now - timedelta(hours=2)),
            )
        ]
        report = BaseReport(
            id="RPT-REPEAT",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Another phishing report same day.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = triage_service.triage(report, reporter_history=history)
        assert result.is_spam is True
        assert "repeated" in result.spam_reason.lower()


# ─── Enrichment Tests ───


class TestReportEnrichment:
    def test_enrich_links_entities(self, enrichment_service, phishing_report, entity_store):
        result = enrichment_service.enrich(phishing_report)
        assert "ENT-001" in result.linked_entity_ids

    def test_enrich_finds_related_reports(
        self, enrichment_service, phishing_report, corroborated_report
    ):
        result = enrichment_service.enrich(phishing_report)
        # RPT-003 (corroborated_report) shares ENT-001
        assert "RPT-003" in result.related_report_ids

    def test_enrich_finds_campaigns(self, enrichment_service, phishing_report):
        result = enrichment_service.enrich(phishing_report)
        # CAMP-001 matches by entity + fraud_type
        assert "CAMP-001" in result.related_campaign_ids

    def test_enrich_infrastructure_indicators(self, enrichment_service, phishing_report):
        result = enrichment_service.enrich(phishing_report)
        # ENT-001 has ip_addresses and asn in metadata
        assert len(result.infrastructure_indicators) >= 2

    def test_enrich_no_related(self, enrichment_service, now):
        report = BaseReport(
            id="RPT-ISOLATED",
            status=ReportStatus.UNVERIFIED.value,
            category="other",
            description="An isolated report with no related entities.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-NONEXISTENT"],
            audit=AuditMetadata(created_at=now),
        )
        result = enrichment_service.enrich(report)
        assert len(result.linked_entity_ids) == 0
        assert len(result.related_report_ids) == 0

    def test_enrich_event_published(self, enrichment_service, phishing_report, mock_event_bus):
        enrichment_service.enrich(phishing_report)
        mock_event_bus.publish.assert_called_once()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "report.enriched"

    def test_enrich_audit_logged(self, enrichment_service, phishing_report, mock_audit):
        enrichment_service.enrich(phishing_report)
        mock_audit.log.assert_called_once()

    def test_enrich_get_result(self, enrichment_service, phishing_report):
        enrichment_service.enrich(phishing_report)
        result = enrichment_service.get_enrichment(phishing_report.id)
        assert result is not None

    def test_enrich_campaign_by_fraud_type(self, enrichment_service, now):
        """Campaign linked by fraud_type match even without entity overlap."""
        report = BaseReport(
            id="RPT-FT",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Phishing report.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-DIFFERENT"],
            audit=AuditMetadata(created_at=now),
        )
        result = enrichment_service.enrich(report)
        # CAMP-001 has fraud_type="phishing"
        assert "CAMP-001" in result.related_campaign_ids


# ─── Scoring Tests ───


class TestReportScoring:
    def test_score_basic(self, scoring_service, phishing_report):
        result = scoring_service.score(phishing_report)
        assert 0 <= result.score <= 100
        assert result.risk_band in (
            RiskLevel.LOW.value,
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        )

    def test_score_has_breakdown(self, scoring_service, phishing_report):
        result = scoring_service.score(phishing_report)
        assert "report_count" in result.score_breakdown
        assert "corroborated_count" in result.score_breakdown
        assert "evidence_count" in result.score_breakdown
        assert "campaign_count" in result.score_breakdown
        assert "entity_risk" in result.score_breakdown

    def test_score_deterministic(self, scoring_service, phishing_report):
        """Same inputs should produce same score."""
        r1 = scoring_service.score(phishing_report)
        # Reset and rescore
        scoring_service._scores.clear()
        r2 = scoring_service.score(phishing_report)
        assert r1.score == r2.score

    def test_score_low_for_isolated_report(self, scoring_service, now):
        report = BaseReport(
            id="RPT-ISO",
            status=ReportStatus.UNVERIFIED.value,
            category="other",
            description="An isolated report.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-ISOLATED"],
            related_evidence_ids=[],
            risk_level=RiskLevel.UNKNOWN.value,
            audit=AuditMetadata(created_at=now),
        )
        result = scoring_service.score(report)
        assert result.score <= 20
        assert result.risk_band == RiskLevel.LOW.value

    def test_score_high_for_corroborated(self, scoring_service, corroborated_report):
        result = scoring_service.score(corroborated_report)
        # RPT-003 shares ENT-001 with RPT-001, and has 3 evidence + HIGH risk
        assert result.score > 20

    def test_score_with_enrichment(self, scoring_service, phishing_report):
        enrichment = EnrichmentResult(
            report_id=phishing_report.id,
            related_campaign_ids=["CAMP-001"],
        )
        result = scoring_service.score(phishing_report, enrichment=enrichment)
        # Campaign association adds to score
        assert result.score_breakdown["campaign_count"] > 0

    def test_score_stored_on_metadata(self, scoring_service, phishing_report):
        scoring_service.score(phishing_report)
        assert "risk_score" in phishing_report.metadata
        assert "risk_band" in phishing_report.metadata

    def test_score_max_100(self, scoring_service, now):
        """Score should never exceed 100."""
        report = BaseReport(
            id="RPT-MAX",
            status=ReportStatus.UNVERIFIED.value,
            category="identity_theft",
            description="Major identity theft incident.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            related_evidence_ids=[f"EV-{i:03d}" for i in range(20)],
            risk_level=RiskLevel.CRITICAL.value,
            audit=AuditMetadata(created_at=now),
        )
        result = scoring_service.score(report)
        assert result.score <= 100

    def test_score_bands(self, scoring_service, now):
        """Verify band boundaries with actual reports."""
        # LOW: isolated report, no signals
        low_report = BaseReport(
            id="RPT-LOW-BAND",
            status=ReportStatus.UNVERIFIED.value,
            category="other",
            description="An isolated report with no signals.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-ISOLATED"],
            related_evidence_ids=[],
            risk_level=RiskLevel.UNKNOWN.value,
            audit=AuditMetadata(created_at=now),
        )
        result = scoring_service.score(low_report)
        assert result.risk_band == RiskLevel.LOW.value
        assert result.score <= 20

    def test_score_batch(self, scoring_service, phishing_report, investment_report):
        results = scoring_service.batch_score([phishing_report, investment_report])
        assert len(results) == 2
        assert all(0 <= r.score <= 100 for r in results)

    def test_score_audit_logged(self, scoring_service, phishing_report, mock_audit):
        scoring_service.score(phishing_report)
        mock_audit.log.assert_called_once()

    def test_score_get_result(self, scoring_service, phishing_report):
        scoring_service.score(phishing_report)
        result = scoring_service.get_score(phishing_report.id)
        assert result is not None

    def test_report_count_weight(self, scoring_service, phishing_report):
        """Report count should contribute up to 25 points."""
        result = scoring_service.score(phishing_report)
        assert result.score_breakdown["report_count"] <= 25

    def test_corroborated_weight(self, scoring_service, phishing_report):
        result = scoring_service.score(phishing_report)
        assert result.score_breakdown["corroborated_count"] <= 30

    def test_evidence_weight(self, scoring_service, phishing_report):
        result = scoring_service.score(phishing_report)
        assert result.score_breakdown["evidence_count"] <= 20


# ─── Deduplication Tests ───


class TestReportDeduplication:
    def test_detect_exact_duplicate(self, dedup_service, phishing_report, duplicate_report):
        """Same entity, same category, same description = duplicate."""
        dedup_service._reports[phishing_report.id] = phishing_report
        result = dedup_service.check_duplicate(duplicate_report)
        assert result.is_duplicate is True
        assert result.original_report_id == "RPT-001"
        assert result.similarity_score >= 0.8

    def test_not_duplicate_different_entity(self, dedup_service, investment_report, now):
        report = BaseReport(
            id="RPT-DIFF",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Different phishing report for different entity.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-999"],
            audit=AuditMetadata(created_at=now),
        )
        result = dedup_service.check_duplicate(report)
        assert result.is_duplicate is False

    def test_not_duplicate_different_category(self, dedup_service, phishing_report, now):
        report = BaseReport(
            id="RPT-DIFFCAT",
            status=ReportStatus.UNVERIFIED.value,
            category="investment_fraud",
            description="I received a suspicious email claiming to be from my bank asking for credentials.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = dedup_service.check_duplicate(report)
        assert result.is_duplicate is False

    def test_duplicate_same_reporter_within_24h(self, dedup_service, phishing_report, now):
        """Same reporter, same entity, same category within 24h = duplicate."""
        report = BaseReport(
            id="RPT-SAME-RPT",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="A completely different description about phishing.",
            reporter_id=phishing_report.reporter_id,
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = dedup_service.check_duplicate(report)
        assert result.is_duplicate is True

    def test_duplicate_marks_status(self, dedup_service, phishing_report, duplicate_report):
        dedup_service._reports[phishing_report.id] = phishing_report
        dedup_service.check_duplicate(duplicate_report)
        assert duplicate_report.status == "DUPLICATE"

    def test_duplicate_event_published(
        self, dedup_service, phishing_report, duplicate_report, mock_event_bus
    ):
        dedup_service._reports[phishing_report.id] = phishing_report
        dedup_service.check_duplicate(duplicate_report)
        mock_event_bus.publish.assert_called_once()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "report.deduplicated"

    def test_no_duplicate_no_event(self, dedup_service, investment_report, mock_event_bus):
        dedup_service.check_duplicate(investment_report)
        mock_event_bus.publish.assert_not_called()

    def test_duplicate_audit_logged(
        self, dedup_service, phishing_report, duplicate_report, mock_audit
    ):
        dedup_service._reports[phishing_report.id] = phishing_report
        dedup_service.check_duplicate(duplicate_report)
        mock_audit.log.assert_called_once()

    def test_get_result(self, dedup_service, phishing_report):
        result = dedup_service.check_duplicate(phishing_report)
        assert dedup_service.get_result(phishing_report.id) is not None

    def test_similarity_threshold(self):
        """Verify threshold is 0.8."""
        assert ReportDeduplicationService.SIMILARITY_THRESHOLD == 0.8


# ─── Campaign Linking Tests ───


class TestCampaignLinking:
    def test_link_by_entity(self, campaign_service, phishing_report):
        result = campaign_service.link_to_campaigns(phishing_report)
        assert "CAMP-001" in result.linked_campaign_ids

    def test_link_by_fraud_type(self, campaign_service, now):
        report = BaseReport(
            id="RPT-FT-LINK",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Phishing report.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-DIFFERENT"],
            audit=AuditMetadata(created_at=now),
        )
        result = campaign_service.link_to_campaigns(report)
        # CAMP-001 has fraud_type="phishing"
        assert "CAMP-001" in result.linked_campaign_ids

    def test_no_link_for_non_matching(self, campaign_service, now):
        report = BaseReport(
            id="RPT-NOMATCH",
            status=ReportStatus.UNVERIFIED.value,
            category="romance_scam",
            description="Romance scam report.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-NOMATCH"],
            audit=AuditMetadata(created_at=now),
        )
        result = campaign_service.link_to_campaigns(report)
        assert len(result.linked_campaign_ids) == 0

    def test_dont_link_dismantled_campaign(self, campaign_service, now):
        """Dismantled campaigns should not be linked."""
        report = BaseReport(
            id="RPT-OLD",
            status=ReportStatus.UNVERIFIED.value,
            category="phishing",
            description="Old phishing.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-001"],
            audit=AuditMetadata(created_at=now),
        )
        result = campaign_service.link_to_campaigns(report)
        # CAMP-002 is DISMANTLED — should not be linked
        assert "CAMP-002" not in result.linked_campaign_ids

    def test_link_event_published(self, campaign_service, phishing_report, mock_event_bus):
        campaign_service.link_to_campaigns(phishing_report)
        mock_event_bus.publish.assert_called_once()
        assert mock_event_bus.publish.call_args.kwargs["topic"] == "report.campaign_linked"

    def test_no_link_no_event(self, campaign_service, now, mock_event_bus):
        report = BaseReport(
            id="RPT-NOLINK",
            status=ReportStatus.UNVERIFIED.value,
            category="romance_scam",
            description="Romance scam.",
            reporter_id="citizen-001",
            related_entity_ids=["ENT-NOMATCH"],
            audit=AuditMetadata(created_at=now),
        )
        campaign_service.link_to_campaigns(report)
        mock_event_bus.publish.assert_not_called()

    def test_link_audit_logged(self, campaign_service, phishing_report, mock_audit):
        campaign_service.link_to_campaigns(phishing_report)
        mock_audit.log.assert_called_once()

    def test_get_link_result(self, campaign_service, phishing_report):
        campaign_service.link_to_campaigns(phishing_report)
        result = campaign_service.get_link_result(phishing_report.id)
        assert result is not None


# ─── Integration Tests ───


class TestIntegrationPipeline:
    def test_full_pipeline(
        self,
        report_store,
        entity_store,
        campaign_store,
        mock_event_bus,
        mock_audit,
        phishing_report,
    ):
        """Full pipeline: triage → enrich → score → dedup → campaign link."""
        triage_svc = ReportTriageService(
            report_store=report_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )
        enrich_svc = ReportEnrichmentService(
            entity_store=entity_store,
            report_store=report_store,
            campaign_store=campaign_store,
            event_bus=mock_event_bus,
            audit_logger=mock_audit,
        )
        score_svc = ReportScoringService(report_store=report_store, audit_logger=mock_audit)
        dedup_svc = ReportDeduplicationService(
            report_store=report_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )
        campaign_svc = CampaignLinkingService(
            campaign_store=campaign_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )

        # 1. Triage
        triage = triage_svc.triage(phishing_report)
        assert triage.priority in ("LOW", "MEDIUM", "HIGH", "URGENT")

        # 2. Enrich
        enrichment = enrich_svc.enrich(phishing_report)
        assert len(enrichment.linked_entity_ids) > 0

        # 3. Score
        score_result = score_svc.score(phishing_report, enrichment=enrichment)
        assert 0 <= score_result.score <= 100

        # 4. Dedup check
        dedup_result = dedup_svc.check_duplicate(phishing_report)
        # phishing_report shares ENT-001 with RPT-003, but different description
        assert isinstance(dedup_result, DeduplicationResult)

        # 5. Campaign link
        link_result = campaign_svc.link_to_campaigns(phishing_report)
        assert "CAMP-001" in link_result.linked_campaign_ids

    def test_spam_short_circuits_pipeline(
        self,
        report_store,
        mock_event_bus,
        mock_audit,
        short_report,
    ):
        """Spam reports should be marked and not proceed to enrichment."""
        triage_svc = ReportTriageService(
            report_store=report_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )
        result = triage_svc.triage(short_report)
        assert result.is_spam is True
        assert short_report.status == "SPAM"

    def test_duplicate_detection_in_pipeline(
        self,
        report_store,
        entity_store,
        campaign_store,
        mock_event_bus,
        mock_audit,
        phishing_report,
        duplicate_report,
    ):
        """Duplicate report should be detected and marked."""
        triage_svc = ReportTriageService(
            report_store=report_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )
        dedup_svc = ReportDeduplicationService(
            report_store=report_store, event_bus=mock_event_bus, audit_logger=mock_audit
        )

        # Triang original
        triage_svc.triage(phishing_report)

        # Check duplicate
        dedup_result = dedup_svc.check_duplicate(duplicate_report)
        assert dedup_result.is_duplicate is True
        assert duplicate_report.status == "DUPLICATE"
