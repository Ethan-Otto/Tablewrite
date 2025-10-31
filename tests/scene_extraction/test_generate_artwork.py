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
        """Test that generate_scene_image calls Gemini Imagen API."""
        with patch('src.scene_extraction.generate_artwork.genai.Client') as mock_client_class:
            # Mock the PIL Image
            mock_pil_image = MagicMock()

            # Mock the generated image
            mock_generated_image = MagicMock()
            mock_generated_image.image._pil_image = mock_pil_image

            # Mock the response with generated_images list
            mock_response = MagicMock()
            mock_response.generated_images = [mock_generated_image]

            # Mock the client instance and models.generate_images
            mock_client = MagicMock()
            mock_client.models.generate_images.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Mock BytesIO save
            with patch('src.scene_extraction.generate_artwork.BytesIO') as mock_bytesio_class:
                mock_buffer = MagicMock()
                mock_buffer.getvalue.return_value = b"fake_image_data"
                mock_bytesio_class.return_value = mock_buffer

                # Call function
                image_bytes, prompt = generate_scene_image(sample_scene, sample_context, style_prompt="fantasy art")

                # Verify Client was created
                mock_client_class.assert_called_once()

                # Verify generate_images was called
                mock_client.models.generate_images.assert_called_once()

                # Verify PIL image save was called
                mock_pil_image.save.assert_called_once()

                # Verify result
                assert isinstance(image_bytes, bytes)
                assert image_bytes == b"fake_image_data"
                assert isinstance(prompt, str)
                assert len(prompt) > 0

    def test_generate_image_constructs_prompt_with_context(self, sample_scene, sample_context):
        """Test that prompt includes scene description and chapter context."""
        with patch('src.scene_extraction.generate_artwork.genai.Client') as mock_client_class:
            # Mock the PIL Image
            mock_pil_image = MagicMock()

            # Mock the generated image
            mock_generated_image = MagicMock()
            mock_generated_image.image._pil_image = mock_pil_image

            # Mock the response
            mock_response = MagicMock()
            mock_response.generated_images = [mock_generated_image]

            # Mock the client
            mock_client = MagicMock()
            mock_client.models.generate_images.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Mock BytesIO
            with patch('src.scene_extraction.generate_artwork.BytesIO') as mock_bytesio_class:
                mock_buffer = MagicMock()
                mock_buffer.getvalue.return_value = b"data"
                mock_bytesio_class.return_value = mock_buffer

                generate_scene_image(sample_scene, sample_context)

                # Verify prompt contains scene description and context
                call_args = mock_client.models.generate_images.call_args
                # The prompt is passed as the 'prompt' keyword argument
                prompt = call_args.kwargs.get('prompt', '')
                assert "cave" in prompt.lower()
                assert "underground" in prompt.lower()


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
