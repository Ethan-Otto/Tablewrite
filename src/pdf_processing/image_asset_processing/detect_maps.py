"""Gemini Vision-based map detection."""
import asyncio
import logging
import os
import fitz
import io
from google import genai
from google.genai import types
from typing import List
from dotenv import load_dotenv
from src.pdf_processing.image_asset_processing.models import MapDetectionResult

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


async def detect_single_page(client: genai.Client, page_image: bytes, page_num: int) -> MapDetectionResult:
    """Detect map on single PDF page using Gemini Vision.

    Args:
        client: Gemini client instance
        page_image: PDF page rendered as PNG bytes
        page_num: Page number (for logging)

    Returns:
        MapDetectionResult with detection results
    """
    prompt = """Analyze this D&D module page. Does it contain a navigation map (dungeon/wilderness overview)
or battle map (tactical grid/encounter area)?

If yes, respond with JSON:
{
  "has_map": true,
  "type": "navigation_map" or "battle_map",
  "name": "Descriptive 3-word max name"
}

If no map, respond with JSON:
{
  "has_map": false,
  "type": null,
  "name": null
}

Ignore: character portraits, item illustrations, decorative art, page decorations."""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=page_image, mime_type="image/png"),
                    prompt
                ]
            )

            # Parse JSON response
            import json
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result_data = json.loads(response_text)
            result = MapDetectionResult(**result_data)

            logger.debug(f"Page {page_num}: has_map={result.has_map}, type={result.type}, name={result.name}")
            return result

        except Exception as e:
            logger.warning(f"Page {page_num} attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                logger.error(f"Page {page_num} detection failed after {MAX_RETRIES} attempts")
                return MapDetectionResult(has_map=False, type=None, name=None)


async def detect_maps_async(pdf_path: str) -> List[MapDetectionResult]:
    """Detect maps in all pages of PDF using async Gemini Vision calls.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of MapDetectionResult, one per page
    """
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI environment variable not set")

    client = genai.Client(api_key=api_key)

    # Open PDF and render all pages to images
    doc = fitz.open(pdf_path)
    page_images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at 150 DPI for good quality
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.pil_tobytes(format="PNG")
        page_images.append((page_num + 1, img_bytes))

    doc.close()

    logger.info(f"Detecting maps in {len(page_images)} pages...")

    # Process all pages in parallel
    tasks = [detect_single_page(client, img_bytes, page_num)
             for page_num, img_bytes in page_images]
    results = await asyncio.gather(*tasks)

    maps_found = sum(1 for r in results if r.has_map)
    logger.info(f"Detection complete: {maps_found}/{len(results)} pages have maps")

    return results
