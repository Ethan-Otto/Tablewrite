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


class TestContentExtraction:
    """Test HTML content extraction with section markers."""

    def test_extract_simple_html(self):
        """Test extracting text from simple HTML."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journal = {
            "_id": "abc123",
            "name": "Test Journal",
            "pages": [
                {
                    "_id": "page1",
                    "name": "Introduction",
                    "text": {"content": "<p>Welcome to the adventure.</p>"}
                }
            ]
        }

        content, section_map = tool._extract_text_with_section_markers(journal)

        assert "Welcome to the adventure" in content
        assert "[PAGE: Introduction]" in content
        assert section_map["Introduction"] == "page1"

    def test_extract_with_headings(self):
        """Test extracting headings as section markers."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journal = {
            "_id": "abc123",
            "name": "Test Journal",
            "pages": [
                {
                    "_id": "page1",
                    "name": "Chapter 1",
                    "text": {
                        "content": """
                        <h1>The Beginning</h1>
                        <p>Our story starts here.</p>
                        <h2>Cragmaw Hideout</h2>
                        <p>A goblin lair.</p>
                        <h3>Area 1: Cave Mouth</h3>
                        <p>The entrance.</p>
                        """
                    }
                }
            ]
        }

        content, section_map = tool._extract_text_with_section_markers(journal)

        assert "[CHAPTER: The Beginning]" in content
        assert "[SECTION: Cragmaw Hideout]" in content
        assert "[SUBSECTION: Area 1: Cave Mouth]" in content
        assert "Our story starts here" in content
        assert section_map["The Beginning"] == "page1"
        assert section_map["Cragmaw Hideout"] == "page1"

    def test_extract_multiple_pages(self):
        """Test extracting from multiple journal pages."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journal = {
            "_id": "abc123",
            "name": "Test Journal",
            "pages": [
                {
                    "_id": "page1",
                    "name": "Chapter 1",
                    "text": {"content": "<p>First chapter content.</p>"}
                },
                {
                    "_id": "page2",
                    "name": "Chapter 2",
                    "text": {"content": "<p>Second chapter content.</p>"}
                }
            ]
        }

        content, section_map = tool._extract_text_with_section_markers(journal)

        assert "[PAGE: Chapter 1]" in content
        assert "[PAGE: Chapter 2]" in content
        assert section_map["Chapter 1"] == "page1"
        assert section_map["Chapter 2"] == "page2"

    def test_extract_none_content(self):
        """Test extraction handles None content gracefully."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        journal = {
            "_id": "test",
            "name": "Test",
            "pages": [{"_id": "p1", "name": "Page", "text": {"content": None}}]
        }
        content, section_map = tool._extract_text_with_section_markers(journal)
        assert "[PAGE: Page]" in content
        assert section_map["Page"] == "p1"


class TestFuzzyMatching:
    """Test fuzzy journal name matching."""

    def test_exact_match(self):
        """Test exact name match."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journals = [
            {"uuid": "j1", "name": "Lost Mine of Phandelver"},
            {"uuid": "j2", "name": "Curse of Strahd"}
        ]

        result = tool._fuzzy_match_journal("Lost Mine of Phandelver", journals)
        assert result["uuid"] == "j1"

    def test_partial_match(self):
        """Test partial name match (case-insensitive)."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journals = [
            {"uuid": "j1", "name": "Lost Mine of Phandelver"},
            {"uuid": "j2", "name": "Curse of Strahd"}
        ]

        result = tool._fuzzy_match_journal("lost mine", journals)
        assert result["uuid"] == "j1"

    def test_no_match(self):
        """Test no match returns None."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journals = [
            {"uuid": "j1", "name": "Lost Mine of Phandelver"},
        ]

        result = tool._fuzzy_match_journal("Tomb of Horrors", journals)
        assert result is None

    def test_case_insensitive(self):
        """Test matching is case-insensitive."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        journals = [
            {"uuid": "j1", "name": "LOST MINE OF PHANDELVER"},
        ]

        result = tool._fuzzy_match_journal("lost mine of phandelver", journals)
        assert result["uuid"] == "j1"

    def test_empty_input_returns_none(self):
        """Test empty input returns None."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        journals = [{"uuid": "j1", "name": "Test Journal"}]

        assert tool._fuzzy_match_journal("", journals) is None
        assert tool._fuzzy_match_journal("   ", journals) is None

    def test_empty_journals_list(self):
        """Test empty journals list returns None."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        assert tool._fuzzy_match_journal("Test", []) is None

    def test_first_match_wins_for_ambiguous(self):
        """Test that first match is returned for ambiguous substring matches."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        journals = [
            {"uuid": "j1", "name": "Lost Mine of Phandelver"},
            {"uuid": "j2", "name": "Lost Caverns of Tsojcanth"}
        ]

        result = tool._fuzzy_match_journal("Lost", journals)
        assert result["uuid"] == "j1"  # First match wins

    def test_missing_name_key_handled(self):
        """Test journals with missing name key are handled gracefully."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        journals = [
            {"uuid": "j1"},  # Missing 'name' key
            {"uuid": "j2", "name": "Valid Journal"}
        ]

        result = tool._fuzzy_match_journal("Valid", journals)
        assert result["uuid"] == "j2"
