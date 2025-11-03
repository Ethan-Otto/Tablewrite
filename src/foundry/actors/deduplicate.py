"""
Deduplicate actors by name, prioritizing official sources.

Priority order:
1. Player's Handbook (dnd-players-handbook)
2. D&D 5e 2024 rules (dnd5e.actors24)
3. D&D 5e SRD (dnd5e.monsters)
4. Other sources
"""

import logging
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_source_priority(uuid: str) -> int:
    """
    Get priority score for an actor's source (lower = higher priority).

    Args:
        uuid: Actor UUID like "Compendium.dnd5e.monsters.abc123"

    Returns:
        Priority score (0 = highest priority)
    """
    if 'dnd-players-handbook' in uuid:
        return 0  # Highest priority - official Player's Handbook
    elif '.actors24' in uuid or 'dnd5e.actors24' in uuid:
        return 1  # 2024 rules update
    elif 'dnd5e.monsters' in uuid or 'dnd5e.' in uuid:
        return 2  # Classic D&D 5e SRD/monsters
    else:
        return 3  # Other sources (homebrew, modules, etc.)


def deduplicate_actors(
    actors: List[Dict],
    dedupe_key: str = 'name',
    verbose: bool = True
) -> List[Dict]:
    """
    Deduplicate actors by a key (typically name), keeping highest priority source.

    Args:
        actors: List of actor dicts with at least 'uuid' and dedupe_key fields
        dedupe_key: Field to use for deduplication (default: 'name')
        verbose: Log duplicate removals

    Returns:
        Deduplicated list of actors sorted by dedupe_key
    """
    # Group by dedupe_key
    actors_by_key = defaultdict(list)
    for actor in actors:
        key = actor.get(dedupe_key, '').strip()
        if key:
            actors_by_key[key].append(actor)

    # For each key, pick the highest priority source
    deduplicated = []
    duplicates_removed = 0

    for key, actor_variants in actors_by_key.items():
        # Sort by priority (lower score = higher priority)
        actor_variants_sorted = sorted(
            actor_variants,
            key=lambda a: get_source_priority(a.get('uuid', ''))
        )

        # Take the first one (highest priority)
        best_actor = actor_variants_sorted[0]
        deduplicated.append(best_actor)

        # Log if we had duplicates
        if len(actor_variants) > 1:
            duplicates_removed += len(actor_variants) - 1

            if verbose:
                sources = [a.get('uuid', '').split('.')[1] if '.' in a.get('uuid', '') else 'unknown'
                          for a in actor_variants_sorted[1:]]
                logger.debug(
                    f"Removed {len(actor_variants) - 1} duplicate(s) of '{key}' "
                    f"(kept {actor_variants_sorted[0].get('uuid', '').split('.')[1]}, "
                    f"removed {', '.join(sources)})"
                )

    if verbose and duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate actors")

    # Sort by dedupe key
    deduplicated_sorted = sorted(deduplicated, key=lambda a: a.get(dedupe_key, '').lower())

    return deduplicated_sorted


def get_source_stats(actors: List[Dict]) -> Dict[str, int]:
    """
    Get statistics about actor sources.

    Args:
        actors: List of actor dicts with 'uuid' field

    Returns:
        Dict mapping source names to counts
    """
    stats = defaultdict(int)

    for actor in actors:
        uuid = actor.get('uuid', '')

        if 'dnd-players-handbook' in uuid:
            stats["Player's Handbook"] += 1
        elif '.actors24' in uuid or 'dnd5e.actors24' in uuid:
            stats["D&D 5e 2024"] += 1
        elif 'dnd5e.monsters' in uuid:
            stats["D&D 5e SRD"] += 1
        else:
            stats["Other"] += 1

    return dict(stats)
