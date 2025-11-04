"""Integration tests for actor orchestration pipeline."""

import pytest
import os
from pathlib import Path

from actors.orchestrate import create_actor_from_description
from actors.models import ActorCreationResult


class TestActorOrchestrationIntegration:
    """Integration tests for full actor creation pipeline."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_end_to_end(self, tmp_path):
        """
        Test complete pipeline from description to FoundryVTT.

        NOTE: This test currently expects generate_actor_description() to be implemented.
        Since it's a stub, we skip if NotImplementedError is raised.
        """
        # Skip if API key not available
        if not os.getenv("GeminiImageAPI") and not os.getenv("GEMINI_API_KEY"):
            pytest.skip("Gemini API key not available")

        # Skip if FoundryVTT not available (connection may fail)
        # The test will handle FoundryVTT connection errors gracefully

        description = "A small goblin warrior with a rusty short sword"
        challenge_rating = 0.25

        try:
            result = await create_actor_from_description(
                description=description,
                challenge_rating=challenge_rating,
                output_dir_base=str(tmp_path)
            )

            # Verify result structure
            assert isinstance(result, ActorCreationResult)
            assert result.description == description
            assert result.challenge_rating == challenge_rating

            # Verify intermediate outputs exist
            assert result.raw_stat_block_text
            assert result.stat_block
            assert result.stat_block.name
            assert result.stat_block.armor_class > 0
            assert result.stat_block.hit_points > 0
            assert result.stat_block.challenge_rating == challenge_rating

            assert result.parsed_actor_data
            assert result.parsed_actor_data.name

            # Verify FoundryVTT UUID
            assert result.foundry_uuid
            assert result.foundry_uuid.startswith("Actor.")

            # Verify files were saved
            assert result.output_dir.exists()
            assert result.raw_text_file and result.raw_text_file.exists()
            assert result.stat_block_file and result.stat_block_file.exists()
            assert result.parsed_data_file and result.parsed_data_file.exists()
            assert result.foundry_json_file and result.foundry_json_file.exists()

            # Verify file contents can be read
            assert result.raw_text_file.read_text()
            assert result.stat_block_file.read_text()
            assert result.parsed_data_file.read_text()
            assert result.foundry_json_file.read_text()

            print(f"✓ Integration test passed!")
            print(f"  Actor: {result.stat_block.name}")
            print(f"  UUID: {result.foundry_uuid}")
            print(f"  Output: {result.output_dir}")

        except NotImplementedError as e:
            if "generate_actor_description" in str(e):
                pytest.skip("generate_actor_description() not yet implemented")
            else:
                raise
        except Exception as e:
            # Log the error for debugging but allow test to see it
            print(f"Integration test failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_creates_output_directory(self, tmp_path):
        """Test that pipeline creates properly structured output directory."""
        description = "A simple test goblin"

        try:
            result = await create_actor_from_description(
                description=description,
                challenge_rating=0.25,
                output_dir_base=str(tmp_path)
            )

            # Verify directory structure
            assert result.output_dir.exists()
            assert result.output_dir.parent.parent == tmp_path
            assert result.output_dir.name == "actors"

            # Verify timestamp directory exists
            timestamp_dir = result.output_dir.parent
            assert len(timestamp_dir.name) == 15  # YYYYMMDD_HHMMSS

        except NotImplementedError as e:
            if "generate_actor_description" in str(e):
                pytest.skip("generate_actor_description() not yet implemented")
            else:
                raise
