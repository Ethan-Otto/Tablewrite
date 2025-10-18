"""Tests for upload_to_foundry script."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.foundry.upload_to_foundry import (
    find_latest_run,
    find_xml_directory,
    upload_run_to_foundry
)


class TestUploadScript:
    """Tests for upload script functions."""

    def test_find_latest_run(self, tmp_path):
        """Test finding the most recent run directory."""
        output_dir = tmp_path / "output" / "runs"
        output_dir.mkdir(parents=True)

        # Create mock run directories
        (output_dir / "20250101_120000").mkdir()
        (output_dir / "20250102_120000").mkdir()
        (output_dir / "20250103_120000").mkdir()

        latest = find_latest_run(str(tmp_path / "output" / "runs"))

        assert latest == str(output_dir / "20250103_120000")

    def test_find_xml_directory(self, tmp_path):
        """Test finding XML directory in run directory."""
        # Create run directory with documents folder
        run_dir = tmp_path / "run_20250101_120000"
        xml_dir = run_dir / "documents"
        xml_dir.mkdir(parents=True)

        # Create test XML files
        (xml_dir / "01_Chapter_One.xml").write_text("<chapter><title>Chapter 1</title></chapter>")
        (xml_dir / "02_Chapter_Two.xml").write_text("<chapter><title>Chapter 2</title></chapter>")

        found_dir = find_xml_directory(str(run_dir))

        assert found_dir == str(xml_dir)

    def test_find_xml_directory_no_xml_files(self, tmp_path):
        """Test finding XML directory raises error when no XML files exist."""
        run_dir = tmp_path / "run_20250101_120000"
        run_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="No XML files found"):
            find_xml_directory(str(run_dir))

    @patch('src.foundry.upload_to_foundry.convert_xml_directory_to_journals')
    @patch('src.foundry.upload_to_foundry.FoundryClient')
    def test_upload_run_to_foundry(self, mock_client_class, mock_convert, tmp_path):
        """Test uploading XML files to Foundry as single journal with multiple pages."""
        # Create run directory with XML files
        run_dir = tmp_path / "run_20250101_120000"
        xml_dir = run_dir / "documents"
        xml_dir.mkdir(parents=True)
        (xml_dir / "01_Test.xml").write_text("<chapter><title>Test</title></chapter>")

        # Mock XML to journal conversion
        mock_convert.return_value = [
            {"name": "01_Test", "html": "<h1>Test</h1>", "metadata": {}}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.create_or_update_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(run_dir), target="local", journal_name="Test Module")

        assert result["uploaded"] == 1
        assert result["failed"] == 0
        mock_client.create_or_update_journal.assert_called_once_with(
            name="Test Module",
            pages=[{"name": "01_Test", "content": "<h1>Test</h1>"}]
        )

    @patch('src.foundry.upload_to_foundry.convert_xml_directory_to_journals')
    @patch('src.foundry.upload_to_foundry.FoundryClient')
    def test_upload_run_to_foundry_multiple_pages(self, mock_client_class, mock_convert, tmp_path):
        """Test uploading multiple XML files as pages in single journal."""
        # Create run directory with XML files
        run_dir = tmp_path / "run_20250101_120000"
        xml_dir = run_dir / "documents"
        xml_dir.mkdir(parents=True)
        (xml_dir / "01_Chapter_One.xml").write_text("<chapter><title>Chapter 1</title></chapter>")
        (xml_dir / "02_Chapter_Two.xml").write_text("<chapter><title>Chapter 2</title></chapter>")

        # Mock XML to journal conversion
        mock_convert.return_value = [
            {"name": "01_Chapter_One", "html": "<h1>Chapter 1</h1>", "metadata": {}},
            {"name": "02_Chapter_Two", "html": "<h1>Chapter 2</h1>", "metadata": {}}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.create_or_update_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(run_dir), target="local", journal_name="Test Module")

        assert result["uploaded"] == 2  # 2 pages uploaded
        assert result["failed"] == 0

        # Verify single journal created with both pages
        mock_client.create_or_update_journal.assert_called_once()
        call_args = mock_client.create_or_update_journal.call_args
        assert call_args.kwargs["name"] == "Test Module"
        assert len(call_args.kwargs["pages"]) == 2
        assert call_args.kwargs["pages"][0]["name"] == "01_Chapter_One"
        assert call_args.kwargs["pages"][1]["name"] == "02_Chapter_Two"
