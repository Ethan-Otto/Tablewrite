"""Tests for foundry_converters.actors.parser."""

import json
import pytest
from pathlib import Path


@pytest.mark.unit
class TestParseSenses:
    """Tests for parse_senses helper function."""

    def test_parses_darkvision(self):
        """Should parse darkvision from senses string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("Darkvision 60 ft., Passive Perception 14")
        assert result["darkvision"] == 60

    def test_parses_passive_perception(self):
        """Should parse passive perception from senses string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("Darkvision 60 ft., Passive Perception 14")
        assert result["passive_perception"] == 14

    def test_handles_none(self):
        """Should return empty dict for None input."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses(None)
        assert result == {}

    def test_parses_blindsight(self):
        """Should parse blindsight from senses string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("Blindsight 30 ft., Darkvision 60 ft., Passive Perception 18")
        assert result["blindsight"] == 30
        assert result["darkvision"] == 60
        assert result["passive_perception"] == 18

    def test_parses_tremorsense(self):
        """Should parse tremorsense from senses string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("Tremorsense 60 ft., Passive Perception 10")
        assert result["tremorsense"] == 60

    def test_parses_truesight(self):
        """Should parse truesight from senses string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("Truesight 120 ft., Passive Perception 22")
        assert result["truesight"] == 120

    def test_handles_empty_string(self):
        """Should return empty dict for empty string."""
        from foundry_converters.actors.parser import parse_senses

        result = parse_senses("")
        assert result == {}


@pytest.mark.unit
class TestParserIntegration:
    """Integration tests with real fixture data."""

    def test_parse_senses_from_real_goblin_data(self):
        """Test parse_senses matches real goblin fixture data.

        Uses real goblin_parsed.json fixture to verify senses parsing
        produces expected values.
        """
        from foundry_converters.actors.parser import parse_senses

        # Load real fixture data
        fixtures_dir = Path(__file__).parent.parent.parent / "foundry" / "actors" / "fixtures"
        goblin_file = fixtures_dir / "goblin_parsed.json"

        with open(goblin_file) as f:
            goblin_data = json.load(f)

        # Goblin has darkvision 60 and passive_perception 9
        # Construct a senses string that would produce these values
        senses_str = f"Darkvision {goblin_data['darkvision']} ft., Passive Perception {goblin_data['passive_perception']}"

        result = parse_senses(senses_str)

        assert result["darkvision"] == goblin_data["darkvision"]
        assert result["passive_perception"] == goblin_data["passive_perception"]
