"""Integration tests for ActorQueryTool with real Foundry data."""
import pytest
import httpx
import os

from tests.conftest import check_backend_and_foundry, get_or_create_test_folder

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_actor_roundtrip():
    """
    Integration test: Create a test actor, query it, verify answer contains expected info.

    1. Create a test actor with known stats
    2. Query the actor's abilities
    3. Verify the answer mentions the expected stats
    4. Delete the test actor
    """
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("Actor")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create test actor with known stats
        actor_data = {
            "name": "Test Query Goblin",
            "type": "npc",
            "system": {
                "details": {
                    "cr": 0.25,
                    "type": {"value": "humanoid", "subtype": "goblinoid"}
                },
                "attributes": {
                    "ac": {"value": 15},
                    "hp": {"value": 7, "max": 7}
                },
                "abilities": {
                    "str": {"value": 8, "mod": -1},
                    "dex": {"value": 14, "mod": 2},
                    "con": {"value": 10, "mod": 0},
                    "int": {"value": 10, "mod": 0},
                    "wis": {"value": 8, "mod": -1},
                    "cha": {"value": 8, "mod": -1}
                }
            }
        }

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json={"actor": actor_data, "folder": folder_id}
        )
        assert create_response.status_code == 200, f"Failed to create actor: {create_response.text}"
        actor_uuid = create_response.json()["uuid"]

        try:
            # Query the actor's abilities
            query_response = await client.post(
                f"{BACKEND_URL}/api/tools/query_actor",
                json={
                    "actor_uuid": actor_uuid,
                    "query": "What are this creature's ability scores?",
                    "query_type": "abilities"
                }
            )
            assert query_response.status_code == 200, f"Query failed: {query_response.text}"

            data = query_response.json()
            assert data["type"] == "text", f"Expected text response, got: {data['type']}"

            message = data["message"].lower()
            # Verify the answer mentions key stats
            assert "dex" in message or "dexterity" in message or "14" in message, \
                f"Expected DEX info in response: {data['message']}"

        finally:
            # Clean up: delete the test actor
            delete_response = await client.delete(
                f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}"
            )
            assert delete_response.status_code == 200, f"Failed to delete actor: {delete_response.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_actor_combat_info():
    """Test querying actor's combat abilities."""
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("Actor")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create actor with weapon
        actor_data = {
            "name": "Test Combat Goblin",
            "type": "npc",
            "system": {
                "details": {"cr": 0.25},
                "attributes": {"ac": {"value": 15}, "hp": {"value": 7}}
            },
            "items": [
                {
                    "name": "Scimitar",
                    "type": "weapon",
                    "system": {
                        "attack": {"bonus": 4},
                        "damage": {"parts": [["1d6+2", "slashing"]]},
                        "actionType": "mwak"
                    }
                }
            ]
        }

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json={"actor": actor_data, "folder": folder_id}
        )
        assert create_response.status_code == 200, f"Failed to create actor: {create_response.text}"
        actor_uuid = create_response.json()["uuid"]

        try:
            # Query combat abilities
            query_response = await client.post(
                f"{BACKEND_URL}/api/tools/query_actor",
                json={
                    "actor_uuid": actor_uuid,
                    "query": "What attacks can this creature make?",
                    "query_type": "combat"
                }
            )
            assert query_response.status_code == 200

            data = query_response.json()
            assert data["type"] == "text"

            message = data["message"].lower()
            # Should mention the weapon
            assert "scimitar" in message or "slashing" in message or "attack" in message, \
                f"Expected combat info in response: {data['message']}"

        finally:
            await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_actor_spells():
    """Test querying actor's spells."""
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("Actor")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create actor with spells
        actor_data = {
            "name": "Test Mage",
            "type": "npc",
            "system": {
                "details": {"cr": 1},
                "attributes": {"ac": {"value": 12}, "hp": {"value": 9}}
            },
            "items": [
                {
                    "name": "Fire Bolt",
                    "type": "spell",
                    "system": {
                        "level": 0,
                        "school": "evocation"
                    }
                },
                {
                    "name": "Magic Missile",
                    "type": "spell",
                    "system": {
                        "level": 1,
                        "school": "evocation"
                    }
                }
            ]
        }

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json={"actor": actor_data, "folder": folder_id}
        )
        assert create_response.status_code == 200, f"Failed to create actor: {create_response.text}"
        actor_uuid = create_response.json()["uuid"]

        try:
            # Query spells
            query_response = await client.post(
                f"{BACKEND_URL}/api/tools/query_actor",
                json={
                    "actor_uuid": actor_uuid,
                    "query": "What spells can this creature cast?",
                    "query_type": "combat"
                }
            )
            assert query_response.status_code == 200

            data = query_response.json()
            assert data["type"] == "text"

            message = data["message"].lower()
            # Should mention the spells
            assert "fire bolt" in message or "magic missile" in message or "spell" in message, \
                f"Expected spell info in response: {data['message']}"

        finally:
            await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_nonexistent_actor():
    """Test querying a non-existent actor returns error."""
    await check_backend_and_foundry()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/tools/query_actor",
            json={
                "actor_uuid": "Actor.nonexistent123",
                "query": "What can this do?",
                "query_type": "general"
            }
        )

        assert response.status_code == 200  # Tool returns error in response, not HTTP error
        data = response.json()
        assert data["type"] == "error", f"Expected error response for nonexistent actor: {data}"
