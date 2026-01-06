"""
Public API - Thin HTTP client for D&D Module Processing.

This module provides the official interface for external applications
(chat UI, CLI tools, etc.) to interact with the module processing system.

IMPORTANT: This API requires the backend to be running at BACKEND_URL.
Start the backend with:
    cd ui/backend && uvicorn app.main:app --reload --port 8000

Configuration:
- Set BACKEND_URL environment variable (default: http://localhost:8000)
- Backend reads credentials from project .env file

Quick Start:
-----------

    from api import create_actor, APIError

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created: {result.name} ({result.foundry_uuid})")

Error Handling:
--------------

All functions raise APIError on failure:

    from api import APIError

    try:
        result = create_actor("invalid description")
    except APIError as e:
        logger.error(f"Failed: {e}")
        logger.error(f"Original cause: {e.__cause__}")

Direct Library Usage:
--------------------

For operations not yet available via HTTP API, import from the
internal modules directly:

    from actor_pipeline.orchestrate import create_actor_from_description_sync
    from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from exceptions import FoundryError, ConversionError, ConfigurationError
from scenes.orchestrate import create_scene_from_map_sync
from scenes.models import SceneCreationResult

# Re-export for backwards compatibility
APIError = FoundryError

logger = logging.getLogger(__name__)

# Public API exports
__all__ = [
    # Exceptions
    "APIError",
    # Result types
    "ActorCreationResult",
    "MapExtractionResult",
    "JournalCreationResult",
    "SceneCreationResult",
    # Functions
    "create_actor",
    "extract_maps",
    "process_pdf_to_journal",
    "create_scene",
    # Configuration
    "BACKEND_URL",
]

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@dataclass
class ActorCreationResult:
    """Result from creating a D&D actor.

    Attributes:
        foundry_uuid: FoundryVTT UUID of created actor (e.g., "Actor.abc123")
        name: Name of the actor
        challenge_rating: Creature's challenge rating
        output_dir: Directory containing intermediate files (optional)
        timestamp: ISO timestamp of creation (optional)
    """
    foundry_uuid: str
    name: str
    challenge_rating: float
    output_dir: Optional[Path] = None
    timestamp: Optional[str] = None


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

    Requires backend running at BACKEND_URL (default: http://localhost:8000).

    Args:
        description: Natural language description of the creature/NPC
                    (e.g., "A fierce goblin warrior with a poisoned blade")
        challenge_rating: CR of the creature (auto-determined from description if None)

    Returns:
        ActorCreationResult with FoundryVTT UUID and output paths

    Raises:
        APIError: If actor creation fails (backend not running, Gemini errors,
                 FoundryVTT connection issues, etc.)

    Example:
        >>> result = create_actor("A cunning kobold scout", challenge_rating=0.5)
        >>> print(f"Created: {result.name} ({result.foundry_uuid})")
        Created: Kobold Scout (Actor.abc123)
    """
    try:
        logger.info(f"Creating actor from description: {description[:50]}...")

        response = requests.post(
            f"{BACKEND_URL}/api/actors/create",
            json={
                "description": description,
                "challenge_rating": challenge_rating or 1.0,
            },
            timeout=120  # Actor creation can take a while
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise APIError(f"Actor creation failed: {data.get('detail', 'Unknown error')}")

        result = ActorCreationResult(
            foundry_uuid=data.get("foundry_uuid", ""),
            name=data.get("name", ""),
            challenge_rating=data.get("challenge_rating", 0.0),
            output_dir=Path(data["output_dir"]) if data.get("output_dir") else None,
            timestamp=data.get("timestamp"),
        )

        logger.info(f"Actor created: {result.name} ({result.foundry_uuid})")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Actor creation failed: {e}")
        raise APIError(f"Failed to create actor: {e}") from e
    except Exception as e:
        logger.error(f"Actor creation failed: {e}")
        raise APIError(f"Failed to create actor: {e}") from e


def extract_maps(
    pdf_path: str,
    chapter: Optional[str] = None
) -> MapExtractionResult:
    """
    Extract battle maps and navigation maps from a PDF.

    NOTE: This endpoint is not yet available via HTTP API.
    For direct library usage, import from the internal module:

        from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf
        import asyncio
        maps = asyncio.run(extract_maps_from_pdf(pdf_path, output_dir, chapter_name))

    Args:
        pdf_path: Path to source PDF file (absolute or relative)
        chapter: Optional chapter name for metadata

    Returns:
        MapExtractionResult with extracted maps and metadata

    Raises:
        APIError: Always - endpoint not yet implemented
    """
    raise APIError(
        "Map extraction is not yet available via HTTP API. "
        "Use direct library import: "
        "from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf"
    )


def process_pdf_to_journal(
    pdf_path: str,
    journal_name: str,
    skip_upload: bool = False
) -> JournalCreationResult:
    """
    Process a D&D PDF into FoundryVTT journal entries.

    NOTE: This endpoint is not yet available via HTTP API.
    For direct pipeline usage, run:

        uv run python scripts/full_pipeline.py --journal-name "My Module"

    Args:
        pdf_path: Path to source PDF file
        journal_name: Name for the FoundryVTT journal
        skip_upload: If True, generate XML but don't upload to Foundry

    Returns:
        JournalCreationResult with journal UUID and output paths

    Raises:
        APIError: Always - endpoint not yet implemented
    """
    raise APIError(
        "PDF to journal processing is not yet available via HTTP API. "
        "Use the full pipeline script: "
        "uv run python scripts/full_pipeline.py --journal-name 'My Module'"
    )


def create_scene(
    image_path: str,
    name: Optional[str] = None,
    skip_wall_detection: bool = False,
    grid_size: Optional[int] = None,
    folder: Optional[str] = None
) -> SceneCreationResult:
    """
    Create a FoundryVTT scene from a battle map image.

    This function orchestrates the full scene creation pipeline:
    - Wall detection (AI-powered wall tracing)
    - Grid detection (or use provided grid_size)
    - Image upload to FoundryVTT
    - Scene creation with walls

    Args:
        image_path: Path to the battle map image (PNG, JPG, WebP)
        name: Optional custom scene name (defaults to filename-derived name)
        skip_wall_detection: If True, create scene without walls (default: False)
        grid_size: Grid size in pixels (auto-detected if None)
        folder: Optional folder ID to place the scene in

    Returns:
        SceneCreationResult with scene UUID, name, wall count, and output paths

    Raises:
        APIError: If scene creation fails (file not found, Foundry errors, etc.)

    Example:
        >>> result = create_scene("maps/castle.png", name="Castle Ruins")
        >>> print(f"Created: {result.name} ({result.uuid})")
        Created: Castle Ruins (Scene.abc123)
        >>> print(f"Walls: {result.wall_count}, Grid: {result.grid_size}px")
        Walls: 150, Grid: 100px
    """
    try:
        logger.info(f"Creating scene from image: {image_path}")

        result = create_scene_from_map_sync(
            image_path=Path(image_path),
            name=name,
            skip_wall_detection=skip_wall_detection,
            grid_size_override=grid_size,
            folder=folder
        )

        logger.info(f"Scene created: {result.name} ({result.uuid})")
        return result

    except Exception as e:
        logger.error(f"Scene creation failed: {e}")
        raise APIError(f"Failed to create scene: {e}") from e
