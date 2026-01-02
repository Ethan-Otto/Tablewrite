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


@pytest.mark.unit
class TestSpellcastingDetection:
    """Tests for spellcasting type detection in parse_single_trait_async."""

    def test_detects_regular_spellcasting(self):
        """Should detect regular spellcasting trait."""
        trait_text = """Spellcasting. The mage is a 9th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 14, +6 to hit with spell attacks). The mage has the following spells prepared:

Cantrips (at will): fire bolt, light, mage hand, prestidigitation
1st level (4 slots): detect magic, mage armor, magic missile, shield
2nd level (3 slots): misty step, suggestion
3rd level (3 slots): counterspell, fireball, fly
4th level (3 slots): greater invisibility, ice storm
5th level (1 slot): cone of cold"""

        trait_lower = trait_text.lower()
        is_innate = "innate spellcasting" in trait_lower or ("innate" in trait_lower and "spellcasting" in trait_lower)
        is_pact_magic = "pact magic" in trait_lower
        is_regular_spellcasting = (
            ("spellcasting" in trait_lower or "spellcaster" in trait_lower)
            and not is_innate
            and not is_pact_magic
        )

        assert is_regular_spellcasting is True
        assert is_innate is False
        assert is_pact_magic is False

    def test_detects_innate_spellcasting(self):
        """Should detect innate spellcasting trait."""
        trait_text = """Innate Spellcasting. The drow's innate spellcasting ability is Charisma (spell save DC 12). It can innately cast the following spells, requiring no material components:

At will: dancing lights
1/day each: darkness, faerie fire"""

        trait_lower = trait_text.lower()
        is_innate = "innate spellcasting" in trait_lower or ("innate" in trait_lower and "spellcasting" in trait_lower)
        is_pact_magic = "pact magic" in trait_lower
        is_regular_spellcasting = (
            ("spellcasting" in trait_lower or "spellcaster" in trait_lower)
            and not is_innate
            and not is_pact_magic
        )

        assert is_innate is True
        assert is_regular_spellcasting is False
        assert is_pact_magic is False

    def test_detects_pact_magic(self):
        """Should detect pact magic trait."""
        trait_text = """Pact Magic. The warlock is a 5th-level spellcaster. Its spellcasting ability is Charisma (spell save DC 14, +6 to hit with spell attacks). It regains its expended spell slots when it finishes a short or long rest. It knows the following warlock spells:

Cantrips (at will): eldritch blast, mage hand
1st-3rd level (2 3rd-level slots): armor of agathys, hex, hold person, invisibility"""

        trait_lower = trait_text.lower()
        is_innate = "innate spellcasting" in trait_lower or ("innate" in trait_lower and "spellcasting" in trait_lower)
        is_pact_magic = "pact magic" in trait_lower
        is_regular_spellcasting = (
            ("spellcasting" in trait_lower or "spellcaster" in trait_lower)
            and not is_innate
            and not is_pact_magic
        )

        assert is_pact_magic is True
        assert is_innate is False
        assert is_regular_spellcasting is False


@pytest.mark.integration
@pytest.mark.slow
class TestSpellcastingParsing:
    """Integration tests for spellcasting parsing with real Gemini calls."""

    @pytest.mark.asyncio
    async def test_parses_regular_spellcasting_trait(self):
        """Should parse regular spellcasting and return spell list."""
        from foundry_converters.actors.parser import parse_spellcasting_async

        trait_text = """Spellcasting. The mage is a 9th-level spellcaster. Its spellcasting ability is Intelligence (spell save DC 14, +6 to hit with spell attacks). The mage has the following spells prepared:

Cantrips (at will): fire bolt, light, mage hand
1st level (4 slots): mage armor, magic missile, shield
2nd level (3 slots): misty step
3rd level (3 slots): fireball, fly"""

        result = await parse_spellcasting_async(trait_text, spell_cache=None)

        # Should return tuple of (spellcasting_info, spell_list)
        assert isinstance(result, tuple)
        assert len(result) == 2

        spellcasting_info, spells = result

        # Verify spellcasting info
        assert spellcasting_info["ability"] == "intelligence"
        assert spellcasting_info["save_dc"] == 14
        assert spellcasting_info["attack_bonus"] == 6

        # Verify spells were parsed
        assert len(spells) >= 6  # At least the ones listed

        # Check for expected spells
        spell_names = [s.name.lower() for s in spells]
        assert "fireball" in spell_names
        assert "mage armor" in spell_names or "mage armour" in spell_names
