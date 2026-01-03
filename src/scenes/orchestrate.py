"""Scene creation orchestration pipeline.

Orchestrates the full pipeline for creating a FoundryVTT scene from a battle map image:
1. Derive scene name from filename
2. Create timestamped output directory
3. Run wall detection (redline_walls) unless skipped
4. Detect grid (detect_gridlines) with fallback to estimate_scene_size
5. Upload image to Foundry
6. Create scene with walls
7. Return SceneCreationResult
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from PIL import Image

from scenes.models import SceneCreationResult, GridDetectionResult
from scenes.detect_gridlines import detect_gridlines
from scenes.estimate_scene_size import estimate_scene_size
from wall_detection.redline_walls import redline_walls
from foundry.client import FoundryClient

logger = logging.getLogger(__name__)


def _derive_scene_name(image_path: Path) -> str:
    """
    Derive a scene name from the image filename.

    Converts filename stem to title case, replacing underscores and hyphens with spaces.

    Args:
        image_path: Path to the image file

    Returns:
        Title-cased scene name derived from filename

    Example:
        >>> _derive_scene_name(Path("dark_forest_camp.png"))
        'Dark Forest Camp'
    """
    stem = image_path.stem
    # Replace underscores and hyphens with spaces
    name = stem.replace('_', ' ').replace('-', ' ')
    # Title case
    return name.title()


async def create_scene_from_map(
    image_path: Path,
    name: Optional[str] = None,
    output_dir_base: Path = Path("output/runs"),
    foundry_client: Optional[FoundryClient] = None,
    skip_wall_detection: bool = False,
    skip_grid_detection: bool = False,
    grid_size_override: Optional[int] = None
) -> SceneCreationResult:
    """
    Create a FoundryVTT scene from a battle map image.

    This is the main orchestration function that runs the full pipeline:
    1. Derive scene name from filename (if not provided)
    2. Create timestamped output directory
    3. Run wall detection unless skipped
    4. Detect grid (or use fallback/override)
    5. Upload image to Foundry
    6. Create scene with walls
    7. Return SceneCreationResult

    Args:
        image_path: Path to the battle map image
        name: Optional custom scene name (defaults to filename-derived name)
        output_dir_base: Base directory for output (default: output/runs)
        foundry_client: Optional FoundryClient instance (creates new one if not provided)
        skip_wall_detection: Skip wall detection step (default: False)
        skip_grid_detection: Skip grid detection, use estimate instead (default: False)
        grid_size_override: Use this grid size instead of detection/estimation

    Returns:
        SceneCreationResult with scene UUID, name, output paths, and metadata

    Raises:
        FileNotFoundError: If image_path does not exist
        RuntimeError: If upload or scene creation fails
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Step 1: Derive scene name from filename if not provided
    scene_name = name if name else _derive_scene_name(image_path)
    logger.info(f"Creating scene: {scene_name} from {image_path}")

    # Step 2: Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize scene name for directory (replace spaces with underscores, lowercase)
    safe_name = scene_name.lower().replace(' ', '_').replace("'", "")
    output_dir = output_dir_base / timestamp / "scenes" / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Get image dimensions early
    with Image.open(image_path) as img:
        image_width, image_height = img.size
    image_dimensions = {"width": image_width, "height": image_height}

    # Steps 3 & 4: Run wall detection and grid detection in parallel
    walls = []
    debug_artifacts: Dict[str, Path] = {}
    wall_count = 0
    grid_size: Optional[int] = None

    # Determine what tasks to run
    run_wall_detection = not skip_wall_detection
    run_grid_detection = not skip_grid_detection and grid_size_override is None

    # Build list of parallel tasks
    async def wall_detection_task():
        """Run wall detection and return result."""
        logger.info("Running wall detection...")
        return await redline_walls(
            input_image=image_path,
            save_dir=output_dir / "walls",
            make_run=False
        )

    async def grid_detection_task():
        """Run grid detection and return result."""
        logger.info("Running grid detection...")
        return await detect_gridlines(image_path)

    # Run tasks in parallel
    tasks = []
    task_names = []

    if run_wall_detection:
        tasks.append(wall_detection_task())
        task_names.append('walls')
    if run_grid_detection:
        tasks.append(grid_detection_task())
        task_names.append('grid')

    if tasks:
        logger.info(f"Step 3-4: Running {' and '.join(task_names)} detection in parallel...")
        results = await asyncio.gather(*tasks)

        # Process results based on what was run
        result_idx = 0
        if run_wall_detection:
            wall_result = results[result_idx]
            result_idx += 1

            # Load walls from JSON
            if 'foundry_walls_json' in wall_result:
                walls_json_path = wall_result['foundry_walls_json']
                with open(walls_json_path, 'r') as f:
                    walls_data = json.load(f)
                walls = walls_data.get('walls', [])
                wall_count = len(walls)
                # Update image dimensions from walls data if available
                if 'image_dimensions' in walls_data:
                    image_dimensions = walls_data['image_dimensions']

            # Store debug artifacts
            for key in ['grayscale', 'redlined', 'overlay', 'foundry_walls_json']:
                if key in wall_result:
                    debug_artifacts[key] = wall_result[key]

            logger.info(f"Wall detection complete: {wall_count} walls")

        if run_grid_detection:
            grid_result = results[result_idx]

            if grid_result.has_grid and grid_result.grid_size is not None:
                grid_size = grid_result.grid_size
                logger.info(f"Grid detected: {grid_size}px (confidence: {grid_result.confidence})")
            else:
                # Fallback to estimation
                grid_size = estimate_scene_size(image_path)
                logger.info(f"No grid detected, estimated: {grid_size}px")

    # Handle skipped/override cases
    if skip_wall_detection:
        logger.info("Wall detection: skipped")

    if grid_size_override is not None:
        grid_size = grid_size_override
        logger.info(f"Grid size: using override {grid_size}px")
    elif skip_grid_detection:
        grid_size = estimate_scene_size(image_path)
        logger.info(f"Grid detection: skipped, estimated {grid_size}px")

    # Step 5: Upload image to Foundry
    logger.info("Step 5: Uploading image to Foundry...")
    client = foundry_client if foundry_client else FoundryClient()

    upload_result = client.files.upload_file(image_path, destination="uploaded-maps")

    if not upload_result.get('success'):
        error_msg = upload_result.get('error', 'Unknown error')
        raise RuntimeError(f"Failed to upload image: {error_msg}")

    foundry_image_path = upload_result['path']
    logger.info(f"Image uploaded to: {foundry_image_path}")

    # Step 6: Create scene with walls
    logger.info("Step 6: Creating scene in Foundry...")
    scene_result = client.scenes.create_scene(
        name=scene_name,
        background_image=foundry_image_path,
        width=image_dimensions['width'],
        height=image_dimensions['height'],
        grid_size=grid_size,
        walls=walls if walls else None
    )

    if not scene_result.get('success'):
        error_msg = scene_result.get('error', 'Unknown error')
        raise RuntimeError(f"Failed to create scene: {error_msg}")

    scene_uuid = scene_result['uuid']
    logger.info(f"Scene created: {scene_uuid}")

    # Step 7: Return SceneCreationResult
    result = SceneCreationResult(
        uuid=scene_uuid,
        name=scene_name,
        output_dir=output_dir,
        timestamp=timestamp,
        foundry_image_path=foundry_image_path,
        grid_size=grid_size,
        wall_count=wall_count,
        image_dimensions=image_dimensions,
        debug_artifacts=debug_artifacts
    )

    logger.info(f"Scene creation complete: {scene_name} ({scene_uuid})")
    return result


def create_scene_from_map_sync(
    image_path: Path,
    name: Optional[str] = None,
    output_dir_base: Path = Path("output/runs"),
    foundry_client: Optional[FoundryClient] = None,
    skip_wall_detection: bool = False,
    skip_grid_detection: bool = False,
    grid_size_override: Optional[int] = None
) -> SceneCreationResult:
    """
    Synchronous wrapper for create_scene_from_map.

    See create_scene_from_map for full documentation.
    """
    return asyncio.run(create_scene_from_map(
        image_path=image_path,
        name=name,
        output_dir_base=output_dir_base,
        foundry_client=foundry_client,
        skip_wall_detection=skip_wall_detection,
        skip_grid_detection=skip_grid_detection,
        grid_size_override=grid_size_override
    ))
