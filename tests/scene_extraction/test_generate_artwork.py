"""Tests for scene artwork generation."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.scene_extraction.generate_artwork import generate_scene_image, save_scene_image
from src.scene_extraction.models import Scene, ChapterContext


@pytest.fixture
def sample_scene():
    """Sample scene for testing."""
    return Scene(
        section_path="Chapter 1 → Area 1",
        name="Cave Entrance",
        description="A dark cave with rough stone walls and moss-covered rocks",
        location_type="underground"
    )


@pytest.fixture
def sample_context():
    """Sample chapter context."""
    return ChapterContext(
        environment_type="underground",
        lighting="dim",
        terrain="rocky caverns"
    )


class TestGenerateSceneImage:
    """Tests for generate_scene_image function."""

    @pytest.mark.integration
    def test_generate_image_calls_gemini_imagen(self, sample_scene, sample_context):
        """Test that generate_scene_image calls generate_images_parallel."""
        with patch('src.scene_extraction.generate_artwork.generate_images_parallel') as mock_generate:
            # Mock successful generation
            mock_generate.return_value = [b"fake_image_data"]

            # Call function
            image_bytes, prompt = generate_scene_image(sample_scene, sample_context, style_prompt="fantasy art")

            # Verify generate_images_parallel was called
            assert mock_generate.called
            call_args = mock_generate.call_args

            # Verify model parameter is imagen-4.0-fast-generate-001
            assert call_args.kwargs['model'] == 'imagen-4.0-fast-generate-001'

            # Verify prompts were passed
            prompts = call_args.kwargs.get('prompts', call_args[0] if call_args[0] else [])
            assert len(prompts) == 1

            # Verify result
            assert isinstance(image_bytes, bytes)
            assert image_bytes == b"fake_image_data"
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_generate_image_constructs_prompt_with_context(self, sample_scene, sample_context):
        """Test that prompt includes scene description and chapter context."""
        # Mock generate_images_parallel from our utility
        with patch('src.scene_extraction.generate_artwork.generate_images_parallel') as mock_generate:
            # Mock successful generation
            mock_generate.return_value = [b"fake_image_data"]

            # Call the function
            image_bytes, prompt = generate_scene_image(sample_scene, sample_context)

            # Verify the function was called with correct parameters
            assert mock_generate.called
            call_args = mock_generate.call_args

            # Verify prompt was passed and contains scene details
            prompts = call_args.kwargs.get('prompts', call_args[0] if call_args[0] else [])
            assert len(prompts) == 1
            prompt_text = prompts[0]
            assert "cave" in prompt_text.lower()
            assert "underground" in prompt_text.lower()

            # Verify result
            assert image_bytes == b"fake_image_data"
            assert isinstance(prompt, str)


class TestSaveSceneImage:
    """Tests for save_scene_image helper function."""

    def test_save_image_creates_file(self, tmp_path):
        """Test that save_scene_image saves bytes to file correctly."""
        # Setup
        test_data = b"fake_image_data_12345"
        output_path = tmp_path / "test_image.png"

        # Execute
        save_scene_image(test_data, str(output_path))

        # Verify
        assert output_path.exists()
        assert output_path.read_bytes() == test_data

    def test_save_image_creates_directory(self, tmp_path):
        """Test that save_scene_image creates parent directories."""
        # Setup
        test_data = b"test_data"
        output_path = tmp_path / "nested" / "directories" / "image.png"

        # Verify parent doesn't exist yet
        assert not output_path.parent.exists()

        # Execute
        save_scene_image(test_data, str(output_path))

        # Verify
        assert output_path.parent.exists()
        assert output_path.exists()
        assert output_path.read_bytes() == test_data

    def test_save_image_handles_write_error(self, tmp_path):
        """Test that save_scene_image properly handles IOError."""
        # Setup - create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        output_path = readonly_dir / "image.png"

        # Execute and verify
        with pytest.raises(IOError):
            save_scene_image(b"data", str(output_path))

        # Cleanup - restore permissions so pytest can clean up
        readonly_dir.chmod(0o755)
