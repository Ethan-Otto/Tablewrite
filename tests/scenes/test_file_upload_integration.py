"""Integration tests for file upload to FoundryVTT.

These tests verify that files can be uploaded to FoundryVTT and that the
round-trip works correctly. This is a prerequisite for scene creation
which requires uploading map images.
"""

import pytest
import tempfile
import os
import uuid
from pathlib import Path
from PIL import Image

from foundry.client import FoundryClient


@pytest.mark.foundry
class TestFileUploadRoundtrip:
    """
    Integration tests for file upload to FoundryVTT.

    These tests require:
    - Backend server running at localhost:8000
    - FoundryVTT connected to backend via WebSocket
    """

    @pytest.fixture
    def client(self):
        """Create FoundryVTT client for testing."""
        return FoundryClient()

    @pytest.fixture
    def unique_test_image(self, tmp_path):
        """Create a unique test image with random content to avoid caching issues."""
        # Use UUID in filename to ensure uniqueness
        unique_id = uuid.uuid4().hex[:8]
        image_path = tmp_path / f"test_upload_{unique_id}.png"

        # Create a simple test image with unique color
        img = Image.new('RGB', (100, 100), color='red')
        # Add some variation to make it unique
        img.putpixel((50, 50), (0, 255, 0))
        img.save(image_path)

        return image_path

    def test_file_upload_roundtrip(self, client, unique_test_image):
        """
        Upload file to Foundry and verify it succeeds.

        This test:
        1. Checks Foundry connection (FAILs if not connected)
        2. Creates a unique test image
        3. Uploads to uploaded-maps/tests destination
        4. Verifies success response and path
        """
        # FAIL if not connected - don't skip
        assert client.is_connected(), (
            "Foundry not connected - start backend (cd ui/backend && uvicorn app.main:app --reload) "
            "and connect Foundry module"
        )

        # Upload to tests subfolder
        result = client.files.upload_file(
            local_path=unique_test_image,
            destination="uploaded-maps/tests"
        )

        # Verify success
        assert result.get("success") is True, f"Upload failed: {result.get('error')}"
        assert "path" in result, f"Response missing 'path' field: {result}"
        assert result["path"].endswith(".png"), f"Unexpected path format: {result['path']}"
        assert "test_upload_" in result["path"], f"Filename not preserved: {result['path']}"

    def test_file_upload_with_webp(self, client, tmp_path):
        """Test uploading a WebP image (common format for maps)."""
        # FAIL if not connected
        assert client.is_connected(), (
            "Foundry not connected - start backend and connect Foundry module"
        )

        # Create WebP test image
        unique_id = uuid.uuid4().hex[:8]
        image_path = tmp_path / f"test_map_{unique_id}.webp"
        img = Image.new('RGB', (200, 200), color='blue')
        img.save(image_path, format='WEBP')

        result = client.files.upload_file(
            local_path=image_path,
            destination="uploaded-maps/tests"
        )

        assert result.get("success") is True, f"WebP upload failed: {result.get('error')}"
        assert result["path"].endswith(".webp")

    def test_file_upload_path_format(self, client, unique_test_image):
        """Verify the returned path is in Foundry-compatible format."""
        # FAIL if not connected
        assert client.is_connected(), (
            "Foundry not connected - start backend and connect Foundry module"
        )

        result = client.files.upload_file(
            local_path=unique_test_image,
            destination="uploaded-maps/tests"
        )

        assert result.get("success") is True, f"Upload failed: {result.get('error')}"

        # Path should be relative to Foundry data folder
        # Format: worlds/<world-name>/uploaded-maps/tests/<filename>
        path = result["path"]
        assert "uploaded-maps/tests" in path, f"Path missing destination folder: {path}"
        # Path should start with worlds/ (Foundry world folder structure)
        assert path.startswith("worlds/"), f"Path not in worlds/ format: {path}"

    def test_file_upload_preserves_filename(self, client, tmp_path):
        """Verify filename is preserved in the uploaded path."""
        # FAIL if not connected
        assert client.is_connected(), (
            "Foundry not connected - start backend and connect Foundry module"
        )

        # Create image with specific filename
        unique_id = uuid.uuid4().hex[:8]
        specific_name = f"goblin_cave_map_{unique_id}.png"
        image_path = tmp_path / specific_name
        img = Image.new('RGB', (100, 100), color='green')
        img.save(image_path)

        result = client.files.upload_file(
            local_path=image_path,
            destination="uploaded-maps/tests"
        )

        assert result.get("success") is True, f"Upload failed: {result.get('error')}"
        assert specific_name in result["path"], f"Filename not preserved: expected '{specific_name}' in '{result['path']}'"
