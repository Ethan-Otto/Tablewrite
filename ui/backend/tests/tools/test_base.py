"""Tests for tool system base classes."""
import pytest
from app.tools.base import ToolSchema, ToolResponse, BaseTool


class TestToolSchema:
    """Test ToolSchema model."""

    def test_tool_schema_creation(self):
        """Test creating a valid tool schema."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert "param1" in schema.parameters["properties"]


class TestToolResponse:
    """Test ToolResponse model."""

    def test_tool_response_creation(self):
        """Test creating a valid tool response."""
        response = ToolResponse(
            type="text",
            message="Response message",
            data={"key": "value"}
        )

        assert response.type == "text"
        assert response.message == "Response message"
        assert response.data["key"] == "value"

    def test_tool_response_without_data(self):
        """Test tool response with no data field."""
        response = ToolResponse(
            type="error",
            message="Error occurred"
        )

        assert response.type == "error"
        assert response.data is None
