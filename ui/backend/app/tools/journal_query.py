"""Journal query tool for Q&A, summaries, and extraction from journals."""
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
