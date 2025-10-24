"""Tests for stat block parsing with Gemini."""

import pytest
from pathlib import Path
from actors.parse_stat_blocks import parse_stat_block_with_gemini
from actors.models import StatBlock


@pytest.mark.integration
@pytest.mark.requires_api
class TestStatBlockParsing:
    """Test stat block parsing with real Gemini API calls."""

    def test_parse_goblin_stat_block(self, check_api_key):
        """Test parsing a complete goblin stat block."""
        # Load sample stat block
        fixture_path = Path(__file__).parent / "fixtures" / "sample_stat_block.txt"
        with open(fixture_path, 'r') as f:
            raw_text = f.read()

        # Parse with Gemini
        stat_block = parse_stat_block_with_gemini(raw_text)

        # Verify structured data
        assert isinstance(stat_block, StatBlock)
        assert stat_block.name.upper() == "GOBLIN"  # Case may vary
        assert stat_block.armor_class == 15
        assert stat_block.hit_points == 7
        assert stat_block.challenge_rating == 0.25
        assert stat_block.size == "Small"
        assert "humanoid" in stat_block.type.lower()  # May include subtype
        assert stat_block.raw_text == raw_text

        # Verify abilities parsed
        assert stat_block.abilities is not None
        assert stat_block.abilities["STR"] == 8
        assert stat_block.abilities["DEX"] == 14


@pytest.mark.unit
class TestStatBlockParsingUnit:
    """Unit tests for stat block parsing (mocked)."""

    def test_parse_returns_stat_block_model(self):
        """Test parser returns StatBlock model (integration test required for full test)."""
        # This is a placeholder - real testing requires API
        # Just verify the function exists and has correct signature
        from actors.parse_stat_blocks import parse_stat_block_with_gemini
        import inspect

        sig = inspect.signature(parse_stat_block_with_gemini)
        assert 'raw_text' in sig.parameters
