"""Tests for caches.spell_cache."""

import pytest
from unittest.mock import patch, MagicMock
from caches import SpellCache


class TestSpellCache:
    """Tests for SpellCache class."""

    @pytest.fixture
    def mock_spells(self):
        """Sample spell data from FoundryVTT."""
        return [
            {
                'name': 'Fireball',
                'uuid': 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0',
                'level': 3,
                'school': 'evo'
            },
            {
                'name': 'Magic Missile',
                'uuid': 'Compendium.dnd5e.spells.Item.abc123',
                'level': 1,
                'school': 'evo'
            },
            {
                'name': 'Cure Wounds',
                'uuid': 'Compendium.dnd5e.spells.Item.def456',
                'level': 1,
                'school': 'evo'
            }
        ]

    def test_init(self):
        """Should create empty cache."""
        cache = SpellCache()

        assert not cache.loaded
        assert cache.spell_count == 0

    @patch('caches.spell_cache.fetch_all_spells_ws_sync')
    def test_load(self, mock_fetch, mock_spells):
        """Should load spells from FoundryVTT via WebSocket."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load()

        assert cache.loaded
        assert cache.spell_count == 3
        mock_fetch.assert_called_once()

    @patch('caches.spell_cache.fetch_all_spells_ws_sync')
    def test_get_spell_uuid(self, mock_fetch, mock_spells):
        """Should return UUID for spell by name."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load()

        # Exact match
        assert cache.get_spell_uuid('Fireball') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'

        # Case-insensitive
        assert cache.get_spell_uuid('fireball') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'
        assert cache.get_spell_uuid('FIREBALL') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'

        # Not found
        assert cache.get_spell_uuid('Nonexistent Spell') is None

    @patch('caches.spell_cache.fetch_all_spells_ws_sync')
    def test_get_spell_data(self, mock_fetch, mock_spells):
        """Should return full spell data."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load()

        spell = cache.get_spell_data('Magic Missile')

        assert spell is not None
        assert spell['name'] == 'Magic Missile'
        assert spell['uuid'] == 'Compendium.dnd5e.spells.Item.abc123'
        assert spell['level'] == 1

    @patch('caches.spell_cache.fetch_all_spells_ws_sync')
    def test_get_before_load(self, mock_fetch):
        """Should return None if called before load()."""
        cache = SpellCache()

        # Should log warning and return None
        assert cache.get_spell_uuid('Fireball') is None
        assert cache.get_spell_data('Fireball') is None

        # Should not have called fetch
        mock_fetch.assert_not_called()

    @patch('caches.spell_cache.fetch_all_spells_ws_sync')
    def test_load_failure_raises_runtime_error(self, mock_fetch):
        """Should raise RuntimeError if WebSocket fetch fails (no fallback)."""
        mock_fetch.side_effect = ConnectionError("Backend not running")

        cache = SpellCache()

        with pytest.raises(RuntimeError, match="SpellCache WebSocket fetch failed"):
            cache.load()

        # Cache should not be marked as loaded
        assert not cache.loaded
