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

        # Create mock responses that will be used sequentially
        # Mock for context extraction
        mock_context_response = MagicMock()
        mock_context_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'

        # Mock for scene identification
        mock_scenes_response = MagicMock()
        mock_scenes_response.text = '[{"section_path": "Test Chapter → Area 1", "name": "Forest Clearing", "description": "A dark forest clearing", "xml_section_id": "area_1"}]'

        # Mock for image generation
        mock_image_response = MagicMock()
        mock_image_response._result = MagicMock()
        mock_image_response._result.candidates = [MagicMock()]
        mock_image_response._result.candidates[0].content = MagicMock()
        mock_image_response._result.candidates[0].content.parts = [MagicMock()]
        mock_image_response._result.candidates[0].content.parts[0].inline_data = MagicMock()
        mock_image_response._result.candidates[0].content.parts[0].inline_data.data = b"fake_png_data"

        # Patch each module's genai import separately
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_context_model, \
             patch('src.scene_extraction.identify_scenes.genai.GenerativeModel') as mock_scenes_model, \
             patch('src.scene_extraction.generate_artwork.genai.GenerativeModel') as mock_image_model:

            # Set up context extraction mock
            mock_context_instance = MagicMock()
            mock_context_instance.generate_content.return_value = mock_context_response
            mock_context_model.return_value = mock_context_instance

            # Set up scene identification mock
            mock_scenes_instance = MagicMock()
            mock_scenes_instance.generate_content.return_value = mock_scenes_response
            mock_scenes_model.return_value = mock_scenes_instance

            # Set up image generation mock
            mock_image_instance = MagicMock()
            mock_image_instance.generate_content.return_value = mock_image_response
            mock_image_model.return_value = mock_image_instance

            # Run workflow
            context = extract_chapter_context(xml_content)
            assert context.environment_type == "forest"

            scenes = identify_scene_locations(xml_content, context)
            assert len(scenes) == 1
            assert scenes[0].name == "Forest Clearing"

            image_bytes = generate_scene_image(scenes[0], context)
            assert image_bytes == b"fake_png_data"

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
