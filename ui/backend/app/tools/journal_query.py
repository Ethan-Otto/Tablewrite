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
