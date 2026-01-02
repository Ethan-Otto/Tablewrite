"""Unit tests for upload_file WebSocket push function."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_upload_file_success():
    """upload_file returns path on success."""
    from app.websocket.push import upload_file

    mock_response = {
        "type": "file_uploaded",
        "data": {"success": True, "path": "worlds/test/uploaded-maps/castle.webp"}
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
async def test_upload_file_error_response():
    """upload_file handles error response from Foundry."""
    from app.websocket.push import upload_file

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
async def test_upload_file_timeout():
    """upload_file handles timeout (no response)."""
    from app.websocket.push import upload_file

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
async def test_upload_file_unexpected_response_type():
    """upload_file handles unexpected response type."""
    from app.websocket.push import upload_file

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
