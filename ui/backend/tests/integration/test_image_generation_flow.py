"""Integration test for complete image generation flow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


@pytest.mark.integration
class TestImageGenerationFlow:
    """Test complete image generation workflow."""

    def test_full_image_generation_flow(self):
        """Test end-to-end image generation."""
        # Mock Gemini service's generate_with_tools method
        with patch('app.routers.chat.gemini_service.generate_with_tools', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                "type": "tool_call",
                "tool_call": {
                    "name": "generate_images",
                    "parameters": {"prompt": "a majestic dragon", "count": 2}
                },
                "text": None
            }

            # Send chat message
            response = client.post("/api/chat", json={
                "message": "Show me a majestic dragon",
                "context": {},
                "conversation_history": []
            })

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
        assert "Generated 2 images" in data["message"]
        assert len(data["data"]["image_urls"]) == 2
        assert data["data"]["prompt"] == "a majestic dragon"

        # Verify image URLs are correct format
        for url in data["data"]["image_urls"]:
            assert url.startswith("/api/images/")
            assert url.endswith(".png")
