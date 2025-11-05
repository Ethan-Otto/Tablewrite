"""Tests for innate spellcasting."""

import pytest
from foundry.actors.models import ParsedActorData, InnateSpellcasting, InnateSpell
from foundry.actors.converter import convert_to_foundry


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


class TestInnateSpellcastingConversion:
    """Tests for converting innate spellcasting to FoundryVTT format."""

    async def test_converts_innate_spellcasting_to_feat(self):
        """Should create Innate Spellcasting feat."""
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
                    InnateSpell(name="Detect Magic", frequency="at will"),
                    InnateSpell(name="Fireball", frequency="at will"),
                ]
            )
        )

        result, spell_uuids = await convert_to_foundry(actor)

        # Should have Innate Spellcasting feat
        feats = [item for item in result["items"] if item["type"] == "feat"]
        innate_feat = next((f for f in feats if "Innate Spellcasting" in f["name"]), None)

        assert innate_feat is not None
        assert "charisma" in innate_feat["system"]["description"]["value"].lower()

    async def test_converts_innate_spells_to_spell_items(self):
        """Should create spell items for innate spells."""
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
                    InnateSpell(name="Hold Monster", frequency="3/day", uses=3),
                ]
            )
        )

        result, spell_uuids = await convert_to_foundry(actor, include_spells_in_payload=True)

        # Should have spell items in payload
        spells = [item for item in result["items"] if item["type"] == "spell"]

        assert len(spells) >= 2

        fireball = next((s for s in spells if s["name"] == "Fireball"), None)
        hold_monster = next((s for s in spells if s["name"] == "Hold Monster"), None)

        assert fireball is not None
        assert hold_monster is not None

        # Limited-use spell should have uses
        assert hold_monster["system"]["uses"]["max"] == 3

    @pytest.mark.integration
    @pytest.mark.requires_foundry
    @pytest.mark.asyncio
    async def test_looks_up_spell_uuids_from_cache(self):
        """Should use SpellCache to get proper spell UUIDs."""
        from foundry.actors.spell_cache import SpellCache
        from dotenv import load_dotenv
        import os

        load_dotenv()

        # Skip if FoundryVTT not available
        if not os.getenv("FOUNDRY_RELAY_URL"):
            pytest.skip("FoundryVTT not configured")

        spell_cache = SpellCache()
        spell_cache.load()

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

        # Convert with spell cache
        result, spell_uuids = await convert_to_foundry(actor, spell_cache=spell_cache)

        # NEW behavior: spells NOT in payload, returned as UUIDs
        spells = [item for item in result["items"] if item["type"] == "spell"]
        assert len(spells) == 0, "Spells should NOT be in payload by default"

        # Check spell UUIDs returned separately
        assert len(spell_uuids) == 1
        fireball_uuid = spell_uuids[0]
        assert fireball_uuid.startswith("Compendium.")

        # Also test backward compatibility with include_spells_in_payload=True
        result_compat, _ = await convert_to_foundry(actor, spell_cache=spell_cache, include_spells_in_payload=True)
        spells_compat = [item for item in result_compat["items"] if item["type"] == "spell"]
        fireball = next((s for s in spells_compat if s["name"] == "Fireball"), None)

        assert fireball is not None
        # Should have proper level (Fireball is 3rd level)
        assert fireball["system"]["level"] == 3
