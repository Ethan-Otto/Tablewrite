#!/usr/bin/env python3
"""
Orchestration script: Convert XML to HTML and optionally upload to FoundryVTT.

This script coordinates the workflow:
1. Run xml_to_html.py to convert XML to HTML (or use existing run)
2. If FOUNDRY_AUTO_UPLOAD=true, upload HTML files to FoundryVTT

Keeps xml_to_html.py and upload_to_foundry.py decoupled.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_config import setup_logging

logger = setup_logging(__name__)


def run_xml_to_html(project_root: Path) -> Path:
    """
    Run xml_to_html.py conversion script.

    Args:
        project_root: Project root directory

    Returns:
        Path to the generated HTML directory

    Raises:
        RuntimeError: If conversion fails
    """
    xml_to_html_script = project_root / "src" / "pdf_processing" / "xml_to_html.py"

    logger.info("Running XML to HTML conversion...")

    try:
        result = subprocess.run(
            [sys.executable, str(xml_to_html_script)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"XML to HTML conversion failed: {result.stderr}")
            raise RuntimeError(f"xml_to_html.py failed with code {result.returncode}")

        logger.info("XML to HTML conversion completed successfully")
        logger.debug(f"Output: {result.stdout}")

        # Find the latest run directory
        runs_dir = project_root / "output" / "runs"
        if not runs_dir.exists():
            raise RuntimeError("No runs directory found after conversion")

        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not run_dirs:
            raise RuntimeError("No run directories found after conversion")

        latest_run = sorted(run_dirs, key=lambda d: d.name)[-1]
        html_dir = latest_run / "documents" / "html"

        if not html_dir.exists():
            raise RuntimeError(f"HTML directory not found: {html_dir}")

        logger.info(f"HTML files generated in: {html_dir}")
        return html_dir

    except subprocess.TimeoutExpired:
        logger.error("XML to HTML conversion timed out after 10 minutes")
        raise RuntimeError("Conversion timed out")
    except Exception as e:
        logger.error(f"Failed to run xml_to_html.py: {e}")
        raise


def upload_to_foundry(html_dir: Path, target: str = "local") -> dict:
    """
    Upload HTML files to FoundryVTT.

    Args:
        html_dir: Path to HTML directory
        target: Target environment ('local' or 'forge')

    Returns:
        Upload statistics dict

    Raises:
        RuntimeError: If upload fails
    """
    logger.info(f"Uploading to FoundryVTT ({target})...")

    # Import here to avoid circular dependencies
    from src.foundry.upload_journal_to_foundry import upload_run_to_foundry

    try:
        result = upload_run_to_foundry(str(html_dir), target=target)

        if result["failed"] > 0:
            logger.warning(
                f"Upload completed with errors: "
                f"{result['uploaded']} succeeded, {result['failed']} failed"
            )
        else:
            logger.info(f"Successfully uploaded {result['uploaded']} journals to FoundryVTT")

        return result

    except Exception as e:
        logger.error(f"Upload to FoundryVTT failed: {e}")
        raise RuntimeError(f"Upload failed: {e}")


def main():
    """Main entry point for orchestration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert XML to HTML and optionally upload to FoundryVTT"
    )
    parser.add_argument(
        "--skip-conversion",
        action="store_true",
        help="Skip XML to HTML conversion, use latest run"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload to FoundryVTT after conversion (overrides FOUNDRY_AUTO_UPLOAD)"
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip upload even if FOUNDRY_AUTO_UPLOAD=true"
    )
    parser.add_argument(
        "--target",
        choices=["local", "forge"],
        default="local",
        help="Target FoundryVTT environment (default: local)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Determine project root
    project_root = Path(__file__).parent.parent

    try:
        # Step 1: XML to HTML conversion
        if args.skip_conversion:
            logger.info("Skipping conversion, using latest run...")
            runs_dir = project_root / "output" / "runs"

            if not runs_dir.exists():
                logger.error("No runs directory found")
                sys.exit(1)

            run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
            if not run_dirs:
                logger.error("No run directories found")
                sys.exit(1)

            latest_run = sorted(run_dirs, key=lambda d: d.name)[-1]
            html_dir = latest_run / "documents" / "html"

            if not html_dir.exists():
                logger.error(f"HTML directory not found in latest run: {html_dir}")
                sys.exit(1)

            logger.info(f"Using HTML from: {html_dir}")
        else:
            html_dir = run_xml_to_html(project_root)

        # Step 2: Upload to FoundryVTT (if enabled)
        should_upload = False

        if args.no_upload:
            logger.info("Upload disabled via --no-upload flag")
        elif args.upload:
            logger.info("Upload enabled via --upload flag")
            should_upload = True
        else:
            # Check environment variable
            auto_upload = os.getenv("FOUNDRY_AUTO_UPLOAD", "false").lower() == "true"
            if auto_upload:
                logger.info("Auto-upload enabled via FOUNDRY_AUTO_UPLOAD=true")
                should_upload = True
            else:
                logger.info("Auto-upload disabled (set FOUNDRY_AUTO_UPLOAD=true to enable)")

        if should_upload:
            target = os.getenv("FOUNDRY_TARGET", args.target)
            result = upload_to_foundry(html_dir, target=target)

            if result["failed"] > 0:
                logger.warning("Some uploads failed, check logs above")
                sys.exit(1)

        logger.info("Processing complete!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
