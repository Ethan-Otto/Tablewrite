"""Tests for POST /api/scenes/create-from-map endpoint."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

# Test fixture path - navigate from ui/backend/tests/routers/ to project root tests/
TEST_MAP = Path(__file__).parent.parent.parent.parent.parent / "tests/scenes/fixtures/gridded_map.webp"


def test_create_scene_from_map_success():
    """Test successful scene creation from uploaded map."""
    assert TEST_MAP.exists(), f"Test fixture not found: {TEST_MAP}"

    # Mock the scene creation to avoid real API calls
    mock_result = MagicMock()
    mock_result.uuid = "Scene.test123"
    mock_result.name = "Test Map"
    mock_result.grid_size = 100
    mock_result.wall_count = 50
    mock_result.image_dimensions = {"width": 1000, "height": 800}
    mock_result.foundry_image_path = "worlds/test/uploaded-maps/test.webp"

    with patch("app.routers.scenes.create_scene_from_map_sync", return_value=mock_result):
        with open(TEST_MAP, "rb") as f:
            response = client.post(
                "/api/scenes/create-from-map",
                files={"file": ("test_map.webp", f, "image/webp")},
                data={"name": "Test Map", "skip_walls": "false"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["uuid"] == "Scene.test123"
    assert data["name"] == "Test Map"
    assert data["wall_count"] == 50


def test_create_scene_from_map_no_file():
    """Test error when no file uploaded."""
    response = client.post("/api/scenes/create-from-map", data={})
    assert response.status_code == 422  # Validation error


def test_create_scene_from_map_skip_walls():
    """Test scene creation with wall detection skipped."""
    assert TEST_MAP.exists()

    mock_result = MagicMock()
    mock_result.uuid = "Scene.nowalls"
    mock_result.name = "No Walls Map"
    mock_result.grid_size = 100
    mock_result.wall_count = 0
    mock_result.image_dimensions = {"width": 1000, "height": 800}
    mock_result.foundry_image_path = "worlds/test/uploaded-maps/nowalls.webp"

    with patch("app.routers.scenes.create_scene_from_map_sync", return_value=mock_result) as mock_fn:
        with open(TEST_MAP, "rb") as f:
            response = client.post(
                "/api/scenes/create-from-map",
                files={"file": ("test.webp", f, "image/webp")},
                data={"skip_walls": "true"},
            )

    assert response.status_code == 200
    # Verify skip_walls was passed to the function (mapped to skip_wall_detection)
    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs.get("skip_wall_detection") is True
