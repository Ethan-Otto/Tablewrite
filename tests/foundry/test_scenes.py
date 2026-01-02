"""Tests for SceneManager - scene operations via WebSocket backend."""

import pytest
from unittest.mock import patch, MagicMock


class TestSceneManagerInit:
    """Tests for SceneManager initialization."""

    def test_scene_manager_initialization(self):
        """Test SceneManager initializes with backend URL."""
        from foundry.scenes import SceneManager

        manager = SceneManager(backend_url="http://localhost:8000")

        assert manager.backend_url == "http://localhost:8000"

    def test_scene_manager_initialization_custom_url(self):
        """Test SceneManager initializes with custom backend URL."""
        from foundry.scenes import SceneManager

        manager = SceneManager(backend_url="https://custom.example.com")

        assert manager.backend_url == "https://custom.example.com"


@pytest.mark.unit
class TestSceneManagerCreateScene:
    """Tests for SceneManager.create_scene method."""

    @pytest.fixture
    def manager(self):
        """Create a SceneManager instance."""
        from foundry.scenes import SceneManager
        return SceneManager(backend_url="http://localhost:8000")

    def test_create_scene_basic(self, manager):
        """SceneManager.create_scene sends scene data to backend."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Castle"}
            )

            result = manager.create_scene(
                name="Castle",
                background_image="worlds/test/uploaded-maps/castle.webp",
                width=1400,
                height=1000,
                grid_size=70,
                walls=[{"c": [0, 0, 100, 100], "move": 0, "sense": 0}]
            )

            assert result["success"] is True
            assert result["uuid"] == "Scene.abc123"
            assert result["name"] == "Castle"
            mock_post.assert_called_once()

    def test_create_scene_minimal(self, manager):
        """SceneManager.create_scene works with just name."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.def456", "name": "Cave"}
            )

            result = manager.create_scene(name="Cave")

            assert result["success"] is True
            assert result["uuid"] == "Scene.def456"

    def test_create_scene_correct_endpoint(self, manager):
        """SceneManager.create_scene calls correct endpoint."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Test"}
            )

            manager.create_scene(name="Test")

            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:8000/api/foundry/scene"

    def test_create_scene_payload_structure(self, manager):
        """SceneManager.create_scene sends correct payload structure."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Castle"}
            )

            manager.create_scene(
                name="Castle",
                background_image="worlds/test/maps/castle.webp",
                width=1400,
                height=1000,
                grid_size=70
            )

            call_args = mock_post.call_args
            payload = call_args[1]['json']

            assert 'scene' in payload
            scene_data = payload['scene']
            assert scene_data['name'] == "Castle"
            assert scene_data['width'] == 1400
            assert scene_data['height'] == 1000
            assert scene_data['background'] == {"src": "worlds/test/maps/castle.webp"}
            assert scene_data['grid'] == {"size": 70, "type": 1}

    def test_create_scene_with_walls(self, manager):
        """SceneManager.create_scene includes walls in payload."""
        walls = [
            {"c": [0, 0, 100, 100], "move": 0, "sense": 0},
            {"c": [100, 100, 200, 200], "move": 0, "sense": 0, "door": 1}
        ]

        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Dungeon"}
            )

            manager.create_scene(name="Dungeon", walls=walls)

            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['scene']['walls'] == walls

    def test_create_scene_with_folder(self, manager):
        """SceneManager.create_scene includes folder in payload."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Test"}
            )

            manager.create_scene(name="Test", folder="tests")

            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['scene']['folder'] == "tests"

    def test_create_scene_gridless(self, manager):
        """SceneManager.create_scene supports gridless (grid_size=None)."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Theater"}
            )

            manager.create_scene(name="Theater", grid_size=None)

            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert 'grid' not in payload['scene']

    def test_create_scene_default_dimensions(self, manager):
        """SceneManager.create_scene uses default dimensions."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Default"}
            )

            manager.create_scene(name="Default")

            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['scene']['width'] == 3000
            assert payload['scene']['height'] == 2000

    def test_create_scene_server_error(self, manager):
        """SceneManager.create_scene handles server errors."""
        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                json=lambda: {"detail": "Internal server error"}
            )

            result = manager.create_scene(name="ErrorTest")

            assert result["success"] is False
            assert "Internal server error" in result["error"]

    def test_create_scene_network_error(self, manager):
        """SceneManager.create_scene handles network errors."""
        import requests

        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = manager.create_scene(name="NetworkTest")

            assert result["success"] is False
            assert "Connection refused" in result["error"]

    def test_create_scene_timeout(self, manager):
        """SceneManager.create_scene handles timeout errors."""
        import requests

        with patch('foundry.scenes.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = manager.create_scene(name="TimeoutTest")

            assert result["success"] is False
            assert "timed out" in result["error"].lower()


@pytest.mark.unit
class TestSceneManagerSearch:
    """Tests for SceneManager search methods."""

    @pytest.fixture
    def manager(self):
        """Create a SceneManager instance."""
        from foundry.scenes import SceneManager
        return SceneManager(backend_url="http://localhost:8000")

    def test_search_scenes_returns_results(self, manager):
        """SceneManager.search_scenes returns matching scenes."""
        with patch('foundry.scenes.requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "results": [
                        {"name": "Castle", "uuid": "Scene.abc"},
                        {"name": "Castle Dungeon", "uuid": "Scene.def"}
                    ]
                }
            )

            results = manager.search_scenes("Castle")

            assert len(results) == 2
            assert results[0]["name"] == "Castle"

    def test_get_scene_by_name_exact_match(self, manager):
        """SceneManager.get_scene_by_name returns exact match."""
        with patch('foundry.scenes.requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "results": [
                        {"name": "Castle", "uuid": "Scene.abc"},
                        {"name": "Castle Dungeon", "uuid": "Scene.def"}
                    ]
                }
            )

            result = manager.get_scene_by_name("Castle")

            assert result is not None
            assert result["name"] == "Castle"
            assert result["uuid"] == "Scene.abc"


@pytest.mark.unit
class TestFoundryClientSceneManager:
    """Tests for SceneManager integration with FoundryClient."""

    def test_foundry_client_has_scenes_manager(self, monkeypatch):
        """Test FoundryClient has scenes manager."""
        from foundry.client import FoundryClient
        from foundry.scenes import SceneManager

        monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
        client = FoundryClient()

        assert hasattr(client, 'scenes')
        assert isinstance(client.scenes, SceneManager)

    def test_foundry_client_scenes_manager_uses_backend_url(self, monkeypatch):
        """Test SceneManager uses same backend URL as client."""
        from foundry.client import FoundryClient

        monkeypatch.setenv("BACKEND_URL", "http://custom:9000")
        client = FoundryClient()

        assert client.scenes.backend_url == "http://custom:9000"


@pytest.mark.integration
@pytest.mark.slow
class TestSceneManagerIntegration:
    """Integration tests for scene creation (requires running backend + Foundry)."""

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

    def test_create_scene_roundtrip(self, require_websocket):
        """Integration test: Create scene in Foundry and verify UUID returned."""
        from foundry.scenes import SceneManager

        manager = SceneManager(backend_url=self.BACKEND_URL)

        result = manager.create_scene(
            name="Test Scene - Integration",
            width=1000,
            height=800,
            grid_size=50,
            folder="tests"
        )

        assert result["success"] is True, f"Create scene failed: {result.get('error')}"
        assert "uuid" in result
        assert result["uuid"].startswith("Scene.")
