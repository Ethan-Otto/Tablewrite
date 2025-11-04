"""Tests for actor orchestration pipeline."""

import pytest
from pathlib import Path
import tempfile
import shutil

from actors.orchestrate import _create_output_directory


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
