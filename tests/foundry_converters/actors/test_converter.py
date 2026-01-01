"""Tests for foundry_converters.actors.converter."""

import pytest
from foundry_converters.actors.converter import convert_to_foundry
from foundry_converters.actors.models import ParsedActorData, Attack, DamageFormula


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
