"""List scenes tool."""
import logging
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import list_scenes

logger = logging.getLogger(__name__)


class ListScenesTool(BaseTool):
    """Tool for listing all scenes in the world."""

    @property
    def name(self) -> str:
        return "list_scenes"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="list_scenes",
            description="List all scenes in the Foundry world with clickable links",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

    async def execute(self) -> ToolResponse:
        """List all scenes with Foundry links."""
        try:
            result = await list_scenes()

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to list scenes: {result.error}",
                    data=None
                )

            if not result.scenes:
                return ToolResponse(
                    type="text",
                    message="No scenes found in the world.",
                    data={"scenes": [], "count": 0}
                )

            lines = [f"**Scenes ({len(result.scenes)}):**\n"]
            for scene in result.scenes:
                lines.append(f"- @UUID[{scene.uuid}]{{{scene.name}}}")

            return ToolResponse(
                type="text",
                message="\n".join(lines),
                data={
                    "scenes": [{"uuid": s.uuid, "name": s.name, "folder": s.folder} for s in result.scenes],
                    "count": len(result.scenes)
                }
            )

        except Exception as e:
            logger.error(f"List scenes failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to list scenes: {str(e)}",
                data=None
            )
