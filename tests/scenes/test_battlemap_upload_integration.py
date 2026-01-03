"""Integration test for battle map upload endpoint.

Tests the full battle map upload pipeline through the REST API:
/api/scenes/create-from-map

Requirements:
- Backend server running at localhost:8000
- FoundryVTT connected to backend via WebSocket
- Tablewrite Assistant module enabled in Foundry
"""

import pytest
from pathlib import Path
import httpx

BACKEND_URL = "http://localhost:8000"
TEST_MAP = Path(__file__).parent / "fixtures" / "gridded_map.webp"


@pytest.mark.integration
@pytest.mark.slow
def test_battlemap_upload_creates_scene_with_walls(require_foundry):
    """Test full pipeline: upload map -> detect walls -> create scene.

    This test:
    1. Uploads a gridded battle map image
    2. Runs wall detection pipeline
    3. Creates scene in Foundry with walls
    4. Verifies scene has walls and correct dimensions
    5. Cleans up by deleting the test scene
    """
    assert TEST_MAP.exists(), f"Test map not found: {TEST_MAP}"

    with open(TEST_MAP, "rb") as f:
        response = httpx.post(
            f"{BACKEND_URL}/api/scenes/create-from-map",
            files={"file": ("test_map.webp", f, "image/webp")},
            data={"name": "Integration Test Scene", "skip_walls": "false"},
            timeout=120.0,  # Wall detection takes time
        )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["uuid"].startswith("Scene.")
    assert data["name"] == "Integration Test Scene"
    assert data["wall_count"] > 0, "Expected walls to be detected"
    assert data["image_dimensions"]["width"] > 0
    assert data["image_dimensions"]["height"] > 0

    # Cleanup: delete the test scene
    scene_uuid = data["uuid"]
    delete_response = httpx.delete(
        f"{BACKEND_URL}/api/foundry/scene/{scene_uuid}",
        timeout=10.0,
    )
    # Verify cleanup succeeded
    assert delete_response.status_code == 200, f"Cleanup failed: {delete_response.text}"


@pytest.mark.integration
def test_battlemap_upload_skip_walls(require_foundry):
    """Test upload with wall detection skipped (faster).

    This test:
    1. Uploads a gridded battle map image
    2. Skips wall detection for speed
    3. Verifies scene is created with 0 walls
    4. Cleans up by deleting the test scene
    """
    assert TEST_MAP.exists(), f"Test map not found: {TEST_MAP}"

    with open(TEST_MAP, "rb") as f:
        response = httpx.post(
            f"{BACKEND_URL}/api/scenes/create-from-map",
            files={"file": ("test.webp", f, "image/webp")},
            data={"name": "No Walls Test", "skip_walls": "true"},
            timeout=30.0,
        )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["uuid"].startswith("Scene.")
    assert data["wall_count"] == 0, "Expected no walls when skipped"

    # Cleanup: delete the test scene
    scene_uuid = data["uuid"]
    delete_response = httpx.delete(
        f"{BACKEND_URL}/api/foundry/scene/{scene_uuid}",
        timeout=10.0,
    )
    # Verify cleanup succeeded
    assert delete_response.status_code == 200, f"Cleanup failed: {delete_response.text}"


@pytest.mark.integration
def test_battlemap_upload_custom_grid_size(require_foundry):
    """Test upload with custom grid size override.

    This test verifies that the grid_size parameter is respected.
    """
    assert TEST_MAP.exists(), f"Test map not found: {TEST_MAP}"

    custom_grid_size = 100

    with open(TEST_MAP, "rb") as f:
        response = httpx.post(
            f"{BACKEND_URL}/api/scenes/create-from-map",
            files={"file": ("test.webp", f, "image/webp")},
            data={
                "name": "Custom Grid Test",
                "skip_walls": "true",
                "grid_size": str(custom_grid_size),
            },
            timeout=30.0,
        )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["grid_size"] == custom_grid_size, (
        f"Grid size mismatch: {data['grid_size']} != {custom_grid_size}"
    )

    # Cleanup: delete the test scene
    scene_uuid = data["uuid"]
    delete_response = httpx.delete(
        f"{BACKEND_URL}/api/foundry/scene/{scene_uuid}",
        timeout=10.0,
    )
    assert delete_response.status_code == 200, f"Cleanup failed: {delete_response.text}"
