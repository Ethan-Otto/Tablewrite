#!/usr/bin/env python3
"""Test redline_walls function."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wall_detection.redline_walls import redline_walls


async def test_redline():
    """Test redlining a battle map."""
    print("=" * 70)
    print("Testing redline_walls Function")
    print("=" * 70)

    # Create a simple test battle map
    print("\nCreating test battle map...")
    from PIL import Image, ImageDraw

    # Create a simple map with walls
    img = Image.new('RGB', (1024, 1024), color='white')
    draw = ImageDraw.Draw(img)

    # Draw some "walls" in gray
    draw.rectangle([100, 100, 900, 150], fill='gray')  # Top wall
    draw.rectangle([100, 850, 900, 900], fill='gray')  # Bottom wall
    draw.rectangle([100, 100, 150, 900], fill='gray')  # Left wall
    draw.rectangle([850, 100, 900, 900], fill='gray')  # Right wall
    draw.rectangle([400, 400, 600, 450], fill='gray')  # Interior wall

    test_map_path = Path("output/test_battle_map.png")
    test_map_path.parent.mkdir(exist_ok=True)
    img.save(test_map_path)
    print(f"✓ Created test map: {test_map_path}")

    # Test redlining
    print("\nGenerating redlined version...")
    results = await redline_walls(
        test_map_path,
        save_dir=Path("output/redlined_walls"),
        make_run=True,
        temperature=0.5
    )

    successful = sum(1 for r in results if r is not None)
    print(f"\n✓ Generated {successful}/{len(results)} redlined images")

    # Show output
    print("\nOutput directory:")
    output_dir = Path("output/redlined_walls")
    if output_dir.exists():
        for subdir in sorted(output_dir.iterdir()):
            if subdir.is_dir():
                print(f"  📁 {subdir.name}/")
                for img in sorted(subdir.glob("*.png")):
                    size_mb = img.stat().st_size / (1024 * 1024)
                    print(f"      🖼️  {img.name} ({size_mb:.2f} MB)")

    print("\n" + "=" * 70)
    print("✓ Test completed!")
    print(f"View results in: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_redline())
