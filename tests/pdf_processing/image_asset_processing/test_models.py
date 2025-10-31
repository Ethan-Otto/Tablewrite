"""Tests for data models."""
import pytest
from pydantic import ValidationError
from src.pdf_processing.image_asset_processing.models import MapDetectionResult, MapMetadata


@pytest.mark.map
@pytest.mark.unit
class TestMapDetectionResult:
    def test_valid_navigation_map(self):
        result = MapDetectionResult(has_map=True, type="navigation_map", name="Cragmaw Hideout")
        assert result.has_map is True
        assert result.type == "navigation_map"
        assert result.name == "Cragmaw Hideout"

    def test_valid_battle_map(self):
        result = MapDetectionResult(has_map=True, type="battle_map", name="Redbrand Hideout")
        assert result.has_map is True
        assert result.type == "battle_map"
        assert result.name == "Redbrand Hideout"

    def test_no_map(self):
        result = MapDetectionResult(has_map=False, type=None, name=None)
        assert result.has_map is False
        assert result.type is None
        assert result.name is None

    def test_optional_fields(self):
        result = MapDetectionResult(has_map=True)
        assert result.has_map is True
        assert result.type is None
        assert result.name is None


@pytest.mark.map
@pytest.mark.unit
class TestMapMetadata:
    def test_valid_metadata_with_chapter(self):
        metadata = MapMetadata(
            name="Cragmaw Hideout",
            chapter="Chapter 1",
            page_num=5,
            type="navigation_map",
            source="extracted"
        )
        assert metadata.name == "Cragmaw Hideout"
        assert metadata.chapter == "Chapter 1"
        assert metadata.page_num == 5
        assert metadata.type == "navigation_map"
        assert metadata.source == "extracted"

    def test_valid_metadata_without_chapter(self):
        metadata = MapMetadata(
            name="Random Encounter",
            chapter=None,
            page_num=42,
            type="battle_map",
            source="segmented"
        )
        assert metadata.chapter is None

    def test_json_serialization(self):
        metadata = MapMetadata(
            name="Test Map",
            chapter=None,
            page_num=1,
            type="navigation_map",
            source="extracted"
        )
        json_data = metadata.model_dump()
        assert json_data["chapter"] is None
        assert json_data["name"] == "Test Map"
