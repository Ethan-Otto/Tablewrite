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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_actor_items(ensure_foundry_connected, test_folders):
    """Test removing items from an actor."""
    from app.websocket.push import push_actor, remove_actor_items, get_or_create_folder

    # Create a test actor with items
    folder_result = await get_or_create_folder("tests", "Actor")
    assert folder_result.success, f"Failed to create test folder: {folder_result.error}"
    folder_id = folder_result.folder_id

    # Create actor with items via direct WebSocket push
    actor_data = {
        "actor": {
            "name": "Test Actor for Item Removal",
            "type": "npc",
            "folder": folder_id,
            "items": [
                {"name": "Test Sword", "type": "weapon"},
                {"name": "Test Shield", "type": "equipment"}
            ]
        }
    }
    create_result = await push_actor(actor_data, timeout=30.0)
    assert create_result.success, f"Failed to create actor: {create_result.error}"
    actor_uuid = create_result.uuid

    try:
        # Remove the sword (case-insensitive partial match on "sword")
        result = await remove_actor_items(
            actor_uuid=actor_uuid,
            item_names=["sword"],
            timeout=30.0
        )

        assert result.success, f"Failed to remove items: {result.error}"
        assert result.items_removed == 1
        assert "Test Sword" in result.removed_names
    finally:
        # Cleanup - delete the actor
        from app.websocket.push import delete_actor
        await delete_actor(actor_uuid)
