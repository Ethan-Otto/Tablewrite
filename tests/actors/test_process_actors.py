"""Tests for actor processing workflow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from actors.process_actors import process_actors_for_run


@pytest.mark.unit
class TestActorProcessingWorkflow:
    """Test complete actor processing workflow (mocked)."""

    def test_process_actors_workflow(self):
        """Test complete workflow: extract stat blocks → parse → extract NPCs → create actors."""

        # Mock XML file
        run_dir = "/tmp/test_run"
        xml_file = f"{run_dir}/documents/chapter_01.xml"

        # Mock dependencies
        with patch('actors.process_actors.extract_and_parse_stat_blocks') as mock_extract_sb, \
             patch('actors.process_actors.identify_npcs_with_gemini') as mock_extract_npcs, \
             patch('actors.process_actors.FoundryClient') as mock_client_class, \
             patch('actors.process_actors.Path') as mock_path_class, \
             patch('actors.process_actors.GeminiAPI') as mock_gemini_api, \
             patch('builtins.open', create=True) as mock_open:

            # Setup mocks for Path
            mock_run_path = MagicMock()
            mock_run_path.exists.return_value = True
            mock_documents_dir = MagicMock()
            mock_documents_dir.exists.return_value = True
            mock_documents_dir.glob.return_value = [Path(xml_file)]
            mock_run_path.__truediv__.return_value = mock_documents_dir
            mock_path_class.return_value = mock_run_path

            # Mock file read
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = "<xml>test</xml>"
            mock_open.return_value = mock_file

            # Mock stat blocks
            from actors.models import StatBlock
            mock_stat_block = StatBlock(
                name="Goblin",
                raw_text="Goblin text",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25
            )
            mock_extract_sb.return_value = [mock_stat_block]

            # Mock NPCs
            from actors.models import NPC
            mock_npc = NPC(
                name="Klarg",
                creature_stat_block_name="Goblin Boss",
                description="Leader",
                plot_relevance="Guards supplies"
            )
            mock_extract_npcs.return_value = [mock_npc]

            # Mock FoundryClient
            mock_client = MagicMock()
            mock_client.search_actor.return_value = None  # Not found in compendium
            mock_client.create_creature_actor.return_value = "Actor.creature123"
            mock_client.create_npc_actor.return_value = "Actor.npc456"
            mock_client_class.return_value = mock_client

            # Run workflow
            result = process_actors_for_run(run_dir, target="local")

            # Verify calls
            mock_extract_sb.assert_called_once()
            mock_extract_npcs.assert_called_once()
            mock_client.search_actor.assert_called()
            mock_client.create_creature_actor.assert_called_once_with(mock_stat_block)
            mock_client.create_npc_actor.assert_called_once()

            # Verify result
            assert result["stat_blocks_found"] == 1
            assert result["stat_blocks_created"] == 1
            assert result["npcs_found"] == 1
            assert result["npcs_created"] == 1

    def test_process_actors_reuses_compendium(self):
        """Test workflow reuses existing compendium actors."""

        run_dir = "/tmp/test_run"
        xml_file = f"{run_dir}/documents/chapter_01.xml"

        with patch('actors.process_actors.extract_and_parse_stat_blocks') as mock_extract_sb, \
             patch('actors.process_actors.identify_npcs_with_gemini') as mock_extract_npcs, \
             patch('actors.process_actors.FoundryClient') as mock_client_class, \
             patch('actors.process_actors.Path') as mock_path_class, \
             patch('actors.process_actors.GeminiAPI') as mock_gemini_api, \
             patch('builtins.open', create=True) as mock_open:

            # Setup mocks for Path
            mock_run_path = MagicMock()
            mock_run_path.exists.return_value = True
            mock_documents_dir = MagicMock()
            mock_documents_dir.exists.return_value = True
            mock_documents_dir.glob.return_value = [Path(xml_file)]
            mock_run_path.__truediv__.return_value = mock_documents_dir
            mock_path_class.return_value = mock_run_path

            # Mock file read
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = "<xml>test</xml>"
            mock_open.return_value = mock_file

            from actors.models import StatBlock, NPC
            mock_stat_block = StatBlock(
                name="Goblin",
                raw_text="text",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25
            )
            mock_extract_sb.return_value = [mock_stat_block]

            mock_npc = NPC(
                name="Snarf",
                creature_stat_block_name="Goblin",
                description="Scout",
                plot_relevance="Ambushes party"
            )
            mock_extract_npcs.return_value = [mock_npc]

            # Mock client finds Goblin in compendium
            mock_client = MagicMock()
            mock_client.search_actor.return_value = "Actor.existing_goblin"
            mock_client.create_npc_actor.return_value = "Actor.npc789"
            mock_client_class.return_value = mock_client

            result = process_actors_for_run(run_dir, target="local")

            # Verify Goblin NOT created (reused from compendium)
            mock_client.create_creature_actor.assert_not_called()

            # Verify NPC created with existing Goblin UUID
            call_args = mock_client.create_npc_actor.call_args
            # call_args is (args, kwargs) - we want kwargs['stat_block_uuid']
            assert call_args.kwargs['stat_block_uuid'] == "Actor.existing_goblin"

            assert result["stat_blocks_reused"] == 1
