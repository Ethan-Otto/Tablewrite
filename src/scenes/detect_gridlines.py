"""AI-powered grid detection for battle map images using Gemini Vision."""

import asyncio
import json
import logging
from pathlib import Path

from PIL import Image

from util.gemini import create_client
from scenes.models import GridDetectionResult

logger = logging.getLogger(__name__)

# Default model for grid detection
DEFAULT_MODEL = "gemini-2.0-flash"

# Prompt for grid detection
GRID_DETECTION_PROMPT = """Analyze this battle map image and detect if it has a grid overlay.

Respond with JSON in this exact format:
{
    "has_grid": true/false,
    "grid_size": <integer pixels per grid square side, or null if no grid>,
    "confidence": <float 0.0-1.0>
}

Instructions:
- Look for regular repeating grid lines (squares or hexes)
- Estimate the pixel size of each grid square (side length in pixels)
- Set confidence based on how certain you are about the grid detection
- If no grid is visible, set has_grid=false and grid_size=null

Return ONLY the JSON object, no other text."""


def _strip_markdown_code_block(text: str) -> str:
    """Strip markdown code block wrappers if present."""
    text = text.strip()

    # Handle ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return text.strip()


async def detect_gridlines(
    image_path: Path,
    model_name: str = DEFAULT_MODEL
) -> GridDetectionResult:
    """
    Detect grid lines in a battle map image using Gemini Vision.

    Args:
        image_path: Path to the battle map image
        model_name: Gemini model to use (default: gemini-2.0-flash)

    Returns:
        GridDetectionResult with has_grid, grid_size, and confidence

    Raises:
        FileNotFoundError: If image_path does not exist

    Example:
        result = await detect_gridlines(Path("maps/castle.png"))
        if result.has_grid:
            print(f"Grid detected: {result.grid_size}px squares")
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    logger.info(f"Detecting grid in: {image_path}")

    # Create Gemini client
    client = create_client()

    # Load image and call API (context manager ensures proper cleanup)
    with Image.open(image_path) as image:
        # Call Gemini Vision API (synchronous call wrapped in thread)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=[image, GRID_DETECTION_PROMPT]
        )

    # Parse response
    response_text = response.text
    logger.debug(f"Raw response: {response_text}")

    # Strip markdown code block if present
    response_text = _strip_markdown_code_block(response_text)

    try:
        data = json.loads(response_text)
        result = GridDetectionResult(
            has_grid=data.get("has_grid", False),
            grid_size=data.get("grid_size"),
            confidence=data.get("confidence", 0.0)
        )
        logger.info(f"Grid detection result: has_grid={result.has_grid}, grid_size={result.grid_size}, confidence={result.confidence}")
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse grid detection response: {e}")
        logger.warning(f"Response was: {response_text}")
        # Return default no-grid result
        return GridDetectionResult(has_grid=False, grid_size=None, confidence=0.0)
