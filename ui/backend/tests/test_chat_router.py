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
    """Test /generate-scene command."""
    with patch('app.routers.chat.GeminiService') as mock_service:
        mock_instance = Mock()
        mock_instance.generate_scene_description.return_value = "A dark cave entrance"
        mock_service.return_value = mock_instance

        response = client.post(
            "/api/chat",
            json={"message": "/generate-scene dark cave", "context": {}}
        )

        assert response.status_code == 200
        data = response.json()
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
