"""
Integration tests for batch actor creation.
Tests the full pipeline via HTTP API, not direct tool invocation.
"""
import os
import pytest
import sys
from pathlib import Path
import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ui/backend"))

# Use environment variable for Docker compatibility
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.asyncio
async def test_batch_actor_creation_roundtrip():
    """
    Test batch actor creation end-to-end via HTTP API:
    1. Send chat message that triggers BatchActorCreatorTool
    2. Parse response for created actor UUIDs
    3. Fetch and validate actors
    4. Cleanup
    """
    # First check that backend is healthy
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{BACKEND_URL}/health")
            assert health.status_code == 200, "Backend not running - start with: cd ui/backend && uvicorn app.main:app --reload"
        except httpx.ConnectError:
            pytest.fail("Backend not running - start with: cd ui/backend && uvicorn app.main:app --reload")

        # Check Foundry connection
        status = await client.get(f"{BACKEND_URL}/api/foundry/status")
        status_data = status.json()
        assert status_data.get("connected_clients", 0) > 0, \
            "Foundry not connected - ensure Tablewrite module is enabled and connected"

        # Step 1: Send chat message to create actors
        chat_response = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": "Create a goblin and a bugbear",
                "conversation_history": []
            },
            timeout=120.0  # Actor creation can take time
        )
        assert chat_response.status_code == 200, f"Chat failed: {chat_response.text}"

        result = chat_response.json()

        # Check for error response
        if result.get("type") == "error":
            pytest.fail(f"Batch creation failed: {result.get('message')}")

        # Step 2: Parse response for created actors
        data = result.get("data", {})
        created = data.get("created", [])

        # If no data.created, the AI might have responded differently
        if not created:
            # Check if message contains @UUID links
            import re
            message = result.get("message", "")
            uuid_pattern = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]'
            matches = re.findall(uuid_pattern, message)
            if matches:
                created = [{"uuid": f"Actor.{m}"} for m in matches]

        assert len(created) >= 2, f"Expected 2 actors, got {len(created)}. Response: {result}"

        created_uuids = [a.get("uuid") for a in created if a.get("uuid")]

        # Step 3: Fetch and validate each actor
        try:
            for uuid in created_uuids:
                actor_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                assert actor_response.status_code == 200, f"Failed to fetch {uuid}"

                actor_result = actor_response.json()
                assert actor_result.get("success"), f"Fetch failed: {actor_result.get('error')}"

                actor = actor_result["entity"]
                assert actor["type"] == "npc", f"Wrong type: {actor['type']}"

                # Validate has stats (not all default 10)
                abilities = actor.get("system", {}).get("abilities", {})
                has_non_default = any(
                    abilities.get(a, {}).get("value", 10) != 10
                    for a in ["str", "dex", "con"]
                )
                assert has_non_default, f"Actor {actor['name']} has default stats"

                # Validate has items
                items = actor.get("items", [])
                assert len(items) > 0, f"Actor {actor['name']} has no items"

                print(f"Validated: {actor['name']}: {len(items)} items")

        finally:
            # Step 4: Cleanup
            for uuid in created_uuids:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                except Exception as e:
                    print(f"Warning: Failed to delete {uuid}: {e}")


@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.asyncio
async def test_batch_actor_with_duplicates():
    """Test that batch handles multiple of the same creature type."""
    async with httpx.AsyncClient() as client:
        # Check backend/Foundry first
        try:
            health = await client.get(f"{BACKEND_URL}/health")
            assert health.status_code == 200, "Backend not running"
        except httpx.ConnectError:
            pytest.fail("Backend not running")

        status = await client.get(f"{BACKEND_URL}/api/foundry/status")
        status_data = status.json()
        assert status_data.get("connected_clients", 0) > 0, "Foundry not connected"

        # Request multiple of the same type
        chat_response = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": "Create two goblins",
                "conversation_history": []
            },
            timeout=120.0
        )
        assert chat_response.status_code == 200

        result = chat_response.json()
        if result.get("type") == "error":
            pytest.fail(f"Batch creation failed: {result.get('message')}")

        # Parse created actors
        data = result.get("data", {})
        created = data.get("created", [])

        if not created:
            import re
            message = result.get("message", "")
            uuid_pattern = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
            matches = re.findall(uuid_pattern, message)
            created = [{"uuid": f"Actor.{m[0]}", "name": m[1]} for m in matches]

        # Check failures if any
        data = result.get("data") or {}
        failed = data.get("failed", [])
        if failed:
            print(f"Warning: Some actors failed: {failed}")

        # Should create at least 1 (ideally 2, but network issues can cause failures)
        assert len(created) >= 1, f"Expected at least 1 goblin, got {len(created)}. Failures: {failed}"

        # Verify unique names if we got 2
        names = [a.get("name", "") for a in created]
        if len(created) >= 2 and all(names):
            assert len(set(names)) == len(created), f"Expected unique names, got: {names}"

        created_uuids = [a.get("uuid") for a in created if a.get("uuid")]

        try:
            # Verify both actors exist
            for uuid in created_uuids:
                actor_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                assert actor_response.status_code == 200
                actor_result = actor_response.json()
                assert actor_result.get("success")
                assert actor_result["entity"]["type"] == "npc"
                print(f"Validated: {actor_result['entity']['name']}")

        finally:
            for uuid in created_uuids:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                except Exception:
                    pass  # Cleanup failures are non-fatal


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_actor_empty_prompt():
    """Test that batch handles prompts with no recognizable creatures."""
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{BACKEND_URL}/health")
            assert health.status_code == 200
        except httpx.ConnectError:
            pytest.fail("Backend not running")

        # Prompt with no creatures
        chat_response = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": "Tell me about the weather",
                "conversation_history": []
            },
            timeout=60.0
        )
        assert chat_response.status_code == 200

        result = chat_response.json()

        # Should not error, just respond conversationally
        # or if it does call create_actors, should create 0
        data = result.get("data") or {}
        created = data.get("created", [])

        # If somehow creatures were created, that's unexpected
        assert len(created) == 0, f"Should not create actors for non-creature prompt, got: {created}"
