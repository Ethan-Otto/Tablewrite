"""Test AI classification on PyMuPDF extraction candidates."""
import asyncio
import fitz
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from src.pdf_processing.image_asset_processing.detect_maps import is_map_image_async

load_dotenv()

MIN_IMAGE_SIZE = 200
PAGE_AREA_THRESHOLD = 0.10

async def main():
    pdf_path = "data/pdfs/Strongholds_Followers_extraction_test.pdf"
    output_dir = Path("dev/tests_assets/pdf_processing/image_asset_processing/test_extract_maps/extracted_images")

    doc = fitz.open(pdf_path)
    page = doc[0]

    # Calculate page area threshold
    page_area = page.rect.width * page.rect.height
    area_threshold = page_area * PAGE_AREA_THRESHOLD

    print(f"Page area: {page_area:.0f} px²")
    print(f"Area threshold (10%): {area_threshold:.0f} px²\n")

    # Extract all images meeting size thresholds
    images = page.get_images()
    candidates = []

    for idx, img_ref in enumerate(images):
        xref = img_ref[0]
        try:
            img_info = doc.extract_image(xref)
            img_width = img_info['width']
            img_height = img_info['height']
            img_area = img_width * img_height

            # Filter 1: Must be above minimum size
            if img_width < MIN_IMAGE_SIZE or img_height < MIN_IMAGE_SIZE:
                continue

            # Filter 2: Must occupy enough page area
            if img_area > area_threshold:
                candidates.append((idx + 1, img_info, img_area, img_width, img_height))
                print(f"Candidate {len(candidates)}: Image {idx + 1}")
                print(f"  Size: {img_width}x{img_height}")
                print(f"  Area: {img_area:,} px² ({100*img_area/page_area:.1f}% of page)")

                # Save candidate image
                img_path = output_dir / f"candidate_{len(candidates)}_image{idx+1}_{img_width}x{img_height}.{img_info['ext']}"
                with open(img_path, "wb") as f:
                    f.write(img_info['image'])
                print(f"  Saved: {img_path.name}\n")
        except Exception as e:
            print(f"Failed to extract image {idx + 1}: {e}")

    doc.close()

    # Classify all candidates with AI
    api_key = os.getenv("GeminiImageAPI")
    client = genai.Client(api_key=api_key)

    print(f"Classifying {len(candidates)} candidates with Gemini Vision...\n")

    classification_tasks = [
        is_map_image_async(client, img_info['image'], width, height)
        for _, img_info, _, width, height in candidates
    ]
    results = await asyncio.gather(*classification_tasks)

    # Report results
    print("=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)
    for (img_num, img_info, img_area, width, height), is_map in zip(candidates, results):
        status = "✓ IS A MAP" if is_map else "✗ NOT A MAP"
        print(f"\nImage {img_num}: {width}x{height} - {status}")
        if is_map:
            # Save the winning map
            map_path = output_dir / f"WINNER_image{img_num}_{width}x{height}.{img_info['ext']}"
            with open(map_path, "wb") as f:
                f.write(img_info['image'])
            print(f"  Saved as: {map_path.name}")

if __name__ == "__main__":
    asyncio.run(main())
