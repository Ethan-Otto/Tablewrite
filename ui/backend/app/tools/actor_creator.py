"""Actor creation tool using the public API."""
import sys
from pathlib import Path
from .base import BaseTool, ToolSchema, ToolResponse

# Add project src to path for api module
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


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
        pass  # TODO: implement
