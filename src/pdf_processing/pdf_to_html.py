#!/usr/bin/env python3
"""Complete pipeline: PDF -> XML -> Maps -> HTML.

Orchestrates the full workflow for processing a D&D module PDF chapter into
a standalone HTML journal with positioned maps.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_processing.pdf_to_xml import process_chapter
from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf
from foundry.upload_journal_to_foundry import load_and_position_images
from logging_config import setup_logging

logger = setup_logging(__name__)


def process_pdf_to_html(
    pdf_path: str,
    output_dir: Optional[Path] = None,
    map_positioning_mode: str = "semantic",
    extract_maps: bool = True,
    open_html: bool = False
) -> Path:
    """Process a PDF chapter through the complete pipeline.

    Pipeline stages:
    1. PDF to XML (Gemini extraction)
    2. Map extraction (optional)
    3. Image positioning and HTML export

    Args:
        pdf_path: Path to PDF file (relative to data/pdf_sections/Lost_Mine_of_Phandelver/)
        output_dir: Optional output directory (defaults to output/runs/<timestamp>)
        map_positioning_mode: "semantic" (use Gemini to match map names) or "page" (use page numbers)
        extract_maps: Whether to extract maps (default: True)
        open_html: Whether to open HTML in browser (default: False)

    Returns:
        Path to generated HTML file

    Example:
        >>> html_path = process_pdf_to_html("02_Part_1_Goblin_Arrows.pdf")
        >>> print(f"Generated: {html_path}")
    """
    logger.info("=== PIPELINE START ===")
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Map positioning mode: {map_positioning_mode}")

    # Step 1: PDF to XML
    logger.info("Step 1: Converting PDF to XML...")
    from datetime import datetime
    from pdf_processing.pdf_to_xml import main as pdf_to_xml_main, configure_gemini, PROJECT_ROOT

    configure_gemini()

    pdf_sections_dir = os.path.join(PROJECT_ROOT, "data", "pdf_sections", "Lost_Mine_of_Phandelver")
    runs_output_dir = os.path.join(PROJECT_ROOT, "output", "runs")

    # Generate timestamp and run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(runs_output_dir) / timestamp

    # Run PDF to XML conversion
    pdf_to_xml_main(pdf_sections_dir, runs_output_dir, single_file=pdf_path)

    logger.info(f"XML saved to: {run_dir / 'documents'}")

    # Step 2: Extract maps (optional)
    if extract_maps:
        logger.info("Step 2: Extracting maps from PDF...")
        import asyncio
        from pdf_processing.image_asset_processing.extract_map_assets import save_metadata

        full_pdf_path = Path("data/pdf_sections/Lost_Mine_of_Phandelver") / pdf_path
        maps_output_dir = run_dir / "map_assets"

        maps = asyncio.run(extract_maps_from_pdf(
            pdf_path=str(full_pdf_path),
            output_dir=str(maps_output_dir)
        ))

        if maps:
            save_metadata(maps, str(maps_output_dir))
            logger.info(f"Extracted {len(maps)} maps")

        logger.info(f"Maps saved to: {maps_output_dir}")

    # Step 3: Position images and export HTML
    logger.info("Step 3: Positioning images and exporting HTML...")
    journal = load_and_position_images(run_dir, map_positioning_mode=map_positioning_mode)
    html_file = journal.export_standalone_html(run_dir / "standalone_export")
    logger.info(f"HTML saved to: {html_file}")

    # Open in browser if requested
    if open_html:
        import subprocess
        subprocess.run(["open", str(html_file)])

    logger.info("=== PIPELINE COMPLETE ===")
    return Path(html_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process D&D PDF chapter to HTML")
    parser.add_argument("--file", required=True, help="PDF filename (e.g., 02_Part_1_Goblin_Arrows.pdf)")
    parser.add_argument("--output-dir", help="Output directory (default: auto-generated)")
    parser.add_argument("--mode", choices=["semantic", "page"], default="semantic",
                        help="Map positioning mode (default: semantic)")
    parser.add_argument("--no-maps", action="store_true", help="Skip map extraction")
    parser.add_argument("--open", action="store_true", help="Open HTML in browser")

    args = parser.parse_args()

    html_path = process_pdf_to_html(
        pdf_path=args.file,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        map_positioning_mode=args.mode,
        extract_maps=not args.no_maps,
        open_html=args.open
    )

    print(f"\n✅ Success! HTML: {html_path}")
