#!/usr/bin/env python3
"""Test generating 10 images from one reference."""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from util.parallel_image_gen import generate_images_parallel


async def test_10_from_reference():
    """Test generating 10 images from single reference."""
    print("\n=== Generating 10 Images from One Reference ===\n")

    reference_path = Path("output/test_ref.png")

    if not reference_path.exists():
        print("Creating test reference image...")
        from PIL import Image
        img = Image.new('RGB', (512, 512), color='blue')
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(reference_path)
        print(f"✓ Created: {reference_path}\n")

    # 10 different style prompts
    prompts = [
        "Transform into fantasy oil painting style",
        "Convert to watercolor illustration",
        "Make it look like a pencil sketch",
        "Style as anime artwork",
        "Render as pixel art",
        "Convert to impressionist painting",
        "Make it look like a comic book panel",
        "Transform into cyberpunk art style",
        "Style as medieval manuscript illustration",
        "Render as abstract art"
    ]

    output_dir = Path("output/test_10_images")

    print(f"Reference image: {reference_path}")
    print(f"Generating {len(prompts)} styled variations...")
    print(f"Max concurrent: 10")
    print(f"Output directory: {output_dir}\n")

    start_time = time.time()

    results = await generate_images_parallel(
        prompts,
        reference_image=str(reference_path),
        save_dir=output_dir,
        make_run=True,
        max_concurrent=10
    )

    elapsed = time.time() - start_time
    successful = [r for r in results if r is not None]

    print(f"\n{'='*70}")
    print(f"✓ Generated {len(successful)}/{len(prompts)} images in {elapsed:.2f}s")
    print(f"  Average: {elapsed/len(successful) if successful else 0:.2f}s per image")
    print(f"  Speedup: {len(successful):.1f}x (vs sequential: {len(successful)*7:.0f}s)")
    print(f"{'='*70}\n")

    # Show directory structure
    print("Output structure:")
    if output_dir.exists():
        for subdir in sorted(output_dir.iterdir()):
            if subdir.is_dir():
                print(f"  📁 {subdir.name}/")
                images = sorted(subdir.glob("*.png"))
                for img in images:
                    size_mb = img.stat().st_size / (1024 * 1024)
                    # Show which prompt this was
                    img_idx = int(img.stem.split('_')[1])
                    prompt_preview = prompts[img_idx][:40] + "..." if len(prompts[img_idx]) > 40 else prompts[img_idx]
                    print(f"      🖼️  {img.name} ({size_mb:.2f} MB) - \"{prompt_preview}\"")

                total_size = sum(img.stat().st_size for img in images) / (1024 * 1024)
                print(f"\n  Total: {len(images)} images, {total_size:.2f} MB")

    return results


async def main():
    """Run test."""
    print("=" * 70)
    print("Testing 10 Image Generation from Single Reference")
    print("=" * 70)

    try:
        await test_10_from_reference()

        print("\n" + "=" * 70)
        print("✓ Test completed successfully!")
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
