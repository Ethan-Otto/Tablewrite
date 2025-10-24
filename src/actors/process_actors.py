"""Orchestrate actor processing workflow for a run directory."""

import logging
from pathlib import Path
from typing import Dict, Any, Literal
from foundry.client import FoundryClient
from util.gemini import GeminiAPI
from .extract_stat_blocks import extract_and_parse_stat_blocks
from .extract_npcs import identify_npcs_with_gemini

logger = logging.getLogger(__name__)


def process_actors_for_run(
    run_dir: str,
    target: Literal["local", "forge"] = "local"
) -> Dict[str, Any]:
    """
    Process all actors for a run directory.

    Complete workflow:
    1. Extract and parse stat blocks from XML files
    2. Extract NPCs from XML files
    3. Create/lookup creature actors in FoundryVTT
    4. Create NPC actors with stat block links

    Args:
        run_dir: Path to run directory (contains documents/ folder)
        target: FoundryVTT target environment

    Returns:
        Dict with processing statistics

    Raises:
        FileNotFoundError: If run directory doesn't exist
        RuntimeError: If processing fails
    """
    run_path = Path(run_dir)
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    documents_dir = run_path / "documents"
    if not documents_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    logger.info(f"Processing actors for run: {run_dir}")

    # Initialize APIs
    gemini_api = GeminiAPI()
    foundry_client = FoundryClient(target=target)

    # Statistics
    stats = {
        "stat_blocks_found": 0,
        "stat_blocks_created": 0,
        "stat_blocks_reused": 0,
        "npcs_found": 0,
        "npcs_created": 0,
        "errors": []
    }

    # Step 1: Extract and parse stat blocks from all XML files
    logger.info("Step 1: Extracting stat blocks from XML files")
    all_stat_blocks = []
    xml_files = list(documents_dir.glob("*.xml"))

    for xml_file in xml_files:
        try:
            stat_blocks = extract_and_parse_stat_blocks(str(xml_file), api=gemini_api)
            all_stat_blocks.extend(stat_blocks)
            logger.info(f"Found {len(stat_blocks)} stat block(s) in {xml_file.name}")
        except Exception as e:
            logger.error(f"Failed to extract stat blocks from {xml_file.name}: {e}")
            stats["errors"].append(f"Stat block extraction failed for {xml_file.name}: {e}")

    stats["stat_blocks_found"] = len(all_stat_blocks)
    logger.info(f"Total stat blocks found: {len(all_stat_blocks)}")

    # Step 2: Extract NPCs from all XML files
    logger.info("Step 2: Extracting NPCs from XML files")
    all_npcs = []

    for xml_file in xml_files:
        try:
            with open(xml_file, 'r') as f:
                xml_content = f.read()

            npcs = identify_npcs_with_gemini(xml_content, api=gemini_api)
            all_npcs.extend(npcs)
            logger.info(f"Found {len(npcs)} NPC(s) in {xml_file.name}")
        except Exception as e:
            logger.error(f"Failed to extract NPCs from {xml_file.name}: {e}")
            stats["errors"].append(f"NPC extraction failed for {xml_file.name}: {e}")

    stats["npcs_found"] = len(all_npcs)
    logger.info(f"Total NPCs found: {len(all_npcs)}")

    # Step 3: Create/lookup creature actors
    logger.info("Step 3: Creating creature actors in FoundryVTT")
    creature_uuid_map = {}  # Map creature name (lowercase) → UUID

    for stat_block in all_stat_blocks:
        try:
            # Search compendium first
            existing_uuid = foundry_client.search_actor(stat_block.name)

            if existing_uuid:
                logger.info(f"Found existing actor in compendium: {stat_block.name}")
                creature_uuid_map[stat_block.name.lower()] = existing_uuid
                stats["stat_blocks_reused"] += 1
            else:
                # Create new actor
                logger.info(f"Creating new creature actor: {stat_block.name}")
                new_uuid = foundry_client.create_creature_actor(stat_block)
                creature_uuid_map[stat_block.name.lower()] = new_uuid
                stats["stat_blocks_created"] += 1

        except Exception as e:
            logger.error(f"Failed to process creature actor '{stat_block.name}': {e}")
            stats["errors"].append(f"Creature actor creation failed for {stat_block.name}: {e}")

    # Step 4: Create NPC actors
    logger.info("Step 4: Creating NPC actors in FoundryVTT")

    for npc in all_npcs:
        try:
            # Get stat block UUID if available (case-insensitive lookup)
            stat_block_uuid = creature_uuid_map.get(npc.creature_stat_block_name.lower())

            if not stat_block_uuid:
                # Try searching compendium for the creature type
                stat_block_uuid = foundry_client.search_actor(npc.creature_stat_block_name)

            if not stat_block_uuid:
                logger.warning(
                    f"NPC '{npc.name}' references unknown creature '{npc.creature_stat_block_name}', "
                    f"creating without stat block link"
                )

            # Create NPC actor
            logger.info(f"Creating NPC actor: {npc.name}")
            foundry_client.create_npc_actor(npc, stat_block_uuid=stat_block_uuid)
            stats["npcs_created"] += 1

        except Exception as e:
            logger.error(f"Failed to create NPC actor '{npc.name}': {e}")
            stats["errors"].append(f"NPC actor creation failed for {npc.name}: {e}")

    # Summary
    logger.info("=" * 60)
    logger.info("Actor processing complete!")
    logger.info(f"Stat blocks: {stats['stat_blocks_found']} found, "
                f"{stats['stat_blocks_created']} created, "
                f"{stats['stat_blocks_reused']} reused")
    logger.info(f"NPCs: {stats['npcs_found']} found, {stats['npcs_created']} created")
    if stats["errors"]:
        logger.warning(f"Errors encountered: {len(stats['errors'])}")
    logger.info("=" * 60)

    return stats
