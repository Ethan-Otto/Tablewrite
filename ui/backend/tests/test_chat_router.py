"""Tests for chat router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_chat_endpoint_basic(client):
    """Test basic chat endpoint."""
    with patch('app.routers.chat.GeminiService') as mock_service:
        mock_instance = Mock()
        mock_instance.generate_chat_response.return_value = "Hello! How can I help?"
        mock_service.return_value = mock_instance

        response = client.post(
            "/api/chat",
            json={"message": "Hello", "context": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "text"
        assert "Hello" in data["message"]


def test_chat_endpoint_generate_scene_command(client):
    """Test /generate-scene command with image generation."""
    from app.tools.base import ToolResponse
    from unittest.mock import AsyncMock

    with patch('app.routers.chat.gemini_service') as mock_gemini:
        mock_gemini.generate_scene_description.return_value = "A dark cave entrance"

        # Mock the image generator tool with async execute
        with patch('app.routers.chat.registry') as mock_registry:
            mock_tool = Mock()
            mock_tool.execute = AsyncMock(return_value=ToolResponse(
                type="image",
                message="Generated image",
                data={"image_urls": ["/api/images/test.png"], "prompt": "test"}
            ))
            mock_registry.tools.get.return_value = mock_tool

            response = client.post(
                "/api/chat",
                json={"message": "/generate-scene dark cave", "context": {}}
            )

            assert response.status_code == 200
            data = response.json()
            # Now returns image type since it generates an image
            assert data["type"] == "image"
            assert "cave" in data["message"].lower()
            assert "image_urls" in data["data"]


def test_chat_endpoint_generate_scene_fallback(client):
    """Test /generate-scene command falls back gracefully if image generation fails."""
    with patch('app.routers.chat.gemini_service') as mock_gemini:
        mock_gemini.generate_scene_description.return_value = "A dark cave entrance"

        # Mock the image generator tool to return None (not found)
        with patch('app.routers.chat.registry') as mock_registry:
            mock_registry.tools.get.return_value = None

            response = client.post(
                "/api/chat",
                json={"message": "/generate-scene dark cave", "context": {}}
            )

            assert response.status_code == 200
            data = response.json()
            # Falls back to scene type without image
            assert data["type"] == "scene"
            assert "cave" in data["message"].lower()


def test_chat_endpoint_help_command(client):
    """Test /help command."""
    response = client.post(
        "/api/chat",
        json={"message": "/help", "context": {}}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "commands" in data["message"].lower()
