#!/usr/bin/env python3
"""Test script to compare PyMuPDF extraction vs Imagen segmentation.

This script:
1. Extracts the map from page 1 using PyMuPDF
2. Extracts the same map using Gemini Imagen segmentation
3. Compares the results (dimensions, file sizes)
"""
import os
import sys
import fitz
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_processing.image_asset_processing.extract_maps import extract_image_with_pymupdf
from pdf_processing.image_asset_processing.segment_maps import segment_with_imagen, SegmentationError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    pdf_path = "data/pdfs/Strongholds_Followers_extraction_test.pdf"
    output_dir = "output/segmentation_test"
    os.makedirs(output_dir, exist_ok=True)

    # Open PDF and get first page
    doc = fitz.open(pdf_path)
    page = doc[0]

    print("=" * 70)
    print("Testing Map Extraction Comparison on Page 1")
    print("=" * 70)

    # Test 1: PyMuPDF Extraction
    print("\n[1/2] Testing PyMuPDF extraction...")
    pymupdf_output = os.path.join(output_dir, "page1_pymupdf.png")
    pymupdf_success = extract_image_with_pymupdf(page, pymupdf_output)

    if pymupdf_success:
        file_size = os.path.getsize(pymupdf_output)
        from PIL import Image
        img = Image.open(pymupdf_output)
        print(f"  ✓ PyMuPDF extraction succeeded")
        print(f"    - Dimensions: {img.width}x{img.height}")
        print(f"    - File size: {file_size:,} bytes")
        print(f"    - Saved to: {pymupdf_output}")
    else:
        print(f"  ✗ PyMuPDF extraction failed (no large images found)")

    # Test 2: Imagen Segmentation
    print("\n[2/2] Testing Gemini Imagen segmentation...")
    imagen_output = os.path.join(output_dir, "page1_imagen_segmented.png")

    try:
        # Render page to image for Imagen
        pix = page.get_pixmap(dpi=150)
        page_image_bytes = pix.pil_tobytes(format="PNG")

        segment_with_imagen(page_image_bytes, "navigation_map", imagen_output)

        file_size = os.path.getsize(imagen_output)
        from PIL import Image
        img = Image.open(imagen_output)
        print(f"  ✓ Imagen segmentation succeeded")
        print(f"    - Dimensions: {img.width}x{img.height}")
        print(f"    - File size: {file_size:,} bytes")
        print(f"    - Saved to: {imagen_output}")

    except SegmentationError as e:
        print(f"  ✗ Imagen segmentation failed: {e}")
    except Exception as e:
        print(f"  ✗ Imagen segmentation error: {e}")

    doc.close()

    # Comparison
    print("\n" + "=" * 70)
    if pymupdf_success and os.path.exists(imagen_output):
        print("COMPARISON RESULTS:")
        print("  Both methods succeeded!")
        print(f"\n  Compare the images visually:")
        print(f"  - PyMuPDF:  {pymupdf_output}")
        print(f"  - Imagen:   {imagen_output}")
        print("\n  Open both images to verify they extracted the same map.")
    elif pymupdf_success:
        print("RESULT: Only PyMuPDF succeeded (expected if Imagen doesn't work)")
    elif os.path.exists(imagen_output):
        print("RESULT: Only Imagen succeeded (PyMuPDF couldn't find embedded image)")
    else:
        print("RESULT: Both methods failed")

    print("=" * 70)

if __name__ == "__main__":
    main()
