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
        pass  # TODO: implement

    async def execute(self, description: str, challenge_rating: float = None) -> ToolResponse:
        """Execute actor creation."""
        pass  # TODO: implement
