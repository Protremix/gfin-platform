"""GFIN Campaign Engine — Module 16.

Detects, creates, manages, and tracks fraud campaigns. A campaign is a set of
correlated entities, reports, and infrastructure indicators that together suggest
a coordinated fraud operation. Campaigns are probabilistic unless supported by
authoritative evidence (Constitution §22).

Layer A: In-memory services with synthetic fixtures
Layer B: Kafka-streamed pipeline + Neo4j graph clustering (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from schemas.base import AuditMetadata, BaseReport, Classification
from schemas.entities import CampaignEntity
from schemas.enums import DataClassification, RiskLevel

# ─── Models ───


class CampaignCandidate(BaseModel):
    """A candidate campaign detected from report/entity clustering."""

    name: str
    fraud_type: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    report_ids: list[str] = Field(default_factory=list)
    shared_infrastructure: list[dict[str, str]] = Field(default_factory=list)
    affected_countries: list[str] = Field(default_factory=list)
    detection_reason: str = ""
    confidence: float = 0.0


class CampaignScoreResult(BaseModel):
    """Result of scoring a campaign."""

    campaign_id: str
    score: int = 0
    severity: str = RiskLevel.LOW.value
    breakdown: dict[str, float] = Field(default_factory=dict)
    scored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Campaign Scorer ───


class CampaignScorer:
    """Scores campaign severity from linked entities and reports."""

    WEIGHTS = {
        "entity_count": 20,
        "report_count": 25,
        "corroborated_count": 30,
        "affected_countries": 15,
        "infrastructure_overlap": 10,
    }

    def __init__(self, report_store: dict[str, BaseReport] | None = None) -> None:
        self._reports = report_store if report_store is not None else {}
        self._scores: dict[str, CampaignScoreResult] = {}

    def score(
        self,
        campaign: CampaignEntity,
        report_ids: list[str] | None = None,
    ) -> CampaignScoreResult:
        """Calculate campaign severity score."""
        breakdown: dict[str, float] = {}

        # Entity count (weight 20) — max 5+ entities = full weight
        entity_count = len(campaign.related_entity_ids)
        breakdown["entity_count"] = min(entity_count * 4, 20)

        # Report count (weight 25)
        if report_ids is None:
            report_ids = self._find_reports_for_campaign(campaign)
        report_count = len(report_ids)
        breakdown["report_count"] = min(report_count * 2.5, 25)

        # Corroborated report count (weight 30)
        corroborated = 0
        for rid in report_ids:
            r = self._reports.get(rid)
            if r and getattr(r, "status", "") in (
                "CORROBORATED",
                "VERIFIED",
                "OFFICIALLY_ESTABLISHED",
            ):
                corroborated += 1
        breakdown["corroborated_count"] = min(corroborated * 6, 30)

        # Affected countries (weight 15)
        country_count = len(campaign.affected_countries)
        breakdown["affected_countries"] = min(country_count * 3, 15)

        # Infrastructure overlap (weight 10) — based on entity_count as proxy
        breakdown["infrastructure_overlap"] = min(entity_count * 2, 10)

        total = min(int(sum(breakdown.values())), 100)

        if total <= 25:
            severity = RiskLevel.LOW.value
        elif total <= 50:
            severity = RiskLevel.MEDIUM.value
        elif total <= 75:
            severity = RiskLevel.HIGH.value
        else:
            severity = RiskLevel.CRITICAL.value

        result = CampaignScoreResult(
            campaign_id=campaign.id,
            score=total,
            severity=severity,
            breakdown=breakdown,
        )
        self._scores[campaign.id] = result

        # Update campaign severity
        campaign.severity = severity

        return result

    def get_score(self, campaign_id: str) -> CampaignScoreResult | None:
        return self._scores.get(campaign_id)

    def _find_reports_for_campaign(self, campaign: CampaignEntity) -> list[str]:
        """Find reports linked to a campaign by entity overlap."""
        camp_entities = set(campaign.related_entity_ids)
        result = []
        for rid, report in self._reports.items():
            if set(getattr(report, "related_entity_ids", [])) & camp_entities:
                result.append(rid)
        return result


# ─── Campaign Detector ───


class CampaignDetector:
    """Detects new campaigns from clusters of reports and entities."""

    MIN_REPORTS_FOR_CAMPAIGN = 3
    MIN_ENTITIES_FOR_INFRA_CLUSTER = 2

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        entity_store: dict[str, Any] | None = None,
    ) -> None:
        self._reports = report_store if report_store is not None else {}
        self._entities = entity_store if entity_store is not None else {}

    def detect_from_reports(self, reports: list[BaseReport]) -> list[CampaignCandidate]:
        """Detect campaign-worthy clusters from a batch of reports."""
        candidates: list[CampaignCandidate] = []

        # Group by category + shared entities
        by_category: dict[str, list[BaseReport]] = {}
        for r in reports:
            cat = getattr(r, "category", "other")
            by_category.setdefault(cat, []).append(r)

        for category, cat_reports in by_category.items():
            # Find clusters by shared entity
            clusters = self._cluster_by_entity(cat_reports)
            for cluster in clusters:
                if len(cluster) >= self.MIN_REPORTS_FOR_CAMPAIGN:
                    entity_ids: set[str] = set()
                    report_ids = []
                    countries: set[str] = set()
                    for r in cluster:
                        entity_ids.update(getattr(r, "related_entity_ids", []))
                        report_ids.append(r.id)
                        c = getattr(r, "country", None)
                        if c:
                            countries.add(c)

                    candidates.append(
                        CampaignCandidate(
                            name=f"{category.replace('_', ' ').title()} Campaign",
                            fraud_type=category,
                            entity_ids=list(entity_ids),
                            report_ids=report_ids,
                            affected_countries=list(countries),
                            detection_reason=f"{len(cluster)} reports sharing entities, category={category}",
                            confidence=min(0.1 * len(cluster), 0.8),
                        )
                    )

        return candidates

    def detect_from_entities(self, entities: dict[str, Any]) -> list[CampaignCandidate]:
        """Detect campaigns from entities sharing infrastructure."""
        candidates: list[CampaignCandidate] = []

        # Group entities by shared infrastructure indicators
        by_infra: dict[str, list[str]] = {}  # indicator_value → entity_ids
        for eid, entity in entities.items():
            metadata = getattr(entity, "metadata", {})
            if not isinstance(metadata, dict):
                continue
            for key in ("ip_addresses", "asn", "ssl_cert_hash", "dns_records"):
                val = metadata.get(key)
                if isinstance(val, list):
                    for v in val:
                        indicator = f"{key}:{v}"
                        by_infra.setdefault(indicator, []).append(eid)
                elif isinstance(val, str):
                    indicator = f"{key}:{val}"
                    by_infra.setdefault(indicator, []).append(eid)

        for indicator, entity_ids in by_infra.items():
            unique_ids = list(set(entity_ids))
            if len(unique_ids) >= self.MIN_ENTITIES_FOR_INFRA_CLUSTER:
                key, value = indicator.split(":", 1)
                candidates.append(
                    CampaignCandidate(
                        name=f"Infrastructure Cluster ({key}={value})",
                        entity_ids=unique_ids,
                        shared_infrastructure=[{"type": key, "value": value}],
                        detection_reason=f"{len(unique_ids)} entities sharing {key}={value}",
                        confidence=min(0.15 * len(unique_ids), 0.8),
                    )
                )

        return candidates

    def _cluster_by_entity(self, reports: list[BaseReport]) -> list[list[BaseReport]]:
        """Cluster reports by shared entity IDs using union-find."""
        # Build entity → reports mapping
        entity_to_reports: dict[str, list[BaseReport]] = {}
        for r in reports:
            for eid in getattr(r, "related_entity_ids", []):
                entity_to_reports.setdefault(eid, []).append(r)

        # Union-find to merge reports sharing entities
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            if parent.get(x, x) == x:
                return x
            parent[x] = find(parent[x])
            return parent[x]

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for reports_sharing in entity_to_reports.values():
            if len(reports_sharing) > 1:
                first = reports_sharing[0].id
                for r in reports_sharing[1:]:
                    union(first, r.id)

        # Group by root
        clusters: dict[str, list[BaseReport]] = {}

        for r in reports:
            root = find(r.id)
            clusters.setdefault(root, []).append(r)

        return list(clusters.values())


# ─── Campaign Linker ───


class CampaignLinker:
    """Links reports and entities to existing campaigns."""

    def __init__(self, campaign_store: dict[str, CampaignEntity] | None = None) -> None:
        self._campaigns = campaign_store if campaign_store is not None else {}

    def link_report(self, report: BaseReport) -> list[str]:
        """Find matching campaigns for a report."""
        matched: list[str] = []
        report_entities = set(getattr(report, "related_entity_ids", []))
        report_category = getattr(report, "category", "")

        for camp_id, campaign in self._campaigns.items():
            # Only link to active/dormant campaigns
            status = campaign.campaign_status
            if status == "DISMANTLED":
                continue

            # Entity overlap
            camp_entities = set(campaign.related_entity_ids)
            if report_entities & camp_entities:
                if camp_id not in matched:
                    matched.append(camp_id)
                continue

            # Fraud type match
            if campaign.fraud_type and campaign.fraud_type == report_category:
                if camp_id not in matched:
                    matched.append(camp_id)

        return matched

    def link_entity(
        self, entity_id: str, entity_metadata: dict[str, Any] | None = None
    ) -> list[str]:
        """Find matching campaigns for an entity by infrastructure overlap."""
        matched: list[str] = []

        # Get entity infrastructure indicators
        entity_indicators: set[str] = set()
        if entity_metadata:
            for key in ("ip_addresses", "asn", "ssl_cert_hash", "dns_records"):
                val = entity_metadata.get(key)
                if isinstance(val, list):
                    for v in val:
                        entity_indicators.add(f"{key}:{v}")
                elif isinstance(val, str):
                    entity_indicators.add(f"{key}:{val}")

        for camp_id, campaign in self._campaigns.items():
            if campaign.campaign_status == "DISMANTLED":
                continue

            # Check if campaign entities share infrastructure
            # In Layer A, we check if entity_id is already in campaign
            if entity_id in campaign.related_entity_ids:
                matched.append(camp_id)
                continue

        return matched


# ─── Campaign Engine ───


class CampaignEngine:
    """Manages the full campaign lifecycle: create, update, detect, link, score."""

    DORMANT_THRESHOLD_DAYS = 30

    # Valid state transitions
    VALID_TRANSITIONS: dict[str, set[str]] = {
        "DRAFT": {"ACTIVE"},
        "ACTIVE": {"DORMANT", "DISMANTLED"},
        "DORMANT": {"ACTIVE", "DISMANTLED"},
        "DISMANTLED": set(),  # terminal state
    }

    def __init__(
        self,
        report_store: dict[str, BaseReport] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._reports = report_store if report_store is not None else {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._campaigns: dict[str, CampaignEntity] = {}
        self._campaign_reports: dict[str, list[str]] = {}  # campaign_id → report_ids
        self._scorer = CampaignScorer(report_store=self._reports)
        self._detector = CampaignDetector(report_store=self._reports)
        self._linker = CampaignLinker(campaign_store=self._campaigns)

    def create_campaign(
        self,
        name: str,
        fraud_type: str = "",
        entity_ids: list[str] | None = None,
        report_ids: list[str] | None = None,
        classification: Classification | None = None,
        created_by: str = "system",
    ) -> CampaignEntity:
        """Create a new campaign."""
        campaign = CampaignEntity(
            name=name,
            campaign_status="DRAFT",
            severity=RiskLevel.LOW.value,
            fraud_type=fraud_type,
            related_entity_ids=entity_ids or [],
            affected_countries=[],
            classification=classification
            or Classification(classification=DataClassification.RESTRICTED),
            audit=AuditMetadata(created_by=created_by),
        )
        campaign.entity_count = len(campaign.related_entity_ids)
        campaign.start_date = datetime.now(UTC)

        self._campaigns[campaign.id] = campaign
        self._campaign_reports[campaign.id] = report_ids or []

        self._audit_log(
            user_id=created_by,
            action="campaign_create",
            resource_id=campaign.id,
            details={"name": name, "fraud_type": fraud_type},
        )

        self._publish_event(
            "campaign.created",
            {
                "campaign_id": campaign.id,
                "name": name,
                "fraud_type": fraud_type,
            },
        )

        return campaign

    def update_campaign(
        self,
        campaign_id: str,
        updates: dict[str, Any],
        updated_by: str = "system",
    ) -> CampaignEntity:
        """Update campaign properties."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        for key, value in updates.items():
            if key in ("name", "fraud_type", "affected_countries", "severity"):
                setattr(campaign, key, value)
            elif key == "start_date" and isinstance(value, str):
                campaign.start_date = datetime.fromisoformat(value)
            elif key == "end_date" and isinstance(value, str):
                campaign.end_date = datetime.fromisoformat(value)

        self._audit_log(
            user_id=updated_by,
            action="campaign_update",
            resource_id=campaign_id,
            details=updates,
        )

        self._publish_event(
            "campaign.updated",
            {
                "campaign_id": campaign_id,
                "updates": list(updates.keys()),
            },
        )

        return campaign

    def transition_status(
        self,
        campaign_id: str,
        new_status: str,
        user_id: str = "system",
    ) -> CampaignEntity:
        """Transition campaign status following the state machine."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        current = campaign.campaign_status
        valid_targets = self.VALID_TRANSITIONS.get(current, set())

        if new_status not in valid_targets:
            raise ValueError(
                f"Invalid transition: {current} → {new_status}. "
                f"Valid transitions from {current}: {valid_targets}"
            )

        campaign.campaign_status = new_status

        if new_status == "DISMANTLED":
            campaign.end_date = datetime.now(UTC)

        self._audit_log(
            user_id=user_id,
            action="campaign_status_change",
            resource_id=campaign_id,
            details={"old": current, "new": new_status},
        )

        event_topic = "campaign.dismantled" if new_status == "DISMANTLED" else "campaign.updated"
        self._publish_event(
            event_topic,
            {
                "campaign_id": campaign_id,
                "old_status": current,
                "new_status": new_status,
            },
        )

        return campaign

    def dismantle_campaign(self, campaign_id: str, user_id: str = "admin") -> CampaignEntity:
        """Mark a campaign as DISMANTLED."""
        return self.transition_status(campaign_id, "DISMANTLED", user_id)

    def reactivate_campaign(self, campaign_id: str, user_id: str = "admin") -> CampaignEntity:
        """Reactivate a DORMANT campaign."""
        return self.transition_status(campaign_id, "ACTIVE", user_id)

    def activate_campaign(self, campaign_id: str, user_id: str = "admin") -> CampaignEntity:
        """Activate a DRAFT campaign."""
        return self.transition_status(campaign_id, "ACTIVE", user_id)

    def link_entity(
        self,
        campaign_id: str,
        entity_id: str,
        user_id: str = "system",
    ) -> CampaignEntity:
        """Link an entity to a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if entity_id not in campaign.related_entity_ids:
            campaign.related_entity_ids.append(entity_id)
            campaign.entity_count = len(campaign.related_entity_ids)

            self._audit_log(
                user_id=user_id,
                action="campaign_link_entity",
                resource_id=campaign_id,
                details={"entity_id": entity_id},
            )

        return campaign

    def unlink_entity(
        self,
        campaign_id: str,
        entity_id: str,
        user_id: str = "system",
    ) -> CampaignEntity:
        """Remove an entity from a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if entity_id in campaign.related_entity_ids:
            campaign.related_entity_ids.remove(entity_id)
            campaign.entity_count = len(campaign.related_entity_ids)

            self._audit_log(
                user_id=user_id,
                action="campaign_unlink_entity",
                resource_id=campaign_id,
                details={"entity_id": entity_id},
            )

        return campaign

    def link_report(
        self,
        campaign_id: str,
        report_id: str,
        user_id: str = "system",
    ) -> None:
        """Link a report to a campaign."""
        if campaign_id not in self._campaigns:
            raise ValueError(f"Campaign {campaign_id} not found")

        if report_id not in self._campaign_reports.get(campaign_id, []):
            self._campaign_reports.setdefault(campaign_id, []).append(report_id)

            self._audit_log(
                user_id=user_id,
                action="campaign_link_report",
                resource_id=campaign_id,
                details={"report_id": report_id},
            )

    def get_campaign(self, campaign_id: str) -> CampaignEntity | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self, status: str | None = None) -> list[CampaignEntity]:
        """List campaigns, optionally filtered by status."""
        if status:
            return [c for c in self._campaigns.values() if c.campaign_status == status]
        return list(self._campaigns.values())

    def get_campaign_reports(self, campaign_id: str) -> list[str]:
        return self._campaign_reports.get(campaign_id, [])

    def score_campaign(self, campaign_id: str) -> CampaignScoreResult:
        """Score a campaign's severity."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        report_ids = self._campaign_reports.get(campaign_id, [])
        return self._scorer.score(campaign, report_ids)

    def detect_campaigns(self, reports: list[BaseReport] | None = None) -> list[CampaignCandidate]:
        """Detect new campaign candidates from reports."""
        if reports is None:
            reports = list(self._reports.values())
        return self._detector.detect_from_reports(reports)

    def detect_and_create(self, reports: list[BaseReport] | None = None) -> list[CampaignEntity]:
        """Detect campaigns and automatically create them."""
        candidates = self.detect_campaigns(reports)
        created: list[CampaignEntity] = []
        for candidate in candidates:
            campaign = self.create_campaign(
                name=candidate.name,
                fraud_type=candidate.fraud_type,
                entity_ids=candidate.entity_ids,
                report_ids=candidate.report_ids,
            )
            created.append(campaign)
        return created

    def link_report_to_campaigns(self, report: BaseReport) -> list[str]:
        """Find and link a report to matching campaigns."""
        matched = self._linker.link_report(report)
        for camp_id in matched:
            self.link_report(camp_id, report.id)
        return matched

    def check_dormant(self, now: datetime | None = None) -> list[str]:
        """Mark campaigns as DORMANT if no new activity in threshold days."""
        if now is None:
            now = datetime.now(UTC)
        dormant_ids: list[str] = []
        cutoff = now - timedelta(days=self.DORMANT_THRESHOLD_DAYS)

        for camp_id, campaign in self._campaigns.items():
            if campaign.campaign_status != "ACTIVE":
                continue
            last_activity = (
                campaign.audit.created_at if hasattr(campaign.audit, "created_at") else now
            )
            if last_activity < cutoff:
                campaign.campaign_status = "DORMANT"
                dormant_ids.append(camp_id)

                self._audit_log(
                    user_id="system",
                    action="campaign_auto_dormant",
                    resource_id=camp_id,
                    details={"last_activity": last_activity.isoformat()},
                )

        return dormant_ids

    def _audit_log(
        self, user_id: str, action: str, resource_id: str, details: dict[str, Any]
    ) -> None:
        if self._audit:
            self._audit.log(
                user_id=user_id,
                action=action,
                resource_type="campaign",
                resource_id=resource_id,
                details=details,
            )

    def _publish_event(self, topic: str, event: dict[str, Any]) -> None:
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic=topic,
                    event={**event, "timestamp": datetime.now(UTC).isoformat()},
                )
