"""
Deduplicate items by name, prioritizing official sources.

Priority order:
1. Player's Handbook (dnd-players-handbook)
2. D&D 5e 2024 rules (dnd5e.*.24)
3. D&D 5e SRD (dnd5e.*)
4. Other sources
"""

import logging
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_source_priority(uuid: str) -> int:
    """
    Get priority score for an item's source (lower = higher priority).

    Args:
        uuid: Item UUID like "Compendium.dnd5e.spells.abc123"

    Returns:
        Priority score (0 = highest priority)
    """
    if 'dnd-players-handbook' in uuid:
        return 0  # Highest priority - official Player's Handbook
    elif '.24' in uuid or 'dnd5e.spells24' in uuid or 'dnd5e.items24' in uuid:
        return 1  # 2024 rules update
    elif 'dnd5e.' in uuid:
        return 2  # Classic D&D 5e SRD
    else:
        return 3  # Other sources (homebrew, modules, etc.)


def deduplicate_items(
    items: List[Dict],
    dedupe_key: str = 'name',
    verbose: bool = True
) -> List[Dict]:
    """
    Deduplicate items by a key (typically name), keeping highest priority source.

    Args:
        items: List of item dicts with at least 'uuid' and dedupe_key fields
        dedupe_key: Field to use for deduplication (default: 'name')
        verbose: Log duplicate removals

    Returns:
        Deduplicated list of items sorted by dedupe_key
    """
    # Group by dedupe_key
    items_by_key = defaultdict(list)
    for item in items:
        key = item.get(dedupe_key, '').strip()
        if key:
            items_by_key[key].append(item)

    # For each key, pick the highest priority source
    deduplicated = []
    duplicates_removed = 0

    for key, item_variants in items_by_key.items():
        # Sort by priority (lower score = higher priority)
        item_variants_sorted = sorted(
            item_variants,
            key=lambda i: get_source_priority(i.get('uuid', ''))
        )

        # Take the first one (highest priority)
        best_item = item_variants_sorted[0]
        deduplicated.append(best_item)

        # Log if we had duplicates
        if len(item_variants) > 1:
            duplicates_removed += len(item_variants) - 1

            if verbose:
                sources = [
                    i.get('uuid', 'unknown').split('.')[1] if '.' in i.get('uuid', '') else 'unknown'
                    for i in item_variants
                ]
                logger.debug(f"  {key}: kept {sources[0]}, removed {', '.join(sources[1:])}")

    # Sort by dedupe_key
    deduplicated_sorted = sorted(deduplicated, key=lambda i: i.get(dedupe_key, ''))

    logger.info(f"✓ Removed {duplicates_removed} duplicates ({len(deduplicated_sorted)} unique items remain)")

    return deduplicated_sorted


def get_source_stats(items: List[Dict]) -> Dict[str, int]:
    """
    Get statistics on item sources.

    Args:
        items: List of item dicts with 'uuid' field

    Returns:
        Dict mapping source names to counts
    """
    sources = defaultdict(int)

    for item in items:
        uuid = item.get('uuid', '')

        if 'dnd-players-handbook' in uuid:
            sources["Player's Handbook"] += 1
        elif '.24' in uuid or 'dnd5e.spells24' in uuid or 'dnd5e.items24' in uuid:
            sources['D&D 5e 2024'] += 1
        elif 'dnd5e.' in uuid:
            sources['D&D 5e SRD'] += 1
        else:
            sources['Other'] += 1

    return dict(sources)
