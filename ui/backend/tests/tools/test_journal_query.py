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


class TestResponseFormatting:
    """Test response formatting with sources."""

    def test_format_response_with_sources(self):
        """Test formatting response with source references."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()

        sources = [
            SourceReference(
                journal_name="Lost Mine",
                journal_uuid="j1",
                chapter="Chapter 1",
                section="Cragmaw Hideout",
                page_id="page1"
            )
        ]
        links = ["@UUID[JournalEntryPage.page1]"]

        result = tool._format_response("The treasure is gold.", sources, links)

        assert "The treasure is gold." in result
        assert "**Sources:**" in result
        assert "Lost Mine > Chapter 1 > Cragmaw Hideout" in result
        assert "@UUID[JournalEntryPage.page1]" in result

    def test_format_response_minimal_source(self):
        """Test formatting with minimal source info."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()

        sources = [
            SourceReference(
                journal_name="Lost Mine",
                journal_uuid="j1",
                chapter=None,
                section=None,
                page_id="page1"
            )
        ]
        links = ["@UUID[JournalEntryPage.page1]"]

        result = tool._format_response("Answer here.", sources, links)

        assert "Answer here." in result
        assert "Lost Mine" in result
        # Should not have trailing arrows when no chapter/section
        assert "> " not in result.split("Lost Mine")[1][:5] if "Lost Mine" in result else True

    def test_build_foundry_link(self):
        """Test building Foundry page links."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        link = tool._build_foundry_link("page123")
        assert link == "@UUID[JournalEntryPage.page123]"

    def test_format_response_multiple_sources(self):
        """Test formatting with multiple source references."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()

        sources = [
            SourceReference(
                journal_name="Lost Mine",
                journal_uuid="j1",
                chapter="Chapter 1",
                section="Cragmaw Hideout",
                page_id="page1"
            ),
            SourceReference(
                journal_name="Lost Mine",
                journal_uuid="j1",
                chapter="Chapter 2",
                section="Phandalin",
                page_id="page2"
            )
        ]
        links = ["@UUID[JournalEntryPage.page1]", "@UUID[JournalEntryPage.page2]"]

        result = tool._format_response("The treasure is found in multiple locations.", sources, links)

        assert "Cragmaw Hideout" in result
        assert "Phandalin" in result
        assert "@UUID[JournalEntryPage.page1]" in result
        assert "@UUID[JournalEntryPage.page2]" in result

    def test_format_response_empty_sources(self):
        """Test formatting with empty sources list."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        result = tool._format_response("No sources found.", [], [])

        assert "No sources found." in result
        assert "**Sources:**" in result  # Header still present

    def test_format_response_chapter_only(self):
        """Test formatting with chapter but no section."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()

        sources = [
            SourceReference(
                journal_name="Lost Mine",
                journal_uuid="j1",
                chapter="Chapter 1",
                section=None,
                page_id="page1"
            )
        ]
        links = ["@UUID[JournalEntryPage.page1]"]

        result = tool._format_response("Answer here.", sources, links)

        assert "Lost Mine > Chapter 1" in result
        # Should not have extra trailing arrow
        lines = result.split("\n")
        location_line = [l for l in lines if "Lost Mine" in l and l.startswith("-")][0]
        assert location_line == "- Lost Mine > Chapter 1"


class TestContextManagement:
    """Test session context management for follow-ups."""

    def test_has_context_returns_false_for_new_session(self):
        """Test _has_context returns False for unknown session."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        assert tool._has_context("unknown-session") is False

    def test_update_and_has_context(self):
        """Test updating and checking context."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()
        session_id = "test-session-123"

        journal = {"_id": "j1", "name": "Test Journal"}
        sources = [
            SourceReference(
                journal_name="Test",
                journal_uuid="j1",
                chapter="Ch1",
                section="Sec1",
                page_id="p1"
            )
        ]

        tool._update_context(session_id, journal, sources)

        assert tool._has_context(session_id) is True

    def test_context_expiry(self):
        """Test context expires after 30 minutes."""
        from app.tools.journal_query import JournalQueryTool, JournalContext, _session_contexts
        from datetime import datetime, timedelta

        tool = JournalQueryTool()
        session_id = "expiry-test"

        # Manually set old context
        _session_contexts[session_id] = JournalContext(
            journal_uuid="j1",
            journal_name="Test",
            last_sections=["Ch1"],
            timestamp=datetime.now() - timedelta(minutes=31)
        )

        # Should return False due to expiry
        assert tool._has_context(session_id) is False
        # Should have been cleaned up
        assert session_id not in _session_contexts

    def test_get_context(self):
        """Test getting context for a session."""
        from app.tools.journal_query import JournalQueryTool, SourceReference

        tool = JournalQueryTool()
        session_id = "get-context-test"

        journal = {"_id": "j1", "name": "Test Journal"}
        sources = [
            SourceReference(
                journal_name="Test",
                journal_uuid="j1",
                chapter="Ch1",
                section="Sec1",
                page_id="p1"
            )
        ]

        tool._update_context(session_id, journal, sources)
        context = tool._get_context(session_id)

        assert context is not None
        assert context.journal_uuid == "j1"
        assert context.journal_name == "Test Journal"

    def test_get_context_returns_none_for_unknown_session(self):
        """Test _get_context returns None for unknown session."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        assert tool._get_context("nonexistent-session") is None

    def test_context_stores_last_sections(self):
        """Test that context stores the sections from sources."""
        from app.tools.journal_query import JournalQueryTool, SourceReference, _session_contexts

        tool = JournalQueryTool()
        session_id = "sections-test"

        journal = {"_id": "j1", "name": "Test Journal"}
        sources = [
            SourceReference(
                journal_name="Test",
                journal_uuid="j1",
                chapter="Ch1",
                section="Section A",
                page_id="p1"
            ),
            SourceReference(
                journal_name="Test",
                journal_uuid="j1",
                chapter="Ch1",
                section="Section B",
                page_id="p2"
            ),
            SourceReference(
                journal_name="Test",
                journal_uuid="j1",
                chapter="Ch2",
                section=None,  # No section
                page_id="p3"
            )
        ]

        tool._update_context(session_id, journal, sources)
        context = _session_contexts[session_id]

        # Should only include non-None sections
        assert "Section A" in context.last_sections
        assert "Section B" in context.last_sections
        assert None not in context.last_sections


class TestPromptBuilding:
    """Test prompt building for different query types."""

    def test_build_question_prompt(self):
        """Test building prompt for question query type."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        prompt = tool._build_prompt(
            query="What treasure is in Cragmaw Castle?",
            query_type="question",
            content="[PAGE: Chapter 3]\nCragmaw Castle contains gold and gems."
        )

        assert "What treasure is in Cragmaw Castle?" in prompt
        assert "Cragmaw Castle contains gold" in prompt
        assert "[SOURCE:" in prompt  # Should include source instruction
        assert "Answer the following question" in prompt

    def test_build_summary_prompt(self):
        """Test building prompt for summary query type."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        prompt = tool._build_prompt(
            query="Summarize Chapter 2",
            query_type="summary",
            content="[PAGE: Chapter 2]\nLots of content here."
        )

        assert "Summarize" in prompt or "summary" in prompt.lower()
        assert "Chapter 2" in prompt
        assert "Provide a concise summary" in prompt

    def test_build_extraction_prompt(self):
        """Test building prompt for extraction query type."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        prompt = tool._build_prompt(
            query="List all NPCs",
            query_type="extraction",
            content="[PAGE: Chapter 1]\nSildar Hallwinter is a human fighter."
        )

        assert "List all NPCs" in prompt or "extract" in prompt.lower()
        assert "Extract and list" in prompt

    def test_build_unknown_query_type_fallback(self):
        """Test that unknown query types use question-like fallback."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()
        prompt = tool._build_prompt(
            query="Some query",
            query_type="invalid_type",
            content="Some content"
        )

        assert "Question: Some query" in prompt
        assert "Answer:" in prompt
