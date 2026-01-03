"""Grid detection for battle maps using hybrid autocorrelation + brute-force.

Uses a two-stage approach:
1. Fast autocorrelation to find dominant periodic patterns (~0.1s)
2. Falls back to vectorized brute-force for weak signals

Autocorrelation naturally finds the fundamental frequency, with harmonic
filtering to avoid picking 2x the actual grid size.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def _autocorr_fft(signal: np.ndarray) -> np.ndarray:
    """Compute autocorrelation using FFT for speed."""
    n = len(signal)
    # Pad to avoid circular correlation
    padded = np.zeros(2 * n)
    padded[:n] = signal
    # FFT method: autocorr = ifft(|fft|^2)
    f = np.fft.fft(padded)
    acf = np.fft.ifft(f * np.conj(f)).real[:n]
    return acf / acf[0]  # Normalize


def _find_best_offset_vectorized(
    h_edges: np.ndarray,
    v_edges: np.ndarray,
    grid_size: int,
) -> Tuple[int, int, float]:
    """Find best offset for a given grid size using vectorized computation."""
    H, W = h_edges.shape[0], v_edges.shape[1]
    gs = grid_size

    # Trim to multiple of gs
    h_trim = (H // gs) * gs
    v_trim = (W // gs) * gs

    if h_trim == 0 or v_trim == 0:
        return 0, 0, 0.0

    n_h_lines = H // gs
    n_v_lines = W // gs

    # Reshape for vectorized offset computation
    # h_reshaped[y_off, line_idx, x] - samples at grid lines for offset y_off
    h_reshaped = h_edges[:h_trim, :].reshape(n_h_lines, gs, -1).transpose(1, 0, 2)
    v_reshaped = v_edges[:, :v_trim].reshape(-1, n_v_lines, gs).transpose(2, 1, 0)

    # Mean edge strength at each offset
    h_means = h_reshaped.mean(axis=(1, 2))
    v_means = v_reshaped.mean(axis=(1, 2))

    # Combined score (we want high edge strength at grid lines)
    score = h_means[:, None] + v_means[None, :]

    max_idx = np.argmax(score)
    y_off, x_off = divmod(max_idx, gs)

    return int(x_off), int(y_off), float(score[y_off, x_off])


def _detect_grid_autocorr(
    h_edges: np.ndarray,
    v_edges: np.ndarray,
    grid_range: Tuple[int, int],
) -> dict:
    """Detect grid using autocorrelation of edge signals."""
    H, W = h_edges.shape[0], v_edges.shape[1]

    # Average edge signals
    h_signal = h_edges.mean(axis=1)
    v_signal = v_edges.mean(axis=0)

    # Remove DC component
    h_signal = h_signal - h_signal.mean()
    v_signal = v_signal - v_signal.mean()

    # Compute autocorrelation
    h_acf = _autocorr_fft(h_signal)
    v_acf = _autocorr_fft(v_signal)

    # Combined autocorrelation (geometric mean)
    min_len = min(len(h_acf), len(v_acf))
    combined_acf = np.sqrt(np.abs(h_acf[:min_len]) * np.abs(v_acf[:min_len]))

    # Find peaks in the valid range
    peaks = []
    for lag in range(grid_range[0], min(grid_range[1], min_len - 1)):
        if combined_acf[lag] > combined_acf[lag - 1] and combined_acf[lag] > combined_acf[lag + 1]:
            peaks.append((lag, combined_acf[lag]))

    if not peaks:
        return {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0.0}

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
        if not is_harmonic:
            filtered_peaks.append((lag, strength))

    if filtered_peaks:
        peaks = filtered_peaks

    # Take the strongest (filtered) peak as grid size
    grid_size = peaks[0][0]
    acf_score = peaks[0][1]

    # Find best offset
    x_off, y_off, _ = _find_best_offset_vectorized(h_edges, v_edges, grid_size)

    return {
        'grid_size': grid_size,
        'x_offset': x_off,
        'y_offset': y_off,
        'snr': float(acf_score),
    }


def _detect_grid_bruteforce(
    h_edges: np.ndarray,
    v_edges: np.ndarray,
    grid_range: Tuple[int, int],
) -> dict:
    """Vectorized brute-force grid detection for all grid sizes."""
    H, W = h_edges.shape[0], v_edges.shape[1]
    best = {'grid_size': None, 'x_offset': 0, 'y_offset': 0, 'snr': 0.0}

    for gs in range(grid_range[0], grid_range[1] + 1):
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
                'snr': float(max_score),
            }

    return best


def detect_grid(
    image_path: Path,
    grid_range: Tuple[int, int] = (20, 100),
    acf_threshold: float = 0.3,
) -> dict:
    """
    Detect grid size and offset using hybrid autocorrelation + brute-force.

    The algorithm:
    1. Computes autocorrelation of edge signals to find periodic patterns
    2. Filters harmonics to find fundamental frequency (not 2x)
    3. Falls back to vectorized brute-force if autocorrelation signal is weak

    Args:
        image_path: Path to battle map image
        grid_range: (min, max) grid sizes to test in pixels
        acf_threshold: Minimum autocorrelation score to trust (default 0.3)

    Returns:
        dict with keys:
            - grid_size: Detected grid size in pixels (or None if failed)
            - x_offset: X offset where grid lines start
            - y_offset: Y offset where grid lines start
            - snr: Score (ACF value or SNR depending on method used)
    """
    image_path = Path(image_path)
    logger.info(f"Detecting grid in {image_path.name}, range={grid_range}")

    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float64)

    # Precompute edge images once
    h_edges = np.abs(arr[2:, :, :] - arr[:-2, :, :]).mean(axis=2)
    v_edges = np.abs(arr[:, 2:, :] - arr[:, :-2, :]).mean(axis=2)

    # Try autocorrelation first (fast, ~0.1s)
    result = _detect_grid_autocorr(h_edges, v_edges, grid_range)
    method = 'ACF'

    # Fall back to brute-force if autocorrelation signal is weak
    if result['snr'] < acf_threshold or result['grid_size'] is None:
        logger.debug(f"ACF score {result['snr']:.3f} < {acf_threshold}, using brute-force")
        result = _detect_grid_bruteforce(h_edges, v_edges, grid_range)
        method = 'BF'

    logger.info(
        f"Detected grid: {result['grid_size']}px @ "
        f"({result['x_offset']}, {result['y_offset']}), "
        f"score={result['snr']:.3f} [{method}]"
    )

    return result


def detect_grid_size_only(
    image_path: Path,
    grid_range: Tuple[int, int] = (20, 100),
) -> Optional[int]:
    """
    Detect just the grid size (ignoring offset).

    Convenience wrapper that returns only the grid size in pixels,
    or None if detection fails.
    """
    result = detect_grid(image_path, grid_range)
    return result.get('grid_size')
