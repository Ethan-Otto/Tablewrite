"""Tests for scene Pydantic models."""

import pytest
from pathlib import Path
from pydantic import ValidationError
from src.scenes.models import GridDetectionResult, SceneCreationResult


@pytest.mark.unit
class TestGridDetectionResult:
    """Test GridDetectionResult model."""

    def test_grid_detection_result_with_grid(self):
        """GridDetectionResult with detected grid."""
        result = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.95)

        assert result.has_grid is True
        assert result.grid_size == 70
        assert result.confidence == 0.95

    def test_grid_detection_result_no_grid(self):
        """GridDetectionResult when no grid detected."""
        result = GridDetectionResult(has_grid=False)

        assert result.has_grid is False
        assert result.grid_size is None
        assert result.confidence == 0.0

    def test_grid_detection_result_immutable(self):
        """GridDetectionResult should be frozen/immutable."""
        result = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.95)

        with pytest.raises(ValidationError):
            result.grid_size = 100

    def test_grid_detection_result_defaults(self):
        """GridDetectionResult has sensible defaults."""
        result = GridDetectionResult(has_grid=False)

        assert result.grid_size is None
        assert result.confidence == 0.0


@pytest.mark.unit
class TestSceneCreationResult:
    """Test SceneCreationResult model."""

    def test_scene_creation_result_minimal(self):
        """SceneCreationResult with required fields only."""
        result = SceneCreationResult(
            uuid="Scene.abc123",
            name="Castle",
            output_dir=Path("output/runs/20241102/scenes/castle"),
            timestamp="20241102_143022",
            foundry_image_path="worlds/test/uploaded-maps/castle.webp",
            image_dimensions={"width": 1400, "height": 1000},
        )

        assert result.uuid == "Scene.abc123"
        assert result.name == "Castle"
        assert result.output_dir == Path("output/runs/20241102/scenes/castle")
        assert result.timestamp == "20241102_143022"
        assert result.foundry_image_path == "worlds/test/uploaded-maps/castle.webp"
        assert result.grid_size is None
        assert result.wall_count == 0
        assert result.image_dimensions == {"width": 1400, "height": 1000}
        assert result.debug_artifacts == {}

    def test_scene_creation_result_complete(self):
        """SceneCreationResult holds all pipeline outputs."""
        output_dir = Path("output/runs/20241102/scenes/castle")
        result = SceneCreationResult(
            uuid="Scene.abc123",
            name="Castle",
            output_dir=output_dir,
            timestamp="20241102_143022",
            foundry_image_path="worlds/test/uploaded-maps/castle.webp",
            grid_size=70,
            wall_count=150,
            image_dimensions={"width": 1400, "height": 1000},
            debug_artifacts={
                "grayscale": output_dir / "02_grayscale.png",
                "redlined": output_dir / "03_redlined.png",
                "overlay": output_dir / "05_final_overlay.png",
                "walls_json": output_dir / "06_foundry_walls.json",
            },
        )

        assert result.uuid == "Scene.abc123"
        assert result.wall_count == 150
        assert result.grid_size == 70
        assert "width" in result.image_dimensions
        assert len(result.debug_artifacts) == 4
        assert result.debug_artifacts["overlay"] == output_dir / "05_final_overlay.png"

    def test_scene_creation_result_missing_required(self):
        """SceneCreationResult requires all required fields."""
        with pytest.raises(ValidationError):
            SceneCreationResult(
                uuid="Scene.abc123",
                name="Castle",
                # Missing: output_dir, timestamp, foundry_image_path, image_dimensions
            )

    def test_scene_creation_result_path_types(self):
        """SceneCreationResult accepts Path objects."""
        output_dir = Path("/tmp/test/scenes")
        result = SceneCreationResult(
            uuid="Scene.test123",
            name="Test Map",
            output_dir=output_dir,
            timestamp="20241102_143022",
            foundry_image_path="worlds/test/maps/test.webp",
            image_dimensions={"width": 800, "height": 600},
            debug_artifacts={"overlay": output_dir / "overlay.png"},
        )

        assert isinstance(result.output_dir, Path)
        assert isinstance(result.debug_artifacts["overlay"], Path)

    def test_scene_creation_result_gridless(self):
        """SceneCreationResult supports gridless scenes."""
        result = SceneCreationResult(
            uuid="Scene.gridless",
            name="Theater Map",
            output_dir=Path("output/theater"),
            timestamp="20241102_143022",
            foundry_image_path="worlds/test/maps/theater.webp",
            grid_size=None,  # Explicitly gridless
            wall_count=50,
            image_dimensions={"width": 2000, "height": 1500},
        )

        assert result.grid_size is None
        assert result.wall_count == 50
