"""Tests for chapter context extraction."""

import pytest
from unittest.mock import patch, MagicMock
from src.scene_extraction.extract_context import extract_chapter_context
from src.scene_extraction.models import ChapterContext


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
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
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
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            # Call function
            context = extract_chapter_context(sample_xml_content)

            # Verify Gemini was called
            mock_model.assert_called_once()
            mock_instance.generate_content.assert_called_once()

            # Verify result is ChapterContext
            assert isinstance(context, ChapterContext)
            assert context.environment_type == "underground"
            assert context.terrain == "rocky caverns"

    def test_extract_context_handles_json_parsing(self):
        """Test that extract_context properly parses Gemini JSON response."""
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '{"environment_type": "forest", "lighting": "dappled sunlight"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            context = extract_chapter_context("<chapter></chapter>")

            assert context.environment_type == "forest"
            assert context.lighting == "dappled sunlight"

    def test_extract_context_raises_on_invalid_json(self):
        """Test that extract_context raises error on malformed JSON."""
        with patch('src.scene_extraction.extract_context.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = "Not valid JSON at all"
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            with pytest.raises(ValueError, match="Failed to parse.*JSON"):
                extract_chapter_context("<chapter></chapter>")
