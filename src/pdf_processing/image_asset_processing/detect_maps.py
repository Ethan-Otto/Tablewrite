"""Gemini Vision-based map detection."""
import asyncio
import logging
import fitz
import io
from google import genai
from google.genai import types
from typing import List
from src.pdf_processing.image_asset_processing.models import MapDetectionResult
from src.util.gemini import create_client

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
    prompt = """Analyze this D&D module page. Does it contain a FUNCTIONAL navigation map (dungeon/wilderness overview)
or battle map (tactical grid/encounter area)?

FUNCTIONAL MAP = The primary content is a usable map for gameplay (floor plans, terrain, tactical grids)

NOT A MAP:
- Maps shown as props in artwork (character holding a map, map on a table)
- Maps as decorative elements in scene illustrations
- Character portraits, item illustrations, decorative art, page decorations

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
}"""

    for attempt in range(MAX_RETRIES):
        try:
            # Wrap blocking Gemini call in asyncio.to_thread() for true parallelization
            response = await asyncio.to_thread(
                client.models.generate_content,
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


async def is_map_image_async(client: genai.Client, image_bytes: bytes, width: int, height: int) -> bool:
    """Asynchronously check if an image is a map using Gemini Vision.

    This is a simpler version of detect_single_page for classifying
    individual extracted images from PyMuPDF.

    Args:
        client: Gemini client instance
        image_bytes: Image as bytes (PNG/JPEG format)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        True if the image is a navigation or battle map, False otherwise
    """
    prompt = """Is this image a FUNCTIONAL D&D navigation map or battle map?

FUNCTIONAL MAP = The image is a usable map for gameplay:
- Navigation maps: dungeon layouts, wilderness areas, floor plans, geographical features
- Battle maps: tactical grids, encounter areas, combat spaces

NOT A MAP:
- Maps shown as props in artwork (character holding map, map on table)
- Maps as decorative elements in illustrations
- Background textures, decorative borders, character portraits, item art

Respond with JSON: {"is_map": true} or {"is_map": false}"""

    try:
        # Wrap blocking Gemini call in asyncio.to_thread() for true parallelization
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt
            ]
        )

        import json
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)
        is_map = result.get("is_map", False)

        logger.debug(f"Image classification ({width}x{height}): is_map={is_map}")
        return is_map

    except Exception as e:
        logger.warning(f"Image classification failed: {e}")
        return False


def _render_single_page(pdf_path: str, page_num: int) -> tuple[int, bytes]:
    """Render a single PDF page to PNG bytes (blocking operation for thread pool)."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.pil_tobytes(format="PNG")
    doc.close()
    return (page_num + 1, img_bytes)  # Return 1-indexed page number


async def detect_maps_async(pdf_path: str) -> List[MapDetectionResult]:
    """Detect maps in all pages of PDF using async Gemini Vision calls.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of MapDetectionResult, one per page
    """
    client = create_client()  # 60s timeout for text detection

    # Get page count
    doc = await asyncio.to_thread(fitz.open, pdf_path)
    page_count = len(doc)
    await asyncio.to_thread(doc.close)

    # Render all pages in parallel using thread pool
    logger.debug(f"Rendering {page_count} pages in parallel...")
    import time
    start_render = time.time()
    render_tasks = [
        asyncio.to_thread(_render_single_page, pdf_path, page_num)
        for page_num in range(page_count)
    ]
    page_images = await asyncio.gather(*render_tasks)
    render_time = time.time() - start_render
    logger.debug(f"Rendered {page_count} pages in {render_time:.1f}s")

    logger.info(f"Detecting maps in {len(page_images)} pages...")

    # Process all pages in parallel
    start_detect = time.time()
    tasks = [detect_single_page(client, img_bytes, page_num)
             for page_num, img_bytes in page_images]
    results = await asyncio.gather(*tasks)
    detect_time = time.time() - start_detect
    logger.debug(f"Gemini detection calls completed in {detect_time:.1f}s")

    maps_found = sum(1 for r in results if r.has_map)
    logger.info(f"Detection complete: {maps_found}/{len(results)} pages have maps")

    return results
