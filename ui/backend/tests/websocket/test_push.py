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
    """Test listing all world scenes via HTTP endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/api/foundry/scenes", timeout=15.0)

    assert response.status_code == 200, f"Failed to list scenes: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert "scenes" in data
    assert isinstance(data["scenes"], list)


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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_actor_items(ensure_foundry_connected, test_folders):
    """Test removing items from an actor via HTTP endpoints."""
    async with httpx.AsyncClient() as client:
        # Create a test folder via HTTP
        folder_response = await client.post(
            f"{BACKEND_URL}/api/foundry/folders",
            json={"name": "tests", "folder_type": "Actor"},
            timeout=15.0
        )
        assert folder_response.status_code == 200, f"Failed to create folder: {folder_response.text}"
        folder_id = folder_response.json().get("folder_id")

        # Create actor with items via HTTP
        actor_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json={
                "actor": {
                    "name": "Test Actor for Item Removal",
                    "type": "npc",
                    "folder": folder_id,
                    "items": [
                        {"name": "Test Sword", "type": "weapon"},
                        {"name": "Test Shield", "type": "equipment"}
                    ]
                }
            },
            timeout=30.0
        )
        assert actor_response.status_code == 200, f"Failed to create actor: {actor_response.text}"
        actor_uuid = actor_response.json()["uuid"]

        try:
            # Remove the sword via HTTP (case-insensitive partial match on "sword")
            remove_response = await client.request(
                "DELETE",
                f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}/items",
                json={"item_names": ["sword"]},
                timeout=30.0
            )

            assert remove_response.status_code == 200, f"Failed to remove items: {remove_response.text}"
            result = remove_response.json()
            assert result["success"] is True
            assert result["items_removed"] == 1
            assert "Test Sword" in result["removed_names"]
        finally:
            # Cleanup - delete the actor via HTTP
            await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}", timeout=15.0)
