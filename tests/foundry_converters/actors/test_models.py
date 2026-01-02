"""Tests for foundry_converters.actors.models."""

import pytest
from foundry_converters.actors.models import (
    ParsedActorData,
    Attack,
    DamageFormula,
    Trait,
)


@pytest.mark.unit
class TestParsedActorData:
    """Tests for ParsedActorData model."""

    def test_creates_minimal_actor(self):
        """Should create actor with minimal required fields."""
        actor = ParsedActorData(
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

        assert actor.name == "Goblin"
        assert actor.armor_class == 15
        assert actor.abilities["DEX"] == 14


@pytest.mark.unit
class TestAttack:
    """Tests for Attack model."""

    def test_creates_melee_attack(self):
        """Should create melee attack with damage."""
        attack = Attack(
            name="Scimitar",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
        )

        assert attack.name == "Scimitar"
        assert attack.attack_type == "melee"
        assert attack.damage[0].denomination == 6


@pytest.mark.unit
class TestDamageFormula:
    """Tests for DamageFormula model."""

    def test_creates_damage_formula(self):
        """Should create damage formula."""
        formula = DamageFormula(number=2, denomination=6, bonus="+3", type="fire")

        assert formula.number == 2
        assert formula.denomination == 6
        assert formula.bonus == "+3"
        assert formula.type == "fire"


@pytest.mark.unit
class TestTrait:
    """Tests for Trait model."""

    def test_creates_trait(self):
        """Should create trait with name and description."""
        trait = Trait(name="Darkvision", description="Can see in dim light within 60 feet.")

        assert trait.name == "Darkvision"
        assert trait.description == "Can see in dim light within 60 feet."
