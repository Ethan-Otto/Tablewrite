"""Integration tests for scene creation round-trip with FoundryVTT.

These tests verify that scenes can be created in FoundryVTT using the full pipeline
and that the data can be fetched back and verified. This is the round-trip integration
test required by CLAUDE.md for all Foundry resources.

Requirements:
- Backend server running at localhost:8000
- FoundryVTT connected to backend via WebSocket
- Tablewrite Assistant module enabled in Foundry
"""

import pytest
import uuid
from pathlib import Path

from foundry.client import FoundryClient
from scenes.orchestrate import create_scene_from_map


# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def gridded_map_path() -> Path:
    """Return path to gridded map fixture."""
    path = FIXTURES_DIR / "gridded_map.webp"
    if not path.exists():
        pytest.fail(f"Gridded map fixture not found: {path}")
    return path


@pytest.fixture
def gridless_map_path() -> Path:
    """Return path to gridless map fixture."""
    path = FIXTURES_DIR / "gridless_map.webp"
    if not path.exists():
        pytest.fail(f"Gridless map fixture not found: {path}")
    return path


@pytest.fixture
def client() -> FoundryClient:
    """Create FoundryVTT client for testing."""
    return FoundryClient()


@pytest.fixture
def unique_scene_name() -> str:
    """Generate a unique scene name for testing."""
    return f"Test Scene {uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestSceneCreationRoundtrip:
    """
    Integration tests for scene creation round-trip.

    These tests verify:
    1. Scene can be created in Foundry using the full pipeline
    2. Scene data can be fetched back from Foundry
    3. Fetched data matches what was sent

    Tests FAIL (not skip) if Foundry is not connected, per CLAUDE.md requirements.
    """

    @pytest.mark.asyncio
    async def test_scene_creation_roundtrip_with_walls(
        self,
        client: FoundryClient,
        gridded_map_path: Path,
        unique_scene_name: str,
        integration_test_output_dir: Path,
        ensure_foundry_connected
    ):
        """
        Create scene with walls using full pipeline, fetch back, verify walls exist.

        This test:
        1. Checks Foundry connection (FAILs if not connected)
        2. Creates a scene using create_scene_from_map with a gridded map
        3. Fetches the scene back from Foundry
        4. Verifies the scene data matches:
           - Scene name
           - Scene exists and has valid UUID
           - Scene has walls (wall_count > 0)
           - Image dimensions are set
        """
        # FAIL if not connected - don't skip
        assert client.is_connected(), (
            "Foundry not connected - start backend (cd ui/backend && uvicorn app.main:app --reload) "
            "and connect Foundry module. See CLAUDE.md for setup instructions."
        )

        # Create scene using full pipeline
        result = await create_scene_from_map(
            image_path=gridded_map_path,
            name=unique_scene_name,
            output_dir_base=integration_test_output_dir,
            foundry_client=client,
            skip_wall_detection=False,  # Run wall detection
            skip_grid_detection=True,   # Skip grid detection to speed up test
            grid_size_override=70       # Use fixed grid size
        )

        # Verify creation result
        assert result is not None, "create_scene_from_map returned None"
        assert result.uuid is not None, "Scene UUID is None"
        assert result.uuid.startswith("Scene."), f"Invalid UUID format: {result.uuid}"
        assert result.name == unique_scene_name, f"Name mismatch: {result.name} != {unique_scene_name}"
        assert result.wall_count > 0, f"Expected walls but got wall_count={result.wall_count}"
        assert result.image_dimensions is not None, "Image dimensions not set"
        assert result.image_dimensions.get("width") > 0, "Invalid image width"
        assert result.image_dimensions.get("height") > 0, "Invalid image height"

        # Fetch scene back from Foundry
        fetch_result = client.scenes.get_scene(result.uuid)

        # Verify fetch succeeded
        assert fetch_result.get("success") is True, (
            f"Failed to fetch scene: {fetch_result.get('error')}"
        )

        # Extract entity data
        entity = fetch_result.get("entity")
        assert entity is not None, "Fetched scene has no entity data"

        # Verify scene data matches
        assert entity.get("name") == unique_scene_name, (
            f"Fetched name mismatch: {entity.get('name')} != {unique_scene_name}"
        )

        # Verify scene has walls
        scene_walls = entity.get("walls", [])
        assert len(scene_walls) > 0, (
            f"Expected walls in fetched scene but got {len(scene_walls)} walls. "
            f"Original wall_count was {result.wall_count}"
        )

        # Verify grid settings
        grid_data = entity.get("grid", {})
        assert grid_data.get("size") == 70, f"Grid size mismatch: {grid_data.get('size')} != 70"

        # Verify image dimensions in scene
        assert entity.get("width") == result.image_dimensions["width"], (
            f"Width mismatch: {entity.get('width')} != {result.image_dimensions['width']}"
        )
        assert entity.get("height") == result.image_dimensions["height"], (
            f"Height mismatch: {entity.get('height')} != {result.image_dimensions['height']}"
        )

    @pytest.mark.asyncio
    async def test_scene_creation_gridless(
        self,
        client: FoundryClient,
        gridless_map_path: Path,
        unique_scene_name: str,
        integration_test_output_dir: Path,
        ensure_foundry_connected
    ):
        """
        Create gridless scene, verify grid estimation works.

        This test:
        1. Checks Foundry connection (FAILs if not connected)
        2. Creates a scene using create_scene_from_map with a gridless map
        3. Uses skip_grid_detection=True to use estimate_scene_size fallback
        4. Verifies the scene is created with estimated grid size
        5. Fetches scene back and verifies data
        """
        # FAIL if not connected - don't skip
        assert client.is_connected(), (
            "Foundry not connected - start backend (cd ui/backend && uvicorn app.main:app --reload) "
            "and connect Foundry module. See CLAUDE.md for setup instructions."
        )

        # Create scene with grid estimation (no override)
        result = await create_scene_from_map(
            image_path=gridless_map_path,
            name=unique_scene_name,
            output_dir_base=integration_test_output_dir,
            foundry_client=client,
            skip_wall_detection=True,   # Skip walls for this test
            skip_grid_detection=True,   # Use estimation instead of detection
            grid_size_override=None     # Let estimation run
        )

        # Verify creation result
        assert result is not None, "create_scene_from_map returned None"
        assert result.uuid is not None, "Scene UUID is None"
        assert result.uuid.startswith("Scene."), f"Invalid UUID format: {result.uuid}"
        assert result.name == unique_scene_name, f"Name mismatch: {result.name} != {unique_scene_name}"

        # Grid size should be set from estimation
        assert result.grid_size is not None, "Grid size not set (estimation failed)"
        assert result.grid_size > 0, f"Invalid grid size: {result.grid_size}"

        # Verify image dimensions are set
        assert result.image_dimensions is not None, "Image dimensions not set"
        assert result.image_dimensions.get("width") > 0, "Invalid image width"
        assert result.image_dimensions.get("height") > 0, "Invalid image height"

        # Fetch scene back from Foundry
        fetch_result = client.scenes.get_scene(result.uuid)

        # Verify fetch succeeded
        assert fetch_result.get("success") is True, (
            f"Failed to fetch scene: {fetch_result.get('error')}"
        )

        # Extract entity data
        entity = fetch_result.get("entity")
        assert entity is not None, "Fetched scene has no entity data"

        # Verify scene data matches
        assert entity.get("name") == unique_scene_name, (
            f"Fetched name mismatch: {entity.get('name')} != {unique_scene_name}"
        )

        # Verify grid size from estimation
        grid_data = entity.get("grid", {})
        fetched_grid_size = grid_data.get("size")
        assert fetched_grid_size == result.grid_size, (
            f"Grid size mismatch: {fetched_grid_size} != {result.grid_size}"
        )

        # No walls expected (we skipped wall detection)
        assert result.wall_count == 0, f"Expected no walls but got {result.wall_count}"

    @pytest.mark.asyncio
    async def test_scene_creation_with_custom_name(
        self,
        client: FoundryClient,
        gridded_map_path: Path,
        integration_test_output_dir: Path,
        ensure_foundry_connected
    ):
        """
        Verify custom scene name is preserved through round-trip.

        This test uses a distinctive name with special characters to verify
        name preservation.
        """
        # FAIL if not connected - don't skip
        assert client.is_connected(), (
            "Foundry not connected - start backend and connect Foundry module"
        )

        # Use a name with apostrophe and unique ID
        custom_name = f"Dragon's Lair {uuid.uuid4().hex[:6]}"

        result = await create_scene_from_map(
            image_path=gridded_map_path,
            name=custom_name,
            output_dir_base=integration_test_output_dir,
            foundry_client=client,
            skip_wall_detection=True,
            skip_grid_detection=True,
            grid_size_override=100
        )

        assert result.name == custom_name, f"Name mismatch in result: {result.name}"

        # Fetch and verify name preserved
        fetch_result = client.scenes.get_scene(result.uuid)
        assert fetch_result.get("success") is True, f"Fetch failed: {fetch_result.get('error')}"

        entity = fetch_result.get("entity")
        assert entity.get("name") == custom_name, (
            f"Name not preserved: '{entity.get('name')}' != '{custom_name}'"
        )

    @pytest.mark.asyncio
    async def test_scene_background_image_set(
        self,
        client: FoundryClient,
        gridded_map_path: Path,
        unique_scene_name: str,
        integration_test_output_dir: Path,
        ensure_foundry_connected
    ):
        """
        Verify background image path is correctly set in Foundry scene.
        """
        # FAIL if not connected - don't skip
        assert client.is_connected(), (
            "Foundry not connected - start backend and connect Foundry module"
        )

        result = await create_scene_from_map(
            image_path=gridded_map_path,
            name=unique_scene_name,
            output_dir_base=integration_test_output_dir,
            foundry_client=client,
            skip_wall_detection=True,
            skip_grid_detection=True,
            grid_size_override=100
        )

        # Verify foundry_image_path is set
        assert result.foundry_image_path is not None, "Foundry image path not set"
        assert result.foundry_image_path.startswith("worlds/"), (
            f"Image path not in worlds/ format: {result.foundry_image_path}"
        )

        # Fetch and verify background is set
        fetch_result = client.scenes.get_scene(result.uuid)
        assert fetch_result.get("success") is True, f"Fetch failed: {fetch_result.get('error')}"

        entity = fetch_result.get("entity")
        background = entity.get("background", {})

        # Background should have src set
        background_src = background.get("src")
        assert background_src is not None, "Background src not set in fetched scene"
        assert background_src == result.foundry_image_path, (
            f"Background src mismatch: '{background_src}' != '{result.foundry_image_path}'"
        )
