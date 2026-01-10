"""Journal query tool for Q&A, summaries, and extraction from journals."""
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from bs4 import BeautifulSoup

from .base import BaseTool, ToolSchema, ToolResponse

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
            html_content = page.get("text", {}).get("content", "") or ""

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

    def _fuzzy_match_journal(self, name: str, journals: list[dict]) -> Optional[dict]:
        """
        Fuzzy match a journal name against available journals.

        Args:
            name: Name to search for (case-insensitive substring match)
            journals: List of journal dicts with 'uuid' and 'name' keys

        Returns:
            Matching journal dict or None. Returns first match for ambiguous cases.
        """
        if not name or not name.strip():
            return None

        name_lower = name.lower().strip()

        # Try exact match first
        for j in journals:
            j_name = j.get("name", "")
            if j_name.lower() == name_lower:
                return j

        # Try substring match (returns first match)
        for j in journals:
            j_name = j.get("name", "")
            if name_lower in j_name.lower():
                return j

        return None

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
