"""Tests for grid detection module."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
class TestDetectGridlines:
    """Test detect_gridlines function with mocked Gemini API."""

    @pytest.mark.smoke
    async def test_detect_gridlines_with_grid(self, tmp_path):
        """Test grid detection returns grid_size when grid is detected."""
        from scenes.detect_gridlines import detect_gridlines
        from scenes.models import GridDetectionResult

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response with grid detected
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "has_grid": True,
            "grid_size": 70,
            "confidence": 0.95
        })

        mock_pil_image = MagicMock()

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_pil_image):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            result = await detect_gridlines(test_image)

            assert isinstance(result, GridDetectionResult)
            assert result.has_grid is True
            assert result.grid_size == 70
            assert result.confidence == 0.95

    async def test_detect_gridlines_no_grid(self, tmp_path):
        """Test grid detection returns has_grid=False when no grid detected."""
        from scenes.detect_gridlines import detect_gridlines
        from scenes.models import GridDetectionResult

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response with no grid
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "has_grid": False,
            "grid_size": None,
            "confidence": 0.85
        })

        mock_pil_image = MagicMock()

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_pil_image):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            result = await detect_gridlines(test_image)

            assert isinstance(result, GridDetectionResult)
            assert result.has_grid is False
            assert result.grid_size is None
            assert result.confidence == 0.85

    async def test_detect_gridlines_handles_markdown_code_blocks(self, tmp_path):
        """Test that markdown code blocks in response are stripped."""
        from scenes.detect_gridlines import detect_gridlines
        from scenes.models import GridDetectionResult

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response with markdown code block wrapper
        mock_response = MagicMock()
        mock_response.text = """```json
{
    "has_grid": true,
    "grid_size": 100,
    "confidence": 0.9
}
```"""

        mock_pil_image = MagicMock()

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_pil_image):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            result = await detect_gridlines(test_image)

            assert isinstance(result, GridDetectionResult)
            assert result.has_grid is True
            assert result.grid_size == 100
            assert result.confidence == 0.9

    async def test_detect_gridlines_handles_json_parse_error(self, tmp_path):
        """Test graceful handling of JSON parse errors returns default no-grid result."""
        from scenes.detect_gridlines import detect_gridlines
        from scenes.models import GridDetectionResult

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON at all!"

        mock_pil_image = MagicMock()

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_pil_image):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            result = await detect_gridlines(test_image)

            # Should return default no-grid result
            assert isinstance(result, GridDetectionResult)
            assert result.has_grid is False
            assert result.grid_size is None
            assert result.confidence == 0.0

    async def test_detect_gridlines_uses_custom_model(self, tmp_path):
        """Test that custom model name is passed to API."""
        from scenes.detect_gridlines import detect_gridlines

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "has_grid": False,
            "grid_size": None,
            "confidence": 0.5
        })

        mock_pil_image = MagicMock()

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_pil_image):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            await detect_gridlines(test_image, model_name="gemini-2.5-pro")

            # Verify the model name was passed correctly
            call_kwargs = mock_client.models.generate_content.call_args
            assert call_kwargs.kwargs.get("model") == "gemini-2.5-pro"

    async def test_detect_gridlines_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing image."""
        from scenes.detect_gridlines import detect_gridlines

        non_existent = tmp_path / "does_not_exist.png"

        with pytest.raises(FileNotFoundError):
            await detect_gridlines(non_existent)

    async def test_detect_gridlines_sends_image_to_api(self, tmp_path):
        """Test that the image is sent to the API."""
        from scenes.detect_gridlines import detect_gridlines

        # Create a dummy image file
        test_image = tmp_path / "test_map.png"
        test_image.write_bytes(b"fake image content")

        # Mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "has_grid": True,
            "grid_size": 50,
            "confidence": 0.8
        })

        # Create mock that works with context manager
        mock_pil_image = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_pil_image)
        mock_context.__exit__ = MagicMock(return_value=False)

        with patch("scenes.detect_gridlines.create_client") as mock_create_client, \
             patch("scenes.detect_gridlines.Image.open", return_value=mock_context):
            mock_client = MagicMock()
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            mock_create_client.return_value = mock_client

            await detect_gridlines(test_image)

            # Verify generate_content was called
            assert mock_client.models.generate_content.called

            # Verify contents include image data (PIL Image object) and prompt text
            call_kwargs = mock_client.models.generate_content.call_args
            contents = call_kwargs.kwargs.get("contents")
            assert contents is not None
            assert len(contents) == 2  # [image, prompt]
            # First item should be the mock PIL image (from context manager)
            assert contents[0] is mock_pil_image


@pytest.mark.unit
class TestStripMarkdownCodeBlock:
    """Test the _strip_markdown_code_block helper function."""

    def test_strip_json_code_block(self):
        """Test stripping ```json ... ``` wrapper."""
        from scenes.detect_gridlines import _strip_markdown_code_block

        input_text = """```json
{"has_grid": true}
```"""
        result = _strip_markdown_code_block(input_text)
        assert result == '{"has_grid": true}'

    def test_strip_plain_code_block(self):
        """Test stripping ``` ... ``` wrapper without language."""
        from scenes.detect_gridlines import _strip_markdown_code_block

        input_text = """```
{"has_grid": false}
```"""
        result = _strip_markdown_code_block(input_text)
        assert result == '{"has_grid": false}'

    def test_no_code_block(self):
        """Test text without code block wrapper is returned as-is."""
        from scenes.detect_gridlines import _strip_markdown_code_block

        input_text = '{"has_grid": true, "grid_size": 50}'
        result = _strip_markdown_code_block(input_text)
        assert result == input_text

    def test_strip_whitespace(self):
        """Test whitespace is stripped."""
        from scenes.detect_gridlines import _strip_markdown_code_block

        input_text = """
{"has_grid": true}
   """
        result = _strip_markdown_code_block(input_text)
        assert result == '{"has_grid": true}'

    def test_multiline_json_preserved(self):
        """Test multiline JSON content is preserved."""
        from scenes.detect_gridlines import _strip_markdown_code_block

        input_text = """```json
{
    "has_grid": true,
    "grid_size": 70,
    "confidence": 0.95
}
```"""
        result = _strip_markdown_code_block(input_text)
        # Content should preserve internal newlines
        assert '"has_grid": true' in result
        assert '"grid_size": 70' in result
        assert '"confidence": 0.95' in result
