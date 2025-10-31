"""End-to-end tests for scene extraction workflow."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.scene_extraction import (
    extract_chapter_context,
    identify_scene_locations,
    generate_scene_image,
    save_scene_image,
    create_scene_gallery_html
)


@pytest.fixture
def test_xml_file(tmp_path):
    """Create test XML file."""
    xml_content = """
<chapter name="Test Chapter">
    <section name="Area 1" id="area_1">
        <p>A dark forest clearing with ancient trees.</p>
    </section>
</chapter>
"""
    xml_file = tmp_path / "test_chapter.xml"
    xml_file.write_text(xml_content)
    return xml_file


class TestSceneProcessingWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.integration
    def test_full_workflow_with_mocked_gemini(self, test_xml_file, tmp_path):
        """Test complete workflow with mocked Gemini calls."""
        xml_content = test_xml_file.read_text()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Patch each module's genai import separately
        # Note: extract_context and identify_scenes use old google.generativeai.GenerativeModel
        #       generate_artwork uses new google.genai.Client
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_context_model, \
             patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_scenes_model, \
             patch('src.scene_extraction.generate_artwork.genai.Client') as mock_client_class:

            # Set up context extraction mock
            mock_context_response = MagicMock()
            mock_context_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'
            mock_context_instance = MagicMock()
            mock_context_instance.generate_content.return_value = mock_context_response
            mock_context_model.return_value = mock_context_instance

            # Debug: verify mock setup and usage
            print(f"DEBUG: mock_context_model = {mock_context_model}")
            print(f"DEBUG: mock_context_model.return_value = {mock_context_model.return_value}")
            print(f"DEBUG: mock_context_response.text = {mock_context_response.text}")

            # Test that calling the model returns the instance
            test_instance = mock_context_model("gemini-2.0-flash-exp")
            print(f"DEBUG: Calling mock_context_model('gemini-2.0-flash-exp') returns: {test_instance}")
            print(f"DEBUG: Is it the same as mock_context_instance? {test_instance is mock_context_instance}")
            test_response = test_instance.generate_content("test")
            print(f"DEBUG: test_response.text = {test_response.text}")

            # Set up scene identification mock (old API)
            mock_scenes_response = MagicMock()
            mock_scenes_response.text = '[{"section_path": "Test Chapter → Area 1", "name": "Forest Clearing", "description": "A dark forest clearing", "location_type": "outdoor", "xml_section_id": "area_1"}]'
            mock_scenes_instance = MagicMock()
            mock_scenes_instance.generate_content.return_value = mock_scenes_response
            mock_scenes_model.return_value = mock_scenes_instance

            # Set up image generation mock (new API with genai.Client)
            mock_pil_image = MagicMock()
            mock_generated_image = MagicMock()
            mock_generated_image.image._pil_image = mock_pil_image
            mock_response = MagicMock()
            mock_response.generated_images = [mock_generated_image]

            mock_client = MagicMock()
            mock_client.models.generate_images.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Run workflow
            context = extract_chapter_context(xml_content)
            assert context.environment_type == "forest"

            scenes = identify_scene_locations(xml_content, context)
            assert len(scenes) == 1
            assert scenes[0].name == "Forest Clearing"

            # Mock BytesIO for image generation
            with patch('src.scene_extraction.generate_artwork.BytesIO') as mock_bytesio_class:
                mock_buffer = MagicMock()
                mock_buffer.getvalue.return_value = b"fake_png_data"
                mock_bytesio_class.return_value = mock_buffer

                image_bytes, prompt = generate_scene_image(scenes[0], context)
                assert image_bytes == b"fake_png_data"
                assert isinstance(prompt, str)

            image_path = output_dir / "scene_001_forest_clearing.png"
            save_scene_image(image_bytes, str(image_path))

            assert image_path.exists()
            assert image_path.read_bytes() == b"fake_png_data"

            # Create gallery HTML
            image_paths = {"Forest Clearing": str(image_path)}
            html = create_scene_gallery_html(scenes, image_paths)

            assert "Scene Gallery" in html
            assert "Forest Clearing" in html
            assert str(image_path) in html
