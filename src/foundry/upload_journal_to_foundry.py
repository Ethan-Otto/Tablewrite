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
from foundry.xml_to_journal_html import convert_xml_directory_to_journals
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
    2. Converts them to journal HTML using xml_to_journal_html module
    3. Uploads to FoundryVTT using client module
    4. Optionally uploads scene gallery if present

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

    # Convert XML to journal data using foundry module
    try:
        journals = convert_xml_directory_to_journals(xml_dir)
        logger.info(f"Converted {len(journals)} XML files to journal pages")
    except Exception as e:
        error_msg = f"Failed to convert XML files: {e}"
        logger.error(error_msg)
        return {"uploaded": 0, "failed": 0, "errors": [error_msg]}

    if not journals:
        logger.warning("No journal pages to upload")
        return {"uploaded": 0, "failed": 0}

    # Determine journal name
    if not journal_name:
        journal_name = "D&D Module"
        logger.info(f"Using default journal name: {journal_name}")

    # Initialize client
    client = FoundryClient(target=target)

    # Build pages list from journal data
    pages = [
        {
            "name": journal["name"],
            "content": journal["html"]
        }
        for journal in journals
    ]

    # Add scene gallery page if present
    run_path = Path(run_dir)
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
