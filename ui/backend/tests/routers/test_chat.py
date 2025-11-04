"""Tests for chat router with tools."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestChatWithTools:
    """Test chat endpoint with tool support."""

    def test_chat_text_response(self):
        """Test chat returns text response when no tool called."""
        with patch('app.routers.chat.gemini_service') as mock_service:
            mock_service.generate_with_tools = AsyncMock(return_value={
                "type": "text",
                "text": "Hello there!",
                "tool_call": None
            })

            response = client.post("/api/chat", json={
                "message": "Hello",
                "context": {},
                "conversation_history": []
            })

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "text"
        assert data["message"] == "Hello there!"

    def test_chat_tool_response(self):
        """Test chat executes tool when called."""
        with patch('app.routers.chat.gemini_service') as mock_service, \
             patch('app.routers.chat.registry') as mock_registry:

            mock_service.generate_with_tools = AsyncMock(return_value={
                "type": "tool_call",
                "tool_call": {
                    "name": "generate_images",
                    "parameters": {"prompt": "dragon", "count": 2}
                },
                "text": None
            })

            mock_registry.execute_tool = AsyncMock(return_value=type('obj', (object,), {
                'type': 'image',
                'message': 'Generated 2 images',
                'data': {'image_urls': ['/api/images/test.png']}
            })())

            response = client.post("/api/chat", json={
                "message": "Show me a dragon",
                "context": {},
                "conversation_history": []
            })

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
        assert "Generated 2 images" in data["message"]
