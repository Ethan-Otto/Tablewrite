"""Tests for multiattack parsing."""

import pytest
from foundry.actors.models import ParsedActorData, Multiattack
from foundry.actors.converter import convert_to_foundry


class TestMultiattackModel:
    """Tests for Multiattack model."""

    def test_basic_multiattack(self):
        """Should create basic multiattack."""
        multiattack = Multiattack(
            name="Multiattack",
            description="The pit fiend makes four attacks: one with its bite, one with its claw, one with its mace, and one with its tail.",
            num_attacks=4
        )

        assert multiattack.name == "Multiattack"
        assert multiattack.num_attacks == 4
        assert "four attacks" in multiattack.description

    def test_multiattack_with_options(self):
        """Should handle multiattack with options."""
        multiattack = Multiattack(
            name="Multiattack",
            description="The dragon can use its Frightful Presence. It then makes three attacks: one with its bite and two with its claws.",
            num_attacks=3
        )

        assert multiattack.num_attacks == 3

    def test_parsed_actor_with_multiattack(self):
        """Should include multiattack in ParsedActorData."""
        actor = ParsedActorData(
            source_statblock_name="Pit Fiend",
            name="Pit Fiend",
            armor_class=19,
            hit_points=300,
            challenge_rating=20,
            abilities={"STR": 26, "DEX": 14, "CON": 24, "INT": 22, "WIS": 18, "CHA": 24},
            multiattack=Multiattack(
                name="Multiattack",
                description="Makes four attacks.",
                num_attacks=4
            )
        )

        assert actor.multiattack is not None
        assert actor.multiattack.num_attacks == 4


class TestMultiattackConversion:
    """Tests for converting multiattack to FoundryVTT format."""

    async def test_converts_multiattack_to_feat(self):
        """Should convert multiattack to feat item."""
        actor = ParsedActorData(
            source_statblock_name="Test",
            name="Test Creature",
            armor_class=15,
            hit_points=100,
            challenge_rating=5,
            abilities={"STR": 18, "DEX": 14, "CON": 16, "INT": 10, "WIS": 12, "CHA": 10},
            multiattack=Multiattack(
                name="Multiattack",
                description="The creature makes two attacks: one with its bite and one with its claws.",
                num_attacks=2
            )
        )

        result, spell_uuids = await convert_to_foundry(actor)

        # Check spell UUIDs (should be empty)
        assert spell_uuids == []

        # Should have multiattack feat in items
        feats = [item for item in result["items"] if item["type"] == "feat"]
        multiattack_feat = next((f for f in feats if f["name"] == "Multiattack"), None)

        assert multiattack_feat is not None
        assert multiattack_feat["system"]["activation"]["type"] == "action"
        assert "two attacks" in multiattack_feat["system"]["description"]["value"]
