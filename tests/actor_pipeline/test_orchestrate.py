"""Tests for actor orchestration pipeline."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from actor_pipeline.orchestrate import (
    _create_output_directory,
    _save_intermediate_file,
    create_actor_from_description,
    create_actor_from_description_sync,
    create_actors_batch,
    create_actors_batch_sync
)
from actor_pipeline.models import StatBlock, ActorCreationResult
from foundry_converters.actors.models import ParsedActorData


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

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_calls_all_steps(self, tmp_path):
        """Test that pipeline calls all 5 steps in order."""

        # Mock all the async functions
        with patch('actor_pipeline.orchestrate.generate_actor_description', new_callable=AsyncMock) as mock_gen, \
             patch('actor_pipeline.orchestrate.parse_raw_text_to_statblock', new_callable=AsyncMock) as mock_parse_sb, \
             patch('actor_pipeline.orchestrate.parse_stat_block_parallel', new_callable=AsyncMock) as mock_parse_actor, \
             patch('actor_pipeline.orchestrate.convert_to_foundry') as mock_convert, \
             patch('actor_pipeline.orchestrate.FoundryClient') as mock_client_class, \
             patch('actor_pipeline.orchestrate._create_output_directory') as mock_create_dir:

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

            # Mock SpellCache and IconCache
            mock_spell_cache = MagicMock()
            mock_icon_cache = MagicMock()
            mock_icon_cache.loaded = True
            mock_icon_cache.get_icon_path.return_value = "icons/default.webp"

            # Call the function
            result = await create_actor_from_description(
                description="A sneaky goblin",
                challenge_rating=0.25,
                output_dir_base=str(tmp_path),
                spell_cache=mock_spell_cache,
                icon_cache=mock_icon_cache,
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


class TestSyncWrapper:
    """Test synchronous wrapper function."""

    def test_sync_wrapper_calls_async_function(self, tmp_path):
        """Test that sync wrapper properly calls the async function."""

        # Mock asyncio.run to capture the call
        with patch('actor_pipeline.orchestrate.asyncio.run') as mock_run:
            mock_result = MagicMock()
            mock_run.return_value = mock_result

            result = create_actor_from_description_sync(
                description="Test goblin",
                challenge_rating=0.25,
                output_dir_base=str(tmp_path)
            )

            # Verify asyncio.run was called
            assert mock_run.called
            assert result == mock_result

            # Verify the async function was passed to asyncio.run
            call_args = mock_run.call_args
            assert call_args is not None


class TestBatchCreation:
    """Test batch actor creation."""

    @pytest.mark.asyncio
    async def test_batch_validates_input_length(self):
        """Test that mismatched list lengths raise error."""
        descriptions = ["Goblin", "Dragon"]
        crs = [0.25]  # Wrong length

        with pytest.raises(ValueError, match="same length"):
            await create_actors_batch(descriptions, challenge_ratings=crs)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_creates_tasks_for_all_descriptions(self, tmp_path):
        """Test that batch creates one task per description."""
        descriptions = ["Goblin 1", "Goblin 2", "Goblin 3"]

        with patch('actor_pipeline.orchestrate.create_actor_from_description', new_callable=AsyncMock) as mock_create, \
             patch('actor_pipeline.orchestrate.asyncio.gather', new_callable=AsyncMock) as mock_gather, \
             patch('actor_pipeline.orchestrate.SpellCache') as mock_cache_class, \
             patch('actor_pipeline.orchestrate.FoundryClient') as mock_client_class:

            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_gather.return_value = [MagicMock(), MagicMock(), MagicMock()]

            results = await create_actors_batch(
                descriptions,
                output_dir_base=str(tmp_path)
            )

            # Verify create_actor_from_description was called 3 times
            assert mock_create.call_count == 3

            # Verify gather was called with return_exceptions=True
            assert mock_gather.called
            call_kwargs = mock_gather.call_args.kwargs
            assert call_kwargs.get('return_exceptions') is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_returns_exceptions_for_failures(self, tmp_path):
        """Test that individual failures are captured as exceptions."""
        descriptions = ["Good", "Bad", "Ugly"]

        with patch('actor_pipeline.orchestrate.create_actor_from_description', new_callable=AsyncMock) as mock_create, \
             patch('actor_pipeline.orchestrate.SpellCache') as mock_cache_class, \
             patch('actor_pipeline.orchestrate.FoundryClient') as mock_client_class:

            # Setup mocks
            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock results: success, failure, success
            mock_result1 = MagicMock(spec=ActorCreationResult)
            mock_error = ValueError("API failed")
            mock_result3 = MagicMock(spec=ActorCreationResult)

            # Use side_effect to return different values
            mock_create.side_effect = [mock_result1, mock_error, mock_result3]

            # Manually simulate asyncio.gather behavior with exceptions
            with patch('actor_pipeline.orchestrate.asyncio.gather', new_callable=AsyncMock) as mock_gather:
                mock_gather.return_value = [mock_result1, mock_error, mock_result3]

                results = await create_actors_batch(
                    descriptions,
                    output_dir_base=str(tmp_path)
                )

                assert len(results) == 3
                assert results[0] == mock_result1
                assert isinstance(results[1], ValueError)
                assert results[2] == mock_result3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_uses_provided_resources(self, tmp_path):
        """Test that batch uses pre-loaded resources if provided."""
        descriptions = ["Goblin", "Dragon"]
        mock_cache = MagicMock()
        mock_client = MagicMock()

        with patch('actor_pipeline.orchestrate.create_actor_from_description', new_callable=AsyncMock) as mock_create, \
             patch('actor_pipeline.orchestrate.asyncio.gather', new_callable=AsyncMock) as mock_gather:

            mock_gather.return_value = [MagicMock(), MagicMock()]

            await create_actors_batch(
                descriptions,
                output_dir_base=str(tmp_path),
                spell_cache=mock_cache,
                foundry_client=mock_client
            )

            # Verify both calls used the same cache and client
            assert mock_create.call_count == 2
            for call in mock_create.call_args_list:
                kwargs = call.kwargs
                assert kwargs['spell_cache'] is mock_cache
                assert kwargs['foundry_client'] is mock_client

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_creates_resources_if_not_provided(self, tmp_path):
        """Test that batch creates resources if not provided."""
        descriptions = ["Goblin"]

        with patch('actor_pipeline.orchestrate.create_actor_from_description', new_callable=AsyncMock) as mock_create, \
             patch('actor_pipeline.orchestrate.asyncio.gather', new_callable=AsyncMock) as mock_gather, \
             patch('actor_pipeline.orchestrate.SpellCache') as mock_cache_class, \
             patch('actor_pipeline.orchestrate.FoundryClient') as mock_client_class:

            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_gather.return_value = [MagicMock()]

            await create_actors_batch(
                descriptions,
                output_dir_base=str(tmp_path)
            )

            # Verify resources were created
            assert mock_cache_class.called
            assert mock_cache.load.called
            assert mock_client_class.called

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_with_challenge_ratings(self, tmp_path):
        """Test batch processing with challenge ratings."""
        descriptions = ["Goblin", "Dragon"]
        crs = [0.25, 10.0]

        with patch('actor_pipeline.orchestrate.create_actor_from_description', new_callable=AsyncMock) as mock_create, \
             patch('actor_pipeline.orchestrate.asyncio.gather', new_callable=AsyncMock) as mock_gather, \
             patch('actor_pipeline.orchestrate.SpellCache') as mock_cache_class, \
             patch('actor_pipeline.orchestrate.FoundryClient') as mock_client_class:

            mock_cache = MagicMock()
            mock_cache_class.return_value = mock_cache
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_gather.return_value = [MagicMock(), MagicMock()]

            await create_actors_batch(
                descriptions,
                challenge_ratings=crs,
                output_dir_base=str(tmp_path)
            )

            # Verify both calls were made with correct CRs
            assert mock_create.call_count == 2
            call1_kwargs = mock_create.call_args_list[0].kwargs
            call2_kwargs = mock_create.call_args_list[1].kwargs

            assert call1_kwargs['description'] == "Goblin"
            assert call1_kwargs['challenge_rating'] == 0.25
            assert call2_kwargs['description'] == "Dragon"
            assert call2_kwargs['challenge_rating'] == 10.0

    def test_sync_batch_wrapper(self, tmp_path):
        """Test synchronous batch wrapper."""
        descriptions = ["Goblin"]

        with patch('actor_pipeline.orchestrate.asyncio.run') as mock_run:
            mock_result = [MagicMock()]
            mock_run.return_value = mock_result

            result = create_actors_batch_sync(
                descriptions,
                output_dir_base=str(tmp_path)
            )

            assert mock_run.called
            assert result == mock_result
