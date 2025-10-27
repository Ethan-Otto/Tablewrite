"""Preprocessing utilities for image segmentation."""
import numpy as np
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


def remove_existing_red_pixels(image_bytes: bytes) -> bytes:
    """Replace existing red pixels with black to avoid confusion with Gemini's red border.

    Detects pixels that are reddish (R > 150, R > G+50, R > B+50) and replaces them
    with black to ensure only Gemini's generated red border will be detected.

    Args:
        image_bytes: Input image as bytes

    Returns:
        Preprocessed image as bytes with red pixels replaced by black
    """
    # Load image
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img_array = np.array(img)

    # Detect existing red pixels using THE SAME threshold as our final red detection
    # This ensures we only remove pixels that would interfere with border detection
    red_mask = (
        (img_array[:, :, 0] > 200) &  # R > 200
        (img_array[:, :, 1] < 50) &   # G < 50
        (img_array[:, :, 2] < 50)     # B < 50
    )

    red_pixel_count = red_mask.sum()

    if red_pixel_count > 0:
        logger.info(f"Preprocessing: Replacing {red_pixel_count} existing red pixels with black")
        # Replace red pixels with black
        img_array[red_mask] = [0, 0, 0]
    else:
        logger.debug("Preprocessing: No existing red pixels found")

    # Convert back to bytes
    processed_img = Image.fromarray(img_array)
    output_buffer = io.BytesIO()
    processed_img.save(output_buffer, format='PNG')
    return output_buffer.getvalue()
