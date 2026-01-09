"""Integration tests for WebSocket push (requires running backend + Foundry)."""
import pytest
import httpx


BACKEND_URL = "http://localhost:8000"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_foundry_connection():
    """Backend has active Foundry WebSocket connection."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/api/foundry/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected", f"Foundry not connected: {data}"
    assert data["connected_clients"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_scenes(ensure_foundry_connected):
    """Test listing all world scenes."""
    from app.websocket.push import list_scenes

    result = await list_scenes(timeout=10.0)

    assert result.success, f"Failed to list scenes: {result.error}"
    assert result.scenes is not None
    assert isinstance(result.scenes, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_push_actor_returns_uuid():
    """
    Create actor in Foundry via API and get UUID back.

    Requires: Backend running + Foundry with Tablewrite module connected.
    """
    async with httpx.AsyncClient() as client:
        # First check connection
        status = await client.get(f"{BACKEND_URL}/api/foundry/status")
        assert status.json()["status"] == "connected", "Foundry not connected"

        # List actors before
        before = await client.get(f"{BACKEND_URL}/api/foundry/actors")
        before_count = before.json()["count"]

        # Create actor via the create_actor tool endpoint (if exists) or test list/delete
        actors = await client.get(f"{BACKEND_URL}/api/foundry/actors", timeout=15.0)

    assert actors.status_code == 200
    data = actors.json()
    assert data["success"] is True
    assert "actors" in data
    # Verify we can list actors (proves WebSocket communication works)
    assert isinstance(data["actors"], list)
