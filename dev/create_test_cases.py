"""Create test input/output pairs for PyMuPDF extraction."""
import asyncio
import fitz
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from src.pdf_processing.image_asset_processing.extract_maps import extract_image_with_pymupdf_async

load_dotenv()

async def create_test_case(pdf_path: str, page_num: int, case_name: str):
    """Create input/output pair for a test case."""
    input_dir = Path("dev/tests_assets/pdf_processing/image_asset_processing/test_extract_maps/input_images")
    output_dir = Path("dev/tests_assets/pdf_processing/image_asset_processing/test_extract_maps/output_images")

    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Save full page as input
    pix = page.get_pixmap(dpi=150)
    input_path = input_dir / f"{case_name}_page{page_num + 1}.png"
    pix.save(str(input_path))
    print(f"✓ Saved input: {input_path.name}")

    # Extract map using PyMuPDF + AI classification
    output_path = output_dir / f"{case_name}_page{page_num + 1}_extracted.png"
    result = await extract_image_with_pymupdf_async(page, str(output_path), use_ai_classification=True)

    if result:
        print(f"✓ Saved output: {output_path.name}")
        # Get dimensions
        from PIL import Image
        img = Image.open(output_path)
        print(f"  Extracted map: {img.width}x{img.height}")
    else:
        print(f"✗ No map found on page {page_num + 1}")

    doc.close()
    return result

async def main():
    pdf_path = "data/pdfs/Strongholds_Followers_extraction_test.pdf"

    # Create test cases for pages 1, 2, and 6
    test_cases = [
        (0, "test_case_1"),  # Page 1
        (1, "test_case_2"),  # Page 2
        (5, "test_case_3"),  # Page 6
    ]

    print("Creating test cases...\n")
    for page_num, case_name in test_cases:
        print(f"{'='*60}")
        print(f"Test Case: {case_name} (Page {page_num + 1})")
        print(f"{'='*60}")
        await create_test_case(pdf_path, page_num, case_name)
        print()

if __name__ == "__main__":
    asyncio.run(main())
