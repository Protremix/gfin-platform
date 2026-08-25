"""Comprehensive tests for Module 07 — Search Platform.

Per Master Spec §11 (Search Platform):
Support: exact, normalized, fuzzy, semantic, entity, graph-assisted,
campaign, infrastructure, and report search.
All search results must respect authorization and data-sharing policies.

Test categories:
1. Exact search
2. Normalized search
3. Fuzzy search (Levenshtein)
4. Entity search (typed)
5. Graph-assisted search
6. Campaign search
7. Infrastructure search
8. Report search
9. Authorization enforcement (fail closed, classification, org isolation)
10. Pagination
11. Indexing (add, delete)
12. Metrics
13. Levenshtein distance (unit)
14. Negative/fail-safe tests
15. Integration
"""

import pytest
from datetime import datetime

from services.search_platform import (
    EnhancedSearchService,
    SearchQueryV2,
    SearchType,
    SearchResultV2,
    SearchResponseV2,
    AuthorizationContext,
    DataSharingPolicy,
    PolicyDecision,
    check_sharing_policy,
    levenshtein,
    normalize_query,
    tokenize,
    can_access,
)
from schemas.base import BaseEntity, Classification, BaseReport, utc_now
from schemas.extended import BaseCampaign
from schemas.enums import DataClassification, EntityType, Confidence


# ─── Fixtures ───

@pytest.fixture
def search_svc():
    return EnhancedSearchService()


@pytest.fixture
def auth_restricted():
    return AuthorizationContext(
        user_id="investigator1",
        user_classification_level=DataClassification.RESTRICTED,
        user_role="investigator",
        organization_id="ORG-001",
        purpose="fraud_investigation",
    )


@pytest.fixture
def auth_public():
    return AuthorizationContext(
        user_id="citizen1",
        user_classification_level=DataClassification.PUBLIC,
        user_role="citizen",
        purpose="fraud_investigation",
    )


@pytest.fixture
def auth_admin():
    return AuthorizationContext(
        user_id="admin1",
        user_classification_level=DataClassification.HIGHLY_RESTRICTED,
        user_role="admin",
        purpose="internal_review",
    )


def make_entity(entity_type, normalized_value, raw_values=None, classification_level=DataClassification.PUBLIC, org_id=None):
    """Helper to create a test entity."""
    e = BaseEntity(
        entity_type=entity_type,
        normalized_value=normalized_value,
        raw_values=raw_values or [normalized_value],
        classification=Classification(classification=classification_level),
    )
    if org_id:
        e.organization_id = org_id
    return e


def make_campaign(campaign_id, name, description="", status="ACTIVE"):
    """Helper to create a test campaign."""
    return BaseCampaign(
        id=campaign_id,
        name=name,
        fraud_type=description,
        campaign_status=status,
    )


def make_report(report_id, description, category="PHISHING", status="UNVERIFIED"):
    """Helper to create a test report."""
    return BaseReport(
        id=report_id,
        description=description,
        category=category,
        status=status,
    )


# ═══════════════════════════════════════════════
# LEVENSHTEIN DISTANCE
# ═══════════════════════════════════════════════

class TestLevenshtein:
    """Test Levenshtein distance computation."""

    def test_identical_strings(self):
        assert levenshtein("hello", "hello") == 0

    def test_single_substitution(self):
        assert levenshtein("hello", "hallo") == 1

    def test_single_deletion(self):
        assert levenshtein("hello", "hell") == 1

    def test_single_insertion(self):
        assert levenshtein("hell", "hello") == 1

    def test_completely_different(self):
        assert levenshtein("abc", "xyz") == 3

    def test_empty_string(self):
        assert levenshtein("", "abc") == 3
        assert levenshtein("abc", "") == 3
        assert levenshtein("", "") == 0

    def test_max_distance_early_exit(self):
        # Should early-exit when distance exceeds max
        result = levenshtein("hello world", "xyz", max_dist=2)
        assert result > 2  # Exceeded max_dist

    def test_max_distance_within(self):
        result = levenshtein("hello", "hallo", max_dist=2)
        assert result == 1


# ═══════════════════════════════════════════════
# NORMALIZATION
# ═══════════════════════════════════════════════

class TestNormalization:
    """Test query normalization and tokenization."""

    def test_normalize_lowercase(self):
        assert normalize_query("HELLO") == "hello"

    def test_normalize_whitespace(self):
        assert normalize_query("  hello   world  ") == "hello world"

    def test_normalize_punctuation(self):
        assert normalize_query("hello, world!") == "hello world"

    def test_tokenize(self):
        tokens = tokenize("John Doe phishing-scam")
        assert "john" in tokens
        assert "doe" in tokens

    def test_tokenize_empty(self):
        assert tokenize("") == []


# ═══════════════════════════════════════════════
# EXACT SEARCH
# ═══════════════════════════════════════════════

class TestExactSearch:
    """Test exact match search."""

    def test_exact_match_normalized_value(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe", ["John Doe"])
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 1
        assert result.results[0].normalized_value == "john doe"
        assert result.results[0].score == 1.0

    def test_exact_match_raw_value(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe", ["John Doe", "JD"])
        search_svc.index_entity(e)

        q = SearchQueryV2(query="John Doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_exact_no_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="jane doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0

    def test_exact_case_sensitive_raw(self, search_svc, auth_restricted):
        """Exact search on raw_values should match exact case."""
        e = make_entity(EntityType.PERSON, "john doe", ["John Doe"])
        search_svc.index_entity(e)

        q = SearchQueryV2(query="John Doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total >= 1


# ═══════════════════════════════════════════════
# NORMALIZED SEARCH
# ═══════════════════════════════════════════════

class TestNormalizedSearch:
    """Test normalized search."""

    def test_normalized_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.DOMAIN, "evil.com")
        search_svc.index_entity(e)

        # Query with different case/whitespace should still match
        q = SearchQueryV2(query="  EVIL.COM  ", search_type=SearchType.NORMALIZED, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].normalized_value == "evil.com"

    def test_normalized_prefix_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.DOMAIN, "evil.com")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="evil", search_type=SearchType.NORMALIZED, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].score < 1.0  # Partial match

    def test_normalized_no_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.DOMAIN, "evil.com")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="good.com", search_type=SearchType.NORMALIZED, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0


# ═══════════════════════════════════════════════
# FUZZY SEARCH
# ═══════════════════════════════════════════════

class TestFuzzySearch:
    """Test fuzzy search with Levenshtein distance."""

    def test_fuzzy_exact_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].score == 1.0

    def test_fuzzy_one_char_diff(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="jon doe", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].normalized_value == "john doe"
        assert result.results[0].score < 1.0

    def test_fuzzy_two_char_diff(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="jn doe", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=3)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_fuzzy_beyond_max_distance(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="xyzabc", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=1)
        result = search_svc.search(q)

        assert result.total == 0

    def test_fuzzy_token_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.DOMAIN, "evil.com", ["evil.com", "phishing-site.com"])
        search_svc.index_entity(e)

        q = SearchQueryV2(query="phishing", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_fuzzy_explain(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="jon doe", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2, explain=True)
        result = search_svc.search(q)

        assert result.total >= 1
        assert "match_type" in result.results[0].explanation


# ═══════════════════════════════════════════════
# ENTITY SEARCH
# ═══════════════════════════════════════════════

class TestEntitySearch:
    """Test typed entity search."""

    def test_entity_search_by_type(self, search_svc, auth_restricted):
        e1 = make_entity(EntityType.PERSON, "john doe")
        e2 = make_entity(EntityType.PHONE, "+34612345678")
        search_svc.index_entity(e1)
        search_svc.index_entity(e2)

        q = SearchQueryV2(query="john", search_type=SearchType.ENTITY, entity_type="PERSON", authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert all(r.entity_type == "PERSON" for r in result.results)

    def test_entity_search_wrong_type(self, search_svc, auth_restricted):
        e1 = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e1)

        q = SearchQueryV2(query="john", search_type=SearchType.ENTITY, entity_type="PHONE", authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0

    def test_entity_search_partial_match(self, search_svc, auth_restricted):
        e = make_entity(EntityType.EMAIL, "scammer@evil.com")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="scammer", search_type=SearchType.ENTITY, entity_type="EMAIL", authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1


# ═══════════════════════════════════════════════
# GRAPH-ASSISTED SEARCH
# ═══════════════════════════════════════════════

class TestGraphAssistedSearch:
    """Test graph-assisted search."""

    def test_graph_search_without_graph(self, search_svc, auth_restricted):
        """Graph-assisted search should still find initial matches without a graph store."""
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.GRAPH_ASSISTED, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_graph_search_finds_related(self, search_svc, auth_restricted):
        """Graph-assisted search should expand results via graph."""
        from common.graph import AdjacencyListGraph, GraphNode, GraphEdge

        graph = AdjacencyListGraph()
        e1 = make_entity(EntityType.PERSON, "john doe")
        e2 = make_entity(EntityType.PHONE, "+34612345678")
        search_svc.index_entity(e1)
        search_svc.index_entity(e2)
        search_svc._graph = graph

        # Add graph nodes and edge
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(graph.add_node(GraphNode(entity_id=e1.id, entity_type="PERSON", label="john doe")))
        loop.run_until_complete(graph.add_node(GraphNode(entity_id=e2.id, entity_type="PHONE", label="+34612345678")))
        loop.run_until_complete(graph.add_edge(GraphEdge(
            relationship_id="REL-001",
            from_entity_id=e1.id,
            to_entity_id=e2.id,
            relationship_type="OWNS",
        )))
        loop.close()

        q = SearchQueryV2(query="john doe", search_type=SearchType.GRAPH_ASSISTED, authorization=auth_restricted, graph_depth=2)
        result = search_svc.search(q)

        # Should find john doe + related phone
        assert result.total >= 2


# ═══════════════════════════════════════════════
# CAMPAIGN SEARCH
# ═══════════════════════════════════════════════

class TestCampaignSearch:
    """Test campaign search."""

    def test_campaign_search_by_name(self, search_svc, auth_restricted):
        c = make_campaign("CMP-001", "Phishing Campaign 2026", description="Mass phishing")
        search_svc.index_campaign(c)

        q = SearchQueryV2(query="phishing", search_type=SearchType.CAMPAIGN, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].entity_id == "CMP-001"

    def test_campaign_search_by_description(self, search_svc, auth_restricted):
        c = make_campaign("CMP-002", "Campaign X", description="Targeted phishing against banks")
        search_svc.index_campaign(c)

        q = SearchQueryV2(query="banks", search_type=SearchType.CAMPAIGN, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_campaign_no_match(self, search_svc, auth_restricted):
        c = make_campaign("CMP-003", "Phishing")
        search_svc.index_campaign(c)

        q = SearchQueryV2(query="ransomware", search_type=SearchType.CAMPAIGN, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0


# ═══════════════════════════════════════════════
# INFRASTRUCTURE SEARCH
# ═══════════════════════════════════════════════

class TestInfrastructureSearch:
    """Test infrastructure search."""

    def test_infrastructure_search_domain(self, search_svc, auth_restricted):
        e = make_entity(EntityType.DOMAIN, "evil.com")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="evil", search_type=SearchType.INFRASTRUCTURE, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].explanation.get("entity_type") == "DOMAIN"

    def test_infrastructure_search_ip(self, search_svc, auth_restricted):
        e = make_entity(EntityType.IP, "192.168.1.1")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="192.168", search_type=SearchType.INFRASTRUCTURE, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_infrastructure_excludes_non_infra(self, search_svc, auth_restricted):
        e1 = make_entity(EntityType.PERSON, "evil person")
        e2 = make_entity(EntityType.DOMAIN, "evil.com")
        search_svc.index_entity(e1)
        search_svc.index_entity(e2)

        q = SearchQueryV2(query="evil", search_type=SearchType.INFRASTRUCTURE, authorization=auth_restricted)
        result = search_svc.search(q)

        # Should only find the domain, not the person
        assert all(r.explanation.get("entity_type") != "PERSON" for r in result.results)


# ═══════════════════════════════════════════════
# REPORT SEARCH
# ═══════════════════════════════════════════════

class TestReportSearch:
    """Test report search."""

    def test_report_search_by_category(self, search_svc, auth_restricted):
        r = make_report("RPT-001", "Fake investment scam", category="INVESTMENT_FRAUD")
        search_svc.index_report(r)

        q = SearchQueryV2(query="investment", search_type=SearchType.REPORT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1
        assert result.results[0].entity_id == "RPT-001"

    def test_report_search_by_description(self, search_svc, auth_restricted):
        r = make_report("RPT-002", "Nigerian prince email scam", category="PHISHING")
        search_svc.index_report(r)

        q = SearchQueryV2(query="prince", search_type=SearchType.REPORT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total >= 1

    def test_report_no_match(self, search_svc, auth_restricted):
        r = make_report("RPT-003", "Phishing", category="PHISHING")
        search_svc.index_report(r)

        q = SearchQueryV2(query="ransomware", search_type=SearchType.REPORT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0


# ═══════════════════════════════════════════════
# AUTHORIZATION ENFORCEMENT
# ═══════════════════════════════════════════════

class TestAuthorization:
    """Test authorization and data-sharing policy enforcement."""

    def test_fail_closed_no_auth(self, search_svc):
        """Search without authorization context should return 0 results (fail closed)."""
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT)
        result = search_svc.search(q)

        assert result.total == 0
        assert result.authorized_results == 0
        assert result.blocked_results == 0  # No auth = no search at all

    def test_public_user_blocked_from_restricted(self, search_svc, auth_public):
        """PUBLIC user should not see RESTRICTED entities."""
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_public)
        result = search_svc.search(q)

        assert result.authorized_results == 0
        assert result.blocked_results == 1

    def test_restricted_user_sees_restricted(self, search_svc, auth_restricted):
        """RESTRICTED user should see RESTRICTED entities."""
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.authorized_results == 1
        assert result.blocked_results == 0

    def test_law_enforcement_requires_le(self, search_svc):
        """LAW_ENFORCEMENT classified entities require LE clearance."""
        e = make_entity(EntityType.PERSON, "suspect", classification_level=DataClassification.LAW_ENFORCEMENT)
        search_svc.index_entity(e)

        # RESTRICTED user blocked
        auth = AuthorizationContext(user_id="u1", user_classification_level=DataClassification.RESTRICTED, user_role="investigator", purpose="fraud_investigation")
        q = SearchQueryV2(query="suspect", search_type=SearchType.FUZZY, authorization=auth, fuzzy_distance=3)
        result = search_svc.search(q)
        assert result.blocked_results >= 1

        # LE user allowed
        auth_le = AuthorizationContext(user_id="u2", user_classification_level=DataClassification.LAW_ENFORCEMENT, user_role="investigator", purpose="law_enforcement")
        q2 = SearchQueryV2(query="suspect", search_type=SearchType.FUZZY, authorization=auth_le, fuzzy_distance=3)
        result2 = search_svc.search(q2)
        assert result2.authorized_results >= 1

    def test_admin_sees_all(self, search_svc, auth_admin):
        """Admin with HIGHLY_RESTRICTED should see everything."""
        e1 = make_entity(EntityType.PERSON, "john", classification_level=DataClassification.PUBLIC)
        e2 = make_entity(EntityType.PERSON, "jane", classification_level=DataClassification.HIGHLY_RESTRICTED)
        search_svc.index_entity(e1)
        search_svc.index_entity(e2)

        q = SearchQueryV2(query="ja", search_type=SearchType.FUZZY, authorization=auth_admin, fuzzy_distance=2)
        # auth_admin already has purpose="internal_review" from fixture
        result = search_svc.search(q)
        assert result.blocked_results == 0

    def test_organization_isolation(self, search_svc):
        """Entities from different organizations should be isolated."""
        e = make_entity(EntityType.PERSON, "john doe", org_id="ORG-OTHER")
        search_svc.index_entity(e)

        auth = AuthorizationContext(
            user_id="u1",
            user_classification_level=DataClassification.RESTRICTED,
            user_role="investigator",
            organization_id="ORG-MINE",
            purpose="fraud_investigation",
        )
        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth)
        result = search_svc.search(q)

        assert result.authorized_results == 0
        assert result.blocked_results >= 1

    def test_organization_isolation_admin_override(self, search_svc):
        """Admin should bypass organization isolation."""
        e = make_entity(EntityType.PERSON, "john doe", org_id="ORG-OTHER")
        search_svc.index_entity(e)

        auth = AuthorizationContext(
            user_id="admin1",
            user_classification_level=DataClassification.RESTRICTED,
            user_role="admin",
            organization_id="ORG-MINE",
            purpose="internal_review",
        )
        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth)
        result = search_svc.search(q)

        assert result.authorized_results == 1

    def test_blocked_results_do_not_leak(self, search_svc, auth_public):
        """Blocked results should not appear in results at all."""
        e = make_entity(EntityType.PERSON, "secret", classification_level=DataClassification.HIGHLY_RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="secret", search_type=SearchType.FUZZY, authorization=auth_public, fuzzy_distance=5)
        result = search_svc.search(q)

        # The entity should not be in results
        assert all("secret" not in r.normalized_value for r in result.results)
        # But blocked count should reflect it was filtered
        assert result.blocked_results >= 1


# ═══════════════════════════════════════════════
# PAGINATION
# ═══════════════════════════════════════════════

class TestPagination:
    """Test search result pagination."""

    def test_pagination_basic(self, search_svc, auth_restricted):
        for i in range(10):
            e = make_entity(EntityType.PERSON, f"person_{i}")
            search_svc.index_entity(e)

        q = SearchQueryV2(query="person", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=3, limit=5, offset=0)
        result = search_svc.search(q)

        assert len(result.results) == 5
        assert result.total >= 10
        assert result.has_more

    def test_pagination_offset(self, search_svc, auth_restricted):
        for i in range(10):
            e = make_entity(EntityType.PERSON, f"person_{i}")
            search_svc.index_entity(e)

        q = SearchQueryV2(query="person", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=3, limit=5, offset=5)
        result = search_svc.search(q)

        assert len(result.results) <= 5
        assert result.offset == 5

    def test_pagination_no_more(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted, limit=10, offset=0)
        result = search_svc.search(q)

        assert not result.has_more


# ═══════════════════════════════════════════════
# INDEXING
# ═══════════════════════════════════════════════

class TestIndexing:
    """Test entity indexing and deletion."""

    def test_index_entity(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total == 1

    def test_delete_index(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)
        assert search_svc.delete_index(e.id)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total == 0

    def test_delete_nonexistent(self, search_svc):
        assert not search_svc.delete_index("NONEXIST")

    def test_reindex_entity(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)
        # Re-index same entity (update)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total == 1  # Should not duplicate


# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════

class TestMetrics:
    """Test search service metrics."""

    def test_metrics_empty(self, search_svc):
        metrics = search_svc.get_metrics()
        assert metrics["total_entities"] == 0

    def test_metrics_after_indexing(self, search_svc):
        search_svc.index_entity(make_entity(EntityType.PERSON, "john"))
        search_svc.index_entity(make_entity(EntityType.DOMAIN, "evil.com"))
        search_svc.index_campaign(make_campaign("CMP-001", "Test"))
        search_svc.index_report(make_report("RPT-001", "Test"))

        metrics = search_svc.get_metrics()
        assert metrics["total_entities"] == 2
        assert metrics["total_campaigns"] == 1
        assert metrics["total_reports"] == 1
        assert metrics["entity_type_count"] == 2


# ═══════════════════════════════════════════════
# CAN_ACCESS FUNCTION
# ═══════════════════════════════════════════════

class TestCanAccess:
    """Test the can_access authorization function."""

    def test_public_entity_public_user(self):
        auth = AuthorizationContext(user_id="u1", user_classification_level=DataClassification.PUBLIC)
        can, reason = can_access(DataClassification.PUBLIC.value, None, None, auth)
        assert can

    def test_restricted_entity_public_user(self):
        auth = AuthorizationContext(user_id="u1", user_classification_level=DataClassification.PUBLIC)
        can, reason = can_access(DataClassification.RESTRICTED.value, None, None, auth)
        assert not can
        assert "Insufficient" in reason

    def test_missing_classification_fail_closed(self):
        auth = AuthorizationContext(user_id="u1", user_classification_level=DataClassification.PUBLIC)
        can, reason = can_access(None, None, None, auth)
        assert not can
        assert "Missing" in reason or "closed" in reason.lower()

    def test_organization_isolation(self):
        auth = AuthorizationContext(
            user_id="u1",
            user_classification_level=DataClassification.RESTRICTED,
            user_role="investigator",
            organization_id="ORG-MINE",
        )
        can, _ = can_access(DataClassification.PUBLIC.value, "ORG-OTHER", None, auth)
        assert not can

    def test_organization_admin_override(self):
        auth = AuthorizationContext(
            user_id="admin",
            user_classification_level=DataClassification.RESTRICTED,
            user_role="admin",
            organization_id="ORG-MINE",
        )
        can, _ = can_access(DataClassification.PUBLIC.value, "ORG-OTHER", None, auth)
        assert can


# ═══════════════════════════════════════════════
# SEMANTIC SEARCH (Layer B)
# ═══════════════════════════════════════════════

# ═══════════════════════════════════════════════
# DATA-SHARING POLICY ENFORCEMENT
# ═══════════════════════════════════════════════

class TestDataSharingPolicy:
    """Test data-sharing policy enforcement per Luna's guidance."""

    def test_no_purpose_denied(self, search_svc, auth_restricted):
        """Without purpose, data-sharing should be denied even for authorized users."""
        auth_restricted.purpose = None
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.authorized_results == 0
        assert result.blocked_results >= 1

    def test_approved_purpose_allowed(self, search_svc, auth_restricted):
        """With approved purpose, data-sharing should be allowed."""
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.authorized_results == 1
        assert result.blocked_results == 0

    def test_unapproved_purpose_denied(self, search_svc, auth_restricted):
        """With unapproved purpose, data-sharing should be denied."""
        auth_restricted.purpose = "marketing"
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.authorized_results == 0
        assert result.blocked_results >= 1

    def test_policy_audit_trail(self, search_svc, auth_restricted):
        """Policy decisions should be recorded in audit trail."""
        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        search_svc.search(q)

        audit = search_svc.get_policy_audit()
        assert len(audit) >= 1
        assert audit[0].decision == "ALLOWED"
        assert audit[0].policy_id == "DSP-DEFAULT"
        assert audit[0].requester == auth_restricted.user_id

    def test_custom_sharing_policy(self, search_svc, auth_restricted):
        """Custom policy with restricted jurisdictions should block cross-border."""
        policy = DataSharingPolicy(
            policy_id="DSP-EU",
            approved_purposes=["fraud_investigation"],
            allowed_jurisdictions=["ES", "FR", "DE"],
        )
        search_svc.set_sharing_policy(policy)

        e = make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED)
        e.jurisdiction = "US"  # Outside allowed jurisdictions
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.blocked_results >= 1

    def test_named_partner_restriction(self, search_svc, auth_restricted):
        """HIGHLY_RESTRICTED data should require named partner."""
        policy = DataSharingPolicy(
            approved_purposes=["fraud_investigation"],
            named_partners=["ORG-PARTNER"],
        )
        search_svc.set_sharing_policy(policy)

        e = make_entity(EntityType.PERSON, "secret", classification_level=DataClassification.HIGHLY_RESTRICTED)
        search_svc.index_entity(e)

        # auth_restricted has ORG-001, not ORG-PARTNER
        q = SearchQueryV2(query="secret", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2)
        result = search_svc.search(q)

        assert result.blocked_results >= 1

    def test_public_access_blocked_for_restricted(self, search_svc):
        """Public users should be denied restricted data by sharing policy."""
        policy = DataSharingPolicy(allow_public_access=False)
        search_svc.set_sharing_policy(policy)

        e = make_entity(EntityType.PERSON, "john", classification_level=DataClassification.RESTRICTED)
        search_svc.index_entity(e)

        auth = AuthorizationContext(
            user_id="u1",
            user_classification_level=DataClassification.RESTRICTED,
            user_role="public",
            purpose="fraud_investigation",
        )
        q = SearchQueryV2(query="john", search_type=SearchType.FUZZY, authorization=auth, fuzzy_distance=2)
        result = search_svc.search(q)

        assert result.blocked_results >= 1

    def test_check_sharing_policy_directly(self):
        """Test check_sharing_policy function directly."""
        from schemas.base import BaseEntity, Classification
        from schemas.enums import EntityType

        e = BaseEntity(
            entity_type=EntityType.PERSON,
            normalized_value="test",
            classification=Classification(classification=DataClassification.PUBLIC),
        )
        auth = AuthorizationContext(user_id="u1", purpose="fraud_investigation")
        policy = DataSharingPolicy()

        can, reason, decision = check_sharing_policy(e, auth, policy)
        assert can
        assert decision.decision == "ALLOWED"

    def test_check_sharing_policy_no_purpose(self):
        """check_sharing_policy should deny without purpose."""
        from schemas.base import BaseEntity, Classification
        from schemas.enums import EntityType

        e = BaseEntity(
            entity_type=EntityType.PERSON,
            normalized_value="test",
            classification=Classification(classification=DataClassification.PUBLIC),
        )
        auth = AuthorizationContext(user_id="u1", purpose=None)
        policy = DataSharingPolicy()

        can, reason, decision = check_sharing_policy(e, auth, policy)
        assert not can
        assert decision.decision == "DENIED"


class TestSemanticSearch:
    """Test that semantic search returns empty in Layer A."""

    def test_semantic_returns_empty(self, search_svc, auth_restricted):
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="a person named john", search_type=SearchType.SEMANTIC, authorization=auth_restricted)
        result = search_svc.search(q)

        assert result.total == 0  # Semantic search is Layer B


# ═══════════════════════════════════════════════
# NEGATIVE / FAIL-SAFE
# ═══════════════════════════════════════════════

class TestNegativeFailSafe:
    """Test fail-safe behavior."""

    def test_empty_query(self, search_svc, auth_restricted):
        q = SearchQueryV2(query="", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total == 0

    def test_search_empty_index(self, search_svc, auth_restricted):
        q = SearchQueryV2(query="anything", search_type=SearchType.EXACT, authorization=auth_restricted)
        result = search_svc.search(q)
        assert result.total == 0

    def test_search_type_not_implemented(self, search_svc, auth_restricted):
        """Unknown search type should fall back to exact."""
        e = make_entity(EntityType.PERSON, "john doe")
        search_svc.index_entity(e)

        q = SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted)
        q.search_type = "unknown_type"
        result = search_svc.search(q)
        assert result.total >= 1  # Falls back to exact


# ═══════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests."""

    def test_multi_type_search_workflow(self, search_svc, auth_restricted):
        """Index entities, campaigns, reports — search across all types."""
        # Index entities
        search_svc.index_entity(make_entity(EntityType.PERSON, "john doe", classification_level=DataClassification.RESTRICTED))
        search_svc.index_entity(make_entity(EntityType.DOMAIN, "phishing-site.com"))
        search_svc.index_entity(make_entity(EntityType.IP, "192.168.1.1"))

        # Index campaigns
        search_svc.index_campaign(make_campaign("CMP-001", "Phishing Operation"))

        # Index reports
        search_svc.index_report(make_report("RPT-001", "User reported phishing email", category="PHISHING"))

        # Exact search
        r1 = search_svc.search(SearchQueryV2(query="john doe", search_type=SearchType.EXACT, authorization=auth_restricted))
        assert r1.total == 1

        # Fuzzy search
        r2 = search_svc.search(SearchQueryV2(query="jon doe", search_type=SearchType.FUZZY, authorization=auth_restricted, fuzzy_distance=2))
        assert r2.total >= 1

        # Infrastructure search
        r3 = search_svc.search(SearchQueryV2(query="phishing", search_type=SearchType.INFRASTRUCTURE, authorization=auth_restricted))
        assert r3.total >= 1

        # Campaign search
        r4 = search_svc.search(SearchQueryV2(query="phishing", search_type=SearchType.CAMPAIGN, authorization=auth_restricted))
        assert r4.total >= 1

        # Report search
        r5 = search_svc.search(SearchQueryV2(query="phishing", search_type=SearchType.REPORT, authorization=auth_restricted))
        assert r5.total >= 1

    def test_authorization_workflow(self, search_svc):
        """Full authorization workflow across classification levels."""
        search_svc.index_entity(make_entity(EntityType.PERSON, "pub_person", classification_level=DataClassification.PUBLIC))
        search_svc.index_entity(make_entity(EntityType.PERSON, "res_person", classification_level=DataClassification.RESTRICTED))
        search_svc.index_entity(make_entity(EntityType.PERSON, "le_person", classification_level=DataClassification.LAW_ENFORCEMENT))

        # Public user
        auth_pub = AuthorizationContext(user_id="u1", user_classification_level=DataClassification.PUBLIC, user_role="citizen", purpose="research")
        r1 = search_svc.search(SearchQueryV2(query="person", search_type=SearchType.FUZZY, authorization=auth_pub, fuzzy_distance=5))
        assert r1.authorized_results == 1  # Only PUBLIC
        assert r1.blocked_results == 2

        # Restricted user
        auth_res = AuthorizationContext(user_id="u2", user_classification_level=DataClassification.RESTRICTED, user_role="investigator", purpose="fraud_investigation")
        r2 = search_svc.search(SearchQueryV2(query="person", search_type=SearchType.FUZZY, authorization=auth_res, fuzzy_distance=5))
        assert r2.authorized_results == 2  # PUBLIC + RESTRICTED
        assert r2.blocked_results == 1

        # LE user
        auth_le = AuthorizationContext(user_id="u3", user_classification_level=DataClassification.LAW_ENFORCEMENT, user_role="investigator", purpose="law_enforcement")
        r3 = search_svc.search(SearchQueryV2(query="person", search_type=SearchType.FUZZY, authorization=auth_le, fuzzy_distance=5))
        assert r3.authorized_results == 3  # All
        assert r3.blocked_results == 0
