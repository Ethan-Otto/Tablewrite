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

IMAGEN_MODEL = "gemini-2.5-flash-image"
MAX_RETRIES = 2


class SegmentationError(Exception):
    """Raised when segmentation validation fails."""
    pass


def detect_red_pixels(image_bytes: bytes) -> np.ndarray:
    """Detect red pixels in image (lenient matching for AI-generated borders).

    Detects pixels that are "very red" - high R channel, low G and B channels.
    This is more lenient than exact RGB(255,0,0) to account for compression artifacts.

    Args:
        image_bytes: PNG image as bytes

    Returns:
        Numpy array of (y, x) coordinates of red pixels
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img)

    # Check for grayscale
    if len(img_array.shape) == 2:  # Grayscale
        return np.array([[], []])

    # Lenient red detection: R > 200, G < 50, B < 50
    # This catches RGB(255,0,0) and similar "very red" pixels
    red_mask = (img_array[:,:,0] > 200) & (img_array[:,:,1] < 50) & (img_array[:,:,2] < 50)
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

    Args:
        page_image: PDF page rendered as PNG bytes
        map_type: "navigation_map" or "battle_map"
        output_path: Path to save cropped image

    Raises:
        SegmentationError: If output validation fails
    """
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI environment variable not set")

    client = genai.Client(api_key=api_key)

    # Construct prompt for red perimeter
    map_type_readable = map_type.replace("_", " ")
    prompt = f"Add a precise 5-pixel red border (RGB 255,0,0) around the {map_type_readable} in this image. Do not modify anything else. The border should be exactly on the edge of the map."

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}/{MAX_RETRIES}: Generating red perimeter with Gemini Flash Image")

            # Step 1: Generate image with red perimeter using generate_content
            # Convert page_image bytes to PIL Image for the API
            page_pil_image = Image.open(io.BytesIO(page_image))

            response = client.models.generate_content(
                model=IMAGEN_MODEL,
                contents=[prompt, page_pil_image]
            )

            # Extract generated image from response
            generated_image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    generated_image_bytes = part.inline_data.data
                    break

            if generated_image_bytes is None:
                raise SegmentationError("No image data in response")

            # Debug: Save the generated image with red perimeter
            debug_path = output_path.replace(".png", "_with_red_perimeter.png")
            generated_img = Image.open(io.BytesIO(generated_image_bytes))
            generated_img.save(debug_path)
            logger.debug(f"Saved image with red perimeter to {debug_path}")

            # Step 2: Detect red pixels
            red_pixels = detect_red_pixels(generated_image_bytes)
            red_pixel_count = len(red_pixels[0])

            logger.debug(f"Detected {red_pixel_count} red pixels")

            # Step 3: Calculate bounding box
            bbox = calculate_bounding_box(red_pixels)

            if bbox is None:
                raise SegmentationError(f"No bounding box found (red pixel count: {red_pixel_count})")

            # Step 4: Validate
            if red_pixel_count < 100:
                raise SegmentationError(f"Insufficient red pixels: {red_pixel_count} (need >= 100)")

            bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if bbox_area < 1000:
                raise SegmentationError(f"Bounding box too small: {bbox_area}px² (need >= 1000)")

            logger.info(f"Validation passed: {red_pixel_count} red pixels, bbox area {bbox_area}px²")

            # Step 5: Crop original image (inset 5px to remove red border)
            original_img = Image.open(io.BytesIO(page_image))
            x_min, y_min, x_max, y_max = bbox

            # Inset by 5 pixels
            x_min = max(0, x_min + 5)
            y_min = max(0, y_min + 5)
            x_max = min(original_img.width, x_max - 5)
            y_max = min(original_img.height, y_max - 5)

            cropped = original_img.crop((x_min, y_min, x_max, y_max))

            # Step 6: Save
            cropped.save(output_path, "PNG")
            logger.info(f"Segmented map saved to {output_path} ({x_max - x_min}x{y_max - y_min})")
            return

        except SegmentationError as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} validation failed: {e}")
            if attempt >= MAX_RETRIES - 1:
                raise
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt >= MAX_RETRIES - 1:
                raise SegmentationError(f"Segmentation failed after {MAX_RETRIES} attempts: {e}")
