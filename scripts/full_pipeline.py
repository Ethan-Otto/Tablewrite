#!/usr/bin/env python3
"""
Full pipeline orchestration: PDF → XML → Scene Art → Actors → FoundryVTT → Export

This script coordinates the complete workflow:
1. Split PDF into chapter PDFs (split_pdf.py)
2. Generate XML from chapters using Gemini (pdf_to_xml.py)
2.5. Generate scene artwork from XML (generate_scene_art.py)
3. Process actors and NPCs (process_actors.py)
4. Upload XML to FoundryVTT (upload_to_foundry.py)
5. Export journal from FoundryVTT to HTML (export_from_foundry.py)

Each step can be skipped with flags for resuming interrupted runs.
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


def run_pdf_split(project_root: Path) -> None:
    """
    Run split_pdf.py to split source PDF into chapter PDFs.

    Args:
        project_root: Project root directory

    Raises:
        RuntimeError: If split fails
    """
    split_script = project_root / "src" / "pdf_processing" / "split_pdf.py"

    logger.info("=" * 60)
    logger.info("STEP 1: Splitting PDF into chapters")
    logger.info("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, str(split_script)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"PDF split failed: {result.stderr}")
            raise RuntimeError(f"split_pdf.py failed with code {result.returncode}")

        logger.info("✓ PDF split completed successfully")
        if result.stdout:
            logger.debug(f"Output: {result.stdout}")

    except subprocess.TimeoutExpired:
        logger.error("PDF split timed out after 5 minutes")
        raise RuntimeError("PDF split timed out")
    except Exception as e:
        logger.error(f"Failed to run split_pdf.py: {e}")
        raise


def run_pdf_to_xml(project_root: Path, chapter_file: str = None) -> Path:
    """
    Run pdf_to_xml.py to generate XML from chapter PDFs using Gemini.

    Args:
        project_root: Project root directory
        chapter_file: Optional specific chapter file to process

    Returns:
        Path to the generated run directory

    Raises:
        RuntimeError: If XML generation fails
    """
    xml_script = project_root / "src" / "pdf_processing" / "pdf_to_xml.py"

    logger.info("=" * 60)
    logger.info("STEP 2: Generating XML from PDFs using Gemini")
    logger.info("=" * 60)
    logger.info("This may take several minutes depending on PDF size...")

    try:
        cmd = [sys.executable, str(xml_script)]
        if chapter_file:
            cmd.extend(["--file", chapter_file])

        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout for Gemini API calls
        )

        if result.returncode != 0:
            logger.error(f"XML generation failed: {result.stderr}")
            raise RuntimeError(f"pdf_to_xml.py failed with code {result.returncode}")

        logger.info("✓ XML generation completed successfully")
        if result.stdout:
            logger.debug(f"Output: {result.stdout}")

        # Find the latest run directory
        runs_dir = project_root / "output" / "runs"
        if not runs_dir.exists():
            raise RuntimeError("No runs directory found after XML generation")

        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not run_dirs:
            raise RuntimeError("No run directories found after XML generation")

        latest_run = sorted(run_dirs, key=lambda d: d.name)[-1]
        logger.info(f"XML files generated in: {latest_run / 'documents'}")
        return latest_run

    except subprocess.TimeoutExpired:
        logger.error("XML generation timed out after 1 hour")
        raise RuntimeError("XML generation timed out")
    except Exception as e:
        logger.error(f"Failed to run pdf_to_xml.py: {e}")
        raise


def process_actors(run_dir: Path, target: str = "local") -> dict:
    """
    Process actors and NPCs from XML files.

    Args:
        run_dir: Path to run directory containing XML files
        target: Target environment ('local' or 'forge')

    Returns:
        Actor processing statistics dict

    Raises:
        RuntimeError: If actor processing fails
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Processing actors and NPCs")
    logger.info("=" * 60)

    # Import here to avoid circular dependencies
    from src.actors.process_actors import process_actors_for_run

    try:
        result = process_actors_for_run(str(run_dir), target=target)

        logger.info(
            f"✓ Actor processing complete: "
            f"{result['stat_blocks_created']} creatures created, "
            f"{result['stat_blocks_reused']} reused, "
            f"{result['npcs_created']} NPCs created"
        )

        if result.get("errors"):
            logger.warning(f"{len(result['errors'])} error(s) occurred during actor processing")
            for error in result["errors"]:
                logger.error(f"  {error}")

        return result

    except Exception as e:
        logger.error(f"Actor processing failed: {e}")
        raise RuntimeError(f"Actor processing failed: {e}")


def run_scene_artwork_generation(
    run_dir: Path,
    style_prompt: str = None,
    continue_on_error: bool = False
) -> None:
    """
    Generate scene artwork from chapter XML files.

    Args:
        run_dir: Run directory containing documents/ folder
        style_prompt: Optional custom style prompt for image generation
        continue_on_error: Continue processing other chapters if one fails

    Raises:
        RuntimeError: If scene generation fails and continue_on_error is False
    """
    logger.info("=" * 60)
    logger.info("STEP 2.5: Generating scene artwork")
    logger.info("=" * 60)

    output_dir = run_dir / "scene_artwork"

    try:
        # Import scene generation functions
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from generate_scene_art import process_chapter, sanitize_filename

        # Find XML files to process
        xml_files = list((run_dir / "documents").glob("*.xml"))

        if not xml_files:
            logger.warning("No XML files found, skipping scene artwork generation")
            return

        logger.info(f"Processing {len(xml_files)} chapter file(s)...")
        output_dir.mkdir(parents=True, exist_ok=True)

        total_scenes = 0
        total_images = 0
        failed_chapters = []

        for xml_file in xml_files:
            try:
                stats = process_chapter(xml_file, output_dir, style_prompt)
                total_scenes += stats["scenes_found"]
                total_images += stats["images_generated"]
                logger.info(f"  ✓ {xml_file.name}: {stats['scenes_found']} scenes, {stats['images_generated']} images")
            except Exception as e:
                logger.error(f"Failed to process {xml_file.name}: {e}")
                failed_chapters.append(xml_file.name)
                if not continue_on_error:
                    raise

        logger.info("✓ Scene artwork generation completed")
        logger.info(f"  Total scenes: {total_scenes}, Images: {total_images}")

        if failed_chapters:
            logger.warning(f"  Failed chapters: {', '.join(failed_chapters)}")

    except Exception as e:
        logger.error(f"Scene artwork generation failed: {e}")
        raise RuntimeError(f"Scene artwork generation failed: {e}") from e


def upload_to_foundry(run_dir: Path, target: str = "local", journal_name: str = None) -> dict:
    """
    Upload XML files to FoundryVTT.

    Args:
        run_dir: Path to run directory containing XML files
        target: Target environment ('local' or 'forge')
        journal_name: Optional journal name

    Returns:
        Upload statistics dict with 'journal_uuid' key

    Raises:
        RuntimeError: If upload fails
    """
    logger.info("=" * 60)
    logger.info("STEP 4: Uploading to FoundryVTT")
    logger.info("=" * 60)

    # Import here to avoid circular dependencies
    from src.foundry.upload_journal_to_foundry import upload_run_to_foundry

    try:
        result = upload_run_to_foundry(
            str(run_dir),
            target=target,
            journal_name=journal_name
        )

        if result["failed"] > 0 or result.get("errors"):
            logger.warning(
                f"Upload completed with errors: "
                f"{result['uploaded']} succeeded, {result['failed']} failed"
            )
            for error in result.get("errors", []):
                logger.error(f"  {error}")
        else:
            logger.info(f"✓ Successfully uploaded {result['uploaded']} page(s) to FoundryVTT")

        return result

    except Exception as e:
        logger.error(f"Upload to FoundryVTT failed: {e}")
        raise RuntimeError(f"Upload failed: {e}")


def export_from_foundry(
    run_dir: Path,
    target: str = "local",
    journal_name: str = None,
    journal_uuid: str = None
) -> None:
    """
    Export journal from FoundryVTT to HTML in the run directory.

    Args:
        run_dir: Path to run directory to save export
        target: Target environment ('local' or 'forge')
        journal_name: Name of the journal to export (used for filename)
        journal_uuid: Optional UUID of journal (if provided, skips search)

    Raises:
        RuntimeError: If export fails
    """
    logger.info("=" * 60)
    logger.info("STEP 5: Exporting from FoundryVTT")
    logger.info("=" * 60)

    # Import here to avoid circular dependencies
    from src.foundry.client import FoundryClient
    from src.foundry.export_from_foundry import export_to_html

    try:
        # Initialize client
        client = FoundryClient()

        # Get journal UUID (either provided or search by name)
        if journal_uuid:
            logger.info(f"Using provided journal UUID: {journal_uuid}")
        else:
            # Need to search for journal by name
            if not journal_name:
                logger.error("Must provide either journal_uuid or journal_name")
                return

            logger.info(f"Searching for journal: {journal_name}")
            journal = client.get_journal_by_name(journal_name)

            if not journal:
                logger.warning(f"Journal not found: {journal_name} - skipping export")
                return

            # Extract UUID from search result
            journal_uuid = journal.get('uuid')
            if not journal_uuid:
                journal_id = journal.get('_id') or journal.get('id')
                if journal_id:
                    journal_uuid = f"JournalEntry.{journal_id}"

            if not journal_uuid:
                logger.error(f"Could not determine UUID for journal: {journal_name}")
                return

        # Get full journal data
        logger.info(f"Retrieving journal data: {journal_uuid}")
        journal_data = client.get_journal(journal_uuid)

        # Use journal name from data if not provided
        if not journal_name:
            data = journal_data.get('data', journal_data)
            journal_name = data.get('name', 'journal')

        # Export to HTML in run directory
        export_dir = run_dir / "foundry_export"
        export_dir.mkdir(exist_ok=True)
        output_path = export_dir / f"{journal_name}.html"

        export_to_html(journal_data, str(output_path), single_file=True)
        logger.info(f"✓ Exported journal to: {output_path}")

    except Exception as e:
        logger.error(f"Export from FoundryVTT failed: {e}")
        raise RuntimeError(f"Export failed: {e}")


def main():
    """Main entry point for full pipeline orchestration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Full pipeline: Split PDF → Generate XML → Upload to FoundryVTT → Export HTML"
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="Skip PDF splitting (use existing chapter PDFs)"
    )
    parser.add_argument(
        "--skip-xml",
        action="store_true",
        help="Skip XML generation (use latest run)"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip FoundryVTT upload"
    )
    parser.add_argument(
        "--skip-actors",
        action="store_true",
        help="Skip actor/NPC extraction and creation"
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip FoundryVTT export"
    )
    parser.add_argument(
        "--skip-scenes",
        action="store_true",
        help="Skip scene artwork generation"
    )
    parser.add_argument(
        "--actors-only",
        action="store_true",
        help="Only process actors (skip PDF splitting, XML generation, upload)"
    )
    parser.add_argument(
        "--chapter-file",
        help="Process only a specific chapter file (e.g., '01_Introduction.pdf')"
    )
    parser.add_argument(
        "--run-dir",
        help="Specific run directory to use (for --actors-only or --skip-xml)"
    )
    parser.add_argument(
        "--journal-name",
        help="Name for the FoundryVTT journal entry (default: 'D&D Module')"
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
        # Actors-only mode
        if args.actors_only:
            logger.info("\n" + "=" * 60)
            logger.info("Running in actors-only mode")
            logger.info("=" * 60)

            # Need to find run directory
            if args.run_dir:
                run_dir = Path(args.run_dir)
                if not run_dir.exists():
                    logger.error(f"Specified run directory not found: {run_dir}")
                    sys.exit(1)
            else:
                # Find latest run
                runs_dir = project_root / "output" / "runs"
                if not runs_dir.exists():
                    logger.error("No runs directory found. Run full pipeline first.")
                    sys.exit(1)

                run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
                if not run_dirs:
                    logger.error("No run directories found. Run full pipeline first.")
                    sys.exit(1)

                run_dir = sorted(run_dirs, key=lambda d: d.name)[-1]
                logger.info(f"Using latest run: {run_dir.name}")

            try:
                actor_stats = process_actors(run_dir, target=args.target)
                logger.info("=" * 60)
                logger.info("ACTORS-ONLY MODE COMPLETE!")
                logger.info("=" * 60)
                sys.exit(0)
            except Exception as e:
                logger.error(f"Actor processing failed: {e}")
                sys.exit(1)

        # Step 1: Split PDF
        if args.skip_split:
            logger.info("Skipping PDF split (--skip-split)")
        else:
            run_pdf_split(project_root)

        # Step 2: Generate XML
        if args.skip_xml:
            logger.info("Skipping XML generation (--skip-xml), using latest run...")

            if args.run_dir:
                run_dir = Path(args.run_dir)
                if not run_dir.exists():
                    logger.error(f"Specified run directory not found: {run_dir}")
                    sys.exit(1)
            else:
                runs_dir = project_root / "output" / "runs"

                if not runs_dir.exists():
                    logger.error("No runs directory found")
                    sys.exit(1)

                run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
                if not run_dirs:
                    logger.error("No run directories found")
                    sys.exit(1)

                run_dir = sorted(run_dirs, key=lambda d: d.name)[-1]

            logger.info(f"Using run: {run_dir.name}")
        else:
            run_dir = run_pdf_to_xml(project_root, chapter_file=args.chapter_file)

        # Step 2.5: Generate scene artwork (optional)
        if args.skip_scenes:
            logger.info("Skipping scene artwork generation (--skip-scenes)")
        else:
            try:
                # Get style prompt from environment variable if not in args
                style_prompt = os.getenv("IMAGE_STYLE_PROMPT")
                run_scene_artwork_generation(run_dir, style_prompt=style_prompt, continue_on_error=True)
            except Exception as e:
                logger.error(f"Scene artwork generation failed: {e}")
                logger.warning("Continuing with pipeline despite scene generation failure")

        # Step 3: Process actors and NPCs
        if args.skip_actors:
            logger.info("Skipping actor processing (--skip-actors)")
        else:
            try:
                actor_stats = process_actors(run_dir, target=args.target)
            except Exception as e:
                logger.error(f"Actor processing failed: {e}")
                logger.warning("Continuing with pipeline...")

        # Step 4: Upload to FoundryVTT
        upload_result = None
        if args.skip_upload:
            logger.info("Skipping FoundryVTT upload (--skip-upload)")
        else:
            upload_result = upload_to_foundry(
                run_dir,
                target=args.target,
                journal_name=args.journal_name
            )

            if upload_result["failed"] > 0 or upload_result.get("errors"):
                logger.warning("Some uploads failed, check logs above")
                sys.exit(1)

        # Step 5: Export from FoundryVTT
        if args.skip_export:
            logger.info("Skipping FoundryVTT export (--skip-export)")
        elif args.skip_upload:
            logger.info("Skipping export (upload was skipped)")
        else:
            # Use journal UUID from upload result (saves an API search call)
            journal_uuid = upload_result.get("journal_uuid") if upload_result else None
            journal_name = upload_result.get("journal_name") if upload_result else (args.journal_name or "D&D Module")

            export_from_foundry(
                run_dir,
                target=args.target,
                journal_name=journal_name,
                journal_uuid=journal_uuid
            )

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 60)
        sys.exit(0)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"PIPELINE FAILED: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
