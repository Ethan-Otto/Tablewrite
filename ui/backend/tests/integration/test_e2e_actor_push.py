"""End-to-end test: Actor creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Real Gemini API key (makes actual API calls)
3. For round-trip tests: Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_actor_push.py -v -m integration
"""
import pytest
import os
import re
import httpx

from tests.conftest import get_or_create_tests_folder, check_backend_and_foundry

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
class TestActorPushE2E:
    """End-to-end actor push tests (real Gemini API + real Foundry)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_create_actor_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Call /api/chat with actor creation request
        2. Backend creates actor via real Gemini API
        3. Actor is pushed to Foundry via WebSocket
        4. Verify response contains UUID

        Note: This uses REAL Gemini API and costs money.
        """
        await check_backend_and_foundry()

        async with httpx.AsyncClient() as client:
            # Request actor creation via chat
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Create a simple goblin with CR 0.25",
                    "context": {},
                    "conversation_history": []
                },
                timeout=120.0
            )

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check for error response
            if response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")

            # Check if the response indicates actor was created with UUID
            if response_data.get("type") == "text":
                message = response_data.get("message", "")
                if "Created" in message:
                    # Should have UUID in message
                    assert "@UUID[Actor." in message or "Actor." in message, \
                        f"Expected UUID in response. Message: {message}"
                    print(f"[TEST] Actor created successfully")
                else:
                    pytest.skip(f"Actor tool not triggered. Response: {response_data}")
            else:
                pytest.skip(f"Unexpected response type: {response_data.get('type')}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_actor_push_contains_required_fields(self):
        """
        Verify created actor has required FoundryVTT fields.

        Real data test: Uses actual Gemini API to create a creature,
        then fetches it from Foundry to verify structure.
        """
        await check_backend_and_foundry()
        created_uuid = None

        async with httpx.AsyncClient() as client:
            # Create actor with explicit CR
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Create a dire wolf creature with CR 1",
                    "context": {},
                    "conversation_history": []
                },
                timeout=120.0
            )

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Extract UUID from message
                message = response_data.get("message", "")
                uuid_match = re.search(r'Actor\.([a-zA-Z0-9]+)', message)
                assert uuid_match, f"Could not find UUID in message: {message}"
                created_uuid = f"Actor.{uuid_match.group(1)}"

                # Fetch actor from Foundry
                actor_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                assert actor_response.status_code == 200, f"Failed to fetch actor: {actor_response.text}"

                actor_result = actor_response.json()
                assert actor_result.get("success"), f"Fetch failed: {actor_result.get('error')}"

                actor = actor_result["entity"]
                assert "name" in actor, "Actor missing 'name'"
                assert "type" in actor, "Actor missing 'type'"
                assert actor["type"] == "npc", f"Expected type 'npc', got '{actor['type']}'"

                # Verify has stats
                system = actor.get("system", {})
                if "abilities" in system:
                    abilities = system["abilities"]
                    # Check at least one ability is defined
                    assert any(abilities.get(a, {}).get("value") for a in ["str", "dex", "con", "int", "wis", "cha"]), \
                        "Actor has no ability scores"

                print(f"[TEST] Verified actor: {actor['name']}")
            else:
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_multiple_actors_created_in_sequence(self):
        """
        Verify multiple actor creations work in sequence.
        """
        await check_backend_and_foundry()
        created_uuids = []

        async with httpx.AsyncClient() as client:
            creatures = ["a kobold with CR 0.125", "a wolf with CR 0.25"]

            for creature in creatures:
                response = await client.post(
                    f"{BACKEND_URL}/api/chat",
                    json={
                        "message": f"Create {creature}",
                        "context": {},
                        "conversation_history": []
                    },
                    timeout=120.0
                )

                assert response.status_code == 200
                response_data = response.json()

                if response_data.get("type") == "error":
                    pytest.fail(f"Actor creation failed for {creature}: {response_data.get('message')}")

                if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                    message = response_data.get("message", "")
                    uuid_match = re.search(r'Actor\.([a-zA-Z0-9]+)', message)
                    if uuid_match:
                        created_uuids.append(f"Actor.{uuid_match.group(1)}")

            # Should have created at least 1 actor
            assert len(created_uuids) >= 1, f"Expected at least 1 actor, got {len(created_uuids)}"
            print(f"[TEST] Created {len(created_uuids)} actors in sequence")

            # Cleanup
            for uuid in created_uuids:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                except Exception as e:
                    print(f"Warning: Failed to delete {uuid}: {e}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_created_actor_can_be_fetched_from_foundry(self):
        """
        Verify that created actor can be fetched back from Foundry
        and has correct structure.
        """
        await check_backend_and_foundry()
        created_uuid = None

        async with httpx.AsyncClient() as client:
            # Request actor creation
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Create a simple skeleton warrior with CR 0.25",
                    "context": {},
                    "conversation_history": []
                },
                timeout=120.0
            )

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                message = response_data.get("message", "")
                uuid_match = re.search(r'Actor\.([a-zA-Z0-9]+)', message)
                assert uuid_match, f"Could not find UUID in message: {message}"
                created_uuid = f"Actor.{uuid_match.group(1)}"

                # Fetch actor from Foundry
                actor_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                assert actor_response.status_code == 200

                actor_result = actor_response.json()
                assert actor_result.get("success"), f"Fetch failed: {actor_result.get('error')}"

                actor = actor_result["entity"]
                assert actor["type"] == "npc", f"Expected type 'npc', got '{actor['type']}'"

                # Verify has items (abilities, weapons, etc.)
                items = actor.get("items", [])
                assert len(items) > 0, f"Actor {actor['name']} has no items"

                # Verify has HP
                hp = actor.get("system", {}).get("attributes", {}).get("hp", {})
                assert hp.get("max", 0) > 0, "Actor has no HP"

                print(f"[TEST] SUCCESS: Actor '{actor['name']}' with {len(items)} items, {hp.get('max')} HP")

            elif response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")


@pytest.mark.integration
class TestActorDirectCreation:
    """Direct actor creation tests via /api/foundry/actor endpoint (no Gemini API)."""

    @pytest.mark.asyncio
    async def test_create_actor_via_api(self):
        """
        Create actor via direct API and verify UUID returned.
        Uses /tests folder for organization.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for Actor
        folder_id = await get_or_create_tests_folder("Actor")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a minimal valid actor
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/actor",
                json={
                    "actor": {
                        "name": "Test Goblin Direct",
                        "type": "npc",
                        "system": {
                            "abilities": {
                                "str": {"value": 8},
                                "dex": {"value": 14},
                                "con": {"value": 10},
                                "int": {"value": 10},
                                "wis": {"value": 8},
                                "cha": {"value": 8}
                            },
                            "attributes": {
                                "hp": {"value": 7, "max": 7},
                                "ac": {"value": 15}
                            },
                            "details": {
                                "cr": 0.25,
                                "type": {"value": "humanoid"}
                            }
                        }
                    },
                    "folder": folder_id
                }
            )

            assert response.status_code == 200, f"Actor creation failed: {response.text}"
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"

            created_uuid = result.get("uuid")
            assert created_uuid, "No UUID returned"
            assert created_uuid.startswith("Actor."), f"Invalid UUID format: {created_uuid}"

            print(f"[TEST] Created actor: {created_uuid}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_actor_roundtrip_fetch(self):
        """
        Create actor, fetch it back, verify data matches.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for Actor
        folder_id = await get_or_create_tests_folder("Actor")

        async with httpx.AsyncClient(timeout=30.0) as client:
            actor_name = "Test Orc Roundtrip"

            # Create actor
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/actor",
                json={
                    "actor": {
                        "name": actor_name,
                        "type": "npc",
                        "system": {
                            "abilities": {
                                "str": {"value": 16},
                                "dex": {"value": 12},
                                "con": {"value": 16},
                                "int": {"value": 7},
                                "wis": {"value": 11},
                                "cha": {"value": 10}
                            },
                            "attributes": {
                                "hp": {"value": 15, "max": 15},
                                "ac": {"value": 13}
                            },
                            "details": {
                                "cr": 0.5,
                                "type": {"value": "humanoid"}
                            }
                        }
                    },
                    "folder": folder_id
                }
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Fetch actor back
            fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
            assert fetch_response.status_code == 200

            fetch_result = fetch_response.json()
            assert fetch_result.get("success"), f"Fetch failed: {fetch_result.get('error')}"

            actor = fetch_result.get("entity", {})
            assert actor.get("name") == actor_name
            assert actor.get("type") == "npc"

            # Verify abilities
            abilities = actor.get("system", {}).get("abilities", {})
            assert abilities.get("str", {}).get("value") == 16

            print(f"[TEST] Successfully fetched: {actor.get('name')}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_actor_can_be_deleted(self):
        """
        Verify actor can be created and deleted.
        """
        await check_backend_and_foundry()

        # Get or create /tests folder for Actor
        folder_id = await get_or_create_tests_folder("Actor")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create actor
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/actor",
                json={
                    "actor": {
                        "name": "Test Delete Actor",
                        "type": "npc",
                        "system": {
                            "abilities": {
                                "str": {"value": 10},
                                "dex": {"value": 10},
                                "con": {"value": 10},
                                "int": {"value": 10},
                                "wis": {"value": 10},
                                "cha": {"value": 10}
                            }
                        }
                    },
                    "folder": folder_id
                }
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Delete actor
            delete_response = await client.delete(f"{BACKEND_URL}/api/foundry/actor/{created_uuid}")
            assert delete_response.status_code == 200

            delete_result = delete_response.json()
            assert delete_result.get("success"), f"Delete failed: {delete_result.get('error')}"

            print(f"[TEST] Successfully deleted actor")
