"""Journal creation tool using FoundryClient."""
import sys
from pathlib import Path
from dotenv import load_dotenv
from .base import BaseTool, ToolSchema, ToolResponse

# Add project paths for foundry module imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))  # For "from src.xxx" imports
sys.path.insert(0, str(project_root / "src"))  # For "from xxx" imports

# Load environment variables from project root before imports
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

from foundry.client import FoundryClient  # noqa: E402
from app.websocket import push_journal  # noqa: E402


class JournalCreatorTool(BaseTool):
    """Tool for creating journal entries in FoundryVTT."""

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
        """Execute journal creation."""
        try:
            # Create FoundryClient instance
            client = FoundryClient()

            # Create journal entry in FoundryVTT
            # Using create_or_replace to avoid duplicates
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.create_journal_entry(name=title, content=content)
            )

            # Extract UUID from result
            # Response format: {"entity": {"_id": "..."}, "uuid": "JournalEntry.xxx"}
            journal_uuid = result.get("uuid", "unknown")

            # Push to connected Foundry clients
            await push_journal({
                "name": title,
                "uuid": journal_uuid
            })

            # Format text response
            message = (
                f"Created journal entry **{title}**!\n\n"
                f"- **FoundryVTT UUID**: `{journal_uuid}`"
            )

            return ToolResponse(
                type="text",
                message=message,
                data=None
            )

        except ValueError as e:
            # Missing environment variables
            return ToolResponse(
                type="error",
                message=f"Configuration error: {str(e)}",
                data=None
            )
        except RuntimeError as e:
            # API request failed
            return ToolResponse(
                type="error",
                message=f"Failed to create journal: {str(e)}",
                data=None
            )
        except Exception as e:
            return ToolResponse(
                type="error",
                message=f"Unexpected error creating journal: {str(e)}",
                data=None
            )
