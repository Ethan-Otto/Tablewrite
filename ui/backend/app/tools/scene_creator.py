"""Scene creation tool using public API for full wall detection pipeline."""

import asyncio
import logging
import sys
from pathlib import Path

from .base import BaseTool, ToolSchema, ToolResponse

# Add project paths for module imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from api import create_scene, APIError  # noqa: E402

logger = logging.getLogger(__name__)


class SceneCreatorTool(BaseTool):
    """Tool for creating FoundryVTT scenes from battle map images.

    This tool uses the full scene creation pipeline including:
    - AI-powered wall detection
    - Grid detection
    - Image upload to FoundryVTT
    - Scene creation with walls
    """

    @property
    def name(self) -> str:
        return "create_scene"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="create_scene",
            description=(
                "Create a FoundryVTT scene from a battle map image with AI-powered "
                "wall detection. Use when user asks to create a scene from a map image, "
                "process a battle map, or add walls to a map."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the battle map image file (PNG, JPG, WebP)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional custom name for the scene (defaults to filename)"
                    },
                    "skip_walls": {
                        "type": "boolean",
                        "description": "If true, create scene without wall detection (default: false)",
                        "default": False
                    },
                    "grid_size": {
                        "type": "integer",
                        "description": "Grid size in pixels (auto-detected if not specified)",
                        "minimum": 10,
                        "maximum": 500
                    }
                },
                "required": ["image_path"]
            }
        )

    async def execute(
        self,
        image_path: str,
        name: str = None,
        skip_walls: bool = False,
        grid_size: int = None
    ) -> ToolResponse:
        """Execute scene creation using the public API.

        Args:
            image_path: Path to the battle map image
            name: Optional custom scene name
            skip_walls: If True, skip wall detection
            grid_size: Grid size in pixels (auto-detected if None)

        Returns:
            ToolResponse with scene details or error message
        """
        try:
            logger.info(f"Creating scene from image: {image_path}")

            # Run blocking API call in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: create_scene(
                    image_path=image_path,
                    name=name,
                    skip_wall_detection=skip_walls,
                    grid_size=grid_size
                )
            )

            logger.info(f"Created scene '{result.name}' with UUID {result.uuid}")

            # Format grid info
            grid_info = f"{result.grid_size}px" if result.grid_size else "gridless"

            # Build response message
            message = (
                f"Created scene **{result.name}**!\n\n"
                f"- **UUID**: `{result.uuid}`\n"
                f"- **Walls**: {result.wall_count}\n"
                f"- **Grid**: {grid_info}\n"
                f"- **Image**: `{result.foundry_image_path}`\n\n"
                f"The scene has been created in FoundryVTT with walls detected and applied."
            )

            return ToolResponse(
                type="text",
                message=message,
                data={
                    "uuid": result.uuid,
                    "name": result.name,
                    "wall_count": result.wall_count,
                    "grid_size": result.grid_size,
                    "foundry_image_path": result.foundry_image_path
                }
            )

        except APIError as e:
            logger.error(f"Scene creation failed (API error): {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create scene: {str(e)}",
                data=None
            )
        except Exception as e:
            logger.error(f"Scene creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create scene: {str(e)}",
                data=None
            )
