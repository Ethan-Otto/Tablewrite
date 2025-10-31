"""Tests for scene gallery journal page creation."""

import pytest
from pathlib import Path
from src.scene_extraction.create_gallery import create_scene_gallery_html
from src.scene_extraction.models import Scene


@pytest.fixture
def sample_scenes():
    """Sample scenes for testing."""
    return [
        Scene(
            section_path="Chapter 1 → Introduction → Town Square",
            name="Phandalin Town Square",
            description="A bustling market square",
            location_type="outdoor"
        ),
        Scene(
            section_path="Chapter 2 → The Cragmaw Hideout → Area 1",
            name="Cave Entrance",
            description="A dark cave entrance",
            location_type="underground"
        )
    ]


@pytest.fixture
def sample_image_paths():
    """Sample image paths for testing."""
    return {
        "Phandalin Town Square": "images/scene_001_phandalin_town_square.png",
        "Cave Entrance": "images/scene_002_cave_entrance.png"
    }


class TestCreateSceneGalleryHTML:
    """Tests for create_scene_gallery_html function."""

    def test_create_gallery_basic_structure(self, sample_scenes, sample_image_paths):
        """Test that gallery HTML has correct structure."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert "<h1>Scene Gallery</h1>" in html
        assert "Phandalin Town Square" in html
        assert "Cave Entrance" in html

    def test_create_gallery_includes_section_paths(self, sample_scenes, sample_image_paths):
        """Test that section hierarchy is included."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert "Chapter 1 → Introduction → Town Square" in html
        assert "Chapter 2 → The Cragmaw Hideout → Area 1" in html

    def test_create_gallery_includes_image_tags(self, sample_scenes, sample_image_paths):
        """Test that image tags are included with correct paths."""
        html = create_scene_gallery_html(sample_scenes, sample_image_paths)

        assert '<img src="images/scene_001_phandalin_town_square.png"' in html
        assert '<img src="images/scene_002_cave_entrance.png"' in html

    def test_create_gallery_handles_missing_image(self, sample_scenes):
        """Test that gallery handles scenes with missing images."""
        image_paths = {
            "Phandalin Town Square": "images/scene_001.png"
            # Cave Entrance missing
        }

        html = create_scene_gallery_html(sample_scenes, image_paths)

        # Should include both scenes but only one image
        assert "Phandalin Town Square" in html
        assert "Cave Entrance" in html
        assert '<img src="images/scene_001.png"' in html
        assert "No image available" in html or "scene_002" not in html

    def test_create_gallery_empty_scenes(self):
        """Test gallery with no scenes."""
        html = create_scene_gallery_html([], {})

        assert "<h1>Scene Gallery</h1>" in html
        assert "No scenes found" in html or "<p>This chapter contains no scene artwork.</p>" in html
