"""Generate red-lined wall images from battle maps using Gemini."""

import sys
from pathlib import Path
from typing import List, Optional, Union
from PIL import Image

# Add parent to path for util import
sys.path.insert(0, str(Path(__file__).parent.parent))

from util.parallel_image_gen import generate_images_parallel


REDLINE_PROMPT = "Draw red lines for walls in this battle map. Draw straight lines only. Avoid stairs. Do not outline the frame."


async def redline_walls(
    reference_image: Union[str, Path, Image.Image],
    save_dir: Path,
    make_run: bool = True,
    max_concurrent: int = 15,
    temperature: float = 0.5,
    model: str = "gemini-2.5-flash-image"
) -> List[Optional[bytes]]:
    """
    Generate red-lined wall images from battle map.

    Args:
        reference_image: Battle map image to redline
        save_dir: Directory to save redlined images
        make_run: Create timestamped subfolder (default True)
        max_concurrent: Max parallel API calls (default 15)
        temperature: Sampling temperature (default 0.5 for consistency)
        model: Gemini model (default gemini-2.5-flash-image)

    Returns:
        List of image bytes (PNG), None for failures

    Example:
        results = await redline_walls(
            "path/to/battle_map.png",
            save_dir=Path("output/redlined")
        )
    """
    return await generate_images_parallel(
        [REDLINE_PROMPT],
        reference_image=reference_image,
        save_dir=save_dir,
        make_run=make_run,
        max_concurrent=max_concurrent,
        temperature=temperature,
        model=model
    )
