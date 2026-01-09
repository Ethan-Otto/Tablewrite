"""Unit tests for JournalQueryTool."""
import pytest
from datetime import datetime, timedelta


class TestJournalQueryModels:
    """Test Pydantic models for journal query."""

    def test_journal_context_model(self):
        """Test JournalContext model creation."""
        from app.tools.journal_query import JournalContext

        context = JournalContext(
            journal_uuid="JournalEntry.abc123",
            journal_name="Lost Mine of Phandelver",
            last_sections=["Chapter 1", "Cragmaw Hideout"],
            timestamp=datetime.now()
        )

        assert context.journal_uuid == "JournalEntry.abc123"
        assert context.journal_name == "Lost Mine of Phandelver"
        assert len(context.last_sections) == 2

    def test_source_reference_model(self):
        """Test SourceReference model creation."""
        from app.tools.journal_query import SourceReference

        source = SourceReference(
            journal_name="Lost Mine of Phandelver",
            journal_uuid="JournalEntry.abc123",
            chapter="Chapter 1",
            section="Cragmaw Hideout",
            page_id="page123"
        )

        assert source.journal_name == "Lost Mine of Phandelver"
        assert source.page_id == "page123"

    def test_source_reference_optional_fields(self):
        """Test SourceReference with optional fields as None."""
        from app.tools.journal_query import SourceReference

        source = SourceReference(
            journal_name="Test Journal",
            journal_uuid="JournalEntry.xyz",
            chapter=None,
            section=None,
            page_id=None
        )

        assert source.chapter is None
        assert source.section is None


class TestJournalQueryToolSchema:
    """Test JournalQueryTool schema."""

    def test_tool_name(self):
        """Test tool has correct name."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        assert tool.name == "query_journal"

    def test_get_schema_returns_tool_schema(self):
        """Test get_schema returns valid ToolSchema."""
        from app.tools.journal_query import JournalQueryTool
        from app.tools.base import ToolSchema

        tool = JournalQueryTool()
        schema = tool.get_schema()

        assert isinstance(schema, ToolSchema)
        assert schema.name == "query_journal"
        assert "query" in schema.parameters["properties"]
        assert "journal_name" in schema.parameters["properties"]
        assert "query_type" in schema.parameters["properties"]

    def test_schema_query_type_enum(self):
        """Test query_type has correct enum values."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        schema = tool.get_schema()

        query_type = schema.parameters["properties"]["query_type"]
        assert query_type["enum"] == ["question", "summary", "extraction"]
