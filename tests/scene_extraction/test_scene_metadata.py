"""Tests for scene metadata preservation."""

import pytest
import json
from pathlib import Path


@pytest.mark.gemini
def test_generate_scene_art_saves_metadata(tmp_path):
    """Test that scene artwork generation saves metadata JSON."""
    from scripts.generate_scene_art import process_chapter

    # Use real XML fixture
    xml_file = Path("tests/fixtures/sample_chapter.xml")
    output_dir = tmp_path / "scene_artwork"

    # Process chapter
    result = process_chapter(xml_file, output_dir)

    # Verify metadata file exists
    metadata_file = output_dir / "scenes_metadata.json"
    assert metadata_file.exists()

    # Verify structure
    with open(metadata_file) as f:
        data = json.load(f)

    assert "scenes" in data
    assert "generated_at" in data
    assert len(data["scenes"]) > 0

    # Verify scene structure
    scene = data["scenes"][0]
    assert "section_path" in scene
    assert "name" in scene
    assert "description" in scene
    assert "image_file" in scene
