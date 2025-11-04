"""Tests for Gemini service."""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Mock the util.gemini module before any imports
sys.modules['util'] = MagicMock()
sys.modules['util.gemini'] = MagicMock()

from app.services.gemini_service import GeminiService


@pytest.fixture
def gemini_service():
    """Create GeminiService with mocked API."""
    # Patch GeminiAPI at the module level
    with patch('app.services.gemini_service.GeminiAPI') as mock_api_class:
        # Create a mock API instance
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance

        # Create service (will use mocked API)
        service = GeminiService()

        yield service


def test_generate_chat_response(gemini_service):
    """Test generating chat response."""
    # Mock API response
    mock_response = Mock()
    mock_response.text = "This is a test response from Gemini."
    gemini_service.api.generate_content.return_value = mock_response

    result = gemini_service.generate_chat_response(
        message="Hello",
        context={}
    )

    assert result == "This is a test response from Gemini."
    gemini_service.api.generate_content.assert_called_once()


def test_generate_scene_description(gemini_service):
    """Test generating scene description."""
    mock_response = Mock()
    mock_response.text = "A dark cave with dripping water and moss-covered walls."
    gemini_service.api.generate_content.return_value = mock_response

    result = gemini_service.generate_scene_description("dark cave")

    assert "dark cave" in result.lower() or "dripping water" in result
