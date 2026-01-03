"""Tests for scene orchestration module.

Tests the create_scene_from_map pipeline that orchestrates:
1. Scene name derivation from filename
2. Wall detection via redline_walls
3. Grid detection via detect_gridlines (with fallback to estimate_scene_size)
4. Image upload to Foundry
5. Scene creation with walls
"""

import pytest
import json
import struct
import zlib
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


def create_minimal_png(width: int = 100, height: int = 100) -> bytes:
    """Create a minimal valid PNG file with specified dimensions."""
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    # IHDR chunk (width, height, bit_depth=8, color_type=2=RGB, compression=0, filter=0, interlace=0)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
    # IDAT chunk (minimal compressed data - all red pixels)
    raw_data = b''
    for _ in range(height):
        raw_data += b'\x00'  # Filter byte
        raw_data += b'\xff\x00\x00' * width  # Red pixels (RGB)
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b'IDAT' + compressed)
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
    # IEND chunk
    iend_crc = zlib.crc32(b'IEND')
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
    return signature + ihdr + idat + iend


@pytest.mark.unit
class TestDeriveSceneName:
    """Test _derive_scene_name helper function."""

    def test_derive_name_from_simple_filename(self):
        """Test that scene name is derived from simple filename."""
        from scenes.orchestrate import _derive_scene_name

        result = _derive_scene_name(Path("castle.png"))
        assert result == "Castle"

    def test_derive_name_from_underscored_filename(self):
        """Test that underscores are converted to spaces and title-cased."""
        from scenes.orchestrate import _derive_scene_name

        result = _derive_scene_name(Path("dark_forest_camp.webp"))
        assert result == "Dark Forest Camp"

    def test_derive_name_from_hyphenated_filename(self):
        """Test that hyphens are converted to spaces and title-cased."""
        from scenes.orchestrate import _derive_scene_name

        result = _derive_scene_name(Path("goblin-cave-entrance.jpg"))
        assert result == "Goblin Cave Entrance"

    def test_derive_name_from_full_path(self):
        """Test that only the filename stem is used, not the full path."""
        from scenes.orchestrate import _derive_scene_name

        result = _derive_scene_name(Path("/some/long/path/ancient_ruins.png"))
        assert result == "Ancient Ruins"

    def test_derive_name_preserves_capitalized_words(self):
        """Test that already capitalized words stay capitalized."""
        from scenes.orchestrate import _derive_scene_name

        result = _derive_scene_name(Path("BOSS_arena.png"))
        assert result == "Boss Arena"


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateSceneFromMap:
    """Test create_scene_from_map orchestration function."""

    @pytest.mark.smoke
    async def test_basic_pipeline_creates_scene(self, tmp_path):
        """Test the basic pipeline flow creates a scene in Foundry."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import SceneCreationResult, GridDetectionResult

        # Create a real test image
        test_image = tmp_path / "test_castle.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        # Mock all external dependencies
        mock_redline_result = {
            'original_png': tmp_path / "01_original.png",
            'grayscale': tmp_path / "02_grayscale.png",
            'redlined': tmp_path / "03_redlined.png",
            'overlay': tmp_path / "05_final_overlay.png",
            'foundry_walls_json': tmp_path / "06_foundry_walls.json",
        }
        # Create a mock walls JSON file
        walls_json = tmp_path / "06_foundry_walls.json"
        walls_json.write_text(json.dumps({
            "walls": [{"c": [0, 0, 100, 100], "move": 0, "sense": 0, "door": 0, "ds": 0}],
            "image_dimensions": {"width": 100, "height": 100},
            "total_walls": 1
        }))
        mock_redline_result['foundry_walls_json'] = walls_json

        mock_grid_result = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.95)

        mock_upload_result = {
            "success": True,
            "path": "worlds/myworld/uploaded-maps/test_castle.png"
        }

        mock_scene_result = {
            "success": True,
            "uuid": "Scene.abc123",
            "name": "Test Castle"
        }

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid:
            mock_redline.return_value = mock_redline_result
            mock_detect_grid.return_value = mock_grid_result

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )

            # Verify result type and key fields
            assert isinstance(result, SceneCreationResult)
            assert result.uuid == "Scene.abc123"
            assert result.name == "Test Castle"
            assert result.grid_size == 70
            assert result.wall_count == 1

            # Verify the pipeline was called correctly
            mock_redline.assert_called_once()
            mock_detect_grid.assert_called_once()
            mock_client.files.upload_file.assert_called_once()
            mock_client.scenes.create_scene.assert_called_once()

    async def test_skip_wall_detection(self, tmp_path):
        """Test that wall detection can be skipped."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import SceneCreationResult, GridDetectionResult

        # Create a valid test image
        test_image = tmp_path / "no_walls_map.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_grid_result = GridDetectionResult(has_grid=False, grid_size=None, confidence=0.9)

        mock_upload_result = {
            "success": True,
            "path": "worlds/myworld/uploaded-maps/no_walls_map.png"
        }

        mock_scene_result = {
            "success": True,
            "uuid": "Scene.xyz789",
            "name": "No Walls Map"
        }

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_detect_grid.return_value = mock_grid_result
            mock_estimate.return_value = 100  # Fallback grid size

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client,
                skip_wall_detection=True
            )

            # Wall detection should NOT be called
            mock_redline.assert_not_called()

            # Result should have no walls
            assert result.wall_count == 0

    async def test_skip_grid_detection_uses_estimate(self, tmp_path):
        """Test that skipping grid detection falls back to estimate_scene_size."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import SceneCreationResult

        # Create a valid test image
        test_image = tmp_path / "gridless_map.png"
        test_image.write_bytes(create_minimal_png(1000, 800))

        mock_redline_result = {
            'foundry_walls_json': tmp_path / "walls.json",
            'overlay': tmp_path / "overlay.png"
        }
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [],
            "image_dimensions": {"width": 1000, "height": 800},
            "total_walls": 0
        }))

        mock_upload_result = {"success": True, "path": "worlds/test/gridless_map.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.def456", "name": "Gridless Map"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_redline.return_value = mock_redline_result
            mock_estimate.return_value = 80

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client,
                skip_grid_detection=True
            )

            # Grid detection should NOT be called
            mock_detect_grid.assert_not_called()

            # Estimate should be called
            mock_estimate.assert_called_once()

            # Result should use estimated grid size
            assert result.grid_size == 80

    async def test_grid_size_override(self, tmp_path):
        """Test that grid_size_override skips detection and uses provided value."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import SceneCreationResult

        test_image = tmp_path / "custom_grid.png"
        test_image.write_bytes(create_minimal_png(500, 500))

        mock_redline_result = {
            'foundry_walls_json': tmp_path / "walls.json",
        }
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [],
            "image_dimensions": {"width": 500, "height": 500},
            "total_walls": 0
        }))

        mock_upload_result = {"success": True, "path": "worlds/test/custom_grid.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.custom", "name": "Custom Grid"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_redline.return_value = mock_redline_result

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client,
                grid_size_override=150
            )

            # Neither grid detection nor estimation should be called
            mock_detect_grid.assert_not_called()
            mock_estimate.assert_not_called()

            # Result should use the override value
            assert result.grid_size == 150

    async def test_custom_scene_name(self, tmp_path):
        """Test that custom name parameter overrides filename-derived name."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import SceneCreationResult, GridDetectionResult

        test_image = tmp_path / "map_001.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_redline_result = {'foundry_walls_json': tmp_path / "walls.json"}
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [], "image_dimensions": {"width": 100, "height": 100}, "total_walls": 0
        }))

        mock_grid_result = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.9)
        mock_upload_result = {"success": True, "path": "worlds/test/map_001.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.named", "name": "Dragon's Lair"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid:
            mock_redline.return_value = mock_redline_result
            mock_detect_grid.return_value = mock_grid_result

            result = await create_scene_from_map(
                image_path=test_image,
                name="Dragon's Lair",
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )

            assert result.name == "Dragon's Lair"

    async def test_file_not_found_error(self, tmp_path):
        """Test that FileNotFoundError is raised for missing image."""
        from scenes.orchestrate import create_scene_from_map

        non_existent = tmp_path / "does_not_exist.png"

        with pytest.raises(FileNotFoundError):
            await create_scene_from_map(
                image_path=non_existent,
                output_dir_base=tmp_path
            )

    async def test_upload_failure_raises_error(self, tmp_path):
        """Test that upload failure raises an appropriate error."""
        from scenes.orchestrate import create_scene_from_map

        test_image = tmp_path / "upload_fail.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_redline_result = {'foundry_walls_json': tmp_path / "walls.json"}
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [], "image_dimensions": {"width": 100, "height": 100}, "total_walls": 0
        }))

        mock_upload_result = {"success": False, "error": "Connection refused"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_redline.return_value = mock_redline_result
            mock_estimate.return_value = 100

            with pytest.raises(RuntimeError, match="Failed to upload"):
                await create_scene_from_map(
                    image_path=test_image,
                    output_dir_base=tmp_path,
                    foundry_client=mock_client,
                    skip_grid_detection=True
                )

    async def test_scene_creation_failure_raises_error(self, tmp_path):
        """Test that scene creation failure raises an appropriate error."""
        from scenes.orchestrate import create_scene_from_map

        test_image = tmp_path / "scene_fail.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_redline_result = {'foundry_walls_json': tmp_path / "walls.json"}
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [], "image_dimensions": {"width": 100, "height": 100}, "total_walls": 0
        }))

        mock_upload_result = {"success": True, "path": "worlds/test/scene_fail.png"}
        mock_scene_result = {"success": False, "error": "Foundry not connected"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_redline.return_value = mock_redline_result
            mock_estimate.return_value = 100

            with pytest.raises(RuntimeError, match="Failed to create scene"):
                await create_scene_from_map(
                    image_path=test_image,
                    output_dir_base=tmp_path,
                    foundry_client=mock_client,
                    skip_grid_detection=True
                )

    async def test_output_directory_structure(self, tmp_path):
        """Test that output directory is created with correct structure."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import GridDetectionResult

        test_image = tmp_path / "struct_test.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_redline_result = {
            'foundry_walls_json': tmp_path / "walls.json",
            'overlay': tmp_path / "overlay.png",
            'grayscale': tmp_path / "grayscale.png"
        }
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [], "image_dimensions": {"width": 100, "height": 100}, "total_walls": 0
        }))

        mock_grid_result = GridDetectionResult(has_grid=True, grid_size=50, confidence=0.8)
        mock_upload_result = {"success": True, "path": "worlds/test/struct_test.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.struct", "name": "Struct Test"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid:
            mock_redline.return_value = mock_redline_result
            mock_detect_grid.return_value = mock_grid_result

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )

            # Verify output_dir is set and is a Path
            assert isinstance(result.output_dir, Path)

            # Verify timestamp format
            assert len(result.timestamp) == 15  # YYYYMMDD_HHMMSS
            assert result.timestamp[8] == '_'

    async def test_falls_back_to_estimate_when_no_grid_detected(self, tmp_path):
        """Test that estimate_scene_size is called when detect_gridlines finds no grid."""
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import GridDetectionResult

        test_image = tmp_path / "no_grid.png"
        test_image.write_bytes(create_minimal_png(1000, 800))

        mock_redline_result = {'foundry_walls_json': tmp_path / "walls.json"}
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [], "image_dimensions": {"width": 1000, "height": 800}, "total_walls": 0
        }))

        # Grid detection returns no grid
        mock_grid_result = GridDetectionResult(has_grid=False, grid_size=None, confidence=0.9)
        mock_upload_result = {"success": True, "path": "worlds/test/no_grid.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.nogrid", "name": "No Grid"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid, \
             patch("scenes.orchestrate.estimate_scene_size") as mock_estimate:
            mock_redline.return_value = mock_redline_result
            mock_detect_grid.return_value = mock_grid_result
            mock_estimate.return_value = 90  # Fallback

            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )

            # Both should be called - detect_gridlines first, then estimate as fallback
            mock_detect_grid.assert_called_once()
            mock_estimate.assert_called_once()

            # Should use estimate's value
            assert result.grid_size == 90


@pytest.mark.unit
@pytest.mark.asyncio
class TestParallelDetection:
    """Test that wall and grid detection run in parallel."""

    async def test_wall_and_grid_detection_run_in_parallel(self, tmp_path):
        """Test that wall detection and grid detection execute concurrently.

        Uses timing to verify both tasks start before either finishes.
        If sequential, total time would be >= 0.2s (0.1s + 0.1s).
        If parallel, total time should be ~0.1s.
        """
        import asyncio
        import time
        from scenes.orchestrate import create_scene_from_map
        from scenes.models import GridDetectionResult

        test_image = tmp_path / "parallel_test.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        # Track call times
        call_log = []

        async def slow_redline_walls(*args, **kwargs):
            """Mock wall detection that takes 100ms."""
            call_log.append(('walls_start', time.time()))
            await asyncio.sleep(0.1)
            call_log.append(('walls_end', time.time()))
            # Create the walls JSON file
            walls_json = tmp_path / "walls" / "06_foundry_walls.json"
            walls_json.parent.mkdir(parents=True, exist_ok=True)
            walls_json.write_text(json.dumps({
                "walls": [{"c": [0, 0, 100, 100], "move": 0, "sense": 0, "door": 0, "ds": 0}],
                "image_dimensions": {"width": 100, "height": 100},
                "total_walls": 1
            }))
            return {'foundry_walls_json': walls_json}

        async def slow_detect_gridlines(*args, **kwargs):
            """Mock grid detection that takes 100ms."""
            call_log.append(('grid_start', time.time()))
            await asyncio.sleep(0.1)
            call_log.append(('grid_end', time.time()))
            return GridDetectionResult(has_grid=True, grid_size=70, confidence=0.95)

        mock_upload_result = {"success": True, "path": "worlds/test/parallel_test.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.parallel", "name": "Parallel Test"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", side_effect=slow_redline_walls), \
             patch("scenes.orchestrate.detect_gridlines", side_effect=slow_detect_gridlines):

            start_time = time.time()
            result = await create_scene_from_map(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )
            total_time = time.time() - start_time

        # Verify both functions were called
        assert any(event[0] == 'walls_start' for event in call_log), "Wall detection should start"
        assert any(event[0] == 'grid_start' for event in call_log), "Grid detection should start"
        assert any(event[0] == 'walls_end' for event in call_log), "Wall detection should end"
        assert any(event[0] == 'grid_end' for event in call_log), "Grid detection should end"

        # Extract timestamps
        walls_start = next(t for name, t in call_log if name == 'walls_start')
        walls_end = next(t for name, t in call_log if name == 'walls_end')
        grid_start = next(t for name, t in call_log if name == 'grid_start')
        grid_end = next(t for name, t in call_log if name == 'grid_end')

        # Key assertion: Both tasks should start before either finishes
        # This proves they run in parallel
        first_end = min(walls_end, grid_end)
        assert walls_start < first_end, "Wall detection should start before first task ends"
        assert grid_start < first_end, "Grid detection should start before first task ends"

        # Timing assertion: Should complete in ~0.1s (parallel), not ~0.2s (sequential)
        # Allow some buffer for test overhead
        assert total_time < 0.18, f"Tasks should run in parallel (~0.1s), but took {total_time:.3f}s"

        # Verify result is correct
        assert result.uuid == "Scene.parallel"
        assert result.grid_size == 70
        assert result.wall_count == 1


@pytest.mark.unit
class TestCreateSceneFromMapSync:
    """Test the synchronous wrapper function."""

    def test_sync_wrapper_calls_async_function(self, tmp_path):
        """Test that sync wrapper properly calls the async function."""
        from scenes.orchestrate import create_scene_from_map_sync
        from scenes.models import SceneCreationResult, GridDetectionResult

        test_image = tmp_path / "sync_test.png"
        test_image.write_bytes(create_minimal_png(100, 100))

        mock_redline_result = {'foundry_walls_json': tmp_path / "walls.json"}
        (tmp_path / "walls.json").write_text(json.dumps({
            "walls": [{"c": [0, 0, 10, 10], "move": 0, "sense": 0, "door": 0, "ds": 0}],
            "image_dimensions": {"width": 100, "height": 100},
            "total_walls": 1
        }))

        mock_grid_result = GridDetectionResult(has_grid=True, grid_size=50, confidence=0.9)
        mock_upload_result = {"success": True, "path": "worlds/test/sync_test.png"}
        mock_scene_result = {"success": True, "uuid": "Scene.sync", "name": "Sync Test"}

        mock_client = MagicMock()
        mock_client.files.upload_file = MagicMock(return_value=mock_upload_result)
        mock_client.scenes.create_scene = MagicMock(return_value=mock_scene_result)

        with patch("scenes.orchestrate.redline_walls", new_callable=AsyncMock) as mock_redline, \
             patch("scenes.orchestrate.detect_gridlines", new_callable=AsyncMock) as mock_detect_grid:
            mock_redline.return_value = mock_redline_result
            mock_detect_grid.return_value = mock_grid_result

            result = create_scene_from_map_sync(
                image_path=test_image,
                output_dir_base=tmp_path,
                foundry_client=mock_client
            )

            # Should return proper result
            assert isinstance(result, SceneCreationResult)
            assert result.uuid == "Scene.sync"
            assert result.name == "Sync Test"
