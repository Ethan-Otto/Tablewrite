"""Tests for automatic image positioning in Journal model."""

import pytest
from pathlib import Path
from models.xml_document import parse_xml_file
from models.journal import Journal, ImageMetadata


def test_add_map_assets_positions_images_near_source_page():
    """Test that map assets are positioned near their source page in the Journal."""
    # Load a real XML document
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    # Simulate map metadata from extract_map_assets.py
    map_metadata = [
        {
            "name": "Goblin Ambush",
            "page_num": 5,
            "type": "battle_map",
            "source": "extracted"
        },
        {
            "name": "Cragmaw Hideout",
            "page_num": 8,
            "type": "navigation_map",
            "source": "segmented"
        }
    ]

    # Add map assets to journal
    journal.add_map_assets(map_metadata, image_dir=Path("output/runs/test/map_assets/images"))

    # Verify maps were added to registry
    assert "page_005_goblin_ambush" in journal.image_registry
    assert "page_008_cragmaw_hideout" in journal.image_registry

    # Verify positioning: should be at first content after page 5
    img_meta = journal.image_registry["page_005_goblin_ambush"]
    assert img_meta.insert_before_content_id is not None
    assert "chapter_0_section" in img_meta.insert_before_content_id
