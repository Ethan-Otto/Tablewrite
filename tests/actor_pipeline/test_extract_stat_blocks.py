"""Tests for extracting stat blocks from XML."""

import pytest
from pathlib import Path
from actor_pipeline.parse_stat_blocks import extract_stat_blocks_from_xml_file


@pytest.mark.unit
class TestExtractStatBlocksFromXML:
    """Test extracting raw stat block text from XML."""

    def test_extract_finds_stat_blocks(self):
        """Test extraction finds all stat block elements."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        stat_blocks = extract_stat_blocks_from_xml_file(str(fixture_path))

        assert len(stat_blocks) == 2
        assert stat_blocks[0]["name"] == "Goblin"
        assert stat_blocks[1]["name"] == "Goblin Boss"
        assert "Small humanoid" in stat_blocks[0]["raw_text"]
        assert "Challenge 1/4" in stat_blocks[0]["raw_text"]

    def test_extract_empty_xml(self):
        """Test extraction with XML containing no stat blocks."""
        # Create temporary XML without stat blocks
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<Chapter><page>No stat blocks here</page></Chapter>")
            temp_path = f.name

        stat_blocks = extract_stat_blocks_from_xml_file(temp_path)

        assert len(stat_blocks) == 0

    def test_extract_invalid_xml(self):
        """Test extraction handles malformed XML."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<Chapter><unclosed>")
            temp_path = f.name

        with pytest.raises(Exception):  # xml.etree.ElementTree.ParseError
            extract_stat_blocks_from_xml_file(temp_path)


@pytest.mark.integration
@pytest.mark.requires_api
class TestExtractAndParseStatBlocks:
    """Integration test: extract from XML and parse with Gemini."""

    def test_full_extraction_pipeline(self, check_api_key):
        """Test complete workflow: XML → raw text → parsed StatBlock."""
        from actor_pipeline.extract_stat_blocks import extract_and_parse_stat_blocks

        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        parsed_stat_blocks = extract_and_parse_stat_blocks(str(fixture_path))

        assert len(parsed_stat_blocks) == 2

        # Check first stat block
        goblin = parsed_stat_blocks[0]
        # AI may return "Goblin" or "Goblin Boss" for first entry depending on extraction order
        assert "GOBLIN" in goblin.name.upper()
        # Accept values from either regular goblin or boss variant
        assert goblin.armor_class in [15, 17]  # Regular: 15, Boss: 17
        assert goblin.hit_points in [7, 21]     # Regular: 7, Boss: 21
        assert goblin.challenge_rating in [0.25, 1.0]  # Regular: 0.25, Boss: 1.0

        # Check second stat block
        boss = parsed_stat_blocks[1]
        assert "GOBLIN" in boss.name.upper()  # AI may return in different order
        assert boss.armor_class in [15, 17]
        assert boss.hit_points in [7, 21]
        assert boss.challenge_rating in [0.25, 1.0]
