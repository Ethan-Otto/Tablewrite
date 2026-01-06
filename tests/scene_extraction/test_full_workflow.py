"""End-to-end tests for scene extraction workflow."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scene_extraction import (
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

        # Patch genai.Client constructor (new API pattern)
        # NOTE: All scene_extraction modules share the same genai import,
        # so we only need to patch once
        with patch('google.genai.Client') as mock_client_class:

            # Create shared mock client that handles all three operations
            mock_client = MagicMock()

            # Set up context extraction response
            mock_context_response = MagicMock()
            mock_context_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'

            # Set up scene identification response
            mock_scenes_response = MagicMock()
            mock_scenes_response.text = '[{"section_path": "Test Chapter → Area 1", "name": "Forest Clearing", "description": "A dark forest clearing", "location_type": "outdoor", "xml_section_id": "area_1"}]'

            # Mock generate_content to return appropriate response based on call count
            mock_client.models.generate_content.side_effect = [mock_context_response, mock_scenes_response]

            # Set up image generation response
            mock_pil_image = MagicMock()
            mock_generated_image = MagicMock()
            mock_generated_image.image._pil_image = mock_pil_image
            mock_gen_response = MagicMock()
            mock_gen_response.generated_images = [mock_generated_image]
            mock_client.models.generate_images.return_value = mock_gen_response

            mock_client_class.return_value = mock_client

            # Run workflow
            context = extract_chapter_context(xml_content)
            assert context.environment_type == "forest"

            scenes = identify_scene_locations(xml_content, context)
            assert len(scenes) == 1
            assert scenes[0].name == "Forest Clearing"

            # Mock generate_images_parallel for image generation
            with patch('src.scene_extraction.generate_artwork.generate_images_parallel') as mock_gen:
                mock_gen.return_value = [b"fake_png_data"]

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
