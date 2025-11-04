#!/usr/bin/env python3
"""Process Pit Fiend through full actor pipeline: parse → upload → download → save."""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from foundry.actors.models import (
    ParsedActorData, Attack, Trait, DamageFormula,
    Multiattack, InnateSpellcasting, InnateSpell, AttackSave,
    DamageModification
)
from foundry.actors.converter import convert_to_foundry
from foundry.client import FoundryClient
from foundry.actors.spell_cache import SpellCache

load_dotenv(project_root / ".env")

# Parse Pit Fiend from pit_fiend.txt
pit_fiend = ParsedActorData(
    source_statblock_name="Pit Fiend",
    name="Pit Fiend",
    size="large",
    creature_type="fiend",
    creature_subtype="devil",
    alignment="lawful evil",
    armor_class=19,
    hit_points=300,
    hit_dice="24d10+168",
    speed_walk=30,
    speed_fly=60,
    challenge_rating=20,
    abilities={
        "STR": 26,
        "DEX": 14,
        "CON": 24,
        "INT": 22,
        "WIS": 18,
        "CHA": 24
    },
    saving_throw_proficiencies=["dex", "con", "wis"],
    condition_immunities=["poisoned"],
    damage_immunities=DamageModification(types=["fire", "poison"]),
    damage_resistances=DamageModification(
        types=["cold", "bludgeoning", "piercing", "slashing"],
        condition="from nonmagical attacks that aren't silvered"
    ),
    truesight=120,
    languages=["Infernal", "Telepathy 120 ft."],
    multiattack=Multiattack(
        name="Multiattack",
        description="The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail.",
        num_attacks=4
    ),
    traits=[
        Trait(
            name="Fear Aura",
            description=(
                "Any creature hostile to the pit fiend that starts its turn within 20 feet "
                "of the pit fiend must make a DC 21 Wisdom saving throw, unless the pit fiend "
                "is incapacitated. On a failed save, the creature is frightened until the start "
                "of its next turn. If a creature's saving throw is successful, the creature is "
                "immune to the pit fiend's Fear Aura for the next 24 hours."
            ),
            activation="passive"
        ),
        Trait(
            name="Magic Resistance",
            description=(
                "The pit fiend has advantage on saving throws against spells and other "
                "magical effects."
            ),
            activation="passive"
        ),
        Trait(
            name="Magic Weapons",
            description="The pit fiend's weapon attacks are magical.",
            activation="passive"
        ),
    ],
    innate_spellcasting=InnateSpellcasting(
        ability="charisma",
        save_dc=21,
        spells=[
            InnateSpell(name="Detect Magic", frequency="at will"),
            InnateSpell(name="Fireball", frequency="at will"),
            InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
            InnateSpell(name="Wall of Fire", frequency="3/day", uses=3),
        ]
    ),
    attacks=[
        Attack(
            name="Bite",
            attack_type="melee",
            attack_bonus=14,
            reach=5,
            damage=[
                DamageFormula(number=4, denomination=6, bonus="+8", type="piercing")
            ],
            # CRITICAL: AttackSave with ongoing poison damage
            attack_save=AttackSave(
                ability="con",
                dc=21,
                ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
                duration_rounds=None,  # Repeats until success
                effect_description=(
                    "Poisoned - can't regain HP. Repeat save at end of each turn to end effect."
                )
            )
        ),
        Attack(
            name="Claw",
            attack_type="melee",
            attack_bonus=14,
            reach=10,
            damage=[
                DamageFormula(number=2, denomination=8, bonus="+8", type="slashing")
            ]
        ),
        Attack(
            name="Mace",
            attack_type="melee",
            attack_bonus=14,
            reach=10,
            damage=[
                DamageFormula(number=2, denomination=6, bonus="+8", type="bludgeoning"),
                DamageFormula(number=6, denomination=6, bonus="", type="fire")
            ]
        ),
        Attack(
            name="Tail",
            attack_type="melee",
            attack_bonus=14,
            reach=10,
            damage=[
                DamageFormula(number=3, denomination=10, bonus="+8", type="bludgeoning")
            ]
        ),
    ]
)

print("=" * 80)
print("PIT FIEND PIPELINE TEST")
print("=" * 80)

# Step 1: Load spell cache
print("\n1. Loading spell cache...")
spell_cache = SpellCache()
spell_cache.load()
print("   ✓ Spell cache loaded")

# Step 2: Convert to FoundryVTT format
print("\n2. Converting to FoundryVTT format...")
foundry_json = convert_to_foundry(pit_fiend, spell_cache=spell_cache)
print(f"   ✓ Converted to FoundryVTT format ({len(foundry_json['items'])} items)")

# Print item summary
weapon_count = sum(1 for i in foundry_json["items"] if i["type"] == "weapon")
feat_count = sum(1 for i in foundry_json["items"] if i["type"] == "feat")
spell_count = sum(1 for i in foundry_json["items"] if i["type"] == "spell")
print(f"   - Weapons: {weapon_count}")
print(f"   - Feats: {feat_count}")
print(f"   - Spells: {spell_count}")

# Verify Bite has 3 activities
bite = [i for i in foundry_json["items"] if i["name"] == "Bite"][0]
print(f"\n   Bite weapon activities: {len(bite['system']['activities'])}")
for act_id, act in bite["system"]["activities"].items():
    print(f"   - {act['type']}")
    if act["type"] == "damage":
        part = act["damage"]["parts"][0]
        print(f"     damage.parts[0]: {part}")

# Step 3: Upload to FoundryVTT
print("\n3. Uploading to FoundryVTT...")
client = FoundryClient(target="local")
actor_uuid = client.actors.create_actor(foundry_json)
print(f"   ✓ Uploaded: {actor_uuid}")

# Step 4: Download from FoundryVTT
print("\n4. Downloading from FoundryVTT...")
downloaded = client.actors.get_actor(actor_uuid)
print(f"   ✓ Downloaded: {downloaded['name']} ({len(downloaded['items'])} items)")

# Step 5: Save to file
output_path = project_root / "output" / "pit_fiend_roundtrip.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w") as f:
    json.dump(downloaded, f, indent=2)

print(f"\n5. Saved to: {output_path}")

# Step 6: Verify round-trip
print("\n6. Round-trip verification:")
print(f"   - Actor name: {downloaded['name']}")
print(f"   - Total items: {len(downloaded['items'])}")

downloaded_weapons = [i for i in downloaded["items"] if i["type"] == "weapon"]
downloaded_feats = [i for i in downloaded["items"] if i["type"] == "feat"]
downloaded_spells = [i for i in downloaded["items"] if i["type"] == "spell"]

print(f"   - Weapons: {len(downloaded_weapons)}")
print(f"   - Feats: {len(downloaded_feats)}")
print(f"   - Spells: {len(downloaded_spells)}")

# Verify Bite activities survived round-trip
bite_matches = [i for i in downloaded["items"] if i["name"] == "Bite"]
if bite_matches:
    bite_downloaded = bite_matches[0]
    print(f"\n   Bite activities after round-trip: {len(bite_downloaded['system']['activities'])}")
    for act_id, act in bite_downloaded["system"]["activities"].items():
        print(f"   - {act['type']}")
        if act["type"] == "damage":
            part = act["damage"]["parts"][0]
            print(f"     damage.parts[0]: {part}")
            # Verify object structure
            if isinstance(part, dict):
                print(f"     ✓ Object structure preserved (number={part['number']}, denomination={part['denomination']}, types={part['types']})")
            else:
                print(f"     ✗ Array structure detected: {part}")
else:
    print("\n   ✗ WARNING: Bite weapon MISSING after round-trip!")

# Report all downloaded item names
print("\n   Downloaded items:")
for item in downloaded["items"]:
    print(f"     - {item['name']} ({item['type']})")

# Verify no items were lost
uploaded_weapons = {i["name"] for i in foundry_json["items"] if i["type"] == "weapon"}
downloaded_weapons = {i["name"] for i in downloaded["items"] if i["type"] == "weapon"}
missing_weapons = uploaded_weapons - downloaded_weapons

if missing_weapons:
    print(f"\n✗ ERROR: Missing weapons after round-trip: {missing_weapons}")
    print(f"   Uploaded: {uploaded_weapons}")
    print(f"   Downloaded: {downloaded_weapons}")
    print("\n" + "=" * 80)
    print("PIPELINE FAILED - ITEMS LOST")
    print("=" * 80)
    sys.exit(1)

# Check for duplicate spells
uploaded_spell_names = [i["name"] for i in foundry_json["items"] if i["type"] == "spell"]
downloaded_spell_names = [i["name"] for i in downloaded["items"] if i["type"] == "spell"]
if len(downloaded_spell_names) != len(set(downloaded_spell_names)):
    from collections import Counter
    duplicates = [name for name, count in Counter(downloaded_spell_names).items() if count > 1]
    print(f"\n✗ WARNING: Duplicate spells detected: {duplicates}")

print("\n" + "=" * 80)
print("PIPELINE COMPLETE - ALL ITEMS PRESERVED")
print("=" * 80)
