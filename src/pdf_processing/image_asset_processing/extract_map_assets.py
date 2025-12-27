"""Main orchestration script for extracting map assets from D&D PDFs.

This script combines three extraction approaches:
1. PyMuPDF extraction with AI classification (for embedded images)
2. Gemini Vision detection (identifies pages with maps)
3. Gemini Imagen segmentation (for baked-in maps)

Usage:
    python extract_map_assets.py --pdf path/to/module.pdf --output output/maps/
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import fitz

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logging_config import setup_logging

from src.pdf_processing.image_asset_processing.detect_maps import detect_maps_async
from src.pdf_processing.image_asset_processing.extract_maps import extract_image_with_pymupdf_async
from src.pdf_processing.image_asset_processing.segment_maps import segment_with_imagen
from src.pdf_processing.image_asset_processing.models import MapMetadata

logger = setup_logging(__name__)

# Project root (3 levels up: image_asset_processing/ -> pdf_processing/ -> src/ -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _check_if_flattened(pdf_path: str, page_num: int) -> tuple[bool, str]:
    """Check if page is flattened (blocking operation, run in thread pool).

    Returns:
        Tuple of (is_flattened, log_message)
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # 0-indexed

    images = page.get_images()
    page_area = page.rect.width * page.rect.height
    is_flattened = False
    log_msg = ""

    if len(images) == 1:
        try:
            xref = images[0][0]
            img_info = doc.extract_image(xref)
            img_area = img_info['width'] * img_info['height']
            if img_area / page_area > 0.8:
                is_flattened = True
                log_msg = f"Detected flattened page (single image {img_info['width']}x{img_info['height']} covers {100*img_area/page_area:.0f}% of page)"
        except:
            pass

    doc.close()
    return is_flattened, log_msg


def _render_page_to_image(pdf_path: str, page_num: int) -> bytes:
    """Render PDF page to PNG image (blocking operation, run in thread pool)."""
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=150)
    page_image = pix.pil_tobytes(format="PNG")
    doc.close()
    return page_image


async def extract_single_page(pdf_path: str, page_num: int, detection, output_dir: str, chapter_name: str = None) -> MapMetadata | None:
    """Extract map from a single PDF page.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        detection: MapDetectionResult for this page
        output_dir: Directory to save extracted map
        chapter_name: Optional chapter name for metadata

    Returns:
        MapMetadata if extraction succeeded, None otherwise
    """
    logger.info(f"Processing page {page_num}: {detection.type} - {detection.name}")

    output_path = os.path.join(
        output_dir,
        f"page_{page_num:03d}_{detection.name.replace(' ', '_').lower()}.png"
    )

    # Check if page is flattened (run in thread pool to avoid blocking)
    is_flattened, log_msg = await asyncio.to_thread(_check_if_flattened, pdf_path, page_num)
    if log_msg:
        logger.info(f"  Page {page_num}: {log_msg}")

    # Try PyMuPDF extraction first (faster for embedded images)
    # Skip if page is flattened - PyMuPDF would just extract the whole page
    if not is_flattened:
        logger.info(f"  Page {page_num}: Attempting PyMuPDF extraction...")

        # Open PDF in thread pool (blocking operation)
        doc = await asyncio.to_thread(fitz.open, pdf_path)
        page = doc[page_num - 1]

        success = await extract_image_with_pymupdf_async(
            page, output_path, use_ai_classification=True
        )

        # Close in thread pool
        await asyncio.to_thread(doc.close)
    else:
        logger.info(f"  Page {page_num}: Skipping PyMuPDF (flattened page), using Imagen segmentation...")
        success = False

    metadata = None

    if success:
        logger.info(f"  Page {page_num}: ✓ Extracted with PyMuPDF -> {output_path}")
        metadata = MapMetadata(
            name=detection.name,
            chapter=chapter_name,
            page_num=page_num,
            type=detection.type,
            source="extracted"
        )
    else:
        # Fallback to Imagen segmentation for baked-in maps
        logger.info(f"  Page {page_num}: PyMuPDF failed, attempting Imagen segmentation...")

        # Render page to image (run in thread pool to avoid blocking)
        page_image = await asyncio.to_thread(_render_page_to_image, pdf_path, page_num)

        try:
            # segment_with_imagen is synchronous, run in thread pool
            await asyncio.to_thread(segment_with_imagen, page_image, detection.type, output_path)
            logger.info(f"  Page {page_num}: ✓ Segmented with Imagen -> {output_path}")
            metadata = MapMetadata(
                name=detection.name,
                chapter=chapter_name,
                page_num=page_num,
                type=detection.type,
                source="segmented"
            )
        except Exception as e:
            logger.warning(f"  Page {page_num}: ✗ Failed to segment map: {e}")

    return metadata


async def extract_maps_from_pdf(pdf_path: str, output_dir: str, chapter_name: str = None) -> list[MapMetadata]:
    """
    Extract maps from the given PDF into the output directory using a hybrid extraction pipeline.
    
    Parameters:
        pdf_path (str): Path to the source PDF file.
        output_dir (str): Directory where extracted map images and metadata will be saved.
        chapter_name (str, optional): Optional chapter identifier to attach to each map's metadata.
    
    Returns:
        list[MapMetadata]: List of MapMetadata objects for maps that were successfully extracted.
    """
    # Step 1: Detect which pages have maps
    logger.info(f"Step 1: Detecting maps in {pdf_path}...")
    detection_results = await detect_maps_async(pdf_path)

    pages_with_maps = [
        (i + 1, result) for i, result in enumerate(detection_results)
        if result.has_map
    ]

    if not pages_with_maps:
        logger.warning("No maps detected in PDF")
        return []

    logger.info(f"Found {len(pages_with_maps)} page(s) with maps")

    # Step 2: Extract maps from all pages in parallel
    logger.info(f"Step 2: Extracting maps from {len(pages_with_maps)} pages in parallel...")

    extraction_tasks = [
        extract_single_page(pdf_path, page_num, detection, output_dir, chapter_name)
        for page_num, detection in pages_with_maps
    ]

    results = await asyncio.gather(*extraction_tasks)

    # Filter out None results (failed extractions)
    extracted_maps = [m for m in results if m is not None]

    return extracted_maps


def save_metadata(maps: list[MapMetadata], output_dir: str):
    """Save extraction metadata as JSON."""
    import json

    metadata_path = os.path.join(output_dir, "maps_metadata.json")
    data = {
        "extracted_at": datetime.now().isoformat(),
        "total_maps": len(maps),
        "maps": [m.model_dump() for m in maps]
    }

    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved metadata to {metadata_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Extract map assets from D&D PDFs using hybrid AI approach"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF file"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: output/runs/<timestamp>/map_assets)"
    )
    parser.add_argument(
        "--chapter",
        default=None,
        help="Chapter name for metadata"
    )

    args = parser.parse_args()

    # Resolve paths
    pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)

    # Create output directory
    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(
            PROJECT_ROOT,
            "output",
            "runs",
            timestamp,
            "map_assets"
        )

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Extract maps
    try:
        maps = await extract_maps_from_pdf(pdf_path, output_dir, args.chapter)

        if maps:
            logger.info(f"\n{'='*60}")
            logger.info(f"EXTRACTION COMPLETE")
            logger.info(f"{'='*60}")
            logger.info(f"Total maps extracted: {len(maps)}")
            logger.info(f"  PyMuPDF extraction: {sum(1 for m in maps if m.source == 'extracted')}")
            logger.info(f"  Imagen segmentation: {sum(1 for m in maps if m.source == 'segmented')}")

            # Save metadata
            save_metadata(maps, output_dir)

            logger.info(f"\nMaps saved to: {output_dir}")
        else:
            logger.warning("No maps were extracted")

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())