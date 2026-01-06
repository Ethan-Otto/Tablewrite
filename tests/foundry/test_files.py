"""Tests for FileManager - file upload operations via WebSocket backend."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


class TestFileManagerInit:
    """Tests for FileManager initialization."""

    def test_file_manager_initialization(self):
        """Test FileManager initializes with backend URL."""
        from foundry.files import FileManager

        manager = FileManager(backend_url="http://localhost:8000")

        assert manager.backend_url == "http://localhost:8000"

    def test_file_manager_initialization_custom_url(self):
        """Test FileManager initializes with custom backend URL."""
        from foundry.files import FileManager

        manager = FileManager(backend_url="https://custom.example.com")

        assert manager.backend_url == "https://custom.example.com"


@pytest.mark.unit
class TestFileManagerUpload:
    """Tests for FileManager.upload_file method."""

    @pytest.fixture
    def manager(self):
        """Create a FileManager instance."""
        from foundry.files import FileManager
        return FileManager(backend_url="http://localhost:8000")

    def test_upload_file_success(self, manager, tmp_path):
        """FileManager.upload_file sends file to backend and returns result."""
        # Create a real test file
        test_file = tmp_path / "test_image.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)  # Minimal PNG header

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "path": "worlds/test/uploaded-maps/test_image.png"}
            )

            result = manager.upload_file(
                local_path=test_file,
                destination="uploaded-maps"
            )

            assert result["success"] is True
            assert result["path"] == "worlds/test/uploaded-maps/test_image.png"
            mock_post.assert_called_once()

            # Verify correct endpoint
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:8000/api/foundry/files/upload"

    def test_upload_file_with_custom_destination(self, manager, tmp_path):
        """FileManager.upload_file uses custom destination folder."""
        test_file = tmp_path / "map.webp"
        test_file.write_bytes(b'RIFF' + b'\x00' * 100)  # Minimal WEBP header

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "path": "worlds/test/battle-maps/map.webp"}
            )

            result = manager.upload_file(
                local_path=test_file,
                destination="battle-maps"
            )

            assert result["success"] is True
            assert "battle-maps" in result["path"]

            # Verify destination was passed
            call_args = mock_post.call_args
            assert call_args[1]['data']['destination'] == "battle-maps"

    def test_upload_file_default_destination(self, manager, tmp_path):
        """FileManager.upload_file uses default 'uploaded-maps' destination."""
        test_file = tmp_path / "map.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "path": "worlds/test/uploaded-maps/map.png"}
            )

            result = manager.upload_file(local_path=test_file)

            # Verify default destination
            call_args = mock_post.call_args
            assert call_args[1]['data']['destination'] == "uploaded-maps"

    def test_upload_file_not_found(self, manager):
        """FileManager.upload_file returns error for non-existent file."""
        result = manager.upload_file(
            local_path=Path("/nonexistent/path/image.png"),
            destination="uploaded-maps"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_upload_file_server_error(self, manager, tmp_path):
        """FileManager.upload_file handles server errors."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n')

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                json=lambda: {"error": "Internal server error"}
            )

            result = manager.upload_file(local_path=test_file)

            assert result["success"] is False
            assert "500" in result["error"]

    def test_upload_file_network_error(self, manager, tmp_path):
        """FileManager.upload_file handles network errors."""
        import requests

        test_file = tmp_path / "test.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n')

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = manager.upload_file(local_path=test_file)

            assert result["success"] is False
            assert "Connection refused" in result["error"]

    def test_upload_file_timeout(self, manager, tmp_path):
        """FileManager.upload_file handles timeout errors."""
        import requests

        test_file = tmp_path / "test.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n')

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = manager.upload_file(local_path=test_file)

            assert result["success"] is False
            assert "timed out" in result["error"].lower()

    def test_upload_file_passes_correct_file_data(self, manager, tmp_path):
        """FileManager.upload_file sends correct file name and data."""
        test_file = tmp_path / "castle_map.webp"
        file_content = b'RIFF' + b'\x00' * 100
        test_file.write_bytes(file_content)

        with patch('foundry.files.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "path": "worlds/test/uploaded-maps/castle_map.webp"}
            )

            result = manager.upload_file(local_path=test_file)

            # Verify file was passed with correct name
            call_args = mock_post.call_args
            files_arg = call_args[1]['files']
            assert 'file' in files_arg
            assert files_arg['file'][0] == "castle_map.webp"


@pytest.mark.unit
class TestFoundryClientFileManager:
    """Tests for FileManager integration with FoundryClient."""

    def test_foundry_client_has_files_manager(self, monkeypatch):
        """Test FoundryClient has files manager."""
        from foundry.client import FoundryClient
        from foundry.files import FileManager

        monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
        client = FoundryClient()

        assert hasattr(client, 'files')
        assert isinstance(client.files, FileManager)

    def test_foundry_client_files_manager_uses_backend_url(self, monkeypatch):
        """Test FileManager uses same backend URL as client."""
        from foundry.client import FoundryClient

        monkeypatch.setenv("BACKEND_URL", "http://custom:9000")
        client = FoundryClient()

        assert client.files.backend_url == "http://custom:9000"


@pytest.mark.integration
@pytest.mark.slow
class TestFileManagerIntegration:
    """Integration tests for file upload (requires running backend + Foundry)."""

    BACKEND_URL = "http://localhost:8000"

    @pytest.fixture
    def require_websocket(self):
        """Ensure backend is running and Foundry is connected via WebSocket."""
        import httpx

        # Check backend health
        try:
            response = httpx.get(f"{self.BACKEND_URL}/health", timeout=5.0)
            if response.status_code != 200:
                pytest.fail("Backend not healthy")
        except httpx.ConnectError:
            pytest.fail("Backend not running on localhost:8000")

        # Check Foundry WebSocket connection
        try:
            response = httpx.get(f"{self.BACKEND_URL}/api/foundry/status", timeout=5.0)
            if response.json().get("status") != "connected":
                pytest.fail("Foundry not connected to backend via WebSocket")
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            pytest.fail(f"Failed to check Foundry status: {e}")

        return True

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image file."""
        from PIL import Image

        img = Image.new('RGB', (100, 100), color='red')
        image_path = tmp_path / "test_upload.png"
        img.save(image_path)
        return image_path

    def test_upload_file_roundtrip(self, require_websocket, test_image):
        """Integration test: Upload file to Foundry and verify path returned."""
        from foundry.files import FileManager

        manager = FileManager(backend_url=self.BACKEND_URL)

        result = manager.upload_file(
            local_path=test_image,
            destination="uploaded-maps/tests"
        )

        assert result["success"] is True, f"Upload failed: {result.get('error')}"
        assert "path" in result
        assert "test_upload.png" in result["path"]
