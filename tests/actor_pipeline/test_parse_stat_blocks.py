"""Tests for stat block parsing with Gemini."""

import pytest
from pathlib import Path
from actor_pipeline.parse_stat_blocks import (
    parse_stat_block_with_gemini,
    extract_stat_blocks_from_document,
    extract_stat_blocks_from_xml_file
)
from actor_pipeline.models import StatBlock
from models import XMLDocument


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
        from actor_pipeline.parse_stat_blocks import parse_stat_block_with_gemini
        import inspect

        sig = inspect.signature(parse_stat_block_with_gemini)
        assert 'raw_text' in sig.parameters


@pytest.mark.unit
class TestStatBlockExtractionFromXMLDocument:
    """Unit tests for extracting stat blocks from XMLDocument objects."""

    def test_extract_stat_blocks_from_document(self):
        """Test extracting stat blocks from XMLDocument."""
        # Load fixture
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"
        with open(fixture_path, 'r') as f:
            xml_string = f.read()

        # Parse to XMLDocument
        doc = XMLDocument.from_xml(xml_string)

        # Extract stat blocks
        stat_blocks = extract_stat_blocks_from_document(doc)

        # Verify extraction
        assert len(stat_blocks) == 2
        assert stat_blocks[0]["name"] == "Goblin"
        assert "GOBLIN" in stat_blocks[0]["raw_text"]
        assert "Small humanoid" in stat_blocks[0]["raw_text"]

        assert stat_blocks[1]["name"] == "Goblin Boss"
        assert "GOBLIN BOSS" in stat_blocks[1]["raw_text"]
        assert "chain shirt" in stat_blocks[1]["raw_text"]

    def test_extract_stat_blocks_from_document_empty(self):
        """Test extracting stat blocks from document with no stat blocks."""
        xml_string = """<Chapter>
            <page number="1">
                <section>Introduction</section>
                <p>No stat blocks here.</p>
            </page>
        </Chapter>"""

        doc = XMLDocument.from_xml(xml_string)
        stat_blocks = extract_stat_blocks_from_document(doc)

        assert len(stat_blocks) == 0

    def test_extract_stat_blocks_from_xml_file(self):
        """Test convenience wrapper for extracting from XML file."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        # Extract stat blocks directly from file
        stat_blocks = extract_stat_blocks_from_xml_file(str(fixture_path))

        # Verify extraction
        assert len(stat_blocks) == 2
        assert stat_blocks[0]["name"] == "Goblin"
        assert stat_blocks[1]["name"] == "Goblin Boss"

    def test_extract_stat_blocks_from_xml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            extract_stat_blocks_from_xml_file("/nonexistent/path.xml")
