"""Tests for adding compendium spells via /give endpoint."""

import pytest
from foundry_converters.actors.models import ParsedActorData, Attack, DamageFormula, InnateSpellcasting, InnateSpell
from foundry_converters.actors.converter import convert_to_foundry
from foundry.client import FoundryClient
from foundry.actors.spell_cache import SpellCache


@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.asyncio
async def test_spell_via_give_workflow(check_foundry_credentials):
    """Test that spells added via /give have full compendium data."""
    # Create actor with weapons and spells
    actor = ParsedActorData(
        source_statblock_name="Test",
        name="Spell Via Give Test",
        size="medium",
        creature_type="humanoid",
        armor_class=15,
        hit_points=50,
        challenge_rating=2,
        abilities={"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10},
        attacks=[
            Attack(name="Sword", attack_type="melee", attack_bonus=5, reach=5,
                   damage=[DamageFormula(number=1, denomination=8, bonus="+3", type="slashing")])
        ],
        innate_spellcasting=InnateSpellcasting(
            ability="charisma",
            save_dc=15,
            spells=[
                InnateSpell(name="Fireball", frequency="at will"),
                InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
            ]
        )
    )

    # Load spell cache
    spell_cache = SpellCache()
    spell_cache.load()

    # Convert with new API
    actor_json, spell_uuids = await convert_to_foundry(actor, spell_cache=spell_cache)

    # Verify conversion
    assert len(spell_uuids) == 2, "Should collect 2 spell UUIDs"
    assert all("Compendium." in uuid for uuid in spell_uuids), "All UUIDs should be compendium refs"

    # Verify weapons in payload
    weapons = [i for i in actor_json["items"] if i["type"] == "weapon"]
    assert len(weapons) == 1, "Should have 1 weapon in payload"
    assert weapons[0]["name"] == "Sword"

    # Verify spells NOT in payload by default
    spells_in_payload = [i for i in actor_json["items"] if i["type"] == "spell"]
    assert len(spells_in_payload) == 0, "Should have 0 spells in payload (added via /give)"

    # Create actor with spell UUIDs
    client = FoundryClient()
    actor_uuid = client.actors.create_actor(actor_json, spell_uuids=spell_uuids)

    # Download and verify
    downloaded = client.actors.get_actor(actor_uuid)

    downloaded_weapons = [i["name"] for i in downloaded["items"] if i["type"] == "weapon"]
    downloaded_spells = [i["name"] for i in downloaded["items"] if i["type"] == "spell"]

    assert downloaded_weapons == ["Sword"], "Weapon should be preserved"
    assert set(downloaded_spells) == {"Fireball", "Hold Monster"}, "All spells should be added"

    # Verify spells have full compendium data
    for spell_item in downloaded["items"]:
        if spell_item["type"] == "spell":
            system_data = spell_item.get("system", {})
            assert system_data.get("description", {}).get("value"), \
                f"Spell {spell_item['name']} should have description"
            assert system_data.get("activities"), \
                f"Spell {spell_item['name']} should have activities"


@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.asyncio
async def test_backward_compatibility_with_include_spells_flag(check_foundry_credentials):
    """Test that include_spells_in_payload=True still works (for backward compatibility)."""
    actor = ParsedActorData(
        source_statblock_name="Test",
        name="Backward Compat Test",
        size="medium",
        creature_type="humanoid",
        armor_class=15,
        hit_points=50,
        challenge_rating=2,
        abilities={"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10},
        innate_spellcasting=InnateSpellcasting(
            ability="charisma",
            save_dc=15,
            spells=[InnateSpell(name="Fireball", frequency="at will")]
        )
    )

    spell_cache = SpellCache()
    spell_cache.load()

    # Convert with include_spells_in_payload=True
    actor_json, spell_uuids = await convert_to_foundry(
        actor,
        spell_cache=spell_cache,
        include_spells_in_payload=True
    )

    # Verify spells ARE in payload when flag is True
    spells_in_payload = [i for i in actor_json["items"] if i["type"] == "spell"]
    assert len(spells_in_payload) == 1, "Should have 1 spell in payload when flag is True"

    # Verify UUIDs still collected
    assert len(spell_uuids) == 1, "Should still collect spell UUIDs"


@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.asyncio
async def test_multiple_actors_with_spells(check_foundry_credentials):
    """Test creating multiple actors with spells doesn't cause race conditions."""
    spell_cache = SpellCache()
    spell_cache.load()
    client = FoundryClient()

    results = []

    for i in range(1, 4):
        actor = ParsedActorData(
            source_statblock_name="Test",
            name=f"Test Actor {i}",
            size="medium",
            creature_type="humanoid",
            armor_class=15,
            hit_points=50,
            challenge_rating=2,
            abilities={"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10},
            attacks=[
                Attack(name=f"Weapon_{j}", attack_type="melee", attack_bonus=5, reach=5,
                       damage=[DamageFormula(number=1, denomination=6, bonus="+3", type="slashing")])
                for j in range(1, i + 1)  # 1 weapon for actor 1, 2 for actor 2, 3 for actor 3
            ],
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=15,
                spells=[
                    InnateSpell(name="Fireball", frequency="at will"),
                    InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                ]
            )
        )

        actor_json, spell_uuids = await convert_to_foundry(actor, spell_cache=spell_cache)
        actor_uuid = client.actors.create_actor(actor_json, spell_uuids=spell_uuids)

        downloaded = client.actors.get_actor(actor_uuid)
        weapons = [item["name"] for item in downloaded["items"] if item["type"] == "weapon"]
        spells = [item["name"] for item in downloaded["items"] if item["type"] == "spell"]

        results.append({
            "actor": i,
            "weapons": weapons,
            "spells": spells,
            "expected_weapons": i,
            "expected_spells": 2
        })

    # Verify all actors have correct items
    for result in results:
        assert len(result["weapons"]) == result["expected_weapons"], \
            f"Actor {result['actor']} should have {result['expected_weapons']} weapons, got {len(result['weapons'])}"
        assert len(result["spells"]) == result["expected_spells"], \
            f"Actor {result['actor']} should have {result['expected_spells']} spells, got {len(result['spells'])}"


@pytest.mark.unit
async def test_converter_return_format():
    """Test that converter returns tuple of (actor_json, spell_uuids)."""
    actor = ParsedActorData(
        source_statblock_name="Test",
        name="Test Actor",
        size="medium",
        creature_type="humanoid",
        armor_class=15,
        hit_points=50,
        challenge_rating=2,
        abilities={"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10},
        attacks=[]
    )

    result = await convert_to_foundry(actor, spell_cache=None)

    # Verify return type
    assert isinstance(result, tuple), "Should return a tuple"
    assert len(result) == 2, "Should return tuple of length 2"

    actor_json, spell_uuids = result

    assert isinstance(actor_json, dict), "First element should be dict"
    assert isinstance(spell_uuids, list), "Second element should be list"
    assert actor_json["name"] == "Test Actor"
