"""Journal creation tool using WebSocket-only (no relay server)."""
import logging
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import push_journal

logger = logging.getLogger(__name__)


class JournalCreatorTool(BaseTool):
    """Tool for creating journal entries in FoundryVTT via WebSocket."""

    @property
    def name(self) -> str:
        return "create_journal"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="create_journal",
            description=(
                "Create a journal entry in FoundryVTT with a title and content. "
                "Use when user asks to create, make, or write a journal entry, "
                "note, document, or lore entry."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the journal entry"
                    },
                    "content": {
                        "type": "string",
                        "description": "HTML or plain text content of the journal entry"
                    }
                },
                "required": ["title", "content"]
            }
        )

    async def execute(self, title: str, content: str) -> ToolResponse:
        """Execute journal creation via WebSocket (no relay server)."""
        try:
            # Prepare FULL journal data for FoundryVTT
            # The Foundry module will call JournalEntry.create(data)
            journal_data = {
                "name": title,
                "pages": [
                    {
                        "name": "Page 1",
                        "type": "text",
                        "text": {
                            "content": content
                        }
                    }
                ]
            }

            # Push FULL journal data to connected Foundry clients via WebSocket
            # The Foundry module will call JournalEntry.create(data) and return the UUID
            result = await push_journal({
                "journal": journal_data,
                "name": title
            })

            if not result.success:
                logger.error(f"Failed to create journal in Foundry: {result.error}")
                return ToolResponse(
                    type="error",
                    message=f"Failed to create journal in Foundry: {result.error}",
                    data=None
                )

            logger.info(f"Created journal '{title}' in Foundry with UUID {result.uuid}")

            # Format text response with UUID
            message = (
                f"Created journal entry **{title}**!\n\n"
                f"UUID: `{result.uuid}`\n"
                f"The journal has been created in FoundryVTT."
            )

            return ToolResponse(
                type="text",
                message=message,
                data={"uuid": result.uuid, "name": title}
            )

        except Exception as e:
            logger.error(f"Journal creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create journal: {str(e)}",
                data=None
            )
