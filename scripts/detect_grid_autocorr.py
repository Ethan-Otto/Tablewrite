#!/usr/bin/env python3
"""Autocorrelation-based grid detection."""

import numpy as np
from PIL import Image
from pathlib import Path
import time


def detect_grid_autocorr(image_path: Path, grid_range=(20, 150)) -> dict:
    """
    Detect grid using autocorrelation of edge signals.

    Autocorrelation naturally finds the fundamental period,
    with harmonics appearing at multiples.
    """
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float64)

    # Compute edge images
    h_edges = np.abs(arr[2:, :, :] - arr[:-2, :, :]).mean(axis=2)
    v_edges = np.abs(arr[:, 2:, :] - arr[:, :-2, :]).mean(axis=2)
    H, W = h_edges.shape[0], v_edges.shape[1]

    # Average edge signals
    h_signal = h_edges.mean(axis=1)
    v_signal = v_edges.mean(axis=0)

    # Remove DC component
    h_signal = h_signal - h_signal.mean()
    v_signal = v_signal - v_signal.mean()

    # Autocorrelation (using FFT for speed)
    def autocorr_fft(signal):
        n = len(signal)
        # Pad to avoid circular correlation
        padded = np.zeros(2 * n)
        padded[:n] = signal
        # FFT method: autocorr = ifft(|fft|^2)
        f = np.fft.fft(padded)
        acf = np.fft.ifft(f * np.conj(f)).real[:n]
        return acf / acf[0]  # Normalize

    h_acf = autocorr_fft(h_signal)
    v_acf = autocorr_fft(v_signal)

    # Combined autocorrelation (geometric mean)
    min_len = min(len(h_acf), len(v_acf))
    combined_acf = np.sqrt(np.abs(h_acf[:min_len]) * np.abs(v_acf[:min_len]))

    # Find peaks in the valid range
    peaks = []
    for lag in range(grid_range[0], min(grid_range[1], min_len - 1)):
        if combined_acf[lag] > combined_acf[lag-1] and combined_acf[lag] > combined_acf[lag+1]:
            peaks.append((lag, combined_acf[lag]))

    if not peaks:
        return {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0}

    # Sort by autocorrelation strength
    peaks.sort(key=lambda x: -x[1])
    peak_dict = {p[0]: p[1] for p in peaks}

    # Filter harmonics: if lag L and ~L/2 both exist as peaks,
    # prefer L/2 (the fundamental) if it's reasonably strong
    filtered_peaks = []
    for lag, strength in peaks:
        half = lag // 2
        # Check if half-lag (with tolerance ±2) exists and is strong enough
        is_harmonic = False
        for tol in range(-2, 3):
            check_lag = half + tol
            if check_lag in peak_dict and peak_dict[check_lag] > strength * 0.7:
                is_harmonic = True
                break
        if is_harmonic:
            continue  # Skip this harmonic
        filtered_peaks.append((lag, strength))

    if filtered_peaks:
        peaks = filtered_peaks

    # Take the strongest (filtered) peak as grid size
    grid_size = peaks[0][0]
    acf_score = peaks[0][1]

    # Find best offset using vectorized approach
    h_trim = (H // grid_size) * grid_size
    v_trim = (W // grid_size) * grid_size

    if h_trim == 0 or v_trim == 0:
        return {'grid_size': grid_size, 'x_offset': 0, 'y_offset': 0, 'snr': acf_score}

    n_h_lines = H // grid_size
    n_v_lines = W // grid_size
    gs = grid_size

    # Vectorized offset search
    h_reshaped = h_edges[:h_trim, :].reshape(n_h_lines, gs, -1).transpose(1, 0, 2)
    v_reshaped = v_edges[:, :v_trim].reshape(-1, n_v_lines, gs).transpose(2, 1, 0)

    # Mean edge strength at each offset
    h_means = h_reshaped.mean(axis=(1, 2))
    v_means = v_reshaped.mean(axis=(1, 2))

    # Combined score (we want high edge strength at grid lines)
    score = h_means[:, None] + v_means[None, :]

    max_idx = np.argmax(score)
    y_off, x_off = divmod(max_idx, gs)

    return {
        'grid_size': grid_size,
        'x_offset': int(x_off),
        'y_offset': int(y_off),
        'snr': float(acf_score)
    }


def main():
    maps_dir = Path(__file__).parent.parent / "data" / "verification" / "battlemaps"

    map_files = sorted([
        f for f in maps_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])

    print(f"Testing autocorrelation on {len(map_files)} maps...\n")

    total_time = 0
    for map_file in map_files:
        start = time.time()
        result = detect_grid_autocorr(map_file)
        elapsed = time.time() - start
        total_time += elapsed

        gs = result['grid_size']
        print(f"{map_file.name:40} {gs if gs else 'N/A':>3}px  ACF={result['snr']:.3f}  [{elapsed:.2f}s]")

    print(f"\nTotal: {total_time:.1f}s")


if __name__ == '__main__':
    main()
