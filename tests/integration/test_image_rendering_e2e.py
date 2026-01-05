"""End-to-end test for image rendering using real build_image_mapping."""

import pytest
import json
from pathlib import Path
from PIL import Image


@pytest.mark.integration
def test_scene_images_render_in_html_with_build_image_mapping(tmp_path):
    """Test that scene images are correctly rendered when using build_image_mapping."""
    # Setup run directory structure
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create scene metadata (matching real generate_scene_art.py output)
    # Note: section_path uses the arrow character, not ->
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows \u2192 Goblin Ambush",
                "name": "Forest Road",
                "description": "Dense forest",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_road.png"
            }
        ]
    }
    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock image with EXACT filename format used by generate_scene_art.py
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_road.png")

    # Load and position images using real functions
    from foundry.upload_journal_to_foundry import load_and_position_images, build_image_mapping
    journal = load_and_position_images(run_dir)

    # Build image mapping using real function (not manual)
    image_mapping = build_image_mapping(run_dir)

    # Verify key alignment: registry key MUST exist in image_mapping
    for registry_key in journal.image_registry:
        if registry_key.startswith("scene_"):
            assert registry_key in image_mapping, \
                f"Registry key '{registry_key}' not found in image_mapping. " \
                f"Available keys: {list(image_mapping.keys())}"

    # Render HTML
    html = journal.to_foundry_html(image_mapping)

    # Verify image appears in HTML
    assert "scene_001_forest_road.png" in html, \
        f"Image not found in HTML. HTML content: {html[:500]}..."


@pytest.mark.integration
def test_map_images_render_in_html_with_build_image_mapping(tmp_path):
    """Test that map images are correctly rendered when using build_image_mapping.

    NOTE: Maps are saved directly in map_assets/ (not map_assets/images/) by extract_map_assets.py.
    build_image_mapping looks in map_assets/images/ for consistency with scene_artwork structure,
    so we place maps there for this test.
    """
    # Setup run directory structure
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    # Maps go in images/ subdirectory for build_image_mapping to find them
    maps_dir = run_dir / "map_assets" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create map metadata (matching real extract_map_assets.py output)
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

    # Create mock image with EXACT filename format
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_goblin_ambush.png")

    # Load and position images
    from foundry.upload_journal_to_foundry import load_and_position_images, build_image_mapping
    journal = load_and_position_images(run_dir)

    # Build image mapping
    image_mapping = build_image_mapping(run_dir)

    # Verify key alignment for map assets added via add_map_assets
    # Note: The XML may have legacy image_ref elements (e.g., page_5_battle_map) that don't match
    # the new format. We specifically check for the new format keys (page_XXX_).
    map_keys_found = []
    for registry_key in journal.image_registry:
        # New format from add_map_assets: page_XXX_ (3 digits)
        if registry_key.startswith("page_") and len(registry_key) > 8 and registry_key[5:8].isdigit():
            map_keys_found.append(registry_key)
            assert registry_key in image_mapping, \
                f"Registry key '{registry_key}' not found in image_mapping"

    assert len(map_keys_found) > 0, "No map assets found in registry"

    # Render HTML
    html = journal.to_foundry_html(image_mapping)

    # Verify image appears in HTML
    assert "page_005_goblin_ambush.png" in html


@pytest.mark.integration
def test_mixed_scene_and_map_images_render_together(tmp_path):
    """Test that both scene and map images render correctly when combined."""
    # Setup run directory structure
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

    # Create scene metadata (using arrow character for section_path)
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows \u2192 Goblin Ambush",
                "name": "Forest Road",
                "description": "Dense forest",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_road.png"
            },
            {
                "section_path": "Chapter 1: Goblin Arrows \u2192 The Cragmaw Hideout \u2192 Area 1: Cave Entrance",
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
    from foundry.upload_journal_to_foundry import load_and_position_images, build_image_mapping
    journal = load_and_position_images(run_dir)

    # Build image mapping
    image_mapping = build_image_mapping(run_dir)

    # Verify dynamically added keys exist in image_mapping
    # (Legacy image_ref keys from XML may not have corresponding files)
    missing_keys = []
    for registry_key in journal.image_registry:
        # Skip legacy image_ref keys (e.g., page_5_battle_map) that don't follow new format
        if registry_key.startswith("page_") and not (len(registry_key) > 8 and registry_key[5:8].isdigit()):
            continue  # Legacy format, skip
        if registry_key not in image_mapping:
            missing_keys.append(registry_key)

    assert not missing_keys, \
        f"Registry keys not found in image_mapping: {missing_keys}. " \
        f"Available mapping keys: {list(image_mapping.keys())}"

    # Render HTML
    html = journal.to_foundry_html(image_mapping)

    # Verify all images appear in HTML
    assert "page_005_goblin_ambush.png" in html, "Map image not found in HTML"
    assert "scene_001_forest_road.png" in html, "Scene 1 image not found in HTML"
    assert "scene_002_cave_entrance.png" in html, "Scene 2 image not found in HTML"
