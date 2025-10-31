"""Tests for image preprocessing utilities."""
import pytest
import numpy as np
from PIL import Image
import io
from src.pdf_processing.image_asset_processing.preprocess_image import remove_existing_red_pixels


@pytest.mark.unit
class TestRemoveExistingRedPixels:
    def test_remove_red_pixels_from_image(self):
        """Test that red pixels are replaced with black."""
        # Create image with red pixels (R>200, G<50, B<50)
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        img_array[25:75, 25:75] = [255, 0, 0]  # Red square in center

        # Convert to bytes
        img = Image.fromarray(img_array)
        input_bytes = io.BytesIO()
        img.save(input_bytes, format='PNG')
        input_bytes = input_bytes.getvalue()

        # Process
        output_bytes = remove_existing_red_pixels(input_bytes)

        # Load result
        output_img = Image.open(io.BytesIO(output_bytes)).convert('RGB')
        output_array = np.array(output_img)

        # Verify red pixels are now black
        center_pixels = output_array[25:75, 25:75]
        assert np.all(center_pixels == [0, 0, 0])

    def test_no_red_pixels_unchanged(self):
        """Test that images without red pixels remain unchanged."""
        # Create image with blue and green pixels (no red)
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        img_array[25:50, 25:50] = [0, 0, 255]  # Blue square
        img_array[50:75, 50:75] = [0, 255, 0]  # Green square

        # Convert to bytes
        img = Image.fromarray(img_array)
        input_bytes = io.BytesIO()
        img.save(input_bytes, format='PNG')
        input_bytes = input_bytes.getvalue()

        # Process
        output_bytes = remove_existing_red_pixels(input_bytes)

        # Load result
        output_img = Image.open(io.BytesIO(output_bytes)).convert('RGB')
        output_array = np.array(output_img)

        # Verify unchanged
        assert np.array_equal(output_array, img_array)

    def test_preserves_non_red_colors(self):
        """Test that non-red colors are preserved."""
        # Create image with various colors
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        img_array[0:25, :] = [255, 255, 255]  # White
        img_array[25:50, :] = [100, 100, 100]  # Gray
        img_array[50:75, :] = [0, 0, 255]  # Blue
        img_array[75:100, :] = [255, 0, 0]  # Bright red (will be removed)

        # Convert to bytes
        img = Image.fromarray(img_array)
        input_bytes = io.BytesIO()
        img.save(input_bytes, format='PNG')
        input_bytes = input_bytes.getvalue()

        # Process
        output_bytes = remove_existing_red_pixels(input_bytes)

        # Load result
        output_img = Image.open(io.BytesIO(output_bytes)).convert('RGB')
        output_array = np.array(output_img)

        # Verify non-red colors preserved
        assert np.all(output_array[0:25, 0] == [255, 255, 255])  # White preserved
        assert np.all(output_array[25:50, 0] == [100, 100, 100])  # Gray preserved
        assert np.all(output_array[50:75, 0] == [0, 0, 255])  # Blue preserved
        # Red should be black now
        assert np.all(output_array[75:100, 0] == [0, 0, 0])

    def test_returns_valid_png_bytes(self):
        """Test that output is valid PNG bytes that can be loaded."""
        # Create simple image
        img_array = np.zeros((50, 50, 3), dtype=np.uint8)
        img_array[:, :] = [128, 128, 128]  # Gray

        # Convert to bytes
        img = Image.fromarray(img_array)
        input_bytes = io.BytesIO()
        img.save(input_bytes, format='PNG')
        input_bytes = input_bytes.getvalue()

        # Process
        output_bytes = remove_existing_red_pixels(input_bytes)

        # Verify it's valid PNG
        assert isinstance(output_bytes, bytes)
        assert len(output_bytes) > 0

        # Verify it can be loaded as PNG
        output_img = Image.open(io.BytesIO(output_bytes))
        assert output_img.format == 'PNG'
        assert output_img.size == (50, 50)

    def test_threshold_matches_detection(self):
        """Test that preprocessing threshold matches detection threshold (R>200, G<50, B<50)."""
        # Create image with pixels at the threshold boundary
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)

        # Pixel that should be removed: R=201, G=49, B=49 (just above threshold)
        img_array[10:20, 10:20] = [201, 49, 49]

        # Pixel that should NOT be removed: R=200, G=50, B=50 (at threshold)
        img_array[30:40, 30:40] = [200, 50, 50]

        # Pixel that should NOT be removed: R=199, G=49, B=49 (below threshold)
        img_array[50:60, 50:60] = [199, 49, 49]

        # Convert to bytes
        img = Image.fromarray(img_array)
        input_bytes = io.BytesIO()
        img.save(input_bytes, format='PNG')
        input_bytes = input_bytes.getvalue()

        # Process
        output_bytes = remove_existing_red_pixels(input_bytes)

        # Load result
        output_img = Image.open(io.BytesIO(output_bytes)).convert('RGB')
        output_array = np.array(output_img)

        # Verify: R=201 pixel should be removed (black)
        assert np.all(output_array[10:20, 10:20] == [0, 0, 0])

        # Verify: R=200 and R=199 pixels should be preserved (or close due to compression)
        # We allow some tolerance for PNG compression artifacts
        assert output_array[30, 30, 0] >= 190  # R channel preserved (with tolerance)
        assert output_array[50, 50, 0] >= 190  # R channel preserved (with tolerance)
