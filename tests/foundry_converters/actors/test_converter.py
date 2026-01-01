"""Tests for foundry_converters.actors.converter."""

import json
from pathlib import Path

import pytest
from foundry_converters.actors.converter import convert_to_foundry
from foundry_converters.actors.models import (
    ParsedActorData,
    Attack,
    DamageFormula,
    AttackSave,
    Trait,
)


@pytest.mark.unit
class TestConvertToFoundry:
    """Tests for convert_to_foundry function."""

    @pytest.mark.asyncio
    async def test_converts_basic_actor(self):
        """Should convert minimal actor to FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={
                "STR": 8, "DEX": 14, "CON": 10,
                "INT": 10, "WIS": 8, "CHA": 8
            }
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        assert result["name"] == "Goblin"
        assert result["type"] == "npc"
        assert result["system"]["abilities"]["dex"]["value"] == 14
        assert result["system"]["attributes"]["ac"]["value"] == 15
        assert spell_uuids == []

    @pytest.mark.asyncio
    async def test_converts_actor_with_attack(self):
        """Should convert actor with attack to FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            attacks=[
                Attack(
                    name="Scimitar",
                    attack_type="melee",
                    attack_bonus=4,
                    reach=5,
                    damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        assert len(result["items"]) >= 1
        weapon = result["items"][0]
        assert weapon["name"] == "Scimitar"
        assert weapon["type"] == "weapon"

    @pytest.mark.asyncio
    async def test_converts_attack_with_saving_throw(self):
        """Should convert attack with saving throw to FoundryVTT format with save activity."""
        pit_fiend = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20.0,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            attacks=[
                Attack(
                    name="Bite",
                    attack_type="melee",
                    attack_bonus=14,
                    reach=5,
                    damage=[DamageFormula(number=4, denomination=6, bonus="+8", type="piercing")],
                    attack_save=AttackSave(
                        ability="con",
                        dc=21,
                        damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
                        on_save="half"
                    )
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(pit_fiend)

        # Find the Bite weapon
        bite_weapon = next((item for item in result["items"] if item["name"] == "Bite"), None)
        assert bite_weapon is not None
        assert bite_weapon["type"] == "weapon"

        # Should have 2 activities: attack + save
        activities = bite_weapon["system"]["activities"]
        assert len(activities) == 2

        # Check for attack activity
        attack_activity = next((a for a in activities.values() if a["type"] == "attack"), None)
        assert attack_activity is not None
        assert attack_activity["attack"]["bonus"] == "14"

        # Check for save activity
        save_activity = next((a for a in activities.values() if a["type"] == "save"), None)
        assert save_activity is not None
        assert save_activity["save"]["ability"] == ["con"]
        assert save_activity["save"]["dc"]["formula"] == "21"
        assert save_activity["damage"]["onSave"] == "half"

    @pytest.mark.asyncio
    async def test_converts_attack_with_ongoing_damage(self):
        """Should convert attack with ongoing damage to FoundryVTT format with 3 activities."""
        poisonous_creature = ParsedActorData(
            source_statblock_name="Venomous Snake",
            name="Venomous Snake",
            armor_class=13,
            hit_points=11,
            challenge_rating=0.25,
            abilities={"STR": 4, "DEX": 16, "CON": 11, "INT": 1, "WIS": 10, "CHA": 3},
            attacks=[
                Attack(
                    name="Bite",
                    attack_type="melee",
                    attack_bonus=5,
                    reach=5,
                    damage=[DamageFormula(number=1, denomination=1, bonus="", type="piercing")],
                    attack_save=AttackSave(
                        ability="con",
                        dc=11,
                        damage=[DamageFormula(number=2, denomination=4, bonus="", type="poison")],
                        on_save="half",
                        ongoing_damage=[DamageFormula(number=1, denomination=4, bonus="", type="poison")],
                        duration_rounds=3
                    )
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(poisonous_creature)

        bite_weapon = next((item for item in result["items"] if item["name"] == "Bite"), None)
        assert bite_weapon is not None

        # Should have 3 activities: attack + save + ongoing damage
        activities = bite_weapon["system"]["activities"]
        assert len(activities) == 3

        # Check for ongoing damage activity
        damage_activity = next((a for a in activities.values() if a["type"] == "damage"), None)
        assert damage_activity is not None
        assert damage_activity["activation"]["type"] == "turnStart"
        assert len(damage_activity["damage"]["parts"]) == 1
        assert damage_activity["damage"]["parts"][0]["types"] == ["poison"]

    @pytest.mark.asyncio
    async def test_converts_trait_to_feat_item(self):
        """Should convert traits to feat items in FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            traits=[
                Trait(
                    name="Nimble Escape",
                    description="The goblin can take the Disengage or Hide action as a bonus action on each of its turns.",
                    activation="bonus"
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        # Find the Nimble Escape feat
        nimble_escape = next((item for item in result["items"] if item["name"] == "Nimble Escape"), None)
        assert nimble_escape is not None
        assert nimble_escape["type"] == "feat"
        assert nimble_escape["system"]["description"]["value"] == "The goblin can take the Disengage or Hide action as a bonus action on each of its turns."
        assert nimble_escape["system"]["activation"]["type"] == "bonus"

        # Should have activity for non-passive traits
        assert len(nimble_escape["system"]["activities"]) == 1

    @pytest.mark.asyncio
    async def test_converts_passive_trait_without_activity(self):
        """Passive traits should not have activities."""
        creature = ParsedActorData(
            source_statblock_name="Wolf",
            name="Wolf",
            armor_class=13,
            hit_points=11,
            challenge_rating=0.25,
            abilities={"STR": 12, "DEX": 15, "CON": 12, "INT": 3, "WIS": 12, "CHA": 6},
            traits=[
                Trait(
                    name="Pack Tactics",
                    description="The wolf has advantage on attack rolls against a creature if at least one of the wolf's allies is within 5 feet of the creature.",
                    activation="passive"
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(creature)

        pack_tactics = next((item for item in result["items"] if item["name"] == "Pack Tactics"), None)
        assert pack_tactics is not None
        assert pack_tactics["type"] == "feat"

        # Passive traits should NOT have activities
        assert len(pack_tactics["system"]["activities"]) == 0


@pytest.mark.unit
class TestConvertToFoundryWithRealData:
    """Integration tests using real fixture data."""

    @pytest.mark.asyncio
    async def test_converts_goblin_from_fixture(self):
        """Should convert goblin from real fixture file."""
        fixture_path = Path(__file__).parent.parent.parent / "foundry" / "actors" / "fixtures" / "goblin_parsed.json"
        with open(fixture_path) as f:
            goblin_data = json.load(f)

        goblin = ParsedActorData(**goblin_data)
        result, spell_uuids = await convert_to_foundry(goblin)

        # Verify basic actor structure
        assert result["name"] == "Goblin"
        assert result["type"] == "npc"

        # Verify abilities from fixture
        assert result["system"]["abilities"]["str"]["value"] == 8
        assert result["system"]["abilities"]["dex"]["value"] == 14
        assert result["system"]["abilities"]["con"]["value"] == 10

        # Verify AC and HP
        assert result["system"]["attributes"]["ac"]["value"] == 15
        assert result["system"]["attributes"]["hp"]["value"] == 7

        # Verify movement
        assert result["system"]["attributes"]["movement"]["walk"] == 30

        # Verify senses (darkvision from fixture)
        assert result["system"]["attributes"]["senses"]["darkvision"] == 60

        # Verify details
        assert result["system"]["details"]["cr"] == 0.25
        assert result["system"]["details"]["type"]["value"] == "humanoid"
        assert result["system"]["details"]["alignment"] == "neutral evil"

        # Verify skills (stealth expertise from fixture)
        assert "ste" in result["system"]["skills"]
        assert result["system"]["skills"]["ste"]["value"] == 2  # expertise

        # Verify items: 2 attacks (Scimitar, Shortbow) + 1 trait (Nimble Escape)
        assert len(result["items"]) == 3

        # Check weapons
        scimitar = next((item for item in result["items"] if item["name"] == "Scimitar"), None)
        assert scimitar is not None
        assert scimitar["type"] == "weapon"
        assert scimitar["system"]["damage"]["base"]["denomination"] == 6
        assert scimitar["system"]["damage"]["base"]["types"] == ["slashing"]

        shortbow = next((item for item in result["items"] if item["name"] == "Shortbow"), None)
        assert shortbow is not None
        assert shortbow["type"] == "weapon"
        assert shortbow["system"]["range"]["value"] == 80
        assert shortbow["system"]["range"]["long"] == 320

        # Check trait
        nimble_escape = next((item for item in result["items"] if item["name"] == "Nimble Escape"), None)
        assert nimble_escape is not None
        assert nimble_escape["type"] == "feat"

        # No spells for goblin
        assert spell_uuids == []

    @pytest.mark.asyncio
    async def test_converts_mage_from_fixture(self):
        """Should convert mage from real fixture file and collect spell UUIDs."""
        fixture_path = Path(__file__).parent.parent.parent / "foundry" / "actors" / "fixtures" / "mage_parsed.json"
        with open(fixture_path) as f:
            mage_data = json.load(f)

        mage = ParsedActorData(**mage_data)
        result, spell_uuids = await convert_to_foundry(mage)

        # Verify basic structure
        assert result["name"] == "Mage"
        assert result["type"] == "npc"
        assert result["system"]["details"]["cr"] == 6.0

        # Verify spellcasting attributes
        assert result["system"]["attributes"]["spellcasting"] == "int"
        assert result["system"]["attributes"]["spelldc"] == 14

        # Verify saving throw proficiencies
        assert result["system"]["abilities"]["int"]["proficient"] == 1
        assert result["system"]["abilities"]["wis"]["proficient"] == 1
        assert result["system"]["abilities"]["str"]["proficient"] == 0

        # Verify spell UUIDs were collected (16 spells in fixture)
        assert len(spell_uuids) == 16
        assert "Compendium.dnd5e.spells.Item.abc123" in spell_uuids  # Fire Bolt
        assert "Compendium.dnd5e.spells.Item.hij456" in spell_uuids  # Fireball
