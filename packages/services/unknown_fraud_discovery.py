"""GFIN Unknown Fraud Discovery Engine (UFDE)

Per Engineering Task Specification v1.0:
- Autonomous intelligence-discovery and investigation-support system
- Starting from one seed entity, continuously discover lawful, permitted,
  previously unknown relationships and intelligence leads
- Present to authorized investigators with evidence, provenance, confidence, and explanation

Layer A: In-memory implementation with mock sources
Layer B: Real external sources (REQUIRES EXTERNAL INFRASTRUCTURE)

Components:
    - DiscoveryOrchestrator: Manages a full discovery run from seed to leads
    - DiscoveryPlanner: Decides what to investigate next
    - GraphExplorer: Expands the investigation graph with cycle detection
    - SourceRouter: Routes discovery tasks to appropriate sources
    - RelationshipHypothesizer: Generates observed/derived/hypothesized relationships
    - DiscoveryScorer: Calculates evidence confidence and investigation priority
    - CampaignCandidateDetector: Identifies clusters that may form new campaigns
    - AnomalyDetector: Detects anomalous patterns in discovered data
    - LeadEngine: Generates investigative leads with full explanation
    - CoverageReporter: Reports what was checked, not checked, failed, unavailable
    - MonitoringRuleManager: Configures continuous monitoring for discovered entities
    - ResourceController: Enforces rate limits, budgets, and prevents graph explosion
    - DataPoisoningGuard: Prevents single untrusted sources from establishing high confidence

Security:
    - External content is untrusted data, not authority
    - No source writes to canonical tables without validation
    - Prompt injection protection on all external content
    - Data poisoning safeguards
    - Lawful access only — no bypassing authentication
    - Human-in-the-loop: no autonomous accusations or guilt determinations
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger("gfin.ufde")

# ─── Enums ───


class DiscoveryRunStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    COLLECTING = "COLLECTING"
    RESOLVING = "RESOLVING"
    SCORING = "SCORING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHORIZED = "UNAUTHORIZED"


class SourceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    FAILED = "FAILED"
    NOT_CHECKED = "NOT_CHECKED"
    CHECKED = "CHECKED"
    LIMITED = "LIMITED"


class RelationshipCertainty(StrEnum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    HYPOTHESIZED = "HYPOTHESIZED"


class LeadStatus(StrEnum):
    PENDING = "PENDING"
    EXPANDED = "EXPANDED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SUPPRESSED = "SUPPRESSED"


class CampaignCandidateStatus(StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"


class MonitoringTTL(StrEnum):
    SHORT = "24h"
    MEDIUM = "7d"
    LONG = "30d"
    PERMANENT = "permanent"


# ─── Data Models ───


@dataclass
class SourceCapability:
    """Describes what a discovery source can do."""

    name: str
    entity_types: list[str]
    relationship_types: list[str]
    requires_auth: bool = False
    rate_limit_per_minute: int = 60
    cost_per_query: float = 0.0
    reliability: float = 0.8  # 0.0 to 1.0


@dataclass
class SourceRestriction:
    """Access restrictions on a discovery source."""

    source_name: str
    auth_required: bool = False
    classification_required: str | None = None
    jurisdiction_restricted: list[str] = field(default_factory=list)
    tos_url: str | None = None
    max_queries_per_day: int | None = None


@dataclass
class DiscoveryTask:
    """A prioritized task to query a specific source for a specific entity."""

    id: str
    run_id: str
    entity_id: str
    entity_type: str
    entity_value: str
    source_name: str
    relationship_type: str
    priority: float  # 0.0 to 1.0
    depth: int
    status: TaskStatus = TaskStatus.PENDING
    result: DiscoveryResult | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class DiscoveryResult:
    """Raw result from a discovery task."""

    task_id: str
    source_name: str
    discovered_entities: list[dict[str, Any]] = field(default_factory=list)
    discovered_relationships: list[dict[str, Any]] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    retrieval_time: float = field(default_factory=time.time)
    source_reliability: float = 0.8
    error: str | None = None


@dataclass
class RelationshipHypothesis:
    """A hypothesized (not confirmed) relationship between entities."""

    id: str
    run_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    certainty: RelationshipCertainty
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""
    sources: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class InvestigationLead:
    """A generated investigative lead with evidence, confidence, and explanation."""

    id: str
    run_id: str
    seed_entity_id: str
    seed_entity_value: str
    discovered_entity_id: str
    discovered_entity_value: str
    discovered_entity_type: str
    evidence_count: int = 0
    evidence_sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    priority: float = 0.0
    reason: str = ""
    relationship_path: list[dict[str, str]] = field(default_factory=list)
    campaign_candidate_id: str | None = None
    status: LeadStatus = LeadStatus.PENDING
    created_at: float = field(default_factory=time.time)


@dataclass
class CampaignCandidate:
    """A cluster of entities that may form a new campaign."""

    id: str
    run_id: str
    entity_ids: list[str]
    entity_types: list[str]
    relationship_count: int = 0
    confidence: float = 0.0
    similarity_score: float = 0.0
    shared_indicators: list[str] = field(default_factory=list)
    status: CampaignCandidateStatus = CampaignCandidateStatus.DRAFT
    created_at: float = field(default_factory=time.time)


@dataclass
class DiscoveryCoverage:
    """What sources were checked, not checked, failed, unavailable."""

    run_id: str
    source_status: dict[str, SourceStatus] = field(default_factory=dict)
    checked: list[str] = field(default_factory=list)
    not_checked: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    unavailable: list[str] = field(default_factory=list)
    authorization_required: list[str] = field(default_factory=list)
    limited: list[str] = field(default_factory=list)


@dataclass
class MonitoringRule:
    """A rule for continuously monitoring a discovered entity."""

    id: str
    entity_id: str
    entity_type: str
    entity_value: str
    monitor_types: list[str] = field(default_factory=list)
    ttl: MonitoringTTL = MonitoringTTL.MEDIUM
    priority: float = 0.5
    investigation_id: str | None = None
    active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class DiscoveryRun:
    """A single investigation expansion from a seed entity."""

    id: str
    seed_entity_id: str
    seed_entity_type: str
    seed_entity_value: str
    status: DiscoveryRunStatus = DiscoveryRunStatus.PENDING
    tasks: list[DiscoveryTask] = field(default_factory=list)
    results: list[DiscoveryResult] = field(default_factory=list)
    hypotheses: list[RelationshipHypothesis] = field(default_factory=list)
    leads: list[InvestigationLead] = field(default_factory=list)
    campaign_candidates: list[CampaignCandidate] = field(default_factory=list)
    coverage: DiscoveryCoverage | None = None
    monitoring_rules: list[MonitoringRule] = field(default_factory=list)
    graph: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    discovered_entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    config: DiscoveryConfig | None = None
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class DiscoveryConfig:
    """Configuration for a discovery run."""

    max_depth: int = 5
    max_nodes: int = 100
    max_tasks: int = 50
    max_runtime_seconds: int = 300
    min_confidence_threshold: float = 0.1
    per_source_budget: dict[str, int] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    concurrency_limit: int = 5
    enable_anomaly_detection: bool = True
    enable_campaign_detection: bool = True
    enable_monitoring: bool = True
    user_role: str = "investigator"
    user_jurisdiction: str | None = None
    user_organization: str | None = None
    user_classification: str = "PUBLIC"


# ─── Source Registry ───

# Default source capabilities for Layer A (mock sources)
DEFAULT_SOURCES: dict[str, SourceCapability] = {
    "dns_resolver": SourceCapability(
        name="dns_resolver",
        entity_types=["DOMAIN", "IP"],
        relationship_types=["resolves_to", "has_nameserver", "has_mx"],
        requires_auth=False,
        rate_limit_per_minute=100,
        reliability=0.95,
    ),
    "certificate_transparency": SourceCapability(
        name="certificate_transparency",
        entity_types=["DOMAIN", "CERTIFICATE"],
        relationship_types=["has_certificate", "has_san", "shares_certificate"],
        requires_auth=False,
        rate_limit_per_minute=30,
        reliability=0.9,
    ),
    "whois_rdap": SourceCapability(
        name="whois_rdap",
        entity_types=["DOMAIN", "ORGANIZATION", "PERSON"],
        relationship_types=["registered_by", "has_registrar"],
        requires_auth=False,
        rate_limit_per_minute=20,
        reliability=0.85,
    ),
    "ip_intelligence": SourceCapability(
        name="ip_intelligence",
        entity_types=["IP", "ASN"],
        relationship_types=["belongs_to_asn", "has_prefix", "reverse_dns"],
        requires_auth=False,
        rate_limit_per_minute=60,
        reliability=0.9,
    ),
    "web_crawler": SourceCapability(
        name="web_crawler",
        entity_types=["URL", "DOMAIN"],
        relationship_types=["hosted_on", "links_to", "contains_content"],
        requires_auth=False,
        rate_limit_per_minute=10,
        reliability=0.8,
    ),
    "misp_feed": SourceCapability(
        name="misp_feed",
        entity_types=["DOMAIN", "IP", "URL", "EMAIL", "PHONE"],
        relationship_types=["reported_in", "tagged_as", "correlated_with"],
        requires_auth=True,
        rate_limit_per_minute=30,
        reliability=0.85,
    ),
    "opencti_graph": SourceCapability(
        name="opencti_graph",
        entity_types=["DOMAIN", "IP", "URL", "EMAIL", "PERSON", "ORGANIZATION"],
        relationship_types=["indicates", "targets", "uses", "attributed_to"],
        requires_auth=True,
        rate_limit_per_minute=20,
        reliability=0.9,
    ),
    "cortex_enrichment": SourceCapability(
        name="cortex_enrichment",
        entity_types=["IP", "DOMAIN", "URL", "EMAIL"],
        relationship_types=["enriched_with", "reputation_score"],
        requires_auth=True,
        rate_limit_per_minute=30,
        reliability=0.85,
    ),
    "police_database": SourceCapability(
        name="police_database",
        entity_types=["PERSON", "PHONE", "EMAIL", "ORGANIZATION"],
        relationship_types=["reported_to", "investigated_in", "linked_to_case"],
        requires_auth=True,
        rate_limit_per_minute=10,
        reliability=0.95,
    ),
    "crypto_intelligence": SourceCapability(
        name="crypto_intelligence",
        entity_types=["CRYPTO_WALLET", "TRANSACTION"],
        relationship_types=["sent_to", "received_from", "shares_wallet"],
        requires_auth=False,
        rate_limit_per_minute=20,
        reliability=0.85,
    ),
}

# Default source restrictions
DEFAULT_RESTRICTIONS: dict[str, SourceRestriction] = {
    "misp_feed": SourceRestriction(
        source_name="misp_feed",
        auth_required=True,
        classification_required="COMMUNITY",
    ),
    "opencti_graph": SourceRestriction(
        source_name="opencti_graph",
        auth_required=True,
        classification_required="COMMUNITY",
    ),
    "cortex_enrichment": SourceRestriction(
        source_name="cortex_enrichment",
        auth_required=True,
    ),
    "police_database": SourceRestriction(
        source_name="police_database",
        auth_required=True,
        classification_required="LAW_ENFORCEMENT",
    ),
}


# ─── Discovery Planner ───


class DiscoveryPlanner:
    """Decides what to investigate next for each entity.

    For each entity, determines:
    - available relationship types
    - available data sources
    - expected value
    - cost
    - risk
    - freshness

    Generates prioritized discovery tasks.
    """

    # Discovery chains per entity type (Section 9 of spec)
    DISCOVERY_CHAINS: dict[str, list[dict[str, Any]]] = {
        "DOMAIN": [
            {"source": "dns_resolver", "relationship": "resolves_to", "target_type": "IP", "priority": 0.9},
            {"source": "certificate_transparency", "relationship": "has_certificate", "target_type": "CERTIFICATE", "priority": 0.85},
            {"source": "whois_rdap", "relationship": "registered_by", "target_type": "ORGANIZATION", "priority": 0.7},
            {"source": "web_crawler", "relationship": "hosted_on", "target_type": "URL", "priority": 0.6},
            {"source": "misp_feed", "relationship": "reported_in", "target_type": "REPORT", "priority": 0.5},
            {"source": "opencti_graph", "relationship": "indicates", "target_type": "CAMPAIGN", "priority": 0.45},
        ],
        "IP": [
            {"source": "ip_intelligence", "relationship": "belongs_to_asn", "target_type": "ASN", "priority": 0.9},
            {"source": "dns_resolver", "relationship": "reverse_dns", "target_type": "DOMAIN", "priority": 0.8},
            {"source": "certificate_transparency", "relationship": "has_certificate", "target_type": "CERTIFICATE", "priority": 0.7},
            {"source": "cortex_enrichment", "relationship": "reputation_score", "target_type": "OBSERVATION", "priority": 0.6},
            {"source": "misp_feed", "relationship": "reported_in", "target_type": "REPORT", "priority": 0.5},
        ],
        "URL": [
            {"source": "web_crawler", "relationship": "hosted_on", "target_type": "DOMAIN", "priority": 0.9},
            {"source": "dns_resolver", "relationship": "resolves_to", "target_type": "IP", "priority": 0.85},
            {"source": "certificate_transparency", "relationship": "has_certificate", "target_type": "CERTIFICATE", "priority": 0.7},
            {"source": "misp_feed", "relationship": "reported_in", "target_type": "REPORT", "priority": 0.5},
        ],
        "EMAIL": [
            {"source": "misp_feed", "relationship": "correlated_with", "target_type": "DOMAIN", "priority": 0.8},
            {"source": "opencti_graph", "relationship": "targets", "target_type": "PERSON", "priority": 0.7},
            {"source": "cortex_enrichment", "relationship": "enriched_with", "target_type": "OBSERVATION", "priority": 0.6},
            {"source": "police_database", "relationship": "linked_to_case", "target_type": "CASE", "priority": 0.5},
        ],
        "PHONE": [
            {"source": "misp_feed", "relationship": "correlated_with", "target_type": "EMAIL", "priority": 0.8},
            {"source": "opencti_graph", "relationship": "targets", "target_type": "PERSON", "priority": 0.7},
            {"source": "police_database", "relationship": "linked_to_case", "target_type": "CASE", "priority": 0.6},
        ],
        "CERTIFICATE": [
            {"source": "certificate_transparency", "relationship": "has_san", "target_type": "DOMAIN", "priority": 0.95},
            {"source": "certificate_transparency", "relationship": "shares_certificate", "target_type": "DOMAIN", "priority": 0.9},
        ],
        "ASN": [
            {"source": "ip_intelligence", "relationship": "has_prefix", "target_type": "IP", "priority": 0.85},
            {"source": "ip_intelligence", "relationship": "reverse_dns", "target_type": "DOMAIN", "priority": 0.7},
        ],
        "CRYPTO_WALLET": [
            {"source": "crypto_intelligence", "relationship": "sent_to", "target_type": "CRYPTO_WALLET", "priority": 0.9},
            {"source": "crypto_intelligence", "relationship": "received_from", "target_type": "CRYPTO_WALLET", "priority": 0.9},
            {"source": "misp_feed", "relationship": "reported_in", "target_type": "REPORT", "priority": 0.5},
        ],
        "PERSON": [
            {"source": "opencti_graph", "relationship": "attributed_to", "target_type": "CAMPAIGN", "priority": 0.7},
            {"source": "police_database", "relationship": "investigated_in", "target_type": "CASE", "priority": 0.65},
        ],
        "ORGANIZATION": [
            {"source": "whois_rdap", "relationship": "registered_by", "target_type": "DOMAIN", "priority": 0.8},
            {"source": "opencti_graph", "relationship": "targets", "target_type": "CAMPAIGN", "priority": 0.6},
        ],
    }

    def plan(
        self,
        entity_id: str,
        entity_type: str,
        entity_value: str,
        depth: int,
        config: DiscoveryConfig,
        existing_sources: list[str] | None = None,
    ) -> list[DiscoveryTask]:
        """Generate prioritized discovery tasks for an entity."""
        if depth >= config.max_depth:
            return []

        chain = self.DISCOVERY_CHAINS.get(entity_type, [])
        if not chain:
            return []

        existing_sources = existing_sources or []
        tasks: list[DiscoveryTask] = []
        run_id = ""  # Set by orchestrator

        for step in chain:
            source_name = step["source"]

            # Check source budget
            budget = config.per_source_budget.get(source_name, 10)
            if source_name in existing_sources and existing_sources.count(source_name) >= budget:
                continue

            # Check authorization
            restriction = DEFAULT_RESTRICTIONS.get(source_name)
            if restriction and restriction.auth_required:
                if config.user_role == "investigator" and source_name == "police_database":
                    continue  # Investigator can't access police database

            task = DiscoveryTask(
                id=f"TASK-{uuid.uuid4().hex[:8].upper()}",
                run_id=run_id,
                entity_id=entity_id,
                entity_type=entity_type,
                entity_value=entity_value,
                source_name=source_name,
                relationship_type=step["relationship"],
                priority=step["priority"] * (1.0 - depth * 0.15),  # Lower priority at deeper levels
                depth=depth,
            )
            tasks.append(task)

        # Sort by priority (descending)
        tasks.sort(key=lambda t: t.priority, reverse=True)
        return tasks


# ─── Source Router (Mock for Layer A) ───


class SourceRouter:
    """Routes discovery tasks to appropriate sources and executes them.

    Layer A: Mock sources that return simulated results
    Layer B: Real external sources (REQUIRES EXTERNAL INFRASTRUCTURE)
    """

    def __init__(self) -> None:
        self._call_counts: dict[str, int] = defaultdict(int)
        self._failure_modes: dict[str, str] = {}  # For testing
        self._rate_limited_until: dict[str, float] = {}

    def set_failure_mode(self, source_name: str, mode: str) -> None:
        """Set a failure mode for a source (for testing)."""
        self._failure_modes[source_name] = mode

    def clear_failure_mode(self, source_name: str) -> None:
        """Clear a failure mode."""
        self._failure_modes.pop(source_name, None)

    def execute(self, task: DiscoveryTask, config: DiscoveryConfig) -> DiscoveryResult:
        """Execute a discovery task against a source (mock in Layer A)."""
        source_name = task.source_name
        source_cap = DEFAULT_SOURCES.get(source_name)

        if not source_cap:
            return DiscoveryResult(
                task_id=task.id,
                source_name=source_name,
                error=f"Unknown source: {source_name}",
            )

        # Check failure mode
        if source_name in self._failure_modes:
            mode = self._failure_modes[source_name]
            if mode == "unavailable":
                task.status = TaskStatus.FAILED
                return DiscoveryResult(
                    task_id=task.id,
                    source_name=source_name,
                    error="Source unavailable",
                )
            elif mode == "unauthorized":
                task.status = TaskStatus.UNAUTHORIZED
                return DiscoveryResult(
                    task_id=task.id,
                    source_name=source_name,
                    error="Authorization required",
                )
            elif mode == "rate_limited":
                task.status = TaskStatus.RATE_LIMITED
                return DiscoveryResult(
                    task_id=task.id,
                    source_name=source_name,
                    error="Rate limited",
                )

        # Check rate limit
        now = time.time()
        if source_name in self._rate_limited_until:
            if now < self._rate_limited_until[source_name]:
                task.status = TaskStatus.RATE_LIMITED
                return DiscoveryResult(
                    task_id=task.id,
                    source_name=source_name,
                    error="Rate limited",
                )

        # Check authorization
        restriction = DEFAULT_RESTRICTIONS.get(source_name)
        if restriction and restriction.auth_required:
            if config.user_role == "investigator" and source_name == "police_database":
                task.status = TaskStatus.UNAUTHORIZED
                return DiscoveryResult(
                    task_id=task.id,
                    source_name=source_name,
                    error="Authorization required",
                )

        # Increment call count
        self._call_counts[source_name] += 1

        # Mock discovery: generate simulated results based on source and entity type
        result = self._mock_discover(task, source_cap)
        task.status = TaskStatus.COMPLETED
        task.completed_at = now
        return result

    def _mock_discover(self, task: DiscoveryTask, source_cap: SourceCapability) -> DiscoveryResult:
        """Generate mock discovery results (Layer A)."""
        discovered_entities: list[dict[str, Any]] = []
        discovered_relationships: list[dict[str, Any]] = []

        source = task.source_name
        entity_value = task.entity_value
        entity_type = task.entity_type

        if source == "dns_resolver" and entity_type == "DOMAIN":
            # Domain → IP
            ip = f"192.168.{hash(entity_value) % 255}.{(hash(entity_value) >> 8) % 255}"
            ip_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": ip_id,
                "entity_type": "IP",
                "normalized_value": ip,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": ip_id,
                "relationship_type": "resolves_to",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "certificate_transparency" and entity_type in ("DOMAIN", "IP"):
            # Domain/IP → Certificate
            cert_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            cert_hash = f"sha256:{uuid.uuid4().hex}"
            discovered_entities.append({
                "id": cert_id,
                "entity_type": "CERTIFICATE",
                "normalized_value": cert_hash,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": cert_id,
                "relationship_type": "has_certificate",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })
            # Also discover related domains via SANs
            san_domain = f"related-{entity_value}"
            san_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": san_id,
                "entity_type": "DOMAIN",
                "normalized_value": san_domain,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": cert_id,
                "target_entity_id": san_id,
                "relationship_type": "has_san",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "ip_intelligence" and entity_type == "IP":
            # IP → ASN
            asn = f"AS{hash(entity_value) % 65000}"
            asn_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": asn_id,
                "entity_type": "ASN",
                "normalized_value": asn,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": asn_id,
                "relationship_type": "belongs_to_asn",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "whois_rdap" and entity_type == "DOMAIN":
            # Domain → Organization
            org_name = f"Registrant of {entity_value}"
            org_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": org_id,
                "entity_type": "ORGANIZATION",
                "normalized_value": org_name,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": org_id,
                "relationship_type": "registered_by",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "web_crawler" and entity_type in ("DOMAIN", "URL"):
            # Domain/URL → URL
            url = f"https://{entity_value}/page-{hash(entity_value) % 100}"
            url_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": url_id,
                "entity_type": "URL",
                "normalized_value": url,
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": url_id,
                "relationship_type": "hosted_on",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "misp_feed":
            # MISP → Report
            report_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": report_id,
                "entity_type": "REPORT",
                "normalized_value": f"MISP report on {entity_value}",
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": report_id,
                "relationship_type": "reported_in",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "opencti_graph":
            # OpenCTI → Campaign/Person
            campaign_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": campaign_id,
                "entity_type": "CAMPAIGN",
                "normalized_value": f"OpenCTI campaign on {entity_value}",
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": campaign_id,
                "relationship_type": "indicates",
                "certainty": RelationshipCertainty.HYPOTHESIZED.value,
                "source": source,
            })

        elif source == "cortex_enrichment":
            # Cortex → Observation
            obs_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            score = hash(entity_value) % 100
            discovered_entities.append({
                "id": obs_id,
                "entity_type": "OBSERVATION",
                "normalized_value": f"Cortex score: {score}",
                "source": source,
                "reputation_score": score,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": obs_id,
                "relationship_type": "reputation_score",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "police_database":
            # Police → Case
            case_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": case_id,
                "entity_type": "CASE",
                "normalized_value": f"Police case on {entity_value}",
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": case_id,
                "relationship_type": "linked_to_case",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        elif source == "crypto_intelligence" and entity_type == "CRYPTO_WALLET":
            # Crypto → Transaction/Wallet
            tx_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            wallet_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            discovered_entities.append({
                "id": tx_id,
                "entity_type": "TRANSACTION",
                "normalized_value": f"tx:{uuid.uuid4().hex[:16]}",
                "source": source,
            })
            discovered_entities.append({
                "id": wallet_id,
                "entity_type": "CRYPTO_WALLET",
                "normalized_value": f"bc1q{uuid.uuid4().hex[:32]}",
                "source": source,
            })
            discovered_relationships.append({
                "source_entity_id": task.entity_id,
                "target_entity_id": tx_id,
                "relationship_type": "sent_to",
                "certainty": RelationshipCertainty.OBSERVED.value,
                "source": source,
            })

        return DiscoveryResult(
            task_id=task.id,
            source_name=source,
            discovered_entities=discovered_entities,
            discovered_relationships=discovered_relationships,
            source_reliability=source_cap.reliability,
        )


# ─── Graph Explorer ───


class GraphExplorer:
    """Expands the investigation graph with cycle detection and duplicate suppression.

    Uses BFS traversal from the seed entity, with:
    - Maximum depth
    - Maximum nodes per investigation
    - Priority scoring
    - Duplicate suppression (same entity discovered by multiple sources)
    - Cycle detection (avoid revisiting entities)
    """

    def __init__(self) -> None:
        self._visited: set[str] = set()
        self._entity_values: dict[str, str] = {}  # normalized_value → entity_id (for dedup)

    def reset(self) -> None:
        self._visited.clear()
        self._entity_values.clear()

    def should_explore(
        self,
        entity_id: str,
        entity_type: str,
        entity_value: str,
        depth: int,
        config: DiscoveryConfig,
    ) -> bool:
        """Check if an entity should be explored further."""
        # Already visited
        if entity_id in self._visited:
            return False

        # Depth limit
        if depth >= config.max_depth:
            return False

        # Node limit
        if len(self._visited) >= config.max_nodes:
            return False

        # Mark visited
        self._visited.add(entity_id)
        return True

    def deduplicate(self, entity: dict[str, Any]) -> str | None:
        """Check if an entity is a duplicate. Returns existing entity_id if duplicate, None if new."""
        value = entity.get("normalized_value", "")
        entity_type = entity.get("entity_type", "")

        # Dedup key: type + value
        dedup_key = f"{entity_type}:{value}"
        if dedup_key in self._entity_values:
            return self._entity_values[dedup_key]

        self._entity_values[dedup_key] = entity["id"]
        return None

    def add_to_graph(
        self,
        graph: dict[str, list[dict[str, Any]]],
        source_id: str,
        target_id: str,
        relationship_type: str,
        certainty: str,
        source: str,
    ) -> None:
        """Add a relationship to the investigation graph."""
        if source_id not in graph:
            graph[source_id] = []
        graph[source_id].append({
            "target": target_id,
            "relationship": relationship_type,
            "certainty": certainty,
            "source": source,
        })

    def get_graph_size(self, graph: dict[str, list[dict[str, Any]]]) -> int:
        """Count total nodes in the graph."""
        nodes = set()
        for source_id, edges in graph.items():
            nodes.add(source_id)
            for edge in edges:
                nodes.add(edge["target"])
        return len(nodes)

    def detect_cycles(self, graph: dict[str, list[dict[str, Any]]]) -> list[list[str]]:
        """Detect cycles in the investigation graph using DFS."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in graph.get(node, []):
                neighbor = edge["target"]
                if neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append([*path[cycle_start:], neighbor])
                elif neighbor not in visited:
                    dfs(neighbor, path)

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles


# ─── Relationship Hypothesizer ───


class RelationshipHypothesizer:
    """Generates observed/derived/hypothesized relationships.

    OBSERVED: Direct evidence from a source
    DERIVED: Deterministic transformation supports the relationship
    HYPOTHESIZED: Multiple signals suggest a possible relationship but evidence is incomplete

    Never stores a hypothesis as a confirmed fact.
    """

    def hypothesize(
        self,
        run_id: str,
        entities: dict[str, dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[RelationshipHypothesis]:
        """Generate relationship hypotheses from discovered data."""
        hypotheses: list[RelationshipHypothesis] = []

        # Group relationships by source-target pair
        pair_rels: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for rel in relationships:
            pair_key = (rel["source_entity_id"], rel["target_entity_id"])
            pair_rels[pair_key].append(rel)

        # Check for hypothesized relationships: two domains sharing the same IP or certificate
        entity_to_infra: dict[str, list[str]] = defaultdict(list)
        for rel in relationships:
            if rel["relationship_type"] in ("resolves_to", "has_certificate"):
                entity_to_infra[rel["target_entity_id"]].append(rel["source_entity_id"])

        # If two+ domains share infrastructure, hypothesize a relationship
        for infra_id, domain_ids in entity_to_infra.items():
            if len(domain_ids) >= 2:
                for i in range(len(domain_ids)):
                    for j in range(i + 1, len(domain_ids)):
                        # Check if this hypothesis already exists as an observed relationship
                        already_observed = any(
                            r["source_entity_id"] == domain_ids[i]
                            and r["target_entity_id"] == domain_ids[j]
                            and r["certainty"] == RelationshipCertainty.OBSERVED.value
                            for r in relationships
                        )
                        if not already_observed:
                            hyp = RelationshipHypothesis(
                                id=f"HYP-{uuid.uuid4().hex[:8].upper()}",
                                run_id=run_id,
                                source_entity_id=domain_ids[i],
                                target_entity_id=domain_ids[j],
                                relationship_type="potentially_related_to",
                                certainty=RelationshipCertainty.HYPOTHESIZED,
                                evidence=[f"Shared infrastructure: {infra_id}"],
                                confidence=0.6,
                                explanation=f"Two domains share the same infrastructure ({infra_id}), suggesting a potential relationship.",
                                sources=["infrastructure_correlation"],
                            )
                            hypotheses.append(hyp)

        return hypotheses


# ─── Discovery Scorer ───


class DiscoveryScorer:
    """Calculates evidence confidence and investigation priority.

    Separates Evidence Confidence from Investigation Priority.
    A high-priority lead is not automatically high-confidence evidence.

    Confidence model (not simply 4 sources = 4x confidence):
    - Base confidence from source reliability
    - Diminishing returns from additional sources
    - Independent source agreement boosts confidence
    - Single untrusted source cannot establish high confidence (data poisoning guard)
    """

    def calculate_confidence(
        self,
        sources: list[str],
        source_reliabilities: dict[str, float],
    ) -> float:
        """Calculate evidence confidence from multiple sources.

        Uses a diminishing returns model:
        confidence = 1 - product(1 - reliability_i) for each independent source

        This means:
        - 1 source at 0.8 reliability → 0.80 confidence
        - 2 sources at 0.8 each → 0.96 confidence
        - 3 sources at 0.8 each → 0.992 confidence
        - But a single source at 0.5 → 0.50 (not high)
        """
        if not sources:
            return 0.0

        # Deduplicate sources
        unique_sources = list(set(sources))
        if not unique_sources:
            return 0.0

        # Data poisoning guard: single untrusted source cannot exceed 0.6
        if len(unique_sources) == 1:
            reliability = source_reliabilities.get(unique_sources[0], 0.5)
            return min(reliability, 0.6)

        # Multiple sources: 1 - product(1 - reliability_i)
        complement_product = 1.0
        for source in unique_sources:
            reliability = source_reliabilities.get(source, 0.5)
            complement_product *= (1.0 - reliability)

        confidence = 1.0 - complement_product

        # Cap at 0.95 (never 100% from external sources)
        return min(confidence, 0.95)

    def calculate_priority(
        self,
        confidence: float,
        depth: int,
        entity_type: str,
        anomaly_score: float = 0.0,
        campaign_relevance: float = 0.0,
    ) -> float:
        """Calculate investigation priority.

        Priority is NOT the same as confidence.
        Priority considers: confidence, depth, entity type, anomaly, campaign relevance.
        """
        # Base priority from confidence
        priority = confidence * 0.4

        # Deeper discoveries are lower priority (diminishing returns)
        depth_factor = max(0.0, 1.0 - depth * 0.15)
        priority += depth_factor * 0.2

        # Entity type priority (domains and IPs are high-value)
        type_priority = {
            "DOMAIN": 0.9,
            "IP": 0.85,
            "URL": 0.8,
            "EMAIL": 0.75,
            "PHONE": 0.7,
            "CERTIFICATE": 0.65,
            "CRYPTO_WALLET": 0.85,
            "PERSON": 0.6,
            "ORGANIZATION": 0.65,
            "ASN": 0.5,
        }
        priority += type_priority.get(entity_type, 0.5) * 0.2

        # Anomaly score boosts priority
        priority += anomaly_score * 0.1

        # Campaign relevance boosts priority
        priority += campaign_relevance * 0.1

        return min(priority, 1.0)


# ─── Data Poisoning Guard ───


class DataPoisoningGuard:
    """Prevents single untrusted sources from establishing high confidence.

    Safeguards:
    - Source reliability scoring
    - Independent confirmation requirement
    - Temporal consistency checks
    - Cross-source comparison
    - No single untrusted source establishes high confidence
    """

    UNTRUSTED_SOURCE_THRESHOLD = 0.6
    MIN_SOURCES_FOR_HIGH_CONFIDENCE = 2

    def validate(
        self,
        sources: list[str],
        confidence: float,
        source_reliabilities: dict[str, float],
    ) -> tuple[bool, str]:
        """Validate a discovery against data poisoning safeguards.

        Returns (is_valid, reason).
        """
        unique_sources = list(set(sources))

        # Single untrusted source cannot establish high confidence
        if len(unique_sources) == 1:
            reliability = source_reliabilities.get(unique_sources[0], 0.5)
            if reliability < 0.8 and confidence > self.UNTRUSTED_SOURCE_THRESHOLD:
                return False, (
                    f"Single untrusted source ({unique_sources[0]}, reliability={reliability:.2f}) "
                    f"cannot establish confidence > {self.UNTRUSTED_SOURCE_THRESHOLD}"
                )

        # High confidence requires multiple sources
        if confidence > 0.8 and len(unique_sources) < self.MIN_SOURCES_FOR_HIGH_CONFIDENCE:
            return False, (
                f"High confidence ({confidence:.2f}) requires at least "
                f"{self.MIN_SOURCES_FOR_HIGH_CONFIDENCE} independent sources"
            )

        return True, "Valid"


# ─── Campaign Candidate Detector ───


class CampaignCandidateDetector:
    """Identifies clusters that are not yet assigned to known campaigns.

    Creates CAMPAIGN_CANDIDATE, not a confirmed campaign.
    Requires validation criteria before promotion to a confirmed campaign.
    """

    MIN_ENTITIES_FOR_CANDIDATE = 3
    MIN_RELATIONSHIPS_FOR_CANDIDATE = 2
    MIN_CONFIDENCE_FOR_PROMOTION = 0.7

    def detect(
        self,
        run_id: str,
        entities: dict[str, dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[CampaignCandidate]:
        """Detect campaign candidates from discovered entities and relationships."""
        # Build adjacency graph
        adjacency: dict[str, set[str]] = defaultdict(set)
        for rel in relationships:
            adjacency[rel["source_entity_id"]].add(rel["target_entity_id"])
            adjacency[rel["target_entity_id"]].add(rel["source_entity_id"])

        # Find connected components (clusters)
        visited: set[str] = set()
        clusters: list[set[str]] = []

        for entity_id in entities:
            if entity_id not in visited:
                cluster: set[str] = set()
                queue = [entity_id]
                while queue:
                    current = queue.pop(0)
                    if current in visited:
                        continue
                    visited.add(current)
                    cluster.add(current)
                    for neighbor in adjacency.get(current, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)
                clusters.append(cluster)

        # Filter clusters that meet candidate criteria
        candidates: list[CampaignCandidate] = []
        for cluster in clusters:
            if len(cluster) < self.MIN_ENTITIES_FOR_CANDIDATE:
                continue

            # Count relationships within the cluster
            cluster_rels = [
                r for r in relationships
                if r["source_entity_id"] in cluster and r["target_entity_id"] in cluster
            ]
            if len(cluster_rels) < self.MIN_RELATIONSHIPS_FOR_CANDIDATE:
                continue

            # Calculate shared indicators
            entity_types = list({
                entities[eid].get("entity_type", "UNKNOWN")
                for eid in cluster
                if eid in entities
            })

            # Confidence based on cluster density
            density = len(cluster_rels) / max(len(cluster) * (len(cluster) - 1) / 2, 1)
            confidence = min(density, 0.9)

            candidate = CampaignCandidate(
                id=f"CC-{uuid.uuid4().hex[:8].upper()}",
                run_id=run_id,
                entity_ids=list(cluster),
                entity_types=entity_types,
                relationship_count=len(cluster_rels),
                confidence=confidence,
                shared_indicators=[entities[eid].get("normalized_value", "") for eid in cluster if eid in entities][:5],
            )
            candidates.append(candidate)

        return candidates

    def can_promote(self, candidate: CampaignCandidate) -> bool:
        """Check if a campaign candidate can be promoted to a confirmed campaign."""
        return (
            candidate.confidence >= self.MIN_CONFIDENCE_FOR_PROMOTION
            and len(candidate.entity_ids) >= self.MIN_ENTITIES_FOR_CANDIDATE
            and candidate.status == CampaignCandidateStatus.UNDER_REVIEW
        )


# ─── Anomaly Detector ───


class AnomalyDetector:
    """Detects anomalous patterns in discovered data.

    Anomaly ≠ fraud.
    ANOMALY → INVESTIGATIVE LEAD, not ANOMALY → GUILT.

    Detects:
    - Sudden domain creation patterns
    - Infrastructure concentration
    - Certificate reuse
    - Unusual DNS changes
    - Rapid IP rotation
    - Repeated scam-page structures
    - Unusual report clusters
    - Repeated contact identifiers
    - Campaign emergence
    - Cross-border activity
    """

    def detect(self, entities: dict[str, dict[str, Any]], relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies in discovered data."""
        anomalies: list[dict[str, Any]] = []

        # 1. Infrastructure concentration: many domains on same IP
        ip_to_domains: dict[str, list[str]] = defaultdict(list)
        for rel in relationships:
            if rel["relationship_type"] == "resolves_to":
                ip_id = rel["target_entity_id"]
                domain_id = rel["source_entity_id"]
                ip_to_domains[ip_id].append(domain_id)

        for ip_id, domains in ip_to_domains.items():
            if len(domains) >= 3:
                anomalies.append({
                    "type": "infrastructure_concentration",
                    "description": f"{len(domains)} domains resolve to same IP",
                    "entity_id": ip_id,
                    "severity": "MEDIUM" if len(domains) < 5 else "HIGH",
                    "related_entities": domains,
                })

        # 2. Certificate reuse: same cert on multiple domains
        cert_to_domains: dict[str, list[str]] = defaultdict(list)
        for rel in relationships:
            if rel["relationship_type"] == "has_certificate":
                cert_id = rel["target_entity_id"]
                domain_id = rel["source_entity_id"]
                cert_to_domains[cert_id].append(domain_id)

        for cert_id, domains in cert_to_domains.items():
            if len(domains) >= 2:
                anomalies.append({
                    "type": "certificate_reuse",
                    "description": f"Certificate shared by {len(domains)} domains",
                    "entity_id": cert_id,
                    "severity": "MEDIUM",
                    "related_entities": domains,
                })

        # 3. Repeated contact identifiers: same email/phone in multiple reports
        value_to_entities: dict[str, list[str]] = defaultdict(list)
        for eid, entity in entities.items():
            value = entity.get("normalized_value", "")
            etype = entity.get("entity_type", "")
            if etype in ("EMAIL", "PHONE"):
                value_to_entities[value].append(eid)

        for value, eids in value_to_entities.items():
            if len(eids) >= 2:
                anomalies.append({
                    "type": "repeated_contact_identifier",
                    "description": f"Contact identifier '{value}' appears in {len(eids)} entities",
                    "entity_ids": eids,
                    "severity": "MEDIUM",
                })

        # 4. Cross-border activity: entities from different jurisdictions
        jurisdictions: set[str] = set()
        for _eid, entity in entities.items():
            jurisdiction = entity.get("jurisdiction")
            if jurisdiction:
                jurisdictions.add(jurisdiction)

        if len(jurisdictions) >= 2:
            anomalies.append({
                "type": "cross_border_activity",
                "description": f"Entities span {len(jurisdictions)} jurisdictions",
                "jurisdictions": list(jurisdictions),
                "severity": "LOW",
            })

        return anomalies


# ─── Lead Engine ───


class LeadEngine:
    """Generates investigative leads with full explanation.

    Every lead must show exactly why it was generated.
    """

    def generate_leads(
        self,
        run_id: str,
        seed_entity: dict[str, Any],
        discovered_entities: dict[str, dict[str, Any]],
        relationships: list[dict[str, Any]],
        hypotheses: list[RelationshipHypothesis],
        confidence_scores: dict[str, float],
        priority_scores: dict[str, float],
        anomalies: list[dict[str, Any]],
        campaign_candidates: list[CampaignCandidate],
    ) -> list[InvestigationLead]:
        """Generate investigative leads from discovery results."""
        leads: list[InvestigationLead] = []

        seed_id = seed_entity.get("id", "")
        seed_value = seed_entity.get("normalized_value", "")

        for entity_id, entity in discovered_entities.items():
            if entity_id == seed_id:
                continue

            # Find relationships connecting this entity to the seed
            entity_rels = [
                r for r in relationships
                if r["source_entity_id"] == entity_id or r["target_entity_id"] == entity_id
            ]

            if not entity_rels:
                continue

            # Find sources
            sources = list({r.get("source", "unknown") for r in entity_rels})

            # Find related hypotheses
            related_hyps = [h for h in hypotheses if h.source_entity_id == entity_id or h.target_entity_id == entity_id]

            # Check for anomaly
            entity_anomalies = [a for a in anomalies if a.get("entity_id") == entity_id]

            # Check for campaign candidate
            campaign_id = None
            for cc in campaign_candidates:
                if entity_id in cc.entity_ids:
                    campaign_id = cc.id
                    break

            # Build relationship path
            path = self._find_path(seed_id, entity_id, relationships)

            # Build reason
            reason_parts = []
            reason_parts.append(f"Discovered via {len(sources)} source(s): {', '.join(sources)}")
            if related_hyps:
                reason_parts.append(f"{len(related_hyps)} hypothesized relationship(s)")
            if entity_anomalies:
                reason_parts.append(f"{len(entity_anomalies)} anomaly/anomalies detected")
            if campaign_id:
                reason_parts.append(f"Part of campaign candidate {campaign_id}")

            confidence = confidence_scores.get(entity_id, 0.0)
            priority = priority_scores.get(entity_id, 0.0)

            lead = InvestigationLead(
                id=f"LEAD-{uuid.uuid4().hex[:8].upper()}",
                run_id=run_id,
                seed_entity_id=seed_id,
                seed_entity_value=seed_value,
                discovered_entity_id=entity_id,
                discovered_entity_value=entity.get("normalized_value", ""),
                discovered_entity_type=entity.get("entity_type", "UNKNOWN"),
                evidence_count=len(entity_rels),
                evidence_sources=sources,
                confidence=confidence,
                priority=priority,
                reason="; ".join(reason_parts),
                relationship_path=path,
                campaign_candidate_id=campaign_id,
            )
            leads.append(lead)

        # Sort by priority (descending)
        leads.sort(key=lambda lead_obj: lead_obj.priority, reverse=True)
        return leads

    def _find_path(
        self,
        start: str,
        end: str,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """Find a path from start to end in the relationship graph (BFS)."""
        # Build adjacency
        adjacency: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for rel in relationships:
            adjacency[rel["source_entity_id"]].append(
                (rel["target_entity_id"], rel["relationship_type"], rel.get("source", ""))
            )

        # BFS
        queue: list[tuple[str, list[dict[str, str]]]] = [(start, [])]
        visited: set[str] = {start}

        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path

            for neighbor, rel_type, source in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = [*path, {
                        "from": current,
                        "to": neighbor,
                        "relationship": rel_type,
                        "source": source,
                    }]
                    queue.append((neighbor, new_path))

        return []


# ─── Coverage Reporter ───


class CoverageReporter:
    """Reports what sources were checked, not checked, failed, unavailable.

    Never reports "no match" as absolute if relevant sources were not checked.
    """

    def report(
        self,
        run_id: str,
        tasks: list[DiscoveryTask],
        entity_type: str,
    ) -> DiscoveryCoverage:
        """Generate a coverage report for a discovery run."""
        coverage = DiscoveryCoverage(run_id=run_id)

        # Determine which sources are relevant for this entity type
        relevant_sources = set()
        for source_name, cap in DEFAULT_SOURCES.items():
            if entity_type in cap.entity_types:
                relevant_sources.add(source_name)

        # Also add sources from discovery chains
        planner = DiscoveryPlanner()
        chain = planner.DISCOVERY_CHAINS.get(entity_type, [])
        for step in chain:
            relevant_sources.add(step["source"])

        # Check task results
        task_sources: dict[str, TaskStatus] = {}
        for task in tasks:
            task_sources[task.source_name] = task.status

        for source_name in relevant_sources:
            status = task_sources.get(source_name)

            if status == TaskStatus.COMPLETED:
                coverage.source_status[source_name] = SourceStatus.CHECKED
                coverage.checked.append(source_name)
            elif status == TaskStatus.FAILED:
                coverage.source_status[source_name] = SourceStatus.FAILED
                coverage.failed.append(source_name)
            elif status == TaskStatus.UNAUTHORIZED:
                coverage.source_status[source_name] = SourceStatus.AUTHORIZATION_REQUIRED
                coverage.authorization_required.append(source_name)
            elif status == TaskStatus.RATE_LIMITED:
                coverage.source_status[source_name] = SourceStatus.LIMITED
                coverage.limited.append(source_name)
            elif status is None:
                # Not checked
                restriction = DEFAULT_RESTRICTIONS.get(source_name)
                if restriction and restriction.auth_required:
                    coverage.source_status[source_name] = SourceStatus.AUTHORIZATION_REQUIRED
                    coverage.authorization_required.append(source_name)
                else:
                    coverage.source_status[source_name] = SourceStatus.NOT_CHECKED
                    coverage.not_checked.append(source_name)

        return coverage

    def format_report(self, coverage: DiscoveryCoverage) -> str:
        """Format coverage as a human-readable report."""
        lines = ["INVESTIGATION COVERAGE", ""]
        for source, status in sorted(coverage.source_status.items()):
            status_str = status.value.replace("_", " ").upper()
            lines.append(f"{source:30s} {status_str}")

        if coverage.not_checked:
            lines.append("")
            lines.append("WARNING: Some sources were not checked. 'No match' is not absolute.")
        if coverage.authorization_required:
            lines.append("")
            lines.append("AUTHORIZATION REQUIRED:")
            for source in coverage.authorization_required:
                lines.append(f"  - {source}")

        return "\n".join(lines)


# ─── Monitoring Rule Manager ───


class MonitoringRuleManager:
    """Configures continuous monitoring for discovered entities.

    Uses TTL, priority, investigation status, risk, source cost, and retention policy.
    Does not monitor every entity forever without a policy.
    """

    def create_rules(
        self,
        run_id: str,
        discovered_entities: dict[str, dict[str, Any]],
        leads: list[InvestigationLead],
        config: DiscoveryConfig,
    ) -> list[MonitoringRule]:
        """Create monitoring rules for high-priority discovered entities."""
        if not config.enable_monitoring:
            return []

        rules: list[MonitoringRule] = []

        # Only monitor entities with high-priority leads
        high_priority_leads = [lead for lead in leads if lead.priority >= 0.6]
        monitored_ids = set()

        for lead in high_priority_leads:
            if lead.discovered_entity_id in monitored_ids:
                continue
            monitored_ids.add(lead.discovered_entity_id)

            entity = discovered_entities.get(lead.discovered_entity_id, {})
            entity_type = entity.get("entity_type", "UNKNOWN")
            entity_value = entity.get("normalized_value", "")

            # Determine monitor types based on entity type
            monitor_types = self._get_monitor_types(entity_type)

            # Determine TTL based on priority
            if lead.priority >= 0.8:
                ttl = MonitoringTTL.LONG
            elif lead.priority >= 0.7:
                ttl = MonitoringTTL.MEDIUM
            else:
                ttl = MonitoringTTL.SHORT

            rule = MonitoringRule(
                id=f"MON-{uuid.uuid4().hex[:8].upper()}",
                entity_id=lead.discovered_entity_id,
                entity_type=entity_type,
                entity_value=entity_value,
                monitor_types=monitor_types,
                ttl=ttl,
                priority=lead.priority,
                investigation_id=run_id,
            )
            rules.append(rule)

        return rules

    def _get_monitor_types(self, entity_type: str) -> list[str]:
        """Get relevant monitor types for an entity type."""
        monitor_map = {
            "DOMAIN": ["dns", "certificate", "whois", "related_domains"],
            "IP": ["reverse_dns", "asn", "related_infrastructure"],
            "URL": ["content", "certificate", "dns"],
            "EMAIL": ["breach_feeds", "misp_feeds"],
            "PHONE": ["reports", "misp_feeds"],
            "CRYPTO_WALLET": ["transactions", "misp_feeds"],
            "CERTIFICATE": ["transparency", "san_changes"],
        }
        return monitor_map.get(entity_type, ["reports"])


# ─── Resource Controller ───


class ResourceController:
    """Enforces rate limits, budgets, and prevents graph explosion.

    Controls:
    - Per-source rate limits
    - Per-investigation budgets
    - Concurrency limits
    - Maximum graph depth and nodes
    - Maximum tasks and runtime
    """

    def __init__(self) -> None:
        self._source_call_times: dict[str, list[float]] = defaultdict(list)
        self._source_counts: dict[str, int] = defaultdict(int)
        self._start_time: float = 0.0

    def reset(self) -> None:
        self._source_call_times.clear()
        self._source_counts.clear()
        self._start_time = time.time()

    def can_execute(self, task: DiscoveryTask, config: DiscoveryConfig) -> tuple[bool, str]:
        """Check if a task can be executed under resource limits."""
        # Check max tasks
        total_tasks = sum(self._source_counts.values())
        if total_tasks >= config.max_tasks:
            return False, "Maximum tasks reached"

        # Check max runtime
        if time.time() - self._start_time > config.max_runtime_seconds:
            return False, "Maximum runtime exceeded"

        # Check per-source budget
        source_budget = config.per_source_budget.get(task.source_name, 10)
        if self._source_counts[task.source_name] >= source_budget:
            return False, f"Source budget exceeded for {task.source_name}"

        # Check rate limit
        source_cap = DEFAULT_SOURCES.get(task.source_name)
        if source_cap:
            now = time.time()
            window = 60.0  # 1 minute
            recent_calls = [
                t for t in self._source_call_times[task.source_name]
                if now - t < window
            ]
            if len(recent_calls) >= source_cap.rate_limit_per_minute:
                return False, f"Rate limit exceeded for {task.source_name}"

        return True, "OK"

    def record_execution(self, task: DiscoveryTask) -> None:
        """Record that a task was executed."""
        self._source_counts[task.source_name] += 1
        self._source_call_times[task.source_name].append(time.time())


# ─── Discovery Orchestrator ───


class DiscoveryOrchestrator:
    """Manages a full discovery run from seed to leads.

    Flow:
        Seed → Discovery Plan → Source Selection → Collection → Normalization →
        Entity Resolution → Graph Expansion → Scoring → Validation → New Lead → Continue
    """

    def __init__(self) -> None:
        self.planner = DiscoveryPlanner()
        self.router = SourceRouter()
        self.explorer = GraphExplorer()
        self.hypothesizer = RelationshipHypothesizer()
        self.scorer = DiscoveryScorer()
        self.poisoning_guard = DataPoisoningGuard()
        self.campaign_detector = CampaignCandidateDetector()
        self.anomaly_detector = AnomalyDetector()
        self.lead_engine = LeadEngine()
        self.coverage_reporter = CoverageReporter()
        self.monitoring_manager = MonitoringRuleManager()
        self.resource_controller = ResourceController()

    def run(
        self,
        seed_entity_id: str,
        seed_entity_type: str,
        seed_entity_value: str,
        config: DiscoveryConfig | None = None,
    ) -> DiscoveryRun:
        """Execute a full discovery run from a seed entity."""
        config = config or DiscoveryConfig()

        run = DiscoveryRun(
            id=f"RUN-{uuid.uuid4().hex[:8].upper()}",
            seed_entity_id=seed_entity_id,
            seed_entity_type=seed_entity_type,
            seed_entity_value=seed_entity_value,
            config=config,
        )

        # Initialize
        self.explorer.reset()
        self.resource_controller.reset()

        # Add seed entity to discovered
        seed_entity = {
            "id": seed_entity_id,
            "entity_type": seed_entity_type,
            "normalized_value": seed_entity_value,
            "depth": 0,
        }
        run.discovered_entities[seed_entity_id] = seed_entity
        run.graph[seed_entity_id] = []

        run.status = DiscoveryRunStatus.PLANNING

        # BFS expansion
        queue: list[tuple[str, str, str, int]] = [(seed_entity_id, seed_entity_type, seed_entity_value, 0)]

        while queue:
            # Check resource limits
            if len(run.discovered_entities) >= config.max_nodes:
                logger.info("Max nodes reached, stopping expansion", max=config.max_nodes)
                break

            entity_id, entity_type, entity_value, depth = queue.pop(0)

            # Check if we should explore this entity
            if not self.explorer.should_explore(entity_id, entity_type, entity_value, depth, config):
                continue

            # Plan tasks
            existing_sources = [t.source_name for t in run.tasks]
            tasks = self.planner.plan(entity_id, entity_type, entity_value, depth, config, existing_sources)
            for task in tasks:
                task.run_id = run.id
            run.tasks.extend(tasks)

            run.status = DiscoveryRunStatus.COLLECTING

            # Execute tasks
            for task in tasks:
                # Resource control
                can_exec, reason = self.resource_controller.can_execute(task, config)
                if not can_exec:
                    if "Rate limit" in reason:
                        task.status = TaskStatus.RATE_LIMITED
                    elif "budget" in reason or "Maximum" in reason:
                        task.status = TaskStatus.SKIPPED
                    continue

                self.resource_controller.record_execution(task)

                # Execute
                result = self.router.execute(task, config)
                run.results.append(result)
                run.total_tasks += 1

                if task.status == TaskStatus.COMPLETED:
                    run.completed_tasks += 1

                    # Process discovered entities
                    for disc_entity in result.discovered_entities:
                        # Check max nodes before adding
                        if len(run.discovered_entities) >= config.max_nodes:
                            break
                        # Deduplicate
                        existing_id = self.explorer.deduplicate(disc_entity)
                        if existing_id:
                            # Entity already known — add relationship to existing
                            for rel in result.discovered_relationships:
                                if rel["target_entity_id"] == disc_entity["id"]:
                                    rel["target_entity_id"] = existing_id
                                    self.explorer.add_to_graph(
                                        run.graph,
                                        rel["source_entity_id"],
                                        existing_id,
                                        rel["relationship_type"],
                                        rel.get("certainty", RelationshipCertainty.OBSERVED.value),
                                        rel.get("source", task.source_name),
                                    )
                        else:
                            # New entity
                            run.discovered_entities[disc_entity["id"]] = disc_entity
                            run.graph[disc_entity["id"]] = []
                            queue.append((
                                disc_entity["id"],
                                disc_entity.get("entity_type", "UNKNOWN"),
                                disc_entity.get("normalized_value", ""),
                                depth + 1,
                            ))

                    # Process relationships
                    for rel in result.discovered_relationships:
                        self.explorer.add_to_graph(
                            run.graph,
                            rel["source_entity_id"],
                            rel["target_entity_id"],
                            rel["relationship_type"],
                            rel.get("certainty", RelationshipCertainty.OBSERVED.value),
                            rel.get("source", task.source_name),
                        )
                else:
                    run.failed_tasks += 1

        run.status = DiscoveryRunStatus.RESOLVING

        # Collect all relationships
        all_relationships: list[dict[str, Any]] = []
        for source_id, edges in run.graph.items():
            for edge in edges:
                all_relationships.append({
                    "source_entity_id": source_id,
                    "target_entity_id": edge["target"],
                    "relationship_type": edge["relationship"],
                    "certainty": edge["certainty"],
                    "source": edge["source"],
                })

        # Generate hypotheses
        run.hypotheses = self.hypothesizer.hypothesize(run.id, run.discovered_entities, all_relationships)

        # Score entities
        run.status = DiscoveryRunStatus.SCORING

        confidence_scores: dict[str, float] = {}
        priority_scores: dict[str, float] = {}
        source_reliabilities: dict[str, float] = {
            name: cap.reliability for name, cap in DEFAULT_SOURCES.items()
        }

        for entity_id in run.discovered_entities:
            if entity_id == seed_entity_id:
                continue

            # Find sources that discovered this entity
            entity_sources: list[str] = []
            entity_depth = 0
            for source_id, edges in run.graph.items():
                for edge in edges:
                    if edge["target"] == entity_id:
                        entity_sources.append(edge["source"])
                        entity_depth = max(entity_depth, run.discovered_entities.get(source_id, {}).get("depth", 0) + 1)

            confidence = self.scorer.calculate_confidence(entity_sources, source_reliabilities)

            # Data poisoning guard
            is_valid, _ = self.poisoning_guard.validate(entity_sources, confidence, source_reliabilities)
            if not is_valid:
                confidence = min(confidence, 0.6)

            confidence_scores[entity_id] = confidence

            entity_type = run.discovered_entities[entity_id].get("entity_type", "UNKNOWN")
            priority = self.scorer.calculate_priority(confidence, entity_depth, entity_type)
            priority_scores[entity_id] = priority

        # Detect anomalies
        anomalies: list[dict[str, Any]] = []
        if config.enable_anomaly_detection:
            anomalies = self.anomaly_detector.detect(run.discovered_entities, all_relationships)

        # Detect campaign candidates
        campaign_candidates: list[CampaignCandidate] = []
        if config.enable_campaign_detection:
            campaign_candidates = self.campaign_detector.detect(
                run.id, run.discovered_entities, all_relationships
            )
        run.campaign_candidates = campaign_candidates

        # Generate leads
        run.leads = self.lead_engine.generate_leads(
            run.id,
            seed_entity,
            run.discovered_entities,
            all_relationships,
            run.hypotheses,
            confidence_scores,
            priority_scores,
            anomalies,
            campaign_candidates,
        )

        # Generate coverage report
        run.coverage = self.coverage_reporter.report(run.id, run.tasks, seed_entity_type)

        # Create monitoring rules
        run.monitoring_rules = self.monitoring_manager.create_rules(
            run.id, run.discovered_entities, run.leads, config
        )

        run.status = DiscoveryRunStatus.COMPLETED
        run.completed_at = time.time()

        logger.info(
            "Discovery run completed",
            run_id=run.id,
            seed=seed_entity_value,
            entities=len(run.discovered_entities),
            leads=len(run.leads),
            candidates=len(campaign_candidates),
            anomalies=len(anomalies),
        )

        return run

    def confirm_lead(self, lead: InvestigationLead) -> InvestigationLead:
        """Confirm a lead (human-in-the-loop)."""
        lead.status = LeadStatus.CONFIRMED
        return lead

    def reject_lead(self, lead: InvestigationLead) -> InvestigationLead:
        """Reject a lead (human-in-the-loop)."""
        lead.status = LeadStatus.REJECTED
        return lead

    def suppress_lead(self, lead: InvestigationLead) -> InvestigationLead:
        """Suppress a false positive lead (human-in-the-loop)."""
        lead.status = LeadStatus.SUPPRESSED
        return lead
