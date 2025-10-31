"""Tests for upload_journal_to_foundry script."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.foundry.upload_journal_to_foundry import (
    find_latest_run,
    find_xml_directory,
    upload_run_to_foundry,
    upload_scene_gallery
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

    @patch('src.foundry.upload_journal_to_foundry.convert_xml_directory_to_journals')
    @patch('src.foundry.upload_journal_to_foundry.FoundryClient')
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
        mock_client.create_or_replace_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(run_dir), target="local", journal_name="Test Module")

        assert result["uploaded"] == 1
        assert result["failed"] == 0
        mock_client.create_or_replace_journal.assert_called_once_with(
            name="Test Module",
            pages=[{"name": "01_Test", "content": "<h1>Test</h1>"}]
        )

    @patch('src.foundry.upload_journal_to_foundry.convert_xml_directory_to_journals')
    @patch('src.foundry.upload_journal_to_foundry.FoundryClient')
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
        mock_client.create_or_replace_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(run_dir), target="local", journal_name="Test Module")

        assert result["uploaded"] == 2  # 2 pages uploaded
        assert result["failed"] == 0

        # Verify single journal created with both pages
        mock_client.create_or_replace_journal.assert_called_once()
        call_args = mock_client.create_or_replace_journal.call_args
        assert call_args.kwargs["name"] == "Test Module"
        assert len(call_args.kwargs["pages"]) == 2
        assert call_args.kwargs["pages"][0]["name"] == "01_Chapter_One"
        assert call_args.kwargs["pages"][1]["name"] == "02_Chapter_Two"


class TestSceneGalleryUpload:
    """Tests for scene gallery upload function."""

    def test_upload_scene_gallery_no_gallery_file(self, tmp_path):
        """Test that upload_scene_gallery returns None when no gallery file exists."""
        run_dir = tmp_path / "run_20250101_120000"
        run_dir.mkdir()

        mock_client = Mock()
        mock_client.client_id = "test_client"

        result = upload_scene_gallery(mock_client, run_dir)

        assert result is None

    def test_upload_scene_gallery_with_images(self, tmp_path):
        """Test uploading scene gallery with images."""
        # Create run directory structure
        run_dir = tmp_path / "run_20250101_120000"
        scene_dir = run_dir / "scene_artwork"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True)

        # Create test image file
        test_image = images_dir / "scene_001_cave_entrance.png"
        test_image.write_bytes(b"fake_png_data")

        # Create gallery HTML with image reference
        gallery_html = """
<h1>Scene Gallery</h1>
<h2>Cave Entrance</h2>
<img src="images/scene_001_cave_entrance.png" alt="Cave Entrance" />
<p>A dark cave entrance.</p>
"""
        gallery_file = scene_dir / "scene_gallery.html"
        gallery_file.write_text(gallery_html)

        # Mock client
        mock_client = Mock()
        mock_client.client_id = "test_client"
        mock_client.upload_file = Mock()

        # Call function
        result = upload_scene_gallery(mock_client, run_dir)

        # Verify upload was called
        mock_client.upload_file.assert_called_once_with(
            str(test_image),
            "worlds/test_client/images/scene_001_cave_entrance.png"
        )

        # Verify result structure
        assert result is not None
        assert result["name"] == "Scene Gallery"
        assert result["type"] == "text"
        assert result["text"]["format"] == 1

        # Verify HTML paths were updated
        updated_html = result["text"]["content"]
        assert "worlds/test_client/images/scene_001_cave_entrance.png" in updated_html
        assert 'src="images/scene_001_cave_entrance.png"' not in updated_html

    def test_upload_scene_gallery_multiple_images(self, tmp_path):
        """Test uploading scene gallery with multiple images."""
        # Create run directory structure
        run_dir = tmp_path / "run_20250101_120000"
        scene_dir = run_dir / "scene_artwork"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True)

        # Create multiple test image files
        test_image_1 = images_dir / "scene_001_cave.png"
        test_image_1.write_bytes(b"fake_png_data_1")
        test_image_2 = images_dir / "scene_002_forest.jpg"
        test_image_2.write_bytes(b"fake_jpg_data_2")

        # Create gallery HTML with multiple image references
        gallery_html = """
<h1>Scene Gallery</h1>
<h2>Cave</h2>
<img src="images/scene_001_cave.png" alt="Cave" />
<h2>Forest</h2>
<img src="images/scene_002_forest.jpg" alt="Forest" />
"""
        gallery_file = scene_dir / "scene_gallery.html"
        gallery_file.write_text(gallery_html)

        # Mock client
        mock_client = Mock()
        mock_client.client_id = "test_client"
        mock_client.upload_file = Mock()

        # Call function
        result = upload_scene_gallery(mock_client, run_dir)

        # Verify both uploads were called
        assert mock_client.upload_file.call_count == 2

        # Verify result
        assert result is not None
        updated_html = result["text"]["content"]
        assert "worlds/test_client/images/scene_001_cave.png" in updated_html
        assert "worlds/test_client/images/scene_002_forest.jpg" in updated_html

    def test_upload_scene_gallery_no_images(self, tmp_path):
        """Test uploading scene gallery when images directory is empty."""
        # Create run directory structure (no images)
        run_dir = tmp_path / "run_20250101_120000"
        scene_dir = run_dir / "scene_artwork"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True)

        # Create gallery HTML
        gallery_html = "<h1>Scene Gallery</h1><p>No scenes found.</p>"
        gallery_file = scene_dir / "scene_gallery.html"
        gallery_file.write_text(gallery_html)

        # Mock client
        mock_client = Mock()
        mock_client.client_id = "test_client"

        # Call function
        result = upload_scene_gallery(mock_client, run_dir)

        # Verify no uploads
        mock_client.upload_file.assert_not_called()

        # Verify result still created
        assert result is not None
        assert result["name"] == "Scene Gallery"
        assert result["text"]["content"] == gallery_html

    @patch('src.foundry.upload_journal_to_foundry.convert_xml_directory_to_journals')
    @patch('src.foundry.upload_journal_to_foundry.FoundryClient')
    def test_upload_run_includes_scene_gallery(self, mock_client_class, mock_convert, tmp_path):
        """Test that upload_run_to_foundry includes scene gallery as final page."""
        # Create run directory with XML files and scene gallery
        run_dir = tmp_path / "run_20250101_120000"
        xml_dir = run_dir / "documents"
        xml_dir.mkdir(parents=True)
        (xml_dir / "01_Test.xml").write_text("<chapter><title>Test</title></chapter>")

        # Create scene gallery
        scene_dir = run_dir / "scene_artwork"
        scene_dir.mkdir()
        gallery_file = scene_dir / "scene_gallery.html"
        gallery_file.write_text("<h1>Scene Gallery</h1>")

        # Mock XML to journal conversion
        mock_convert.return_value = [
            {"name": "01_Test", "html": "<h1>Test</h1>", "metadata": {}}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.client_id = "test_client"
        mock_client.create_or_replace_journal.return_value = {"_id": "journal123"}
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(str(run_dir), target="local", journal_name="Test Module")

        # Verify 2 pages (1 XML + 1 scene gallery)
        assert result["uploaded"] == 2
        call_args = mock_client.create_or_replace_journal.call_args
        assert len(call_args.kwargs["pages"]) == 2
        assert call_args.kwargs["pages"][0]["name"] == "01_Test"
        assert call_args.kwargs["pages"][1]["name"] == "Scene Gallery"
