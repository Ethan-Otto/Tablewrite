"""Tests for tool registry."""
import pytest
from app.tools.base import BaseTool, ToolSchema, ToolResponse
from app.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="mock_tool",
            description="A mock tool",
            parameters={"type": "object", "properties": {}}
        )

    async def execute(self, **kwargs) -> ToolResponse:
        return ToolResponse(type="text", message="Mock response")


class TestToolRegistry:
    """Test ToolRegistry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert "mock_tool" in registry.tools
        assert registry.tools["mock_tool"] == tool

    def test_get_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        schemas = registry.get_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "mock_tool"

    @pytest.mark.anyio
    async def test_execute_tool(self):
        """Test executing a tool by name."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        response = await registry.execute_tool("mock_tool")

        assert response.type == "text"
        assert response.message == "Mock response"

    @pytest.mark.anyio
    async def test_execute_unknown_tool_raises(self):
        """Test executing unknown tool raises error."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="Unknown tool"):
            await registry.execute_tool("nonexistent_tool")
