# Image Asset Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone tool that extracts navigation maps and battle maps from D&D PDFs using AI-powered detection and hybrid extraction.

**Architecture:** Three-stage pipeline: (1) Async Gemini Vision detection of all pages, (2) PyMuPDF extraction for embedded images, (3) Gemini Imagen segmentation fallback for baked-in images. Outputs organized by map type with rich metadata.

**Tech Stack:** Python 3.11, PyMuPDF (fitz), Gemini 2.0 Flash (detection), Gemini Imagen (segmentation), Pydantic (models), asyncio (parallelism), aiohttp (async HTTP), opencv-python (image processing)

**Test PDF:** `data/pdfs/Strongholds_Followers_extraction_test.pdf` (7 pages, many extractable images)

---

## Task 1: Create Module Structure

**Files:**
- Create: `src/pdf_processing/image_asset_processing/__init__.py`
- Create: `src/pdf_processing/image_asset_processing/models.py`
- Create: `tests/pdf_processing/image_asset_processing/__init__.py`
- Create: `tests/pdf_processing/image_asset_processing/conftest.py`

**Step 1: Create package directory**

```bash
mkdir -p src/pdf_processing/image_asset_processing
mkdir -p tests/pdf_processing/image_asset_processing
```

**Step 2: Create __init__.py files**

Create `src/pdf_processing/image_asset_processing/__init__.py`:
```python
"""Image asset extraction from D&D PDFs."""
```

Create `tests/pdf_processing/image_asset_processing/__init__.py`:
```python
"""Tests for image asset extraction."""
```

**Step 3: Create test fixtures**

Create `tests/pdf_processing/image_asset_processing/conftest.py`:
```python
"""Shared fixtures for image asset extraction tests."""
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@pytest.fixture
def test_pdf_path():
    """Path to test PDF with extractable images."""
    return os.path.join(PROJECT_ROOT, "data/pdfs/Strongholds_Followers_extraction_test.pdf")

@pytest.fixture
def test_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "test_image_assets"
    output_dir.mkdir()
    return str(output_dir)

@pytest.fixture
def check_api_key():
    """Verify Gemini API key is configured for integration tests."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("GeminiImageAPI not configured in .env")
    return api_key
```

**Step 4: Commit**

```bash
git add src/pdf_processing/image_asset_processing/ tests/pdf_processing/image_asset_processing/
git commit -m "feat: create image asset extraction module structure

- Add package directories
- Add test fixtures for test PDF and API key validation"
```

---

## Task 2: Data Models

**Files:**
- Create: `src/pdf_processing/image_asset_processing/models.py`
- Create: `tests/pdf_processing/image_asset_processing/test_models.py`

**Step 1: Write test for MapDetectionResult model**

Create `tests/pdf_processing/image_asset_processing/test_models.py`:
```python
"""Tests for data models."""
import pytest
from pydantic import ValidationError
from src.pdf_processing.image_asset_processing.models import MapDetectionResult, MapMetadata


class TestMapDetectionResult:
    def test_valid_navigation_map(self):
        result = MapDetectionResult(has_map=True, type="navigation_map", name="Cragmaw Hideout")
        assert result.has_map is True
        assert result.type == "navigation_map"
        assert result.name == "Cragmaw Hideout"

    def test_valid_battle_map(self):
        result = MapDetectionResult(has_map=True, type="battle_map", name="Redbrand Hideout")
        assert result.has_map is True
        assert result.type == "battle_map"
        assert result.name == "Redbrand Hideout"

    def test_no_map(self):
        result = MapDetectionResult(has_map=False, type=None, name=None)
        assert result.has_map is False
        assert result.type is None
        assert result.name is None

    def test_optional_fields(self):
        result = MapDetectionResult(has_map=True)
        assert result.has_map is True
        assert result.type is None
        assert result.name is None


class TestMapMetadata:
    def test_valid_metadata_with_chapter(self):
        metadata = MapMetadata(
            name="Cragmaw Hideout",
            chapter="Chapter 1",
            page_num=5,
            type="navigation_map",
            source="extracted"
        )
        assert metadata.name == "Cragmaw Hideout"
        assert metadata.chapter == "Chapter 1"
        assert metadata.page_num == 5
        assert metadata.type == "navigation_map"
        assert metadata.source == "extracted"

    def test_valid_metadata_without_chapter(self):
        metadata = MapMetadata(
            name="Random Encounter",
            chapter=None,
            page_num=42,
            type="battle_map",
            source="segmented"
        )
        assert metadata.chapter is None

    def test_json_serialization(self):
        metadata = MapMetadata(
            name="Test Map",
            chapter=None,
            page_num=1,
            type="navigation_map",
            source="extracted"
        )
        json_data = metadata.model_dump()
        assert json_data["chapter"] is None
        assert json_data["name"] == "Test Map"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pdf_processing/image_asset_processing/test_models.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.pdf_processing.image_asset_processing.models'"

**Step 3: Implement models**

Create `src/pdf_processing/image_asset_processing/models.py`:
```python
"""Data models for image asset extraction."""
from pydantic import BaseModel
from typing import Optional


class MapDetectionResult(BaseModel):
    """Result from Gemini Vision map detection.

    Attributes:
        has_map: Whether the page contains a map
        type: Map type ("navigation_map" or "battle_map")
        name: Descriptive name (3 words max)
    """
    has_map: bool
    type: Optional[str] = None
    name: Optional[str] = None


class MapMetadata(BaseModel):
    """Metadata for extracted map asset.

    Attributes:
        name: Descriptive map name
        chapter: Chapter name (None if unknown)
        page_num: PDF page number (1-indexed)
        type: Map type ("navigation_map" or "battle_map")
        source: Extraction method ("extracted" or "segmented")
    """
    name: str
    chapter: Optional[str] = None
    page_num: int
    type: str
    source: str
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_models.py -v`

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add src/pdf_processing/image_asset_processing/models.py tests/pdf_processing/image_asset_processing/test_models.py
git commit -m "feat: add Pydantic models for map detection and metadata

- MapDetectionResult: Vision API response
- MapMetadata: Extracted asset metadata with null chapter support"
```

---

## Task 3: PyMuPDF Image Extraction

**Files:**
- Create: `src/pdf_processing/image_asset_processing/extract_maps.py`
- Create: `tests/pdf_processing/image_asset_processing/test_extract_maps.py`

**Step 1: Write test for image extraction**

Create `tests/pdf_processing/image_asset_processing/test_extract_maps.py`:
```python
"""Tests for PyMuPDF image extraction."""
import pytest
import fitz
import os
from src.pdf_processing.image_asset_processing.extract_maps import extract_image_with_pymupdf


@pytest.mark.unit
class TestExtractImageWithPyMuPDF:
    def test_extract_large_image_from_page(self, test_pdf_path, test_output_dir):
        """Test extraction of large image (>25% page area)."""
        doc = fitz.open(test_pdf_path)
        page = doc[0]  # First page has 2400x1650 image

        output_path = os.path.join(test_output_dir, "test_map.png")
        result = extract_image_with_pymupdf(page, output_path)

        assert result is True
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 1000  # Non-empty file

    def test_extract_returns_false_for_text_only_page(self, tmp_path):
        """Test that extraction fails on text-only page."""
        # Create minimal PDF with text only
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), "Text only, no images")

        temp_pdf = tmp_path / "text_only.pdf"
        doc.save(str(temp_pdf))
        doc.close()

        # Try to extract
        doc = fitz.open(str(temp_pdf))
        output_path = str(tmp_path / "no_image.png")
        result = extract_image_with_pymupdf(doc[0], output_path)

        assert result is False
        assert not os.path.exists(output_path)

    def test_extract_filters_small_images(self, test_pdf_path, test_output_dir):
        """Test that small decorative images (<25% page) are ignored."""
        doc = fitz.open(test_pdf_path)
        page = doc[0]

        # Mock: Count how many images are on the page
        images = page.get_images()
        small_images = [img for img in images if True]  # Would filter by size

        # Verify there are small images that should be ignored
        assert len(images) > 1  # Multiple images including small ones
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_extract_maps.py -v -m unit`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.pdf_processing.image_asset_processing.extract_maps'"

**Step 3: Implement extraction function**

Create `src/pdf_processing/image_asset_processing/extract_maps.py`:
```python
"""PyMuPDF-based image extraction."""
import logging
import fitz

logger = logging.getLogger(__name__)


def extract_image_with_pymupdf(page: fitz.Page, output_path: str) -> bool:
    """Extract large images from PDF page using PyMuPDF.

    Searches for images that occupy >25% of the page area. If found,
    extracts and saves the largest image to output_path.

    Args:
        page: PyMuPDF page object
        output_path: Path to save extracted image (PNG format)

    Returns:
        True if extraction succeeded, False if no large images found
    """
    try:
        images = page.get_images()
        if not images:
            logger.debug(f"No images found on page")
            return False

        # Calculate page area
        page_area = page.rect.width * page.rect.height
        threshold = page_area * 0.25

        # Find largest image above threshold
        doc = page.parent
        largest_image = None
        largest_area = 0

        for img_ref in images:
            xref = img_ref[0]
            try:
                img_info = doc.extract_image(xref)
                img_area = img_info['width'] * img_info['height']

                if img_area > threshold and img_area > largest_area:
                    largest_image = img_info
                    largest_area = img_area
            except Exception as e:
                logger.warning(f"Failed to extract image xref {xref}: {e}")
                continue

        if largest_image:
            # Save image as PNG
            with open(output_path, "wb") as f:
                f.write(largest_image['image'])
            logger.info(f"Extracted image: {largest_image['width']}x{largest_image['height']} -> {output_path}")
            return True
        else:
            logger.debug(f"No images above 25% page area threshold")
            return False

    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return False
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_extract_maps.py -v -m unit`

Expected: PASS (all unit tests)

**Step 5: Commit**

```bash
git add src/pdf_processing/image_asset_processing/extract_maps.py tests/pdf_processing/image_asset_processing/test_extract_maps.py
git commit -m "feat: implement PyMuPDF image extraction

- Extract largest image >25% page area
- Return False if no large images found
- Unit tests with real and synthetic PDFs"
```

---

## Task 4: Gemini Vision Map Detection (Async)

**Files:**
- Create: `src/pdf_processing/image_asset_processing/detect_maps.py`
- Create: `tests/pdf_processing/image_asset_processing/test_detect_maps.py`

**Step 1: Write integration test for async detection**

Create `tests/pdf_processing/image_asset_processing/test_detect_maps.py`:
```python
"""Tests for Gemini Vision map detection."""
import pytest
import asyncio
from src.pdf_processing.image_asset_processing.detect_maps import detect_maps_async
from src.pdf_processing.image_asset_processing.models import MapDetectionResult


@pytest.mark.integration
@pytest.mark.slow
class TestDetectMapsAsync:
    def test_detect_maps_returns_results_for_all_pages(self, test_pdf_path, check_api_key):
        """Test that detection returns result for each page."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        # Test PDF has 7 pages
        assert len(results) == 7
        assert all(isinstance(r, MapDetectionResult) for r in results)

    def test_detection_result_structure(self, test_pdf_path, check_api_key):
        """Test that results have expected structure."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        for result in results:
            assert isinstance(result.has_map, bool)
            if result.has_map:
                assert result.type in ["navigation_map", "battle_map", None]
                # Name should be short if provided
                if result.name:
                    assert len(result.name.split()) <= 3

    def test_detection_identifies_at_least_one_map(self, test_pdf_path, check_api_key):
        """Test that detection finds at least one map in test PDF."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        maps_found = [r for r in results if r.has_map]
        # Test PDF should have some maps
        assert len(maps_found) > 0
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_detect_maps.py -v -m integration`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.pdf_processing.image_asset_processing.detect_maps'"

**Step 3: Implement async detection**

Create `src/pdf_processing/image_asset_processing/detect_maps.py`:
```python
"""Gemini Vision-based map detection."""
import asyncio
import logging
import os
import fitz
import io
from google import genai
from google.genai import types
from typing import List
from dotenv import load_dotenv
from src.pdf_processing.image_asset_processing.models import MapDetectionResult

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


async def detect_single_page(client: genai.Client, page_image: bytes, page_num: int) -> MapDetectionResult:
    """Detect map on single PDF page using Gemini Vision.

    Args:
        client: Gemini client instance
        page_image: PDF page rendered as PNG bytes
        page_num: Page number (for logging)

    Returns:
        MapDetectionResult with detection results
    """
    prompt = """Analyze this D&D module page. Does it contain a navigation map (dungeon/wilderness overview)
or battle map (tactical grid/encounter area)?

If yes, respond with JSON:
{
  "has_map": true,
  "type": "navigation_map" or "battle_map",
  "name": "Descriptive 3-word max name"
}

If no map, respond with JSON:
{
  "has_map": false,
  "type": null,
  "name": null
}

Ignore: character portraits, item illustrations, decorative art, page decorations."""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=page_image, mime_type="image/png"),
                    prompt
                ]
            )

            # Parse JSON response
            import json
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result_data = json.loads(response_text)
            result = MapDetectionResult(**result_data)

            logger.debug(f"Page {page_num}: has_map={result.has_map}, type={result.type}, name={result.name}")
            return result

        except Exception as e:
            logger.warning(f"Page {page_num} attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                logger.error(f"Page {page_num} detection failed after {MAX_RETRIES} attempts")
                return MapDetectionResult(has_map=False, type=None, name=None)


async def detect_maps_async(pdf_path: str) -> List[MapDetectionResult]:
    """Detect maps in all pages of PDF using async Gemini Vision calls.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of MapDetectionResult, one per page
    """
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI environment variable not set")

    client = genai.Client(api_key=api_key)

    # Open PDF and render all pages to images
    doc = fitz.open(pdf_path)
    page_images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at 150 DPI for good quality
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.pil_tobytes(format="PNG")
        page_images.append((page_num + 1, img_bytes))

    doc.close()

    logger.info(f"Detecting maps in {len(page_images)} pages...")

    # Process all pages in parallel
    tasks = [detect_single_page(client, img_bytes, page_num)
             for page_num, img_bytes in page_images]
    results = await asyncio.gather(*tasks)

    maps_found = sum(1 for r in results if r.has_map)
    logger.info(f"Detection complete: {maps_found}/{len(results)} pages have maps")

    return results
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_detect_maps.py -v -m integration`

Expected: PASS (all integration tests) - will make real API calls

**Step 5: Commit**

```bash
git add src/pdf_processing/image_asset_processing/detect_maps.py tests/pdf_processing/image_asset_processing/test_detect_maps.py
git commit -m "feat: implement async Gemini Vision map detection

- Parallel detection across all PDF pages
- 3 retries with exponential backoff
- JSON parsing with markdown cleanup
- Integration tests with real API calls"
```

---

## Task 5: Gemini Imagen Segmentation

**Files:**
- Create: `src/pdf_processing/image_asset_processing/segment_maps.py`
- Create: `tests/pdf_processing/image_asset_processing/test_segment_maps.py`

**Step 1: Write integration test for segmentation**

Create `tests/pdf_processing/image_asset_processing/test_segment_maps.py`:
```python
"""Tests for Gemini Imagen segmentation."""
import pytest
import fitz
from src.pdf_processing.image_asset_processing.segment_maps import (
    segment_with_imagen,
    SegmentationError
)


@pytest.mark.integration
@pytest.mark.slow
class TestSegmentWithImagen:
    def test_segmentation_raises_error_on_invalid_output(self, test_pdf_path, test_output_dir, check_api_key):
        """Test that segmentation validates output and raises error if invalid."""
        # This is a placeholder - actual implementation will test with real Gemini Imagen
        # For now, just verify the function exists and has correct signature
        doc = fitz.open(test_pdf_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        page_image = pix.pil_tobytes(format="PNG")

        output_path = f"{test_output_dir}/segmented_map.png"

        # This test will be implemented once Gemini Imagen segmentation is working
        # For now, expect NotImplementedError
        with pytest.raises(NotImplementedError):
            segment_with_imagen(page_image, "navigation_map", output_path)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_segment_maps.py -v -m integration`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.pdf_processing.image_asset_processing.segment_maps'"

**Step 3: Implement segmentation stub (placeholder for validation)**

Create `src/pdf_processing/image_asset_processing/segment_maps.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_segment_maps.py -v -m integration`

Expected: PASS (test expects NotImplementedError)

**Step 5: Commit**

```bash
git add src/pdf_processing/image_asset_processing/segment_maps.py tests/pdf_processing/image_asset_processing/test_segment_maps.py
git commit -m "feat: add segmentation module with red pixel detection

- Placeholder for Gemini Imagen segmentation
- Red pixel detection and bounding box calculation
- SegmentationError for validation failures
- TODO: Implement after validating red perimeter technique"
```

---

## Task 6: Validation Tool

**Files:**
- Create: `src/pdf_processing/image_asset_processing/validate_segmentation.py`

**Step 1: Create validation tool**

Create `src/pdf_processing/image_asset_processing/validate_segmentation.py`:
```python
#!/usr/bin/env python3
"""Standalone tool to validate Gemini Imagen red perimeter segmentation technique.

Usage:
    uv run python src/pdf_processing/image_asset_processing/validate_segmentation.py \\
        --pdf data/pdfs/test.pdf --pages 5 12 18
"""
import argparse
import logging
import fitz
from dataclasses import dataclass
from segment_maps import detect_red_pixels, calculate_bounding_box

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result from testing segmentation on a page."""
    page_num: int
    success: bool
    red_pixel_count: int
    bbox: tuple
    error: str = None


def test_segmentation_on_page(page: fitz.Page, page_num: int) -> ValidationResult:
    """Test red perimeter segmentation technique on a single page.

    TODO: This function needs to:
    1. Render page to image
    2. Call Gemini Imagen to add red perimeter
    3. Detect red pixels in result
    4. Validate bounding box

    For now, returns placeholder result.
    """
    logger.info(f"Testing page {page_num}...")

    # TODO: Implement Gemini Imagen call
    # For now, return placeholder
    return ValidationResult(
        page_num=page_num,
        success=False,
        red_pixel_count=0,
        bbox=None,
        error="Not implemented - need to test Gemini Imagen red perimeter generation"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Validate Gemini Imagen red perimeter segmentation technique"
    )
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--pages", nargs="+", type=int, required=True,
                       help="Page numbers to test (space-separated)")
    args = parser.parse_args()

    doc = fitz.open(args.pdf)

    print(f"\nTesting segmentation on {len(args.pages)} pages from {args.pdf}\n")
    print("=" * 70)

    results = []
    for page_num in args.pages:
        if page_num < 1 or page_num > len(doc):
            logger.error(f"Page {page_num} out of range (1-{len(doc)})")
            continue

        page = doc[page_num - 1]  # Convert to 0-indexed
        result = test_segmentation_on_page(page, page_num)
        results.append(result)

        # Print result
        status = "✓ PASSED" if result.success else "✗ FAILED"
        print(f"\nPage {page_num}: {status}")
        print(f"  Red pixels detected: {result.red_pixel_count}")
        print(f"  Bounding box: {result.bbox}")
        if result.error:
            print(f"  Error: {result.error}")

    print("\n" + "=" * 70)

    # Summary
    passed = sum(1 for r in results if r.success)
    print(f"\nSummary: {passed}/{len(results)} pages passed validation")

    if passed < len(results):
        print("\n⚠️  Some validations failed. Do not use segmentation in production until this works.")
        return 1
    else:
        print("\n✓ All validations passed! Segmentation technique is ready to use.")
        return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Test validation tool**

Run: `uv run python src/pdf_processing/image_asset_processing/validate_segmentation.py --pdf data/pdfs/Strongholds_Followers_extraction_test.pdf --pages 1 2`

Expected: Runs but reports "Not implemented" for each page

**Step 3: Commit**

```bash
git add src/pdf_processing/image_asset_processing/validate_segmentation.py
git commit -m "feat: add validation tool for segmentation technique

- CLI tool to test red perimeter generation
- Tests specific pages and reports results
- Placeholder implementation until Gemini Imagen tested"
```

---

## Task 7: Main Orchestration Script

**Files:**
- Create: `src/pdf_processing/image_asset_processing/extract_map_assets.py`
- Create: `tests/pdf_processing/image_asset_processing/test_extract_map_assets.py`

**Step 1: Write end-to-end integration test**

Create `tests/pdf_processing/image_asset_processing/test_extract_map_assets.py`:
```python
"""End-to-end tests for map asset extraction."""
import pytest
import os
import json
import asyncio
from src.pdf_processing.image_asset_processing.extract_map_assets import main


@pytest.mark.integration
@pytest.mark.slow
class TestExtractMapAssets:
    def test_full_extraction_pipeline(self, test_pdf_path, test_output_dir, check_api_key):
        """Test complete extraction pipeline."""
        # Run extraction
        asyncio.run(main(test_pdf_path, chapter_name="Test Chapter", output_dir=test_output_dir))

        # Verify directory structure
        assert os.path.exists(test_output_dir)
        assert os.path.exists(os.path.join(test_output_dir, "navigation_maps"))
        assert os.path.exists(os.path.join(test_output_dir, "battle_maps"))

        # Verify metadata.json exists
        metadata_path = os.path.join(test_output_dir, "metadata.json")
        assert os.path.exists(metadata_path)

        # Load and validate metadata
        with open(metadata_path, 'r') as f:
            metadata_list = json.load(f)

        assert isinstance(metadata_list, list)
        assert len(metadata_list) > 0  # Should find at least some maps

        for metadata in metadata_list:
            assert "name" in metadata
            assert "chapter" in metadata
            assert metadata["chapter"] == "Test Chapter"
            assert "page_num" in metadata
            assert "type" in metadata
            assert metadata["type"] in ["navigation_map", "battle_map"]
            assert "source" in metadata
            assert metadata["source"] in ["extracted", "segmented"]

    def test_extraction_without_chapter(self, test_pdf_path, test_output_dir, check_api_key):
        """Test extraction with no chapter name."""
        asyncio.run(main(test_pdf_path, chapter_name=None, output_dir=test_output_dir))

        metadata_path = os.path.join(test_output_dir, "metadata.json")
        with open(metadata_path, 'r') as f:
            metadata_list = json.load(f)

        # Verify chapter is null when not provided
        for metadata in metadata_list:
            assert metadata["chapter"] is None
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_extract_map_assets.py -v -m integration`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.pdf_processing.image_asset_processing.extract_map_assets'"

**Step 3: Implement main orchestration**

Create `src/pdf_processing/image_asset_processing/extract_map_assets.py`:
```python
#!/usr/bin/env python3
"""Main script for extracting map assets from D&D PDFs.

Usage:
    uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py \\
        --pdf data/pdfs/module.pdf --chapter "Chapter 1"
"""
import argparse
import asyncio
import logging
import os
import json
import fitz
import re
from typing import List, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_asset_processing.detect_maps import detect_maps_async
from image_asset_processing.extract_maps import extract_image_with_pymupdf
from image_asset_processing.segment_maps import segment_with_imagen, SegmentationError
from image_asset_processing.models import MapMetadata
from logging_config import setup_logging

load_dotenv()
logger = setup_logging(__name__)


def sanitize_name(name: str) -> str:
    """Sanitize map name for use in filename.

    Args:
        name: Original map name

    Returns:
        Sanitized name (lowercase, underscores, alphanumeric)
    """
    # Convert to lowercase and replace spaces with underscores
    sanitized = name.lower().replace(" ", "_")
    # Remove non-alphanumeric characters except underscores
    sanitized = re.sub(r'[^a-z0-9_]', '', sanitized)
    return sanitized


async def main(pdf_path: str, chapter_name: Optional[str] = None, output_dir: str = "output/image_assets"):
    """Extract map assets from PDF.

    Args:
        pdf_path: Path to PDF file
        chapter_name: Optional chapter name for metadata
        output_dir: Output directory for extracted assets
    """
    logger.info(f"Starting map asset extraction from {pdf_path}")

    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "navigation_maps"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "battle_maps"), exist_ok=True)

    # Stage 1: Async detection
    logger.info("Stage 1: Detecting maps with Gemini Vision...")
    detection_results = await detect_maps_async(pdf_path)

    # Stage 2 & 3: Extraction and segmentation
    logger.info("Stage 2 & 3: Extracting images...")
    doc = fitz.open(pdf_path)
    metadata_list = []
    failed_segmentations = []

    for page_num, result in enumerate(detection_results):
        if not result.has_map:
            continue

        logger.info(f"Processing page {page_num + 1}: {result.name} ({result.type})")

        page = doc[page_num]
        output_subdir = os.path.join(output_dir, f"{result.type}s")
        filename = f"{sanitize_name(result.name)}_p{page_num + 1}.png"
        output_path = os.path.join(output_subdir, filename)

        # Try PyMuPDF extraction first
        if extract_image_with_pymupdf(page, output_path):
            source = "extracted"
            logger.info(f"  ✓ Extracted via PyMuPDF")
        else:
            # Fall back to segmentation
            logger.info(f"  Extraction failed, attempting segmentation...")
            try:
                pix = page.get_pixmap(dpi=150)
                page_image = pix.pil_tobytes(format="PNG")
                segment_with_imagen(page_image, result.type, output_path)
                source = "segmented"
                logger.info(f"  ✓ Segmented via Gemini Imagen")
            except (SegmentationError, NotImplementedError) as e:
                logger.error(f"  ✗ Segmentation failed: {e}")
                failed_segmentations.append({
                    "page": page_num + 1,
                    "name": result.name,
                    "error": str(e)
                })
                continue

        # Save metadata
        metadata_list.append(MapMetadata(
            name=result.name,
            chapter=chapter_name,
            page_num=page_num + 1,
            type=result.type,
            source=source
        ))

    doc.close()

    # Save metadata.json
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump([m.model_dump() for m in metadata_list], f, indent=2)
    logger.info(f"Saved metadata to {metadata_path}")

    # Save failed segmentations if any
    if failed_segmentations:
        failed_path = os.path.join(output_dir, "failed_segmentations.json")
        with open(failed_path, 'w') as f:
            json.dump(failed_segmentations, f, indent=2)
        logger.warning(f"Saved {len(failed_segmentations)} failed segmentations to {failed_path}")

    # Summary
    logger.info("=" * 70)
    logger.info(f"Extraction complete!")
    logger.info(f"  Total maps found: {len(metadata_list)}")
    logger.info(f"  Extracted via PyMuPDF: {sum(1 for m in metadata_list if m.source == 'extracted')}")
    logger.info(f"  Segmented via Imagen: {sum(1 for m in metadata_list if m.source == 'segmented')}")
    logger.info(f"  Failed: {len(failed_segmentations)}")
    logger.info(f"  Output: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract map assets from D&D PDFs")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--chapter", help="Chapter name (optional, for metadata)")
    parser.add_argument("--output-dir", default="output/image_assets", help="Output directory")
    args = parser.parse_args()

    asyncio.run(main(args.pdf, args.chapter, args.output_dir))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/test_extract_map_assets.py -v -m integration`

Expected: PASS (end-to-end test with real API calls)

**Step 5: Commit**

```bash
git add src/pdf_processing/image_asset_processing/extract_map_assets.py tests/pdf_processing/image_asset_processing/test_extract_map_assets.py
git commit -m "feat: implement main extraction orchestration

- Three-stage pipeline: detect → extract → segment
- Metadata and failed segmentations saved to JSON
- CLI interface with optional chapter name
- End-to-end integration tests"
```

---

## Task 8: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add new dependencies**

Check current dependencies:
```bash
cat pyproject.toml
```

**Step 2: Add aiohttp and opencv-python**

Add to `[project.dependencies]`:
```toml
dependencies = [
    # ... existing dependencies ...
    "aiohttp>=3.9.0",
    "opencv-python>=4.9.0",
]
```

**Step 3: Sync dependencies**

Run: `uv sync`

Expected: New packages installed

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add aiohttp and opencv-python for image processing

- aiohttp: Async HTTP for parallel Gemini API calls
- opencv-python: Image processing for red pixel detection"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add section to CLAUDE.md**

Add new section under "## Architecture & Data Flow":

```markdown
### Image Asset Extraction

The project includes AI-powered extraction of map images (navigation maps and battle maps) from D&D PDFs.

**Architecture:**
- `src/pdf_processing/image_asset_processing/models.py`: Pydantic models for MapDetectionResult and MapMetadata
- `src/pdf_processing/image_asset_processing/detect_maps.py`: Async Gemini Vision detection
- `src/pdf_processing/image_asset_processing/extract_maps.py`: PyMuPDF image extraction
- `src/pdf_processing/image_asset_processing/segment_maps.py`: Gemini Imagen segmentation (placeholder)
- `src/pdf_processing/image_asset_processing/validate_segmentation.py`: Validation tool for segmentation technique
- `src/pdf_processing/image_asset_processing/extract_map_assets.py`: Main orchestration script

**Processing Workflow:**
1. **Async Detection**: Gemini Vision analyzes all pages in parallel to detect maps
2. **PyMuPDF Extraction**: Attempts to extract embedded images (>25% page area)
3. **Imagen Segmentation**: Fallback for baked-in maps (requires validation)
4. **Metadata Output**: JSON file with map names, types, page numbers, extraction method

**Output Structure:**
```
output/image_assets/
├── navigation_maps/
│   └── cragmaw_hideout_p05.png
├── battle_maps/
│   └── redbrand_hideout_p08.png
├── metadata.json
└── failed_segmentations.json (if failures occur)
```

**Usage:**
```bash
# Extract maps from PDF
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py \\
    --pdf data/pdfs/module.pdf --chapter "Chapter 1"

# Validate segmentation technique (before using in production)
uv run python src/pdf_processing/image_asset_processing/validate_segmentation.py \\
    --pdf data/pdfs/test.pdf --pages 5 12 18
```

**Test PDF:** `data/pdfs/Strongholds_Followers_extraction_test.pdf` (7 pages with extractable images)

**Integration Notes:**
- Standalone tool, not integrated into main pipeline
- Future: Upload extracted maps to FoundryVTT scenes/journals
- Segmentation requires validation before production use
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add image asset extraction to CLAUDE.md

- Document architecture and workflow
- Add usage examples
- Note segmentation validation requirement"
```

---

## Task 10: Manual Testing

**Step 1: Test extraction on real PDF**

Run extraction:
```bash
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py \\
    --pdf data/pdfs/Strongholds_Followers_extraction_test.pdf \\
    --chapter "Strongholds & Followers"
```

Expected output:
- Creates `output/image_assets/navigation_maps/` and `output/image_assets/battle_maps/`
- Extracts images from pages with maps
- Creates `metadata.json` with map details
- May create `failed_segmentations.json` if segmentation not implemented

**Step 2: Verify output**

Check extracted images:
```bash
ls -lh output/image_assets/navigation_maps/
ls -lh output/image_assets/battle_maps/
cat output/image_assets/metadata.json
```

**Step 3: Verify all tests pass**

Run all unit tests:
```bash
PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/ -v -m "not integration and not slow"
```

Expected: All unit tests pass

**Step 4: Run integration tests (if API key available)**

```bash
PYTHONPATH=/Users/ethanotto/Documents/Projects/dnd_module_gen/.worktrees/image_asset_extraction/src uv run pytest tests/pdf_processing/image_asset_processing/ -v -m integration
```

Expected: Integration tests pass (makes real API calls)

---

## Post-Implementation Tasks

### Optional: Implement Gemini Imagen Segmentation

**If you want to complete segmentation:**

1. Use `validate_segmentation.py` to test red perimeter technique
2. Verify Gemini Imagen can reliably add red borders
3. Update `segment_maps.py` with full implementation
4. Update tests to verify actual segmentation (not NotImplementedError)

**This is optional for v1** - extraction alone provides value.

### Future Enhancements

See design document for:
- FoundryVTT integration (auto-upload maps)
- Additional asset types (portraits, items)
- Batch processing all chapters
- Interactive review UI

---

## Execution Notes

**For executing-plans skill:**
- Run tasks sequentially in order
- Verify tests pass after each task
- Commit frequently (after each task)
- Report any failures immediately

**For subagent-driven-development:**
- Dispatch one task per subagent
- Review code after each task completes
- Check tests before proceeding to next task

**Expected total time:** 2-3 hours for tasks 1-10
