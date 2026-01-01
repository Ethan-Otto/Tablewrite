"""Test suite for FoundryVTT icon cache."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.icon_cache import IconCache


class TestIconCache:
    """Tests for IconCache class."""

    @pytest.fixture
    def mock_icon_files(self):
        """Sample icon file paths from FoundryVTT."""
        return [
            "icons/weapons/swords/sword-steel.webp",
            "icons/magic/fire/fireball.webp",
            "icons/equipment/chest/plate-armor.webp"
        ]

    def test_init(self):
        """Should create empty cache."""
        cache = IconCache()

        assert not cache.loaded
        assert cache.icon_count == 0

    @patch.object(IconCache, '_load_via_websocket')
    def test_load(self, mock_ws_load, mock_icon_files):
        """Should load icons from FoundryVTT via WebSocket."""
        mock_ws_load.return_value = mock_icon_files

        cache = IconCache()
        cache.load()

        assert cache.loaded
        assert cache.icon_count == 3
        assert "icons/weapons/swords/sword-steel.webp" in cache._all_icons
        mock_ws_load.assert_called_once()

    @patch.object(IconCache, '_load_via_websocket')
    def test_load_hierarchical_categorization(self, mock_ws_load, mock_icon_files):
        """Should categorize icons by full directory hierarchy."""
        mock_ws_load.return_value = mock_icon_files

        cache = IconCache()
        cache.load()

        # Test hierarchical categorization
        assert "weapons" in cache._icons_by_category
        assert "weapons/swords" in cache._icons_by_category
        assert "magic" in cache._icons_by_category
        assert "magic/fire" in cache._icons_by_category
        assert "equipment" in cache._icons_by_category
        assert "equipment/chest" in cache._icons_by_category

        # Verify paths are in correct categories
        assert "icons/weapons/swords/sword-steel.webp" in cache._icons_by_category["weapons"]
        assert "icons/weapons/swords/sword-steel.webp" in cache._icons_by_category["weapons/swords"]
        assert "icons/magic/fire/fireball.webp" in cache._icons_by_category["magic"]
        assert "icons/magic/fire/fireball.webp" in cache._icons_by_category["magic/fire"]

    @patch.object(IconCache, '_load_via_websocket')
    def test_get_icon_before_load(self, mock_ws_load):
        """Should return None if called before load()."""
        cache = IconCache()

        # Should log warning and return None
        assert cache.get_icon("sword") is None

        # Should not have called fetch
        mock_ws_load.assert_not_called()

    @patch.object(IconCache, '_load_via_websocket')
    def test_load_failure_raises_runtime_error(self, mock_ws_load):
        """Should raise RuntimeError if WebSocket fetch fails (no fallback)."""
        mock_ws_load.side_effect = ConnectionError("Backend not running")

        cache = IconCache()

        with pytest.raises(RuntimeError, match="IconCache WebSocket fetch failed"):
            cache.load()

        # Cache should not be marked as loaded
        assert not cache.loaded


def test_categorize_icon_preserves_all_hierarchy_levels():
    """Test that _categorize_icon preserves all directory levels."""
    cache = IconCache()

    # Test deep hierarchy: icons/weapons/swords/longswords/magical/flaming-sword.webp
    deep_path = "icons/weapons/swords/longswords/magical/flaming-sword.webp"
    cache._all_icons.append(deep_path)
    cache._categorize_icon(deep_path)

    # Should create categories at all levels
    assert "weapons" in cache._icons_by_category
    assert "weapons/swords" in cache._icons_by_category
    assert "weapons/swords/longswords" in cache._icons_by_category
    assert "weapons/swords/longswords/magical" in cache._icons_by_category

    # All levels should contain the path
    assert deep_path in cache._icons_by_category["weapons"]
    assert deep_path in cache._icons_by_category["weapons/swords"]
    assert deep_path in cache._icons_by_category["weapons/swords/longswords"]
    assert deep_path in cache._icons_by_category["weapons/swords/longswords/magical"]


def test_get_icon_with_fuzzy_matching():
    """Test fuzzy matching for icon selection with hierarchical categories."""
    cache = IconCache()
    cache._all_icons = [
        "icons/weapons/swords/scimitar-curved-blue.webp",
        "icons/weapons/axes/axe-battle-worn.webp",
        "icons/magic/fire/fireball-explosion.webp"
    ]
    cache._icons_by_category = {
        "weapons": [
            "icons/weapons/swords/scimitar-curved-blue.webp",
            "icons/weapons/axes/axe-battle-worn.webp"
        ],
        "weapons/swords": ["icons/weapons/swords/scimitar-curved-blue.webp"],
        "weapons/axes": ["icons/weapons/axes/axe-battle-worn.webp"],
        "magic": ["icons/magic/fire/fireball-explosion.webp"],
        "magic/fire": ["icons/magic/fire/fireball-explosion.webp"]
    }
    cache._loaded = True

    # Test top-level category match
    icon = cache.get_icon("scimitar", category="weapons")
    assert icon == "icons/weapons/swords/scimitar-curved-blue.webp"

    # Test subcategory match (more specific)
    icon = cache.get_icon("scimitar", category="weapons/swords")
    assert icon == "icons/weapons/swords/scimitar-curved-blue.webp"

    # Test fuzzy match without category
    icon = cache.get_icon("fire ball")
    assert icon == "icons/magic/fire/fireball-explosion.webp"

    # Test no match returns None
    icon = cache.get_icon("nonexistent item")
    assert icon is None


def test_get_icon_by_keywords():
    """Test keyword matching for icon selection."""
    cache = IconCache()
    cache._all_icons = [
        "icons/weapons/swords/sword-steel.webp",
        "icons/weapons/swords/blade-curved.webp",
    ]
    cache._icons_by_category = {"weapons": cache._all_icons[:]}
    cache._loaded = True

    # Test first keyword matches
    icon = cache.get_icon_by_keywords(["sword", "blade"], category="weapons")
    assert icon == "icons/weapons/swords/sword-steel.webp"

    # Test second keyword matches
    icon = cache.get_icon_by_keywords(["scimitar", "blade"], category="weapons")
    assert icon == "icons/weapons/swords/blade-curved.webp"

    # Test no match
    icon = cache.get_icon_by_keywords(["axe", "hammer"], category="weapons")
    assert icon is None
