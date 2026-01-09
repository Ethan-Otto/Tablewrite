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
