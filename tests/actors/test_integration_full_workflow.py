"""
Full integration tests for actor extraction workflow.

These tests use REAL Gemini API calls to verify the complete workflow:
- XML stat block extraction and parsing
- NPC identification and linking
- Actor creation (mocked FoundryVTT API)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from actors.extract_stat_blocks import extract_and_parse_stat_blocks
from actors.extract_npcs import identify_npcs_with_gemini
from actors.process_actors import process_actors_for_run
from actors.models import StatBlock, NPC


@pytest.mark.integration
@pytest.mark.requires_api
class TestFullActorExtractionWorkflow:
    """Integration tests for complete actor extraction workflow with real Gemini API."""

    def test_complete_workflow_with_sample_chapter(self, check_api_key):
        """
        Test complete workflow: XML → stat blocks → NPCs → actor creation.

        Uses real Gemini API calls for parsing and extraction.
        Mocks only FoundryVTT API calls.
        """
        # Use the sample XML fixture with stat blocks and NPCs
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"

        # Step 1: Extract and parse stat blocks with real Gemini API
        stat_blocks = extract_and_parse_stat_blocks(str(fixture_path))

        # Verify stat blocks were extracted and parsed
        assert len(stat_blocks) >= 2, "Should extract at least 2 stat blocks (Bugbear, Human Fighter)"

        # Find the stat blocks by name
        stat_block_names = [sb.name.upper() for sb in stat_blocks]
        assert "BUGBEAR" in stat_block_names, "Should extract Bugbear stat block"
        assert "HUMAN FIGHTER" in stat_block_names or "HUMAN" in stat_block_names, \
            "Should extract Human Fighter stat block"

        # Verify stat blocks have required fields
        for stat_block in stat_blocks:
            assert isinstance(stat_block, StatBlock)
            assert stat_block.armor_class > 0
            assert stat_block.hit_points > 0
            assert stat_block.challenge_rating >= 0
            assert stat_block.raw_text  # Original text preserved

        # Step 2: Extract NPCs with real Gemini API
        with open(fixture_path, 'r') as f:
            xml_content = f.read()

        npcs = identify_npcs_with_gemini(xml_content)

        # Verify NPCs were extracted
        assert len(npcs) >= 2, "Should extract at least 2 NPCs (Klarg, Sildar)"

        # Find NPCs by name
        npc_names = [npc.name for npc in npcs]
        assert "Klarg" in npc_names, "Should extract Klarg"
        assert "Sildar Hallwinter" in npc_names or "Sildar" in npc_names, \
            "Should extract Sildar Hallwinter"

        # Verify NPCs have required fields and stat block links
        for npc in npcs:
            assert isinstance(npc, NPC)
            assert npc.creature_stat_block_name  # Linked to creature
            assert npc.description
            assert npc.plot_relevance

        # Step 3: Verify NPCs are linked to correct stat blocks
        klarg = next((npc for npc in npcs if npc.name == "Klarg"), None)
        assert klarg is not None
        assert klarg.creature_stat_block_name == "Bugbear", \
            "Klarg should be linked to Bugbear stat block"

        sildar = next((npc for npc in npcs if "Sildar" in npc.name), None)
        assert sildar is not None
        assert "Human" in sildar.creature_stat_block_name or \
               "Fighter" in sildar.creature_stat_block_name, \
            "Sildar should be linked to Human Fighter stat block"

    def test_workflow_with_run_directory(self, check_api_key, tmp_path):
        """
        Test process_actors_for_run with real Gemini API calls.

        Simulates a run directory with XML files and processes actors.
        Mocks FoundryVTT API calls.
        """
        # Create mock run directory structure
        run_dir = tmp_path / "test_run"
        documents_dir = run_dir / "documents"
        documents_dir.mkdir(parents=True)

        # Copy sample XML to run directory
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"
        test_xml = documents_dir / "chapter_01.xml"
        test_xml.write_text(fixture_path.read_text())

        # Mock FoundryVTT API calls
        with patch('actors.process_actors.FoundryClient') as mock_client_class:
            mock_client = Mock()
            mock_client.search_actor.return_value = None  # No existing actors
            mock_client.create_creature_actor.return_value = "Actor.creature123"
            mock_client.create_npc_actor.return_value = "Actor.npc456"
            mock_client_class.return_value = mock_client

            # Run the full workflow
            stats = process_actors_for_run(str(run_dir), target="local")

        # Verify statistics
        assert stats["stat_blocks_found"] >= 2, "Should find at least 2 stat blocks"
        assert stats["stat_blocks_created"] >= 2, "Should create at least 2 creature actors"
        assert stats["stat_blocks_reused"] == 0, "No actors should be reused (all new)"
        assert stats["npcs_found"] >= 2, "Should find at least 2 NPCs"
        assert stats["npcs_created"] >= 2, "Should create at least 2 NPC actors"
        assert len(stats["errors"]) == 0, f"No errors expected, got: {stats['errors']}"

        # Verify FoundryVTT API was called
        assert mock_client.search_actor.call_count >= 2, \
            "Should search for each creature type"
        assert mock_client.create_creature_actor.call_count >= 2, \
            "Should create at least 2 creature actors"
        assert mock_client.create_npc_actor.call_count >= 2, \
            "Should create at least 2 NPC actors"

    def test_workflow_with_compendium_reuse(self, check_api_key, tmp_path):
        """
        Test workflow reuses existing actors from compendium.

        Uses real Gemini API for parsing/extraction.
        Mocks FoundryVTT to simulate existing actors in compendium.
        """
        # Create mock run directory
        run_dir = tmp_path / "test_run_reuse"
        documents_dir = run_dir / "documents"
        documents_dir.mkdir(parents=True)

        # Copy sample XML
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"
        test_xml = documents_dir / "chapter_01.xml"
        test_xml.write_text(fixture_path.read_text())

        # Mock FoundryVTT with existing actors in compendium
        with patch('actors.process_actors.FoundryClient') as mock_client_class:
            mock_client = Mock()

            # Simulate Bugbear exists in compendium, Human Fighter does not
            def mock_search(name):
                if "BUGBEAR" in name.upper():
                    return "Actor.existing_bugbear"
                return None

            mock_client.search_actor.side_effect = mock_search
            mock_client.create_creature_actor.return_value = "Actor.new_human"
            mock_client.create_npc_actor.return_value = "Actor.npc_created"
            mock_client_class.return_value = mock_client

            # Run workflow
            stats = process_actors_for_run(str(run_dir), target="local")

        # Verify compendium reuse
        assert stats["stat_blocks_reused"] >= 1, \
            "Should reuse at least 1 actor (Bugbear) from compendium"
        assert stats["stat_blocks_created"] >= 1, \
            "Should create at least 1 new actor (Human Fighter)"

        # Verify NPCs were linked to both existing and new actors
        assert stats["npcs_created"] >= 2, "Should create NPCs"

    def test_workflow_handles_no_stat_blocks(self, check_api_key, tmp_path):
        """
        Test workflow gracefully handles XML with no stat blocks.

        Uses real Gemini API - should identify NPCs but no stat blocks.
        """
        # Create run directory
        run_dir = tmp_path / "test_run_no_stats"
        documents_dir = run_dir / "documents"
        documents_dir.mkdir(parents=True)

        # Create XML with NPCs but no stat blocks
        xml_content = """
        <Chapter_01>
            <page number="1">
                <section>Town of Phandalin</section>
                <p>The mayor greets you warmly.</p>
            </page>
        </Chapter_01>
        """
        test_xml = documents_dir / "chapter_01.xml"
        test_xml.write_text(xml_content)

        # Mock FoundryVTT
        with patch('actors.process_actors.FoundryClient') as mock_client_class:
            mock_client = Mock()
            mock_client.search_actor.return_value = None
            mock_client_class.return_value = mock_client

            # Run workflow
            stats = process_actors_for_run(str(run_dir), target="local")

        # Verify graceful handling
        assert stats["stat_blocks_found"] == 0, "No stat blocks in XML"
        assert stats["stat_blocks_created"] == 0, "No creatures created"
        assert len(stats["errors"]) == 0, "No errors - empty results are valid"

    def test_stat_block_parsing_accuracy(self, check_api_key):
        """
        Test Gemini parsing accuracy for various stat block formats.

        Verifies Gemini correctly extracts all D&D 5e fields.
        """
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_stat_blocks.xml"

        # Extract and parse with real Gemini API
        stat_blocks = extract_and_parse_stat_blocks(str(fixture_path))

        assert len(stat_blocks) >= 2, "Should parse multiple stat blocks"

        # Verify Goblin stat block accuracy
        goblin = next((sb for sb in stat_blocks if "GOBLIN" in sb.name.upper() and "BOSS" not in sb.name.upper()), None)
        if goblin:
            assert goblin.armor_class == 15, "Goblin AC should be 15"
            assert goblin.hit_points == 7, "Goblin HP should be 7"
            assert goblin.challenge_rating == 0.25, "Goblin CR should be 1/4"

            # Verify optional fields if parsed
            if goblin.abilities:
                assert "DEX" in goblin.abilities or "dex" in goblin.abilities, \
                    "Goblin should have DEX ability score"

    def test_npc_extraction_accuracy(self, check_api_key):
        """
        Test Gemini NPC extraction accuracy.

        Verifies NPCs are correctly identified and linked to stat blocks.
        """
        fixture_path = Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"

        with open(fixture_path, 'r') as f:
            xml_content = f.read()

        # Extract NPCs with real Gemini API
        npcs = identify_npcs_with_gemini(xml_content)

        assert len(npcs) >= 2, "Should identify multiple NPCs"

        # Verify Klarg details
        klarg = next((npc for npc in npcs if npc.name == "Klarg"), None)
        if klarg:
            assert klarg.creature_stat_block_name == "Bugbear", \
                "Klarg should be linked to Bugbear"
            assert "goblin" in klarg.description.lower() or \
                   "cragmaw" in klarg.description.lower(), \
                "Klarg description should mention goblins or Cragmaw"
            assert klarg.location is not None, "Klarg should have a location"

        # Verify Sildar details
        sildar = next((npc for npc in npcs if "Sildar" in npc.name), None)
        if sildar:
            assert "Human" in sildar.creature_stat_block_name or \
                   "Fighter" in sildar.creature_stat_block_name, \
                "Sildar should be linked to Human Fighter"
            assert "lords" in sildar.description.lower() or \
                   "alliance" in sildar.description.lower(), \
                "Sildar description should mention Lords' Alliance"


@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.slow
class TestEndToEndWithRealPDF:
    """
    End-to-end tests that process real PDFs with Gemini API.

    These tests are marked as slow and require both Gemini API and test PDFs.
    Uses the Appendix B: Monsters PDF which contains 20+ stat blocks.
    """

    def test_xml_has_stat_block_tags(self, check_api_key, tmp_path):
        """
        Test that XML generation includes stat block tags.

        Uses Appendix B: Monsters PDF which contains stat blocks for:
        - Goblin, Ghoul, Giant Spider, Grick, Hobgoblin
        - Owlbear, Ogre, Spectator, Stirge, Wolf
        - Young Green Dragon, Zombie, Cultist, Doppelganger
        - And more (20+ total stat blocks)

        This verifies:
        1. pdf_to_xml.py processes the PDF successfully
        2. <stat_block name="..."> tags are present in output XML
        3. Raw stat block text is preserved inside tags
        4. Multiple stat blocks are detected
        """
        import sys
        import os
        import re
        import glob
        from pathlib import Path

        # Path to monsters PDF directory
        monsters_pdf_dir = Path("/Users/ethanotto/Documents/Projects/dnd_module_gen/data/pdf_sections/Lost_Mine_of_Phandelver")
        monsters_pdf_name = "08_Appendix_B_Monsters.pdf"
        monsters_pdf = monsters_pdf_dir / monsters_pdf_name

        if not monsters_pdf.exists():
            pytest.skip(f"Monsters PDF not found: {monsters_pdf}")

        # Add src to path for importing pdf_to_xml
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root / "src"))

        # Import the PDF processing main function
        from pdf_processing.pdf_to_xml import main, configure_gemini

        # Create output directory
        output_dir = tmp_path / "monsters_output"
        output_dir.mkdir(parents=True)

        # Process the monsters PDF
        print(f"\nProcessing monsters PDF: {monsters_pdf}")
        print(f"Output directory: {output_dir}")

        try:
            # Configure Gemini API
            configure_gemini()

            # Process the PDF (this will make real Gemini API calls)
            # main() expects:
            #   - input_dir: directory containing PDFs
            #   - base_output_dir: where to create timestamped run
            #   - single_file: name of the PDF file to process
            main(
                input_dir=str(monsters_pdf_dir),
                base_output_dir=str(output_dir),
                single_file=monsters_pdf_name
            )

            # Find the generated XML in the timestamped run directory
            # The structure is: output_dir/<timestamp>/documents/08_Appendix_B_Monsters.xml
            run_dirs = sorted(glob.glob(str(output_dir / "*")))
            assert len(run_dirs) > 0, "No run directory created"

            latest_run = run_dirs[-1]
            xml_output_path = Path(latest_run) / "documents" / "08_Appendix_B_Monsters.xml"

            assert xml_output_path.exists(), f"XML output not created: {xml_output_path}"

            # Read the generated XML
            with open(xml_output_path, 'r') as f:
                xml_content = f.read()

            # Verify stat blocks are tagged
            stat_block_pattern = r'<stat_block name="([^"]+)">(.*?)</stat_block>'
            stat_blocks = re.findall(stat_block_pattern, xml_content, re.DOTALL)

            print(f"\nFound {len(stat_blocks)} stat blocks in generated XML:")
            for name, _ in stat_blocks[:5]:  # Show first 5
                print(f"  - {name}")
            if len(stat_blocks) > 5:
                print(f"  ... and {len(stat_blocks) - 5} more")

            # Assertions
            assert len(stat_blocks) >= 5, \
                f"Expected at least 5 stat blocks, found {len(stat_blocks)}"

            # Check for some expected creatures
            stat_block_names = [name.upper() for name, _ in stat_blocks]
            expected_creatures = ["GOBLIN", "GHOUL", "GIANT SPIDER", "OGRE", "WOLF"]

            found_expected = []
            for expected in expected_creatures:
                if any(expected in name for name in stat_block_names):
                    found_expected.append(expected)

            print(f"\nExpected creatures found: {found_expected}")

            assert len(found_expected) >= 2, \
                f"Expected to find at least 2 of {expected_creatures}, found {found_expected}"

            # Verify raw text is preserved (check one stat block)
            if stat_blocks:
                first_name, first_content = stat_blocks[0]
                assert len(first_content.strip()) > 50, \
                    f"Stat block '{first_name}' content too short: {len(first_content)} chars"

                # Should contain typical stat block elements
                typical_elements = ["Armor Class", "Hit Points", "Speed", "STR", "DEX"]
                found_elements = [elem for elem in typical_elements if elem in first_content]

                assert len(found_elements) >= 2, \
                    f"Stat block should contain typical elements, found {found_elements}"

            print("\n✅ XML stat block tagging verification passed!")

        except Exception as e:
            pytest.fail(f"Failed to process PDF or verify output: {e}")
