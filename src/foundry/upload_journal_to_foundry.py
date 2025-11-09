#!/usr/bin/env python3
"""Upload generated XML documents to FoundryVTT as journal entries."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundry.client import FoundryClient
from models import XMLDocument, Journal, parse_xml_file
from logging_config import setup_logging

logger = setup_logging(__name__)


def find_latest_run(runs_dir: str) -> str:
    """
    Find the most recent run directory.

    Args:
        runs_dir: Path to output/runs directory

    Returns:
        Path to latest run directory

    Raises:
        ValueError: If no run directories found
    """
    runs_path = Path(runs_dir)

    if not runs_path.exists():
        raise ValueError(f"Runs directory does not exist: {runs_dir}")

    run_dirs = [d for d in runs_path.iterdir() if d.is_dir()]

    if not run_dirs:
        raise ValueError(f"No run directories found in: {runs_dir}")

    # Sort by directory name (timestamp format YYYYMMDD_HHMMSS)
    latest = sorted(run_dirs, key=lambda d: d.name)[-1]

    logger.info(f"Latest run: {latest.name}")
    return str(latest)


def find_xml_directory(run_dir: str) -> str:
    """
    Find the XML documents directory in a run.

    Args:
        run_dir: Path to run directory

    Returns:
        Path to XML documents directory

    Raises:
        ValueError: If XML directory not found
    """
    run_path = Path(run_dir)

    # Try documents/ directory (standard location)
    xml_dir = run_path / "documents"
    if xml_dir.exists() and list(xml_dir.glob("*.xml")):
        return str(xml_dir)

    # Try root of run directory
    if list(run_path.glob("*.xml")):
        return str(run_path)

    raise ValueError(f"No XML files found in run directory: {run_dir}")


def build_image_mapping(run_dir: Path) -> Dict[str, str]:
    """
    Build image mapping from map_assets and scene_artwork directories.

    Scans for images in:
    - run_dir/map_assets/images/
    - run_dir/scene_artwork/images/

    Args:
        run_dir: Path to run directory

    Returns:
        Dictionary mapping image keys (filename without extension) to file paths
    """
    image_mapping = {}

    # Check map_assets directory
    map_assets_dir = run_dir / "map_assets" / "images"
    if map_assets_dir.exists():
        for image_file in map_assets_dir.iterdir():
            if image_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                # Use filename without extension as key
                key = image_file.stem
                image_mapping[key] = str(image_file)
                logger.debug(f"  Added map asset: {key} -> {image_file.name}")

    # Check scene_artwork directory
    scene_artwork_dir = run_dir / "scene_artwork" / "images"
    if scene_artwork_dir.exists():
        for image_file in scene_artwork_dir.iterdir():
            if image_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                # Use filename without extension as key
                key = image_file.stem
                image_mapping[key] = str(image_file)
                logger.debug(f"  Added scene artwork: {key} -> {image_file.name}")

    logger.info(f"Built image mapping with {len(image_mapping)} images")
    return image_mapping


def load_and_position_images(run_dir: Path) -> Journal:
    """Load Journal from XML and automatically position all extracted images.

    Processes:
    1. Load XMLDocument from documents/ directory
    2. Convert to Journal
    3. Add map assets with automatic positioning
    4. Add scene artwork with automatic positioning

    Args:
        run_dir: Run directory containing documents/, map_assets/, scene_artwork/

    Returns:
        Journal with all images positioned
    """
    import json

    # Load all XML documents
    xml_dir = run_dir / "documents"
    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        raise ValueError(f"No XML files found in {xml_dir}")

    # For now, merge all chapters into one Journal
    # TODO: Support multi-chapter journals properly
    journals = []
    for xml_file in xml_files:
        xml_doc = parse_xml_file(xml_file)
        journal = Journal.from_xml_document(xml_doc)
        journals.append(journal)

    # Use first journal (single-chapter workflow)
    journal = journals[0]
    logger.info(f"Loaded journal: {journal.title}")

    # Add map assets if present
    maps_metadata_file = run_dir / "map_assets" / "maps_metadata.json"
    if maps_metadata_file.exists():
        with open(maps_metadata_file) as f:
            maps_data = json.load(f)
            maps = maps_data.get("maps", [])

        if maps:
            maps_dir = run_dir / "map_assets" / "images"
            journal.add_map_assets(maps, maps_dir)
            logger.info(f"Added {len(maps)} map assets to journal")

    # Add scene artwork if present
    scenes_metadata_file = run_dir / "scene_artwork" / "scenes_metadata.json"
    if scenes_metadata_file.exists():
        with open(scenes_metadata_file) as f:
            scenes_data = json.load(f)
            scenes = scenes_data.get("scenes", [])

        if scenes:
            scenes_dir = run_dir / "scene_artwork" / "images"
            journal.add_scene_artwork(scenes, scenes_dir)
            logger.info(f"Added {len(scenes)} scene artworks to journal")
    elif (run_dir / "scene_artwork" / "images").exists():
        # Fallback to filename parsing if no metadata
        logger.warning("No scenes_metadata.json found, using filename heuristic")
        scenes_dir = run_dir / "scene_artwork" / "images"
        scenes = []
        for i, img_file in enumerate(sorted(scenes_dir.glob("scene_*.png")), start=1):
            # Extract name from filename: scene_001_forest_ambush.png -> Forest Ambush
            name_part = img_file.stem.split("_", 2)[-1] if len(img_file.stem.split("_")) > 2 else img_file.stem
            name = name_part.replace("_", " ").title()

            scenes.append({
                "section_path": f"{journal.title} → Scene {i}",
                "name": name,
                "description": ""
            })

        if scenes:
            journal.add_scene_artwork(scenes, scenes_dir)
            logger.info(f"Added {len(scenes)} scene artworks to journal (using filename heuristic)")

    return journal


def upload_scene_gallery(client: FoundryClient, run_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Upload scene artwork and create gallery journal page.

    Args:
        client: FoundryClient instance
        run_dir: Run directory (Path object)

    Returns:
        Gallery page dict or None if no scene gallery found
    """
    scene_artwork_dir = run_dir / "scene_artwork"
    images_dir = scene_artwork_dir / "images"
    gallery_file = scene_artwork_dir / "scene_gallery.html"

    if not gallery_file.exists():
        logger.info("No scene gallery found, skipping")
        return None

    logger.info("Uploading scene artwork...")

    # Upload images to FoundryVTT
    image_path_mapping = {}
    if images_dir.exists():
        image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg"))

        for image_file in image_files:
            # Upload to worlds/<client-id>/images/
            target_path = f"worlds/{client.client_id}/images/{image_file.name}"

            try:
                client.upload_file(str(image_file), target_path)
                # Map local path format to FoundryVTT path
                image_path_mapping[f"images/{image_file.name}"] = target_path
                logger.debug(f"  Uploaded {image_file.name}")
            except Exception as e:
                logger.error(f"Failed to upload {image_file.name}: {e}")

    # Update gallery HTML with FoundryVTT paths
    gallery_html = gallery_file.read_text()
    for old_path, new_path in image_path_mapping.items():
        gallery_html = gallery_html.replace(old_path, new_path)

    # Create gallery page dict
    gallery_page = {
        "name": "Scene Gallery",
        "type": "text",
        "text": {
            "content": gallery_html,
            "format": 1
        }
    }

    logger.info(f"✓ Scene gallery page created ({len(image_path_mapping)} images)")
    return gallery_page


def upload_run_to_foundry(
    run_dir: str,
    target: str = "local",
    journal_name: str = None
) -> Dict[str, Any]:
    """
    Upload XML documents from a run to FoundryVTT as a single journal with multiple pages.

    This is a pipeline function that:
    1. Finds XML files in the run directory
    2. Converts them to Journal using XMLDocument and Journal models
    3. Builds image mapping from map_assets and scene_artwork
    4. Renders Journal to HTML using to_foundry_html()
    5. Uploads to FoundryVTT using client module
    6. Optionally uploads scene gallery if present

    Args:
        run_dir: Path to run directory (contains documents/ with XML files)
        target: Target environment ('local' or 'forge')
        journal_name: Name for the journal entry (default: "D&D Module")

    Returns:
        Dict with upload statistics
    """
    logger.info(f"Uploading to FoundryVTT ({target})")

    # Find XML directory
    try:
        xml_dir = find_xml_directory(run_dir)
        logger.info(f"Found XML directory: {xml_dir}")
    except ValueError as e:
        logger.error(str(e))
        return {"uploaded": 0, "failed": 0, "errors": [str(e)]}

    # Get all XML files
    xml_files = list(Path(xml_dir).glob("*.xml"))
    if not xml_files:
        logger.warning("No XML files found")
        return {"uploaded": 0, "failed": 0}

    logger.info(f"Found {len(xml_files)} XML file(s)")

    # Build image mapping from map_assets and scene_artwork
    run_path = Path(run_dir)
    image_mapping = build_image_mapping(run_path)

    # Convert XML files to Journal pages using XMLDocument and Journal models
    pages = []
    for xml_file in xml_files:
        try:
            # Parse XML file to XMLDocument
            xml_doc = parse_xml_file(xml_file)
            logger.debug(f"  Parsed {xml_file.name} -> {xml_doc.title}")

            # Convert XMLDocument to Journal with positioned images
            journal = Journal.from_xml_document(xml_doc)

            # Add positioned images if this is the first/only chapter
            # (For multi-chapter support, this logic will need refinement)
            if len(xml_files) == 1 or xml_file == xml_files[0]:
                # Add map assets if present
                maps_metadata_file = run_path / "map_assets" / "maps_metadata.json"
                if maps_metadata_file.exists():
                    import json
                    with open(maps_metadata_file) as f:
                        maps_data = json.load(f)
                        maps = maps_data.get("maps", [])

                    if maps:
                        maps_dir = run_path / "map_assets" / "images"
                        journal.add_map_assets(maps, maps_dir)
                        logger.info(f"Added {len(maps)} map assets to journal")

                # Add scene artwork if present
                scenes_metadata_file = run_path / "scene_artwork" / "scenes_metadata.json"
                if scenes_metadata_file.exists():
                    import json
                    with open(scenes_metadata_file) as f:
                        scenes_data = json.load(f)
                        scenes = scenes_data.get("scenes", [])

                    if scenes:
                        scenes_dir = run_path / "scene_artwork" / "images"
                        journal.add_scene_artwork(scenes, scenes_dir)
                        logger.info(f"Added {len(scenes)} scene artworks to journal")

            # Render Journal to HTML using to_foundry_html()
            html = journal.to_foundry_html(image_mapping)

            # Create page dict for FoundryVTT
            pages.append({
                "name": xml_doc.title,
                "content": html
            })

            logger.debug(f"  Converted {xml_file.name} to HTML ({len(html)} chars)")

        except Exception as e:
            error_msg = f"Failed to process {xml_file.name}: {e}"
            logger.error(error_msg)
            return {"uploaded": 0, "failed": 0, "errors": [error_msg]}

    if not pages:
        logger.warning("No journal pages to upload")
        return {"uploaded": 0, "failed": 0}

    logger.info(f"Converted {len(pages)} XML file(s) to journal pages")

    # Determine journal name
    if not journal_name:
        journal_name = "D&D Module"
        logger.info(f"Using default journal name: {journal_name}")

    # Initialize client
    client = FoundryClient(target=target)

    # Add scene gallery page if present
    gallery_page = upload_scene_gallery(client, run_path)
    if gallery_page:
        pages.append(gallery_page)

    logger.info(f"Uploading journal '{journal_name}' with {len(pages)} page(s)")

    # Upload as single journal with multiple pages
    try:
        result = client.create_or_replace_journal(
            name=journal_name,
            pages=pages
        )

        # Extract UUID from response
        journal_uuid = result.get('uuid')
        if not journal_uuid:
            # Construct from entity ID if uuid not directly available
            entity = result.get('entity', {})
            if isinstance(entity, list):
                entity_id = entity[0].get('_id') if entity else None
            else:
                entity_id = entity.get('_id')

            if entity_id:
                journal_uuid = f"JournalEntry.{entity_id}"
            else:
                journal_uuid = 'unknown'

        logger.info(f"✓ Uploaded journal: {journal_name} with {len(pages)} page(s) (UUID: {journal_uuid})")

        return {
            "uploaded": len(pages),
            "failed": 0,
            "errors": [],
            "journal_uuid": journal_uuid,
            "journal_name": journal_name
        }

    except Exception as e:
        error_msg = f"✗ Failed to upload journal: {journal_name} - {e}"
        logger.error(error_msg)
        return {
            "uploaded": 0,
            "failed": len(pages),
            "errors": [error_msg],
            "journal_uuid": None,
            "journal_name": journal_name
        }


def upload_file_to_foundry(
    local_path: str,
    target_path: str,
    target: str = "local",
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Upload a file to FoundryVTT.

    Convenience wrapper around FoundryClient.upload_file() for use in pipelines.

    Args:
        local_path: Path to local file
        target_path: Target path in FoundryVTT (e.g., "worlds/my-world/assets/image.png")
        target: Target environment ('local' or 'forge')
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Upload response dict

    Raises:
        RuntimeError: If upload fails
    """
    logger.info(f"Uploading file to FoundryVTT ({target})")
    logger.debug(f"  Local:  {local_path}")
    logger.debug(f"  Target: {target_path}")

    client = FoundryClient(target=target)

    try:
        result = client.upload_file(local_path, target_path, overwrite=overwrite)
        logger.info(f"✓ File uploaded successfully")
        return result
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise


def main():
    """Main entry point for upload script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload XML documents to FoundryVTT as a single journal with multiple pages"
    )
    parser.add_argument(
        "--run-dir",
        help="Specific run directory (default: latest)"
    )
    parser.add_argument(
        "--target",
        choices=["local", "forge"],
        default="local",
        help="Target environment (default: local)"
    )
    parser.add_argument(
        "--journal-name",
        help="Name for the journal entry (default: 'D&D Module')"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Determine run directory
    if args.run_dir:
        run_dir = args.run_dir
    else:
        project_root = Path(__file__).parent.parent.parent
        runs_dir = project_root / "output" / "runs"
        run_dir = find_latest_run(str(runs_dir))

    # Upload (pipeline: find XML -> convert to journal HTML -> upload)
    try:
        result = upload_run_to_foundry(
            run_dir=run_dir,
            target=args.target,
            journal_name=args.journal_name
        )

        if result["failed"] > 0 or result.get("errors"):
            logger.error("Upload completed with errors")
            sys.exit(1)
        else:
            logger.info("Upload complete!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
