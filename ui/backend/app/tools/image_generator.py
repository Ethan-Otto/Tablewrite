"""Image generation tool using Gemini Imagen."""
import asyncio
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import List
from io import BytesIO
from .base import BaseTool, ToolSchema, ToolResponse
from ..config import settings

# Add project src to path for GeminiAPI
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
from util.gemini import GeminiAPI  # noqa: E402
from google.genai import types  # noqa: E402


class ImageGeneratorTool(BaseTool):
    """Tool for generating images using Gemini Imagen."""

    def __init__(self):
        """Initialize image generator."""
        self.output_dir = settings.IMAGE_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(settings.IMAGEN_CONCURRENT_LIMIT)
        self.api = GeminiAPI(model_name="imagen-3.0-generate-002")

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
        print(f"[DEBUG] ImageGenerator.execute() called with prompt='{prompt}', count={count}")

        # Cap count at maximum
        count = min(count, settings.MAX_IMAGES_PER_REQUEST)

        try:
            # Generate images concurrently
            tasks = [self._generate_single_image(prompt) for _ in range(count)]
            filenames = await asyncio.gather(*tasks)

            # Convert filenames to URLs
            image_urls = [f"/api/images/{fn}" for fn in filenames]

            response = ToolResponse(
                type="image",
                message=f"Generated {count} images based on your description.",
                data={
                    "image_urls": image_urls,
                    "prompt": prompt
                }
            )
            print(f"[DEBUG] ImageGenerator returning: {response}")
            return response

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
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{timestamp}_{unique_id}.png"
            filepath = self.output_dir / filename

            # Generate image using Gemini Imagen
            # Run blocking API call in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._generate_and_save_image,
                prompt,
                filepath
            )

            return filename

    def _generate_and_save_image(self, prompt: str, filepath: Path):
        """
        Blocking call to generate and save image.

        Args:
            prompt: Image description
            filepath: Where to save the image
        """
        # Generate image using Gemini Imagen
        response = self.api.client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )

        # Save the generated image
        if response.generated_images:
            generated_image = response.generated_images[0]
            # Extract PIL image and convert to bytes
            image_buffer = BytesIO()
            generated_image.image._pil_image.save(image_buffer, format='PNG')
            image_data = image_buffer.getvalue()

            # Write to file
            with open(filepath, 'wb') as f:
                f.write(image_data)
