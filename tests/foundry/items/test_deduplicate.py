"""Tests for foundry.items.deduplicate module."""

import pytest
from foundry.items.deduplicate import (
    get_source_priority,
    deduplicate_items,
    get_source_stats
)


class TestGetSourcePriority:
    """Tests for get_source_priority function."""

    def test_players_handbook_highest_priority(self):
        """Player's Handbook should have highest priority (0)."""
        uuid = "Compendium.dnd-players-handbook.spells.phbsplFireball"
        assert get_source_priority(uuid) == 0

    def test_2024_rules_second_priority(self):
        """D&D 5e 2024 rules should have second priority (1)."""
        # Test .24 suffix
        uuid1 = "Compendium.dnd5e.spells24.phbsplFireball"
        assert get_source_priority(uuid1) == 1

        # Test .items24
        uuid2 = "Compendium.dnd5e.items24.sword123"
        assert get_source_priority(uuid2) == 1

        # Test .24 anywhere
        uuid3 = "Compendium.dnd5e.equipment.24sword"
        assert get_source_priority(uuid3) == 1

    def test_srd_third_priority(self):
        """D&D 5e SRD should have third priority (2)."""
        uuid = "Compendium.dnd5e.spells.Fireball123"
        assert get_source_priority(uuid) == 2

    def test_other_sources_lowest_priority(self):
        """Other sources should have lowest priority (3)."""
        uuid = "Compendium.homebrew.spells.CustomFireball"
        assert get_source_priority(uuid) == 3

    def test_empty_uuid(self):
        """Empty UUID should return lowest priority."""
        assert get_source_priority("") == 3


class TestDeduplicateItems:
    """Tests for deduplicate_items function."""

    def test_no_duplicates(self):
        """Items with unique names should all be kept."""
        items = [
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells.1"},
            {"name": "Lightning Bolt", "uuid": "Compendium.dnd5e.spells.2"},
            {"name": "Magic Missile", "uuid": "Compendium.dnd5e.spells.3"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 3

    def test_duplicates_phb_wins(self):
        """Player's Handbook version should be kept over SRD."""
        items = [
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells.srd123"},
            {"name": "Fireball", "uuid": "Compendium.dnd-players-handbook.spells.phb123"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 1
        assert "dnd-players-handbook" in result[0]["uuid"]

    def test_duplicates_2024_wins_over_srd(self):
        """2024 rules should be kept over classic SRD."""
        items = [
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells.srd123"},
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells24.new123"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 1
        assert "spells24" in result[0]["uuid"]

    def test_multiple_duplicates(self):
        """Should keep highest priority among multiple duplicates."""
        items = [
            {"name": "Fireball", "uuid": "Compendium.homebrew.spells.custom"},
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells.srd123"},
            {"name": "Fireball", "uuid": "Compendium.dnd-players-handbook.spells.phb123"},
            {"name": "Fireball", "uuid": "Compendium.dnd5e.spells24.new123"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 1
        assert "dnd-players-handbook" in result[0]["uuid"]

    def test_sorted_output(self):
        """Output should be sorted by dedupe_key."""
        items = [
            {"name": "Zebra Spell", "uuid": "Compendium.dnd5e.spells.1"},
            {"name": "Apple Spell", "uuid": "Compendium.dnd5e.spells.2"},
            {"name": "Monkey Spell", "uuid": "Compendium.dnd5e.spells.3"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert result[0]["name"] == "Apple Spell"
        assert result[1]["name"] == "Monkey Spell"
        assert result[2]["name"] == "Zebra Spell"

    def test_custom_dedupe_key(self):
        """Should support custom deduplication key."""
        items = [
            {"id": "123", "name": "Spell A", "uuid": "Compendium.dnd5e.spells.1"},
            {"id": "123", "name": "Spell A", "uuid": "Compendium.dnd-players-handbook.spells.2"},
        ]
        result = deduplicate_items(items, dedupe_key="id", verbose=False)
        assert len(result) == 1

    def test_empty_items(self):
        """Empty list should return empty list."""
        result = deduplicate_items([], verbose=False)
        assert result == []

    def test_items_without_dedupe_key(self):
        """Items without dedupe_key should be filtered out."""
        items = [
            {"name": "Valid Spell", "uuid": "Compendium.dnd5e.spells.1"},
            {"uuid": "Compendium.dnd5e.spells.2"},  # No name
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 1
        assert result[0]["name"] == "Valid Spell"

    def test_whitespace_handling(self):
        """Names with different whitespace should be treated as same."""
        items = [
            {"name": "  Fireball  ", "uuid": "Compendium.dnd5e.spells.1"},
            {"name": "Fireball", "uuid": "Compendium.dnd-players-handbook.spells.2"},
        ]
        result = deduplicate_items(items, verbose=False)
        assert len(result) == 1


class TestGetSourceStats:
    """Tests for get_source_stats function."""

    def test_single_source(self):
        """Should count items from single source."""
        items = [
            {"uuid": "Compendium.dnd-players-handbook.spells.1"},
            {"uuid": "Compendium.dnd-players-handbook.spells.2"},
            {"uuid": "Compendium.dnd-players-handbook.spells.3"},
        ]
        stats = get_source_stats(items)
        assert stats["Player's Handbook"] == 3

    def test_multiple_sources(self):
        """Should count items from multiple sources."""
        items = [
            {"uuid": "Compendium.dnd-players-handbook.spells.1"},
            {"uuid": "Compendium.dnd-players-handbook.spells.2"},
            {"uuid": "Compendium.dnd5e.spells.3"},
            {"uuid": "Compendium.dnd5e.spells24.4"},
            {"uuid": "Compendium.homebrew.spells.5"},
        ]
        stats = get_source_stats(items)
        assert stats["Player's Handbook"] == 2
        assert stats["D&D 5e SRD"] == 1
        assert stats["D&D 5e 2024"] == 1
        assert stats["Other"] == 1

    def test_2024_detection(self):
        """Should correctly detect 2024 rules items."""
        items = [
            {"uuid": "Compendium.dnd5e.spells24.abc"},
            {"uuid": "Compendium.dnd5e.items24.def"},
            {"uuid": "Compendium.dnd5e.equipment.24ghi"},
        ]
        stats = get_source_stats(items)
        assert stats["D&D 5e 2024"] == 3

    def test_empty_items(self):
        """Empty list should return empty dict."""
        stats = get_source_stats([])
        assert stats == {}

    def test_items_without_uuid(self):
        """Items without UUID should be counted as Other."""
        items = [
            {"name": "Test Item"},
            {"uuid": ""},
        ]
        stats = get_source_stats(items)
        assert stats.get("Other", 0) == 2
