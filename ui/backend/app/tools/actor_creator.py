"""Actor creation tool using the public API."""
import sys
from pathlib import Path
from .base import BaseTool, ToolSchema, ToolResponse

# Add project src to path for api module
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
from api import create_actor, APIError  # noqa: E402


class ActorCreatorTool(BaseTool):
    """Tool for creating D&D actors from descriptions."""

    @property
    def name(self) -> str:
        return "create_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="create_actor",
            description=(
                "Create a D&D actor/creature in FoundryVTT from a natural "
                "language description. Use when user asks to create, make, "
                "or generate an actor, monster, NPC, or creature."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the creature"
                    },
                    "challenge_rating": {
                        "type": "number",
                        "description": "Optional CR (0.125 to 30). Omit to infer from description.",
                        "minimum": 0.125,
                        "maximum": 30
                    }
                },
                "required": ["description"]
            }
        )

    async def execute(self, description: str, challenge_rating: float = None) -> ToolResponse:
        """Execute actor creation."""
        try:
            # Call synchronous API in thread pool (non-blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                create_actor,
                description,
                challenge_rating
            )

            # Format text response
            cr_text = f"CR {result.challenge_rating}"
            message = (
                f"Created **{result.name}** ({cr_text})!\n\n"
                f"- **FoundryVTT UUID**: `{result.foundry_uuid}`\n"
                f"- **Output Directory**: `{result.output_dir}`"
            )

            return ToolResponse(
                type="text",
                message=message,
                data=None
            )

        except APIError as e:
            return ToolResponse(
                type="error",
                message=f"Failed to create actor: {str(e)}",
                data=None
            )
