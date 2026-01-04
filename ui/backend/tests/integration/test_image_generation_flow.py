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


@pytest.mark.integration
@pytest.mark.slow
class TestGenerateSceneWithImage:
    """Test /generate-scene command generates images using real API."""

    def test_generate_scene_creates_image(self):
        """Test /generate-scene actually generates an image using real Gemini API.

        This test uses real API calls to verify the end-to-end workflow:
        1. User sends /generate-scene command
        2. Gemini generates scene description
        3. Image generator creates image using Imagen
        4. Response includes image URL
        """
        # Send /generate-scene command with real API call
        response = client.post("/api/chat", json={
            "message": "/generate-scene a dark cave with glowing mushrooms",
            "context": {},
            "conversation_history": []
        })

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Should return image type with generated image
        assert data["type"] == "image", f"Expected image type, got: {data}"
        assert "image_urls" in data["data"], f"Missing image_urls in: {data}"
        assert len(data["data"]["image_urls"]) >= 1, "Expected at least 1 image URL"

        # Verify image URL format
        image_url = data["data"]["image_urls"][0]
        assert image_url.startswith("/api/images/"), f"Invalid image URL: {image_url}"
        assert image_url.endswith(".png"), f"Invalid image extension: {image_url}"

        # Verify description is in message
        assert "cave" in data["message"].lower() or "mushroom" in data["message"].lower()
