#!/usr/bin/env python3
"""Debug tool to compare segmentation extraction against expected output.

Runs the segmentation process on an input image and compares the result
to the expected output image.
"""
import os
import sys
import logging
from PIL import Image
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_processing.image_asset_processing.segment_maps import segment_with_imagen, SegmentationError

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def compare_images(actual_path: str, expected_path: str):
    """Compare two images and report differences."""
    actual = Image.open(actual_path)
    expected = Image.open(expected_path)

    print("\n" + "=" * 70)
    print("IMAGE COMPARISON")
    print("=" * 70)

    print(f"\nActual (segmented):   {actual.width}x{actual.height} ({actual.mode})")
    print(f"Expected (reference): {expected.width}x{expected.height} ({expected.mode})")

    # Dimension comparison
    width_diff = abs(actual.width - expected.width)
    height_diff = abs(actual.height - expected.height)

    if actual.size == expected.size:
        print("✓ Dimensions match exactly")
    else:
        print(f"✗ Dimension difference: {width_diff}px width, {height_diff}px height")

    # Pixel similarity (if same size)
    if actual.size == expected.size and actual.mode == expected.mode:
        actual_array = np.array(actual)
        expected_array = np.array(expected)

        # Calculate pixel-wise difference
        diff = np.abs(actual_array.astype(int) - expected_array.astype(int))
        mean_diff = np.mean(diff)
        max_diff = np.max(diff)

        print(f"\nPixel differences:")
        print(f"  Mean: {mean_diff:.2f}")
        print(f"  Max:  {max_diff}")

        # Similarity percentage (0 = identical, 255 = completely different)
        similarity = 100 * (1 - mean_diff / 255)
        print(f"  Similarity: {similarity:.1f}%")

        if similarity > 95:
            print("✓ Images are very similar")
        elif similarity > 80:
            print("⚠ Images are similar but have noticeable differences")
        else:
            print("✗ Images are significantly different")

    print("=" * 70)

def main():
    input_name = "example_keep.png"
    test_dir = "tests_assets/pdf_processing/image_asset_processing/test_segment_maps"

    input_path = os.path.join(test_dir, "input_images", input_name)
    expected_path = os.path.join(test_dir, "output_images", input_name)
    actual_path = "output/debug_segmentation/actual_output.png"

    # Create output directory
    os.makedirs("output/debug_segmentation", exist_ok=True)

    print("=" * 70)
    print("SEGMENTATION DEBUGGING TOOL")
    print("=" * 70)
    print(f"\nInput:    {input_path}")
    print(f"Expected: {expected_path}")
    print(f"Output:   {actual_path}")

    # Load input image
    print("\n[1/3] Loading input image...")
    input_img = Image.open(input_path)
    print(f"  Loaded: {input_img.width}x{input_img.height} ({input_img.mode})")

    # Convert to bytes for segmentation
    import io
    img_buffer = io.BytesIO()
    input_img.save(img_buffer, format='PNG')
    input_bytes = img_buffer.getvalue()

    # Run segmentation
    print("\n[2/3] Running Gemini segmentation...")
    try:
        segment_with_imagen(input_bytes, "navigation_map", actual_path)
        print(f"  ✓ Segmentation succeeded")
    except SegmentationError as e:
        print(f"  ✗ Segmentation failed: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return 1

    # Compare results
    print("\n[3/3] Comparing with expected output...")
    compare_images(actual_path, expected_path)

    print(f"\n📁 Files saved to output/debug_segmentation/")
    print(f"   - actual_output.png (segmented result)")
    print(f"   - actual_output_with_red_perimeter.png (debug)")
    print(f"\n💡 Open both images to visually compare:")
    print(f"   Expected: {expected_path}")
    print(f"   Actual:   {actual_path}")

    return 0

if __name__ == "__main__":
    exit(main())
