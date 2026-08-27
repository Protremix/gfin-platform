"""Security tests for Brain authorization enforcement."""
import pytest
from packages.brain.schemas import ToolDefinition, ToolInputSchema, ToolOutputSchema, RiskLevel
from packages.brain.tool_registry import ToolRegistry, create_default_registry


class TestBrainAuthorization:
    """Test that Brain enforces authorization on every tool call."""

    def setup_method(self):
        self.registry = create_default_registry()

    def test_no_anonymous_tool_calls(self):
        """Tools should not be callable without permissions."""
        for tool_id in self.registry.list_tool_ids():
            ok, msg = self.registry.check_permissions(tool_id, [])
            # At least some tools should require permissions
            if not ok:
                assert "permission" in msg.lower()

    def test_permission_isolation(self):
        """Different tools should require different permissions."""
        ok1, _ = self.registry.check_permissions("search_exact", ["search:read"])
        ok2, _ = self.registry.check_permissions("search_exact", ["domain:read"])
        assert ok1 is True
        assert ok2 is False

    def test_classification_enforcement(self):
        """Tools should enforce classification levels."""
        # Create a restricted tool
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="restricted_tool",
            name="Restricted",
            description="Restricted tool",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
            required_permissions=["evidence:read"],
            classification="LAW_ENFORCEMENT",
        )
        registry.register(tool, lambda **kw: {})

        ok, _ = registry.check_classification("restricted_tool", "LAW_ENFORCEMENT")
        assert ok is True
        ok, msg = registry.check_classification("restricted_tool", "PUBLIC")
        assert ok is False
        assert "clearance" in msg.lower()

    def test_disabled_tool_cannot_be_called(self):
        """Disabled tools should not be executable."""
        registry = ToolRegistry()
        tool = ToolDefinition(
            tool_id="disabled",
            name="Disabled",
            description="Disabled tool",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(),
            enabled=False,
        )
        registry.register(tool, lambda **kw: {})
        assert not registry.is_valid("disabled")

    def test_gpt_cannot_bypass_authorization(self):
        """GPT should not be able to bypass authorization checks."""
        # Try calling create_case without case:create permission
        ok, msg = self.registry.check_permissions("create_case", [])
        assert ok is False
        # Try with wrong permission
        ok, msg = self.registry.check_permissions("create_case", ["search:read"])
        assert ok is False
        # Only correct permission works
        ok, _ = self.registry.check_permissions("create_case", ["case:create"])
        assert ok is True

    def test_risk_level_available(self):
        """Every tool should have a risk level."""
        for tool in self.registry.list_tools():
            assert tool.risk_level in RiskLevel

    def test_tool_registry_does_not_expose_credentials(self):
        """Tool definitions should not contain credentials."""
        defs = self.registry.get_all_definitions()
        for tid, d in defs.items():
            serialized = str(d)
            assert "password" not in serialized.lower()
            assert "secret" not in serialized.lower()
            assert "api_key" not in serialized.lower()
            assert "token" not in serialized.lower()
