#!/usr/bin/env python3
"""Upload generated HTML files to FoundryVTT as journal entries."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundry.client import FoundryClient
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


def read_html_files(html_dir: str) -> List[Dict[str, str]]:
    """
    Read all HTML files from directory.

    Args:
        html_dir: Path to HTML directory

    Returns:
        List of dicts with 'name' and 'content' keys
    """
    html_path = Path(html_dir)

    if not html_path.exists():
        raise ValueError(f"HTML directory does not exist: {html_dir}")

    html_files = []

    for html_file in sorted(html_path.glob("*.html")):
        name = html_file.stem  # Filename without extension
        content = html_file.read_text(encoding="utf-8")

        html_files.append({
            "name": name,
            "content": content,
            "path": str(html_file)
        })

        logger.debug(f"Read HTML file: {name} ({len(content)} chars)")

    logger.info(f"Found {len(html_files)} HTML files")
    return html_files


def upload_run_to_foundry(
    html_dir: str,
    target: str = "local",
    journal_name: str = None
) -> Dict[str, Any]:
    """
    Upload all HTML files from a run to FoundryVTT as a single journal with multiple pages.

    Args:
        html_dir: Path to HTML directory
        target: Target environment ('local' or 'forge')
        journal_name: Name for the journal entry (default: derived from directory)

    Returns:
        Dict with upload statistics
    """
    logger.info(f"Uploading to FoundryVTT ({target})")

    # Read HTML files
    html_files = read_html_files(html_dir)

    if not html_files:
        logger.warning("No HTML files to upload")
        return {"uploaded": 0, "failed": 0}

    # Determine journal name
    if not journal_name:
        # Try to extract module name from path structure
        # Path is typically: output/runs/<timestamp>/documents/html/
        html_path = Path(html_dir)
        run_dir = html_path.parent.parent  # Go up from html -> documents -> run_dir
        # For now, use a generic name - could be enhanced to read from config
        journal_name = "D&D Module"
        logger.info(f"Using journal name: {journal_name}")

    # Initialize client
    client = FoundryClient(target=target)

    # Build pages list from HTML files
    pages = [
        {
            "name": html_file["name"],
            "content": html_file["content"]
        }
        for html_file in html_files
    ]

    logger.info(f"Creating journal '{journal_name}' with {len(pages)} page(s)")

    # Upload as single journal with multiple pages
    try:
        result = client.create_or_update_journal(
            name=journal_name,
            pages=pages
        )

        # Extract ID from response
        entity = result.get('entity', {})
        if isinstance(entity, list):
            entity_id = entity[0].get('_id') if entity else result.get('uuid', 'unknown')
        else:
            entity_id = entity.get('_id') or result.get('uuid', 'unknown')

        logger.info(f"✓ Uploaded journal: {journal_name} with {len(pages)} page(s) (ID: {entity_id})")

        return {
            "uploaded": len(pages),
            "failed": 0,
            "errors": []
        }

    except Exception as e:
        error_msg = f"✗ Failed to upload journal: {journal_name} - {e}"
        logger.error(error_msg)
        return {
            "uploaded": 0,
            "failed": len(pages),
            "errors": [error_msg]
        }


def main():
    """Main entry point for upload script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload HTML files to FoundryVTT as a single journal with multiple pages"
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

    # Find HTML directory
    html_dir = Path(run_dir) / "documents" / "html"

    if not html_dir.exists():
        logger.error(f"HTML directory not found: {html_dir}")
        sys.exit(1)

    # Upload
    try:
        result = upload_run_to_foundry(
            str(html_dir),
            target=args.target,
            journal_name=args.journal_name
        )

        if result["failed"] > 0:
            sys.exit(1)
        else:
            logger.info("Upload complete!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
