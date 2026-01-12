# Journal Query Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Q&A, summary, and extraction capabilities for D&D module journals via the existing chat interface.

**Architecture:** New `JournalQueryTool` following the existing `BaseTool` pattern. Uses WebSocket functions to fetch journals from Foundry, passes content to Gemini for answering, and returns formatted responses with source references and page links.

**Tech Stack:** Python, FastAPI, Pydantic, Gemini API, BeautifulSoup for HTML parsing

---

## Task 1: Create Pydantic Models

**Files:**
- Create: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Create `ui/backend/tests/tools/test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py -v`
Expected: FAIL with "No module named 'app.tools.journal_query'"

**Step 3: Write minimal implementation**

Create `ui/backend/app/tools/journal_query.py`:

```python
"""Journal query tool for Q&A, summaries, and extraction from journals."""
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# In-memory session context storage
_session_contexts: dict[str, "JournalContext"] = {}


class JournalContext(BaseModel):
    """Context for conversational follow-ups."""
    journal_uuid: str
    journal_name: str
    last_sections: list[str]
    timestamp: datetime


class SourceReference(BaseModel):
    """Reference to source location in a journal."""
    journal_name: str
    journal_uuid: str
    chapter: Optional[str]
    section: Optional[str]
    page_id: Optional[str]
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add JournalQuery Pydantic models"
```

---

## Task 2: Create Tool Schema

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestJournalQueryToolSchema -v`
Expected: FAIL with "cannot import name 'JournalQueryTool'"

**Step 3: Write minimal implementation**

Add to `journal_query.py`:

```python
from .base import BaseTool, ToolSchema, ToolResponse


class JournalQueryTool(BaseTool):
    """Tool for querying journals for Q&A, summaries, and content extraction."""

    @property
    def name(self) -> str:
        return "query_journal"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="query_journal",
            description=(
                "Answer questions, summarize, or extract information from D&D module journals. "
                "Use when user asks about module content, NPCs, locations, treasures, encounters, "
                "or wants summaries of chapters/sections."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question or request"
                    },
                    "journal_name": {
                        "type": "string",
                        "description": "Optional - specific journal to search (if user mentioned one)"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["question", "summary", "extraction"],
                        "description": "Type of query: question for Q&A, summary for overviews, extraction for listing entities"
                    }
                },
                "required": ["query", "query_type"]
            }
        )

    async def execute(self, query: str, query_type: str, journal_name: str = None, session_id: str = None) -> ToolResponse:
        """Execute journal query."""
        # Stub for now
        return ToolResponse(
            type="text",
            message="Not implemented yet",
            data=None
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestJournalQueryToolSchema -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add JournalQueryTool schema"
```

---

## Task 3: Implement HTML Content Extraction

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestContentExtraction -v`
Expected: FAIL with "'JournalQueryTool' object has no attribute '_extract_text_with_section_markers'"

**Step 3: Write minimal implementation**

Add to `journal_query.py` (add import at top):

```python
from bs4 import BeautifulSoup
```

Add method to `JournalQueryTool` class:

```python
    def _extract_text_with_section_markers(self, journal: dict) -> tuple[str, dict]:
        """
        Parse journal HTML, preserve structure for source tracking.

        Returns:
            tuple: (extracted_text, section_to_page_id_map)
        """
        sections = []
        section_map = {}  # section_name -> page_id

        for page in journal.get("pages", []):
            page_id = page.get("_id")
            page_name = page.get("name", "")
            html_content = page.get("text", {}).get("content", "")

            # Track page for section mapping
            section_map[page_name] = page_id
            sections.append(f"\n[PAGE: {page_name}]\n")

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            for element in soup.descendants:
                if element.name == "h1":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[CHAPTER: {text}]\n")
                elif element.name == "h2":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[SECTION: {text}]\n")
                elif element.name == "h3":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[SUBSECTION: {text}]\n")
                elif element.name == "p":
                    text = element.get_text(strip=True)
                    if text:
                        sections.append(text + "\n")

        return "".join(sections), section_map
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestContentExtraction -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add HTML content extraction with section markers"
```

---

## Task 4: Implement Fuzzy Journal Matching

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestFuzzyMatching -v`
Expected: FAIL with "has no attribute '_fuzzy_match_journal'"

**Step 3: Write minimal implementation**

Add method to `JournalQueryTool` class:

```python
    def _fuzzy_match_journal(self, name: str, journals: list[dict]) -> Optional[dict]:
        """
        Fuzzy match a journal name against available journals.

        Args:
            name: Name to search for (case-insensitive substring match)
            journals: List of journal dicts with 'uuid' and 'name' keys

        Returns:
            Matching journal dict or None
        """
        name_lower = name.lower().strip()

        # Try exact match first
        for j in journals:
            if j["name"].lower() == name_lower:
                return j

        # Try substring match
        for j in journals:
            if name_lower in j["name"].lower():
                return j

        return None
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestFuzzyMatching -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add fuzzy journal name matching"
```

---

## Task 5: Implement Response Formatting

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
        # Should not have trailing arrows
        assert "Lost Mine > " not in result or "Lost Mine >" not in result

    def test_build_foundry_link(self):
        """Test building Foundry page links."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        link = tool._build_foundry_link("page123")
        assert link == "@UUID[JournalEntryPage.page123]"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestResponseFormatting -v`
Expected: FAIL with "has no attribute '_format_response'"

**Step 3: Write minimal implementation**

Add methods to `JournalQueryTool` class:

```python
    def _build_foundry_link(self, page_id: str) -> str:
        """Build a Foundry link to a specific journal page."""
        return f"@UUID[JournalEntryPage.{page_id}]"

    def _format_response(self, answer: str, sources: list[SourceReference], links: list[str]) -> str:
        """
        Format the final response with answer and sources.

        Args:
            answer: The answer text
            sources: List of source references
            links: List of Foundry page links

        Returns:
            Formatted response string
        """
        response_parts = [answer, "", "---", "**Sources:**"]

        for source, link in zip(sources, links):
            location = source.journal_name
            if source.chapter:
                location += f" > {source.chapter}"
            if source.section:
                location += f" > {source.section}"
            response_parts.append(f"- {location}")
            response_parts.append(f"  {link}")

        return "\n".join(response_parts)
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestResponseFormatting -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add response formatting with Foundry links"
```

---

## Task 6: Implement Context Management

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestContextManagement -v`
Expected: FAIL with "has no attribute '_has_context'"

**Step 3: Write minimal implementation**

Add methods to `JournalQueryTool` class:

```python
    def _has_context(self, session_id: str) -> bool:
        """Check if session has recent (non-expired) context."""
        if session_id not in _session_contexts:
            return False

        context = _session_contexts[session_id]
        # Expire after 30 minutes
        if (datetime.now() - context.timestamp).total_seconds() > 1800:
            del _session_contexts[session_id]
            return False

        return True

    def _get_context(self, session_id: str) -> Optional[JournalContext]:
        """Get context for a session if it exists and is not expired."""
        if self._has_context(session_id):
            return _session_contexts.get(session_id)
        return None

    def _update_context(self, session_id: str, journal: dict, sources: list[SourceReference]):
        """Store context for follow-up questions."""
        _session_contexts[session_id] = JournalContext(
            journal_uuid=journal["_id"],
            journal_name=journal["name"],
            last_sections=[s.section for s in sources if s.section],
            timestamp=datetime.now()
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestContextManagement -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add session context management for follow-ups"
```

---

## Task 7: Implement Full Execute Method

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestPromptBuilding -v`
Expected: FAIL with "has no attribute '_build_prompt'"

**Step 3: Write minimal implementation**

Add method to `JournalQueryTool` class:

```python
    def _build_prompt(self, query: str, query_type: str, content: str) -> str:
        """
        Build a prompt for Gemini based on query type.

        Args:
            query: User's question
            query_type: One of "question", "summary", "extraction"
            content: Extracted journal content with section markers

        Returns:
            Formatted prompt string
        """
        base_instructions = """You are a D&D module assistant. Answer based ONLY on the provided journal content.
Include [SOURCE: section name] markers in your response to indicate where information came from.

Journal Content:
"""

        if query_type == "question":
            task = f"""
Answer the following question based on the journal content above.
Be specific and cite the relevant section.

Question: {query}

Answer:"""

        elif query_type == "summary":
            task = f"""
Provide a concise summary based on the journal content above.
Focus on the key points and important details.

Request: {query}

Summary:"""

        elif query_type == "extraction":
            task = f"""
Extract and list the requested information from the journal content above.
Format as a bulleted list with section references.

Request: {query}

Extracted Information:"""

        else:
            task = f"\n\nQuestion: {query}\n\nAnswer:"

        return base_instructions + content + task
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestPromptBuilding -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add prompt building for query types"
```

---

## Task 8: Implement Source Parsing

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`
- Test: `ui/backend/tests/tools/test_journal_query.py`

**Step 1: Write the failing test**

Add to `test_journal_query.py`:

```python
class TestSourceParsing:
    """Test parsing source references from Gemini response."""

    def test_parse_single_source(self):
        """Test parsing a single source reference."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        response = "The treasure includes gold coins. [SOURCE: Cragmaw Castle]"
        journal = {"_id": "j1", "name": "Lost Mine"}
        section_map = {"Cragmaw Castle": "page1"}

        answer, sources = tool._parse_response_with_sources(response, journal, section_map)

        assert "The treasure includes gold coins" in answer
        assert len(sources) == 1
        assert sources[0].section == "Cragmaw Castle"
        assert sources[0].page_id == "page1"

    def test_parse_multiple_sources(self):
        """Test parsing multiple source references."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        response = "Info from [SOURCE: Chapter 1] and [SOURCE: Chapter 2]."
        journal = {"_id": "j1", "name": "Test"}
        section_map = {"Chapter 1": "p1", "Chapter 2": "p2"}

        answer, sources = tool._parse_response_with_sources(response, journal, section_map)

        assert len(sources) == 2

    def test_parse_no_sources(self):
        """Test parsing response with no source markers."""
        from app.tools.journal_query import JournalQueryTool

        tool = JournalQueryTool()

        response = "General answer with no specific source."
        journal = {"_id": "j1", "name": "Test"}
        section_map = {}

        answer, sources = tool._parse_response_with_sources(response, journal, section_map)

        assert answer == "General answer with no specific source."
        # Should still have at least the journal-level source
        assert len(sources) >= 1
        assert sources[0].journal_name == "Test"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestSourceParsing -v`
Expected: FAIL with "has no attribute '_parse_response_with_sources'"

**Step 3: Write minimal implementation**

Add import at top:

```python
import re
```

Add method to `JournalQueryTool` class:

```python
    def _parse_response_with_sources(
        self,
        response: str,
        journal: dict,
        section_map: dict
    ) -> tuple[str, list[SourceReference]]:
        """
        Parse Gemini response and extract source references.

        Args:
            response: Raw response from Gemini
            journal: Journal dict with _id and name
            section_map: Map of section names to page IDs

        Returns:
            tuple: (cleaned_answer, list_of_source_references)
        """
        # Find all [SOURCE: ...] markers
        source_pattern = r'\[SOURCE:\s*([^\]]+)\]'
        matches = re.findall(source_pattern, response)

        # Clean the response by removing source markers
        cleaned = re.sub(source_pattern, '', response).strip()

        sources = []
        seen_sections = set()

        for match in matches:
            section_name = match.strip()
            if section_name in seen_sections:
                continue
            seen_sections.add(section_name)

            page_id = section_map.get(section_name)

            sources.append(SourceReference(
                journal_name=journal["name"],
                journal_uuid=journal["_id"],
                chapter=None,  # Could be enhanced to detect chapters
                section=section_name,
                page_id=page_id
            ))

        # If no sources found, add journal-level reference
        if not sources:
            # Use first page as default
            first_page_id = None
            if journal.get("pages"):
                first_page_id = journal["pages"][0].get("_id")

            sources.append(SourceReference(
                journal_name=journal["name"],
                journal_uuid=journal["_id"],
                chapter=None,
                section=None,
                page_id=first_page_id
            ))

        return cleaned, sources
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py::TestSourceParsing -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/journal_query.py ui/backend/tests/tools/test_journal_query.py
git commit -m "feat(tools): add source reference parsing from Gemini response"
```

---

## Task 9: Implement Full Execute Method with Gemini

**Files:**
- Modify: `ui/backend/app/tools/journal_query.py`

**Step 1: Update execute method**

Replace the stub `execute` method with the full implementation:

```python
    async def execute(
        self,
        query: str,
        query_type: str,
        journal_name: str = None,
        session_id: str = None
    ) -> ToolResponse:
        """
        Execute journal query for Q&A, summaries, or extraction.

        Args:
            query: User's question or request
            query_type: One of "question", "summary", "extraction"
            journal_name: Optional specific journal name
            session_id: Optional session ID for context

        Returns:
            ToolResponse with answer and source references
        """
        try:
            # 1. Resolve which journal to query
            if journal_name:
                journal = await self._fetch_journal_by_name(journal_name)
            elif session_id and self._has_context(session_id):
                context = self._get_context(session_id)
                journal = await self._fetch_journal_by_uuid(context.journal_uuid)
            else:
                journal = await self._select_journal_via_gemini(query)
                if journal is None:
                    journal_names = await self._list_journal_names()
                    return ToolResponse(
                        type="clarification",
                        message=f"Which journal are you asking about?\n\nAvailable journals:\n" +
                                "\n".join(f"- {name}" for name in journal_names),
                        data={"available_journals": journal_names}
                    )

            if journal is None:
                return ToolResponse(
                    type="error",
                    message=f"Could not find journal: {journal_name or 'unknown'}",
                    data=None
                )

            # 2. Extract text content with section markers
            content, section_map = self._extract_text_with_section_markers(journal)

            # 3. Build and send prompt to Gemini
            prompt = self._build_prompt(query, query_type, content)
            response = await self._query_gemini(prompt)

            # 4. Parse response and build source references
            answer, sources = self._parse_response_with_sources(response, journal, section_map)

            # 5. Store context for follow-ups
            if session_id:
                self._update_context(session_id, journal, sources)

            # 6. Build Foundry links
            foundry_links = [
                self._build_foundry_link(s.page_id)
                for s in sources if s.page_id
            ]

            # 7. Format and return response
            formatted = self._format_response(answer, sources, foundry_links)

            return ToolResponse(
                type="text",
                message=formatted,
                data={
                    "answer": answer,
                    "sources": [s.model_dump() for s in sources],
                    "foundry_links": foundry_links,
                    "journal_name": journal["name"],
                    "journal_uuid": journal["_id"]
                }
            )

        except Exception as e:
            logger.error(f"Journal query failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to query journal: {str(e)}",
                data=None
            )

    async def _fetch_journal_by_name(self, name: str) -> Optional[dict]:
        """Fetch journal by name from Foundry."""
        journals_result = await list_journals()
        if not journals_result.success:
            return None

        journals = [{"uuid": j.uuid, "name": j.name} for j in journals_result.journals]
        matched = self._fuzzy_match_journal(name, journals)

        if matched:
            return await self._fetch_journal_by_uuid(matched["uuid"])
        return None

    async def _fetch_journal_by_uuid(self, uuid: str) -> Optional[dict]:
        """Fetch full journal content by UUID from Foundry."""
        result = await fetch_journal(uuid)
        if result.success:
            return result.entity
        return None

    async def _list_journal_names(self) -> list[str]:
        """Get list of all journal names."""
        result = await list_journals()
        if result.success:
            return [j.name for j in result.journals]
        return []

    async def _select_journal_via_gemini(self, query: str) -> Optional[dict]:
        """Ask Gemini to pick the most relevant journal."""
        journal_names = await self._list_journal_names()
        if not journal_names:
            return None

        journal_list = "\n".join(f"- {name}" for name in journal_names)

        prompt = f"""Given these available D&D module journals:
{journal_list}

User question: "{query}"

Which journal most likely contains the answer?
- If clearly one journal, respond with ONLY the exact journal name
- If unclear or could be multiple, respond with "CLARIFY"
"""

        response = await self._query_gemini(prompt)

        if "CLARIFY" in response.upper():
            return None

        # Try to match response to a journal
        journals_result = await list_journals()
        if not journals_result.success:
            return None

        journals = [{"uuid": j.uuid, "name": j.name} for j in journals_result.journals]
        matched = self._fuzzy_match_journal(response.strip(), journals)

        if matched:
            return await self._fetch_journal_by_uuid(matched["uuid"])

        return None

    async def _query_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and get response."""
        from app.services.gemini_service import GeminiService

        service = GeminiService()
        response = service.api.generate_content(prompt)
        return response.text
```

Also add the import at the top:

```python
from app.websocket import list_journals, fetch_journal
```

**Step 2: Run all unit tests**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add ui/backend/app/tools/journal_query.py
git commit -m "feat(tools): implement full execute method with Gemini integration"
```

---

## Task 10: Register Tool in Registry

**Files:**
- Modify: `ui/backend/app/tools/__init__.py`

**Step 1: Add import and registration**

Edit `ui/backend/app/tools/__init__.py`:

Add import:
```python
from .journal_query import JournalQueryTool
```

Add registration (after other registry.register calls):
```python
registry.register(JournalQueryTool())
```

Add to `__all__`:
```python
'JournalQueryTool',
```

**Step 2: Verify tool is registered**

Run: `cd ui/backend && uv run python -c "from app.tools import registry; print([t.name for t in registry.get_schemas()])"`
Expected: Output should include `'query_journal'`

**Step 3: Commit**

```bash
git add ui/backend/app/tools/__init__.py
git commit -m "feat(tools): register JournalQueryTool in registry"
```

---

## Task 11: Integration Test - Query Specific Journal

**Files:**
- Create: `ui/backend/tests/tools/test_journal_query_integration.py`

**Step 1: Write integration test**

Create `ui/backend/tests/tools/test_journal_query_integration.py`:

```python
"""Integration tests for JournalQueryTool with real Foundry and Gemini."""
import pytest
from tests.conftest import check_backend_and_foundry, get_or_create_test_folder


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_specific_journal_roundtrip():
    """
    Integration test: Create a test journal, query it, verify answer.

    1. Create a test journal with known content
    2. Query the journal with a question
    3. Verify the answer contains expected information
    4. Delete the test journal
    """
    import httpx

    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    # Create test journal with known content
    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>Test Adventure</h1>
        <h2>The Treasure Room</h2>
        <p>Inside the treasure room, the party finds a golden chalice worth 500 gold pieces
        and a magical sword called Dragonbane.</p>
        <h2>The Monster</h2>
        <p>A young red dragon named Scorchclaw guards the treasure.</p>
        """

        create_response = await client.post(
            "http://localhost:8000/api/foundry/journal",
            json={
                "name": "Test Query Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        assert create_response.status_code == 200, f"Failed to create journal: {create_response.text}"
        journal_uuid = create_response.json()["uuid"]

        try:
            # Query the journal via chat
            chat_response = await client.post(
                "http://localhost:8000/api/chat",
                json={
                    "message": "What treasure is in Test Query Journal?",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            response_data = chat_response.json()

            # Verify the response contains expected content
            message = response_data.get("message", "")
            assert "golden chalice" in message.lower() or "500 gold" in message.lower() or "dragonbane" in message.lower(), \
                f"Expected treasure info in response: {message}"

        finally:
            # Clean up: delete the test journal
            delete_response = await client.delete(
                f"http://localhost:8000/api/foundry/journal/{journal_uuid}"
            )
            assert delete_response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_summary_request():
    """Test summary query type returns condensed information."""
    import httpx

    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>Chapter 1: The Beginning</h1>
        <p>Our heroes meet in a tavern. They receive a quest from an old wizard.</p>
        <h2>The Quest</h2>
        <p>The wizard asks them to retrieve a magical artifact from a dungeon.</p>
        <h2>The Journey</h2>
        <p>The party travels through forests and over mountains.</p>
        """

        create_response = await client.post(
            "http://localhost:8000/api/foundry/journal",
            json={
                "name": "Test Summary Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        journal_uuid = create_response.json()["uuid"]

        try:
            chat_response = await client.post(
                "http://localhost:8000/api/chat",
                json={
                    "message": "Summarize Test Summary Journal",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            message = chat_response.json().get("message", "")
            # Summary should mention key elements
            assert any(word in message.lower() for word in ["wizard", "quest", "artifact", "tavern"]), \
                f"Summary should contain key story elements: {message}"

        finally:
            await client.delete(f"http://localhost:8000/api/foundry/journal/{journal_uuid}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extraction_request():
    """Test extraction query type lists entities."""
    import httpx

    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>NPCs of the Town</h1>
        <p>Sildar Hallwinter is a human knight who seeks to restore order.</p>
        <p>Gundren Rockseeker is a dwarf merchant looking for the lost mine.</p>
        <p>Sister Garaele is an elf cleric at the shrine.</p>
        """

        create_response = await client.post(
            "http://localhost:8000/api/foundry/journal",
            json={
                "name": "Test NPCs Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        journal_uuid = create_response.json()["uuid"]

        try:
            chat_response = await client.post(
                "http://localhost:8000/api/chat",
                json={
                    "message": "List all NPCs in Test NPCs Journal",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            message = chat_response.json().get("message", "")
            # Should list the NPCs
            npc_count = sum(1 for name in ["sildar", "gundren", "garaele"] if name in message.lower())
            assert npc_count >= 2, f"Should list at least 2 NPCs: {message}"

        finally:
            await client.delete(f"http://localhost:8000/api/foundry/journal/{journal_uuid}")
```

**Step 2: Run the integration test**

Run: `cd ui/backend && uv run pytest tests/tools/test_journal_query_integration.py -v`
Expected: All tests PASS (requires backend and Foundry running)

**Step 3: Commit**

```bash
git add ui/backend/tests/tools/test_journal_query_integration.py
git commit -m "test(tools): add integration tests for JournalQueryTool"
```

---

## Task 12: Run Full Test Suite

**Step 1: Run all backend tests**

Run: `cd ui/backend && uv run pytest -v`
Expected: All tests PASS

**Step 2: Run smoke tests from project root**

Run: `uv run pytest`
Expected: All smoke tests PASS

**Step 3: Run full test suite**

Run: `uv run pytest --full -x`
Expected: All tests PASS

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(tools): complete JournalQueryTool implementation

- Add Q&A, summary, and extraction query types
- Support journal selection by name or Gemini auto-select
- Include source references with Foundry page links
- Add session context for conversational follow-ups
- Integration tests with real Gemini and Foundry"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Pydantic models | journal_query.py, test_journal_query.py |
| 2 | Tool schema | journal_query.py, test_journal_query.py |
| 3 | HTML extraction | journal_query.py, test_journal_query.py |
| 4 | Fuzzy matching | journal_query.py, test_journal_query.py |
| 5 | Response formatting | journal_query.py, test_journal_query.py |
| 6 | Context management | journal_query.py, test_journal_query.py |
| 7 | Prompt building | journal_query.py, test_journal_query.py |
| 8 | Source parsing | journal_query.py, test_journal_query.py |
| 9 | Full execute | journal_query.py |
| 10 | Registry | __init__.py |
| 11 | Integration tests | test_journal_query_integration.py |
| 12 | Final verification | - |
