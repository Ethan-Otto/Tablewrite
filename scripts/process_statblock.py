#!/usr/bin/env python3
"""
Process any stat block through complete end-to-end pipeline.

Usage:
    python scripts/process_statblock.py data/foundry_examples/gaint_octopus.txt
    python scripts/process_statblock.py data/foundry_examples/pit_fiend.txt
"""

import sys
import json
import asyncio
import re
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from actors.statblock_parser import parse_raw_text_to_statblock
from foundry.actors.parser import parse_stat_block_parallel
from foundry.actors.converter import convert_to_foundry
from foundry.client import FoundryClient
from foundry.actors.spell_cache import SpellCache

load_dotenv(project_root / ".env")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/process_statblock.py <path_to_txt_file>")
        print("Example: python scripts/process_statblock.py data/foundry_examples/gaint_octopus.txt")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    creature_name = input_file.stem.replace("_", " ").title()

    print("=" * 80)
    print(f"PROCESSING: {creature_name}")
    print("=" * 80)

    # Step 1: Read raw text
    print(f"\n1. Reading stat block from {input_file.name}...")
    with open(input_file, "r") as f:
        raw_text = f.read()
    print(f"   ✓ Read {len(raw_text)} characters")

    # Step 2: Parse raw text → StatBlock (using Gemini)
    print("\n2. Parsing raw text to StatBlock (using Gemini)...")
    stat_block = await parse_raw_text_to_statblock(raw_text)
    print(f"   ✓ Parsed StatBlock:")
    print(f"     - Name: {stat_block.name}")
    print(f"     - AC: {stat_block.armor_class}, HP: {stat_block.hit_points}, CR: {stat_block.challenge_rating}")
    print(f"     - Traits: {len(stat_block.traits)}")
    print(f"     - Actions: {len(stat_block.actions)}")
    if stat_block.skills:
        print(f"     - Skills: {', '.join(f'{k.title()} +{v}' for k, v in stat_block.skills.items())}")
    if stat_block.saving_throws:
        print(f"     - Saving Throws: {', '.join(f'{k.upper()} +{v}' for k, v in stat_block.saving_throws.items())}")

    # Step 3: Load spell cache
    print("\n3. Loading spell cache...")
    spell_cache = SpellCache()
    spell_cache.load()
    print(f"   ✓ Spell cache loaded ({len(spell_cache._spell_by_name)} spells)")

    # Step 4: StatBlock → ParsedActorData (using parallel parser)
    print("\n4. Parsing StatBlock to ParsedActorData (parallel Gemini calls)...")
    total_calls = len(stat_block.actions) + len(stat_block.traits)
    print(f"   This will make {total_calls} parallel API calls")

    parsed_actor = await parse_stat_block_parallel(
        stat_block,
        spell_cache=spell_cache
    )

    print(f"   ✓ Parsed to ParsedActorData:")
    print(f"     - Attacks: {len(parsed_actor.attacks)}")
    print(f"     - Traits: {len(parsed_actor.traits)}")
    print(f"     - Multiattack: {parsed_actor.multiattack is not None}")
    print(f"     - Innate Spellcasting: {parsed_actor.innate_spellcasting is not None}")

    if parsed_actor.innate_spellcasting:
        print(f"       - Spells: {len(parsed_actor.innate_spellcasting.spells)}")

    # Step 5: Convert to FoundryVTT format
    print("\n5. Converting to FoundryVTT format...")
    foundry_json, spell_uuids = convert_to_foundry(parsed_actor, spell_cache=spell_cache)
    print(f"   ✓ Converted to FoundryVTT format")
    print(f"     - Items in payload: {len(foundry_json['items'])}")
    print(f"     - Spells via /give: {len(spell_uuids)}")

    # Item breakdown
    weapon_count = sum(1 for i in foundry_json["items"] if i["type"] == "weapon")
    feat_count = sum(1 for i in foundry_json["items"] if i["type"] == "feat")
    print(f"     - Weapons: {weapon_count}")
    print(f"     - Feats: {feat_count}")

    # Step 6: Upload to FoundryVTT
    print("\n6. Uploading to FoundryVTT...")
    client = FoundryClient()
    actor_uuid = client.actors.create_actor(foundry_json, spell_uuids=spell_uuids)
    print(f"   ✓ Uploaded: {actor_uuid}")

    # Step 7: Download from FoundryVTT
    print("\n7. Downloading from FoundryVTT...")
    downloaded = client.actors.get_actor(actor_uuid)
    print(f"   ✓ Downloaded: {downloaded['name']}")
    print(f"     - Total items: {len(downloaded['items'])}")

    # Item breakdown
    downloaded_weapons = [i for i in downloaded["items"] if i["type"] == "weapon"]
    downloaded_feats = [i for i in downloaded["items"] if i["type"] == "feat"]
    downloaded_spells = [i for i in downloaded["items"] if i["type"] == "spell"]

    print(f"     - Weapons: {len(downloaded_weapons)}")
    print(f"     - Feats: {len(downloaded_feats)}")
    print(f"     - Spells: {len(downloaded_spells)}")

    # Step 8: Save to file
    output_filename = f"{input_file.stem}_end_to_end.json"
    output_path = project_root / "output" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(downloaded, f, indent=2)

    print(f"\n8. Saved to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Step 9: Verification
    print("\n9. Downloaded items:")
    for item in downloaded["items"]:
        print(f"     - {item['name']} ({item['type']})")

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
