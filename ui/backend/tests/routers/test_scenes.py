"""Tests for scenes router - scene creation endpoint.

Run with: pytest ui/backend/tests/routers/test_scenes.py -v
Run integration only: pytest ui/backend/tests/routers/test_scenes.py -v -m integration
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


BACKEND_URL = "http://localhost:8000"


@pytest.mark.unit
class TestCreateSceneEndpointUnit:
    """Unit tests for POST /api/foundry/scene with mocked WebSocket."""

    def test_create_scene_endpoint_success(self):
        """POST /api/foundry/scene creates scene via WebSocket."""
        mock_result = type('MockResult', (), {
            'success': True,
            'uuid': 'Scene.abc123',
            'name': 'Castle',
            'error': None
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {
                        "name": "Castle",
                        "width": 1400,
                        "height": 1000,
                        "grid": {"size": 70, "type": 1},
                        "walls": [{"c": [0, 0, 100, 100]}]
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["uuid"] == "Scene.abc123"
            assert data["name"] == "Castle"

            # Verify push_scene was called with correct args
            mock_push.assert_called_once()
            call_args = mock_push.call_args
            scene_data = call_args[0][0]
            assert scene_data["name"] == "Castle"
            assert scene_data["width"] == 1400
            assert scene_data["height"] == 1000

    def test_create_scene_endpoint_minimal(self):
        """POST /api/foundry/scene works with just name."""
        mock_result = type('MockResult', (), {
            'success': True,
            'uuid': 'Scene.def456',
            'name': 'Cave',
            'error': None
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {"name": "Cave"}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["uuid"] == "Scene.def456"

    def test_create_scene_endpoint_with_walls(self):
        """POST /api/foundry/scene includes walls in payload."""
        walls = [
            {"c": [0, 0, 100, 100], "move": 0, "sense": 0},
            {"c": [100, 100, 200, 200], "move": 0, "sense": 0, "door": 1}
        ]

        mock_result = type('MockResult', (), {
            'success': True,
            'uuid': 'Scene.ghi789',
            'name': 'Dungeon',
            'error': None
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {
                        "name": "Dungeon",
                        "walls": walls
                    }
                }
            )

            assert response.status_code == 200
            call_args = mock_push.call_args
            scene_data = call_args[0][0]
            assert scene_data["walls"] == walls

    def test_create_scene_endpoint_with_background(self):
        """POST /api/foundry/scene includes background image."""
        mock_result = type('MockResult', (), {
            'success': True,
            'uuid': 'Scene.jkl012',
            'name': 'Forest',
            'error': None
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {
                        "name": "Forest",
                        "background": {"src": "worlds/test/maps/forest.webp"}
                    }
                }
            )

            assert response.status_code == 200
            call_args = mock_push.call_args
            scene_data = call_args[0][0]
            assert scene_data["background"]["src"] == "worlds/test/maps/forest.webp"

    def test_create_scene_endpoint_returns_503_when_not_connected(self):
        """POST /api/foundry/scene returns 503 when Foundry not connected."""
        mock_result = type('MockResult', (), {
            'success': False,
            'uuid': None,
            'name': None,
            'error': 'No Foundry client connected or timeout waiting for response'
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {"name": "Test"}
                }
            )

            assert response.status_code == 503
            data = response.json()
            detail_lower = data["detail"].lower()
            assert "connected" in detail_lower or "timeout" in detail_lower

    def test_create_scene_endpoint_returns_500_on_other_errors(self):
        """POST /api/foundry/scene returns 500 on non-connection errors."""
        mock_result = type('MockResult', (), {
            'success': False,
            'uuid': None,
            'name': None,
            'error': 'Failed to create scene: invalid data'
        })()

        with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
            mock_push.return_value = mock_result

            response = client.post(
                "/api/foundry/scene",
                json={
                    "scene": {"name": "Test"}
                }
            )

            assert response.status_code == 500
            data = response.json()
            assert "Failed to create scene" in data["detail"]

    def test_create_scene_endpoint_missing_scene_key(self):
        """POST /api/foundry/scene returns 422 without scene key."""
        response = client.post(
            "/api/foundry/scene",
            json={}
        )

        assert response.status_code == 422

    def test_create_scene_endpoint_invalid_json(self):
        """POST /api/foundry/scene returns 422 for invalid JSON."""
        response = client.post(
            "/api/foundry/scene",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestCreateSceneEndpointIntegration:
    """Integration tests for POST /api/foundry/scene (requires Foundry)."""

    @pytest.mark.asyncio
    async def test_foundry_connected_before_scene_tests(self):
        """Verify Foundry is connected before running scene tests."""
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(f"{BACKEND_URL}/api/foundry/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected", f"Foundry not connected: {data}"
        assert data["connected_clients"] > 0

    @pytest.mark.asyncio
    async def test_create_scene_via_rest_endpoint_real(self):
        """
        Create a scene via REST endpoint and verify UUID returned.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First check connection
            status = await http_client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.fail("Foundry not connected - start backend and connect Foundry module")

            # Create scene via REST endpoint
            response = await http_client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": "Test Scene - REST Integration",
                        "width": 1000,
                        "height": 800,
                        "grid": {"size": 50, "type": 1},
                        "folder": "tests"
                    }
                }
            )

        assert response.status_code == 200, f"Scene creation failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["uuid"] is not None
        assert data["uuid"].startswith("Scene.")
        print(f"\n[INTEGRATION] Created scene via REST: {data['uuid']}")

    @pytest.mark.asyncio
    async def test_create_scene_with_walls_real(self):
        """
        Create a scene with walls via REST endpoint.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        walls = [
            {"c": [0, 0, 100, 0], "move": 0, "sense": 0},
            {"c": [100, 0, 100, 100], "move": 0, "sense": 0},
            {"c": [100, 100, 0, 100], "move": 0, "sense": 0},
            {"c": [0, 100, 0, 0], "move": 0, "sense": 0}
        ]

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First check connection
            status = await http_client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.fail("Foundry not connected - start backend and connect Foundry module")

            # Create scene with walls
            response = await http_client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": "Test Scene - Walls Integration",
                        "width": 500,
                        "height": 500,
                        "grid": {"size": 50, "type": 1},
                        "walls": walls,
                        "folder": "tests"
                    }
                }
            )

        assert response.status_code == 200, f"Scene creation failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["uuid"] is not None
        print(f"\n[INTEGRATION] Created scene with walls: {data['uuid']}")
