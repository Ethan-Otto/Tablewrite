"""Tests for foundry.actors.models."""

import pytest
from foundry.actors.models import (
    DamageFormula, Attack, Trait, Spell, SkillProficiency,
    DamageModification, ParsedActorData
)


class TestDamageFormula:
    """Tests for DamageFormula model."""

    def test_basic_creation(self):
        """Should create damage formula with required fields."""
        formula = DamageFormula(
            number=1,
            denomination=6,
            bonus="+2",
            type="piercing"
        )

        assert formula.number == 1
        assert formula.denomination == 6
        assert formula.bonus == "+2"
        assert formula.type == "piercing"

    def test_immutable(self):
        """Should be immutable (frozen)."""
        formula = DamageFormula(number=1, denomination=6, type="slashing")

        with pytest.raises(Exception):  # Pydantic raises ValidationError
            formula.number = 2


class TestAttack:
    """Tests for Attack model."""

    def test_melee_attack(self):
        """Should create melee attack."""
        attack = Attack(
            name="Scimitar",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[
                DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")
            ]
        )

        assert attack.name == "Scimitar"
        assert attack.attack_type == "melee"
        assert attack.reach == 5
        assert len(attack.damage) == 1

    def test_ranged_attack(self):
        """Should create ranged attack."""
        attack = Attack(
            name="Shortbow",
            attack_type="ranged",
            attack_bonus=4,
            range_short=80,
            range_long=320,
            damage=[
                DamageFormula(number=1, denomination=6, bonus="+2", type="piercing")
            ]
        )

        assert attack.range_short == 80
        assert attack.range_long == 320


class TestParsedActorData:
    """Tests for ParsedActorData model."""

    def test_minimal_goblin(self):
        """Should create minimal goblin data."""
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

        assert goblin.name == "Goblin"
        assert goblin.armor_class == 15
        assert goblin.abilities["DEX"] == 14

    def test_with_attacks_and_traits(self):
        """Should create goblin with attacks and traits."""
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
            ],
            traits=[
                Trait(
                    name="Nimble Escape",
                    description="The goblin can take the Disengage or Hide action as a bonus action.",
                    activation="bonus"
                )
            ]
        )

        assert len(goblin.attacks) == 1
        assert len(goblin.traits) == 1
        assert goblin.traits[0].activation == "bonus"
