"""Tests for chapter context extraction."""

import pytest
from unittest.mock import patch, MagicMock
from scene_extraction.extract_context import extract_chapter_context
from scene_extraction.models import ChapterContext


@pytest.fixture
def sample_xml_content():
    """Sample XML content for testing."""
    return """
    <chapter name="The Cragmaw Hideout">
        <section name="Overview">
            <p>Deep in the forest, a cave system serves as the hideout for Cragmaw goblins.</p>
        </section>
        <section name="Area 1">
            <p>The cave entrance is dark and foreboding, with rough stone walls.</p>
        </section>
    </chapter>
    """


class TestExtractChapterContext:
    """Tests for extract_chapter_context function."""

    @pytest.mark.integration
    def test_extract_context_calls_gemini(self, sample_xml_content):
        """Test that extract_chapter_context calls Gemini API with correct prompt."""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = """
            {
                "environment_type": "underground",
                "weather": "dry",
                "atmosphere": "oppressive",
                "lighting": "dim",
                "terrain": "rocky caverns",
                "additional_notes": "Forest cave system"
            }
            """
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call function
            context = extract_chapter_context(sample_xml_content)

            # Verify Gemini was called
            mock_client.models.generate_content.assert_called_once()

            # Verify result is ChapterContext
            assert isinstance(context, ChapterContext)
            assert context.environment_type == "underground"
            assert context.terrain == "rocky caverns"

    def test_extract_context_handles_json_parsing(self):
        """Test that extract_context properly parses Gemini JSON response."""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "forest"
            assert context.lighting == "dappled sunlight"

    def test_extract_context_raises_on_invalid_json(self):
        """Test that extract_context raises error on malformed JSON."""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = "Not valid JSON at all"
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Failed to parse.*JSON"):
                extract_chapter_context("<chapter></chapter>")

    def test_extract_context_handles_markdown_json_same_line(self):
        """Test parsing when json identifier is on same line as backticks: ```json"""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```json
{"environment_type": "forest", "lighting": "dappled sunlight"}
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "forest"
            assert context.lighting == "dappled sunlight"

    def test_extract_context_handles_markdown_json_separate_line(self):
        """Test parsing when json identifier is on separate line after backticks."""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```
json
{"environment_type": "underground", "atmosphere": "oppressive"}
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "underground"
            assert context.atmosphere == "oppressive"

    def test_extract_context_handles_markdown_no_json_identifier(self):
        """Test parsing when markdown blocks have no json identifier."""
        with patch('src.scene_extraction.extract_context.genai.Client') as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = '''```
{"environment_type": "coastal", "weather": "foggy"}
```'''
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "coastal"
            assert context.weather == "foggy"
