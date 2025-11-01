#!/usr/bin/env python3
"""
Deduplicate spells by name, prioritizing official sources.

Priority order:
1. Player's Handbook (dnd-players-handbook)
2. D&D 5e 2024 rules (dnd5e.spells24)
3. D&D 5e SRD (dnd5e.spells)
4. Other sources
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def get_source_priority(uuid: str) -> int:
    """
    Get priority score for a spell's source (lower = higher priority).

    Args:
        uuid: Spell UUID like "Compendium.dnd5e.spells.abc123"

    Returns:
        Priority score (0 = highest priority)
    """
    if 'dnd-players-handbook' in uuid:
        return 0  # Highest priority
    elif 'dnd5e.spells24' in uuid:
        return 1  # 2024 rules
    elif 'dnd5e.spells' in uuid:
        return 2  # Classic SRD
    else:
        return 3  # Other sources (homebrew, modules, etc.)


def deduplicate_spells(spells: List[Dict]) -> List[Dict]:
    """
    Deduplicate spells by name, keeping highest priority source.

    Args:
        spells: List of spell dicts with 'name' and 'uuid' fields

    Returns:
        Deduplicated list of spells
    """
    # Group by name
    spells_by_name = defaultdict(list)
    for spell in spells:
        name = spell.get('name', '').strip()
        if name:
            spells_by_name[name].append(spell)

    # For each name, pick the highest priority source
    deduplicated = []
    for name, spell_variants in spells_by_name.items():
        # Sort by priority (lower score = higher priority)
        spell_variants_sorted = sorted(
            spell_variants,
            key=lambda s: get_source_priority(s.get('uuid', ''))
        )

        # Take the first one (highest priority)
        best_spell = spell_variants_sorted[0]
        deduplicated.append(best_spell)

        # Log if we had duplicates
        if len(spell_variants) > 1:
            sources = [s.get('uuid', 'unknown').split('.')[1] if '.' in s.get('uuid', '') else 'unknown'
                      for s in spell_variants]
            print(f"  {name}: kept {sources[0]}, removed {', '.join(sources[1:])}")

    # Sort by name
    deduplicated_sorted = sorted(deduplicated, key=lambda s: s.get('name', ''))

    return deduplicated_sorted


def main():
    # Load all spells
    input_file = Path(__file__).parent.parent / 'data' / 'foundry_examples' / 'all_spells.json'
    output_file = Path(__file__).parent.parent / 'data' / 'foundry_examples' / 'spells_deduplicated.json'

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    print(f"Loading spells from {input_file.name}...\n")
    with open(input_file) as f:
        all_spells = json.load(f)

    print(f"Total spells before deduplication: {len(all_spells)}\n")

    # Count by source
    sources = defaultdict(int)
    for spell in all_spells:
        uuid = spell.get('uuid', '')
        if 'dnd-players-handbook' in uuid:
            sources['Player\'s Handbook'] += 1
        elif 'dnd5e.spells24' in uuid:
            sources['D&D 5e 2024'] += 1
        elif 'dnd5e.spells' in uuid:
            sources['D&D 5e SRD'] += 1
        else:
            sources['Other'] += 1

    print("Sources before deduplication:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count}")

    print("\nDeduplicating...\n")
    deduplicated = deduplicate_spells(all_spells)

    print(f"\n{'='*60}")
    print(f"Total unique spell names: {len(deduplicated)}")
    print(f"Removed {len(all_spells) - len(deduplicated)} duplicates")
    print(f"{'='*60}\n")

    # Count by source after deduplication
    sources_after = defaultdict(int)
    for spell in deduplicated:
        uuid = spell.get('uuid', '')
        if 'dnd-players-handbook' in uuid:
            sources_after['Player\'s Handbook'] += 1
        elif 'dnd5e.spells24' in uuid:
            sources_after['D&D 5e 2024'] += 1
        elif 'dnd5e.spells' in uuid:
            sources_after['D&D 5e SRD'] += 1
        else:
            sources_after['Other'] += 1

    print("Sources after deduplication:")
    for source, count in sorted(sources_after.items()):
        print(f"  {source}: {count}")

    # Save deduplicated list
    with open(output_file, 'w') as f:
        json.dump(deduplicated, f, indent=2)

    print(f"\n✓ Saved {len(deduplicated)} deduplicated spells to {output_file.name}")

    # Show first 20
    print(f"\n{'Name':<40} {'Source':<25} {'UUID'}")
    print("-" * 120)
    for spell in deduplicated[:20]:
        uuid = spell.get('uuid', 'UNKNOWN')
        source = uuid.split('.')[1] if '.' in uuid else 'unknown'
        print(f"{spell.get('name', 'UNKNOWN'):<40} {source:<25} {uuid}")


if __name__ == "__main__":
    main()
