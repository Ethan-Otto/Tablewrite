"""Tests for foundry.items.fetch module."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.items.fetch import fetch_items_by_type, fetch_all_spells


class TestFetchItemsByType:
    """Tests for fetch_items_by_type function."""

    @patch('foundry.items.fetch.requests.get')
    @patch('foundry.items.fetch.os.getenv')
    def test_basic_fetch(self, mock_getenv, mock_get):
        """Should fetch items successfully."""
        # Setup environment variables
        mock_getenv.side_effect = lambda key: {
            'FOUNDRY_RELAY_URL': 'http://localhost:3010',
            'FOUNDRY_LOCAL_API_KEY': 'test-key',
            'FOUNDRY_LOCAL_CLIENT_ID': 'test-client'
        }.get(key)

        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},
                {'uuid': 'Compendium.dnd5e.spells.2', 'name': 'Lightning Bolt'},
            ]
        }
        mock_get.return_value = mock_response

        # Execute
        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Verify
        assert len(items) >= 2  # May have more from empty query
        assert any(item['name'] == 'Fireball' for item in items)

    @patch('foundry.items.fetch.os.getenv')
    def test_missing_credentials(self, mock_getenv):
        """Should raise ValueError if credentials missing."""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="Missing required credentials"):
            fetch_items_by_type('spell')

    @patch('foundry.items.fetch.requests.get')
    @patch('foundry.items.fetch.os.getenv')
    def test_deduplication(self, mock_getenv, mock_get):
        """Should deduplicate items by UUID."""
        mock_getenv.side_effect = lambda key: {
            'FOUNDRY_RELAY_URL': 'http://localhost:3010',
            'FOUNDRY_LOCAL_API_KEY': 'test-key',
            'FOUNDRY_LOCAL_CLIENT_ID': 'test-client'
        }.get(key)

        # Setup mock to return same item multiple times
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},  # Duplicate UUID
            ]
        }
        mock_get.return_value = mock_response

        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Should only have one item despite duplicate in results
        uuids = [item['uuid'] for item in items if item['uuid'] == 'Compendium.dnd5e.spells.1']
        assert len(uuids) == 1

    @patch('foundry.items.fetch.requests.get')
    @patch('foundry.items.fetch.os.getenv')
    def test_two_letter_fallback_triggered(self, mock_getenv, mock_get):
        """Should use two-letter combos when hitting 200 limit."""
        mock_getenv.side_effect = lambda key: {
            'FOUNDRY_RELAY_URL': 'http://localhost:3010',
            'FOUNDRY_LOCAL_API_KEY': 'test-key',
            'FOUNDRY_LOCAL_CLIENT_ID': 'test-client'
        }.get(key)

        # Setup mock: 'a' returns exactly 200 items, triggering fallback
        def mock_response_side_effect(*args, **kwargs):
            query = kwargs.get('params', {}).get('query', '')
            response = MagicMock()

            if query == 'a':
                # Return exactly 200 items to trigger fallback
                response.json.return_value = {
                    'results': [{'uuid': f'Compendium.dnd5e.spells.{i}', 'name': f'Spell {i}'}
                               for i in range(200)]
                }
            elif query in ['aa', 'ab', 'ac']:
                # Two-letter queries return fewer items
                response.json.return_value = {'results': [
                    {'uuid': f'Compendium.dnd5e.spells.{query}1', 'name': f'{query.upper()} Spell'}
                ]}
            else:
                response.json.return_value = {'results': []}

            return response

        mock_get.side_effect = mock_response_side_effect

        items = fetch_items_by_type('spell', use_two_letter_fallback=True)

        # Should have items from both single-letter and two-letter queries
        assert len(items) > 200

    @patch('foundry.items.fetch.requests.get')
    @patch('foundry.items.fetch.os.getenv')
    def test_custom_credentials(self, mock_getenv, mock_get):
        """Should use provided credentials over environment variables."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response

        fetch_items_by_type(
            'spell',
            relay_url='http://custom:3010',
            api_key='custom-key',
            client_id='custom-client',
            use_two_letter_fallback=False
        )

        # Verify custom credentials were used
        call_args = mock_get.call_args
        assert call_args[1]['headers']['x-api-key'] == 'custom-key'
        assert call_args[1]['params']['clientId'] == 'custom-client'

    @patch('foundry.items.fetch.requests.get')
    @patch('foundry.items.fetch.os.getenv')
    def test_api_error_handling(self, mock_getenv, mock_get):
        """Should raise RuntimeError on API failure."""
        import requests

        mock_getenv.side_effect = lambda key: {
            'FOUNDRY_RELAY_URL': 'http://localhost:3010',
            'FOUNDRY_LOCAL_API_KEY': 'test-key',
            'FOUNDRY_LOCAL_CLIENT_ID': 'test-client'
        }.get(key)

        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        with pytest.raises(RuntimeError, match="Failed to search"):
            fetch_items_by_type('spell', use_two_letter_fallback=False)


class TestFetchAllSpells:
    """Tests for fetch_all_spells convenience function."""

    @patch('foundry.items.fetch.fetch_items_by_type')
    def test_calls_fetch_items_by_type(self, mock_fetch):
        """Should call fetch_items_by_type with 'spell' subtype."""
        mock_fetch.return_value = []

        result = fetch_all_spells(relay_url='http://test', api_key='key', client_id='id')

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] == 'spell'
        assert call_args[1]['relay_url'] == 'http://test'


@pytest.mark.integration
class TestFetchItemsIntegration:
    """Integration tests that make real API calls."""

    def test_fetch_real_spells(self, check_api_key):
        """Fetch real spells from FoundryVTT (requires running server)."""
        import os

        # Skip if relay not configured
        if not os.getenv('FOUNDRY_RELAY_URL'):
            pytest.skip("FOUNDRY_RELAY_URL not configured")

        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Should return some spells
        assert len(items) > 0

        # Verify structure
        for item in items[:5]:
            assert 'uuid' in item
            assert 'name' in item
            assert 'Compendium.' in item['uuid']

    def test_fetch_real_weapons(self, check_api_key):
        """Fetch real weapons from FoundryVTT (requires running server)."""
        import os

        if not os.getenv('FOUNDRY_RELAY_URL'):
            pytest.skip("FOUNDRY_RELAY_URL not configured")

        items = fetch_items_by_type('weapon', use_two_letter_fallback=False)

        assert len(items) > 0

        # Verify these are weapons
        for item in items[:5]:
            assert 'uuid' in item
            assert 'name' in item
