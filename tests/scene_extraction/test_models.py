"""Tests for scene extraction data models."""

import pytest
from src.scene_extraction.models import Scene, ChapterContext


class TestSceneModel:
    """Tests for Scene Pydantic model."""

    def test_scene_creation_with_all_fields(self):
        """Test creating a Scene with all fields."""
        scene = Scene(
            section_path="Chapter 2 → The Cragmaw Hideout → Area 1",
            name="Cave Mouth",
            description="A dark cave entrance with rough stone walls",
            location_type="underground",
            xml_section_id="chapter_2_area_1"
        )

        assert scene.section_path == "Chapter 2 → The Cragmaw Hideout → Area 1"
        assert scene.name == "Cave Mouth"
        assert scene.description == "A dark cave entrance with rough stone walls"
        assert scene.location_type == "underground"
        assert scene.xml_section_id == "chapter_2_area_1"

    def test_scene_creation_minimal_fields(self):
        """Test creating a Scene with only required fields."""
        scene = Scene(
            section_path="Chapter 1 → Introduction",
            name="Town Square",
            description="A bustling town square",
            location_type="outdoor"
        )

        assert scene.section_path == "Chapter 1 → Introduction"
        assert scene.name == "Town Square"
        assert scene.description == "A bustling town square"
        assert scene.location_type == "outdoor"
        assert scene.xml_section_id is None

    def test_scene_validates_non_empty_name(self):
        """Test that Scene rejects empty name."""
        with pytest.raises(ValueError):
            Scene(
                section_path="Chapter 1",
                name="",
                description="Test description",
                location_type="interior"
            )

    def test_scene_validates_non_empty_description(self):
        """Test that Scene rejects empty description."""
        with pytest.raises(ValueError):
            Scene(
                section_path="Chapter 1",
                name="Test Scene",
                description="",
                location_type="interior"
            )


class TestChapterContextModel:
    """Tests for ChapterContext Pydantic model."""

    def test_chapter_context_creation(self):
        """Test creating ChapterContext with all fields."""
        context = ChapterContext(
            environment_type="underground",
            weather="dry",
            atmosphere="oppressive",
            lighting="dim torchlight",
            terrain="rocky caverns",
            additional_notes="Goblin-infested dungeon"
        )

        assert context.environment_type == "underground"
        assert context.weather == "dry"
        assert context.atmosphere == "oppressive"
        assert context.lighting == "dim torchlight"
        assert context.terrain == "rocky caverns"
        assert context.additional_notes == "Goblin-infested dungeon"

    def test_chapter_context_optional_fields(self):
        """Test ChapterContext with minimal fields."""
        context = ChapterContext(
            environment_type="forest"
        )

        assert context.environment_type == "forest"
        assert context.weather is None
        assert context.atmosphere is None
        assert context.lighting is None
        assert context.terrain is None
        assert context.additional_notes is None
