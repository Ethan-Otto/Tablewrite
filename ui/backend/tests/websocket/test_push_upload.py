"""Tests for upload_file WebSocket push function.

Run with: pytest ui/backend/tests/websocket/test_push_upload.py -v
Run integration only: pytest ui/backend/tests/websocket/test_push_upload.py -v -m integration
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.websocket.push import upload_file


BACKEND_URL = "http://localhost:8000"


@pytest.mark.unit
class TestUploadFileUnit:
    """Unit tests for upload_file with mocked WebSocket."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """upload_file returns path on success."""
        mock_response = {
            "type": "file_uploaded",
            "data": {"path": "worlds/test/uploaded-maps/castle.webp"}
        }

        with patch('app.websocket.push.foundry_manager') as mock_mgr:
            mock_mgr.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await upload_file(
                filename="castle.webp",
                content="dGVzdA==",  # base64 "test"
                destination="uploaded-maps"
            )

            assert result.success
            assert result.path == "worlds/test/uploaded-maps/castle.webp"

    @pytest.mark.asyncio
    async def test_upload_file_error_response(self):
        """upload_file handles error response from Foundry."""
        mock_response = {
            "type": "file_error",
            "error": "Disk full"
        }

        with patch('app.websocket.push.foundry_manager') as mock_mgr:
            mock_mgr.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await upload_file(
                filename="castle.webp",
                content="dGVzdA==",
                destination="uploaded-maps"
            )

            assert not result.success
            assert result.error == "Disk full"

    @pytest.mark.asyncio
    async def test_upload_file_timeout(self):
        """upload_file handles timeout (no response)."""
        with patch('app.websocket.push.foundry_manager') as mock_mgr:
            mock_mgr.broadcast_and_wait = AsyncMock(return_value=None)

            result = await upload_file(
                filename="castle.webp",
                content="dGVzdA==",
                destination="uploaded-maps"
            )

            assert not result.success
            assert "No Foundry client connected" in result.error

    @pytest.mark.asyncio
    async def test_upload_file_unexpected_response_type(self):
        """upload_file handles unexpected response type."""
        mock_response = {
            "type": "something_unexpected",
            "data": {}
        }

        with patch('app.websocket.push.foundry_manager') as mock_mgr:
            mock_mgr.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await upload_file(
                filename="castle.webp",
                content="dGVzdA==",
                destination="uploaded-maps"
            )

            assert not result.success
            assert "Unexpected response type" in result.error


@pytest.mark.integration
class TestUploadFileIntegration:
    """Integration tests for upload_file (requires Foundry connection)."""

    @pytest.mark.asyncio
    async def test_foundry_connected_before_upload(self):
        """Verify Foundry is connected before running upload tests."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/api/foundry/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected", f"Foundry not connected: {data}"
        assert data["connected_clients"] > 0

    @pytest.mark.asyncio
    async def test_upload_file_real(self):
        """
        Upload a file to Foundry and verify it was created.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        import base64

        async with httpx.AsyncClient(timeout=30.0) as client:
            # First check connection
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.fail("Foundry not connected - start backend and connect Foundry module")

        # Create minimal test content (a tiny PNG)
        # 1x1 red PNG pixel
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
        content = base64.b64encode(test_png).decode()

        result = await upload_file(
            filename="test_upload_integration.png",
            content=content,
            destination="uploaded-maps/tests"
        )

        assert result.success, f"Upload failed: {result.error}"
        assert result.path is not None
        assert "test_upload_integration.png" in result.path
        print(f"\n[INTEGRATION] Uploaded file to: {result.path}")
