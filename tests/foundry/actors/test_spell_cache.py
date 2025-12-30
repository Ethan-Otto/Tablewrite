"""Tests for foundry.actors.spell_cache."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.actors.spell_cache import SpellCache


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

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_load(self, mock_fetch, mock_spells):
        """Should load spells from FoundryVTT via relay (legacy mode)."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load(use_websocket=False)

        assert cache.loaded
        assert cache.spell_count == 3
        mock_fetch.assert_called_once()

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_get_spell_uuid(self, mock_fetch, mock_spells):
        """Should return UUID for spell by name."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load(use_websocket=False)

        # Exact match
        assert cache.get_spell_uuid('Fireball') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'

        # Case-insensitive
        assert cache.get_spell_uuid('fireball') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'
        assert cache.get_spell_uuid('FIREBALL') == 'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'

        # Not found
        assert cache.get_spell_uuid('Nonexistent Spell') is None

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_get_spell_data(self, mock_fetch, mock_spells):
        """Should return full spell data."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load(use_websocket=False)

        spell = cache.get_spell_data('Magic Missile')

        assert spell is not None
        assert spell['name'] == 'Magic Missile'
        assert spell['uuid'] == 'Compendium.dnd5e.spells.Item.abc123'
        assert spell['level'] == 1

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_get_before_load(self, mock_fetch):
        """Should return None if called before load()."""
        cache = SpellCache()

        # Should log warning and return None
        assert cache.get_spell_uuid('Fireball') is None
        assert cache.get_spell_data('Fireball') is None

        # Should not have called fetch
        mock_fetch.assert_not_called()

    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_load_with_credentials(self, mock_fetch, mock_spells):
        """Should pass credentials to fetch_all_spells() in legacy mode."""
        mock_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load(
            relay_url='https://example.com',
            api_key='test-key',
            client_id='test-client',
            use_websocket=False
        )

        mock_fetch.assert_called_once_with(
            relay_url='https://example.com',
            api_key='test-key',
            client_id='test-client'
        )

    @patch('foundry.actors.spell_cache.fetch_all_spells_ws_sync')
    def test_load_via_websocket(self, mock_ws_fetch, mock_spells):
        """Should load spells from FoundryVTT via WebSocket (default mode)."""
        mock_ws_fetch.return_value = mock_spells

        cache = SpellCache()
        cache.load(use_websocket=True)

        assert cache.loaded
        assert cache.spell_count == 3
        mock_ws_fetch.assert_called_once()

    @patch('foundry.actors.spell_cache.fetch_all_spells_ws_sync')
    @patch('foundry.actors.spell_cache.fetch_all_spells')
    def test_websocket_fallback_to_relay(self, mock_relay, mock_ws, mock_spells):
        """Should fall back to relay if WebSocket fails and relay_url is configured."""
        mock_ws.side_effect = RuntimeError("WebSocket connection failed")
        mock_relay.return_value = mock_spells

        cache = SpellCache()
        cache.load(relay_url='https://example.com', use_websocket=True)

        # Should have tried WebSocket first
        mock_ws.assert_called_once()
        # Then fallen back to relay
        mock_relay.assert_called_once()
        # And successfully loaded
        assert cache.loaded
        assert cache.spell_count == 3
