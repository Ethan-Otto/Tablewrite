"""Scene size estimation for gridless battle maps.

This module provides a simple, non-AI method to estimate a reasonable
grid size for maps that don't have visible grid lines.
"""

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# Grid size constraints (pixels per square)
MIN_GRID_SIZE = 50
MAX_GRID_SIZE = 200

# Default number of squares to target along the longest edge
DEFAULT_TARGET_SQUARES = 25


def estimate_scene_size(image_path: Path, target_squares: int = DEFAULT_TARGET_SQUARES) -> int:
    """
    Estimate a reasonable grid size for a gridless map based on image dimensions.

    This function calculates a grid size by dividing the longest edge of the image
    by the target number of squares, then rounds to the nearest 10 pixels for
    cleaner numbers and clamps to a reasonable range.

    Args:
        image_path: Path to the battle map image
        target_squares: Desired number of grid squares along the longest edge
                       (default: 25)

    Returns:
        Grid size in pixels (integer), rounded to nearest 10 and clamped to 50-200px

    Raises:
        FileNotFoundError: If image_path does not exist

    Example:
        # For a 2000x1000 pixel map with default target_squares=25:
        # longest_edge = 2000
        # raw_size = 2000 / 25 = 80
        # rounded = 80 (already a multiple of 10)
        # result = 80 (within 50-200 range)
        grid_size = estimate_scene_size(Path("maps/castle.png"))
        print(f"Estimated grid size: {grid_size}px")
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    logger.info(f"Estimating scene size for: {image_path}")

    # Open image to get dimensions (context manager ensures proper cleanup)
    with Image.open(image_path) as img:
        width, height = img.size

    logger.debug(f"Image dimensions: {width}x{height}")

    # Calculate grid size based on longest edge
    longest_edge = max(width, height)
    raw_grid_size = longest_edge / target_squares

    logger.debug(f"Raw grid size calculation: {longest_edge} / {target_squares} = {raw_grid_size:.2f}")

    # Round to nearest 10 pixels
    rounded_grid_size = round(raw_grid_size / 10) * 10

    logger.debug(f"Rounded to nearest 10: {rounded_grid_size}")

    # Clamp to reasonable range
    clamped_grid_size = max(MIN_GRID_SIZE, min(MAX_GRID_SIZE, rounded_grid_size))

    if clamped_grid_size != rounded_grid_size:
        logger.debug(f"Clamped to range [{MIN_GRID_SIZE}, {MAX_GRID_SIZE}]: {clamped_grid_size}")

    logger.info(f"Estimated grid size: {clamped_grid_size}px")

    return int(clamped_grid_size)
