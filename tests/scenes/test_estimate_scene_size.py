"""Tests for scene size estimation module."""

import os
import pytest
from pathlib import Path
from PIL import Image


@pytest.mark.unit
class TestEstimateSceneSize:
    """Test estimate_scene_size function."""

    @pytest.mark.smoke
    def test_estimate_scene_size_wide_image(self, tmp_path):
        """Test grid size estimation for a wide image (2000x1000).

        Expected: ~80px grid (longest edge 2000 / 25 = 80, rounded to nearest 10)
        Acceptable range: 60-100px
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a wide test image (2000x1000)
        test_image = tmp_path / "wide_map.png"
        with Image.new("RGB", (2000, 1000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be ~80px (2000/25=80, already round)
            assert 60 <= result <= 100, f"Expected 60-100px, got {result}px"
            # Should be rounded to nearest 10
            assert result % 10 == 0, f"Expected multiple of 10, got {result}"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_tall_image(self, tmp_path):
        """Test grid size estimation for a tall image (1000x3000).

        Expected: ~120px grid (longest edge 3000 / 25 = 120)
        Acceptable range: 100-150px
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a tall test image (1000x3000)
        test_image = tmp_path / "tall_map.png"
        with Image.new("RGB", (1000, 3000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be ~120px (3000/25=120)
            assert 100 <= result <= 150, f"Expected 100-150px, got {result}px"
            # Should be rounded to nearest 10
            assert result % 10 == 0, f"Expected multiple of 10, got {result}"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_custom_target_squares(self, tmp_path):
        """Test grid size estimation with custom target_squares parameter.

        Image 2000x1000 with target_squares=40:
        Expected: ~50px grid (2000/40=50)
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a test image (2000x1000)
        test_image = tmp_path / "custom_target_map.png"
        with Image.new("RGB", (2000, 1000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image, target_squares=40)

            # Should be ~50px (2000/40=50)
            assert result == 50, f"Expected 50px, got {result}px"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_small_image_clamps_to_minimum(self, tmp_path):
        """Test that small images clamp grid size to minimum (50px).

        Image 500x500 with target_squares=25:
        Raw calculation: 500/25=20px, but should clamp to 50px minimum
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a small test image (500x500)
        test_image = tmp_path / "small_map.png"
        with Image.new("RGB", (500, 500), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be clamped to minimum of 50px
            assert result == 50, f"Expected 50px (minimum), got {result}px"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_large_image_clamps_to_maximum(self, tmp_path):
        """Test that large images clamp grid size to maximum (200px).

        Image 10000x10000 with target_squares=25:
        Raw calculation: 10000/25=400px, but should clamp to 200px maximum
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a large test image (10000x10000)
        test_image = tmp_path / "large_map.png"
        with Image.new("RGB", (10000, 10000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be clamped to maximum of 200px
            assert result == 200, f"Expected 200px (maximum), got {result}px"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_rounds_to_nearest_10(self, tmp_path):
        """Test that grid size is rounded to nearest 10 pixels.

        Image 2500x1000 with target_squares=25:
        Raw calculation: 2500/25=100px, which is already a multiple of 10
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a test image (2500x1000)
        test_image = tmp_path / "round_map.png"
        with Image.new("RGB", (2500, 1000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be 100px (2500/25=100)
            assert result == 100, f"Expected 100px, got {result}px"
            assert result % 10 == 0, f"Expected multiple of 10, got {result}"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_rounds_correctly(self, tmp_path):
        """Test rounding behavior (round to nearest 10).

        Image 1700x1000 with target_squares=25:
        Raw calculation: 1700/25=68px -> rounds to 70px
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a test image (1700x1000)
        test_image = tmp_path / "rounding_map.png"
        with Image.new("RGB", (1700, 1000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # 1700/25=68 -> rounds to 70
            assert result == 70, f"Expected 70px (68 rounded to nearest 10), got {result}px"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_square_image(self, tmp_path):
        """Test grid size estimation for a square image.

        Image 2000x2000 with target_squares=25:
        Expected: 80px grid (2000/25=80)
        """
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a square test image (2000x2000)
        test_image = tmp_path / "square_map.png"
        with Image.new("RGB", (2000, 2000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            # Should be 80px (2000/25=80)
            assert result == 80, f"Expected 80px, got {result}px"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_returns_int(self, tmp_path):
        """Test that the function returns an integer, not a float."""
        from scenes.estimate_scene_size import estimate_scene_size

        # Create a test image (2000x1000)
        test_image = tmp_path / "int_check_map.png"
        with Image.new("RGB", (2000, 1000), color="white") as img:
            img.save(test_image)

        try:
            result = estimate_scene_size(test_image)

            assert isinstance(result, int), f"Expected int, got {type(result)}"
        finally:
            os.unlink(test_image)

    def test_estimate_scene_size_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing image."""
        from scenes.estimate_scene_size import estimate_scene_size

        non_existent = tmp_path / "does_not_exist.png"

        with pytest.raises(FileNotFoundError):
            estimate_scene_size(non_existent)
