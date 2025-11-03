"""Tests for test fixtures."""

import json
import pytest
from pathlib import Path
from foundry.actors.models import ParsedActorData


class TestFixtures:
    """Tests to verify fixture files are valid."""

    @pytest.fixture
    def fixtures_dir(self):
        """Get path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_goblin_fixture_valid(self, fixtures_dir):
        """Goblin fixture should be valid ParsedActorData."""
        fixture_path = fixtures_dir / "goblin_parsed.json"

        with open(fixture_path) as f:
            data = json.load(f)

        # Should parse without errors
        goblin = ParsedActorData(**data)

        # Verify key fields
        assert goblin.name == "Goblin"
        assert goblin.armor_class == 15
        assert goblin.hit_points == 7
        assert goblin.challenge_rating == 0.25
        assert len(goblin.attacks) == 2
        assert len(goblin.traits) == 1
        assert goblin.traits[0].name == "Nimble Escape"

    def test_mage_fixture_valid(self, fixtures_dir):
        """Mage fixture should be valid ParsedActorData."""
        fixture_path = fixtures_dir / "mage_parsed.json"

        with open(fixture_path) as f:
            data = json.load(f)

        # Should parse without errors
        mage = ParsedActorData(**data)

        # Verify key fields
        assert mage.name == "Mage"
        assert mage.armor_class == 12
        assert mage.hit_points == 40
        assert mage.challenge_rating == 6.0
        assert len(mage.attacks) == 1
        assert len(mage.spells) == 16  # Cantrips through 5th level
        assert mage.spellcasting_ability == "int"
        assert mage.spell_save_dc == 14
        assert mage.spell_attack_bonus == 6

    def test_goblin_attacks_structure(self, fixtures_dir):
        """Goblin attacks should have correct structure."""
        fixture_path = fixtures_dir / "goblin_parsed.json"

        with open(fixture_path) as f:
            data = json.load(f)

        goblin = ParsedActorData(**data)

        # Scimitar (melee)
        scimitar = goblin.attacks[0]
        assert scimitar.name == "Scimitar"
        assert scimitar.attack_type == "melee"
        assert scimitar.attack_bonus == 4
        assert scimitar.reach == 5
        assert len(scimitar.damage) == 1
        assert scimitar.damage[0].number == 1
        assert scimitar.damage[0].denomination == 6
        assert scimitar.damage[0].bonus == "+2"
        assert scimitar.damage[0].type == "slashing"

        # Shortbow (ranged)
        shortbow = goblin.attacks[1]
        assert shortbow.name == "Shortbow"
        assert shortbow.attack_type == "ranged"
        assert shortbow.range_short == 80
        assert shortbow.range_long == 320

    def test_mage_spells_structure(self, fixtures_dir):
        """Mage spells should have correct structure."""
        fixture_path = fixtures_dir / "mage_parsed.json"

        with open(fixture_path) as f:
            data = json.load(f)

        mage = ParsedActorData(**data)

        # Check spell levels
        cantrips = [s for s in mage.spells if s.level == 0]
        assert len(cantrips) == 4

        # Check UUIDs are present
        for spell in mage.spells:
            assert spell.uuid is not None
            assert spell.uuid.startswith("Compendium.")

        # Check specific spell
        fireball = next(s for s in mage.spells if s.name == "Fireball")
        assert fireball.level == 3
        assert fireball.school == "evo"
