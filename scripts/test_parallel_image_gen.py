#!/usr/bin/env python3
"""Manual test script for parallel image generation utility."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from util.parallel_image_gen import generate_images_parallel, generate_variations


async def test_basic_generation():
    """Test basic parallel image generation."""
    print("\n=== Test 1: Basic Parallel Generation (3 images) ===")

    prompts = [
        "A dark mysterious cave entrance, fantasy art style",
        "A cozy medieval tavern interior with fireplace, fantasy art style",
        "A mystical forest clearing with glowing mushrooms, fantasy art style"
    ]

    print(f"Generating {len(prompts)} images with max_concurrent=3...")
    results = await generate_images_parallel(prompts, max_concurrent=3)

    successful = [r for r in results if r is not None]
    print(f"✓ Generated {len(successful)}/{len(prompts)} images successfully")

    for i, result in enumerate(results):
        if result:
            print(f"  Image {i}: {len(result)} bytes")
        else:
            print(f"  Image {i}: FAILED")

    return results


async def test_with_save():
    """Test image generation with auto-save."""
    print("\n=== Test 2: Generation with Auto-Save (2 images) ===")

    prompts = [
        "A goblin hideout entrance, fantasy art style",
        "A dragon's lair cave, fantasy art style"
    ]

    output_dir = Path("output/test_parallel_gen")
    print(f"Generating {len(prompts)} images and saving to {output_dir}...")

    results = await generate_images_parallel(
        prompts,
        max_concurrent=2,
        save_dir=output_dir
    )

    successful = [r for r in results if r is not None]
    print(f"✓ Generated {len(successful)}/{len(prompts)} images successfully")

    # Check saved files
    for i in range(len(prompts)):
        filepath = output_dir / f"image_{i:03d}.png"
        if filepath.exists():
            print(f"  ✓ Saved: {filepath} ({filepath.stat().st_size} bytes)")
        else:
            print(f"  ✗ Missing: {filepath}")

    return results


async def test_variations():
    """Test generating variations of same prompt."""
    print("\n=== Test 3: Variations (4 versions of same prompt) ===")

    prompt = "A mysterious dungeon entrance with torches, fantasy art style"
    count = 4

    print(f"Generating {count} variations of: '{prompt}'...")
    results = await generate_variations(prompt, count=count, max_concurrent=4)

    successful = [r for r in results if r is not None]
    print(f"✓ Generated {len(successful)}/{count} variations successfully")

    return results


async def test_high_concurrency():
    """Test with many images to verify concurrency control."""
    print("\n=== Test 4: High Concurrency (10 images, max_concurrent=5) ===")

    prompts = [f"A fantasy dungeon room {i}, art style" for i in range(10)]

    print(f"Generating {len(prompts)} images with max_concurrent=5...")
    import time
    start = time.time()

    results = await generate_images_parallel(prompts, max_concurrent=5)

    elapsed = time.time() - start
    successful = [r for r in results if r is not None]

    print(f"✓ Generated {len(successful)}/{len(prompts)} images in {elapsed:.2f}s")
    print(f"  Average: {elapsed/len(successful):.2f}s per image")

    return results


async def main():
    """Run all manual tests."""
    print("=" * 70)
    print("Manual Test Suite for Parallel Image Generation")
    print("=" * 70)

    try:
        # Test 1: Basic generation
        await test_basic_generation()

        # Test 2: With save
        await test_with_save()

        # Test 3: Variations
        await test_variations()

        # Test 4: High concurrency (optional - costs money)
        # Uncomment to test:
        # await test_high_concurrency()

        print("\n" + "=" * 70)
        print("✓ All manual tests completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
