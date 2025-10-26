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

    # Construct detailed prompt for red perimeter
    map_type_readable = map_type.replace("_", " ")

    if map_type == "navigation_map":
        map_description = """a dungeon or wilderness map showing:
- Rooms, corridors, caves, or outdoor terrain
- Walls, doors, pathways, or geographical features
- Often includes a compass rose
- May show tactical grid or scale
- The actual geographic/floor plan content, NOT decorative page borders or text headers"""
    else:  # battle_map
        map_description = """a tactical battle map showing:
- Combat grid or encounter area
- Room layouts or terrain features
- Tactical positioning spaces
- The actual combat map content, NOT decorative page borders or text"""

    prompt = f"""Look at this D&D module page and identify the LARGEST {map_type_readable}.

The {map_type_readable} is {map_description}

Your task:
1. Find the LARGEST map diagram on the page (ignore small inset diagrams or thumbnails)
2. Add a precise 5-pixel red border (RGB 255,0,0) around it
3. The border should outline ONLY the map illustration - the actual drawn terrain/rooms/layout

What to INCLUDE in the red border:
- The full map illustration showing terrain, rooms, or tactical spaces
- Any compass rose or scale that is part of the map
- Grid lines if present

What to EXCLUDE from the red border:
- Decorative page borders or frames
- Text labels, titles, or headers above/below the map
- Corner ornaments or flourishes
- Page numbers or margins
- Any text that says "EXAMPLE" or describes the map

The red border should tightly fit around the largest map illustration on the page."""

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

            # Step 5: Scale bounding box back to original resolution
            # Gemini downscales images, so we need to scale coordinates back up
            original_img = Image.open(io.BytesIO(page_image))
            generated_img_pil = Image.open(io.BytesIO(generated_image_bytes))

            scale_x = original_img.width / generated_img_pil.width
            scale_y = original_img.height / generated_img_pil.height

            logger.debug(f"Scaling bbox from {generated_img_pil.width}x{generated_img_pil.height} to {original_img.width}x{original_img.height}")
            logger.debug(f"Scale factors: x={scale_x:.2f}, y={scale_y:.2f}")

            x_min, y_min, x_max, y_max = bbox

            # Scale to original resolution
            x_min = int(x_min * scale_x)
            y_min = int(y_min * scale_y)
            x_max = int(x_max * scale_x)
            y_max = int(y_max * scale_y)

            logger.debug(f"Scaled bbox: ({x_min}, {y_min}) to ({x_max}, {y_max})")

            # Inset by 5 pixels (scaled)
            inset = int(5 * max(scale_x, scale_y))
            x_min = max(0, x_min + inset)
            y_min = max(0, y_min + inset)
            x_max = min(original_img.width, x_max - inset)
            y_max = min(original_img.height, y_max - inset)

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
