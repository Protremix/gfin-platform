"""Unified Fraud Network Graph for GFIN Platform.

Connects ALL GFIN entity types and relationship types with provenance,
temporal tracking, and security enforcement.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

VALID_NODE_TYPES = {
    "PHONE",
    "EMAIL",
    "DOMAIN",
    "URL",
    "IP",
    "ASN",
    "CERTIFICATE",
    "SERVER",
    "ORGANIZATION",
    "ENTITY",
    "WALLET",
    "TRANSACTION",
    "LOCATION",
    "CASE",
    "CAMPAIGN",
    "REPORT",
    "EVENT",
    "OBSERVATION",
}

VALID_RELATIONSHIP_TYPES = {
    "USES",
    "HOSTS",
    "RESOLVES_TO",
    "REGISTERED_WITH",
    "CONNECTED_TO",
    "PAID_TO",
    "REPORTED_IN",
    "LOCATED_AT",
    "OBSERVED_AT",
    "PART_OF",
    "SIMILAR_TO",
    "PRECEDES",
    "FOLLOWED_BY",
}

CLASSIFICATION_LEVELS = {
    "PUBLIC": 0,
    "RESTRICTED": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


@dataclass
class GraphNode:
    id: str
    node_type: str  # one of the types above
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    classification: str = "PUBLIC"  # PUBLIC, RESTRICTED, CONFIDENTIAL, SECRET
    jurisdiction: str | None = None
    organization: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GraphEdge:
    id: str
    source_id: str
    target_id: str
    edge_type: str  # one of the types above
    properties: dict[str, Any] = field(default_factory=dict)
    provenance: str = "system"  # source of this relationship
    evidence_id: str | None = None  # link to evidence vault
    confidence: float = 1.0  # 0.0-1.0
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    classification: str = "PUBLIC"
    jurisdiction: str | None = None


@dataclass
class GraphTraversalResult:
    path: list[str] = field(default_factory=list)  # node IDs
    edges: list[GraphEdge] = field(default_factory=list)
    total_hops: int = 0
    accessible: bool = True  # whether user can access all nodes in path
    blocked_nodes: list[str] = field(default_factory=list)  # nodes user cannot access


class FraudGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._adjacency: dict[str, list[str]] = {}  # node_id -> [edge_ids]

    def add_node(self, node: GraphNode) -> str:
        """Add or update a node in the graph."""
        if not isinstance(node, GraphNode):
            raise TypeError("node must be an instance of GraphNode")
        if node.node_type and node.node_type.upper() not in VALID_NODE_TYPES:
            raise ValueError(f"Invalid node_type '{node.node_type}'. Must be one of {VALID_NODE_TYPES}")
        if node.classification and node.classification.upper() not in CLASSIFICATION_LEVELS:
            raise ValueError(f"Invalid classification '{node.classification}'. Must be one of {CLASSIFICATION_LEVELS.keys()}")

        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        return node.id

    def add_edge(self, edge: GraphEdge) -> str:
        """Add an edge between existing nodes in the graph."""
        if not isinstance(edge, GraphEdge):
            raise TypeError("edge must be an instance of GraphEdge")
        if edge.edge_type and edge.edge_type.upper() not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid edge_type '{edge.edge_type}'. Must be one of {VALID_RELATIONSHIP_TYPES}")
        if edge.classification and edge.classification.upper() not in CLASSIFICATION_LEVELS:
            raise ValueError(f"Invalid classification '{edge.classification}'. Must be one of {CLASSIFICATION_LEVELS.keys()}")
        if not (0.0 <= edge.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            raise ValueError(f"Both source_id '{edge.source_id}' and target_id '{edge.target_id}' must exist in the graph.")

        self._edges[edge.id] = edge
        if edge.id not in self._adjacency[edge.source_id]:
            self._adjacency[edge.source_id].append(edge.id)
        if edge.id not in self._adjacency[edge.target_id]:
            self._adjacency[edge.target_id].append(edge.id)
        return edge.id

    def get_node(self, node_id: str, user_context: dict | None = None) -> GraphNode | None:
        """Get node by ID if it exists and passes user_context security checks."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        if user_context is not None and not self._check_node_access(node, user_context):
            return None
        return node

    def get_edge(self, edge_id: str, user_context: dict | None = None) -> GraphEdge | None:
        """Get edge by ID if it exists and passes user_context security checks."""
        edge = self._edges.get(edge_id)
        if not edge:
            return None
        if user_context is not None:
            if not self._check_node_access(edge.source_id, user_context) or not self._check_node_access(edge.target_id, user_context):
                return None
            if not self._check_edge_access(edge, user_context):
                return None
        return edge

    def get_neighbors(self, node_id: str, max_depth: int = 1, user_context: dict | None = None) -> list[str]:
        """Get accessible neighbor node IDs up to max_depth hops away."""
        if node_id not in self._nodes:
            return []
        if user_context is not None and not self._check_node_access(node_id, user_context):
            return []
        if max_depth < 1:
            return []

        visited = {node_id}
        current_level = {node_id}
        result = []

        for _ in range(max_depth):
            next_level = set()
            for curr in current_level:
                for eid in self._adjacency.get(curr, []):
                    edge = self._edges.get(eid)
                    if not edge:
                        continue
                    if user_context is not None and not self._check_edge_access(edge, user_context):
                        continue
                    neighbor_id = edge.target_id if edge.source_id == curr else edge.source_id
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        if user_context is None or self._check_node_access(neighbor_id, user_context):
                            result.append(neighbor_id)
                            next_level.add(neighbor_id)
            current_level = next_level
            if not current_level:
                break

        return result

    def find_path(
        self, source_id: str, target_id: str, max_hops: int = 5, user_context: dict | None = None
    ) -> GraphTraversalResult | None:
        """Find path between source_id and target_id up to max_hops."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        queue = deque([(source_id, [source_id], [])])
        visited = {source_id}

        found_path: tuple[list[str], list[GraphEdge]] | None = None

        while queue:
            curr_id, path_nodes, path_edges = queue.popleft()
            if curr_id == target_id:
                found_path = (path_nodes, path_edges)
                break
            if len(path_edges) >= max_hops:
                continue

            for eid in self._adjacency.get(curr_id, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                nxt_id = edge.target_id if edge.source_id == curr_id else edge.source_id
                if nxt_id not in visited:
                    visited.add(nxt_id)
                    queue.append((nxt_id, [*path_nodes, nxt_id], [*path_edges, edge]))

        if not found_path:
            return None

        p_nodes, p_edges = found_path

        blocked = []
        if user_context is not None:
            for nid in p_nodes:
                if not self._check_node_access(nid, user_context):
                    blocked.append(nid)

        accessible = (len(blocked) == 0)

        if accessible:
            return GraphTraversalResult(
                path=p_nodes,
                edges=p_edges,
                total_hops=len(p_edges),
                accessible=True,
                blocked_nodes=[],
            )
        else:
            acc_nodes = [nid for nid in p_nodes if nid not in blocked]
            acc_edges = [e for e in p_edges if e.source_id not in blocked and e.target_id not in blocked]
            return GraphTraversalResult(
                path=acc_nodes,
                edges=acc_edges,
                total_hops=len(p_edges),
                accessible=False,
                blocked_nodes=blocked,
            )

    def traverse(
        self, start_id: str, max_depth: int = 3, user_context: dict | None = None
    ) -> GraphTraversalResult:
        """BFS traversal from start_id up to max_depth."""
        if start_id not in self._nodes:
            return GraphTraversalResult(path=[], edges=[], total_hops=0, accessible=False, blocked_nodes=[])

        if user_context is not None and not self._check_node_access(start_id, user_context):
            return GraphTraversalResult(
                path=[], edges=[], total_hops=0, accessible=False, blocked_nodes=[start_id]
            )

        queue = deque([(start_id, 0)])
        visited_nodes = {start_id}
        path_nodes = [start_id]
        collected_edges: list[GraphEdge] = []
        blocked_nodes: set[str] = set()
        max_hops_reached = 0

        while queue:
            curr_id, depth = queue.popleft()
            if depth > max_hops_reached:
                max_hops_reached = depth
            if depth >= max_depth:
                continue

            for eid in self._adjacency.get(curr_id, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                neighbor_id = edge.target_id if edge.source_id == curr_id else edge.source_id

                if user_context is not None and not self._check_node_access(neighbor_id, user_context):
                    blocked_nodes.add(neighbor_id)
                    continue

                if user_context is not None and not self._check_edge_access(edge, user_context):
                    continue

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    path_nodes.append(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

                if edge not in collected_edges:
                    collected_edges.append(edge)

        return GraphTraversalResult(
            path=path_nodes,
            edges=collected_edges,
            total_hops=max_hops_reached,
            accessible=(len(blocked_nodes) == 0),
            blocked_nodes=list(blocked_nodes),
        )

    def filter_by_classification(self, nodes: list, user_clearance: str) -> list:
        """Filter list of nodes or node_ids by user clearance level."""
        user_lvl = CLASSIFICATION_LEVELS.get((user_clearance or "PUBLIC").upper(), 0)
        res = []
        for item in nodes:
            node = item if isinstance(item, GraphNode) else self._nodes.get(item)
            if node:
                node_lvl = CLASSIFICATION_LEVELS.get((node.classification or "PUBLIC").upper(), 0)
                if user_lvl >= node_lvl:
                    res.append(item)
        return res

    def filter_by_jurisdiction(self, nodes: list, user_jurisdiction: str) -> list:
        """Filter list of nodes or node_ids by user jurisdiction."""
        res = []
        for item in nodes:
            node = item if isinstance(item, GraphNode) else self._nodes.get(item)
            if node:
                if not node.jurisdiction or (user_jurisdiction and (
                    str(user_jurisdiction).upper() in ("*", "ALL", "GLOBAL", "INTERNATIONAL")
                    or node.jurisdiction == user_jurisdiction
                )):
                    res.append(item)
        return res

    def filter_by_organization(self, nodes: list, user_org: str) -> list:
        """Filter list of nodes or node_ids by user organization."""
        res = []
        for item in nodes:
            node = item if isinstance(item, GraphNode) else self._nodes.get(item)
            if node:
                if not node.organization or (user_org and (
                    str(user_org).upper() in ("*", "ALL", "GLOBAL")
                    or node.organization == user_org
                )):
                    res.append(item)
        return res

    def get_subgraph(self, node_ids: list[str], user_context: dict | None = None) -> dict:
        """Extract a subgraph containing specified node_ids and connecting edges."""
        sub_nodes = []
        included_ids = set()

        for nid in node_ids:
            node = self.get_node(nid, user_context=user_context)
            if node:
                sub_nodes.append(node)
                included_ids.add(nid)

        sub_edges = []
        seen_edge_ids = set()

        for nid in included_ids:
            for eid in self._adjacency.get(nid, []):
                if eid in seen_edge_ids:
                    continue
                edge = self._edges.get(eid)
                if edge and edge.source_id in included_ids and edge.target_id in included_ids:
                    if user_context is None or self._check_edge_access(edge, user_context):
                        sub_edges.append(edge)
                        seen_edge_ids.add(eid)

        return {"nodes": sub_nodes, "edges": sub_edges}

    def get_node_degree(self, node_id: str) -> int:
        """Get total degree (number of connected edges) of a node."""
        if node_id not in self._nodes:
            return 0
        return len(self._adjacency.get(node_id, []))

    def find_central_nodes(self, top_n: int = 10) -> list[tuple[str, int]]:
        """Find top N nodes sorted by degree descending."""
        degrees = [(nid, self.get_node_degree(nid)) for nid in self._nodes]
        degrees.sort(key=lambda x: (-x[1], x[0]))
        return degrees[:top_n]

    def export_graph(self, user_context: dict | None = None) -> dict:
        """Full graph export respecting user_context security filters."""
        export_nodes = []
        export_edges = []

        for _nid, node in self._nodes.items():
            if user_context is None or self._check_node_access(node, user_context):
                export_nodes.append(asdict(node))

        accessible_node_ids = {n["id"] for n in export_nodes}

        for _eid, edge in self._edges.items():
            if edge.source_id in accessible_node_ids and edge.target_id in accessible_node_ids:
                if user_context is None or self._check_edge_access(edge, user_context):
                    export_edges.append(asdict(edge))

        return {"nodes": export_nodes, "edges": export_edges}

    def get_stats(self, user_context: dict | None = None) -> dict:
        """Get graph statistics and distributions."""
        accessible_nodes = [
            n for n in self._nodes.values()
            if user_context is None or self._check_node_access(n, user_context)
        ]
        accessible_ids = {n.id for n in accessible_nodes}
        accessible_edges = [
            e for e in self._edges.values()
            if e.source_id in accessible_ids and e.target_id in accessible_ids
            and (user_context is None or self._check_edge_access(e, user_context))
        ]

        node_types: dict[str, int] = {}
        classifications: dict[str, int] = {}
        for n in accessible_nodes:
            node_types[n.node_type] = node_types.get(n.node_type, 0) + 1
            classifications[n.classification] = classifications.get(n.classification, 0) + 1

        edge_types: dict[str, int] = {}
        for e in accessible_edges:
            edge_types[e.edge_type] = edge_types.get(e.edge_type, 0) + 1

        return {
            "node_count": len(accessible_nodes),
            "edge_count": len(accessible_edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "classification_distribution": classifications,
        }

    def _check_node_access(self, node: GraphNode | str, user_context: dict | None) -> bool:
        """Check if user_context permits access to node."""
        if user_context is None:
            return True

        node_obj = node if isinstance(node, GraphNode) else self._nodes.get(node)
        if not node_obj:
            return False

        # Classification check
        user_clearance = (
            user_context.get("clearance")
            or user_context.get("user_clearance")
            or user_context.get("clearance_level")
        )
        if user_clearance is not None:
            user_lvl = CLASSIFICATION_LEVELS.get(str(user_clearance).upper(), 0)
            node_lvl = CLASSIFICATION_LEVELS.get((node_obj.classification or "PUBLIC").upper(), 0)
            if user_lvl < node_lvl:
                return False

        # Jurisdiction check
        if node_obj.jurisdiction:
            user_jur = user_context.get("jurisdiction") or user_context.get("user_jurisdiction")
            has_intl = (
                user_context.get("international_clearance") is True
                or user_context.get("international_access") is True
                or user_context.get("allow_international") is True
                or user_context.get("is_international") is True
                or user_context.get("cross_jurisdiction") is True
            )
            if not has_intl:
                if not user_jur or (
                    user_jur != node_obj.jurisdiction
                    and str(user_jur).upper() not in ("*", "ALL", "GLOBAL", "INTERNATIONAL")
                ):
                    return False

        # Organization check
        if node_obj.organization:
            user_org = (
                user_context.get("organization")
                or user_context.get("user_org")
                or user_context.get("org")
            )
            has_cross_org = (
                user_context.get("cross_org_access") is True
                or user_context.get("cross_org_permission") is True
                or user_context.get("cross_org") is True
                or user_context.get("allow_cross_org") is True
                or user_context.get("is_cross_org") is True
            )
            if not has_cross_org:
                if not user_org or (
                    user_org != node_obj.organization and str(user_org).upper() not in ("*", "ALL", "GLOBAL")
                ):
                    return False

        return True

    def _check_edge_access(self, edge: GraphEdge, user_context: dict | None) -> bool:
        """Check if user_context permits access to edge."""
        if user_context is None:
            return True

        if edge.classification:
            user_clearance = (
                user_context.get("clearance")
                or user_context.get("user_clearance")
                or user_context.get("clearance_level")
            )
            if user_clearance is not None:
                user_lvl = CLASSIFICATION_LEVELS.get(str(user_clearance).upper(), 0)
                edge_lvl = CLASSIFICATION_LEVELS.get((edge.classification or "PUBLIC").upper(), 0)
                if user_lvl < edge_lvl:
                    return False

        if edge.jurisdiction:
            user_jur = user_context.get("jurisdiction") or user_context.get("user_jurisdiction")
            has_intl = (
                user_context.get("international_clearance") is True
                or user_context.get("international_access") is True
                or user_context.get("allow_international") is True
                or user_context.get("is_international") is True
                or user_context.get("cross_jurisdiction") is True
            )
            if not has_intl:
                if not user_jur or (
                    user_jur != edge.jurisdiction
                    and str(user_jur).upper() not in ("*", "ALL", "GLOBAL", "INTERNATIONAL")
                ):
                    return False

        return True
