"""Tests for NPC extraction with Gemini."""

import pytest
from pathlib import Path
from actor_pipeline.extract_npcs import identify_npcs_with_gemini
from actor_pipeline.models import NPC


@pytest.mark.gemini
class TestNPCExtraction:
    """Test NPC extraction with real Gemini API calls."""

    def test_identify_npcs_from_xml(self, check_api_key):
        """Test Gemini identifies named NPCs from XML."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"

        with open(fixture_path, 'r') as f:
            xml_content = f.read()

        npcs = identify_npcs_with_gemini(xml_content)

        # Should find at least Klarg and Sildar
        assert len(npcs) >= 2

        npc_names = [npc.name for npc in npcs]
        assert "Klarg" in npc_names
        assert "Sildar Hallwinter" in npc_names

        # Check Klarg details
        klarg = next(npc for npc in npcs if npc.name == "Klarg")
        assert klarg.creature_stat_block_name == "Bugbear"
        assert "goblin" in klarg.description.lower() or "cragmaw" in klarg.description.lower()
        assert klarg.location is not None

        # Check Sildar details
        sildar = next(npc for npc in npcs if npc.name == "Sildar Hallwinter")
        assert sildar.creature_stat_block_name == "Human Fighter"
        assert "lords" in sildar.description.lower() or "alliance" in sildar.description.lower()

    def test_identify_npcs_no_npcs(self, check_api_key):
        """Test extraction from XML with no named NPCs."""
        xml_content = """
        <Chapter>
            <page>
                <section>Empty Room</section>
                <p>This room contains nothing of interest.</p>
            </page>
        </Chapter>
        """

        npcs = identify_npcs_with_gemini(xml_content)

        assert len(npcs) == 0


@pytest.mark.unit
class TestNPCExtractionUnit:
    """Unit tests for NPC extraction."""

    def test_function_exists(self):
        """Verify function exists with correct signature."""
        from actor_pipeline.extract_npcs import identify_npcs_with_gemini
        import inspect

        sig = inspect.signature(identify_npcs_with_gemini)
        assert 'xml_content' in sig.parameters
