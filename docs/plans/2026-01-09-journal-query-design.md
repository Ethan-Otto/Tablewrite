# Journal Query Tool Design

## Overview

Add Q&A, summary, and extraction capabilities for D&D module journals via the existing chat interface.

## User Flow

```
User asks question (e.g., "What treasure is in Cragmaw Castle?")
    ↓
Gemini detects journal-related question → calls JournalQueryTool
    ↓
Tool checks: Did user specify a journal name?
    ├─ Yes → Fetch that journal's content from Foundry
    └─ No → Check for follow-up context
              ├─ Has context → Reuse previous journal
              └─ No context → Fetch all journal titles, ask Gemini to pick
                              ├─ Gemini picks one → Fetch that journal
                              └─ Gemini unsure → Return clarification request
    ↓
Pass journal content + user question to Gemini
    ↓
Gemini generates answer with source section/chapter info
    ↓
Tool formats response with:
    - Answer text
    - Source reference (journal name, chapter, section)
    - Clickable Foundry link (@UUID[JournalEntryPage.{pageId}])
    ↓
Store context (journal UUID, last section) for follow-ups
```

## Decisions

| Aspect | Decision |
|--------|----------|
| Location | Existing chat interface |
| Journal selection | User specifies, or Gemini picks from titles |
| Search method | Full journal content to Gemini |
| Query types | Q&A, summaries, extraction |
| Integration | New JournalQueryTool (BaseTool pattern) |
| Response format | Answer + sources + page links |
| Follow-ups | In-memory context per session |

## Tool Implementation

### New File: `ui/backend/app/tools/journal_query.py`

```python
from app.tools.base import BaseTool, ToolSchema, ToolResponse
from pydantic import BaseModel
from datetime import datetime

# In-memory session context
_session_contexts: dict[str, "JournalContext"] = {}

class JournalContext(BaseModel):
    journal_uuid: str
    journal_name: str
    last_sections: list[str]
    timestamp: datetime

class SourceReference(BaseModel):
    journal_name: str
    journal_uuid: str
    chapter: str | None
    section: str | None
    page_id: str | None

class JournalQueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    foundry_links: list[str]

class JournalQueryTool(BaseTool):
    """Query journals for Q&A, summaries, and content extraction."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="query_journal",
            description="Answer questions, summarize, or extract information from D&D module journals. Use when user asks about module content, NPCs, locations, treasures, encounters, or wants summaries.",
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
                        "description": "Type of query"
                    }
                },
                "required": ["query", "query_type"]
            }
        )

    async def execute(self, params: dict, session_id: str = None) -> ToolResponse:
        query = params["query"]
        journal_name = params.get("journal_name")
        query_type = params.get("query_type", "question")

        # 1. Resolve which journal to query
        if journal_name:
            journal = await self._fetch_journal_by_name(journal_name)
        elif session_id and self._has_context(session_id):
            context = _session_contexts[session_id]
            journal = await self._fetch_journal_by_uuid(context.journal_uuid)
        else:
            journal = await self._select_journal_via_gemini(query)
            if journal is None:
                return ToolResponse(
                    type="clarification",
                    message="Which journal are you asking about?",
                    data={"available_journals": await self._list_journal_names()}
                )

        # 2. Extract text content from journal HTML with section markers
        content, section_map = self._extract_text_with_section_markers(journal)

        # 3. Send to Gemini with appropriate prompt
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

        # 7. Return formatted response
        return ToolResponse(
            type="success",
            message=self._format_response(answer, sources, foundry_links),
            data=JournalQueryResponse(
                answer=answer,
                sources=sources,
                foundry_links=foundry_links
            ).model_dump()
        )
```

### Journal Selection Logic

```python
async def _select_journal_via_gemini(self, query: str) -> dict | None:
    """Ask Gemini to pick the most relevant journal."""
    journals = await self._list_journals()

    journal_list = "\n".join(f"- {j['name']}" for j in journals)

    prompt = f"""Given these available D&D module journals:
{journal_list}

User question: "{query}"

Which journal most likely contains the answer?
- If clearly one journal, respond with just the journal name
- If unclear or could be multiple, respond with "CLARIFY"
"""

    response = await self._query_gemini(prompt)

    if "CLARIFY" in response:
        return None

    matched = self._fuzzy_match_journal(response.strip(), journals)
    if matched:
        return await self._fetch_journal_content(matched["uuid"])

    return None
```

### Content Extraction

```python
def _extract_text_with_section_markers(self, journal: dict) -> tuple[str, dict]:
    """Parse journal HTML, preserve structure for source tracking.

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

        # Parse HTML and extract with heading markers
        for element in self._parse_html(html_content):
            if element.tag == "h1":
                section_map[element.text] = page_id
                sections.append(f"\n[CHAPTER: {element.text}]\n")
            elif element.tag == "h2":
                section_map[element.text] = page_id
                sections.append(f"\n[SECTION: {element.text}]\n")
            elif element.tag == "h3":
                section_map[element.text] = page_id
                sections.append(f"\n[SUBSECTION: {element.text}]\n")
            else:
                sections.append(element.get_text())

    return "".join(sections), section_map
```

### Foundry Links

```python
def _build_foundry_link(self, page_id: str) -> str:
    """Link directly to the journal page containing the content."""
    return f"@UUID[JournalEntryPage.{page_id}]"
```

### Response Formatting

```python
def _format_response(self, answer: str, sources: list[SourceReference], links: list[str]) -> str:
    """Format the final response with answer and sources."""
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

### Context Management

```python
def _has_context(self, session_id: str) -> bool:
    """Check if session has recent context."""
    if session_id not in _session_contexts:
        return False
    context = _session_contexts[session_id]
    # Expire after 30 minutes
    if (datetime.now() - context.timestamp).total_seconds() > 1800:
        del _session_contexts[session_id]
        return False
    return True

def _update_context(self, session_id: str, journal: dict, sources: list[SourceReference]):
    """Store context for follow-up questions."""
    _session_contexts[session_id] = JournalContext(
        journal_uuid=journal["_id"],
        journal_name=journal["name"],
        last_sections=[s.section for s in sources if s.section],
        timestamp=datetime.now()
    )
```

## File Changes

### New Files
- `ui/backend/app/tools/journal_query.py` - JournalQueryTool implementation
- `tests/backend/tools/test_journal_query.py` - Unit tests
- `tests/backend/tools/test_journal_query_integration.py` - Integration tests

### Modified Files
- `ui/backend/app/tools/registry.py` - Register JournalQueryTool
- `ui/backend/app/tools/__init__.py` - Export new tool

## Testing Strategy

### Unit Tests (`tests/backend/tools/test_journal_query.py`)
- `test_extract_text_with_section_markers()` - Parse sample HTML correctly
- `test_fuzzy_match_journal()` - Name matching logic
- `test_build_foundry_link()` - Link format
- `test_format_response()` - Output formatting
- `test_context_expiry()` - 30-minute timeout

### Integration Tests (`tests/backend/tools/test_journal_query_integration.py`)
- `test_query_specific_journal()` - User names a journal, gets answer with sources
- `test_query_without_journal_name()` - Gemini selects journal from titles
- `test_summary_request()` - "Summarize chapter 2" works
- `test_extraction_request()` - "List all NPCs" extracts entities
- `test_followup_uses_context()` - Second question reuses journal context
- `test_clarification_when_ambiguous()` - Returns journal list when unclear

All integration tests use real Gemini API calls and create test resources in `/tests` folder.
