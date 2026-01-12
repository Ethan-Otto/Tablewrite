"""
Public API for D&D Module Processing.

This module provides the official interface for creating actors and scenes.

IMPORTANT: Requires backend running at BACKEND_URL for actor creation.
Start the backend with:
    cd ui/backend && uvicorn app.main:app --reload --port 8000

Quick Start:
-----------

    from api import create_actor, create_scene, APIError

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created: {result.name} ({result.foundry_uuid})")

    # Create scene from battle map
    result = create_scene("maps/castle.png", name="Castle Ruins")
    print(f"Created: {result.name} ({result.uuid})")

Error Handling:
--------------

All functions raise APIError on failure:

    try:
        result = create_actor("invalid description")
    except APIError as e:
        logger.error(f"Failed: {e}")

For PDF Processing:
------------------

Use the Module tab in the Foundry chat UI, or run:
    uv run python scripts/full_pipeline.py --journal-name "My Module"

For Map Extraction:
------------------

    from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf
    import asyncio
    maps = asyncio.run(extract_maps_from_pdf(pdf_path, output_dir, chapter_name))
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from exceptions import FoundryError
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
    "SceneCreationResult",
    # Functions
    "create_actor",
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
