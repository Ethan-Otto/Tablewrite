"""Complete wall detection pipeline: image → grayscale → AI redline → polygonize → overlay."""

import sys
import subprocess
import logging
import json
import shutil
from pathlib import Path
from typing import Union, Dict, Any, List, Tuple
from datetime import datetime
from PIL import Image
import cv2
import numpy as np

# Add parent to path for util import
sys.path.insert(0, str(Path(__file__).parent.parent))

from util.parallel_image_gen import generate_images_parallel

logger = logging.getLogger(__name__)

REDLINE_PROMPT = "Draw red lines for walls in this battle map. Draw straight lines only. Avoid stairs. Do not outline the frame."


def convert_to_png(input_path: Path, output_path: Path) -> None:
    """Convert any image format to PNG with white background."""
    img = Image.open(input_path)
    if img.mode == 'RGBA':
        # Composite onto white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.save(output_path, 'PNG')
    logger.info(f"✓ Saved PNG: {output_path}")


def create_grayscale(png_path: Path, output_path: Path) -> None:
    """Create grayscale version of PNG image."""
    img = Image.open(png_path)
    img_gray = img.convert('L')
    img_gray.save(output_path, 'PNG')
    logger.info(f"✓ Saved grayscale: {output_path}")


async def generate_redlines(
    grayscale_path: Path,
    output_path: Path,
    temp_dir: Path,
    temperature: float = 0.5,
    model: str = "gemini-2.5-flash-image"
) -> None:
    """Generate AI red-lined walls from grayscale image."""
    logger.info("Generating AI red-lined walls...")

    redline_results = await generate_images_parallel(
        [REDLINE_PROMPT],
        reference_image=grayscale_path,
        save_dir=temp_dir,
        make_run=False,
        max_concurrent=1,
        temperature=temperature,
        model=model
    )

    if not redline_results or redline_results[0] is None:
        raise RuntimeError("Failed to generate red-lined image")

    # Save redlined image
    with open(output_path, 'wb') as f:
        f.write(redline_results[0])
    logger.info(f"✓ Saved red-lined image: {output_path}")


def polygonize_redlines(
    redlined_path: Path,
    output_dir: Path,
    polygonize_params: Dict[str, Any] = None
) -> None:
    """Extract vector polylines from red-lined image using polygonize.py."""
    logger.info("Polygonizing to extract vector lines...")
    output_dir.mkdir(exist_ok=True)

    # Build polygonize.py command
    polygonize_script = Path(__file__).parent / "polygonize.py"
    params = polygonize_params or {}
    cmd = [
        "python", str(polygonize_script),
        str(redlined_path),
        "--outdir", str(output_dir),
        "--close", str(params.get('close', 5)),
        "--open", str(params.get('open', 3)),
        "--dilate", str(params.get('dilate', 6)),
        "--eps", str(params.get('eps', 5.0)),
        "--snap", str(params.get('snap', 6.0)),
        "--minlen", str(params.get('minlen', 12.0)),
        "--json"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Polygonize failed: {result.stderr}")
        raise RuntimeError(f"Polygonize failed: {result.stderr}")

    logger.info(f"✓ Polygonize output:\n{result.stdout}")


def create_overlay(
    original_path: Path,
    polygonize_dir: Path,
    output_path: Path,
    alpha: float = 0.2
) -> None:
    """Overlay extracted lines on original image with transparency."""
    logger.info(f"Overlaying lines on original (alpha={alpha})...")

    # Load original image with OpenCV
    original_cv = cv2.imread(str(original_path))

    # Load the lines-only transparent PNG from polygonize output
    lines_transparent = cv2.imread(str(polygonize_dir / "lines_only_transparent.png"), cv2.IMREAD_UNCHANGED)

    # Resize to match original if needed
    if lines_transparent.shape[:2] != original_cv.shape[:2]:
        logger.info(f"Resizing lines from {lines_transparent.shape[:2]} to {original_cv.shape[:2]}")
        lines_transparent = cv2.resize(lines_transparent, (original_cv.shape[1], original_cv.shape[0]))

    # Extract alpha channel as mask
    if lines_transparent.shape[2] == 4:
        lines_bgr = lines_transparent[:, :, :3]
        lines_alpha = lines_transparent[:, :, 3]
        mask = lines_alpha > 10
    else:
        # Fallback if no alpha channel
        mask = cv2.cvtColor(lines_transparent, cv2.COLOR_BGR2GRAY) > 10

    # Create final overlay
    final_overlay = original_cv.copy().astype(float)

    # Apply red color with alpha transparency only where lines exist
    red_color = np.array([0, 0, 255], dtype=float)  # Red in BGR
    for c in range(3):
        final_overlay[:, :, c][mask] = (
            original_cv[:, :, c][mask] * (1 - alpha) +
            red_color[c] * alpha
        )

    final_overlay = final_overlay.astype(np.uint8)

    cv2.imwrite(str(output_path), final_overlay)
    logger.info(f"✓ Saved final overlay: {output_path}")


def convert_to_foundry_format(
    polylines_json_path: Path,
    original_dims: Tuple[int, int],
    output_path: Path
) -> int:
    """
    Convert polylines JSON to FoundryVTT wall format.

    Args:
        polylines_json_path: Path to polylines.json from polygonize
        original_dims: (height, width) of original image
        output_path: Where to save FoundryVTT JSON

    Returns:
        Number of walls created
    """
    logger.info("Converting to FoundryVTT wall format...")

    # Load polylines from JSON
    with open(polylines_json_path, 'r') as f:
        poly_data = json.load(f)

    # Scale polylines back to original image dimensions if needed
    orig_h, orig_w = original_dims
    poly_w, poly_h = poly_data['width'], poly_data['height']

    scale_x = orig_w / poly_w
    scale_y = orig_h / poly_h

    # Convert to FoundryVTT wall format
    foundry_walls = []
    for polyline in poly_data['polylines']:
        # Each polyline becomes multiple wall segments (point-to-point)
        for i in range(len(polyline) - 1):
            x1, y1 = polyline[i]
            x2, y2 = polyline[i + 1]

            # Scale coordinates back to original dimensions
            wall = {
                "c": [
                    round(x1 * scale_x, 2),
                    round(y1 * scale_y, 2),
                    round(x2 * scale_x, 2),
                    round(y2 * scale_y, 2)
                ],
                "move": 0,  # 0 = wall blocks movement
                "sense": 0,  # 0 = wall blocks all senses
                "door": 0,  # 0 = not a door
                "ds": 0     # door state (0 = closed)
            }
            foundry_walls.append(wall)

    foundry_json = {
        "walls": foundry_walls,
        "image_dimensions": {"width": orig_w, "height": orig_h},
        "total_walls": len(foundry_walls)
    }

    with open(output_path, 'w') as f:
        json.dump(foundry_json, f, indent=2)

    logger.info(f"✓ Saved FoundryVTT walls: {output_path} ({len(foundry_walls)} walls)")
    return len(foundry_walls)


async def redline_walls(
    input_image: Union[str, Path],
    save_dir: Path,
    make_run: bool = True,
    temperature: float = 0.5,
    model: str = "gemini-2.5-flash-image",
    alpha: float = 0.8,
    polygonize_params: Dict[str, Any] = None
) -> Dict[str, Path]:
    """
    Complete wall detection pipeline.

    Pipeline:
    1. Convert input to PNG
    2. Create grayscale version
    3. Generate AI red-lined walls
    4. Polygonize to extract vector lines
    5. Overlay lines on original
    6. Convert to FoundryVTT format

    Args:
        input_image: Path to battle map (any image format)
        save_dir: Output directory
        make_run: Create timestamped subfolder (default True)
        temperature: AI sampling temperature (default 0.5 for consistency)
        model: Gemini model (default gemini-2.5-flash-image)
        alpha: Transparency for overlay lines (0.0-1.0, default 0.2)
        polygonize_params: Custom params for polygonize.py

    Returns:
        Dict with paths to all output files

    Example:
        result = await redline_walls(
            "data/maps/castle.webp",
            save_dir=Path("output/walls")
        )
        print(f"Overlay: {result['overlay']}")
        print(f"FoundryVTT walls: {result['foundry_walls_json']}")
    """
    input_path = Path(input_image)
    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    # Create output directory
    if make_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = save_dir / timestamp
    else:
        output_dir = save_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting wall detection pipeline for: {input_path}")
    logger.info(f"Output directory: {output_dir}")

    # Define output paths
    original_png = output_dir / "01_original.png"
    grayscale_path = output_dir / "02_grayscale.png"
    redlined_path = output_dir / "03_redlined.png"
    polygonize_dir = output_dir / "04_polygonized"
    overlay_path = output_dir / "05_final_overlay.png"
    foundry_path = output_dir / "06_foundry_walls.json"
    temp_dir = output_dir / "redline_temp"

    # Step 1: Convert to PNG
    logger.info("Step 1: Converting to PNG...")
    convert_to_png(input_path, original_png)

    # Step 2: Create grayscale
    logger.info("Step 2: Creating grayscale...")
    create_grayscale(original_png, grayscale_path)

    # Step 3: Generate AI redlines
    logger.info("Step 3: Generating AI red-lines...")
    await generate_redlines(
        grayscale_path=grayscale_path,
        output_path=redlined_path,
        temp_dir=temp_dir,
        temperature=temperature,
        model=model
    )

    # Step 4: Polygonize
    logger.info("Step 4: Extracting vector lines...")
    polygonize_redlines(
        redlined_path=redlined_path,
        output_dir=polygonize_dir,
        polygonize_params=polygonize_params
    )

    # Step 5: Create overlay
    logger.info("Step 5: Creating overlay...")
    create_overlay(
        original_path=original_png,
        polygonize_dir=polygonize_dir,
        output_path=overlay_path,
        alpha=alpha
    )

    # Step 6: Convert to FoundryVTT format
    logger.info("Step 6: Converting to FoundryVTT format...")
    original_cv = cv2.imread(str(original_png))
    convert_to_foundry_format(
        polylines_json_path=polygonize_dir / "polylines.json",
        original_dims=original_cv.shape[:2],
        output_path=foundry_path
    )

    # Cleanup temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        'original_png': original_png,
        'grayscale': grayscale_path,
        'redlined': redlined_path,
        'polygonized_dir': polygonize_dir,
        'overlay': overlay_path,
        'polylines_json': polygonize_dir / "polylines.json",
        'foundry_walls_json': foundry_path
    }
