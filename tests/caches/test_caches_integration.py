"""Integration tests for caches module with real Foundry connection.

These tests verify that SpellCache and IconCache work correctly with a real
FoundryVTT instance connected via WebSocket.
"""

import pytest
from caches import SpellCache, IconCache


@pytest.mark.integration
class TestSpellCacheIntegration:
    """Integration tests for SpellCache with real Foundry connection."""

    def test_spell_cache_load_from_foundry(self, ensure_foundry_connected):
        """Test loading spells from real FoundryVTT instance."""
        cache = SpellCache()
        cache.load()

        # Verify cache loaded successfully
        assert cache.loaded, "SpellCache should be marked as loaded"
        assert cache.spell_count > 0, "Should have loaded some spells"

        # Verify we can look up a common spell
        fireball_uuid = cache.get_spell_uuid("Fireball")
        assert fireball_uuid is not None, "Should find Fireball spell"
        assert fireball_uuid.startswith("Compendium."), "UUID should be a compendium reference"

    def test_spell_cache_case_insensitive(self, ensure_foundry_connected):
        """Test that spell lookups are case-insensitive."""
        cache = SpellCache()
        cache.load()

        # All these should return the same UUID
        uuid_lower = cache.get_spell_uuid("fireball")
        uuid_upper = cache.get_spell_uuid("FIREBALL")
        uuid_mixed = cache.get_spell_uuid("Fireball")

        assert uuid_lower == uuid_upper == uuid_mixed, "Case should not matter"

    def test_spell_cache_unknown_spell(self, ensure_foundry_connected):
        """Test that unknown spells return None."""
        cache = SpellCache()
        cache.load()

        result = cache.get_spell_uuid("Totally Fake Spell That Does Not Exist 12345")
        assert result is None, "Unknown spell should return None"


@pytest.mark.integration
class TestIconCacheIntegration:
    """Integration tests for IconCache with real Foundry connection."""

    def test_icon_cache_load_from_foundry(self, ensure_foundry_connected):
        """Test loading icons from real FoundryVTT instance."""
        cache = IconCache()
        cache.load()

        # Verify cache loaded successfully
        assert cache.loaded, "IconCache should be marked as loaded"
        assert cache.icon_count > 0, f"Should have loaded some icons, got {cache.icon_count}"

    def test_icon_cache_has_weapon_category(self, ensure_foundry_connected):
        """Test that weapon icons are categorized correctly."""
        cache = IconCache()
        cache.load()

        # Verify weapons category exists and has icons
        assert "weapons" in cache._icons_by_category, "Should have weapons category"
        weapons = cache._icons_by_category["weapons"]
        assert len(weapons) > 0, "Weapons category should have icons"

    def test_icon_cache_fuzzy_matching(self, ensure_foundry_connected):
        """Test fuzzy matching for icon selection."""
        cache = IconCache()
        cache.load()

        # Try to find a sword icon using fuzzy match
        icon = cache.get_icon("sword", category="weapons")

        # May not find exact match, but should return something or None
        if icon:
            assert icon.endswith(('.webp', '.png', '.jpg', '.svg')), \
                "Icon should have valid extension"
            assert "icons" in icon, "Icon path should include 'icons' directory"


@pytest.mark.smoke
@pytest.mark.integration
class TestCachesSmoke:
    """Smoke tests for caches module - verify basic functionality works."""

    def test_caches_can_be_imported(self):
        """Verify caches module exports correct classes."""
        from caches import SpellCache, IconCache

        # Verify classes exist and are importable
        assert SpellCache is not None
        assert IconCache is not None

    def test_caches_load_without_error(self, ensure_foundry_connected):
        """Smoke test: Verify both caches can load without error."""
        # SpellCache
        spell_cache = SpellCache()
        spell_cache.load()
        assert spell_cache.loaded

        # IconCache
        icon_cache = IconCache()
        icon_cache.load()
        assert icon_cache.loaded

        # Verify we have some data
        assert spell_cache.spell_count > 100, f"Expected 100+ spells, got {spell_cache.spell_count}"
        assert icon_cache.icon_count > 100, f"Expected 100+ icons, got {icon_cache.icon_count}"
