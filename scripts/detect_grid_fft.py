#!/usr/bin/env python3
"""FFT-based grid detection - finds dominant periodic patterns."""

import numpy as np
from PIL import Image
from pathlib import Path
import time


def detect_grid_fft(image_path: Path, grid_range=(20, 150)) -> dict:
    """
    Detect grid size using FFT to find dominant frequencies.

    Much faster than brute force - O(n log n) vs O(n * gs^2).
    """
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float64)

    # Compute edge images
    h_edges = np.abs(arr[2:, :, :] - arr[:-2, :, :]).mean(axis=2)
    v_edges = np.abs(arr[:, 2:, :] - arr[:, :-2, :]).mean(axis=2)

    # Average edge signal along each axis
    h_signal = h_edges.mean(axis=1)
    v_signal = v_edges.mean(axis=0)

    # FFT
    h_fft = np.abs(np.fft.rfft(h_signal))
    v_fft = np.abs(np.fft.rfft(v_signal))

    # Convert to periods
    h_freqs = np.fft.rfftfreq(len(h_signal))
    v_freqs = np.fft.rfftfreq(len(v_signal))

    # Build period -> magnitude maps for both directions
    def get_period_scores(fft_mag, freqs, min_period, max_period):
        scores = {}
        for mag, freq in zip(fft_mag[1:], freqs[1:]):
            if freq <= 0:
                continue
            period = 1 / freq
            if min_period <= period <= max_period:
                # Round to nearest integer
                period_int = int(round(period))
                if period_int not in scores or mag > scores[period_int]:
                    scores[period_int] = mag
        return scores

    h_scores = get_period_scores(h_fft, h_freqs, grid_range[0], grid_range[1])
    v_scores = get_period_scores(v_fft, v_freqs, grid_range[0], grid_range[1])

    # Find best COMMON period (strong in both H and V)
    common_periods = set(h_scores.keys()) & set(v_scores.keys())
    period_scores = {}
    for period in common_periods:
        # Geometric mean rewards periods strong in both
        combined = np.sqrt(h_scores[period] * v_scores[period])
        period_scores[period] = combined

    # Filter sub-harmonics: if period P and 2P both exist, prefer 2P
    # (the fundamental frequency, not the harmonic)
    filtered_scores = {}
    for period, score in period_scores.items():
        double = period * 2
        # Check if double exists and is reasonably strong (>50% of this score)
        if double in period_scores and period_scores[double] > score * 0.5:
            continue  # Skip this sub-harmonic
        filtered_scores[period] = score

    # Find best from filtered
    best_combined = 0
    grid_size = None
    for period, score in filtered_scores.items():
        if score > best_combined:
            best_combined = score
            grid_size = period

    # Fallback to strongest single direction if no common periods
    if grid_size is None:
        all_scores = [(p, m, 'h') for p, m in h_scores.items()]
        all_scores += [(p, m, 'v') for p, m in v_scores.items()]
        if all_scores:
            best = max(all_scores, key=lambda x: x[1])
            grid_size = best[0]

    # Find best offset using edge correlation
    if grid_size:
        H, W = h_edges.shape[0], v_edges.shape[1]
        best_score = 0
        best_offset = (0, 0)

        for y_off in range(grid_size):
            h_rows = np.arange(y_off, H, grid_size)
            if len(h_rows) == 0:
                continue
            h_score = h_edges[h_rows, :].mean()

            for x_off in range(grid_size):
                v_cols = np.arange(x_off, W, grid_size)
                if len(v_cols) == 0:
                    continue
                v_score = v_edges[:, v_cols].mean()

                score = h_score + v_score
                if score > best_score:
                    best_score = score
                    best_offset = (x_off, y_off)

        x_offset, y_offset = best_offset
    else:
        x_offset, y_offset = 0, 0
        best_score = 0

    return {
        'grid_size': grid_size,
        'x_offset': x_offset,
        'y_offset': y_offset,
        'snr': best_score
    }


def main():
    maps_dir = Path(__file__).parent.parent / "data" / "verification" / "battlemaps"

    map_files = sorted([
        f for f in maps_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])

    print(f"Testing FFT detection on {len(map_files)} maps...\n")

    total_time = 0
    for map_file in map_files:
        start = time.time()
        result = detect_grid_fft(map_file)
        elapsed = time.time() - start
        total_time += elapsed

        gs = result['grid_size']
        print(f"{map_file.name:40} {gs if gs else 'N/A':>3}px  [{elapsed:.2f}s]")

    print(f"\nTotal: {total_time:.1f}s")


if __name__ == '__main__':
    main()
