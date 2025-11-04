"""Tests for main app endpoints."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
from app.config import settings


client = TestClient(app)


class TestImageServing:
    """Test image serving endpoint."""

    def test_serve_existing_image(self, tmp_path):
        """Test serving an existing image."""
        # Create test image
        test_image = settings.IMAGE_OUTPUT_DIR / "test_image.png"
        test_image.parent.mkdir(parents=True, exist_ok=True)
        test_image.write_bytes(b"fake image data")

        try:
            response = client.get("/api/images/test_image.png")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == b"fake image data"
        finally:
            test_image.unlink()

    def test_serve_nonexistent_image(self):
        """Test serving nonexistent image returns 404."""
        response = client.get("/api/images/nonexistent.png")
        assert response.status_code == 404

    def test_serve_image_path_traversal_blocked(self):
        """Test path traversal attempts are blocked."""
        response = client.get("/api/images/../../../etc/passwd")
        assert response.status_code in [400, 404]
