#!/usr/bin/env python3
"""
Process Pit Fiend through COMPLETE end-to-end pipeline:
Raw text → StatBlock → ParsedActorData → Upload → Download → Save JSON

This script demonstrates the full actor generation workflow using the new
parallel parser.
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

from actor_pipeline.models import StatBlock
from foundry_converters.actors.parser import parse_stat_block_parallel
from foundry_converters.actors.converter import convert_to_foundry
from foundry.client import FoundryClient
from caches import SpellCache

load_dotenv(project_root / ".env")


def parse_raw_text_to_statblock(text: str) -> StatBlock:
    """
    Parse raw D&D 5e stat block text into StatBlock model.

    This is a simple regex-based parser for the standard stat block format.
    For production, consider using Gemini to parse more complex formats.
    """
    lines = text.strip().split('\n')

    # Extract name (first non-empty line)
    name = lines[1].strip() if len(lines) > 1 else "Unknown"

    # Extract basic stats with regex
    ac_match = re.search(r'Armor Class (\d+)', text)
    hp_match = re.search(r'Hit Points (\d+)', text)
    cr_match = re.search(r'Challenge (\d+)', text)

    armor_class = int(ac_match.group(1)) if ac_match else 10
    hit_points = int(hp_match.group(1)) if hp_match else 1
    challenge_rating = float(cr_match.group(1)) if cr_match else 0

    # Extract size and type
    type_match = re.search(r'(Tiny|Small|Medium|Large|Huge|Gargantuan) ([^,]+)', text)
    size = type_match.group(1).lower() if type_match else None
    creature_type = type_match.group(2).lower() if type_match else None

    # Extract alignment
    alignment_match = re.search(r', ([^,\n]+Evil|Neutral|Good)', text)
    alignment = alignment_match.group(1).lower() if alignment_match else None

    # Extract abilities
    abilities = {}
    ability_pattern = r'(STR|DEX|CON|INT|WIS|CHA)\s*\n\s*(\d+)'
    for match in re.finditer(ability_pattern, text):
        abilities[match.group(1)] = int(match.group(2))

    # Split into sections
    traits_section = extract_section(text, "Traits", "Actions")
    actions_section = extract_section(text, "Actions", "Reactions")

    # Extract traits (split by double newlines or paragraph breaks)
    traits = []
    if traits_section:
        # Split on trait names (capitalized words followed by period)
        trait_entries = re.split(r'\n(?=[A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+\.)', traits_section)
        traits = [t.strip() for t in trait_entries if t.strip() and len(t.strip()) > 20]

    # Extract actions
    actions = []
    if actions_section:
        action_entries = re.split(r'\n(?=[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\.)', actions_section)
        actions = [a.strip() for a in action_entries if a.strip() and len(a.strip()) > 20]

    return StatBlock(
        name=name,
        raw_text=text,
        armor_class=armor_class,
        hit_points=hit_points,
        challenge_rating=challenge_rating,
        size=size,
        type=creature_type,
        alignment=alignment,
        abilities=abilities if abilities else None,
        traits=traits,
        actions=actions,
        reactions=[]
    )


def extract_section(text: str, start_marker: str, end_marker: str = None) -> str:
    """Extract text between two section markers."""
    pattern = f"{start_marker}\s*\n(.*?)(?:{end_marker}|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


async def main():
    print("=" * 80)
    print("PIT FIEND END-TO-END PIPELINE")
    print("Using NEW parallel parser")
    print("=" * 80)

    # Step 1: Read raw text
    print("\n1. Reading raw stat block from pit_fiend.txt...")
    input_path = project_root / "data" / "foundry_examples" / "pit_fiend.txt"
    with open(input_path, "r") as f:
        raw_text = f.read()
    print(f"   ✓ Read {len(raw_text)} characters")

    # Step 2: Parse raw text → StatBlock
    print("\n2. Parsing raw text to StatBlock...")
    stat_block = parse_raw_text_to_statblock(raw_text)
    print(f"   ✓ Parsed StatBlock:")
    print(f"     - Name: {stat_block.name}")
    print(f"     - AC: {stat_block.armor_class}, HP: {stat_block.hit_points}, CR: {stat_block.challenge_rating}")
    print(f"     - Traits: {len(stat_block.traits)}")
    print(f"     - Actions: {len(stat_block.actions)}")
    print(f"     - Reactions: {len(stat_block.reactions)}")

    # Step 3: Load spell cache
    print("\n3. Loading spell cache...")
    spell_cache = SpellCache()
    spell_cache.load()
    print(f"   ✓ Spell cache loaded ({len(spell_cache._spell_by_name)} spells)")

    # Step 4: StatBlock → ParsedActorData (using parallel parser)
    print("\n4. Parsing StatBlock to ParsedActorData (parallel Gemini calls)...")
    print(f"   This will make {len(stat_block.actions) + len(stat_block.traits)} parallel API calls")

    parsed_actor = await parse_stat_block_parallel(
        stat_block,
        spell_cache=spell_cache,
        model_name="gemini-2.0-flash-exp"
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
    output_path = project_root / "output" / "pit_fiend_end_to_end.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(downloaded, f, indent=2)

    print(f"\n8. Saved to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Step 9: Verification
    print("\n9. Round-trip verification:")
    print(f"   Downloaded items:")
    for item in downloaded["items"]:
        print(f"     - {item['name']} ({item['type']})")

    # Verify no items were lost
    uploaded_items = {i["name"] for i in foundry_json["items"]}
    downloaded_items_no_spells = {i["name"] for i in downloaded["items"] if i["type"] != "spell"}
    missing_items = uploaded_items - downloaded_items_no_spells

    if missing_items:
        print(f"\n   ✗ WARNING: Missing items after round-trip: {missing_items}")

    # Check for duplicate spells
    spell_names = [i["name"] for i in downloaded["items"] if i["type"] == "spell"]
    if len(spell_names) != len(set(spell_names)):
        from collections import Counter
        duplicates = [name for name, count in Counter(spell_names).items() if count > 1]
        print(f"\n   ✗ WARNING: Duplicate spells detected: {duplicates}")

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\nRaw text → StatBlock → ParsedActorData → FoundryVTT → Downloaded JSON")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
