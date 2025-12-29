"""Scene creation tool for FoundryVTT."""
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
from app.websocket import push_scene  # noqa: E402


class SceneCreatorTool(BaseTool):
    """Tool for creating simple scenes in FoundryVTT."""

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
        """Execute scene creation."""
        try:
            # Initialize Foundry client
            client = FoundryClient()

            # Create scene in FoundryVTT
            import asyncio
            loop = asyncio.get_event_loop()

            # Run synchronous Foundry API call in thread pool (non-blocking)
            result = await loop.run_in_executor(
                None,
                lambda: client.scenes.create_scene(
                    name=name,
                    background_image=background_image
                )
            )

            scene_uuid = result.get("uuid")

            # Push to connected Foundry clients
            await push_scene({
                "name": name,
                "uuid": scene_uuid,
                "background_image": background_image
            })

            # Format text response
            bg_text = f"\n- **Background Image**: `{background_image}`" if background_image else ""
            message = (
                f"Created scene **{name}**!\n\n"
                f"- **FoundryVTT UUID**: `{scene_uuid}`{bg_text}"
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
                message=f"FoundryVTT configuration error: {str(e)}",
                data=None
            )
        except RuntimeError as e:
            # API call failed
            return ToolResponse(
                type="error",
                message=f"Failed to create scene: {str(e)}",
                data=None
            )
        except Exception as e:
            return ToolResponse(
                type="error",
                message=f"Unexpected error creating scene: {str(e)}",
                data=None
            )
