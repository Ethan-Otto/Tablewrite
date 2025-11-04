"""Tests for image generator tool."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from app.tools.image_generator import ImageGeneratorTool
from app.tools.base import ToolResponse


class TestImageGeneratorTool:
    """Test ImageGeneratorTool."""

    def test_get_schema(self):
        """Test tool schema."""
        tool = ImageGeneratorTool()
        schema = tool.get_schema()

        assert schema.name == "generate_images"
        assert "prompt" in schema.parameters["properties"]
        assert "count" in schema.parameters["properties"]
        assert "prompt" in schema.parameters["required"]

    def test_name_property(self):
        """Test tool name property."""
        tool = ImageGeneratorTool()
        assert tool.name == "generate_images"

    @pytest.mark.anyio
    async def test_execute_caps_count_at_max(self):
        """Test execute caps count at maximum."""
        tool = ImageGeneratorTool()

        with patch.object(tool, '_generate_single_image', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "test.png"

            response = await tool.execute(prompt="test", count=10)

        assert mock_gen.call_count == 4  # Capped at MAX_IMAGES_PER_REQUEST

    @pytest.mark.anyio
    async def test_execute_returns_image_response(self):
        """Test execute returns correct response format."""
        tool = ImageGeneratorTool()

        with patch.object(tool, '_generate_single_image', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "test_123.png"

            response = await tool.execute(prompt="a dragon", count=2)

        assert response.type == "image"
        assert "Generated 2 images" in response.message
        assert len(response.data["image_urls"]) == 2
        assert response.data["prompt"] == "a dragon"
