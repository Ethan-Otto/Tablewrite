"""Integration tests for grid detection with real Gemini API."""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from config import PROJECT_ROOT

# Test fixture paths
TEST_MAP_PATH = PROJECT_ROOT / "data" / "image_examples" / "castle.png"
WEBP_MAP_PATH = PROJECT_ROOT / "data" / "verification" / "battlemaps" / "Cragmaw.webp"

# Load environment variables at module level
load_dotenv(PROJECT_ROOT / ".env")


@pytest.fixture(scope="module")
def gemini_api_key():
    """Ensure Gemini API key is available for integration tests."""
    api_key = os.getenv("GeminiImageAPI")
    assert api_key, (
        "Gemini API key not found. Set GeminiImageAPI in .env file. "
        "Integration tests require real API access."
    )
    return api_key


@pytest.mark.gemini
@pytest.mark.asyncio
async def test_detect_gridlines_real_api(gemini_api_key):
    """Test grid detection with real Gemini API call.

    This test makes a real API call to Gemini to verify:
    1. The API integration works correctly
    2. The response can be parsed into GridDetectionResult
    3. Result fields have valid values (has_grid is bool, confidence 0-1, etc.)

    Note: This test verifies the API works, not specific detection results
    (AI responses may vary).
    """
    from scenes.detect_gridlines import detect_gridlines
    from scenes.models import GridDetectionResult

    # Ensure test fixture exists - FAIL (not skip) if missing per CLAUDE.md
    assert TEST_MAP_PATH.exists(), (
        f"Test fixture not found: {TEST_MAP_PATH}. "
        "Expected castle.png in data/image_examples/"
    )

    # Make real API call
    result = await detect_gridlines(TEST_MAP_PATH)

    # Verify result is correct type
    assert isinstance(result, GridDetectionResult), (
        f"Expected GridDetectionResult, got {type(result).__name__}"
    )

    # Verify has_grid is a boolean
    assert isinstance(result.has_grid, bool), (
        f"has_grid should be bool, got {type(result.has_grid).__name__}"
    )

    # Verify confidence is in valid range [0.0, 1.0]
    assert 0.0 <= result.confidence <= 1.0, (
        f"confidence should be between 0.0 and 1.0, got {result.confidence}"
    )

    # If grid detected, grid_size must be a positive integer
    if result.has_grid:
        assert result.grid_size is not None, (
            "grid_size should not be None when has_grid=True"
        )
        assert isinstance(result.grid_size, int), (
            f"grid_size should be int, got {type(result.grid_size).__name__}"
        )
        assert result.grid_size > 0, (
            f"grid_size should be positive, got {result.grid_size}"
        )

    # If no grid detected, grid_size should be None
    if not result.has_grid:
        assert result.grid_size is None, (
            f"grid_size should be None when has_grid=False, got {result.grid_size}"
        )


@pytest.mark.gemini
@pytest.mark.asyncio
async def test_detect_gridlines_real_api_with_webp(gemini_api_key):
    """Test grid detection with a WEBP image format.

    Verifies the API handles different image formats correctly.
    """
    from scenes.detect_gridlines import detect_gridlines
    from scenes.models import GridDetectionResult

    # Ensure test fixture exists - FAIL (not skip) if missing per CLAUDE.md
    assert WEBP_MAP_PATH.exists(), (
        f"WEBP test fixture not found: {WEBP_MAP_PATH}. "
        "Expected Cragmaw.webp in data/verification/battlemaps/"
    )

    # Make real API call
    result = await detect_gridlines(WEBP_MAP_PATH)

    # Verify result structure
    assert isinstance(result, GridDetectionResult)
    assert isinstance(result.has_grid, bool)
    assert 0.0 <= result.confidence <= 1.0

    if result.has_grid:
        assert result.grid_size is not None
        assert result.grid_size > 0
