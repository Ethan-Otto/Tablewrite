#!/usr/bin/env python3
"""Test the make_run parameter for timestamped folders."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from util.parallel_image_gen import generate_images_parallel


async def test_make_run():
    """Test make_run parameter creates timestamped folder."""
    print("\n=== Testing make_run Parameter ===\n")

    prompts = [
        "A dark cave entrance, fantasy art",
        "A medieval tavern, fantasy art"
    ]

    output_dir = Path("output/test_make_run")

    print(f"Generating {len(prompts)} images with make_run=True...")
    print(f"Base directory: {output_dir}\n")

    results = await generate_images_parallel(
        prompts,
        save_dir=output_dir,
        make_run=True,  # Create timestamped subfolder
        max_concurrent=2
    )

    print(f"\n✓ Generated {len([r for r in results if r])} images")

    # Check directory structure
    print(f"\nDirectory structure:")
    if output_dir.exists():
        for subdir in sorted(output_dir.iterdir()):
            if subdir.is_dir():
                print(f"  📁 {subdir.name}/")
                for img in sorted(subdir.glob("*.png")):
                    size_mb = img.stat().st_size / (1024 * 1024)
                    print(f"      🖼️  {img.name} ({size_mb:.2f} MB)")
    else:
        print(f"  ✗ Directory {output_dir} not found!")

    return results


async def test_without_make_run():
    """Test without make_run (saves directly to base dir)."""
    print("\n\n=== Testing WITHOUT make_run (Direct Save) ===\n")

    prompts = ["A simple forest, fantasy art"]
    output_dir = Path("output/test_direct_save")

    print(f"Generating 1 image with make_run=False...")
    print(f"Base directory: {output_dir}\n")

    results = await generate_images_parallel(
        prompts,
        save_dir=output_dir,
        make_run=False,  # Save directly to base directory
        max_concurrent=1
    )

    print(f"\n✓ Generated {len([r for r in results if r])} images")

    # Check directory structure
    print(f"\nDirectory structure:")
    if output_dir.exists():
        for img in sorted(output_dir.glob("*.png")):
            size_mb = img.stat().st_size / (1024 * 1024)
            print(f"  🖼️  {img.name} ({size_mb:.2f} MB)")
    else:
        print(f"  ✗ Directory {output_dir} not found!")

    return results


async def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing make_run Parameter")
    print("=" * 70)

    try:
        # Test 1: With make_run=True (timestamped folder)
        await test_make_run()

        # Test 2: Without make_run (direct save)
        await test_without_make_run()

        print("\n" + "=" * 70)
        print("✓ All tests completed!")
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
