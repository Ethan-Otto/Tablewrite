"""Tests for actor orchestration pipeline."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from actors.orchestrate import _create_output_directory, _save_intermediate_file, create_actor_from_description
from actors.models import StatBlock
from foundry.actors.models import ParsedActorData


class TestCreateOutputDirectory:
    """Test output directory creation."""

    def test_creates_directory_with_timestamp(self, tmp_path):
        """Test that directory is created with timestamp format."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        assert output_dir.exists()
        assert output_dir.is_dir()
        assert str(output_dir).startswith(str(base_dir))
        assert output_dir.name == "actors"

    def test_directory_structure(self, tmp_path):
        """Test that directory structure is output/runs/<timestamp>/actors/."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        # Should be: base_dir/<timestamp>/actors/
        assert output_dir.parent.parent == base_dir
        assert output_dir.name == "actors"

    def test_timestamp_format(self, tmp_path):
        """Test that timestamp follows YYYYMMDD_HHMMSS format."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        timestamp_dir = output_dir.parent.name
        # Should match format like: 20241103_143022
        assert len(timestamp_dir) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_dir[8] == "_"

    def test_creates_parents(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        base_dir = tmp_path / "nonexistent" / "nested" / "path"
        output_dir = _create_output_directory(str(base_dir))

        assert output_dir.exists()
        assert base_dir.exists()


class TestSaveIntermediateFile:
    """Test saving intermediate files."""

    def test_save_text_file(self, tmp_path):
        """Test saving plain text content."""
        filepath = tmp_path / "test.txt"
        content = "Goblin\nSmall humanoid, neutral evil"

        result = _save_intermediate_file(content, filepath, "test text")

        assert result == filepath
        assert filepath.exists()
        assert filepath.read_text() == content

    def test_save_dict_as_json(self, tmp_path):
        """Test saving dict as JSON."""
        filepath = tmp_path / "test.json"
        content = {"name": "Goblin", "cr": 0.25, "hp": 7}

        result = _save_intermediate_file(content, filepath, "test dict")

        assert result == filepath
        assert filepath.exists()

        loaded = json.loads(filepath.read_text())
        assert loaded == content

    def test_save_pydantic_model_as_json(self, tmp_path):
        """Test saving Pydantic model as JSON."""
        filepath = tmp_path / "stat_block.json"
        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )

        result = _save_intermediate_file(stat_block, filepath, "StatBlock")

        assert result == filepath
        assert filepath.exists()

        loaded = json.loads(filepath.read_text())
        assert loaded["name"] == "Goblin"
        assert loaded["armor_class"] == 15

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directories are created if needed."""
        filepath = tmp_path / "nested" / "dir" / "test.txt"
        content = "test content"

        result = _save_intermediate_file(content, filepath, "nested file")

        assert filepath.exists()
        assert filepath.parent.exists()

    def test_invalid_content_type_raises_error(self, tmp_path):
        """Test that invalid content type raises IOError."""
        filepath = tmp_path / "test.txt"

        with pytest.raises(IOError, match="Failed to save list"):
            _save_intermediate_file([1, 2, 3], filepath, "list")


class TestCreateActorPipeline:
    """Test main actor creation pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_calls_all_steps(self, tmp_path):
        """Test that pipeline calls all 5 steps in order."""

        # Mock all the async functions
        with patch('actors.orchestrate.generate_actor_description', new_callable=AsyncMock) as mock_gen, \
             patch('actors.orchestrate.parse_raw_text_to_statblock', new_callable=AsyncMock) as mock_parse_sb, \
             patch('actors.orchestrate.parse_stat_block_parallel', new_callable=AsyncMock) as mock_parse_actor, \
             patch('actors.orchestrate.convert_to_foundry') as mock_convert, \
             patch('actors.orchestrate.FoundryClient') as mock_client_class, \
             patch('actors.orchestrate._create_output_directory') as mock_create_dir:

            # Setup mocks
            mock_gen.return_value = "Goblin\nSmall humanoid..."

            mock_stat_block = StatBlock(
                name="Goblin",
                raw_text="Goblin\nSmall humanoid...",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25
            )
            mock_parse_sb.return_value = mock_stat_block

            mock_parsed = ParsedActorData(
                source_statblock_name="Goblin",
                name="Goblin",
                armor_class=15,
                hit_points=7,
                challenge_rating=0.25,
                abilities={"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8}
            )
            mock_parse_actor.return_value = mock_parsed

            mock_convert.return_value = ({"name": "Goblin"}, [])

            mock_client = MagicMock()
            mock_client.actors.create_actor.return_value = "Actor.abc123"
            mock_client_class.return_value = mock_client

            mock_create_dir.return_value = tmp_path / "test_output"
            (tmp_path / "test_output").mkdir()

            # Mock SpellCache
            mock_spell_cache = MagicMock()

            # Call the function
            result = await create_actor_from_description(
                description="A sneaky goblin",
                challenge_rating=0.25,
                output_dir_base=str(tmp_path),
                spell_cache=mock_spell_cache,
                foundry_client=mock_client
            )

            # Verify all steps were called
            assert mock_gen.called
            assert mock_parse_sb.called
            assert mock_parse_actor.called
            assert mock_convert.called
            assert mock_client.actors.create_actor.called

            # Verify result
            assert result.description == "A sneaky goblin"
            assert result.foundry_uuid == "Actor.abc123"
            assert result.stat_block.name == "Goblin"
