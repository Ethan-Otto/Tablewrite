"""Test segmentation reliability by running the same page 10 times."""
import asyncio
import io
import os
import fitz
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from PIL import Image
import pytesseract

load_dotenv()

# Test cases directory (relative to project root when running as: python dev/benchmark_segmentation.py)
TEST_CASES_DIR = Path("dev_output/segmentation_benchmarks/test_cases")


def check_extraction_quality(extracted_path: str, reference_path: str) -> dict:
    """Check extraction quality against reference.

    Quality criteria:
    1. Dimensions within 20% of reference in both axes

    Note: Text content is calculated but not used for quality determination
    (word count validation happens during segmentation at 100 word threshold)

    Args:
        extracted_path: Path to extracted image
        reference_path: Path to reference good extraction

    Returns:
        Dict with quality metrics
    """
    if not os.path.exists(reference_path):
        return {"quality": "unknown", "reason": "No reference image"}

    # Load images
    extracted_img = Image.open(extracted_path)
    reference_img = Image.open(reference_path)

    ex_w, ex_h = extracted_img.size
    ref_w, ref_h = reference_img.size

    # Check dimensions (20% tolerance)
    width_diff_pct = abs(ex_w - ref_w) / ref_w * 100
    height_diff_pct = abs(ex_h - ref_h) / ref_h * 100

    dimension_ok = width_diff_pct <= 20 and height_diff_pct <= 20

    # Check text content using OCR (for reporting only, not quality determination)
    try:
        extracted_text = pytesseract.image_to_string(extracted_img)
        reference_text = pytesseract.image_to_string(reference_img)

        ex_text_len = len(extracted_text.strip())
        ref_text_len = len(reference_text.strip())

        text_ratio = ex_text_len / ref_text_len if ref_text_len > 0 else 0
    except Exception as e:
        # If OCR fails, just report as unknown
        text_ratio = 0
        ex_text_len = 0
        ref_text_len = 0

    # Quality is based ONLY on dimensions (text validation happens at 100 word threshold during segmentation)
    quality = "good" if dimension_ok else "bad"

    return {
        "quality": quality,
        "dimension_ok": dimension_ok,
        "width_diff_pct": width_diff_pct,
        "height_diff_pct": height_diff_pct,
        "text_ratio": text_ratio,
        "extracted_text_len": ex_text_len,
        "reference_text_len": ref_text_len,
        "reason": [] if quality == "good" else [
            f"Dimensions off by {max(width_diff_pct, height_diff_pct):.1f}%" if not dimension_ok else None
        ]
    }


def segment_single_attempt_sync(page_image: bytes, attempt_num: int, output_dir: Path, temp_dir: Path, reference_path: str, temperature: float = 0.5):
    """Segment a single attempt (synchronous)."""
    from src.pdf_processing.image_asset_processing.segment_maps import segment_with_imagen

    # Initial output path in temp/ (will be moved after quality check)
    temp_output_path = str(temp_dir / f"attempt_{attempt_num:02d}_temp.png")

    try:
        segment_with_imagen(page_image, "navigation_map", temp_output_path, temperature=temperature)

        # Check if file was created and has reasonable size
        if os.path.exists(temp_output_path):
            file_size = os.path.getsize(temp_output_path)
            img = Image.open(temp_output_path)
            width, height = img.size

            # Success criteria: file exists, reasonable size, reasonable dimensions
            # Map should be roughly 1000-3000px wide and 800-2500px tall
            # (excluding full page which would be ~1700x2200)
            is_success = (
                file_size > 50000 and  # At least 50KB
                500 < width < 3500 and
                400 < height < 2500 and
                not (width > 1600 and height > 2000)  # Not full page
            )

            # Check quality if extraction succeeded
            quality_info = None
            quality_suffix = "fail"
            if is_success and os.path.exists(reference_path):
                quality_info = check_extraction_quality(temp_output_path, reference_path)
                if quality_info and quality_info["quality"] == "good":
                    quality_suffix = "pass"

            # Move file from temp/ to main directory with pass/fail suffix
            final_output_path = str(output_dir / f"attempt_{attempt_num:02d}_{quality_suffix}.png")
            os.rename(temp_output_path, final_output_path)
            # temp files (_preprocessed.png and _with_red_perimeter.png) remain in temp/

            return {
                "attempt": attempt_num,
                "success": is_success,
                "width": width,
                "height": height,
                "file_size": file_size,
                "output_path": final_output_path,
                "quality": quality_info
            }
        else:
            return {
                "attempt": attempt_num,
                "success": False,
                "error": "File not created"
            }

    except Exception as e:
        return {
            "attempt": attempt_num,
            "success": False,
            "error": str(e)
        }


async def main(test_case: str = "cragmaw_hideout", temperature: float = 0.5):
    # Setup
    from datetime import datetime

    # Load test case
    test_case_dir = TEST_CASES_DIR / test_case
    if not test_case_dir.exists():
        raise ValueError(f"Test case '{test_case}' not found in {TEST_CASES_DIR}")

    page_image_path = test_case_dir / "page.png"
    reference_image_path = test_case_dir / "reference.png"

    if not page_image_path.exists():
        raise ValueError(f"page.png not found in test case '{test_case}'")
    if not reference_image_path.exists():
        raise ValueError(f"reference.png not found in test case '{test_case}'")

    # Load page image
    page_image = page_image_path.read_bytes()

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"dev_output/segmentation_benchmarks/runs/{test_case}_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp subdirectory for intermediate files
    temp_dir = output_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    # Save preprocessed image once (shared across all attempts) in temp/
    from src.pdf_processing.image_asset_processing.preprocess_image import remove_existing_red_pixels
    preprocessed_image = remove_existing_red_pixels(page_image)
    preprocessed_path = temp_dir / "preprocessed.png"
    Image.open(io.BytesIO(preprocessed_image)).save(preprocessed_path)

    print("=" * 70)
    print("SEGMENTATION RELIABILITY TEST")
    print("=" * 70)
    print(f"Test Case: {test_case}")
    print(f"Temperature: {temperature}")
    print(f"Iterations: 10 (parallel using ThreadPoolExecutor)")
    print(f"Output: {output_dir}")
    print()

    # Run 10 attempts in parallel using thread pool
    print("Running 10 segmentation attempts in parallel...")
    from concurrent.futures import ThreadPoolExecutor
    import functools

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = [
            loop.run_in_executor(
                executor,
                functools.partial(segment_single_attempt_sync, page_image, i + 1, output_dir, temp_dir, str(reference_image_path), temperature)
            )
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)

    # Analyze results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    successes = []
    failures = []
    good_quality = []
    bad_quality = []

    for result in results:
        if result["success"]:
            successes.append(result)
            quality_info = result.get("quality")

            # Display result with quality
            quality_str = ""
            if quality_info:
                if quality_info["quality"] == "good":
                    quality_str = " [GOOD QUALITY]"
                    good_quality.append(result)
                else:
                    reasons = [r for r in quality_info["reason"] if r]
                    quality_str = f" [BAD QUALITY: {', '.join(reasons)}]"
                    bad_quality.append(result)

            print(f"✓ Attempt {result['attempt']:2d}: SUCCESS - {result['width']}x{result['height']} ({result['file_size']:,} bytes){quality_str}")
        else:
            failures.append(result)
            error = result.get("error", "Unknown error")
            print(f"✗ Attempt {result['attempt']:2d}: FAILED  - {error}")

    # Summary
    success_rate = len(successes) / len(results) * 100
    quality_rate = len(good_quality) / len(successes) * 100 if successes else 0

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total attempts:  {len(results)}")
    print(f"Successful:      {len(successes)}")
    print(f"Failed:          {len(failures)}")
    print(f"Success rate:    {success_rate:.1f}%")
    print()
    print(f"Quality tracking (of successful extractions):")
    print(f"  Good quality:  {len(good_quality)} ({quality_rate:.1f}%)")
    print(f"  Bad quality:   {len(bad_quality)}")
    if bad_quality:
        print(f"\n  Bad quality reasons:")
        for result in bad_quality:
            quality_info = result.get("quality", {})
            reasons = [r for r in quality_info.get("reason", []) if r]
            print(f"    Attempt {result['attempt']:2d}: {', '.join(reasons)}")

    if successes:
        avg_width = sum(r['width'] for r in successes) / len(successes)
        avg_height = sum(r['height'] for r in successes) / len(successes)
        avg_size = sum(r['file_size'] for r in successes) / len(successes)

        print(f"\nAverage dimensions (successful): {avg_width:.0f}x{avg_height:.0f}")
        print(f"Average file size (successful):  {avg_size:,.0f} bytes")

    # Show sample output paths
    if successes:
        print(f"\nSample successful extraction: {successes[0]['output_path']}")
    if failures and 'output_path' in failures[0]:
        print(f"Sample failed extraction:     {failures[0].get('output_path', 'N/A')}")

    print()

    # Return results for programmatic use
    return {
        "test_case": test_case,
        "temperature": temperature,
        "total": len(results),
        "successful": len(successes),
        "failed": len(failures),
        "success_rate": success_rate,
        "good_quality": len(good_quality),
        "bad_quality": len(bad_quality),
        "quality_rate": quality_rate
    }


if __name__ == "__main__":
    import sys

    # Parse command line arguments: [test_case] [temperature]
    # If no test case specified, run all test cases
    test_case = None  # None means run all
    temperature = 0.5  # default

    if len(sys.argv) > 1:
        test_case = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            temperature = float(sys.argv[2])
            if temperature < 0 or temperature > 1:
                print("Error: Temperature must be between 0 and 1")
                sys.exit(1)
        except ValueError:
            print("Error: Temperature must be a number")
            sys.exit(1)

    # Get available test cases
    available_cases = [d.name for d in TEST_CASES_DIR.iterdir() if d.is_dir()]

    if test_case is None:
        # Run all test cases
        print("=" * 70)
        print("RUNNING ALL TEST CASES")
        print("=" * 70)
        print(f"Test cases: {', '.join(available_cases)}")
        print(f"Temperature: {temperature}")
        print()

        all_results = []
        for case in available_cases:
            result = asyncio.run(main(case, temperature))
            all_results.append(result)

        # Print combined summary
        print("\n\n" + "=" * 70)
        print("COMBINED SUMMARY (ALL TEST CASES)")
        print("=" * 70)
        total_successful = sum(r['successful'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        total_good = sum(r['good_quality'] for r in all_results)
        total_bad = sum(r['bad_quality'] for r in all_results)
        total_attempts = total_successful + total_failed

        success_rate = (total_successful / total_attempts * 100) if total_attempts > 0 else 0
        quality_rate = (total_good / total_successful * 100) if total_successful > 0 else 0

        print(f"Total attempts:  {total_attempts}")
        print(f"Successful:      {total_successful} ({success_rate:.1f}%)")
        print(f"Failed:          {total_failed}")
        print()
        print(f"Quality (of successful extractions):")
        print(f"  Good quality:  {total_good} ({quality_rate:.1f}%)")
        print(f"  Bad quality:   {total_bad}")
        print()
    else:
        # Run single test case
        if test_case not in available_cases:
            print(f"Error: Test case '{test_case}' not found")
            print(f"Available test cases: {', '.join(available_cases)}")
            sys.exit(1)

        asyncio.run(main(test_case, temperature))
