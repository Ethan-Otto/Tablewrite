"""End-to-end test: Scene creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_scene_push.py -v -m integration
"""
import pytest
import os
import httpx

from tests.conftest import get_or_create_tests_folder, check_backend_and_foundry

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
class TestScenePushE2E:
    """End-to-end scene push tests (real Foundry)."""

    @pytest.mark.asyncio
    async def test_create_scene_via_api(self):
        """
        Create scene via API and verify it exists.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for Scene
        folder_id = await get_or_create_tests_folder("Scene")

        async with httpx.AsyncClient() as client:
            scene_name = "Test E2E Scene"

            # Create scene via direct API (must wrap in "scene" key)
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": scene_name,
                        "width": 1000,
                        "height": 1000,
                        "grid": {"size": 100},
                        "folder": folder_id
                    }
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            if not result.get("success"):
                pytest.fail(f"Scene creation failed: {result.get('error')}")

            created_uuid = result.get("uuid")
            assert created_uuid, "No UUID returned"
            assert created_uuid.startswith("Scene."), f"Invalid UUID format: {created_uuid}"

            print(f"[TEST] Created scene: {created_uuid}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_scene_push_contains_required_fields(self):
        """
        Verify scene has correct structure with grid and dimensions.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for Scene
        folder_id = await get_or_create_tests_folder("Scene")

        async with httpx.AsyncClient() as client:
            scene_name = "Test Fields Scene"

            response = await client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": scene_name,
                        "width": 2000,
                        "height": 1500,
                        "grid": {"size": 50},
                        "folder": folder_id
                    }
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            if not result.get("success"):
                pytest.fail(f"Scene creation failed: {result.get('error')}")

            created_uuid = result.get("uuid")
            assert created_uuid, "No UUID returned"

            # Fetch scene to verify structure
            fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
            assert fetch_response.status_code == 200

            fetch_result = fetch_response.json()
            if fetch_result.get("success"):
                scene = fetch_result.get("entity", {})
                assert scene.get("name") == scene_name
                assert scene.get("width") == 2000
                assert scene.get("height") == 1500
                grid = scene.get("grid", {})
                assert grid.get("size") == 50
                print(f"[TEST] Verified scene: {scene.get('name')}")
            else:
                pytest.fail(f"Failed to fetch scene: {fetch_result.get('error')}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_created_scene_can_be_fetched_from_foundry(self):
        """
        Verify created scene can be fetched back from Foundry.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for Scene
        folder_id = await get_or_create_tests_folder("Scene")

        async with httpx.AsyncClient() as client:
            scene_name = "Test Fetch Scene"

            # Create
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": scene_name,
                        "width": 1200,
                        "height": 800,
                        "grid": {"size": 100},
                        "folder": folder_id
                    }
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Fetch
            fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
            assert fetch_response.status_code == 200

            fetch_result = fetch_response.json()
            assert fetch_result.get("success"), f"Fetch failed: {fetch_result.get('error')}"

            scene = fetch_result.get("entity", {})
            assert scene.get("name") == scene_name

            print(f"[TEST] Successfully fetched: {scene.get('name')}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_scene_can_be_deleted(self):
        """
        Verify scene can be created and deleted.
        """
        await check_backend_and_foundry()

        # Get or create /tests folder for Scene
        folder_id = await get_or_create_tests_folder("Scene")

        async with httpx.AsyncClient() as client:
            scene_name = "Test Delete Scene"

            # Create
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/scene",
                json={
                    "scene": {
                        "name": scene_name,
                        "width": 1000,
                        "height": 1000,
                        "grid": {"size": 100},
                        "folder": folder_id
                    }
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Delete
            delete_response = await client.delete(f"{BACKEND_URL}/api/foundry/scene/{created_uuid}")
            assert delete_response.status_code == 200

            delete_result = delete_response.json()
            assert delete_result.get("success"), f"Delete failed: {delete_result.get('error')}"

            print(f"[TEST] Successfully deleted scene")
