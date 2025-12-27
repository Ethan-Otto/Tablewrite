"""PyMuPDF-based image extraction with AI classification."""
import logging
import fitz
import asyncio
from src.util.gemini import create_client

logger = logging.getLogger(__name__)

# Size thresholds
MIN_IMAGE_SIZE = 200  # Minimum width/height in pixels to avoid tiny decorative elements
PAGE_AREA_THRESHOLD = 0.10  # 10% of page area (lowered from 25% to catch more maps)


async def extract_image_with_pymupdf_async(page: fitz.Page, output_path: str, use_ai_classification: bool = True) -> bool:
    """Extract large images from PDF page using PyMuPDF with async AI classification.

    Searches for images that meet size thresholds (>10% page area AND >200x200px).
    Uses async Gemini Vision to verify images are actually maps, not decorative elements.

    Args:
        page: PyMuPDF page object
        output_path: Path to save extracted image (PNG format)
        use_ai_classification: If True, use Gemini to classify images as maps.
                               If False, use old behavior (largest image wins).

    Returns:
        True if extraction succeeded and image is a map, False otherwise
    """
    # Import here to avoid circular dependency
    from src.pdf_processing.image_asset_processing.detect_maps import is_map_image_async

    try:
        images = page.get_images()
        if not images:
            logger.debug(f"No images found on page")
            return False

        # Calculate page area threshold
        page_area = page.rect.width * page.rect.height
        area_threshold = page_area * PAGE_AREA_THRESHOLD

        # Extract all images meeting size thresholds
        doc = page.parent
        candidates = []

        for img_ref in images:
            xref = img_ref[0]
            try:
                img_info = doc.extract_image(xref)
                img_width = img_info['width']
                img_height = img_info['height']
                img_area = img_width * img_height

                # Filter 1: Must be above minimum size
                if img_width < MIN_IMAGE_SIZE or img_height < MIN_IMAGE_SIZE:
                    logger.debug(f"Skipping tiny image: {img_width}x{img_height}")
                    continue

                # Filter 2: Must occupy enough page area
                if img_area > area_threshold:
                    candidates.append((img_info, img_area, img_width, img_height))
                    logger.debug(f"Found large image: {img_width}x{img_height} ({img_area} px², {100*img_area/page_area:.1f}% of page)")
            except Exception as e:
                logger.warning(f"Failed to extract image xref {xref}: {e}")
                continue

        if not candidates:
            logger.debug(f"No images above size thresholds ({PAGE_AREA_THRESHOLD*100:.0f}% page area, {MIN_IMAGE_SIZE}x{MIN_IMAGE_SIZE}px)")
            return False

        # Sort by area (largest first)
        candidates.sort(key=lambda x: x[1], reverse=True)

        # If AI classification enabled, classify all candidates in parallel
        if use_ai_classification:
            try:
                client = create_client()  # 60s timeout for classification
            except ValueError:
                logger.warning("GeminiImageAPI not set, falling back to largest image")
                use_ai_classification = False
            else:
                logger.info(f"Classifying {len(candidates)} large image(s) with Gemini Vision (async)...")

                # Classify all in parallel
                classification_tasks = [
                    is_map_image_async(client, img_info['image'], width, height)
                    for img_info, _, width, height in candidates
                ]
                results = await asyncio.gather(*classification_tasks)

                # Find first image that's classified as a map
                for (img_info, img_area, width, height), is_map in zip(candidates, results):
                    if is_map:
                        # This is a map! Save it.
                        with open(output_path, "wb") as f:
                            f.write(img_info['image'])
                        logger.info(f"✓ Extracted map: {width}x{height} -> {output_path}")
                        return True
                    else:
                        logger.debug(f"✗ Not a map: {width}x{height} (likely background/decoration)")

                logger.info(f"No maps found among {len(candidates)} large image(s)")
                return False

        # Fallback: just use largest image
        if not use_ai_classification:
            img_info, img_area, width, height = candidates[0]
            with open(output_path, "wb") as f:
                f.write(img_info['image'])
            logger.info(f"Extracted largest image: {width}x{height} -> {output_path}")
            return True

        return False

    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return False
