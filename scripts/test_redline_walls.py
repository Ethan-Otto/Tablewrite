#!/usr/bin/env python3
"""Test complete wall detection pipeline."""

import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wall_detection.redline_walls import redline_walls

logging.basicConfig(level=logging.INFO, format='%(message)s')


async def test_pipeline():
    """Test complete wall detection pipeline with Cragmaw.webp."""
    print("=" * 80)
    print("Wall Detection Pipeline Test")
    print("=" * 80)

    # Use the Cragmaw map
    test_map = Path("data/image_examples/Cragmaw.webp")

    if not test_map.exists():
        print(f"❌ Test map not found: {test_map}")
        print("Please ensure Cragmaw.webp is in data/image_examples/")
        return

    print(f"\nInput: {test_map}")
    print(f"Size: {test_map.stat().st_size / 1024:.1f} KB")

    # Run complete pipeline
    print("\n" + "=" * 80)
    print("Running complete pipeline...")
    print("=" * 80)

    result = await redline_walls(
        input_image=test_map,
        save_dir=Path("output/wall_detection_test"),
        make_run=True,
        temperature=0.5,
        alpha=0.8
    )

    # Display results
    print("\n" + "=" * 80)
    print("✓ Pipeline completed successfully!")
    print("=" * 80)

    print("\nOutput files:")
    for key, path in result.items():
        if path.exists():
            if path.is_file():
                size_kb = path.stat().st_size / 1024
                print(f"  ✓ {key:20} → {path.name} ({size_kb:.1f} KB)")
            else:
                # Directory
                num_files = len(list(path.glob("*")))
                print(f"  ✓ {key:20} → {path.name}/ ({num_files} files)")
        else:
            print(f"  ✗ {key:20} → NOT FOUND")

    print("\n" + "=" * 80)
    print(f"View final overlay: {result['overlay']}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pipeline())
