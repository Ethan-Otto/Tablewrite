"""Test suite for FoundryVTT icon cache."""

import pytest
from foundry.icon_cache import IconCache


def test_icon_cache_initialization():
    """Test IconCache initializes with empty state."""
    cache = IconCache()

    assert not cache.loaded
    assert cache.icon_count == 0


@pytest.mark.integration
def test_icon_cache_load():
    """Test loading icons from FoundryVTT file system."""
    import os
    from unittest.mock import patch, MagicMock

    # Mock file system API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "files": [
            {"name": "sword-steel.webp", "path": "icons/weapons/swords/sword-steel.webp", "type": "file"},
            {"name": "fireball.webp", "path": "icons/magic/fire/fireball.webp", "type": "file"},
            {"name": "plate-armor.webp", "path": "icons/equipment/chest/plate-armor.webp", "type": "file"}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch('requests.get', return_value=mock_response):
        cache = IconCache()
        cache.load(
            relay_url="http://test",
            api_key="test_key",
            client_id="test_client"
        )

        assert cache.loaded
        assert cache.icon_count == 3
        assert "icons/weapons/swords/sword-steel.webp" in cache._all_icons

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
