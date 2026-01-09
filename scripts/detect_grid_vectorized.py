#!/usr/bin/env python3
"""Fully vectorized grid detection - test version."""

import numpy as np
from PIL import Image
from pathlib import Path
import time


def detect_grid_vectorized(image_path: Path, grid_range=(20, 100)) -> dict:
    """Fully vectorized grid detection."""
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float64)

    # Precompute edge images
    h_edges = np.abs(arr[2:, :, :] - arr[:-2, :, :]).mean(axis=2)
    v_edges = np.abs(arr[:, 2:, :] - arr[:, :-2, :]).mean(axis=2)
    H, W = h_edges.shape[0], v_edges.shape[1]

    best = {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0}

    for gs in range(grid_range[0], grid_range[1] + 1):
        # Trim to multiple of gs
        h_trim = (H // gs) * gs
        v_trim = (W // gs) * gs

        if h_trim == 0 or v_trim == 0:
            continue

        n_h_lines = H // gs
        n_v_lines = W // gs

        # Reshape to [gs, n_lines, width] - each row is a different y_offset
        h_reshaped = h_edges[:h_trim, :].reshape(n_h_lines, gs, -1).transpose(1, 0, 2)
        # h_reshaped[y_off, line_idx, x] - samples at grid lines for offset y_off

        # Compute mean and var for each y_offset (across lines and x positions)
        # Shape: [gs]
        h_means = h_reshaped.mean(axis=(1, 2))
        h_vars = h_reshaped.var(axis=(1, 2))

        # Same for vertical: reshape to [n_lines, gs, height] then transpose
        v_reshaped = v_edges[:, :v_trim].reshape(-1, n_v_lines, gs).transpose(2, 1, 0)
        # v_reshaped[x_off, line_idx, y]

        v_means = v_reshaped.mean(axis=(1, 2))
        v_vars = v_reshaped.var(axis=(1, 2))

        # Compute SNR for all (y_off, x_off) combinations
        # Broadcasting: h_means[gs, 1] + v_means[1, gs] -> [gs, gs]
        combined_mean = (h_means[:, None] + v_means[None, :]) / 2
        combined_var = (h_vars[:, None] + v_vars[None, :]) / 2

        # Avoid division by zero
        valid = combined_var > 0
        snr = np.zeros((gs, gs))
        snr[valid] = combined_mean[valid] / np.sqrt(combined_var[valid])

        # Weight by log(lines)
        n_lines = n_h_lines + n_v_lines
        score = snr * np.log(n_lines + 1)

        # Find best offset for this grid size
        max_idx = np.argmax(score)
        y_off, x_off = divmod(max_idx, gs)
        max_score = score[y_off, x_off]

        if max_score > best['snr']:
            best = {
                'grid_size': gs,
                'x_offset': int(x_off),
                'y_offset': int(y_off),
                'snr': float(max_score)
            }

    return best


def main():
    maps_dir = Path(__file__).parent.parent / "data" / "verification" / "battlemaps"

    map_files = sorted([
        f for f in maps_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])

    print(f"Testing vectorized detection on {len(map_files)} maps...\n")

    total_time = 0
    for map_file in map_files:
        start = time.time()
        result = detect_grid_vectorized(map_file)
        elapsed = time.time() - start
        total_time += elapsed

        print(f"{map_file.name:40} {result['grid_size']:3}px  SNR={result['snr']:.3f}  [{elapsed:.2f}s]")

    print(f"\nTotal: {total_time:.1f}s")


if __name__ == '__main__':
    main()
