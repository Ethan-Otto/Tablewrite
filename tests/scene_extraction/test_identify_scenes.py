"""Tests for scene location identification."""

import pytest
from unittest.mock import patch, MagicMock
from src.scene_extraction.identify_scenes import identify_scene_locations
from src.scene_extraction.models import Scene, ChapterContext


@pytest.fixture
def sample_xml_content():
    """Sample XML for testing."""
    return """
    <chapter name="The Cragmaw Hideout">
        <section name="Area 1" id="area_1">
            <p>The cave entrance is dark and foreboding.</p>
        </section>
    </chapter>
    """


@pytest.fixture
def sample_context():
    """Sample chapter context."""
    return ChapterContext(
        environment_type="underground",
        lighting="dim",
        terrain="rocky caverns"
    )


class TestIdentifySceneLocations:
    """Tests for identify_scene_locations function."""

    @pytest.mark.integration
    def test_identify_scenes_calls_gemini(self, sample_xml_content, sample_context):
        """Test that identify_scene_locations calls Gemini with XML and context."""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = """
            [
                {
                    "section_path": "Chapter 1 → Area 1",
                    "name": "Cave Entrance",
                    "description": "Dark cave entrance with rough stone walls",
                    "location_type": "underground",
                    "xml_section_id": "area_1"
                }
            ]
            """
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations(sample_xml_content, sample_context)

            # Verify Gemini called
            mock_client.models.generate_content.assert_called_once()

            # Verify result
            assert len(scenes) == 1
            assert isinstance(scenes[0], Scene)
            assert scenes[0].name == "Cave Entrance"

    def test_identify_scenes_parses_json_array(self, sample_context):
        """Test parsing of JSON array response."""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '[{"section_path": "Ch1", "name": "Room", "description": "A room", "location_type": "interior"}]'
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert len(scenes) == 1
            assert scenes[0].name == "Room"

    def test_identify_scenes_returns_empty_list_on_no_scenes(self, sample_context):
        """Test that function returns empty list when no scenes found."""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = "[]"
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert scenes == []

    def test_identify_scenes_handles_markdown_json_same_line(self, sample_context):
        """Test parsing when json identifier is on same line as backticks: ```json"""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```json
[{"section_path": "Ch1", "name": "Forest Clearing", "description": "A sunlit clearing", "location_type": "outdoor"}]
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert len(scenes) == 1
            assert scenes[0].name == "Forest Clearing"
            assert scenes[0].description == "A sunlit clearing"

    def test_identify_scenes_handles_markdown_json_separate_line(self, sample_context):
        """Test parsing when json identifier is on separate line after backticks."""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```
json
[{"section_path": "Ch2", "name": "Underground Chamber", "description": "A dark stone chamber", "location_type": "underground"}]
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert len(scenes) == 1
            assert scenes[0].name == "Underground Chamber"
            assert scenes[0].description == "A dark stone chamber"

    def test_identify_scenes_handles_markdown_no_json_identifier(self, sample_context):
        """Test parsing when there's no json identifier, just backticks."""
        with patch('src.scene_extraction.identify_scenes.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```
[{"section_path": "Ch3", "name": "City Street", "description": "Cobblestone street", "location_type": "outdoor"}]
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            scenes = identify_scene_locations("<xml></xml>", sample_context)

            assert len(scenes) == 1
            assert scenes[0].name == "City Street"
            assert scenes[0].description == "Cobblestone street"
