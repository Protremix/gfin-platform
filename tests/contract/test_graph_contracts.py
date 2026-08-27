"""Contract tests for graph engine operations.

Per Luna Directive — Focus Area 1: Contract tests for graph nodes, edges,
path finding, and neighbor queries.
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

import pytest

from common.graph import AdjacencyListGraph, GraphEdge, GraphNode, GraphPath
from schemas.versions import get_schema


class TestGraphNodeContracts:
    """Test GraphNode schema contracts."""

    def test_graph_node_schema_v1_exists(self):
        """Graph node schema v1.0 should exist."""
        schema = get_schema("graph_node", "1.0")
        assert schema is not None
        assert "entity_id" in schema.required_fields
        assert "entity_type" in schema.required_fields
        assert "label" in schema.required_fields

    def test_graph_node_requires_label(self):
        """GraphNode should require the label field."""
        with pytest.raises(Exception):
            GraphNode(entity_id="test", entity_type="entity")  # Missing label

    def test_graph_node_creates_with_all_fields(self):
        """GraphNode should create successfully with all fields."""
        node = GraphNode(entity_id="N1", entity_type="Person", label="John")
        assert node.entity_id == "N1"
        assert node.entity_type == "Person"
        assert node.label == "John"

    def test_graph_node_properties_optional(self):
        """GraphNode properties should be optional."""
        node = GraphNode(entity_id="N1", entity_type="Person", label="John")
        assert node.properties is not None  # Has default


class TestGraphEdgeContracts:
    """Test GraphEdge schema contracts."""

    def test_graph_edge_schema_v1_exists(self):
        """Graph edge schema v1.0 should exist."""
        schema = get_schema("graph_edge", "1.0")
        assert schema is not None
        assert "relationship_id" in schema.required_fields
        assert "from_entity_id" in schema.required_fields
        assert "to_entity_id" in schema.required_fields
        assert "relationship_type" in schema.required_fields

    def test_graph_edge_requires_relationship_id(self):
        """GraphEdge should require relationship_id."""
        with pytest.raises(Exception):
            GraphEdge(
                from_entity_id="A",
                to_entity_id="B",
                relationship_type="LINKED",
            )  # Missing relationship_id

    def test_graph_edge_creates_with_all_fields(self):
        """GraphEdge should create successfully with all required fields."""
        edge = GraphEdge(
            relationship_id="edge-1",
            from_entity_id="A",
            to_entity_id="B",
            relationship_type="LINKED_TO",
        )
        assert edge.from_entity_id == "A"
        assert edge.to_entity_id == "B"
        assert edge.relationship_type == "LINKED_TO"

    def test_graph_edge_confidence_optional(self):
        """GraphEdge confidence should be optional."""
        edge = GraphEdge(
            relationship_id="e1",
            from_entity_id="A",
            to_entity_id="B",
            relationship_type="LINKED",
        )
        assert edge.confidence is not None  # Has default


class TestGraphOperationContracts:
    """Test graph engine operation contracts."""

    def test_add_and_get_node(self):
        """Added node should be retrievable."""
        graph = AdjacencyListGraph()

        async def run():
            node = GraphNode(entity_id="N1", entity_type="Person", label="John")
            await graph.add_node(node)
            return await graph.get_node("N1")

        result = asyncio.run(run())
        assert result is not None
        assert result.entity_id == "N1"

    def test_get_nonexistent_node_returns_none(self):
        """Getting nonexistent node should return None."""
        graph = AdjacencyListGraph()

        async def run():
            return await graph.get_node("DOES-NOT-EXIST")

        result = asyncio.run(run())
        assert result is None

    def test_add_edge_and_get_neighbors(self):
        """Added edge should appear in neighbor query."""
        graph = AdjacencyListGraph()

        async def run():
            n1 = GraphNode(entity_id="A", entity_type="entity", label="A")
            n2 = GraphNode(entity_id="B", entity_type="entity", label="B")
            await graph.add_node(n1)
            await graph.add_node(n2)
            edge = GraphEdge(
                relationship_id="e1",
                from_entity_id="A",
                to_entity_id="B",
                relationship_type="LINKED_TO",
            )
            await graph.add_edge(edge)
            nodes, edges = await graph.get_neighbors("A")
            return nodes, edges

        nodes, edges = asyncio.run(run())
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_get_neighbors_returns_tuple(self):
        """get_neighbors should return tuple of (nodes, edges)."""
        graph = AdjacencyListGraph()

        async def run():
            return await graph.get_neighbors("nonexistent")

        result = asyncio.run(run())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_find_path_returns_graphpath(self):
        """find_path should return GraphPath or None."""
        graph = AdjacencyListGraph()

        async def run():
            n1 = GraphNode(entity_id="A", entity_type="entity", label="A")
            n2 = GraphNode(entity_id="B", entity_type="entity", label="B")
            await graph.add_node(n1)
            await graph.add_node(n2)
            edge = GraphEdge(
                relationship_id="e1",
                from_entity_id="A",
                to_entity_id="B",
                relationship_type="LINKED",
            )
            await graph.add_edge(edge)
            return await graph.find_path("A", "B")

        path = asyncio.run(run())
        assert path is not None
        assert isinstance(path, GraphPath)
        assert path.length >= 1

    def test_find_path_respects_max_depth(self):
        """find_path should respect max_depth parameter."""
        graph = AdjacencyListGraph()

        async def run():
            for i in range(10):
                node = GraphNode(entity_id=f"n{i}", entity_type="entity", label=f"N{i}")
                await graph.add_node(node)
            for i in range(9):
                edge = GraphEdge(
                    relationship_id=f"e{i}",
                    from_entity_id=f"n{i}",
                    to_entity_id=f"n{i + 1}",
                    relationship_type="LINKED",
                )
                await graph.add_edge(edge)
            # Path length is 9, max_depth=5 should return None
            return await graph.find_path("n0", "n9", max_depth=5)

        path = asyncio.run(run())
        assert path is None  # Too deep

    def test_remove_node(self):
        """Removing a node should make it inaccessible."""
        graph = AdjacencyListGraph()

        async def run():
            node = GraphNode(entity_id="N1", entity_type="entity", label="N1")
            await graph.add_node(node)
            removed = await graph.remove_node("N1")
            after = await graph.get_node("N1")
            return removed, after

        removed, after = asyncio.run(run())
        assert removed is True
        assert after is None

    def test_remove_nonexistent_node(self):
        """Removing nonexistent node should return False."""
        graph = AdjacencyListGraph()

        async def run():
            return await graph.remove_node("DOES-NOT-EXIST")

        result = asyncio.run(run())
        assert result is False
