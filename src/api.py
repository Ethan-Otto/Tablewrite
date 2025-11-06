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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from actors.orchestrate import create_actor_from_description_sync as orchestrate_create_actor_from_description_sync

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
