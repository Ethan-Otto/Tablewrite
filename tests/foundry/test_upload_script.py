"""Tests for upload_to_foundry script."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.foundry.upload_to_foundry import (
    find_latest_run,
    read_html_files,
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

    def test_read_html_files(self, tmp_path):
        """Test reading HTML files from run directory."""
        html_dir = tmp_path / "documents" / "html"
        html_dir.mkdir(parents=True)

        # Create test HTML files
        (html_dir / "01_Chapter_One.html").write_text("<h1>Chapter 1</h1>")
        (html_dir / "02_Chapter_Two.html").write_text("<h1>Chapter 2</h1>")

        html_files = read_html_files(str(html_dir))

        assert len(html_files) == 2
        assert html_files[0]["name"] == "01_Chapter_One"
        assert html_files[0]["content"] == "<h1>Chapter 1</h1>"

    @patch('src.foundry.upload_to_foundry.FoundryClient')
    def test_upload_run_to_foundry(self, mock_client_class, tmp_path):
        """Test uploading HTML files to Foundry."""
        html_dir = tmp_path / "documents" / "html"
        html_dir.mkdir(parents=True)
        (html_dir / "01_Test.html").write_text("<p>Test</p>")

        mock_client = Mock()
        mock_client.create_or_update_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(html_dir), target="local")

        assert result["uploaded"] == 1
        assert result["failed"] == 0
        mock_client.create_or_update_journal.assert_called_once_with(
            name="01_Test",
            content="<p>Test</p>"
        )
