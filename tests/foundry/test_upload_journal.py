"""Tests for Journal-based upload workflow in upload_journal_to_foundry.py"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from models import XMLDocument, Journal, parse_xml_file
from foundry.upload_journal_to_foundry import (
    upload_run_to_foundry,
    find_latest_run,
    find_xml_directory,
    build_image_mapping,
)


# Sample XML for testing
SAMPLE_XML = """
<Chapter_1>
  <page number="1">
    <chapter_title>Introduction</chapter_title>
    <p>Welcome to the adventure.</p>
    <section>Background</section>
    <p>Long ago in a distant land...</p>
    <image_ref key="page_1_intro_illustration" />
  </page>
  <page number="2">
    <subsection>Getting Started</subsection>
    <p>To begin your quest...</p>
  </page>
</Chapter_1>
"""


@pytest.fixture
def temp_run_dir(tmp_path):
    """Create a temporary run directory with sample XML and assets."""
    run_dir = tmp_path / "runs" / "20240101_120000"
    run_dir.mkdir(parents=True)

    # Create documents directory with XML file
    docs_dir = run_dir / "documents"
    docs_dir.mkdir()
    xml_file = docs_dir / "chapter_1.xml"
    xml_file.write_text(SAMPLE_XML)

    # Create map_assets directory with sample map
    map_assets_dir = run_dir / "map_assets" / "images"
    map_assets_dir.mkdir(parents=True)
    map_image = map_assets_dir / "battle_map_1.png"
    map_image.write_text("fake png data")

    # Create scene_artwork directory with sample scene
    scene_dir = run_dir / "scene_artwork" / "images"
    scene_dir.mkdir(parents=True)
    scene_image = scene_dir / "page_1_intro_illustration.png"
    scene_image.write_text("fake scene data")

    return run_dir


@pytest.fixture
def temp_runs_dir(tmp_path):
    """Create a temporary runs directory with multiple run subdirectories."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create three run directories with different timestamps
    (runs_dir / "20240101_100000").mkdir()
    (runs_dir / "20240101_110000").mkdir()
    (runs_dir / "20240101_120000").mkdir()  # Latest

    return runs_dir


class TestFindLatestRun:
    """Tests for find_latest_run() function."""

    def test_finds_latest_run(self, temp_runs_dir):
        """Should find the most recent run directory by timestamp."""
        latest = find_latest_run(str(temp_runs_dir))
        assert latest.endswith("20240101_120000")

    def test_raises_on_missing_dir(self, tmp_path):
        """Should raise ValueError if runs directory doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            find_latest_run(str(tmp_path / "nonexistent"))

    def test_raises_on_empty_dir(self, tmp_path):
        """Should raise ValueError if no run directories found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="No run directories found"):
            find_latest_run(str(empty_dir))


class TestFindXMLDirectory:
    """Tests for find_xml_directory() function."""

    def test_finds_documents_directory(self, temp_run_dir):
        """Should find XML files in documents/ subdirectory."""
        xml_dir = find_xml_directory(str(temp_run_dir))
        assert xml_dir.endswith("documents")
        assert Path(xml_dir).exists()

    def test_finds_xml_in_root(self, tmp_path):
        """Should find XML files in run directory root if no documents/ dir."""
        run_dir = tmp_path / "run_1"
        run_dir.mkdir()
        xml_file = run_dir / "chapter.xml"
        xml_file.write_text(SAMPLE_XML)

        xml_dir = find_xml_directory(str(run_dir))
        assert xml_dir == str(run_dir)

    def test_raises_on_no_xml_files(self, tmp_path):
        """Should raise ValueError if no XML files found."""
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()

        with pytest.raises(ValueError, match="No XML files found"):
            find_xml_directory(str(run_dir))


class TestBuildImageMapping:
    """Tests for build_image_mapping() function."""

    def test_builds_mapping_from_map_assets(self, temp_run_dir):
        """Should build image mapping from map_assets directory."""
        mapping = build_image_mapping(temp_run_dir)

        # Should include map asset
        assert "battle_map_1" in mapping
        assert mapping["battle_map_1"].endswith("battle_map_1.png")

    def test_builds_mapping_from_scene_artwork(self, temp_run_dir):
        """Should build image mapping from scene_artwork directory."""
        mapping = build_image_mapping(temp_run_dir)

        # Should include scene artwork
        assert "page_1_intro_illustration" in mapping
        assert mapping["page_1_intro_illustration"].endswith("page_1_intro_illustration.png")

    def test_returns_empty_dict_when_no_images(self, tmp_path):
        """Should return empty dict when no image directories exist."""
        run_dir = tmp_path / "run_no_images"
        run_dir.mkdir()

        mapping = build_image_mapping(run_dir)
        assert mapping == {}

    def test_handles_mixed_image_types(self, temp_run_dir):
        """Should handle both PNG and JPG images."""
        # Add a JPG file
        map_dir = temp_run_dir / "map_assets" / "images"
        jpg_file = map_dir / "map_2.jpg"
        jpg_file.write_text("fake jpg")

        mapping = build_image_mapping(temp_run_dir)

        assert "battle_map_1" in mapping  # PNG
        assert "map_2" in mapping  # JPG


class TestJournalBasedUpload:
    """Tests for Journal-based upload workflow."""

    def test_parses_xml_to_journal(self, temp_run_dir):
        """Should parse XML files using XMLDocument and Journal models."""
        xml_dir = find_xml_directory(str(temp_run_dir))
        xml_files = list(Path(xml_dir).glob("*.xml"))

        assert len(xml_files) == 1

        # Parse using models
        xml_doc = parse_xml_file(xml_files[0])
        journal = Journal.from_xml_document(xml_doc)

        # Verify structure
        assert journal.title == "Chapter_1"
        assert len(journal.chapters) == 1
        assert journal.chapters[0].title == "Introduction"

    def test_journal_to_html_conversion(self, temp_run_dir):
        """Should convert Journal to HTML using to_foundry_html()."""
        xml_dir = find_xml_directory(str(temp_run_dir))
        xml_file = list(Path(xml_dir).glob("*.xml"))[0]

        # Parse to Journal
        xml_doc = parse_xml_file(xml_file)
        journal = Journal.from_xml_document(xml_doc)

        # Build image mapping
        image_mapping = build_image_mapping(temp_run_dir)

        # Convert to HTML
        html = journal.to_foundry_html(image_mapping)

        # Verify HTML structure
        assert "<h1>Introduction</h1>" in html
        assert "<h2>Background</h2>" in html
        assert "<h3>Getting Started</h3>" in html
        assert "<p>Welcome to the adventure.</p>" in html

    def test_image_mapping_applied_in_html(self, temp_run_dir):
        """Should apply image_mapping to ImageRef elements in HTML output."""
        xml_dir = find_xml_directory(str(temp_run_dir))
        xml_file = list(Path(xml_dir).glob("*.xml"))[0]

        xml_doc = parse_xml_file(xml_file)
        journal = Journal.from_xml_document(xml_doc)

        # Build image mapping
        image_mapping = build_image_mapping(temp_run_dir)

        # Convert to HTML
        html = journal.to_foundry_html(image_mapping)

        # Verify image reference is rendered with correct path
        assert "page_1_intro_illustration" in image_mapping
        assert f'<img src="{image_mapping["page_1_intro_illustration"]}"' in html

    @patch('foundry.upload_journal_to_foundry.FoundryClient')
    def test_upload_run_uses_journal_workflow(self, mock_client_class, temp_run_dir):
        """Should use XMLDocument -> Journal -> HTML workflow for upload."""
        # Setup mock client
        mock_client = Mock()
        mock_client.client_id = "test-client"
        mock_client.create_or_replace_journal.return_value = {
            'uuid': 'JournalEntry.test123',
            'entity': {'_id': 'test123'}
        }
        mock_client.upload_file = Mock()
        mock_client_class.return_value = mock_client

        # Call upload function
        result = upload_run_to_foundry(
            run_dir=str(temp_run_dir),
            target="local",
            journal_name="Test Journal"
        )

        # Verify FoundryClient was called
        mock_client_class.assert_called_once_with()

        # Verify create_or_replace_journal was called with pages
        mock_client.create_or_replace_journal.assert_called_once()
        call_args = mock_client.create_or_replace_journal.call_args

        assert call_args.kwargs['name'] == "Test Journal"
        pages = call_args.kwargs['pages']

        # Should have one page for the chapter
        assert len(pages) == 1
        assert pages[0]['name'] == "Chapter_1"
        assert "<h1>Introduction</h1>" in pages[0]['content']

        # Verify result
        assert result['uploaded'] == 1
        assert result['failed'] == 0
        assert result['journal_uuid'] == 'JournalEntry.test123'

    @patch('foundry.upload_journal_to_foundry.FoundryClient')
    def test_upload_preserves_semantic_hierarchy(self, mock_client_class, temp_run_dir):
        """Should preserve semantic hierarchy (not page-based) in upload."""
        mock_client = Mock()
        mock_client.client_id = "test-client"
        mock_client.create_or_replace_journal.return_value = {
            'uuid': 'JournalEntry.test123',
            'entity': {'_id': 'test123'}
        }
        mock_client.upload_file = Mock()
        mock_client_class.return_value = mock_client

        result = upload_run_to_foundry(
            run_dir=str(temp_run_dir),
            target="local",
            journal_name="Test"
        )

        # Get the HTML content that was uploaded
        call_args = mock_client.create_or_replace_journal.call_args
        pages = call_args.kwargs['pages']
        html = pages[0]['content']

        # Verify semantic structure (sections spanning pages)
        # Should have chapter title, section, and subsection
        assert "<h1>Introduction</h1>" in html
        assert "<h2>Background</h2>" in html
        assert "<h3>Getting Started</h3>" in html

        # Content from both pages should be merged under semantic hierarchy
        assert "Welcome to the adventure" in html
        assert "To begin your quest" in html


@pytest.mark.integration
def test_upload_journal_includes_positioned_images(tmp_path):
    """Test that upload includes automatically positioned images."""
    # Create mock run directory structure
    run_dir = tmp_path / "runs" / "test_run"
    docs_dir = run_dir / "documents"
    maps_dir = run_dir / "map_assets" / "images"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy sample XML
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create mock metadata files
    import json

    maps_metadata = {
        "maps": [
            {
                "name": "Test Map",
                "page_num": 5,
                "type": "battle_map",
                "source": "extracted"
            }
        ]
    }

    with open(run_dir / "map_assets" / "maps_metadata.json", "w") as f:
        json.dump(maps_metadata, f)

    # Create mock image files
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_test_map.png")
    img.save(scenes_dir / "scene_001_test_scene.png")

    # Load and process journal
    from foundry.upload_journal_to_foundry import load_and_position_images

    journal = load_and_position_images(run_dir)

    # Verify images are in registry with positions
    assert "page_005_test_map" in journal.image_registry
    assert journal.image_registry["page_005_test_map"].insert_before_content_id is not None


def test_load_and_position_uses_scene_metadata(tmp_path):
    """Test that scene positioning uses scenes_metadata.json."""
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create scene metadata
    import json
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
                "name": "Forest Ambush",
                "description": "Dense forest path",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_ambush.png"
            }
        ]
    }

    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_ambush.png")

    # Load journal
    from foundry.upload_journal_to_foundry import load_and_position_images
    journal = load_and_position_images(run_dir)

    # Verify scene was positioned using metadata
    assert "scene_forest_ambush" in journal.image_registry
