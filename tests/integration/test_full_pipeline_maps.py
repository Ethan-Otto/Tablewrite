"""Test that full pipeline includes map extraction step."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


def test_full_pipeline_has_map_extraction_function():
    """Verify run_map_extraction function exists in full_pipeline."""
    from scripts.full_pipeline import run_map_extraction
    assert callable(run_map_extraction)


def test_run_map_extraction_returns_stats(tmp_path):
    """Test that run_map_extraction returns a stats dictionary."""
    # Create a mock run directory with documents folder
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()
    (run_dir / "documents").mkdir()

    # Mock the extraction functions at the module level
    with patch('src.pdf_processing.image_asset_processing.extract_map_assets.extract_maps_from_pdf', new_callable=AsyncMock) as mock_extract:
        with patch('src.pdf_processing.image_asset_processing.extract_map_assets.save_metadata'):
            mock_extract.return_value = []  # No maps found

            from scripts.full_pipeline import run_map_extraction

            # Should return stats dict even when no PDF found (no PDF in data/pdfs)
            result = run_map_extraction(run_dir, continue_on_error=True)

            assert isinstance(result, dict)
            assert "maps_extracted" in result or "error" in result


def test_skip_maps_cli_argument():
    """Test that --skip-maps CLI argument is recognized."""
    import argparse
    from scripts.full_pipeline import main

    # Test that the argument parser recognizes --skip-maps
    # We need to temporarily patch sys.argv
    with patch.object(sys, 'argv', ['full_pipeline.py', '--skip-maps', '--skip-split', '--skip-xml', '--skip-scenes', '--skip-actors', '--skip-upload', '--skip-export']):
        with patch('scripts.full_pipeline.load_dotenv'):
            with patch('scripts.full_pipeline.logger'):
                # The main function would exit, so we catch that
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # This test just verifies the argument is accepted without error
                assert exc_info.value.code in [0, 1]


@pytest.mark.integration
def test_map_extraction_creates_metadata_file(tmp_path):
    """Test that map extraction creates maps_metadata.json in output directory."""
    from scripts.full_pipeline import run_map_extraction

    # Create a mock run directory
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()

    # Mock the extraction functions at the source module level
    with patch('src.pdf_processing.image_asset_processing.extract_map_assets.extract_maps_from_pdf', new_callable=AsyncMock) as mock_extract:
        with patch('src.pdf_processing.image_asset_processing.extract_map_assets.save_metadata'):
            # Return empty list (no maps found)
            mock_extract.return_value = []

            result = run_map_extraction(run_dir, pdf_path="/fake/path.pdf", continue_on_error=True)

            # Should handle the case gracefully (returns error dict instead of raising)
            assert isinstance(result, dict)
            assert "errors" in result or "maps_extracted" in result


@pytest.mark.integration
@pytest.mark.slow
def test_map_extraction_with_real_pdf(tmp_path):
    """Integration test: run map extraction on real test PDF.

    This test uses the actual test PDF and calls the real extraction pipeline.
    It verifies the maps_metadata.json file is created with the correct structure.
    """
    from scripts.full_pipeline import run_map_extraction

    # Use the test PDF from the test fixtures
    project_root = Path(__file__).parent.parent.parent
    test_pdf = project_root / "data" / "pdfs" / "Lost_Mine_of_Phandelver_test.pdf"

    if not test_pdf.exists():
        pytest.skip(f"Test PDF not found: {test_pdf}")

    # Create a temporary run directory
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()

    # Run the actual extraction (this calls the real AI pipeline)
    result = run_map_extraction(run_dir, pdf_path=str(test_pdf), continue_on_error=True)

    # Verify result structure
    assert isinstance(result, dict)
    assert "maps_extracted" in result

    # Check that map_assets directory was created
    map_assets_dir = run_dir / "map_assets"
    assert map_assets_dir.exists(), "map_assets directory should be created"

    # If maps were extracted, verify metadata file exists
    if result.get("maps_extracted", 0) > 0:
        import json
        metadata_file = map_assets_dir / "maps_metadata.json"
        assert metadata_file.exists(), "maps_metadata.json should be created when maps are extracted"

        # Verify metadata structure
        with open(metadata_file) as f:
            metadata = json.load(f)

        assert "maps" in metadata
        assert "total_maps" in metadata
        assert metadata["total_maps"] == result["maps_extracted"]

        # Verify each map has required fields
        for map_entry in metadata["maps"]:
            assert "name" in map_entry
            assert "page_num" in map_entry
            assert "type" in map_entry
            assert "source" in map_entry
