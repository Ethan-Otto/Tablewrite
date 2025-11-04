"""Orchestrate full actor creation pipeline from description to FoundryVTT."""

import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Union, Optional, List
from pydantic import BaseModel

from actors.generate_actor_file import generate_actor_description
from actors.statblock_parser import parse_raw_text_to_statblock
from actors.models import ActorCreationResult
from foundry.actors.parser import parse_stat_block_parallel
from foundry.actors.converter import convert_to_foundry
from foundry.actors.spell_cache import SpellCache
from foundry.client import FoundryClient

logger = logging.getLogger(__name__)


def _create_output_directory(base_dir: str = "output/runs") -> Path:
    """
    Create timestamped output directory for actor creation files.

    Args:
        base_dir: Base directory for runs (default: "output/runs")

    Returns:
        Path to created directory: output/runs/<timestamp>/actors/

    Example:
        output/runs/20241103_143022/actors/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / timestamp / "actors"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created output directory: {output_dir}")
    return output_dir


def _save_intermediate_file(
    content: Union[str, dict, BaseModel],
    filepath: Path,
    description: str = "file"
) -> Path:
    """
    Save intermediate output to file (text or JSON).

    Args:
        content: Content to save (str for text, dict/BaseModel for JSON)
        filepath: Full path to save file
        description: Human-readable description for logging

    Returns:
        Path to saved file

    Raises:
        IOError: If file write fails

    Examples:
        # Save raw text
        _save_intermediate_file("Goblin\\nSmall humanoid...",
                               output_dir / "raw_text.txt",
                               "raw stat block text")

        # Save Pydantic model as JSON
        _save_intermediate_file(stat_block,
                               output_dir / "stat_block.json",
                               "StatBlock model")
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            # Save as text file
            filepath.write_text(content, encoding='utf-8')
        elif isinstance(content, BaseModel):
            # Save Pydantic model as JSON
            filepath.write_text(content.model_dump_json(indent=2), encoding='utf-8')
        elif isinstance(content, dict):
            # Save dict as JSON
            filepath.write_text(json.dumps(content, indent=2), encoding='utf-8')
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

        logger.debug(f"Saved {description} to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save {description} to {filepath}: {e}")
        raise IOError(f"Failed to save {description}: {e}") from e


async def create_actor_from_description(
    description: str,
    challenge_rating: Optional[float] = None,
    model_name: str = "gemini-2.0-flash",
    output_dir_base: str = "output/runs",
    spell_cache: Optional[SpellCache] = None,
    foundry_client: Optional[FoundryClient] = None
) -> ActorCreationResult:
    """
    Create a complete D&D 5e actor in FoundryVTT from a natural language description.

    This function orchestrates the full pipeline:
    1. Generate raw stat block text using Gemini
    2. Parse raw text to StatBlock model
    3. Parse StatBlock to detailed ParsedActorData
    4. Convert to FoundryVTT JSON format
    5. Upload to FoundryVTT server

    All intermediate outputs are saved to disk for debugging.

    Args:
        description: Natural language description of the actor
                    Example: "A fierce red dragon wyrmling with fire breath"
        challenge_rating: Optional CR (0.125, 0.25, 0.5, 1-30). If None, Gemini determines it.
        model_name: Gemini model to use (default: "gemini-2.0-flash")
        output_dir_base: Base directory for output (default: "output/runs")
        spell_cache: Optional pre-loaded SpellCache (will create if None)
        foundry_client: Optional FoundryClient (will create if None)

    Returns:
        ActorCreationResult with all intermediate outputs and final FoundryVTT UUID

    Raises:
        ValueError: If any parsing step fails
        RuntimeError: If Gemini API calls fail
        IOError: If file save fails

    Example:
        result = await create_actor_from_description(
            "A cunning goblin assassin with poisoned daggers",
            challenge_rating=2.0
        )
        print(f"Actor created: {result.foundry_uuid}")
        print(f"Saved to: {result.output_dir}")
    """
    timestamp_str = datetime.now().isoformat()

    # Step 0: Create output directory
    logger.info(f"Starting actor creation: {description[:50]}...")
    output_dir = _create_output_directory(output_dir_base)

    try:
        # Step 1: Generate raw stat block text
        logger.info("Step 1/5: Generating stat block text with Gemini...")
        raw_text = await generate_actor_description(
            description=description,
            challenge_rating=challenge_rating,
            model_name=model_name
        )
        raw_text_file = _save_intermediate_file(
            raw_text,
            output_dir / "01_raw_stat_block.txt",
            "raw stat block text"
        )

        # Step 2: Parse to StatBlock model
        logger.info("Step 2/5: Parsing stat block to StatBlock model...")
        stat_block = await parse_raw_text_to_statblock(raw_text, model_name=model_name)
        stat_block_file = _save_intermediate_file(
            stat_block,
            output_dir / "02_stat_block.json",
            "StatBlock model"
        )

        # Step 3: Parse to detailed ParsedActorData
        logger.info("Step 3/5: Parsing to detailed ParsedActorData...")
        parsed_actor = await parse_stat_block_parallel(stat_block)
        parsed_data_file = _save_intermediate_file(
            parsed_actor,
            output_dir / "03_parsed_actor_data.json",
            "ParsedActorData model"
        )

        # Step 4: Convert to FoundryVTT format
        logger.info("Step 4/5: Converting to FoundryVTT format...")
        if spell_cache is None:
            spell_cache = SpellCache()
            spell_cache.load()

        actor_json, spell_uuids = convert_to_foundry(parsed_actor, spell_cache=spell_cache)
        foundry_json_file = _save_intermediate_file(
            actor_json,
            output_dir / "04_foundry_actor.json",
            "FoundryVTT actor JSON"
        )

        # Step 5: Upload to FoundryVTT
        logger.info("Step 5/5: Uploading to FoundryVTT...")
        if foundry_client is None:
            foundry_client = FoundryClient(
                target=os.getenv("FOUNDRY_TARGET", "local")
            )

        actor_uuid = foundry_client.actors.create_actor(
            actor_data=actor_json,
            spell_uuids=spell_uuids
        )

        logger.info(f"✓ Actor created successfully: {actor_uuid}")
        logger.info(f"  Output directory: {output_dir}")

        # Return complete result
        return ActorCreationResult(
            description=description,
            challenge_rating=challenge_rating,
            raw_stat_block_text=raw_text,
            stat_block=stat_block,
            parsed_actor_data=parsed_actor,
            foundry_uuid=actor_uuid,
            output_dir=output_dir,
            raw_text_file=raw_text_file,
            stat_block_file=stat_block_file,
            parsed_data_file=parsed_data_file,
            foundry_json_file=foundry_json_file,
            timestamp=timestamp_str,
            model_used=model_name
        )

    except Exception as e:
        logger.error(f"Actor creation failed: {e}")
        raise


def create_actor_from_description_sync(
    description: str,
    challenge_rating: Optional[float] = None,
    model_name: str = "gemini-2.0-flash",
    output_dir_base: str = "output/runs",
    spell_cache: Optional[SpellCache] = None,
    foundry_client: Optional[FoundryClient] = None
) -> ActorCreationResult:
    """
    Synchronous wrapper for create_actor_from_description().

    This is a convenience function that runs the async pipeline in a synchronous context.
    All parameters and return values are identical to the async version.

    Args:
        description: Natural language description of the actor
        challenge_rating: Optional CR (0.125, 0.25, 0.5, 1-30). If None, Gemini determines it.
        model_name: Gemini model to use (default: "gemini-2.0-flash")
        output_dir_base: Base directory for output (default: "output/runs")
        spell_cache: Optional pre-loaded SpellCache
        foundry_client: Optional FoundryClient

    Returns:
        ActorCreationResult with all outputs and FoundryVTT UUID

    Example:
        # Simple synchronous usage
        result = create_actor_from_description_sync(
            "A cunning goblin assassin",
            challenge_rating=2.0
        )
        print(f"Created: {result.foundry_uuid}")
    """
    return asyncio.run(
        create_actor_from_description(
            description=description,
            challenge_rating=challenge_rating,
            model_name=model_name,
            output_dir_base=output_dir_base,
            spell_cache=spell_cache,
            foundry_client=foundry_client
        )
    )


async def create_actors_batch(
    descriptions: List[str],
    challenge_ratings: Optional[List[Optional[float]]] = None,
    model_name: str = "gemini-2.0-flash",
    output_dir_base: str = "output/runs",
    spell_cache: Optional[SpellCache] = None,
    foundry_client: Optional[FoundryClient] = None
) -> List[Union[ActorCreationResult, Exception]]:
    """
    Create multiple actors in parallel from a list of descriptions.

    This function processes all actors concurrently using asyncio.gather().
    Individual failures are captured and returned in the results list.

    Args:
        descriptions: List of natural language descriptions
        challenge_ratings: Optional list of CRs (same length as descriptions, or None)
        model_name: Gemini model to use (default: "gemini-2.0-flash")
        output_dir_base: Base directory for output (default: "output/runs")
        spell_cache: Optional pre-loaded SpellCache (recommended for batch processing)
        foundry_client: Optional FoundryClient (recommended for batch processing)

    Returns:
        List of ActorCreationResult or Exception objects (one per description)
        Successful results are ActorCreationResult instances
        Failed results are Exception instances

    Example:
        descriptions = [
            "A fierce red dragon wyrmling",
            "A cunning goblin assassin",
            "An ancient treant guardian"
        ]
        crs = [2.0, 1.0, 9.0]

        # Pre-load shared resources for efficiency
        spell_cache = SpellCache()
        spell_cache.load()
        client = FoundryClient()

        results = await create_actors_batch(
            descriptions,
            challenge_ratings=crs,
            spell_cache=spell_cache,
            foundry_client=client
        )

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed: {descriptions[i]} - {result}")
            else:
                print(f"Created: {result.foundry_uuid}")
    """
    # Validate inputs
    if challenge_ratings is not None and len(challenge_ratings) != len(descriptions):
        raise ValueError("challenge_ratings must be same length as descriptions")

    # Default challenge_ratings to all None
    if challenge_ratings is None:
        challenge_ratings = [None] * len(descriptions)

    # Pre-load shared resources if not provided
    if spell_cache is None:
        logger.info("Loading spell cache for batch processing...")
        spell_cache = SpellCache()
        spell_cache.load()

    if foundry_client is None:
        logger.info("Creating FoundryVTT client for batch processing...")
        foundry_client = FoundryClient(
            target=os.getenv("FOUNDRY_TARGET", "local")
        )

    logger.info(f"Starting batch creation of {len(descriptions)} actors...")

    # Create tasks for all actors
    tasks = []
    for desc, cr in zip(descriptions, challenge_ratings):
        task = create_actor_from_description(
            description=desc,
            challenge_rating=cr,
            model_name=model_name,
            output_dir_base=output_dir_base,
            spell_cache=spell_cache,
            foundry_client=foundry_client
        )
        tasks.append(task)

    # Run all tasks concurrently, capturing exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log summary
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes
    logger.info(f"Batch complete: {successes} succeeded, {failures} failed")

    return results


def create_actors_batch_sync(
    descriptions: List[str],
    challenge_ratings: Optional[List[Optional[float]]] = None,
    model_name: str = "gemini-2.0-flash",
    output_dir_base: str = "output/runs",
    spell_cache: Optional[SpellCache] = None,
    foundry_client: Optional[FoundryClient] = None
) -> List[Union[ActorCreationResult, Exception]]:
    """
    Synchronous wrapper for create_actors_batch().

    See create_actors_batch() for full documentation.
    """
    return asyncio.run(
        create_actors_batch(
            descriptions=descriptions,
            challenge_ratings=challenge_ratings,
            model_name=model_name,
            output_dir_base=output_dir_base,
            spell_cache=spell_cache,
            foundry_client=foundry_client
        )
    )
