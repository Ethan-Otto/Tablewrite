"""Image generation tool using Gemini Imagen."""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from .base import BaseTool, ToolSchema, ToolResponse
from ..config import settings


class ImageGeneratorTool(BaseTool):
    """Tool for generating images using Gemini Imagen."""

    def __init__(self):
        """Initialize image generator."""
        self.output_dir = settings.IMAGE_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(settings.IMAGEN_CONCURRENT_LIMIT)

    @property
    def name(self) -> str:
        """Return tool name."""
        return "generate_images"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="generate_images",
            description="Generate images based on a text description. Use this when the user asks to create, generate, or show images.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of images to generate (default: 2, max: 4)",
                        "default": 2
                    }
                },
                "required": ["prompt"]
            }
        )

    async def execute(self, prompt: str, count: int = 2) -> ToolResponse:
        """
        Execute image generation.

        Args:
            prompt: Image description
            count: Number of images (default 2, max 4)

        Returns:
            ToolResponse with image URLs
        """
        # Cap count at maximum
        count = min(count, settings.MAX_IMAGES_PER_REQUEST)

        try:
            # Generate images concurrently
            tasks = [self._generate_single_image(prompt) for _ in range(count)]
            filenames = await asyncio.gather(*tasks)

            # Convert filenames to URLs
            image_urls = [f"/api/images/{fn}" for fn in filenames]

            return ToolResponse(
                type="image",
                message=f"Generated {count} images based on your description.",
                data={
                    "image_urls": image_urls,
                    "prompt": prompt
                }
            )

        except Exception as e:
            return ToolResponse(
                type="error",
                message=f"Failed to generate images: {str(e)}",
                data=None
            )

    async def _generate_single_image(self, prompt: str) -> str:
        """
        Generate a single image.

        Args:
            prompt: Image description

        Returns:
            Filename of generated image
        """
        async with self.semaphore:
            # TODO: Implement actual Gemini Imagen API call
            # For now, return mock filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{timestamp}_{unique_id}.png"

            # Mock: create empty file
            filepath = self.output_dir / filename
            filepath.touch()

            return filename
