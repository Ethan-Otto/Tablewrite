"""
Public API for D&D Module Processing.

This module provides the official interface for external applications
(chat UI, CLI tools, etc.) to interact with the module processing system.

All functions use environment variables for configuration (.env file).
Operations are synchronous and may take several minutes for large PDFs.

Example usage:
    from api import create_actor, extract_maps, process_pdf_to_journal

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created actor: {result.foundry_uuid}")

    # Extract maps from PDF
    maps = extract_maps("data/pdfs/module.pdf")
    print(f"Extracted {maps.total_maps} maps")

    # Process PDF to journal
    journal = process_pdf_to_journal(
        "data/pdfs/module.pdf",
        "Lost Mine of Phandelver"
    )
    print(f"Created journal: {journal.journal_uuid}")
"""

import logging
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from actors.orchestrate import create_actor_from_description_sync as orchestrate_create_actor_from_description_sync
from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Raised when API operations fail.

    This exception wraps internal errors to provide a clean boundary
    between the public API and internal implementation details.

    The original exception is preserved as __cause__ for debugging.
    """
    pass


@dataclass
class ActorCreationResult:
    """Result from creating a D&D actor.

    Attributes:
        foundry_uuid: FoundryVTT UUID of created actor (e.g., "Actor.abc123")
        name: Name of the actor
        challenge_rating: Creature's challenge rating
        output_dir: Directory containing intermediate files
        timestamp: ISO timestamp of creation
    """
    foundry_uuid: str
    name: str
    challenge_rating: float
    output_dir: Path
    timestamp: str


@dataclass
class MapExtractionResult:
    """Result from extracting maps from a PDF.

    Attributes:
        maps: List of map metadata dictionaries
        output_dir: Directory containing extracted map images
        total_maps: Total number of maps extracted
        timestamp: ISO timestamp of extraction
    """
    maps: List[Dict[str, Any]]
    output_dir: Path
    total_maps: int
    timestamp: str


@dataclass
class JournalCreationResult:
    """Result from creating a FoundryVTT journal.

    Attributes:
        journal_uuid: FoundryVTT UUID of created journal (e.g., "JournalEntry.xyz789")
        journal_name: Name of the journal
        output_dir: Directory containing XML/HTML files
        chapter_count: Number of chapters processed
        timestamp: ISO timestamp of creation
    """
    journal_uuid: str
    journal_name: str
    output_dir: Path
    chapter_count: int
    timestamp: str


def create_actor(
    description: str,
    challenge_rating: Optional[float] = None
) -> ActorCreationResult:
    """
    Create a D&D actor from natural language description.

    This function generates a complete FoundryVTT actor including:
    - Stat block parsing from description
    - Ability scores, skills, and attacks
    - Spell resolution (if applicable)
    - Upload to FoundryVTT server

    Args:
        description: Natural language description of the creature/NPC
                    (e.g., "A fierce goblin warrior with a poisoned blade")
        challenge_rating: CR of the creature (auto-determined from description if None)

    Returns:
        ActorCreationResult with FoundryVTT UUID and output paths

    Raises:
        APIError: If actor creation fails (missing API key, Gemini errors,
                 FoundryVTT connection issues, etc.)

    Example:
        >>> result = create_actor("A cunning kobold scout", challenge_rating=0.5)
        >>> print(f"Created: {result.name} ({result.foundry_uuid})")
        Created: Kobold Scout (Actor.abc123)
    """
    try:
        logger.info(f"Creating actor from description: {description[:50]}...")

        # Call orchestrate function
        orchestrate_result = orchestrate_create_actor_from_description_sync(
            description=description,
            challenge_rating=challenge_rating
        )

        # Extract name from parsed_actor_data
        actor_name = orchestrate_result.parsed_actor_data.name

        # Convert to simplified result
        result = ActorCreationResult(
            foundry_uuid=orchestrate_result.foundry_uuid,
            name=actor_name,
            challenge_rating=orchestrate_result.challenge_rating,
            output_dir=orchestrate_result.output_dir,
            timestamp=orchestrate_result.timestamp
        )

        logger.info(f"Actor created: {result.name} ({result.foundry_uuid})")
        return result

    except Exception as e:
        logger.error(f"Actor creation failed: {e}")
        raise APIError(f"Failed to create actor: {e}") from e


def extract_maps(
    pdf_path: str,
    chapter: Optional[str] = None
) -> MapExtractionResult:
    """
    Extract battle maps and navigation maps from a PDF.

    Uses hybrid approach: PyMuPDF extraction (fast) + Gemini segmentation
    (handles baked-in maps). All pages processed in parallel.

    Args:
        pdf_path: Path to source PDF file (absolute or relative)
        chapter: Optional chapter name for metadata

    Returns:
        MapExtractionResult with extracted maps and metadata

    Raises:
        APIError: If extraction fails (file not found, PDF corrupt,
                 Gemini errors, etc.)

    Example:
        >>> result = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")
        >>> print(f"Extracted {result.total_maps} maps")
        Extracted 3 maps
        >>> for map_meta in result.maps:
        ...     print(f"  - {map_meta['name']} ({map_meta['type']})")
    """
    try:
        logger.info(f"Extracting maps from: {pdf_path}")

        # Create output directory (extract_maps_from_pdf expects output_dir parameter)
        # Use timestamp-based directory like other pipelines
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output/runs") / timestamp / "map_assets"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run async extraction in sync context
        maps = asyncio.run(extract_maps_from_pdf(
            pdf_path=pdf_path,
            output_dir=str(output_dir),
            chapter_name=chapter
        ))

        # Convert MapMetadata objects to dicts
        maps_dicts = [m.model_dump() for m in maps]

        result = MapExtractionResult(
            maps=maps_dicts,
            output_dir=output_dir,
            total_maps=len(maps),
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Extracted {result.total_maps} maps to {result.output_dir}")
        return result

    except Exception as e:
        logger.error(f"Map extraction failed: {e}")
        raise APIError(f"Failed to extract maps: {e}") from e


def process_pdf_to_journal(
    pdf_path: str,
    journal_name: str,
    skip_upload: bool = False
) -> JournalCreationResult:
    """
    Process a D&D PDF into FoundryVTT journal entries.

    Runs the full pipeline:
    1. Split PDF into chapter PDFs (if not already split)
    2. Generate XML from chapters using Gemini
    3. Upload to FoundryVTT (unless skip_upload=True)

    Args:
        pdf_path: Path to source PDF file
        journal_name: Name for the FoundryVTT journal
        skip_upload: If True, generate XML but don't upload to Foundry

    Returns:
        JournalCreationResult with journal UUID and output paths

    Raises:
        APIError: If processing fails (PDF errors, Gemini errors,
                 FoundryVTT connection issues, etc.)

    Example:
        >>> result = process_pdf_to_journal(
        ...     "data/pdfs/module.pdf",
        ...     "Lost Mine of Phandelver"
        ... )
        >>> print(f"Created journal: {result.journal_uuid}")
        Created journal: JournalEntry.xyz789
    """
    try:
        logger.info(f"Processing PDF to journal: {pdf_path}")

        # Step 1: Run PDF to XML conversion
        # This returns the run directory (e.g., output/runs/20251105_120000)
        logger.info("Step 1/2: Converting PDF to XML...")
        run_dir = run_pdf_to_xml(pdf_path)

        # Count chapters by counting XML files
        xml_files = list(run_dir.glob("documents/*.xml"))
        chapter_count = len(xml_files)

        journal_uuid = ""
        if not skip_upload:
            # Step 2: Upload to FoundryVTT
            logger.info("Step 2/2: Uploading to FoundryVTT...")
            journal_uuid = upload_xml_to_foundry(run_dir, journal_name)
        else:
            logger.info("Skipping upload (skip_upload=True)")

        result = JournalCreationResult(
            journal_uuid=journal_uuid,
            journal_name=journal_name,
            output_dir=run_dir,
            chapter_count=chapter_count,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Journal processing complete: {result.journal_name}")
        return result

    except Exception as e:
        logger.error(f"PDF to journal processing failed: {e}")
        raise APIError(f"Failed to process PDF to journal: {e}") from e


def run_pdf_to_xml(pdf_path: str) -> Path:
    """
    Internal helper: Run PDF to XML conversion pipeline.

    This is a simplified placeholder implementation. In production,
    this would need to be refactored from full_pipeline.py to handle
    PDF splitting, XML generation, etc.

    Args:
        pdf_path: Path to source PDF file

    Returns:
        Path to run directory containing generated XML files
    """
    # TODO: Refactor full_pipeline.py to expose this as a clean function
    # For now, this is a placeholder that would need actual implementation
    raise NotImplementedError(
        "run_pdf_to_xml needs to be refactored from scripts/full_pipeline.py"
    )


def upload_xml_to_foundry(run_dir: Path, journal_name: str) -> str:
    """
    Internal helper: Upload XML files to FoundryVTT.

    This is a simplified placeholder implementation. In production,
    this would need to be refactored from upload_to_foundry.py.

    Args:
        run_dir: Directory containing XML files to upload
        journal_name: Name for the journal in FoundryVTT

    Returns:
        Journal UUID (e.g., "JournalEntry.xyz789")
    """
    # TODO: Refactor upload_to_foundry.py to expose this as a clean function
    # For now, this is a placeholder that would need actual implementation
    raise NotImplementedError(
        "upload_xml_to_foundry needs to be refactored from src/foundry/upload_to_foundry.py"
    )
