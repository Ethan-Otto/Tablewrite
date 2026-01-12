"""List actors tool."""
import logging
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import list_actors

logger = logging.getLogger(__name__)


class ListActorsTool(BaseTool):
    """Tool for listing all actors in the world."""

    @property
    def name(self) -> str:
        return "list_actors"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="list_actors",
            description="List all actors in the Foundry world with clickable links",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

    async def execute(self) -> ToolResponse:
        """List all actors with Foundry links."""
        try:
            result = await list_actors()

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to list actors: {result.error}",
                    data=None
                )

            if not result.actors:
                return ToolResponse(
                    type="text",
                    message="No actors found in the world.",
                    data={"actors": [], "count": 0}
                )

            lines = [f"**Actors ({len(result.actors)}):**\n"]
            for actor in result.actors:
                lines.append(f"- @UUID[{actor.uuid}]{{{actor.name}}}")

            return ToolResponse(
                type="text",
                message="\n".join(lines),
                data={
                    "actors": [{"uuid": a.uuid, "name": a.name, "folder": a.folder} for a in result.actors],
                    "count": len(result.actors)
                }
            )

        except Exception as e:
            logger.error(f"List actors failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to list actors: {str(e)}",
                data=None
            )
