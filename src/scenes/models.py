"""Data models for scene creation pipeline."""

from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict


class GridDetectionResult(BaseModel):
    """Result from detect_gridlines()."""

    model_config = ConfigDict(frozen=True)

    has_grid: bool
    grid_size: Optional[int] = None  # Side length in pixels (e.g., 100 = 100x100px)
    confidence: float = 0.0  # 0.0-1.0


class SceneCreationResult(BaseModel):
    """Result from create_scene_from_map()."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core identifiers (matches ActorCreationResult pattern)
    uuid: str  # "Scene.abc123"
    name: str  # "Castle" (derived from filename)
    output_dir: Path  # output/runs/.../scenes/castle/
    timestamp: str  # "20241102_143022"

    # Scene-specific details
    foundry_image_path: str  # "worlds/myworld/uploaded-maps/castle.webp"
    grid_size: Optional[int] = None  # Side length in pixels, None if gridless
    wall_count: int = 0  # Number of walls created
    image_dimensions: Dict[str, int]  # {"width": 1380, "height": 940}

    # Debug artifacts (paths to intermediate files)
    debug_artifacts: Dict[str, Path] = {}  # {grayscale, redlined, overlay, walls_json}
