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

    # Verify positioning: different pages should get different positions
    img_meta_5 = journal.image_registry["page_005_goblin_ambush"]
    img_meta_8 = journal.image_registry["page_008_cragmaw_hideout"]

    assert img_meta_5.insert_before_content_id is not None
    assert img_meta_8.insert_before_content_id is not None
    assert "chapter_0_section" in img_meta_5.insert_before_content_id
    assert "chapter_0_section" in img_meta_8.insert_before_content_id

    # Critical assertion: different source pages MUST get different positions
    assert img_meta_5.insert_before_content_id != img_meta_8.insert_before_content_id, \
        "Images from different pages should not have the same position"


def test_add_scene_artwork_positions_at_sections():
    """Test that scene artwork is positioned at section/subsection boundaries."""
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    # Simulate scene metadata from generate_scene_art.py
    scenes = [
        {
            "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
            "name": "Forest Road Ambush",
            "description": "A dense forest path with overturned wagon"
        },
        {
            "section_path": "Chapter 1: Goblin Arrows → The Cragmaw Hideout → Area 1: Cave Entrance",
            "name": "Cave Entrance",
            "description": "Rocky cave entrance with twin pools"
        }
    ]

    # Add scene artwork
    journal.add_scene_artwork(scenes, image_dir=Path("output/runs/test/scene_artwork/images"))

    # Verify scenes were added to registry
    assert "scene_forest_road_ambush" in journal.image_registry
    assert "scene_cave_entrance" in journal.image_registry

    # Verify positioning: should be at subsection boundaries
    img_meta = journal.image_registry["scene_forest_road_ambush"]
    assert img_meta.insert_before_content_id is not None
