"""Tests for foundry.actors.converter."""

import pytest
from foundry.actors.converter import (
    convert_to_foundry,
    _generate_activity_id,
    _base_activity_structure,
    _create_attack_activity,
    _create_save_activity,
    _create_ongoing_damage_activity
)
from foundry.actors.models import ParsedActorData, Attack, Trait, DamageFormula, AttackSave


class TestConverter:
    """Tests for convert_to_foundry implementation."""

    async def test_converts_basic_actor(self):
        """Should convert minimal actor to FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={
                "STR": 8,
                "DEX": 14,
                "CON": 10,
                "INT": 10,
                "WIS": 8,
                "CHA": 8
            }
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        # Check top-level structure
        assert result["name"] == "Goblin"
        assert result["type"] == "npc"
        assert "system" in result
        assert "items" in result

        # Check spell UUIDs (should be empty for basic actor)
        assert spell_uuids == []

        # Check abilities
        assert result["system"]["abilities"]["dex"]["value"] == 14
        assert result["system"]["abilities"]["str"]["value"] == 8

        # Check attributes
        assert result["system"]["attributes"]["ac"]["value"] == 15
        assert result["system"]["attributes"]["hp"]["max"] == 7

        # Check details
        assert result["system"]["details"]["cr"] == 0.25

    async def test_converts_actor_with_attacks(self):
        """Should convert attacks to weapon items with activities."""
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
        weapon = result["items"][0]

        # Check spell UUIDs (should be empty)
        assert spell_uuids == []

        # NEW v10+ structure checks
        assert "activities" in weapon["system"]
        assert len(weapon["system"]["activities"]) == 1

        # Verify attack activity
        activity = list(weapon["system"]["activities"].values())[0]
        assert activity["type"] == "attack"
        assert activity["attack"]["bonus"] == "4"
        assert activity["attack"]["flat"] == True

        # OLD v9 fields should be removed
        assert "attackBonus" not in weapon["system"]
        assert "parts" not in weapon["system"].get("damage", {})

        # NEW damage.base structure
        assert "base" in weapon["system"]["damage"]
        assert weapon["system"]["damage"]["base"]["number"] == 1
        assert weapon["system"]["damage"]["base"]["denomination"] == 6

    async def test_converts_actor_with_traits(self):
        """Should convert traits to feat items."""
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
                    description="The goblin can take the Disengage or Hide action as a bonus action.",
                    activation="bonus"
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        # Check spell UUIDs (should be empty)
        assert spell_uuids == []

        # Check items array has feat
        assert len(result["items"]) == 1
        feat = result["items"][0]
        assert feat["name"] == "Nimble Escape"
        assert feat["type"] == "feat"

        # Check activation in v10+ activities structure
        assert "activities" in feat["system"]
        assert len(feat["system"]["activities"]) == 1
        activity = list(feat["system"]["activities"].values())[0]
        assert activity["activation"]["type"] == "bonus"

    def test_importable(self):
        """Converter should be importable from foundry.actors."""
        from foundry.actors import convert_to_foundry as imported_converter

        assert imported_converter is convert_to_foundry


class TestActivityHelpers:
    """Tests for activity generation helper functions."""

    def test_generate_activity_id(self):
        """Should generate unique 16-character IDs."""
        id1 = _generate_activity_id()
        id2 = _generate_activity_id()

        assert len(id1) == 16
        assert len(id2) == 16
        assert id1 != id2  # Should be unique

    def test_base_activity_structure(self):
        """Should return dict with all required base fields."""
        base = _base_activity_structure()

        assert "activation" in base
        assert "consumption" in base
        assert "description" in base
        assert "duration" in base
        assert "effects" in base
        assert "range" in base
        assert "target" in base
        assert "uses" in base

    def test_create_attack_activity(self):
        """Should create attack-type activity."""
        attack = Attack(
            name="Longsword",
            attack_type="melee",
            attack_bonus=5,
            reach=5,
            damage=[DamageFormula(number=1, denomination=8, bonus="+3", type="slashing")]
        )

        activity = _create_attack_activity(attack, "test123")

        assert activity["type"] == "attack"
        assert activity["_id"] == "test123"
        assert activity["attack"]["bonus"] == "5"
        assert activity["attack"]["flat"] == True
        assert activity["damage"]["includeBase"] == True

    def test_create_save_activity(self):
        """Should create save-type activity."""
        save = AttackSave(
            ability="con",
            dc=13,
            damage=[DamageFormula(number=2, denomination=6, bonus="", type="poison")],
            on_save="half"
        )

        activity = _create_save_activity(save, "save456")

        assert activity["type"] == "save"
        assert activity["_id"] == "save456"
        assert activity["save"]["ability"] == ["con"]
        assert activity["save"]["dc"]["formula"] == "13"
        assert activity["damage"]["onSave"] == "half"
        assert len(activity["damage"]["parts"]) == 1
        # Check object structure (v10+)
        part = activity["damage"]["parts"][0]
        assert part["number"] == 2
        assert part["denomination"] == 6
        assert part["bonus"] == ""
        assert part["types"] == ["poison"]

    def test_create_ongoing_damage_activity(self):
        """Should create damage-type activity for ongoing effects."""
        save = AttackSave(
            ability="con",
            dc=21,
            ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")]
        )

        activity = _create_ongoing_damage_activity(save, "dmg789")

        assert activity["type"] == "damage"
        assert activity["_id"] == "dmg789"
        assert activity["activation"]["type"] == "turnStart"
        assert len(activity["damage"]["parts"]) == 1
        # Check object structure (v10+)
        part = activity["damage"]["parts"][0]
        assert part["number"] == 6
        assert part["denomination"] == 6
        assert part["bonus"] == ""
        assert part["types"] == ["poison"]


class TestWeaponActivities:
    """Tests for weapon conversion with v10+ activities structure."""

    async def test_converts_attack_with_save(self):
        """Should create weapon with attack + save activities."""
        actor = ParsedActorData(
            source_statblock_name="Test",
            name="Test",
            armor_class=15,
            hit_points=50,
            challenge_rating=2,
            abilities={"STR": 14, "DEX": 12, "CON": 13, "INT": 10, "WIS": 11, "CHA": 8},
            attacks=[
                Attack(
                    name="Poison Bite",
                    attack_type="melee",
                    attack_bonus=4,
                    reach=5,
                    damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="piercing")],
                    attack_save=AttackSave(
                        ability="con",
                        dc=13,
                        damage=[DamageFormula(number=2, denomination=6, bonus="", type="poison")],
                        on_save="half"
                    )
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(actor)
        weapon = result["items"][0]

        # Check spell UUIDs (should be empty)
        assert spell_uuids == []

        # Should have 2 activities: attack + save
        assert len(weapon["system"]["activities"]) == 2

        activities = list(weapon["system"]["activities"].values())
        assert any(a["type"] == "attack" for a in activities)
        assert any(a["type"] == "save" for a in activities)

    async def test_converts_attack_with_ongoing_damage(self):
        """Should create weapon with attack + save + ongoing damage activities."""
        pit_fiend = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
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
                        ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
                        duration_rounds=10
                    )
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(pit_fiend)
        bite = result["items"][0]

        # Check spell UUIDs (should be empty)
        assert spell_uuids == []

        # Should have 3 activities: attack + save + ongoing damage
        assert len(bite["system"]["activities"]) == 3

        activities = list(bite["system"]["activities"].values())
        assert any(a["type"] == "attack" for a in activities)
        assert any(a["type"] == "save" for a in activities)
        assert any(a["type"] == "damage" for a in activities)

        # Verify ongoing damage has correct activation
        dmg_activity = [a for a in activities if a["type"] == "damage"][0]
        assert dmg_activity["activation"]["type"] == "turnStart"


class TestIconCacheIntegration:
    """Tests for icon cache integration with converter."""

    async def test_convert_to_foundry_uses_icon_cache(self):
        """Test converter selects appropriate icons from cache."""
        from foundry.actors.converter import convert_to_foundry
        from foundry.actors.models import ParsedActorData, Attack, DamageFormula
        from foundry.icon_cache import IconCache

        # Setup mock icon cache
        icon_cache = IconCache()
        icon_cache._all_icons = [
            "icons/weapons/swords/scimitar-guard-purple.webp",
            "icons/magic/fire/explosion-fireball.webp"
        ]
        icon_cache._icons_by_category = {
            "weapons": ["icons/weapons/swords/scimitar-guard-purple.webp"],
            "magic": ["icons/magic/fire/explosion-fireball.webp"]
        }
        icon_cache._loaded = True

        # Create test actor with scimitar attack
        parsed_actor = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
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

        foundry_json, _ = await convert_to_foundry(parsed_actor, icon_cache=icon_cache, use_ai_icons=False)

        # Find scimitar item
        scimitar = next(item for item in foundry_json['items'] if item['name'] == 'Scimitar')

        assert scimitar['img'] == "icons/weapons/swords/scimitar-guard-purple.webp"
