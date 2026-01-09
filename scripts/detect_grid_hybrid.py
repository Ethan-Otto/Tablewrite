#!/usr/bin/env python3
"""Hybrid FFT + vectorized grid detection."""

import numpy as np
from PIL import Image
from pathlib import Path
import time


def detect_grid_hybrid(image_path: Path, grid_range=(20, 150), top_k=10) -> dict:
    """
    Hybrid approach:
    1. FFT finds top K candidate grid sizes (O(n log n))
    2. Vectorized offset search for each candidate (O(K * 1))
    3. Return best scoring (grid_size, offset)
    """
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float64)

    # Compute edge images
    h_edges = np.abs(arr[2:, :, :] - arr[:-2, :, :]).mean(axis=2)
    v_edges = np.abs(arr[:, 2:, :] - arr[:, :-2, :]).mean(axis=2)
    H, W = h_edges.shape[0], v_edges.shape[1]

    # Average edge signal along each axis
    h_signal = h_edges.mean(axis=1)
    v_signal = v_edges.mean(axis=0)

    # FFT to find candidate periods
    h_fft = np.abs(np.fft.rfft(h_signal))
    v_fft = np.abs(np.fft.rfft(v_signal))
    h_freqs = np.fft.rfftfreq(len(h_signal))
    v_freqs = np.fft.rfftfreq(len(v_signal))

    # Build period -> magnitude maps
    def get_period_scores(fft_mag, freqs):
        scores = {}
        for mag, freq in zip(fft_mag[1:], freqs[1:]):
            if freq <= 0:
                continue
            period = int(round(1 / freq))
            if grid_range[0] <= period <= grid_range[1]:
                if period not in scores or mag > scores[period]:
                    scores[period] = mag
        return scores

    h_scores = get_period_scores(h_fft, h_freqs)
    v_scores = get_period_scores(v_fft, v_freqs)

    # Find common periods and score by geometric mean
    common = set(h_scores.keys()) & set(v_scores.keys())
    candidates = []
    for period in common:
        score = np.sqrt(h_scores[period] * v_scores[period])
        candidates.append((period, score))

    # Sort by FFT score and take top K
    candidates.sort(key=lambda x: -x[1])
    candidates = candidates[:top_k]

    if not candidates:
        return {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0}

    # Vectorized offset search for each candidate
    best = {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0}

    for gs, _ in candidates:
        # Trim to multiple of gs
        h_trim = (H // gs) * gs
        v_trim = (W // gs) * gs

        if h_trim == 0 or v_trim == 0:
            continue

        n_h_lines = H // gs
        n_v_lines = W // gs

        # Reshape for vectorized offset computation
        h_reshaped = h_edges[:h_trim, :].reshape(n_h_lines, gs, -1).transpose(1, 0, 2)
        v_reshaped = v_edges[:, :v_trim].reshape(-1, n_v_lines, gs).transpose(2, 1, 0)

        # Compute mean and var for each offset
        h_means = h_reshaped.mean(axis=(1, 2))
        h_vars = h_reshaped.var(axis=(1, 2))
        v_means = v_reshaped.mean(axis=(1, 2))
        v_vars = v_reshaped.var(axis=(1, 2))

        # Compute SNR for all (y_off, x_off) combinations
        combined_mean = (h_means[:, None] + v_means[None, :]) / 2
        combined_var = (h_vars[:, None] + v_vars[None, :]) / 2

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

    print(f"Testing hybrid FFT+vectorized on {len(map_files)} maps...\n")

    total_time = 0
    for map_file in map_files:
        start = time.time()
        result = detect_grid_hybrid(map_file)
        elapsed = time.time() - start
        total_time += elapsed

        gs = result['grid_size']
        print(f"{map_file.name:40} {gs if gs else 'N/A':>3}px  SNR={result['snr']:.2f}  [{elapsed:.2f}s]")

    print(f"\nTotal: {total_time:.1f}s")


if __name__ == '__main__':
    main()
