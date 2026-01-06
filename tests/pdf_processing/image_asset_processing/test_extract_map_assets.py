"""Tests for map extraction orchestration (extract_map_assets.py)."""
import pytest
import asyncio
import os
import json
import time
from pdf_processing.image_asset_processing.extract_map_assets import (
    extract_maps_from_pdf,
    save_metadata,
    extract_single_page
)
from pdf_processing.image_asset_processing.models import MapMetadata, MapDetectionResult


@pytest.mark.map
@pytest.mark.integration
@pytest.mark.slow
class TestExtractMapsFromPDF:
    """Tests that share a single extraction run via session-scoped fixture.

    The shared_extracted_maps fixture runs extraction once at the start of the
    test session, then all tests in this class reuse those results. This reduces
    test time from ~15 minutes (6 extractions) to ~2-3 minutes (1 extraction).
    """

    def test_extraction_returns_list_of_metadata(self, shared_extracted_maps):
        """Test that extraction returns list of MapMetadata objects."""
        maps, output_dir = shared_extracted_maps

        assert isinstance(maps, list)
        assert all(isinstance(m, MapMetadata) for m in maps)

    def test_extraction_finds_maps(self, shared_extracted_maps):
        """Test that extraction finds at least one map."""
        maps, output_dir = shared_extracted_maps

        assert len(maps) > 0, "Should extract at least one map from test PDF"

    def test_extracted_maps_have_correct_structure(self, shared_extracted_maps):
        """Test that extracted maps have all required metadata fields."""
        maps, output_dir = shared_extracted_maps

        for map_meta in maps:
            assert map_meta.name, "Map missing name"
            assert map_meta.chapter == "Test Chapter", "Map has wrong chapter"
            assert map_meta.page_num >= 1, "Map has invalid page number"
            assert map_meta.type in ["navigation_map", "battle_map"], "Map has invalid type"
            assert map_meta.source in ["extracted", "segmented"], "Map has invalid source"

    def test_output_files_exist(self, shared_extracted_maps):
        """Test that output PNG files are created for extracted maps."""
        maps, output_dir = shared_extracted_maps

        # Check that map files exist
        png_files = [f for f in os.listdir(output_dir) if f.endswith('.png') and not f.startswith('.')]
        assert len(png_files) == len(maps), f"Expected {len(maps)} PNG files, found {len(png_files)}"

        # Verify PNG files are non-empty
        for png_file in png_files:
            filepath = os.path.join(output_dir, png_file)
            assert os.path.getsize(filepath) > 1000, f"{png_file} is too small"

    def test_output_files_have_valid_size(self, shared_extracted_maps):
        """Test that output files are substantial (not corrupt)."""
        maps, output_dir = shared_extracted_maps

        png_files = [f for f in os.listdir(output_dir) if f.endswith('.png') and not f.startswith('.')]

        for png_file in png_files:
            filepath = os.path.join(output_dir, png_file)
            filesize = os.path.getsize(filepath)

            # Maps should be substantial (at least 10KB)
            assert filesize > 10000, f"{png_file} is too small ({filesize} bytes), likely corrupt"
            # Maps shouldn't be unreasonably large (less than 10MB)
            assert filesize < 10_000_000, f"{png_file} is too large ({filesize} bytes)"

    def test_temp_directory_created_for_segmentation(self, shared_extracted_maps):
        """Test that temp/ directory is created when Imagen segmentation is used."""
        maps, output_dir = shared_extracted_maps

        # If any maps used segmentation, temp directory should exist
        segmented_maps = [m for m in maps if m.source == "segmented"]
        if segmented_maps:
            temp_dir = os.path.join(output_dir, "temp")
            assert os.path.isdir(temp_dir), "Temp directory should exist when segmentation is used"

            # Verify debug files exist
            debug_files = [f for f in os.listdir(temp_dir) if f.endswith('.png')]
            # Should have at least preprocessed and red_perimeter images per segmented map
            assert len(debug_files) >= len(segmented_maps) * 2, "Missing debug files for segmentation"

    def test_extraction_methods_used(self, shared_extracted_maps):
        """
        Assert that the extraction produced maps from at least one of the available methods.
        
        Counts maps with source "extracted" (PyMuPDF) and "segmented" (Imagen) and fails if both counts are zero. Prints the counts for debugging.
        """
        maps, output_dir = shared_extracted_maps

        extracted_by_pymupdf = sum(1 for m in maps if m.source == "extracted")
        segmented_by_imagen = sum(1 for m in maps if m.source == "segmented")

        # At least one method should have been used
        assert extracted_by_pymupdf > 0 or segmented_by_imagen > 0

        # Print metrics for debugging
        print(f"\nExtraction metrics:")
        print(f"  PyMuPDF extraction: {extracted_by_pymupdf}")
        print(f"  Imagen segmentation: {segmented_by_imagen}")


@pytest.mark.map
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.smoke
class TestExtractionPerformance:
    """Performance test that runs fresh extraction to measure timing."""

    @pytest.mark.timeout(360)  # 6 minute timeout
    @pytest.mark.flaky(reruns=2, reruns_delay=30)
    def test_full_extraction_performance(self, test_pdf_path, test_output_dir, check_api_key):
        """Test extraction performance on real PDF.

        This test runs a fresh extraction (not using shared fixture) to
        accurately measure timing. It validates that extraction completes
        within acceptable time limits.
        """
        start_time = time.time()
        maps = asyncio.run(extract_maps_from_pdf(
            test_pdf_path,
            test_output_dir,
            chapter_name="Performance Test"
        ))
        elapsed = time.time() - start_time

        assert len(maps) > 0, "Should extract at least one map"

        print(f"\n{'='*60}")
        print(f"EXTRACTION PERFORMANCE")
        print(f"{'='*60}")
        print(f"Total maps: {len(maps)}")
        print(f"Time: {elapsed:.1f}s")
        print(f"Avg per map: {elapsed/len(maps):.1f}s")
        print(f"{'='*60}\n")

        # Performance assertion
        assert elapsed < 300, f"Extraction took {elapsed:.1f}s, should complete in under 5 minutes"


@pytest.mark.map
@pytest.mark.unit
class TestMetadataSaving:
    def test_save_metadata_creates_json_file(self, test_output_dir):
        """Test that save_metadata creates a JSON file."""
        maps = [
            MapMetadata(
                name="Test Map",
                chapter="Test Chapter",
                page_num=1,
                type="navigation_map",
                source="extracted"
            )
        ]

        save_metadata(maps, test_output_dir)

        metadata_path = os.path.join(test_output_dir, "maps_metadata.json")
        assert os.path.exists(metadata_path)

    def test_metadata_json_structure(self, test_output_dir):
        """Test that metadata JSON has correct structure."""
        maps = [
            MapMetadata(
                name="Test Map 1",
                chapter="Chapter 1",
                page_num=5,
                type="navigation_map",
                source="extracted"
            ),
            MapMetadata(
                name="Test Map 2",
                chapter="Chapter 1",
                page_num=10,
                type="battle_map",
                source="segmented"
            )
        ]

        save_metadata(maps, test_output_dir)

        metadata_path = os.path.join(test_output_dir, "maps_metadata.json")
        with open(metadata_path) as f:
            data = json.load(f)

        assert "extracted_at" in data
        assert "total_maps" in data
        assert "maps" in data
        assert data["total_maps"] == 2
        assert len(data["maps"]) == 2

        for map_data in data["maps"]:
            assert "name" in map_data
            assert "chapter" in map_data
            assert "page_num" in map_data
            assert "type" in map_data
            assert "source" in map_data
            assert map_data["source"] in ["extracted", "segmented"]
            assert map_data["type"] in ["navigation_map", "battle_map"]


@pytest.mark.map
@pytest.mark.integration
@pytest.mark.slow
class TestExtractSinglePage:
    @pytest.mark.timeout(120)  # 2 minute timeout (single page)
    def test_extract_single_page_with_detection(self, test_pdf_path, test_output_dir, check_api_key):
        """Test extracting a single page with a map detection result."""
        detection = MapDetectionResult(
            has_map=True,
            type="navigation_map",
            name="Test Map"
        )

        metadata = asyncio.run(
            extract_single_page(test_pdf_path, 1, detection, test_output_dir, "Test Chapter")
        )

        # May return None if extraction fails (no map on page 1)
        assert metadata is None or isinstance(metadata, MapMetadata)

        if metadata:
            assert metadata.name == "Test Map"
            assert metadata.type == "navigation_map"
            assert metadata.page_num == 1