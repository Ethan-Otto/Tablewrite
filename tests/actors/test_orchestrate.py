"""Tests for actor orchestration pipeline."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from actors.orchestrate import _create_output_directory, _save_intermediate_file
from actors.models import StatBlock


class TestCreateOutputDirectory:
    """Test output directory creation."""

    def test_creates_directory_with_timestamp(self, tmp_path):
        """Test that directory is created with timestamp format."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        assert output_dir.exists()
        assert output_dir.is_dir()
        assert str(output_dir).startswith(str(base_dir))
        assert output_dir.name == "actors"

    def test_directory_structure(self, tmp_path):
        """Test that directory structure is output/runs/<timestamp>/actors/."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        # Should be: base_dir/<timestamp>/actors/
        assert output_dir.parent.parent == base_dir
        assert output_dir.name == "actors"

    def test_timestamp_format(self, tmp_path):
        """Test that timestamp follows YYYYMMDD_HHMMSS format."""
        base_dir = tmp_path / "test_runs"
        output_dir = _create_output_directory(str(base_dir))

        timestamp_dir = output_dir.parent.name
        # Should match format like: 20241103_143022
        assert len(timestamp_dir) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_dir[8] == "_"

    def test_creates_parents(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        base_dir = tmp_path / "nonexistent" / "nested" / "path"
        output_dir = _create_output_directory(str(base_dir))

        assert output_dir.exists()
        assert base_dir.exists()


class TestSaveIntermediateFile:
    """Test saving intermediate files."""

    def test_save_text_file(self, tmp_path):
        """Test saving plain text content."""
        filepath = tmp_path / "test.txt"
        content = "Goblin\nSmall humanoid, neutral evil"

        result = _save_intermediate_file(content, filepath, "test text")

        assert result == filepath
        assert filepath.exists()
        assert filepath.read_text() == content

    def test_save_dict_as_json(self, tmp_path):
        """Test saving dict as JSON."""
        filepath = tmp_path / "test.json"
        content = {"name": "Goblin", "cr": 0.25, "hp": 7}

        result = _save_intermediate_file(content, filepath, "test dict")

        assert result == filepath
        assert filepath.exists()

        loaded = json.loads(filepath.read_text())
        assert loaded == content

    def test_save_pydantic_model_as_json(self, tmp_path):
        """Test saving Pydantic model as JSON."""
        filepath = tmp_path / "stat_block.json"
        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin stat block...",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )

        result = _save_intermediate_file(stat_block, filepath, "StatBlock")

        assert result == filepath
        assert filepath.exists()

        loaded = json.loads(filepath.read_text())
        assert loaded["name"] == "Goblin"
        assert loaded["armor_class"] == 15

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directories are created if needed."""
        filepath = tmp_path / "nested" / "dir" / "test.txt"
        content = "test content"

        result = _save_intermediate_file(content, filepath, "nested file")

        assert filepath.exists()
        assert filepath.parent.exists()

    def test_invalid_content_type_raises_error(self, tmp_path):
        """Test that invalid content type raises IOError."""
        filepath = tmp_path / "test.txt"

        with pytest.raises(IOError, match="Failed to save list"):
            _save_intermediate_file([1, 2, 3], filepath, "list")
