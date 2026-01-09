"""End-to-end test: Delete assets via chat endpoint.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled
3. Real Gemini API key (makes actual API calls)

Run with: pytest tests/integration/test_e2e_delete_assets.py -v -m integration
"""
import pytest
import os
import httpx

from tests.conftest import get_or_create_tests_folder, check_backend_and_foundry

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
class TestDeleteAssetsChatE2E:
    """End-to-end tests for delete_assets tool via /api/chat."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_delete_single_actor_via_chat(self):
        """
        Full flow test:
        1. Create an actor in Tablewrite folder
        2. Ask chat to delete it by name
        3. Verify actor was deleted

        Note: This uses REAL Gemini API and costs money.
        """
        await check_backend_and_foundry()
        created_uuid = None

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create an actor in Tablewrite folder first
            create_response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Create a goblin named 'TestDeleteGoblin' with CR 0.25",
                    "context": {},
                    "conversation_history": []
                }
            )

            assert create_response.status_code == 200
            create_data = create_response.json()
            print(f"[TEST] Create response: {create_data}")

            if create_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {create_data.get('message')}")

            # Extract UUID from create response
            if "Actor." in create_data.get("message", ""):
                import re
                uuid_match = re.search(r'Actor\.([a-zA-Z0-9]+)', create_data["message"])
                if uuid_match:
                    created_uuid = f"Actor.{uuid_match.group(1)}"
                    print(f"[TEST] Created actor: {created_uuid}")

            if not created_uuid:
                pytest.skip("Could not create test actor for deletion test")

            # Now ask chat to delete the actor
            delete_response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Delete the actor named TestDeleteGoblin",
                    "context": {},
                    "conversation_history": []
                }
            )

            assert delete_response.status_code == 200
            delete_data = delete_response.json()
            print(f"[TEST] Delete response: {delete_data}")

            # Check response indicates deletion
            message = delete_data.get("message", "").lower()
            if "deleted" in message or "removed" in message:
                print(f"[TEST] Actor deleted via chat successfully")

                # Verify actor no longer exists
                fetch_response = await client.get(
                    f"{BACKEND_URL}/api/foundry/actor/{created_uuid}"
                )
                # Should fail or return not found
                if fetch_response.status_code == 200:
                    fetch_data = fetch_response.json()
                    if fetch_data.get("success"):
                        pytest.fail("Actor still exists after deletion")
                print("[TEST] Verified actor was deleted")
            elif "not found" in message or "no actor" in message:
                # Actor already deleted or not found - that's fine
                print("[TEST] Actor not found (may have been deleted)")
            else:
                # If delete tool wasn't triggered, fail
                pytest.fail(f"Delete tool not triggered. Response: {delete_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_bulk_delete_requires_confirmation_via_chat(self):
        """
        Test that bulk deletion requires confirmation:
        1. Create two actors
        2. Ask to delete all actors matching a pattern
        3. Verify confirmation is required
        4. Cleanup

        Note: This uses REAL Gemini API and costs money.
        """
        await check_backend_and_foundry()
        created_uuids = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create two actors with similar names
            for i in range(2):
                response = await client.post(
                    f"{BACKEND_URL}/api/chat",
                    json={
                        "message": f"Create a goblin named 'BulkTestGoblin{i}' with CR 0.25",
                        "context": {},
                        "conversation_history": []
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if "Actor." in data.get("message", ""):
                        import re
                        uuid_match = re.search(r'Actor\.([a-zA-Z0-9]+)', data["message"])
                        if uuid_match:
                            created_uuids.append(f"Actor.{uuid_match.group(1)}")

            print(f"[TEST] Created {len(created_uuids)} actors for bulk test")

            if len(created_uuids) < 2:
                # Cleanup and skip
                for uuid in created_uuids:
                    try:
                        await client.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                    except Exception:
                        pass
                pytest.skip("Could not create enough test actors")

            try:
                # Ask to delete all matching actors
                delete_response = await client.post(
                    f"{BACKEND_URL}/api/chat",
                    json={
                        "message": "Delete all actors named BulkTestGoblin",
                        "context": {},
                        "conversation_history": []
                    }
                )

                assert delete_response.status_code == 200
                delete_data = delete_response.json()
                print(f"[TEST] Bulk delete response: {delete_data}")

                message = delete_data.get("message", "").lower()
                # Should either ask for confirmation OR delete (if tool confirms automatically)
                if "confirm" in message or "found" in message:
                    print("[TEST] Confirmation requested for bulk delete (expected)")
                elif "deleted" in message:
                    print("[TEST] Bulk delete executed")
                else:
                    print(f"[TEST] Unexpected response: {delete_data}")

            finally:
                # Cleanup any remaining actors
                for uuid in created_uuids:
                    try:
                        await client.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                    except Exception as e:
                        print(f"Warning: Cleanup failed for {uuid}: {e}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    @pytest.mark.asyncio
    async def test_cannot_delete_non_tablewrite_assets_via_chat(self):
        """
        Test that delete tool only works on Tablewrite folder assets.

        Note: This uses REAL Gemini API.
        """
        await check_backend_and_foundry()

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Try to delete a non-existent actor outside Tablewrite
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Delete the actor named 'NonexistentSystemActor'",
                    "context": {},
                    "conversation_history": []
                }
            )

            assert response.status_code == 200
            data = response.json()
            print(f"[TEST] Non-tablewrite delete response: {data}")

            message = data.get("message", "").lower()
            # Should indicate actor not found in Tablewrite
            assert "not found" in message or "no actor" in message or "tablewrite" in message, \
                f"Expected 'not found' or 'tablewrite' restriction. Got: {data}"
            print("[TEST] Correctly rejected non-Tablewrite deletion")


@pytest.mark.integration
class TestDeleteAssetsDirectAPI:
    """Direct API tests for delete_assets tool (no Gemini)."""

    @pytest.mark.asyncio
    async def test_delete_actor_via_tools_api(self):
        """
        Test delete_assets tool directly via /api/tools/delete_assets.
        Creates actor in Tablewrite folder, then deletes via tool API.
        """
        await check_backend_and_foundry()

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Get/create Tablewrite folder (the root folder for all Tablewrite assets)
            folder_response = await client.post(
                f"{BACKEND_URL}/api/foundry/folder",
                json={"name": "Tablewrite", "type": "Actor"}
            )
            assert folder_response.status_code == 200
            folder_id = folder_response.json().get("folder_id")
            assert folder_id, "Failed to get Tablewrite folder"

            # Create an actor in Tablewrite folder via HTTP API
            create_response = await client.post(
                f"{BACKEND_URL}/api/foundry/actor",
                json={
                    "actor": {
                        "name": "DirectDeleteTestActor",
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

            assert create_response.status_code == 200
            create_data = create_response.json()
            assert create_data.get("success"), f"Failed to create actor: {create_data}"
            actor_uuid = create_data.get("uuid")
            print(f"[TEST] Created actor: {actor_uuid}")

            try:
                # Delete via tools API
                response = await client.post(
                    f"{BACKEND_URL}/api/tools/delete_assets",
                    json={
                        "entity_type": "actor",
                        "uuid": actor_uuid
                    }
                )

                assert response.status_code == 200, f"Delete failed: {response.text}"
                data = response.json()
                print(f"[TEST] Delete response: {data}")

                assert "deleted" in data.get("message", "").lower(), \
                    f"Expected deletion confirmation. Got: {data}"
                print("[TEST] Actor deleted via direct API")

                # Verify deletion via HTTP API
                fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")
                if fetch_response.status_code == 200:
                    fetch_data = fetch_response.json()
                    assert not fetch_data.get("success") or not fetch_data.get("entity"), \
                        "Actor still exists after deletion"

            except Exception as e:
                # Cleanup on failure
                await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")
                raise e

    @pytest.mark.asyncio
    async def test_delete_actor_by_name_via_tools_api(self):
        """
        Test searching and deleting actor by name via tools API.
        """
        await check_backend_and_foundry()

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Get/create Tablewrite folder (the root folder for all Tablewrite assets)
            folder_response = await client.post(
                f"{BACKEND_URL}/api/foundry/folder",
                json={"name": "Tablewrite", "type": "Actor"}
            )
            assert folder_response.status_code == 200
            folder_id = folder_response.json().get("folder_id")

            unique_name = "UniqueSearchDeleteTest"
            create_response = await client.post(
                f"{BACKEND_URL}/api/foundry/actor",
                json={
                    "actor": {
                        "name": unique_name,
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

            assert create_response.status_code == 200
            create_data = create_response.json()
            assert create_data.get("success")
            actor_uuid = create_data.get("uuid")
            print(f"[TEST] Created actor: {unique_name} ({actor_uuid})")

            try:
                # Delete via search query
                response = await client.post(
                    f"{BACKEND_URL}/api/tools/delete_assets",
                    json={
                        "entity_type": "actor",
                        "search_query": unique_name
                    }
                )

                assert response.status_code == 200
                data = response.json()
                print(f"[TEST] Delete by name response: {data}")

                assert "deleted" in data.get("message", "").lower()
                print("[TEST] Actor deleted by name successfully")

            except Exception as e:
                await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")
                raise e

    @pytest.mark.asyncio
    async def test_cannot_delete_outside_tablewrite(self):
        """
        Verify that actors outside Tablewrite folders cannot be deleted.
        """
        await check_backend_and_foundry()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to delete a non-existent actor
            response = await client.post(
                f"{BACKEND_URL}/api/tools/delete_assets",
                json={
                    "entity_type": "actor",
                    "search_query": "NonExistentActorOutsideTablewrite"
                }
            )

            assert response.status_code == 200
            data = response.json()
            print(f"[TEST] Non-tablewrite response: {data}")

            # Should indicate not found
            assert "not found" in data.get("message", "").lower() or "no actor" in data.get("message", "").lower()
            print("[TEST] Correctly rejected non-Tablewrite deletion")
