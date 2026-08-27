"""Tests for GFIN Unknown Fraud Discovery Engine (UFDE)

Per Engineering Task Specification v1.0, Section 30:
Tests for: discovery planning, graph expansion, cycle detection, duplicate suppression,
source failure, rate limiting, confidence calculation, priority calculation, provenance,
classification, jurisdiction, authorization, campaign candidates, anomaly detection,
blind-spot reporting, monitoring, prompt injection from external content, data poisoning,
unauthorized source access, resource exhaustion.

Include adversarial tests.

Layer A: In-memory tests with mock sources.
"""

import pytest

from services.unknown_fraud_discovery import (
    AnomalyDetector,
    CampaignCandidateDetector,
    CampaignCandidateStatus,
    CoverageReporter,
    DataPoisoningGuard,
    DiscoveryConfig,
    DiscoveryOrchestrator,
    DiscoveryPlanner,
    DiscoveryScorer,
    GraphExplorer,
    LeadEngine,
    MonitoringRuleManager,
    MonitoringTTL,
    RelationshipCertainty,
    RelationshipHypothesizer,
    ResourceController,
    SourceRouter,
    TaskStatus,
)

# ─── Fixtures ───


@pytest.fixture
def planner():
    return DiscoveryPlanner()


@pytest.fixture
def router():
    return SourceRouter()


@pytest.fixture
def explorer():
    return GraphExplorer()


@pytest.fixture
def hypothesizer():
    return RelationshipHypothesizer()


@pytest.fixture
def scorer():
    return DiscoveryScorer()


@pytest.fixture
def poisoning_guard():
    return DataPoisoningGuard()


@pytest.fixture
def campaign_detector():
    return CampaignCandidateDetector()


@pytest.fixture
def anomaly_detector():
    return AnomalyDetector()


@pytest.fixture
def lead_engine():
    return LeadEngine()


@pytest.fixture
def coverage_reporter():
    return CoverageReporter()


@pytest.fixture
def monitoring_manager():
    return MonitoringRuleManager()


@pytest.fixture
def resource_controller():
    return ResourceController()


@pytest.fixture
def orchestrator():
    return DiscoveryOrchestrator()


@pytest.fixture
def default_config():
    return DiscoveryConfig()


@pytest.fixture
def investigator_config():
    return DiscoveryConfig(
        user_role="investigator",
        user_classification="PUBLIC",
        max_depth=5,
        max_nodes=50,
        max_tasks=30,
    )


@pytest.fixture
def police_config():
    return DiscoveryConfig(
        user_role="police_officer",
        user_classification="LAW_ENFORCEMENT",
        max_depth=5,
        max_nodes=50,
        max_tasks=30,
    )


# ─── 1. Discovery Planning ───


class TestDiscoveryPlanning:
    def test_plan_generates_tasks_for_domain(self, planner):
        """Planner generates prioritized tasks for a domain seed."""
        tasks = planner.plan("ENT-001", "DOMAIN", "example.com", 0, DiscoveryConfig())
        assert len(tasks) > 0
        assert any(t.source_name == "dns_resolver" for t in tasks)
        assert any(t.source_name == "certificate_transparency" for t in tasks)

    def test_plan_prioritizes_correctly(self, planner):
        """DNS resolution has higher priority than MISP feed for domains."""
        tasks = planner.plan("ENT-001", "DOMAIN", "example.com", 0, DiscoveryConfig())
        dns_task = next(t for t in tasks if t.source_name == "dns_resolver")
        misp_task = next(t for t in tasks if t.source_name == "misp_feed")
        assert dns_task.priority > misp_task.priority

    def test_plan_returns_empty_at_max_depth(self, planner):
        """No tasks generated at max depth."""
        config = DiscoveryConfig(max_depth=3)
        tasks = planner.plan("ENT-001", "DOMAIN", "example.com", 3, config)
        assert len(tasks) == 0

    def test_plan_reduces_priority_at_depth(self, planner):
        """Tasks at deeper depth have lower priority."""
        tasks_depth0 = planner.plan("ENT-001", "DOMAIN", "example.com", 0, DiscoveryConfig())
        tasks_depth2 = planner.plan("ENT-001", "DOMAIN", "example.com", 2, DiscoveryConfig())
        dns0 = next(t for t in tasks_depth0 if t.source_name == "dns_resolver")
        dns2 = next(t for t in tasks_depth2 if t.source_name == "dns_resolver")
        assert dns0.priority > dns2.priority

    def test_plan_for_unknown_entity_type(self, planner):
        """Unknown entity types generate no tasks."""
        tasks = planner.plan("ENT-001", "UNKNOWN_TYPE", "value", 0, DiscoveryConfig())
        assert len(tasks) == 0

    def test_plan_generates_tasks_for_ip(self, planner):
        """Planner generates tasks for IP seed."""
        tasks = planner.plan("ENT-001", "IP", "192.168.1.1", 0, DiscoveryConfig())
        assert len(tasks) > 0
        assert any(t.source_name == "ip_intelligence" for t in tasks)

    def test_plan_generates_tasks_for_email(self, planner):
        """Planner generates tasks for email seed."""
        tasks = planner.plan("ENT-001", "EMAIL", "test@example.com", 0, DiscoveryConfig())
        assert len(tasks) > 0
        assert any(t.source_name == "misp_feed" for t in tasks)

    def test_plan_generates_tasks_for_crypto_wallet(self, planner):
        """Planner generates tasks for crypto wallet seed."""
        tasks = planner.plan("ENT-001", "CRYPTO_WALLET", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", 0, DiscoveryConfig())
        assert len(tasks) > 0
        assert any(t.source_name == "crypto_intelligence" for t in tasks)


# ─── 2. Graph Expansion ───


class TestGraphExpansion:
    def test_graph_expands_from_seed(self, orchestrator):
        """Graph expands from seed entity to discovered entities."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test-fraud.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        assert len(run.discovered_entities) > 1  # Seed + discovered

    def test_graph_respects_max_nodes(self, orchestrator):
        """Graph expansion stops at max_nodes."""
        config = DiscoveryConfig(max_depth=10, max_nodes=5)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        assert len(run.discovered_entities) <= 5

    def test_graph_respects_max_depth(self, orchestrator):
        """Graph expansion stops at max_depth."""
        config = DiscoveryConfig(max_depth=1, max_nodes=50)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        # At depth 1, only direct neighbors of seed should be discovered
        assert len(run.discovered_entities) <= 10  # Reasonable upper bound

    def test_graph_contains_seed(self, orchestrator):
        """Seed entity is always in the graph."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example")
        assert "ENT-001" in run.discovered_entities

    def test_graph_has_relationships(self, orchestrator):
        """Graph has edges (relationships) after expansion."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        total_edges = sum(len(edges) for edges in run.graph.values())
        assert total_edges > 0

    def test_graph_discovered_entities_have_provenance(self, orchestrator):
        """Discovered entities have source provenance."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for eid, entity in run.discovered_entities.items():
            if eid == "ENT-001":
                continue
            assert "source" in entity


# ─── 3. Cycle Detection ───


class TestCycleDetection:
    def test_detect_cycles_no_cycles(self, explorer):
        """No cycles in a simple linear graph."""
        graph = {"A": [{"target": "B", "relationship": "r", "certainty": "OBSERVED", "source": "s"}],
                  "B": []}
        cycles = explorer.detect_cycles(graph)
        assert len(cycles) == 0

    def test_detect_cycles_simple_cycle(self, explorer):
        """Detects a simple A→B→A cycle."""
        graph = {"A": [{"target": "B", "relationship": "r", "certainty": "OBSERVED", "source": "s"}],
                  "B": [{"target": "A", "relationship": "r", "certainty": "OBSERVED", "source": "s"}]}
        cycles = explorer.detect_cycles(graph)
        assert len(cycles) >= 1

    def test_detect_cycles_no_false_positive(self, explorer):
        """No false positive cycle in a DAG."""
        graph = {"A": [{"target": "B", "relationship": "r", "certainty": "OBSERVED", "source": "s"},
                        {"target": "C", "relationship": "r", "certainty": "OBSERVED", "source": "s"}],
                  "B": [{"target": "D", "relationship": "r", "certainty": "OBSERVED", "source": "s"}],
                  "C": [{"target": "D", "relationship": "r", "certainty": "OBSERVED", "source": "s"}],
                  "D": []}
        cycles = explorer.detect_cycles(graph)
        assert len(cycles) == 0


# ─── 4. Duplicate Suppression ───


class TestDuplicateSuppression:
    def test_dedup_returns_none_for_new_entity(self, explorer):
        """New entity returns None (no duplicate)."""
        entity = {"id": "ENT-001", "entity_type": "DOMAIN", "normalized_value": "example.com"}
        result = explorer.deduplicate(entity)
        assert result is None

    def test_dedup_returns_existing_id_for_duplicate(self, explorer):
        """Duplicate entity returns existing entity_id."""
        entity1 = {"id": "ENT-001", "entity_type": "DOMAIN", "normalized_value": "example.com"}
        entity2 = {"id": "ENT-002", "entity_type": "DOMAIN", "normalized_value": "example.com"}
        explorer.deduplicate(entity1)
        result = explorer.deduplicate(entity2)
        assert result == "ENT-001"

    def test_dedup_differentiates_by_type(self, explorer):
        """Same value but different type is not a duplicate."""
        domain = {"id": "ENT-001", "entity_type": "DOMAIN", "normalized_value": "example.com"}
        url = {"id": "ENT-002", "entity_type": "URL", "normalized_value": "example.com"}
        explorer.deduplicate(domain)
        result = explorer.deduplicate(url)
        assert result is None


# ─── 5. Source Failure ───


class TestSourceFailure:
    def test_source_unavailable_returns_error(self, router):
        """Unavailable source returns error result."""
        router.set_failure_mode("dns_resolver", "unavailable")

        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert result.error == "Source unavailable"
        assert task.status == TaskStatus.FAILED

    def test_source_unauthorized_returns_unauthorized(self, router):
        """Unauthorized source returns unauthorized status."""
        router.set_failure_mode("police_database", "unauthorized")
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="PERSON",
            entity_value="John Doe", source_name="police_database",
            relationship_type="linked_to_case", priority=0.5, depth=0,
        )
        result = router.execute(task, DiscoveryConfig(user_role="police_officer"))
        assert result.error == "Authorization required"
        assert task.status == TaskStatus.UNAUTHORIZED

    def test_source_rate_limited_returns_rate_limited(self, router):
        """Rate-limited source returns rate_limited status."""
        router.set_failure_mode("dns_resolver", "rate_limited")
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert result.error == "Rate limited"
        assert task.status == TaskStatus.RATE_LIMITED

    def test_unknown_source_returns_error(self, router):
        """Unknown source returns error."""
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="nonexistent_source",
            relationship_type="r", priority=0.5, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert result.error is not None


# ─── 6. Rate Limiting ───


class TestRateLimiting:
    def test_resource_controller_blocks_after_budget(self, resource_controller):
        """Resource controller blocks after per-source budget exceeded."""
        resource_controller.reset()
        config = DiscoveryConfig(per_source_budget={"dns_resolver": 2})
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="r", priority=0.9, depth=0,
        )
        # First two should pass
        assert resource_controller.can_execute(task, config)[0] is True
        resource_controller.record_execution(task)
        assert resource_controller.can_execute(task, config)[0] is True
        resource_controller.record_execution(task)
        # Third should fail
        can, reason = resource_controller.can_execute(task, config)
        assert can is False
        assert "budget" in reason

    def test_resource_controller_blocks_after_max_tasks(self, resource_controller):
        """Resource controller blocks after max_tasks reached."""
        resource_controller.reset()
        config = DiscoveryConfig(max_tasks=2)
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="r", priority=0.9, depth=0,
        )
        resource_controller.record_execution(task)
        resource_controller.record_execution(task)
        can, reason = resource_controller.can_execute(task, config)
        assert can is False
        assert "tasks" in reason

    def test_resource_controller_tracks_per_source(self, resource_controller):
        """Resource controller tracks calls per source separately."""
        resource_controller.reset()
        config = DiscoveryConfig(per_source_budget={"dns_resolver": 1, "misp_feed": 1})
        from services.unknown_fraud_discovery import DiscoveryTask
        dns_task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="r", priority=0.9, depth=0,
        )
        misp_task = DiscoveryTask(
            id="T2", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="misp_feed",
            relationship_type="r", priority=0.5, depth=0,
        )
        resource_controller.record_execution(dns_task)
        # DNS exhausted but MISP still available
        assert resource_controller.can_execute(dns_task, config)[0] is False
        assert resource_controller.can_execute(misp_task, config)[0] is True


# ─── 7. Confidence Calculation ───


class TestConfidenceCalculation:
    def test_single_source_confidence(self, scorer):
        """Single source confidence is limited to source reliability."""
        confidence = scorer.calculate_confidence(["dns_resolver"], {"dns_resolver": 0.95})
        assert confidence == 0.6  # Capped at 0.6 for single source

    def test_multiple_sources_increase_confidence(self, scorer):
        """Multiple independent sources increase confidence beyond single source cap."""
        confidence1 = scorer.calculate_confidence(["dns_resolver"], {"dns_resolver": 0.8})
        confidence2 = scorer.calculate_confidence(["dns_resolver", "misp_feed"], {"dns_resolver": 0.8, "misp_feed": 0.85})
        assert confidence2 > confidence1

    def test_confidence_not_4x_with_4_sources(self, scorer):
        """4 sources don't give 4x confidence (diminishing returns)."""
        confidence1 = scorer.calculate_confidence(["s1"], {"s1": 0.8})
        confidence4 = scorer.calculate_confidence(["s1", "s2", "s3", "s4"], {"s1": 0.8, "s2": 0.8, "s3": 0.8, "s4": 0.8})
        assert confidence4 < confidence1 * 4  # Not 4x
        assert confidence4 <= 0.95  # Capped

    def test_empty_sources_zero_confidence(self, scorer):
        """No sources means zero confidence."""
        confidence = scorer.calculate_confidence([], {})
        assert confidence == 0.0

    def test_confidence_never_exceeds_95_percent(self, scorer):
        """Confidence from external sources is capped at 95%."""
        sources = [f"s{i}" for i in range(10)]
        reliabilities = dict.fromkeys(sources, 0.99)
        confidence = scorer.calculate_confidence(sources, reliabilities)
        assert confidence <= 0.95


# ─── 8. Priority Calculation ───


class TestPriorityCalculation:
    def test_priority_separate_from_confidence(self, scorer):
        """Priority is different from confidence."""
        confidence = 0.9
        priority = scorer.calculate_priority(confidence, depth=0, entity_type="DOMAIN")
        assert priority != confidence  # They are separate metrics

    def test_priority_decreases_with_depth(self, scorer):
        """Deeper discoveries have lower priority."""
        priority0 = scorer.calculate_priority(0.8, depth=0, entity_type="DOMAIN")
        priority3 = scorer.calculate_priority(0.8, depth=3, entity_type="DOMAIN")
        assert priority0 > priority3

    def test_priority_varies_by_entity_type(self, scorer):
        """Different entity types have different base priority."""
        priority_domain = scorer.calculate_priority(0.8, depth=0, entity_type="DOMAIN")
        priority_asn = scorer.calculate_priority(0.8, depth=0, entity_type="ASN")
        assert priority_domain > priority_asn

    def test_priority_never_exceeds_1(self, scorer):
        """Priority is capped at 1.0."""
        priority = scorer.calculate_priority(0.95, depth=0, entity_type="DOMAIN", anomaly_score=1.0, campaign_relevance=1.0)
        assert priority <= 1.0


# ─── 9. Provenance ───


class TestProvenance:
    def test_discovered_entity_has_source(self, orchestrator):
        """Every discovered entity has a source attribute."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=2, max_nodes=10))
        for eid, entity in run.discovered_entities.items():
            if eid == "ENT-001":
                continue
            assert "source" in entity

    def test_relationship_has_source(self, orchestrator):
        """Every relationship in the graph has a source."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=2, max_nodes=10))
        for _source_id, edges in run.graph.items():
            for edge in edges:
                assert "source" in edge

    def test_lead_has_evidence_sources(self, orchestrator):
        """Every lead has evidence sources listed."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert lead.evidence_sources is not None
            assert isinstance(lead.evidence_sources, list)

    def test_lead_has_reason(self, orchestrator):
        """Every lead has a reason explaining why it was generated."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert lead.reason != ""


# ─── 10. Classification ───


class TestClassification:
    def test_config_has_classification(self, default_config):
        """Config has a default classification level."""
        assert default_config.user_classification == "PUBLIC"

    def test_police_config_has_higher_classification(self, police_config):
        """Police config has law enforcement classification."""
        assert police_config.user_classification == "LAW_ENFORCEMENT"

    def test_classification_access_control(self, router):
        """Police database requires law enforcement classification."""
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="PERSON",
            entity_value="John Doe", source_name="police_database",
            relationship_type="linked_to_case", priority=0.5, depth=0,
        )
        # Investigator cannot access
        result = router.execute(task, DiscoveryConfig(user_role="investigator"))
        assert task.status == TaskStatus.UNAUTHORIZED


# ─── 11. Jurisdiction ───


class TestJurisdiction:
    def test_config_has_jurisdiction(self, default_config):
        """Config can have a jurisdiction."""
        config = DiscoveryConfig(user_jurisdiction="ES")
        assert config.user_jurisdiction == "ES"

    def test_jurisdiction_in_config(self, default_config):
        """Config accepts jurisdiction parameter."""
        config = DiscoveryConfig(user_jurisdiction="UK")
        assert config.user_jurisdiction == "UK"

    def test_jurisdiction_null_by_default(self, default_config):
        """Jurisdiction is null by default."""
        assert default_config.user_jurisdiction is None


# ─── 12. Authorization ───


class TestAuthorization:
    def test_investigator_cannot_access_police_database(self, orchestrator):
        """Investigator role cannot access police database."""
        config = DiscoveryConfig(user_role="investigator", max_depth=3, max_nodes=20)
        run = orchestrator.run("ENT-001", "PERSON", "John Doe", config)
        # No police_database tasks should complete
        police_tasks = [t for t in run.tasks if t.source_name == "police_database"]
        for task in police_tasks:
            assert task.status in (TaskStatus.UNAUTHORIZED, TaskStatus.SKIPPED, TaskStatus.PENDING)

    def test_police_officer_can_access_police_database(self, orchestrator):
        """Police officer role can access police database."""
        config = DiscoveryConfig(user_role="police_officer", max_depth=3, max_nodes=20)
        run = orchestrator.run("ENT-001", "PERSON", "John Doe", config)
        police_tasks = [t for t in run.tasks if t.source_name == "police_database"]
        # At least the task should not be unauthorized
        for task in police_tasks:
            assert task.status != TaskStatus.UNAUTHORIZED

    def test_public_sources_available_to_all(self, orchestrator):
        """Public sources (DNS, CT logs) available to all roles."""
        config = DiscoveryConfig(user_role="investigator", max_depth=2, max_nodes=10)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        dns_tasks = [t for t in run.tasks if t.source_name == "dns_resolver"]
        assert len(dns_tasks) > 0
        for task in dns_tasks:
            assert task.status != TaskStatus.UNAUTHORIZED

    def test_misp_requires_auth(self, default_config):
        """MISP feed requires authentication."""
        from services.unknown_fraud_discovery import DEFAULT_RESTRICTIONS
        assert DEFAULT_RESTRICTIONS["misp_feed"].auth_required is True


# ─── 13. Campaign Candidates ───


class TestCampaignCandidates:
    def test_detect_campaign_candidate(self, campaign_detector):
        """Detector finds a cluster with enough entities and relationships."""
        entities = {
            "E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
            "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com"},
            "E3": {"id": "E3", "entity_type": "IP", "normalized_value": "1.2.3.4"},
            "E4": {"id": "E4", "entity_type": "CERTIFICATE", "normalized_value": "cert1"},
        }
        relationships = [
            {"source_entity_id": "E1", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E2", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E1", "target_entity_id": "E4", "relationship_type": "has_certificate", "certainty": "OBSERVED", "source": "ct"},
            {"source_entity_id": "E2", "target_entity_id": "E4", "relationship_type": "has_certificate", "certainty": "OBSERVED", "source": "ct"},
        ]
        candidates = campaign_detector.detect("RUN-1", entities, relationships)
        assert len(candidates) >= 1
        assert candidates[0].status == CampaignCandidateStatus.DRAFT

    def test_small_cluster_not_candidate(self, campaign_detector):
        """Clusters with <3 entities are not candidates."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
                     "E2": {"id": "E2", "entity_type": "IP", "normalized_value": "1.2.3.4"}}
        relationships = [{"source_entity_id": "E1", "target_entity_id": "E2", "relationship_type": "r", "certainty": "O", "source": "s"}]
        candidates = campaign_detector.detect("RUN-1", entities, relationships)
        assert len(candidates) == 0

    def test_candidate_is_draft_not_confirmed(self, campaign_detector):
        """Campaign candidates start as DRAFT, not confirmed."""
        entities = {f"E{i}": {"id": f"E{i}", "entity_type": "DOMAIN", "normalized_value": f"d{i}.com"} for i in range(5)}
        relationships = [
            {"source_entity_id": f"E{i}", "target_entity_id": f"E{j}", "relationship_type": "r", "certainty": "O", "source": "s"}
            for i in range(5) for j in range(i + 1, 5)
        ]
        candidates = campaign_detector.detect("RUN-1", entities, relationships)
        for c in candidates:
            assert c.status == CampaignCandidateStatus.DRAFT

    def test_promotion_requires_under_review(self, campaign_detector):
        """Campaign can only be promoted from UNDER_REVIEW status."""
        from services.unknown_fraud_discovery import CampaignCandidate
        candidate = CampaignCandidate(
            id="CC-1", run_id="R1", entity_ids=["E1", "E2", "E3"],
            entity_types=["DOMAIN"], relationship_count=3, confidence=0.9,
        )
        assert campaign_detector.can_promote(candidate) is False  # Still DRAFT
        candidate.status = CampaignCandidateStatus.UNDER_REVIEW
        assert campaign_detector.can_promote(candidate) is True

    def test_promotion_requires_min_confidence(self, campaign_detector):
        """Promotion requires minimum confidence threshold."""
        from services.unknown_fraud_discovery import CampaignCandidate
        candidate = CampaignCandidate(
            id="CC-1", run_id="R1", entity_ids=["E1", "E2", "E3"],
            entity_types=["DOMAIN"], relationship_count=3, confidence=0.5,
            status=CampaignCandidateStatus.UNDER_REVIEW,
        )
        assert campaign_detector.can_promote(candidate) is False


# ─── 14. Anomaly Detection ───


class TestAnomalyDetection:
    def test_infrastructure_concentration(self, anomaly_detector):
        """Detects when many domains resolve to same IP."""
        entities = {f"E{i}": {"id": f"E{i}", "entity_type": "DOMAIN", "normalized_value": f"d{i}.com"} for i in range(5)}
        entities["IP1"] = {"id": "IP1", "entity_type": "IP", "normalized_value": "1.2.3.4"}
        relationships = [
            {"source_entity_id": f"E{i}", "target_entity_id": "IP1", "relationship_type": "resolves_to", "certainty": "O", "source": "dns"}
            for i in range(5)
        ]
        anomalies = anomaly_detector.detect(entities, relationships)
        infra_anomalies = [a for a in anomalies if a["type"] == "infrastructure_concentration"]
        assert len(infra_anomalies) >= 1
        assert infra_anomalies[0]["severity"] == "HIGH"  # 5 domains

    def test_certificate_reuse(self, anomaly_detector):
        """Detects when certificate is shared by multiple domains."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
                     "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com"},
                     "C1": {"id": "C1", "entity_type": "CERTIFICATE", "normalized_value": "cert1"}}
        relationships = [
            {"source_entity_id": "E1", "target_entity_id": "C1", "relationship_type": "has_certificate", "certainty": "O", "source": "ct"},
            {"source_entity_id": "E2", "target_entity_id": "C1", "relationship_type": "has_certificate", "certainty": "O", "source": "ct"},
        ]
        anomalies = anomaly_detector.detect(entities, relationships)
        cert_anomalies = [a for a in anomalies if a["type"] == "certificate_reuse"]
        assert len(cert_anomalies) >= 1

    def test_repeated_contact_identifier(self, anomaly_detector):
        """Detects when same email/phone appears in multiple entities."""
        entities = {"E1": {"id": "E1", "entity_type": "EMAIL", "normalized_value": "test@example.com"},
                     "E2": {"id": "E2", "entity_type": "EMAIL", "normalized_value": "test@example.com"}}
        anomalies = anomaly_detector.detect(entities, [])
        contact_anomalies = [a for a in anomalies if a["type"] == "repeated_contact_identifier"]
        assert len(contact_anomalies) >= 1

    def test_cross_border_activity(self, anomaly_detector):
        """Detects when entities span multiple jurisdictions."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com", "jurisdiction": "ES"},
                     "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com", "jurisdiction": "UK"}}
        anomalies = anomaly_detector.detect(entities, [])
        cross_border = [a for a in anomalies if a["type"] == "cross_border_activity"]
        assert len(cross_border) >= 1

    def test_no_anomaly_in_clean_data(self, anomaly_detector):
        """No anomalies in a simple, clean dataset."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"}}
        anomalies = anomaly_detector.detect(entities, [])
        assert len(anomalies) == 0


# ─── 15. Blind-Spot Reporting ───


class TestBlindSpotReporting:
    def test_coverage_reports_checked_sources(self, coverage_reporter):
        """Coverage report shows which sources were checked."""
        from services.unknown_fraud_discovery import DiscoveryTask
        tasks = [DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="r", priority=0.9, depth=0,
            status=TaskStatus.COMPLETED,
        )]
        coverage = coverage_reporter.report("R1", tasks, "DOMAIN")
        assert "dns_resolver" in coverage.checked

    def test_coverage_reports_not_checked(self, coverage_reporter):
        """Coverage report shows sources not checked."""
        coverage = coverage_reporter.report("R1", [], "DOMAIN")
        assert len(coverage.not_checked) > 0
        assert len(coverage.checked) == 0

    def test_coverage_reports_authorization_required(self, coverage_reporter):
        """Coverage report shows authorization-required sources."""
        from services.unknown_fraud_discovery import DiscoveryTask
        tasks = [DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="PERSON",
            entity_value="John", source_name="police_database",
            relationship_type="r", priority=0.5, depth=0,
            status=TaskStatus.UNAUTHORIZED,
        )]
        coverage = coverage_reporter.report("R1", tasks, "PERSON")
        assert "police_database" in coverage.authorization_required

    def test_coverage_never_reports_absolute_no_match(self, coverage_reporter):
        """Coverage report warns when sources were not checked."""
        coverage = coverage_reporter.report("R1", [], "DOMAIN")
        report = coverage_reporter.format_report(coverage)
        assert "not checked" in report.lower() or "not_check" in report.lower()


# ─── 16. Monitoring ───


class TestMonitoring:
    def test_monitoring_rule_created_for_high_priority(self, monitoring_manager):
        """Monitoring rules created for high-priority leads."""
        from services.unknown_fraud_discovery import InvestigationLead
        leads = [InvestigationLead(
            id="L1", run_id="R1", seed_entity_id="S1", seed_entity_value="seed",
            discovered_entity_id="E1", discovered_entity_value="test.com",
            discovered_entity_type="DOMAIN", priority=0.8, confidence=0.7,
        )]
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "test.com"}}
        rules = monitoring_manager.create_rules("R1", entities, leads, DiscoveryConfig(enable_monitoring=True))
        assert len(rules) >= 1
        assert rules[0].entity_id == "E1"

    def test_monitoring_not_created_for_low_priority(self, monitoring_manager):
        """No monitoring rules for low-priority leads."""
        from services.unknown_fraud_discovery import InvestigationLead
        leads = [InvestigationLead(
            id="L1", run_id="R1", seed_entity_id="S1", seed_entity_value="seed",
            discovered_entity_id="E1", discovered_entity_value="test.com",
            discovered_entity_type="DOMAIN", priority=0.3, confidence=0.3,
        )]
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "test.com"}}
        rules = monitoring_manager.create_rules("R1", entities, leads, DiscoveryConfig(enable_monitoring=True))
        assert len(rules) == 0

    def test_monitoring_disabled(self, monitoring_manager):
        """No monitoring rules when monitoring is disabled."""
        from services.unknown_fraud_discovery import InvestigationLead
        leads = [InvestigationLead(
            id="L1", run_id="R1", seed_entity_id="S1", seed_entity_value="seed",
            discovered_entity_id="E1", discovered_entity_value="test.com",
            discovered_entity_type="DOMAIN", priority=0.9, confidence=0.8,
        )]
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "test.com"}}
        rules = monitoring_manager.create_rules("R1", entities, leads, DiscoveryConfig(enable_monitoring=False))
        assert len(rules) == 0

    def test_monitoring_ttl_based_on_priority(self, monitoring_manager):
        """TTL varies based on lead priority."""
        from services.unknown_fraud_discovery import InvestigationLead
        high = InvestigationLead(
            id="L1", run_id="R1", seed_entity_id="S1", seed_entity_value="seed",
            discovered_entity_id="E1", discovered_entity_value="test.com",
            discovered_entity_type="DOMAIN", priority=0.9, confidence=0.8,
        )
        medium = InvestigationLead(
            id="L2", run_id="R1", seed_entity_id="S1", seed_entity_value="seed",
            discovered_entity_id="E2", discovered_entity_value="test2.com",
            discovered_entity_type="DOMAIN", priority=0.72, confidence=0.5,
        )
        entities = {
            "E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "test.com"},
            "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "test2.com"},
        }
        rules = monitoring_manager.create_rules("R1", entities, [high, medium], DiscoveryConfig(enable_monitoring=True))
        high_rule = next(r for r in rules if r.entity_id == "E1")
        medium_rule = next(r for r in rules if r.entity_id == "E2")
        assert high_rule.ttl == MonitoringTTL.LONG
        assert medium_rule.ttl == MonitoringTTL.MEDIUM


# ─── 17. Prompt Injection from External Content ───


class TestPromptInjection:
    def test_external_content_is_untrusted(self, orchestrator):
        """External content in discovery results is marked with source, not treated as authority."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=2, max_nodes=10))
        for eid, entity in run.discovered_entities.items():
            if eid == "ENT-001":
                continue
            # External entities have source provenance — they're data, not instructions
            assert "source" in entity
            assert entity["source"] != "GFIN_INTERNAL"  # Not treated as internal authority

    def test_hypothesis_not_stored_as_fact(self, orchestrator):
        """Hypothesized relationships are marked as HYPOTHESIZED, not OBSERVED."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for hyp in run.hypotheses:
            assert hyp.certainty == RelationshipCertainty.HYPOTHESIZED
            assert hyp.confidence < 1.0  # Never 100% confident

    def test_lead_explains_what_is_inferred(self, orchestrator):
        """Leads distinguish between observed and inferred evidence."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            # Lead reason should explain the evidence
            assert lead.reason != ""
            assert "source" in lead.reason.lower() or "discover" in lead.reason.lower()


# ─── 18. Data Poisoning ───


class TestDataPoisoning:
    def test_single_untrusted_source_capped(self, poisoning_guard):
        """Single untrusted source cannot establish high confidence."""
        is_valid, reason = poisoning_guard.validate(
            ["untrusted_source"], confidence=0.8,
            source_reliabilities={"untrusted_source": 0.5},
        )
        assert is_valid is False
        assert "untrusted" in reason.lower() or "cannot" in reason.lower()

    def test_multiple_sources_required_for_high_confidence(self, poisoning_guard):
        """High confidence requires multiple independent sources."""
        is_valid, reason = poisoning_guard.validate(
            ["source1"], confidence=0.85,
            source_reliabilities={"source1": 0.9},
        )
        assert is_valid is False
        assert "independent" in reason.lower() or "sources" in reason.lower()

    def test_multiple_trusted_sources_valid(self, poisoning_guard):
        """Multiple trusted sources can establish high confidence."""
        is_valid, _reason = poisoning_guard.validate(
            ["source1", "source2"], confidence=0.85,
            source_reliabilities={"source1": 0.9, "source2": 0.85},
        )
        assert is_valid is True


# ─── 19. Unauthorized Source Access ───


class TestUnauthorizedSourceAccess:
    def test_investigator_blocked_from_police_db(self, orchestrator):
        """Investigator cannot access police database."""
        config = DiscoveryConfig(user_role="investigator", max_depth=3, max_nodes=20)
        run = orchestrator.run("ENT-001", "EMAIL", "test@example.com", config)
        for task in run.tasks:
            if task.source_name == "police_database":
                assert task.status != TaskStatus.COMPLETED

    def test_public_sources_no_auth_required(self, orchestrator):
        """Public sources don't require auth."""
        config = DiscoveryConfig(user_role="investigator", max_depth=1, max_nodes=5)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        for task in run.tasks:
            if task.source_name in ("dns_resolver", "certificate_transparency", "whois_rdap"):
                assert task.status != TaskStatus.UNAUTHORIZED

    def test_coverage_shows_authorization_required(self, orchestrator):
        """Coverage report shows authorization-required sources."""
        config = DiscoveryConfig(user_role="investigator", max_depth=3, max_nodes=20)
        run = orchestrator.run("ENT-001", "EMAIL", "test@example.com", config)
        if run.coverage:
            assert isinstance(run.coverage.authorization_required, list)


# ─── 20. Resource Exhaustion ───


class TestResourceExhaustion:
    def test_max_nodes_prevents_explosion(self, orchestrator):
        """Max nodes prevents uncontrolled graph expansion."""
        config = DiscoveryConfig(max_depth=10, max_nodes=3)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        assert len(run.discovered_entities) <= 3

    def test_max_tasks_prevents_explosion(self, orchestrator):
        """Max tasks prevents uncontrolled task generation."""
        config = DiscoveryConfig(max_depth=10, max_nodes=100, max_tasks=5)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        assert run.total_tasks <= 5

    def test_max_depth_prevents_infinite_recursion(self, orchestrator):
        """Max depth prevents infinite recursion."""
        config = DiscoveryConfig(max_depth=1, max_nodes=100, max_tasks=100)
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", config)
        # With depth=1, only direct neighbors should be explored
        for entity in run.discovered_entities.values():
            assert entity.get("depth", 0) <= 1


# ─── 21. Lead Generation ───


class TestLeadGeneration:
    def test_leads_generated_from_discovery(self, orchestrator):
        """Leads are generated from discovery results."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        assert len(run.leads) > 0

    def test_lead_has_seed_reference(self, orchestrator):
        """Each lead references the seed entity."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert lead.seed_entity_id == "ENT-001"

    def test_lead_has_confidence_and_priority(self, orchestrator):
        """Each lead has both confidence and priority scores."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert 0.0 <= lead.confidence <= 1.0
            assert 0.0 <= lead.priority <= 1.0

    def test_lead_has_relationship_path(self, orchestrator):
        """Each lead has a relationship path from seed to discovered entity."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert isinstance(lead.relationship_path, list)

    def test_lead_has_explanation(self, orchestrator):
        """Each lead has a human-readable explanation."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        for lead in run.leads:
            assert lead.reason != ""
            # Reason should mention sources or discovery
            assert len(lead.reason) > 10


# ─── 22. Relationship Hypotheses ───


class TestRelationshipHypotheses:
    def test_observed_vs_hypothesized_separation(self, orchestrator):
        """Observed and hypothesized relationships are distinct."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        # All graph relationships should have certainty labels
        for _source_id, edges in run.graph.items():
            for edge in edges:
                assert edge["certainty"] in (
                    RelationshipCertainty.OBSERVED.value,
                    RelationshipCertainty.DERIVED.value,
                    RelationshipCertainty.HYPOTHESIZED.value,
                )

    def test_hypothesis_has_evidence(self, hypothesizer):
        """Hypothesized relationships include evidence."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
                     "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com"},
                     "E3": {"id": "E3", "entity_type": "IP", "normalized_value": "1.2.3.4"}}
        relationships = [
            {"source_entity_id": "E1", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E2", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
        ]
        hypotheses = hypothesizer.hypothesize("R1", entities, relationships)
        for h in hypotheses:
            assert len(h.evidence) > 0
            assert h.certainty == RelationshipCertainty.HYPOTHESIZED

    def test_hypothesis_confidence_below_1(self, hypothesizer):
        """Hypothesized relationships never have confidence = 1.0."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
                     "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com"},
                     "E3": {"id": "E3", "entity_type": "IP", "normalized_value": "1.2.3.4"}}
        relationships = [
            {"source_entity_id": "E1", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E2", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
        ]
        hypotheses = hypothesizer.hypothesize("R1", entities, relationships)
        for h in hypotheses:
            assert h.confidence < 1.0

    def test_no_hypothesis_for_already_observed(self, hypothesizer):
        """No hypothesis generated when relationship already observed."""
        entities = {"E1": {"id": "E1", "entity_type": "DOMAIN", "normalized_value": "a.com"},
                     "E2": {"id": "E2", "entity_type": "DOMAIN", "normalized_value": "b.com"},
                     "E3": {"id": "E3", "entity_type": "IP", "normalized_value": "1.2.3.4"}}
        relationships = [
            {"source_entity_id": "E1", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E2", "target_entity_id": "E3", "relationship_type": "resolves_to", "certainty": "OBSERVED", "source": "dns"},
            {"source_entity_id": "E1", "target_entity_id": "E2", "relationship_type": "potentially_related_to", "certainty": "OBSERVED", "source": "direct"},
        ]
        hypotheses = hypothesizer.hypothesize("R1", entities, relationships)
        # The E1↔E2 relationship is already observed, so no new hypothesis for it
        for h in hypotheses:
            assert not (h.source_entity_id == "E1" and h.target_entity_id == "E2")


# ─── 23. Coverage Reporting ───


class TestCoverageReporting:
    def test_coverage_in_run(self, orchestrator):
        """Coverage report is included in the run."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        assert run.coverage is not None

    def test_coverage_has_checked_sources(self, orchestrator):
        """Coverage report has checked sources list."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=3, max_nodes=20))
        assert isinstance(run.coverage.checked, list)

    def test_coverage_has_not_checked_sources(self, orchestrator):
        """Coverage report has not_checked sources list."""
        run = orchestrator.run("ENT-001", "DOMAIN", "test.example", DiscoveryConfig(max_depth=1, max_nodes=5))
        assert isinstance(run.coverage.not_checked, list)


# ─── 24. Source Capability/Routing ───


class TestSourceRouting:
    def test_source_router_routes_to_correct_source(self, router):
        """Router routes to the correct source based on task."""
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert result.source_name == "dns_resolver"
        assert task.status == TaskStatus.COMPLETED

    def test_source_returns_entities_and_relationships(self, router):
        """Source returns discovered entities and relationships."""
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert len(result.discovered_entities) > 0
        assert len(result.discovered_relationships) > 0

    def test_source_returns_reliability(self, router):
        """Source returns its reliability score."""
        from services.unknown_fraud_discovery import DiscoveryTask
        task = DiscoveryTask(
            id="T1", run_id="R1", entity_id="E1", entity_type="DOMAIN",
            entity_value="test.com", source_name="dns_resolver",
            relationship_type="resolves_to", priority=0.9, depth=0,
        )
        result = router.execute(task, DiscoveryConfig())
        assert 0.0 < result.source_reliability <= 1.0

    def test_different_sources_for_different_types(self, planner):
        """Different entity types route to different sources."""
        domain_tasks = planner.plan("E1", "DOMAIN", "test.com", 0, DiscoveryConfig())
        ip_tasks = planner.plan("E2", "IP", "1.2.3.4", 0, DiscoveryConfig())
        domain_sources = {t.source_name for t in domain_tasks}
        ip_sources = {t.source_name for t in ip_tasks}
        # They should have different source sets (DNS for domains, IP intel for IPs)
        assert domain_sources != ip_sources
