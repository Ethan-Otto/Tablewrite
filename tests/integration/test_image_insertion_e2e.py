"""End-to-end test for automatic image insertion."""

import pytest
import json
from pathlib import Path
from PIL import Image


@pytest.mark.integration
def test_full_pipeline_with_image_insertion(tmp_path):
    """Test complete workflow: XML → Journal → positioned images → HTML."""
    # Setup run directory
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    maps_dir = run_dir / "map_assets" / "images"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create map metadata
    maps_metadata = {
        "maps": [
            {
                "name": "Goblin Ambush",
                "page_num": 5,
                "type": "battle_map",
                "source": "extracted"
            }
        ]
    }
    with open(run_dir / "map_assets" / "maps_metadata.json", "w") as f:
        json.dump(maps_metadata, f)

    # Create scene metadata
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
                "name": "Forest Road",
                "description": "Dense forest",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_road.png"
            },
            {
                "section_path": "Chapter 1: Goblin Arrows → The Cragmaw Hideout → Area 1: Cave Entrance",
                "name": "Cave Entrance",
                "description": "Rocky cave",
                "location_type": "underground",
                "image_file": "images/scene_002_cave_entrance.png"
            }
        ]
    }
    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock images
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_goblin_ambush.png")

    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_road.png")
    img.save(scenes_dir / "scene_002_cave_entrance.png")

    # Load and position images
    from foundry.upload_journal_to_foundry import load_and_position_images
    journal = load_and_position_images(run_dir)

    # Verify all images in registry (scene keys include index to match filename format)
    assert "page_005_goblin_ambush" in journal.image_registry
    assert "scene_001_forest_road" in journal.image_registry
    assert "scene_002_cave_entrance" in journal.image_registry

    # Verify positioned images have insert locations
    # (Note: Original image_ref elements from XML may not have positions)
    assert journal.image_registry["page_005_goblin_ambush"].insert_before_content_id is not None
    assert journal.image_registry["scene_001_forest_road"].insert_before_content_id is not None
    assert journal.image_registry["scene_002_cave_entrance"].insert_before_content_id is not None

    # Render HTML
    image_mapping = {
        "page_005_goblin_ambush": "https://example.com/map.png",
        "scene_001_forest_road": "https://example.com/scene1.png",
        "scene_002_cave_entrance": "https://example.com/scene2.png"
    }

    html = journal.to_foundry_html(image_mapping)

    # Verify images appear in HTML
    assert "https://example.com/map.png" in html
    assert "https://example.com/scene1.png" in html
    assert "https://example.com/scene2.png" in html

    # Verify structure (headings before images)
    assert "<h1>Chapter 1: Goblin Arrows</h1>" in html
    assert "<h2>Goblin Ambush</h2>" in html
