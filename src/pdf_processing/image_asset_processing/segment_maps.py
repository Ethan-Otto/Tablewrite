"""Gemini Imagen-based map segmentation."""
import logging
import os
import numpy as np
from PIL import Image
import io
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

IMAGEN_MODEL = "imagen-3.0-generate-002"
MAX_RETRIES = 2


class SegmentationError(Exception):
    """Raised when segmentation validation fails."""
    pass


def detect_red_pixels(image_bytes: bytes) -> np.ndarray:
    """Detect pure red pixels (RGB 255,0,0) in image.

    Args:
        image_bytes: PNG image as bytes

    Returns:
        Numpy array of (y, x) coordinates of red pixels
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img)

    # Check for pure red: R=255, G=0, B=0
    if len(img_array.shape) == 2:  # Grayscale
        return np.array([[], []])

    red_mask = (img_array[:,:,0] == 255) & (img_array[:,:,1] == 0) & (img_array[:,:,2] == 0)
    red_pixels = np.where(red_mask)

    return red_pixels


def calculate_bounding_box(red_pixels: np.ndarray) -> tuple:
    """Calculate bounding box from red pixel coordinates.

    Args:
        red_pixels: Numpy array from detect_red_pixels

    Returns:
        Tuple of (x_min, y_min, x_max, y_max)
    """
    if len(red_pixels[0]) == 0:
        return None

    y_coords, x_coords = red_pixels
    return (x_coords.min(), y_coords.min(), x_coords.max(), y_coords.max())


def segment_with_imagen(page_image: bytes, map_type: str, output_path: str) -> None:
    """Segment baked-in map using Gemini Imagen red perimeter technique.

    NOTE: This is a placeholder implementation. The red perimeter technique
    needs to be validated using the validate_segmentation.py tool before
    this can be fully implemented.

    Args:
        page_image: PDF page rendered as PNG bytes
        map_type: "navigation_map" or "battle_map"
        output_path: Path to save cropped image

    Raises:
        SegmentationError: If output validation fails
        NotImplementedError: Placeholder until technique is validated
    """
    # TODO: Implement after validating red perimeter technique
    # Steps:
    # 1. Generate image with red perimeter using Gemini Imagen
    # 2. Detect red pixels
    # 3. Calculate bounding box
    # 4. Validate (>100 red pixels, bbox area >1000)
    # 5. Crop and save (inset 5px to remove red border)

    raise NotImplementedError(
        "Gemini Imagen segmentation not yet implemented. "
        "Use validate_segmentation.py to test red perimeter technique first."
    )
