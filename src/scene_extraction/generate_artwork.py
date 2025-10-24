"""Generate scene artwork using Gemini Imagen."""

import logging
import os
from typing import Optional
import google.generativeai as genai

from .models import Scene, ChapterContext

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

IMAGEN_MODEL_NAME = "imagen-3.0-generate-001"
DEFAULT_STYLE_PROMPT = "fantasy illustration, D&D 5e art style, detailed environment, high quality"


def generate_scene_image(
    scene: Scene,
    chapter_context: ChapterContext,
    style_prompt: Optional[str] = None
) -> bytes:
    """
    Generate artwork for a scene using Gemini Imagen.

    Args:
        scene: Scene object with description
        chapter_context: Chapter environmental context
        style_prompt: Optional custom style prompt (uses default if not provided)

    Returns:
        Image data as bytes (PNG format)

    Raises:
        RuntimeError: If image generation fails
    """
    logger.info(f"Generating artwork for scene: {scene.name}")

    style = style_prompt or DEFAULT_STYLE_PROMPT

    # Construct comprehensive prompt
    prompt = f"""
{scene.description}

Environment: {chapter_context.environment_type}
Lighting: {chapter_context.lighting or 'natural'}
Terrain: {chapter_context.terrain or 'varied'}
Atmosphere: {chapter_context.atmosphere or 'neutral'}

Style: {style}
"""

    logger.debug(f"Image generation prompt: {prompt}")

    try:
        model = genai.GenerativeModel(IMAGEN_MODEL_NAME)
        response = model.generate_content(prompt)

        # Extract image data from response
        # Gemini Imagen returns image in response.candidates[0].content.parts[0].inline_data
        image_data = response._result.candidates[0].content.parts[0].inline_data.data

        logger.info(f"Generated image for '{scene.name}' ({len(image_data)} bytes)")
        return image_data

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
