#!/usr/bin/env python3
"""
Generate scene artwork from D&D module XML.

This script:
1. Extracts chapter environmental context using Gemini
2. Identifies physical location scenes in the XML
3. Generates AI artwork for each scene using Gemini Imagen
4. Creates a FoundryVTT journal page with scene gallery
5. Saves images and gallery HTML to output directory

Usage:
    uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456
    uv run python scripts/generate_scene_art.py --xml-file output/runs/latest/documents/chapter_01.xml
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_config import setup_logging
from src.scene_extraction import (
    extract_chapter_context,
    identify_scene_locations,
    generate_scene_image,
    save_scene_image,
    create_scene_gallery_html
)

logger = setup_logging(__name__)


def sanitize_filename(name: str) -> str:
    """Convert scene name to safe filename."""
    import re
    # Remove special characters, replace spaces with underscores
    safe_name = re.sub(r'[^\w\s-]', '', name.lower())
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    return safe_name


def process_chapter(
    xml_file: Path,
    output_dir: Path,
    style_prompt: str = None
) -> dict:
    """
    Process a single chapter XML file to generate scene artwork.

    Args:
        xml_file: Path to chapter XML file
        output_dir: Directory to save images and HTML
        style_prompt: Optional custom style prompt for image generation

    Returns:
        Dict with processing statistics
    """
    logger.info(f"Processing chapter: {xml_file.name}")

    # Read XML
    xml_content = xml_file.read_text()

    # Step 1: Extract chapter context
    logger.info("Step 1: Extracting chapter environmental context...")
    context = extract_chapter_context(xml_content)
    logger.info(f"  Environment: {context.environment_type}")

    # Step 2: Identify scenes
    logger.info("Step 2: Identifying scene locations...")
    scenes = identify_scene_locations(xml_content, context)
    logger.info(f"  Found {len(scenes)} scenes")

    if not scenes:
        logger.warning("No scenes found in chapter")
        return {"scenes_found": 0, "images_generated": 0}

    # Create images directory
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Generate images
    logger.info("Step 3: Generating scene artwork...")
    image_paths = {}
    for i, scene in enumerate(scenes, start=1):
        logger.info(f"  [{i}/{len(scenes)}] Generating image for: {scene.name}")

        try:
            # Generate image
            image_bytes = generate_scene_image(scene, context, style_prompt)

            # Save image
            safe_name = sanitize_filename(scene.name)
            image_filename = f"scene_{i:03d}_{safe_name}.png"
            image_path = images_dir / image_filename
            save_scene_image(image_bytes, str(image_path))

            # Store relative path for FoundryVTT (will be updated during upload)
            image_paths[scene.name] = f"images/{image_filename}"

        except Exception as e:
            logger.error(f"Failed to generate image for '{scene.name}': {e}")
            # Continue with other scenes

    # Step 4: Create gallery HTML
    logger.info("Step 4: Creating scene gallery HTML...")
    gallery_html = create_scene_gallery_html(scenes, image_paths)

    # Save gallery HTML
    gallery_file = output_dir / "scene_gallery.html"
    gallery_file.write_text(gallery_html)
    logger.info(f"  Saved gallery to: {gallery_file}")

    return {
        "scenes_found": len(scenes),
        "images_generated": len(image_paths),
        "gallery_file": str(gallery_file)
    }


def main():
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate scene artwork from D&D module XML")
    parser.add_argument("--run-dir", help="Run directory containing documents/ folder")
    parser.add_argument("--xml-file", help="Single XML file to process")
    parser.add_argument("--style", help="Custom style prompt for image generation")
    parser.add_argument("--output-dir", help="Custom output directory (default: <run-dir>/scene_artwork)")

    args = parser.parse_args()

    if not args.run_dir and not args.xml_file:
        parser.error("Must specify either --run-dir or --xml-file")

    # Determine XML files to process
    if args.xml_file:
        xml_files = [Path(args.xml_file)]
        output_dir = Path(args.output_dir) if args.output_dir else Path(args.xml_file).parent / "scene_artwork"
    else:
        run_dir = Path(args.run_dir)
        xml_files = list((run_dir / "documents").glob("*.xml"))
        output_dir = Path(args.output_dir) if args.output_dir else run_dir / "scene_artwork"

    if not xml_files:
        logger.error("No XML files found to process")
        return 1

    logger.info(f"Found {len(xml_files)} XML files to process")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each chapter
    total_scenes = 0
    total_images = 0

    for xml_file in xml_files:
        try:
            stats = process_chapter(xml_file, output_dir, args.style)
            total_scenes += stats["scenes_found"]
            total_images += stats["images_generated"]
        except Exception as e:
            logger.error(f"Failed to process {xml_file.name}: {e}")
            continue

    # Summary
    logger.info("=" * 60)
    logger.info("Scene artwork generation complete!")
    logger.info(f"  Total scenes identified: {total_scenes}")
    logger.info(f"  Total images generated: {total_images}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
