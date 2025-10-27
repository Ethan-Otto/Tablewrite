"""Gemini Imagen-based map segmentation."""
import logging
import os
import numpy as np
from PIL import Image
import io
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pytesseract

load_dotenv()
logger = logging.getLogger(__name__)

IMAGEN_MODEL = "gemini-2.5-flash-image"
MAX_RETRIES = 5


class SegmentationError(Exception):
    """Raised when segmentation validation fails."""
    pass


def check_word_count(image_bytes: bytes, max_words: int = 200) -> tuple[int, bool]:
    """Check word count in image using OCR.

    Args:
        image_bytes: Image as bytes
        max_words: Maximum allowed word count

    Returns:
        Tuple of (word_count, is_valid)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        word_count = len(text.split())
        is_valid = word_count <= max_words
        return word_count, is_valid
    except Exception as e:
        logger.warning(f"OCR word count check failed: {e}, assuming valid")
        return 0, True


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


def find_rectangular_regions(red_pixels: np.ndarray) -> list:
    """Find rectangular regions from red pixels using connected components.

    Uses connected components to find disconnected red regions, then returns
    the bounding box of each region.

    Args:
        red_pixels: Numpy array from detect_red_pixels

    Returns:
        List of rectangles as (x_min, y_min, x_max, y_max, area) tuples, sorted by area (largest first)
    """
    if len(red_pixels[0]) == 0:
        return []

    import cv2

    # Create binary mask from red pixels
    y_coords, x_coords = red_pixels
    height = y_coords.max() + 1
    width = x_coords.max() + 1
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y_coords, x_coords] = 255

    # Morphological closing to connect thin borders into solid regions
    # This connects the 4 edges of a rectangular border into one region
    # Use a very large kernel to ensure border edges are connected
    kernel = np.ones((50, 50), np.uint8)
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_closed, connectivity=8)

    rectangles = []
    for label_id in range(1, num_labels):  # Skip background (label 0)
        x = stats[label_id, cv2.CC_STAT_LEFT]
        y = stats[label_id, cv2.CC_STAT_TOP]
        w = stats[label_id, cv2.CC_STAT_WIDTH]
        h = stats[label_id, cv2.CC_STAT_HEIGHT]
        area = w * h

        # Filter out very small regions (noise/artifacts)
        if area < 10000:
            continue

        rectangles.append((x, y, x + w, y + h, area))

    # Sort by area (largest first)
    rectangles.sort(key=lambda r: r[4], reverse=True)

    logger.debug(f"Found {len(rectangles)} connected region(s)")
    for i, (x_min, y_min, x_max, y_max, area) in enumerate(rectangles[:3]):  # Show top 3
        logger.debug(f"  Region {i+1}: {x_max-x_min}x{y_max-y_min} (area: {area}px²)")

    return rectangles


def calculate_bounding_box(red_pixels: np.ndarray) -> tuple:
    """Calculate bounding box from red pixel coordinates.

    For a rectangular border (4 thin edges), the bounding box of all red pixels
    gives us the enclosed rectangle.

    Args:
        red_pixels: Numpy array from detect_red_pixels

    Returns:
        Tuple of (x_min, y_min, x_max, y_max)
    """
    if len(red_pixels[0]) == 0:
        return None

    # Simple bounding box approach
    # When Gemini draws a rectangular border (4 edges), the min/max of all red pixels
    # gives us the corners of the rectangle
    y_coords, x_coords = red_pixels
    x_min = x_coords.min()
    y_min = y_coords.min()
    x_max = x_coords.max()
    y_max = y_coords.max()

    width = x_max - x_min
    height = y_max - y_min

    logger.debug(f"Bounding box: {width}x{height}")

    return (x_min, y_min, x_max, y_max)


def segment_with_imagen(page_image: bytes, map_type: str, output_path: str, temperature: float = 0.5) -> None:
    """Segment baked-in map using Gemini Imagen red perimeter technique.

    Args:
        page_image: PDF page rendered as PNG bytes
        map_type: "navigation_map" or "battle_map"
        output_path: Path to save cropped image
        temperature: Model temperature for generation (0-1, default 0.2)

    Raises:
        SegmentationError: If output validation fails
    """
    from src.pdf_processing.image_asset_processing.preprocess_image import remove_existing_red_pixels

    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI environment variable not set")

    client = genai.Client(api_key=api_key)

    # Create temp directory for debug files
    # If output_path is already in a "temp" directory, use it; otherwise create temp/
    output_dir = os.path.dirname(output_path)
    if os.path.basename(output_dir) == "temp":
        # Already in temp directory, use it
        temp_dir = output_dir
    else:
        # Create temp subdirectory
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

    # Preprocess: Remove any existing red pixels ONLY for the Gemini request
    # (we'll crop from the original image later)
    logger.info("Preprocessing: Removing existing red pixels for boundary detection...")
    preprocessed_image = remove_existing_red_pixels(page_image)

    # Debug: Save preprocessed image to temp/
    output_filename = os.path.basename(output_path)
    preprocessed_debug_path = os.path.join(temp_dir, output_filename.replace(".png", "_preprocessed.png"))
    Image.open(io.BytesIO(preprocessed_image)).save(preprocessed_debug_path)
    logger.debug(f"Saved preprocessed image to {preprocessed_debug_path}")

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

    prompt = "draw a tight bright red RGB(255,0,0) perimeter around the dnd map in this image. Do NOT include paragraphs. No padding"

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}/{MAX_RETRIES}: Generating red perimeter with Gemini Flash Image")

            # Step 1: Generate image with red perimeter using generate_content
            # Use preprocessed image (with red pixels removed) for boundary detection
            preprocessed_pil = Image.open(io.BytesIO(preprocessed_image))

            # Use specified temperature for border placement
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE"]
            )

            response = client.models.generate_content(
                model=IMAGEN_MODEL,
                contents=[preprocessed_pil, prompt],
                config=config
            )

            # Extract generated image from response
            generated_image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    generated_image_bytes = part.inline_data.data
                    break

            if generated_image_bytes is None:
                raise SegmentationError("No image data in response")

            # Debug: Save the generated image with red perimeter to temp/
            debug_path = os.path.join(temp_dir, output_filename.replace(".png", "_with_red_perimeter.png"))
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

            # Step 6: Quality check - verify word count
            cropped_buffer = io.BytesIO()
            cropped.save(cropped_buffer, format='PNG')
            cropped_bytes = cropped_buffer.getvalue()

            word_count, is_valid = check_word_count(cropped_bytes, max_words=100)
            if not is_valid:
                raise SegmentationError(f"Extracted region contains {word_count} words (max 100), likely included text paragraphs")

            logger.info(f"Quality check passed: {word_count} words (threshold: 100)")

            # Step 7: Save
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
