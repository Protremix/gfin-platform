"""GFIN Fraud Reporting Pipeline — Module 14.

Backend processing pipeline that takes citizen-submitted reports and prepares
them for analysis: triage, enrichment, scoring, deduplication, campaign linking.

Layer A: In-memory services with synthetic fixtures
Layer B: Kafka-streamed pipeline + Redis + PostgreSQL (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field

from schemas.base import BaseReport
from schemas.enums import ReportStatus, RiskLevel

# ─── Models ───

FRAUD_CATEGORIES: dict[str, dict[str, Any]] = {
    "phishing": {"priority": "HIGH", "weight": 80},
    "investment_fraud": {"priority": "HIGH", "weight": 85},
    "romance_scam": {"priority": "MEDIUM", "weight": 65},
    "advance_fee_fraud": {"priority": "HIGH", "weight": 75},
    "identity_theft": {"priority": "HIGH", "weight": 90},
    "crypto_fraud": {"priority": "HIGH", "weight": 85},
    "online_shop_fraud": {"priority": "MEDIUM", "weight": 55},
    "tech_support_scam": {"priority": "MEDIUM", "weight": 60},
    "social_media_impersonation": {"priority": "MEDIUM", "weight": 50},
    "phone_scam": {"priority": "MEDIUM", "weight": 55},
    "other": {"priority": "LOW", "weight": 30},
}


class TriageResult(BaseModel):
    """Result of triaging a report."""

    report_id: str
    priority: str = "LOW"  # LOW, MEDIUM, HIGH, URGENT
    is_spam: bool = False
    spam_reason: str = ""
    triaged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: list[str] = Field(default_factory=list)


class EnrichmentResult(BaseModel):
    """Result of enriching a report."""

    report_id: str
    linked_entity_ids: list[str] = Field(default_factory=list)
    related_report_ids: list[str] = Field(default_factory=list)
    related_campaign_ids: list[str] = Field(default_factory=list)
    infrastructure_indicators: list[dict[str, str]] = Field(default_factory=list)
    enriched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScoreResult(BaseModel):
    """Result of scoring a report."""

    report_id: str
    score: int = 0  # 0-100
    risk_band: str = RiskLevel.LOW.value
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    scored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeduplicationResult(BaseModel):
    """Result of deduplication check."""

    report_id: str
    is_duplicate: bool = False
    original_report_id: str | None = None
    duplicate_of_ids: list[str] = Field(default_factory=list)
    similarity_score: float = 0.0
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CampaignLinkResult(BaseModel):
    """Result of campaign linking."""

    report_id: str
    linked_campaign_ids: list[str] = Field(default_factory=list)
    linked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Report Triage Service ───


class ReportTriageService:
    """Automated triage of incoming fraud reports.

    Assigns priority, detects spam/junk, flags for review.
    """

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._reports = report_store or {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._triage_results: dict[str, TriageResult] = {}

    def triage(
        self,
        report: BaseReport,
        reporter_history: list[BaseReport] | None = None,
    ) -> TriageResult:
        """Triage a single report."""
        result = TriageResult(report_id=report.id)
        notes: list[str] = []

        # Spam detection
        spam = self._detect_spam(report, reporter_history or [])
        if spam:
            result.is_spam = True
            result.spam_reason = spam
            result.priority = "LOW"
            report.status = "SPAM"
            notes.append(f"Marked as spam: {spam}")
        else:
            # Priority assessment
            priority = self._assess_priority(report, reporter_history or [])
            result.priority = priority

            # Volume spike check
            spike = self._check_volume_spike(report)
            if spike:
                result.priority = "URGENT"
                notes.append("Volume spike detected for this entity")

            if not spike:
                notes.append(f"Priority: {priority} (category: {report.category})")

        self._triage_results[report.id] = result

        # Audit
        if self._audit:
            self._audit.log(
                user_id="system",
                action="report_triage",
                resource_type="report",
                resource_id=report.id,
                details={"priority": result.priority, "is_spam": result.is_spam},
            )

        # Event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="report.triaged",
                    event={
                        "report_id": report.id,
                        "priority": result.priority,
                        "is_spam": result.is_spam,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        result.notes = notes
        return result

    def get_triage_result(self, report_id: str) -> TriageResult | None:
        return self._triage_results.get(report_id)

    def override_priority(
        self,
        report_id: str,
        new_priority: str,
        user_id: str = "admin",
    ) -> TriageResult:
        """Admin override of triage priority."""
        result = self._triage_results.get(report_id)
        if not result:
            raise ValueError(f"No triage result for report {report_id}")

        if new_priority not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
            raise ValueError(f"Invalid priority: {new_priority}")

        old = result.priority
        result.priority = new_priority
        result.notes.append(f"Priority overridden by {user_id}: {old} → {new_priority}")

        if self._audit:
            self._audit.log(
                user_id=user_id,
                action="triage_priority_override",
                resource_type="report",
                resource_id=report_id,
                details={"old": old, "new": new_priority},
            )

        return result

    def _detect_spam(self, report: BaseReport, history: list[BaseReport]) -> str:
        """Detect spam/junk reports. Returns reason string or empty."""
        # Too short
        if len(report.description.strip()) < 10:
            return "Description too short (< 10 characters)"

        # Repeated submissions from same reporter for same entity within 24h
        now = datetime.now(UTC)
        report_time = report.audit.created_at if hasattr(report.audit, "created_at") else now
        for prev in history:
            if prev.reporter_id != report.reporter_id:
                continue
            if prev.id == report.id:
                continue
            prev_time = prev.audit.created_at if hasattr(prev.audit, "created_at") else now
            if (report_time - prev_time) < timedelta(hours=24):
                if prev.category == report.category:
                    return "Repeated submission for same category within 24h"

        # Gibberish detection — check if words lack vowels (not real words)
        words = report.description.split()
        vowels = set("aeiouAEIOU")
        real_words = [w for w in words if len(w) >= 3 and w.isalpha() and bool(set(w) & vowels)]
        if len(words) > 3 and len(real_words) == 0:
            return "Gibberish content (no recognizable words)"

        return ""

    def _assess_priority(self, report: BaseReport, history: list[BaseReport]) -> str:
        """Assess priority based on category, reporter credibility, entity risk."""
        cat_info = FRAUD_CATEGORIES.get(report.category, FRAUD_CATEGORIES["other"])
        priority = str(cat_info["priority"])

        # Reporter credibility — repeat reporters get a boost
        if report.reporter_id:
            reporter_reports = [r for r in history if r.reporter_id == report.reporter_id]
            if len(reporter_reports) >= 5:
                if priority == "LOW":
                    priority = "MEDIUM"
                elif priority == "MEDIUM":
                    priority = "HIGH"

        # Entity risk level boost
        if report.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
            if priority == "MEDIUM":
                priority = "HIGH"
            elif priority == "LOW":
                priority = "MEDIUM"

        return priority

    def _check_volume_spike(self, report: BaseReport) -> bool:
        """Check if there's a volume spike for reports of the same category."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=1)
        count = 0
        for r in self._reports.values():
            r_time = r.audit.created_at if hasattr(r.audit, "created_at") else now
            if r.category == report.category and r_time > cutoff:
                count += 1
        return count >= 10  # 10+ reports in 1 hour = spike


# ─── Report Enrichment Service ───


class ReportEnrichmentService:
    """Enrich reports with entity data, related reports, and infrastructure indicators."""

    def __init__(
        self,
        entity_store: dict[str, Any] | None = None,
        report_store: dict[str, BaseReport] | None = None,
        campaign_store: dict[str, Any] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._entities = entity_store or {}
        self._reports = report_store or {}
        self._campaigns = campaign_store or {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._enrichment_results: dict[str, EnrichmentResult] = {}

    def enrich(self, report: BaseReport) -> EnrichmentResult:
        """Enrich a report with related data."""
        result = EnrichmentResult(report_id=report.id)

        # Link entities referenced in report
        for eid in report.related_entity_ids:
            if eid in self._entities:
                result.linked_entity_ids.append(eid)

                # Get infrastructure indicators from entity
                entity = self._entities[eid]
                if hasattr(entity, "metadata") and isinstance(entity.metadata, dict):
                    for key in ("ip_addresses", "asn", "dns_records", "ssl_cert"):
                        if key in entity.metadata:
                            val = entity.metadata[key]
                            if isinstance(val, list):
                                for v in val:
                                    result.infrastructure_indicators.append(
                                        {"type": key, "value": str(v)}
                                    )
                            elif isinstance(val, str):
                                result.infrastructure_indicators.append({"type": key, "value": val})

        # Find related reports for same entities
        for other_id, other_report in self._reports.items():
            if other_id == report.id:
                continue
            shared = set(report.related_entity_ids) & set(other_report.related_entity_ids)
            if shared:
                result.related_report_ids.append(other_id)

        # Find related campaigns
        for camp_id, campaign in self._campaigns.items():
            campaign_entities = getattr(campaign, "related_entity_ids", [])
            if isinstance(campaign_entities, list):
                shared = set(report.related_entity_ids) & set(campaign_entities)
                if shared:
                    result.related_campaign_ids.append(camp_id)

            # Also check fraud_type match
            camp_ft = getattr(campaign, "fraud_type", "")
            if camp_ft and camp_ft == report.category:
                if camp_id not in result.related_campaign_ids:
                    result.related_campaign_ids.append(camp_id)

        self._enrichment_results[report.id] = result

        # Audit
        if self._audit:
            self._audit.log(
                user_id="system",
                action="report_enrich",
                resource_type="report",
                resource_id=report.id,
                details={
                    "linked_entities": len(result.linked_entity_ids),
                    "related_reports": len(result.related_report_ids),
                    "related_campaigns": len(result.related_campaign_ids),
                },
            )

        # Event
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="report.enriched",
                    event={
                        "report_id": report.id,
                        "linked_entity_count": len(result.linked_entity_ids),
                        "related_report_count": len(result.related_report_ids),
                        "related_campaign_count": len(result.related_campaign_ids),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return result

    def get_enrichment(self, report_id: str) -> EnrichmentResult | None:
        return self._enrichment_results.get(report_id)


# ─── Report Scoring Service ───


class ReportScoringService:
    """Composite risk scoring for reports.

    Score is deterministic for the same inputs.
    Score = weighted sum of: report count (25), corroborated (30),
    evidence (20), campaign (15), entity risk (10).
    """

    WEIGHTS = {
        "report_count": 25,
        "corroborated_count": 30,
        "evidence_count": 20,
        "campaign_count": 15,
        "entity_risk": 10,
    }

    RISK_WEIGHTS = {
        RiskLevel.UNKNOWN.value: 0,
        RiskLevel.LOW.value: 2,
        RiskLevel.MEDIUM.value: 5,
        RiskLevel.HIGH.value: 8,
        RiskLevel.CRITICAL.value: 10,
    }

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._reports = report_store or {}
        self._audit = audit_logger
        self._scores: dict[str, ScoreResult] = {}

    def score(
        self,
        report: BaseReport,
        enrichment: EnrichmentResult | None = None,
    ) -> ScoreResult:
        """Calculate composite risk score for a report."""
        breakdown: dict[str, float] = {}

        # 1. Report count for same entities (weight 25)
        entity_ids = set(report.related_entity_ids)
        report_count = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if set(r.related_entity_ids) & entity_ids:
                report_count += 1
        breakdown["report_count"] = min(report_count * 2.5, 25)

        # 2. Corroborated report count (weight 30)
        corroborated = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if set(r.related_entity_ids) & entity_ids:
                if r.status in (
                    ReportStatus.CORROBORATED.value,
                    ReportStatus.VERIFIED.value,
                    ReportStatus.OFFICIALLY_ESTABLISHED.value,
                ):
                    corroborated += 1
        breakdown["corroborated_count"] = min(corroborated * 6, 30)

        # 3. Evidence count (weight 20)
        evidence_count = len(report.related_evidence_ids)
        breakdown["evidence_count"] = min(evidence_count * 4, 20)

        # 4. Campaign association (weight 15)
        campaign_count = len(enrichment.related_campaign_ids) if enrichment else 0
        breakdown["campaign_count"] = min(campaign_count * 7.5, 15)

        # 5. Entity risk level (weight 10)
        risk_weight = self.RISK_WEIGHTS.get(report.risk_level, 0)
        breakdown["entity_risk"] = risk_weight

        # Total
        total = sum(breakdown.values())
        total = min(int(total), 100)

        # Band
        if total <= 20:
            band = RiskLevel.LOW.value
        elif total <= 50:
            band = RiskLevel.MEDIUM.value
        elif total <= 75:
            band = RiskLevel.HIGH.value
        else:
            band = RiskLevel.CRITICAL.value

        result = ScoreResult(
            report_id=report.id,
            score=total,
            risk_band=band,
            score_breakdown=breakdown,
        )
        self._scores[report.id] = result

        # Store score on report metadata
        if hasattr(report, "metadata") and isinstance(report.metadata, dict):
            report.metadata["risk_score"] = total
            report.metadata["risk_band"] = band

        # Audit
        if self._audit:
            self._audit.log(
                user_id="system",
                action="report_score",
                resource_type="report",
                resource_id=report.id,
                details={"score": total, "band": band},
            )

        return result

    def get_score(self, report_id: str) -> ScoreResult | None:
        return self._scores.get(report_id)

    def batch_score(
        self,
        reports: list[BaseReport],
        enrichments: dict[str, EnrichmentResult] | None = None,
    ) -> list[ScoreResult]:
        """Score multiple reports."""
        results = []
        for r in reports:
            enr = enrichments.get(r.id) if enrichments else None
            results.append(self.score(r, enr))
        return results


# ─── Report Deduplication Service ───


class ReportDeduplicationService:
    """Detect and mark duplicate reports."""

    SIMILARITY_THRESHOLD = 0.8

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._reports = report_store or {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._dedup_results: dict[str, DeduplicationResult] = {}

    def check_duplicate(self, report: BaseReport) -> DeduplicationResult:
        """Check if a report is a duplicate of an existing one."""
        result = DeduplicationResult(report_id=report.id)

        for other_id, other in self._reports.items():
            if other_id == report.id:
                continue

            # Same entity + same category
            shared_entities = set(report.related_entity_ids) & set(other.related_entity_ids)
            if not shared_entities:
                continue
            if report.category != other.category:
                continue

            # Same reporter + same entity within 24h
            if report.reporter_id and report.reporter_id == other.reporter_id:
                now = datetime.now(UTC)
                r_time = report.audit.created_at if hasattr(report.audit, "created_at") else now
                o_time = other.audit.created_at if hasattr(other.audit, "created_at") else now
                if abs((r_time - o_time).total_seconds()) < 86400:
                    result.is_duplicate = True
                    result.original_report_id = other_id
                    result.similarity_score = 1.0
                    break

            # Description similarity
            similarity = SequenceMatcher(
                None, report.description.lower(), other.description.lower()
            ).ratio()
            if similarity >= self.SIMILARITY_THRESHOLD:
                result.is_duplicate = True
                result.original_report_id = other_id
                result.similarity_score = similarity
                break

        if result.is_duplicate:
            report.status = "DUPLICATE"

            # Audit
            if self._audit:
                self._audit.log(
                    user_id="system",
                    action="report_deduplicated",
                    resource_type="report",
                    resource_id=report.id,
                    details={
                        "original": result.original_report_id,
                        "similarity": result.similarity_score,
                    },
                )

            # Event
            if self._event_bus:
                with contextlib.suppress(Exception):
                    self._event_bus.publish(
                        topic="report.deduplicated",
                        event={
                            "report_id": report.id,
                            "original_report_id": result.original_report_id,
                            "similarity": result.similarity_score,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )

        self._dedup_results[report.id] = result
        return result

    def get_result(self, report_id: str) -> DeduplicationResult | None:
        return self._dedup_results.get(report_id)


# ─── Campaign Linking Service ───


class CampaignLinkingService:
    """Link reports to active fraud campaigns."""

    def __init__(
        self,
        campaign_store: dict[str, Any] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._campaigns = campaign_store or {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._link_results: dict[str, CampaignLinkResult] = {}

    def link_to_campaigns(self, report: BaseReport) -> CampaignLinkResult:
        """Link a report to matching active campaigns."""
        result = CampaignLinkResult(report_id=report.id)

        for camp_id, campaign in self._campaigns.items():
            # Only link to active campaigns
            status = getattr(campaign, "campaign_status", "ACTIVE")
            if hasattr(status, "value"):
                status = status.value
            if status not in ("ACTIVE", "DORMANT"):
                continue

            # Check entity overlap
            camp_entities = getattr(campaign, "related_entity_ids", [])
            if isinstance(camp_entities, list) and camp_entities:
                shared = set(report.related_entity_ids) & set(camp_entities)
                if shared:
                    result.linked_campaign_ids.append(camp_id)
                    continue

            # Check fraud_type match
            camp_ft = getattr(campaign, "fraud_type", "")
            if camp_ft and camp_ft == report.category:
                result.linked_campaign_ids.append(camp_id)

        # Audit
        if self._audit and result.linked_campaign_ids:
            self._audit.log(
                user_id="system",
                action="report_campaign_link",
                resource_type="report",
                resource_id=report.id,
                details={"campaigns": result.linked_campaign_ids},
            )

        # Event
        if self._event_bus and result.linked_campaign_ids:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="report.campaign_linked",
                    event={
                        "report_id": report.id,
                        "campaign_ids": result.linked_campaign_ids,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        self._link_results[report.id] = result
        return result

    def get_link_result(self, report_id: str) -> CampaignLinkResult | None:
        return self._link_results.get(report_id)
