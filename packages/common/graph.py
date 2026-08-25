# GFIN Graph Store Abstraction Interface
#
# Layer A (current): AdjacencyListGraph — in-memory adjacency list
# Layer B (target):  Neo4jGraph — Neo4j (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# Per Master Spec §40: Users should be able to explore direct connections,
# indirect connections, cross-border, infrastructure, campaigns, reports,
# and cases. Each relationship should be clickable and traceable to evidence.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """A node in the intelligence graph."""

    entity_id: str
    entity_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge (relationship) in the intelligence graph."""

    relationship_id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    confidence: str = "UNKNOWN"
    source_id: str | None = None
    timestamp: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphPath(BaseModel):
    """A path between two entities."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    length: int = 0


class GraphStore(ABC):
    """Abstract graph store interface.

    All application code interacts with the graph through this interface.
    The specific adapter (adjacency list, Neo4j) is selected by configuration.
    """

    @abstractmethod
    async def add_node(self, node: GraphNode) -> None:
        """Add or update a node."""
        ...

    @abstractmethod
    async def add_edge(self, edge: GraphEdge) -> None:
        """Add or update an edge (relationship)."""
        ...

    @abstractmethod
    async def get_node(self, entity_id: str) -> GraphNode | None:
        """Get a node by entity ID."""
        ...

    @abstractmethod
    async def get_neighbors(
        self, entity_id: str, relationship_type: str | None = None, max_depth: int = 1
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Get neighbors of a node, optionally filtered by relationship type."""
        ...

    @abstractmethod
    async def find_path(
        self, from_entity_id: str, to_entity_id: str, max_depth: int = 5
    ) -> GraphPath | None:
        """Find shortest path between two entities."""
        ...

    @abstractmethod
    async def remove_node(self, entity_id: str) -> bool:
        """Remove a node and all its edges."""
        ...

    @abstractmethod
    async def remove_edge(self, relationship_id: str) -> bool:
        """Remove an edge."""
        ...


class AdjacencyListGraph(GraphStore):
    """Development adapter — in-memory adjacency list graph.

    NOT for production. No persistence. Limited query capability.
    Production uses Neo4j adapter (REQUIRES EXTERNAL INFRASTRUCTURE).

    Suitable for development, unit testing, and small-scale MVP.
    Does NOT support: graph algorithms, pathfinding optimization,
    multi-hop queries at scale.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._adjacency: dict[str, dict[str, list[str]]] = {}  # entity_id -> {rel_type: [edge_ids]}

    async def add_node(self, node: GraphNode) -> None:
        self._nodes[node.entity_id] = node
        if node.entity_id not in self._adjacency:
            self._adjacency[node.entity_id] = {}

    async def add_edge(self, edge: GraphEdge) -> None:
        self._edges[edge.relationship_id] = edge
        for entity_id in [edge.from_entity_id, edge.to_entity_id]:
            if entity_id not in self._adjacency:
                self._adjacency[entity_id] = {}
            if edge.relationship_type not in self._adjacency[entity_id]:
                self._adjacency[entity_id][edge.relationship_type] = []
            self._adjacency[entity_id][edge.relationship_type].append(edge.relationship_id)

    async def get_node(self, entity_id: str) -> GraphNode | None:
        return self._nodes.get(entity_id)

    async def get_neighbors(
        self, entity_id: str, relationship_type: str | None = None, max_depth: int = 1
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        visited: set[str] = set()
        current_level = {entity_id}

        for _ in range(max_depth):
            next_level: set[str] = set()
            for eid in current_level:
                if eid in visited:
                    continue
                visited.add(eid)
                adj = self._adjacency.get(eid, {})
                rel_types = [relationship_type] if relationship_type else list(adj.keys())
                for rt in rel_types:
                    for edge_id in adj.get(rt, []):
                        edge = self._edges.get(edge_id)
                        if edge is None:
                            continue
                        edges.append(edge)
                        neighbor_id = (
                            edge.to_entity_id if edge.from_entity_id == eid else edge.from_entity_id
                        )
                        if neighbor_id not in visited:
                            neighbor = self._nodes.get(neighbor_id)
                            if neighbor:
                                nodes.append(neighbor)
                            next_level.add(neighbor_id)
            current_level = next_level

        return nodes, edges

    async def find_path(
        self, from_entity_id: str, to_entity_id: str, max_depth: int = 5
    ) -> GraphPath | None:
        if from_entity_id == to_entity_id:
            node = self._nodes.get(from_entity_id)
            if node:
                return GraphPath(nodes=[node], edges=[], length=0)
            return None

        # BFS
        from collections import deque

        queue: deque[tuple[str, list[str], list[str]]] = deque(
            [(from_entity_id, [from_entity_id], [])]
        )
        visited: set[str] = {from_entity_id}

        while queue:
            current, path_nodes, path_edges = queue.popleft()
            if len(path_nodes) - 1 >= max_depth:
                continue

            adj = self._adjacency.get(current, {})
            for edge_ids in adj.values():
                for edge_id in edge_ids:
                    edge = self._edges.get(edge_id)
                    if edge is None:
                        continue
                    neighbor = (
                        edge.to_entity_id if edge.from_entity_id == current else edge.from_entity_id
                    )
                    if neighbor == to_entity_id:
                        # Found path
                        all_node_ids = [*path_nodes, neighbor]
                        all_edge_ids = [*path_edges, edge_id]
                        nodes = [self._nodes[nid] for nid in all_node_ids if nid in self._nodes]
                        edges = [self._edges[eid] for eid in all_edge_ids if eid in self._edges]
                        return GraphPath(nodes=nodes, edges=edges, length=len(edges))
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, [*path_nodes, neighbor], [*path_edges, edge_id]))

        return None

    async def remove_node(self, entity_id: str) -> bool:
        if entity_id not in self._nodes:
            return False
        del self._nodes[entity_id]
        # Remove all edges connected to this node
        edges_to_remove = [
            eid
            for eid, e in self._edges.items()
            if e.from_entity_id == entity_id or e.to_entity_id == entity_id
        ]
        for eid in edges_to_remove:
            del self._edges[eid]
        self._adjacency.pop(entity_id, None)
        return True

    async def remove_edge(self, relationship_id: str) -> bool:
        if relationship_id not in self._edges:
            return False
        del self._edges[relationship_id]
        return True
