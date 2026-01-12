"""Unit tests for ActorQueryTool."""
import pytest


class TestActorQueryToolSchema:
    """Test ActorQueryTool schema."""

    def test_tool_name(self):
        """Test tool has correct name."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        assert tool.name == "query_actor"

    def test_get_schema_returns_tool_schema(self):
        """Test get_schema returns valid ToolSchema."""
        from app.tools.actor_query import ActorQueryTool
        from app.tools.base import ToolSchema

        tool = ActorQueryTool()
        schema = tool.get_schema()

        assert isinstance(schema, ToolSchema)
        assert schema.name == "query_actor"
        assert "actor_uuid" in schema.parameters["properties"]
        assert "query" in schema.parameters["properties"]
        assert "query_type" in schema.parameters["properties"]

    def test_schema_query_type_enum(self):
        """Test query_type has correct enum values."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        schema = tool.get_schema()

        query_type = schema.parameters["properties"]["query_type"]
        assert query_type["enum"] == ["abilities", "combat", "general"]
