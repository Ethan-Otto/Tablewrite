#!/usr/bin/env python3
"""Test grid detection on all battle maps in the verification folder."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PIL import Image, ImageDraw
from scenes.detect_grid import detect_grid
import time

MAPS_DIR = Path(__file__).parent.parent / "data" / "verification" / "battlemaps"
OUTPUT_DIR = MAPS_DIR / "overlays"


def create_overlay(image_path: Path, grid_size: int, x_offset: int, y_offset: int) -> Path:
    """Create an overlay image showing detected grid lines."""
    img = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(img, 'RGBA')

    w, h = img.size

    # Draw vertical lines (red, semi-transparent)
    for x in range(x_offset, w, grid_size):
        draw.line([(x, 0), (x, h)], fill=(255, 0, 0, 180), width=2)

    # Draw horizontal lines (red, semi-transparent)
    for y in range(y_offset, h, grid_size):
        draw.line([(0, y), (w, y)], fill=(255, 0, 0, 180), width=2)

    output_path = OUTPUT_DIR / f"{image_path.stem}_overlay.png"
    img.save(output_path)
    return output_path


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Get all map files
    map_files = sorted([
        f for f in MAPS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])

    print(f"Testing grid detection on {len(map_files)} maps...\n")

    results = []

    for map_file in map_files:
        print(f"Processing {map_file.name}...")
        start = time.time()

        result = detect_grid(map_file)
        elapsed = time.time() - start

        gs = result['grid_size']
        x_off = result['x_offset']
        y_off = result['y_offset']
        snr = result['snr']

        # Create overlay
        overlay_path = create_overlay(map_file, gs, x_off, y_off)

        print(f"  Grid: {gs}px @ ({x_off}, {y_off}) SNR={snr:.3f} [{elapsed:.1f}s]")
        print(f"  Overlay: {overlay_path.name}")

        results.append({
            'name': map_file.name,
            'grid_size': gs,
            'x_offset': x_off,
            'y_offset': y_off,
            'snr': snr,
            'time': elapsed,
            'overlay': overlay_path
        })

    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    for r in results:
        print(f"{r['name']:40} {r['grid_size']:3}px  SNR={r['snr']:.3f}  [{r['time']:.1f}s]")

    # Open all overlays for review
    print(f"\nOpening {len(results)} overlays in Preview...")
    import subprocess
    overlay_paths = [str(r['overlay']) for r in results]
    subprocess.run(['open', '-a', 'Preview'] + overlay_paths)


if __name__ == '__main__':
    main()
