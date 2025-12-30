"""Scene creation tool using WebSocket-only (no relay server)."""
import logging
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import push_scene

logger = logging.getLogger(__name__)


class SceneCreatorTool(BaseTool):
    """Tool for creating simple scenes in FoundryVTT via WebSocket."""

    @property
    def name(self) -> str:
        return "create_scene"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="create_scene",
            description=(
                "Create a simple scene in FoundryVTT with an optional background image. "
                "Use when user asks to create, make, or generate a scene, map, or battle map."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the scene (e.g., 'Forest Clearing', 'Dungeon Room 1')"
                    },
                    "background_image": {
                        "type": "string",
                        "description": "Optional URL or path to background image for the scene"
                    }
                },
                "required": ["name"]
            }
        )

    async def execute(self, name: str, background_image: str = None) -> ToolResponse:
        """Execute scene creation via WebSocket (no relay server)."""
        try:
            # Prepare FULL scene data for FoundryVTT
            # The Foundry module will call Scene.create(data)
            scene_data = {
                "name": name,
                "width": 3000,
                "height": 2000,
                "grid": {
                    "size": 100
                }
            }

            # Add background image if provided
            if background_image:
                scene_data["background"] = {
                    "src": background_image
                }

            # Push FULL scene data to connected Foundry clients via WebSocket
            # The Foundry module will call Scene.create(data) and return the UUID
            result = await push_scene({
                "scene": scene_data,
                "name": name,
                "background_image": background_image
            })

            if not result.success:
                logger.error(f"Failed to create scene in Foundry: {result.error}")
                return ToolResponse(
                    type="error",
                    message=f"Failed to create scene in Foundry: {result.error}",
                    data=None
                )

            logger.info(f"Created scene '{name}' in Foundry with UUID {result.uuid}")

            # Format text response with UUID
            bg_text = f"\n- **Background Image**: `{background_image}`" if background_image else ""
            message = (
                f"Created scene **{name}**!\n\n"
                f"UUID: `{result.uuid}`\n"
                f"The scene has been created in FoundryVTT.{bg_text}"
            )

            return ToolResponse(
                type="text",
                message=message,
                data={"uuid": result.uuid, "name": name}
            )

        except Exception as e:
            logger.error(f"Scene creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create scene: {str(e)}",
                data=None
            )
