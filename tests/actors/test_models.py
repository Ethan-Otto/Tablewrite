"""Tests for actor Pydantic models."""

import pytest
from pydantic import ValidationError
from src.actors.models import StatBlock, NPC


@pytest.mark.unit
class TestStatBlockModel:
    """Test StatBlock Pydantic model."""

    def test_stat_block_valid_minimal(self):
        """Test StatBlock with minimal required fields."""
        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block text...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )
        assert stat_block.name == "Goblin"
        assert stat_block.armor_class == 15
        assert stat_block.hit_points == 7
        assert stat_block.challenge_rating == 0.25
        assert stat_block.raw_text == "Goblin stat block text..."

    def test_stat_block_valid_complete(self):
        """Test StatBlock with all optional fields."""
        stat_block = StatBlock(
            name="Goblin Boss",
            raw_text="Goblin Boss stat block...",
            armor_class=17,
            hit_points=21,
            challenge_rating=1.0,
            size="Small",
            type="humanoid",
            alignment="neutral evil",
            abilities={"STR": 10, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 10},
            speed="30 ft.",
            senses="darkvision 60 ft.",
            languages="Common, Goblin"
        )
        assert stat_block.size == "Small"
        assert stat_block.type == "humanoid"
        assert stat_block.abilities["DEX"] == 14

    def test_stat_block_invalid_ac(self):
        """Test StatBlock rejects invalid armor class."""
        with pytest.raises(ValidationError):
            StatBlock(
                name="Invalid",
                raw_text="text",
                armor_class=50,  # Too high
                hit_points=10,
                challenge_rating=1.0
            )

    def test_stat_block_missing_required(self):
        """Test StatBlock requires all required fields."""
        with pytest.raises(ValidationError):
            StatBlock(
                name="Missing Fields",
                raw_text="text"
                # Missing AC, HP, CR
            )


@pytest.mark.unit
class TestNPCModel:
    """Test NPC Pydantic model."""

    def test_npc_valid_minimal(self):
        """Test NPC with minimal required fields."""
        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader of the Cragmaw goblins",
            plot_relevance="Guards the stolen supplies"
        )
        assert npc.name == "Klarg"
        assert npc.creature_stat_block_name == "Goblin Boss"
        assert npc.location is None

    def test_npc_valid_complete(self):
        """Test NPC with all optional fields."""
        npc = NPC(
            name="Sildar Hallwinter",
            creature_stat_block_name="Human Fighter",
            description="Member of the Lords' Alliance",
            plot_relevance="Captured by goblins, needs rescue",
            location="Cragmaw Hideout",
            first_appearance_section="Chapter 1 → Goblin Ambush"
        )
        assert npc.location == "Cragmaw Hideout"
        assert npc.first_appearance_section == "Chapter 1 → Goblin Ambush"

    def test_npc_missing_required(self):
        """Test NPC requires all required fields."""
        with pytest.raises(ValidationError):
            NPC(
                name="Incomplete",
                description="Missing creature type"
                # Missing creature_stat_block_name and plot_relevance
            )
