"""Tests for Gemini Vision map detection."""
import pytest
import asyncio
from pdf_processing.image_asset_processing.detect_maps import detect_maps_async
from pdf_processing.image_asset_processing.models import MapDetectionResult


@pytest.mark.map
@pytest.mark.integration
@pytest.mark.slow
class TestDetectMapsAsync:
    def test_detect_maps_returns_results_for_all_pages(self, test_pdf_path, check_api_key):
        """Test that detection returns result for each page."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        # Test PDF has 7 pages
        assert len(results) == 7
        assert all(isinstance(r, MapDetectionResult) for r in results)

    def test_detection_result_structure(self, test_pdf_path, check_api_key):
        """Test that results have expected structure."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        for result in results:
            assert isinstance(result.has_map, bool)
            if result.has_map:
                assert result.type in ["navigation_map", "battle_map", None]
                # Name should be short if provided
                if result.name:
                    assert len(result.name.split()) <= 3

    def test_detection_identifies_at_least_one_map(self, test_pdf_path, check_api_key):
        """Test that detection finds at least one map in test PDF."""
        results = asyncio.run(detect_maps_async(test_pdf_path))

        maps_found = [r for r in results if r.has_map]
        # Test PDF should have some maps
        assert len(maps_found) > 0
