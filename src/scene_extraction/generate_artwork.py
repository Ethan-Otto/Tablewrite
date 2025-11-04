"""Generate scene artwork using Gemini Imagen."""

import logging
import os
import time
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from io import BytesIO

from .models import Scene, ChapterContext

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")

IMAGEN_MODEL_NAME = "imagen-3.0-generate-002"
DEFAULT_STYLE_PROMPT = "fantasy illustration, D&D 5e art style, detailed environment, high quality"


def construct_image_prompt(
    scene: Scene,
    chapter_context: ChapterContext,
    style_prompt: Optional[str] = None
) -> str:
    """
    Construct the full prompt for image generation.

    Args:
        scene: Scene object with description and location_type
        chapter_context: Chapter environmental context
        style_prompt: Optional custom style prompt

    Returns:
        Complete prompt string for Gemini Imagen
    """
    style = style_prompt or DEFAULT_STYLE_PROMPT

    return f"""
{scene.description}

Location Type: {scene.location_type}
Lighting: {chapter_context.lighting or 'natural'}
Terrain: {chapter_context.terrain or 'varied'}
Atmosphere: {chapter_context.atmosphere or 'neutral'}

Style: {style}

IMPORTANT CONSTRAINTS:
- Do NOT include any text, words, letters, signs, or writing in the image
- Do NOT depict specific named creatures or characters (generic mobs or background townsfolk are acceptable if needed for atmosphere)
- Focus on the physical environment and location details only
- If location_type is "underground", ensure the scene clearly shows it is inside a cave/dungeon with stone walls, dim lighting, and enclosed space
"""


def generate_scene_image(
    scene: Scene,
    chapter_context: ChapterContext,
    style_prompt: Optional[str] = None
) -> tuple[bytes, str]:
    """
    Generate artwork for a scene using Gemini Imagen.

    Args:
        scene: Scene object with description
        chapter_context: Chapter environmental context
        style_prompt: Optional custom style prompt (uses default if not provided)

    Returns:
        Tuple of (image_bytes, prompt_text)
        - image_bytes: Image data as bytes (PNG format)
        - prompt_text: Full prompt sent to Gemini

    Raises:
        RuntimeError: If image generation fails
    """
    logger.info(f"Generating artwork for scene: {scene.name}")

    # Construct comprehensive prompt
    prompt = construct_image_prompt(scene, chapter_context, style_prompt)

    logger.debug(f"Image generation prompt: {prompt}")

    try:
        # Create client with API key
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Generate image using new Imagen API
        response = client.models.generate_images(
            model=IMAGEN_MODEL_NAME,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )

        # Extract image from response
        generated_image = response.generated_images[0]

        # The image object has a _pil_image attribute with the actual PIL Image
        # Convert to bytes (PNG format)
        image_buffer = BytesIO()
        generated_image.image._pil_image.save(image_buffer, format='PNG')
        image_data = image_buffer.getvalue()

        logger.info(f"Generated image for '{scene.name}' ({len(image_data)} bytes)")
        return (image_data, prompt)

    except Exception as e:
        logger.error(f"Failed to generate image for scene '{scene.name}': {e}")
        raise RuntimeError(f"Failed to generate scene image: {e}") from e


def save_scene_image(image_bytes: bytes, output_path: str) -> None:
    """
    Save image bytes to file.

    Args:
        image_bytes: Image data as bytes
        output_path: Path to save image file

    Raises:
        IOError: If file write fails
    """
    from pathlib import Path

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Saved image to {output_path}")
    except IOError as e:
        logger.error(f"Failed to save image to '{output_path}': {e}")
        raise
