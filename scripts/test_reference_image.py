#!/usr/bin/env python3
"""Test the reference_image parameter."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from util.parallel_image_gen import generate_images_parallel


async def test_reference_image():
    """Test using a reference image for generation."""
    print("\n=== Testing reference_image Parameter ===\n")

    # Use a simple test image
    reference_path = Path("output/test_ref.png")

    if not reference_path.exists():
        print(f"⚠️  Reference image not found: {reference_path}")
        print("Run test_make_run.py first to generate a reference image")
        return

    prompts = [
        "Transform this into a vibrant fantasy painting",
        "Make this look like a watercolor illustration"
    ]

    output_dir = Path("output/test_reference_image")

    print(f"Reference image: {reference_path}")
    print(f"Generating {len(prompts)} images conditioned on reference...")
    print(f"Output directory: {output_dir}\n")

    results = await generate_images_parallel(
        prompts,
        reference_image=str(reference_path),
        save_dir=output_dir,
        make_run=True,
        max_concurrent=2
    )

    successful = [r for r in results if r is not None]
    print(f"\n✓ Generated {len(successful)}/{len(prompts)} images")

    # Check directory structure
    print(f"\nDirectory structure:")
    if output_dir.exists():
        for subdir in sorted(output_dir.iterdir()):
            if subdir.is_dir():
                print(f"  📁 {subdir.name}/")
                for img in sorted(subdir.glob("*.png")):
                    size_mb = img.stat().st_size / (1024 * 1024)
                    print(f"      🖼️  {img.name} ({size_mb:.2f} MB)")

    return results


async def main():
    """Run test."""
    print("=" * 70)
    print("Testing Reference Image Parameter")
    print("=" * 70)

    try:
        await test_reference_image()

        print("\n" + "=" * 70)
        print("✓ Test completed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
