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

    def test_converts_basic_actor(self):
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

        result = convert_to_foundry(goblin)

        # Check top-level structure
        assert result["name"] == "Goblin"
        assert result["type"] == "npc"
        assert "system" in result
        assert "items" in result

        # Check abilities
        assert result["system"]["abilities"]["dex"]["value"] == 14
        assert result["system"]["abilities"]["str"]["value"] == 8

        # Check attributes
        assert result["system"]["attributes"]["ac"]["value"] == 15
        assert result["system"]["attributes"]["hp"]["max"] == 7

        # Check details
        assert result["system"]["details"]["cr"] == 0.25

    def test_converts_actor_with_attacks(self):
        """Should convert attacks to weapon items."""
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

        result = convert_to_foundry(goblin)

        # Check items array has weapon
        assert len(result["items"]) == 1
        weapon = result["items"][0]
        assert weapon["name"] == "Scimitar"
        assert weapon["type"] == "weapon"
        assert weapon["system"]["attackBonus"] == "4"
        assert weapon["system"]["actionType"] == "melee"

    def test_converts_actor_with_traits(self):
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

        result = convert_to_foundry(goblin)

        # Check items array has feat
        assert len(result["items"]) == 1
        feat = result["items"][0]
        assert feat["name"] == "Nimble Escape"
        assert feat["type"] == "feat"
        assert feat["system"]["activation"]["type"] == "bonus"

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
        assert activity["damage"]["parts"][0] == ["2d6", "poison"]

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
        assert activity["damage"]["parts"][0] == ["6d6", "poison"]
