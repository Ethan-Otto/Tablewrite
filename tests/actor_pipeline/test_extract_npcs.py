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

        # Should find at least Snarltooth and Erik Stoneheart
        assert len(npcs) >= 2

        npc_names = [npc.name for npc in npcs]
        assert "Snarltooth" in npc_names
        assert "Erik Stoneheart" in npc_names

        # Check Snarltooth details (bugbear leader)
        snarltooth = next(npc for npc in npcs if npc.name == "Snarltooth")
        assert snarltooth.creature_stat_block_name == "Bugbear"
        assert "goblin" in snarltooth.description.lower() or "mill" in snarltooth.description.lower()
        assert snarltooth.location is not None

        # Check Erik Stoneheart details (human fighter)
        erik = next(npc for npc in npcs if npc.name == "Erik Stoneheart")
        assert erik.creature_stat_block_name == "Human Fighter"
        assert "merchant" in erik.description.lower() or "guild" in erik.description.lower()

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
