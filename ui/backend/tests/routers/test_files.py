"""Tests for files router - file upload endpoint.

Run with: pytest ui/backend/tests/routers/test_files.py -v
Run integration only: pytest ui/backend/tests/routers/test_files.py -v -m integration
"""
import pytest
import base64
import httpx
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


BACKEND_URL = "http://localhost:8000"


@pytest.mark.unit
class TestUploadFileEndpointUnit:
    """Unit tests for POST /api/foundry/files/upload with mocked WebSocket."""

    def test_upload_file_endpoint_success(self):
        """POST /api/foundry/files/upload returns path on success."""
        mock_result = type('MockResult', (), {
            'success': True,
            'path': 'worlds/test/uploaded-maps/castle.webp',
            'error': None
        })()

        with patch('app.routers.files.upload_file', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_result

            # Create minimal file content
            file_content = b"fake image data"

            response = client.post(
                "/api/foundry/files/upload",
                files={"file": ("castle.webp", file_content, "image/webp")},
                data={"destination": "uploaded-maps"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["path"] == "worlds/test/uploaded-maps/castle.webp"

            # Verify upload_file was called with correct args
            mock_upload.assert_called_once()
            call_kwargs = mock_upload.call_args.kwargs
            assert call_kwargs["filename"] == "castle.webp"
            assert call_kwargs["destination"] == "uploaded-maps"
            # Content should be base64-encoded
            expected_b64 = base64.b64encode(file_content).decode('utf-8')
            assert call_kwargs["content"] == expected_b64

    def test_upload_file_endpoint_uses_default_destination(self):
        """POST /api/foundry/files/upload uses default destination when not provided."""
        mock_result = type('MockResult', (), {
            'success': True,
            'path': 'worlds/test/uploaded-maps/test.png',
            'error': None
        })()

        with patch('app.routers.files.upload_file', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_result

            response = client.post(
                "/api/foundry/files/upload",
                files={"file": ("test.png", b"test", "image/png")}
                # No destination provided
            )

            assert response.status_code == 200
            call_kwargs = mock_upload.call_args.kwargs
            assert call_kwargs["destination"] == "uploaded-maps"

    def test_upload_file_endpoint_error_returns_500(self):
        """POST /api/foundry/files/upload returns 500 on upload error."""
        mock_result = type('MockResult', (), {
            'success': False,
            'path': None,
            'error': 'Foundry client not connected'
        })()

        with patch('app.routers.files.upload_file', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_result

            response = client.post(
                "/api/foundry/files/upload",
                files={"file": ("castle.webp", b"data", "image/webp")},
                data={"destination": "uploaded-maps"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "Foundry client not connected" in data["detail"]

    def test_upload_file_endpoint_missing_file(self):
        """POST /api/foundry/files/upload returns 422 without file."""
        response = client.post(
            "/api/foundry/files/upload",
            data={"destination": "uploaded-maps"}
            # No file provided
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestUploadFileEndpointIntegration:
    """Integration tests for POST /api/foundry/files/upload (requires Foundry)."""

    @pytest.mark.asyncio
    async def test_foundry_connected_before_upload(self):
        """Verify Foundry is connected before running upload tests."""
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(f"{BACKEND_URL}/api/foundry/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected", f"Foundry not connected: {data}"
        assert data["connected_clients"] > 0

    @pytest.mark.asyncio
    async def test_upload_file_via_rest_endpoint_real(self):
        """
        Upload a file via REST endpoint and verify it was created in Foundry.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # 1x1 red PNG pixel (minimal valid PNG)
        test_png = bytes([
            0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,  # PNG signature
            0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xde, 0x00, 0x00, 0x00, 0x0c, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xfe,
            0xd4, 0xef, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,
            0x4e, 0x44, 0xae, 0x42, 0x60, 0x82
        ])

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First check connection
            status = await http_client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.fail("Foundry not connected - start backend and connect Foundry module")

            # Upload via REST endpoint
            response = await http_client.post(
                f"{BACKEND_URL}/api/foundry/files/upload",
                files={"file": ("test_rest_upload.png", test_png, "image/png")},
                data={"destination": "uploaded-maps/tests"}
            )

        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["path"] is not None
        assert "test_rest_upload.png" in data["path"]
        print(f"\n[INTEGRATION] Uploaded file via REST to: {data['path']}")
