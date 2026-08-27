"""Unit tests for Unified Fraud Network Graph — packages/services/fraud_graph.py."""

from datetime import UTC, datetime

import pytest

from services.fraud_graph import (
    FraudGraph,
    GraphEdge,
    GraphNode,
)


@pytest.fixture
def empty_graph():
    return FraudGraph()


@pytest.fixture
def sample_graph():
    fg = FraudGraph()
    # Add nodes across different classifications, jurisdictions, orgs
    now = datetime.now(UTC)
    n1 = GraphNode(id="phone1", node_type="PHONE", label="+123456789", classification="PUBLIC", jurisdiction="US", organization="ORG_A")
    n2 = GraphNode(id="email1", node_type="EMAIL", label="suspect@fraud.com", classification="RESTRICTED", jurisdiction="US", organization="ORG_A")
    n3 = GraphNode(id="ip1", node_type="IP", label="192.168.1.1", classification="CONFIDENTIAL", jurisdiction="UK", organization="ORG_B")
    n4 = GraphNode(id="wallet1", node_type="WALLET", label="0x123abc", classification="SECRET", jurisdiction="EU", organization="ORG_C")
    n5 = GraphNode(id="domain1", node_type="DOMAIN", label="phishing.com", classification="PUBLIC", jurisdiction="US", organization="ORG_A")

    for n in [n1, n2, n3, n4, n5]:
        fg.add_node(n)

    e1 = GraphEdge(id="e1", source_id="phone1", target_id="email1", edge_type="USES", provenance="telecom_feed", evidence_id="ev_001", confidence=0.9)
    e2 = GraphEdge(id="e2", source_id="email1", target_id="domain1", edge_type="REGISTERED_WITH", provenance="whois_db", evidence_id="ev_002", confidence=0.95)
    e3 = GraphEdge(id="e3", source_id="domain1", target_id="ip1", edge_type="RESOLVES_TO", provenance="dns_logs", evidence_id="ev_003", confidence=0.8)
    e4 = GraphEdge(id="e4", source_id="ip1", target_id="wallet1", edge_type="CONNECTED_TO", provenance="chain_analysis", evidence_id="ev_004", confidence=0.7)

    for e in [e1, e2, e3, e4]:
        fg.add_edge(e)

    return fg


class TestNodeEdgeCRUD:
    def test_add_and_get_node(self, empty_graph):
        node = GraphNode(id="n1", node_type="PHONE", label="+1111", classification="PUBLIC")
        node_id = empty_graph.add_node(node)
        assert node_id == "n1"
        retrieved = empty_graph.get_node("n1")
        assert retrieved is not None
        assert retrieved.id == "n1"
        assert retrieved.node_type == "PHONE"

    def test_add_node_invalid_type(self, empty_graph):
        node = GraphNode(id="n1", node_type="INVALID_TYPE", label="test")
        with pytest.raises(ValueError, match="Invalid node_type"):
            empty_graph.add_node(node)

    def test_add_node_invalid_classification(self, empty_graph):
        node = GraphNode(id="n1", node_type="PHONE", label="test", classification="TOP_SECRET")
        with pytest.raises(ValueError, match="Invalid classification"):
            empty_graph.add_node(node)

    def test_update_existing_node(self, empty_graph):
        n1 = GraphNode(id="n1", node_type="IP", label="1.1.1.1", properties={"version": "v1"})
        empty_graph.add_node(n1)
        n2 = GraphNode(id="n1", node_type="IP", label="1.1.1.1", properties={"version": "v2"})
        empty_graph.add_node(n2)
        assert empty_graph.get_node("n1").properties["version"] == "v2"

    def test_add_and_get_edge(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="PHONE", label="p1"))
        empty_graph.add_node(GraphNode(id="n2", node_type="EMAIL", label="e1"))
        edge = GraphEdge(id="e1", source_id="n1", target_id="n2", edge_type="USES")
        edge_id = empty_graph.add_edge(edge)
        assert edge_id == "e1"
        retrieved = empty_graph.get_edge("e1")
        assert retrieved is not None
        assert retrieved.source_id == "n1"
        assert retrieved.target_id == "n2"

    def test_add_edge_invalid_type(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="PHONE", label="p1"))
        empty_graph.add_node(GraphNode(id="n2", node_type="EMAIL", label="e1"))
        edge = GraphEdge(id="e1", source_id="n1", target_id="n2", edge_type="INVALID_RELATION")
        with pytest.raises(ValueError, match="Invalid edge_type"):
            empty_graph.add_edge(edge)

    def test_add_edge_invalid_confidence(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="PHONE", label="p1"))
        empty_graph.add_node(GraphNode(id="n2", node_type="EMAIL", label="e1"))
        edge = GraphEdge(id="e1", source_id="n1", target_id="n2", edge_type="USES", confidence=1.5)
        with pytest.raises(ValueError, match="confidence must be between"):
            empty_graph.add_edge(edge)

    def test_add_edge_missing_nodes(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="PHONE", label="p1"))
        edge = GraphEdge(id="e1", source_id="n1", target_id="n_missing", edge_type="USES")
        with pytest.raises(ValueError, match="must exist in the graph"):
            empty_graph.add_edge(edge)

    def test_get_nonexistent_node_and_edge(self, empty_graph):
        assert empty_graph.get_node("missing") is None
        assert empty_graph.get_edge("missing") is None


class TestAdjacencyAndNeighbors:
    def test_adjacency_list_updated(self, sample_graph):
        neighbors = sample_graph.get_neighbors("phone1")
        assert "email1" in neighbors

    def test_get_neighbors_depth_1(self, sample_graph):
        neighbors = sample_graph.get_neighbors("email1", max_depth=1)
        assert set(neighbors) == {"phone1", "domain1"}

    def test_get_neighbors_depth_2(self, sample_graph):
        neighbors = sample_graph.get_neighbors("phone1", max_depth=2)
        assert set(neighbors) == {"email1", "domain1"}

    def test_get_neighbors_max_depth_zero(self, sample_graph):
        assert sample_graph.get_neighbors("phone1", max_depth=0) == []

    def test_get_neighbors_isolated_node(self, empty_graph):
        empty_graph.add_node(GraphNode(id="iso", node_type="CASE", label="case_001"))
        assert empty_graph.get_neighbors("iso") == []


class TestPathFinding:
    def test_find_path_shortest_path(self, sample_graph):
        res = sample_graph.find_path("phone1", "ip1", max_hops=5)
        assert res is not None
        assert res.path == ["phone1", "email1", "domain1", "ip1"]
        assert res.total_hops == 3
        assert res.accessible is True

    def test_find_path_no_path(self, empty_graph):
        empty_graph.add_node(GraphNode(id="a", node_type="IP", label="1.1.1.1"))
        empty_graph.add_node(GraphNode(id="b", node_type="IP", label="2.2.2.2"))
        assert empty_graph.find_path("a", "b") is None

    def test_find_path_exceeds_max_hops(self, sample_graph):
        res = sample_graph.find_path("phone1", "wallet1", max_hops=2)
        assert res is None

    def test_find_path_same_source_target(self, sample_graph):
        res = sample_graph.find_path("phone1", "phone1")
        assert res is not None
        assert res.path == ["phone1"]
        assert res.total_hops == 0

    def test_find_path_missing_nodes(self, sample_graph):
        assert sample_graph.find_path("phone1", "nonexistent") is None


class TestBFSTraversal:
    def test_traverse_depth_limit(self, sample_graph):
        res = sample_graph.traverse("phone1", max_depth=2)
        assert set(res.path) == {"phone1", "email1", "domain1"}
        assert res.total_hops == 2

    def test_traverse_empty_graph_or_missing_start(self, empty_graph):
        res = empty_graph.traverse("missing")
        assert res.path == []
        assert res.accessible is False

    def test_traverse_isolated_node(self, empty_graph):
        empty_graph.add_node(GraphNode(id="single", node_type="CAMPAIGN", label="Camp1"))
        res = empty_graph.traverse("single")
        assert res.path == ["single"]
        assert res.total_hops == 0


class TestFiltering:
    def test_filter_by_classification_public(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_classification(nodes, "PUBLIC")
        labels = [n.label for n in filtered]
        assert "+123456789" in labels
        assert "phishing.com" in labels
        assert "suspect@fraud.com" not in labels

    def test_filter_by_classification_restricted(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_classification(nodes, "RESTRICTED")
        ids = [n.id for n in filtered]
        assert "phone1" in ids
        assert "email1" in ids
        assert "ip1" not in ids

    def test_filter_by_classification_confidential(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_classification(nodes, "CONFIDENTIAL")
        ids = [n.id for n in filtered]
        assert "phone1" in ids
        assert "email1" in ids
        assert "ip1" in ids
        assert "wallet1" not in ids

    def test_filter_by_classification_secret(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_classification(nodes, "SECRET")
        assert len(filtered) == 5

    def test_filter_by_jurisdiction_match(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_jurisdiction(nodes, "UK")
        ids = [n.id for n in filtered]
        assert "ip1" in ids

    def test_filter_by_jurisdiction_wildcard(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_jurisdiction(nodes, "*")
        assert len(filtered) == 5

    def test_filter_by_organization_match(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_organization(nodes, "ORG_A")
        ids = [n.id for n in filtered]
        assert "phone1" in ids
        assert "email1" in ids
        assert "domain1" in ids
        assert "ip1" not in ids

    def test_filter_by_organization_wildcard(self, sample_graph):
        nodes = list(sample_graph._nodes.values())
        filtered = sample_graph.filter_by_organization(nodes, "ALL")
        assert len(filtered) == 5


class TestSecurityEnforcement:
    def test_security_clearance_blocked_traversal(self, sample_graph):
        user_ctx = {"clearance": "RESTRICTED", "jurisdiction": "*", "organization": "ALL"}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert res.accessible is False
        assert "ip1" in res.blocked_nodes or "wallet1" in res.blocked_nodes

    def test_security_jurisdiction_blocked_traversal(self, sample_graph):
        user_ctx = {"clearance": "SECRET", "jurisdiction": "US", "organization": "ALL"}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert res.accessible is False
        assert "ip1" in res.blocked_nodes

    def test_security_org_blocked_traversal(self, sample_graph):
        user_ctx = {"clearance": "SECRET", "jurisdiction": "*", "organization": "ORG_A"}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert res.accessible is False
        assert "ip1" in res.blocked_nodes

    def test_security_traversal_does_not_reveal_blocked_nodes(self, sample_graph):
        user_ctx = {"clearance": "PUBLIC", "jurisdiction": "US", "organization": "ORG_A"}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert "email1" in res.blocked_nodes
        assert "email1" not in res.path
        assert res.accessible is False

    def test_security_direct_access_deny_graph_traversal_deny(self, sample_graph):
        user_ctx = {"clearance": "PUBLIC", "jurisdiction": "US", "organization": "ORG_A"}
        # Direct access check
        assert sample_graph.get_node("wallet1", user_context=user_ctx) is None
        # Graph traversal check
        trav = sample_graph.traverse("phone1", max_depth=10, user_context=user_ctx)
        assert "wallet1" not in trav.path
        assert trav.accessible is False
        # Export check
        exp = sample_graph.export_graph(user_context=user_ctx)
        exported_ids = [n["id"] for n in exp["nodes"]]
        assert "wallet1" not in exported_ids

    def test_security_international_clearance_bypasses_jurisdiction(self, sample_graph):
        user_ctx = {"clearance": "SECRET", "jurisdiction": "US", "organization": "ALL", "international_clearance": True}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert "ip1" in res.path
        assert res.accessible is True

    def test_security_cross_org_permission_bypasses_org_check(self, sample_graph):
        user_ctx = {"clearance": "SECRET", "jurisdiction": "*", "organization": "ORG_A", "cross_org_access": True}
        res = sample_graph.traverse("phone1", max_depth=5, user_context=user_ctx)
        assert "ip1" in res.path
        assert res.accessible is True


class TestSubgraphAndAnalytics:
    def test_get_subgraph(self, sample_graph):
        sub = sample_graph.get_subgraph(["phone1", "email1", "domain1"])
        node_ids = [n.id for n in sub["nodes"]]
        edge_ids = [e.id for e in sub["edges"]]
        assert set(node_ids) == {"phone1", "email1", "domain1"}
        assert set(edge_ids) == {"e1", "e2"}

    def test_get_node_degree(self, sample_graph):
        assert sample_graph.get_node_degree("email1") == 2
        assert sample_graph.get_node_degree("phone1") == 1
        assert sample_graph.get_node_degree("nonexistent") == 0

    def test_find_central_nodes(self, sample_graph):
        central = sample_graph.find_central_nodes(top_n=3)
        assert len(central) == 3
        # Node email1 and domain1 have degree 2
        top_ids = [c[0] for c in central]
        assert "email1" in top_ids or "domain1" in top_ids

    def test_get_stats(self, sample_graph):
        stats = sample_graph.get_stats()
        assert stats["node_count"] == 5
        assert stats["edge_count"] == 4
        assert stats["node_types"]["PHONE"] == 1
        assert stats["edge_types"]["USES"] == 1
        assert stats["classification_distribution"]["PUBLIC"] == 2

    def test_export_graph(self, sample_graph):
        exp = sample_graph.export_graph()
        assert len(exp["nodes"]) == 5
        assert len(exp["edges"]) == 4
        assert exp["nodes"][0]["id"] in sample_graph._nodes


class TestProvenanceAndTemporal:
    def test_edge_provenance_and_evidence_linking(self, sample_graph):
        e1 = sample_graph.get_edge("e1")
        assert e1.provenance == "telecom_feed"
        assert e1.evidence_id == "ev_001"

    def test_edge_confidence_and_temporal_tracking(self, sample_graph):
        e1 = sample_graph.get_edge("e1")
        assert e1.confidence == 0.9
        assert isinstance(e1.first_seen, datetime)
        assert isinstance(e1.last_seen, datetime)

    def test_multiple_relationship_types_same_nodes(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="PHONE", label="p1"))
        empty_graph.add_node(GraphNode(id="n2", node_type="ORGANIZATION", label="org1"))

        edge1 = GraphEdge(id="e1", source_id="n1", target_id="n2", edge_type="USES")
        edge2 = GraphEdge(id="e2", source_id="n1", target_id="n2", edge_type="CONNECTED_TO")

        empty_graph.add_edge(edge1)
        empty_graph.add_edge(edge2)

        assert empty_graph.get_node_degree("n1") == 2
        assert len(empty_graph.get_neighbors("n1")) == 1  # n2 is unique neighbor


class TestLargeGraphAndEdgeCases:
    def test_large_graph_performance(self, empty_graph):
        # Build graph with 120 nodes in a chain
        for i in range(120):
            empty_graph.add_node(GraphNode(
                id=f"node_{i}",
                node_type="ENTITY",
                label=f"Entity {i}",
                classification="PUBLIC"
            ))

        for i in range(119):
            empty_graph.add_edge(GraphEdge(
                id=f"edge_{i}",
                source_id=f"node_{i}",
                target_id=f"node_{i+1}",
                edge_type="CONNECTED_TO"
            ))

        assert empty_graph.get_stats()["node_count"] == 120
        assert empty_graph.get_stats()["edge_count"] == 119

        path = empty_graph.find_path("node_0", "node_10", max_hops=15)
        assert path is not None
        assert len(path.path) == 11
        assert path.total_hops == 10

    def test_self_loops(self, empty_graph):
        empty_graph.add_node(GraphNode(id="n1", node_type="TRANSACTION", label="tx_001"))
        empty_graph.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n1", edge_type="PAID_TO"))

        assert empty_graph.get_node_degree("n1") == 1
        assert empty_graph.get_neighbors("n1") == []

    def test_empty_graph_operations(self, empty_graph):
        stats = empty_graph.get_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        assert empty_graph.find_central_nodes() == []
        assert empty_graph.export_graph()["nodes"] == []
