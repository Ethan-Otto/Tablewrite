#!/usr/bin/env python3
"""
Test creating 3 actors with different weapon combinations to isolate the bug.

This script creates:
1. Actor with 2 weapons
2. Actor with 3 weapons
3. Actor with 4 weapons

Then verifies all weapons survive the round-trip.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from foundry.client import FoundryClient
from foundry.actors.models import ParsedActorData, Attack, DamageFormula
from foundry.actors.converter import convert_to_foundry


def create_test_actor(name: str, weapon_names: list[str]) -> tuple[str, list[str], list[str]]:
    """
    Create an actor with specified weapons.

    Returns:
        (actor_uuid, weapons_uploaded, weapons_downloaded)
    """
    # Create attacks
    attacks = []
    damage_types = ["slashing", "piercing", "bludgeoning", "fire", "cold"]

    for i, weapon_name in enumerate(weapon_names):
        attacks.append(
            Attack(
                name=weapon_name,
                attack_type="melee",
                attack_bonus=5 + i,
                reach=5 + (i * 5),
                damage=[DamageFormula(
                    number=1 + i,
                    denomination=6 + (i * 2),
                    bonus=f"+{3 + i}",
                    type=damage_types[i % len(damage_types)]
                )]
            )
        )

    # Create actor
    actor = ParsedActorData(
        source_statblock_name="Test",
        name=name,
        size="medium",
        creature_type="humanoid",
        armor_class=15,
        hit_points=50,
        challenge_rating=2,
        abilities={"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10},
        attacks=attacks
    )

    # Convert and upload
    foundry_json = convert_to_foundry(actor, spell_cache=None)
    weapons_uploaded = [i['name'] for i in foundry_json['items'] if i['type'] == 'weapon']

    client = FoundryClient(target="local")
    actor_uuid = client.actors.create_actor(foundry_json)

    # Download and verify
    downloaded = client.actors.get_actor(actor_uuid)
    weapons_downloaded = [i['name'] for i in downloaded['items'] if i['type'] == 'weapon']

    return actor_uuid, weapons_uploaded, weapons_downloaded


def main():
    print("=" * 70)
    print("MULTIPLE ACTOR WEAPON TEST")
    print("=" * 70)

    # Define test cases
    test_cases = [
        ("Actor 1: Two Weapons", ["Sword", "Dagger"]),
        ("Actor 2: Three Weapons", ["Longsword", "Shortsword", "Crossbow"]),
        ("Actor 3: Four Weapons", ["Bite", "Claw", "Tail", "Breath Weapon"]),
    ]

    results = []

    for name, weapons in test_cases:
        print(f"\n{name}")
        print("-" * 70)
        print(f"Creating actor with weapons: {weapons}")

        uuid, uploaded, downloaded = create_test_actor(name, weapons)

        print(f"  UUID: {uuid}")
        print(f"  Uploaded:   {uploaded}")
        print(f"  Downloaded: {downloaded}")

        # Check for issues
        success = uploaded == downloaded
        missing = set(uploaded) - set(downloaded)
        extra = set(downloaded) - set(uploaded)
        duplicates = [w for w in set(downloaded) if downloaded.count(w) > 1]

        if success:
            print(f"  ✓ SUCCESS: All {len(uploaded)} weapons intact")
            results.append((name, True, None))
        else:
            print(f"  ✗ FAILURE:")
            if missing:
                print(f"    Missing: {missing}")
            if extra:
                print(f"    Extra: {extra}")
            if duplicates:
                print(f"    Duplicates: {duplicates}")

            error = f"Missing: {missing}, Duplicates: {duplicates}" if (missing or duplicates) else "Unknown"
            results.append((name, False, error))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for name, success, error in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       {error}")

    print(f"\nTotal: {passed}/{len(results)} passed, {failed}/{len(results)} failed")

    if failed > 0:
        print("\n⚠️  Some actors lost weapons during create!")
        sys.exit(1)
    else:
        print("\n✓ All actors preserved their weapons!")
        sys.exit(0)


if __name__ == "__main__":
    main()
