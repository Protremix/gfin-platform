"""GFIN Brain Tool Registry — central registry for all Brain-accessible tools."""
from __future__ import annotations
from typing import Any, Callable, Optional
from packages.brain.schemas import ToolDefinition, ToolResult, ToolCallRequest, RiskLevel


class ToolRegistry:
    """Central registry for all tools exposed to the GPT Brain.

    The Brain may only call tools that exist in this registry.
    Each tool is validated, authorized, and audited before execution.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}
        self._enabled: bool = True

    def register(self, tool: ToolDefinition, handler: Callable) -> None:
        """Register a tool with its execution handler."""
        if tool.tool_id in self._tools:
            raise ValueError(f"Tool already registered: {tool.tool_id}")
        self._tools[tool.tool_id] = tool
        self._handlers[tool.tool_id] = handler

    def unregister(self, tool_id: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(tool_id, None)
        self._handlers.pop(tool_id, None)

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool definition by ID."""
        return self._tools.get(tool_id)

    def list_tools(self, enabled_only: bool = True) -> list[ToolDefinition]:
        """List all registered tools."""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def list_tool_ids(self, enabled_only: bool = True) -> list[str]:
        """List all registered tool IDs."""
        return [t.tool_id for t in self.list_tools(enabled_only)]

    def get_handler(self, tool_id: str) -> Optional[Callable]:
        """Get the execution handler for a tool."""
        return self._handlers.get(tool_id)

    def is_valid(self, tool_id: str) -> bool:
        """Check if a tool ID is valid and enabled."""
        tool = self._tools.get(tool_id)
        return tool is not None and tool.enabled

    def validate_params(self, tool_id: str, params: dict[str, Any]) -> tuple[bool, str]:
        """Validate input parameters against the tool schema."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Tool not found: {tool_id}"
        if not tool.enabled:
            return False, f"Tool disabled: {tool_id}"
        # Check required fields
        required = tool.input_schema.required
        for field_name in required:
            if field_name not in params:
                return False, f"Missing required parameter: {field_name}"
        return True, ""

    def check_permissions(self, tool_id: str, user_permissions: list[str]) -> tuple[bool, str]:
        """Check if the caller has required permissions for the tool."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Tool not found: {tool_id}"
        for perm in tool.required_permissions:
            if perm not in user_permissions:
                return False, f"Missing permission: {perm}"
        return True, ""

    def check_classification(self, tool_id: str, user_classification: str) -> tuple[bool, str]:
        """Check if the tool classification is compatible with user clearance."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Tool not found: {tool_id}"
        levels = ["PUBLIC", "COMMUNITY", "RESTRICTED", "LAW_ENFORCEMENT", "HIGHLY_RESTRICTED"]
        try:
            tool_level = levels.index(tool.classification)
            user_level = levels.index(user_classification)
        except ValueError:
            return False, f"Invalid classification level"
        if user_level < tool_level:
            return False, f"Insufficient classification clearance"
        return True, ""

    def check_jurisdiction(self, tool_id: str, user_jurisdictions: list[str]) -> tuple[bool, str]:
        """Check if the tool is allowed in the user jurisdictions."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Tool not found: {tool_id}"
        if not tool.jurisdiction_scope:
            return True, ""  # No jurisdiction restriction
        for jur in tool.jurisdiction_scope:
            if jur in user_jurisdictions or jur == "GLOBAL":
                return True, ""
        return False, f"Tool not available in your jurisdictions"

    def get_risk_level(self, tool_id: str) -> RiskLevel:
        """Get the risk level of a tool."""
        tool = self.get_tool(tool_id)
        if not tool:
            return RiskLevel.HIGH  # Default to high if unknown
        return tool.risk_level

    def get_all_definitions(self) -> dict[str, dict[str, Any]]:
        """Get all tool definitions as dicts (for GPT context)."""
        result = {}
        for tid, tool in self._tools.items():
            if tool.enabled:
                result[tid] = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema.model_dump(),
                    "risk_level": tool.risk_level.value,
                    "version": tool.version,
                }
        return result


# ─── Default tool factory ───

def create_default_registry() -> ToolRegistry:
    """Create a ToolRegistry with all implemented GFIN tools registered.

    Only tools that are actually implemented are registered.
    Handlers are placeholder lambdas that should be replaced with real service calls.
    """
    registry = ToolRegistry()

    # Identity / Case tools
    _register_tool(registry, "create_case", "Create Case", "Create a new investigation case",
        ["case:create"], {"case_id": "string", "goal": "string"}, ["case_id", "goal"])
    _register_tool(registry, "get_case", "Get Case", "Retrieve case details",
        ["case:read"], {"case_id": "string"}, ["case_id"])
    _register_tool(registry, "update_case", "Update Case", "Update case metadata",
        ["case:update"], {"case_id": "string", "updates": "object"}, ["case_id"])
    _register_tool(registry, "list_case_entities", "List Case Entities", "List entities in a case",
        ["case:read"], {"case_id": "string"}, ["case_id"])

    # Search tools
    _register_tool(registry, "search_exact", "Exact Search", "Search for exact matches",
        ["search:read"], {"query": "string", "entity_type": "string"}, ["query"])
    _register_tool(registry, "search_fuzzy", "Fuzzy Search", "Search for fuzzy matches",
        ["search:read"], {"query": "string", "threshold": "number"}, ["query"])
    _register_tool(registry, "search_semantic", "Semantic Search", "Semantic similarity search",
        ["search:read"], {"query": "string", "limit": "integer"}, ["query"])
    _register_tool(registry, "search_temporal", "Temporal Search", "Search by time range",
        ["search:read"], {"start": "string", "end": "string"}, ["start"])

    # Domain / Infrastructure tools
    _register_tool(registry, "domain_lookup", "Domain Lookup", "Domain WHOIS/metadata lookup",
        ["domain:read"], {"domain": "string"}, ["domain"])
    _register_tool(registry, "dns_lookup", "DNS Lookup", "DNS record lookup",
        ["domain:read"], {"domain": "string", "record_type": "string"}, ["domain"])
    _register_tool(registry, "certificate_lookup", "Certificate Lookup", "TLS certificate lookup",
        ["domain:read"], {"domain": "string"}, ["domain"])
    _register_tool(registry, "ip_lookup", "IP Lookup", "IP geolocation and ASN lookup",
        ["infrastructure:read"], {"ip": "string"}, ["ip"])
    _register_tool(registry, "asn_lookup", "ASN Lookup", "ASN information lookup",
        ["infrastructure:read"], {"asn": "string"}, ["asn"])
    _register_tool(registry, "infrastructure_cluster", "Infrastructure Cluster", "Find shared infrastructure",
        ["infrastructure:read"], {"ip": "string"}, ["ip"])

    # Communications tools
    _register_tool(registry, "public_email_lookup", "Public Email Lookup", "Public email reference search",
        ["communications:read"], {"email": "string"}, ["email"])
    _register_tool(registry, "public_phone_lookup", "Public Phone Lookup", "Public phone reference search",
        ["communications:read"], {"phone": "string"}, ["phone"])

    # Graph tools
    _register_tool(registry, "get_entity", "Get Entity", "Retrieve entity from fraud graph",
        ["graph:read"], {"entity_id": "string"}, ["entity_id"])
    _register_tool(registry, "find_relationships", "Find Relationships", "Find relationships for an entity",
        ["graph:read"], {"entity_id": "string", "depth": "integer"}, ["entity_id"])
    _register_tool(registry, "expand_graph", "Expand Graph", "Expand graph around entity",
        ["graph:read"], {"entity_id": "string", "max_nodes": "integer"}, ["entity_id"])
    _register_tool(registry, "find_paths", "Find Paths", "Find paths between two entities",
        ["graph:read"], {"source_id": "string", "target_id": "string"}, ["source_id", "target_id"])
    _register_tool(registry, "compare_subgraphs", "Compare Subgraphs", "Compare two subgraphs",
        ["graph:read"], {"graph_a": "object", "graph_b": "object"}, ["graph_a", "graph_b"])

    # Evidence tools
    _register_tool(registry, "get_evidence", "Get Evidence", "Retrieve evidence by ID",
        ["evidence:read"], {"evidence_id": "string"}, ["evidence_id"])
    _register_tool(registry, "create_observation", "Create Observation", "Record a new observation",
        ["evidence:create"], {"case_id": "string", "observation": "object"}, ["case_id", "observation"])
    _register_tool(registry, "link_evidence", "Link Evidence", "Link evidence to entity",
        ["evidence:update"], {"evidence_id": "string", "entity_id": "string"}, ["evidence_id", "entity_id"])
    _register_tool(registry, "explain_relationship", "Explain Relationship", "Explain a graph relationship",
        ["graph:read"], {"relationship_id": "string"}, ["relationship_id"])
    _register_tool(registry, "explain_finding", "Explain Finding", "Explain a finding with evidence chain",
        ["evidence:read"], {"finding_id": "string"}, ["finding_id"])

    # Campaign tools
    _register_tool(registry, "campaign_similarity", "Campaign Similarity", "Compare campaign similarity",
        ["campaign:read"], {"campaign_a": "string", "campaign_b": "string"}, ["campaign_a", "campaign_b"])
    _register_tool(registry, "campaign_cluster", "Campaign Cluster", "Cluster campaigns by similarity",
        ["campaign:read"], {"campaign_ids": "array"}, ["campaign_ids"])
    _register_tool(registry, "pattern_analysis", "Pattern Analysis", "Analyze fraud patterns",
        ["campaign:read"], {"entity_ids": "array"}, ["entity_ids"])

    # Financial / Crypto tools
    _register_tool(registry, "wallet_lookup", "Wallet Lookup", "Crypto wallet lookup",
        ["crypto:read"], {"address": "string", "network": "string"}, ["address"])
    _register_tool(registry, "transaction_lookup", "Transaction Lookup", "Blockchain transaction lookup",
        ["crypto:read"], {"tx_hash": "string", "network": "string"}, ["tx_hash"])
    _register_tool(registry, "crypto_graph", "Crypto Graph", "Build crypto transaction graph",
        ["crypto:read"], {"address": "string", "depth": "integer"}, ["address"])

    return registry


def _register_tool(registry: ToolRegistry, tool_id: str, name: str, description: str,
                   permissions: list[str], properties: dict[str, str], required: list[str]) -> None:
    """Helper to register a tool with default schema."""
    from packages.brain.schemas import ToolDefinition, ToolInputSchema, ToolOutputSchema, RiskLevel

    tool = ToolDefinition(
        tool_id=tool_id,
        name=name,
        description=description,
        input_schema=ToolInputSchema(
            properties={k: {"type": v} for k, v in properties.items()},
            required=required,
        ),
        output_schema=ToolOutputSchema(),
        required_permissions=permissions,
        risk_level=RiskLevel.LOW,
    )
    # Placeholder handler — replace with real service calls
    registry.register(tool, lambda **kwargs: {"status": "not_implemented", "tool": tool_id})
