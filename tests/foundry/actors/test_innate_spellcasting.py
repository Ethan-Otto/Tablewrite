"""Tests for innate spellcasting."""

import pytest
from foundry.actors.models import ParsedActorData, InnateSpellcasting, InnateSpell


class TestInnateSpellcastingModel:
    """Tests for innate spellcasting models."""

    def test_innate_spell(self):
        """Should create innate spell."""
        spell = InnateSpell(
            name="Fireball",
            frequency="at will"
        )

        assert spell.name == "Fireball"
        assert spell.frequency == "at will"
        assert spell.uses is None

    def test_innate_spell_with_uses(self):
        """Should handle limited-use spells."""
        spell = InnateSpell(
            name="Hold Monster",
            frequency="3/day",
            uses=3
        )

        assert spell.frequency == "3/day"
        assert spell.uses == 3

    def test_innate_spellcasting(self):
        """Should group spells by frequency."""
        innate = InnateSpellcasting(
            ability="charisma",
            save_dc=21,
            spells=[
                InnateSpell(name="Detect Magic", frequency="at will"),
                InnateSpell(name="Fireball", frequency="at will"),
                InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                InnateSpell(name="Wall of Fire", frequency="3/day", uses=3),
            ]
        )

        assert innate.ability == "charisma"
        assert innate.save_dc == 21
        assert len(innate.spells) == 4

    def test_parsed_actor_with_innate_spellcasting(self):
        """Should include innate spellcasting in ParsedActorData."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            innate_spellcasting=InnateSpellcasting(
                ability="charisma",
                save_dc=21,
                spells=[
                    InnateSpell(name="Fireball", frequency="at will"),
                ]
            )
        )

        assert actor.innate_spellcasting is not None
        assert len(actor.innate_spellcasting.spells) == 1
