"""Tests for foundry.items.fetch module (via WebSocket backend)."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.items.fetch import fetch_items_by_type, fetch_all_spells


class TestFetchItemsByType:
    """Tests for fetch_items_by_type function."""

    @patch('foundry.items.fetch.requests.get')
    def test_basic_fetch(self, mock_get):
        """Should fetch items successfully."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'results': [
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},
                {'uuid': 'Compendium.dnd5e.spells.2', 'name': 'Lightning Bolt'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Execute
        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Verify
        assert len(items) >= 2  # May have more from empty query
        assert any(item['name'] == 'Fireball' for item in items)

    @patch('foundry.items.fetch.requests.get')
    def test_deduplication(self, mock_get):
        """Should deduplicate items by UUID."""
        # Setup mock to return same item multiple times
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'results': [
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},
                {'uuid': 'Compendium.dnd5e.spells.1', 'name': 'Fireball'},  # Duplicate UUID
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Should only have one item despite duplicate in results
        uuids = [item['uuid'] for item in items if item['uuid'] == 'Compendium.dnd5e.spells.1']
        assert len(uuids) == 1

    @patch('foundry.items.fetch.requests.get')
    def test_two_letter_fallback_triggered(self, mock_get):
        """Should use two-letter combos when hitting 200 limit."""
        # Setup mock: 'a' returns exactly 200 items, triggering fallback
        def mock_response_side_effect(*args, **kwargs):
            query = kwargs.get('params', {}).get('query', '')
            response = MagicMock()
            response.raise_for_status = MagicMock()

            if query == 'a':
                # Return exactly 200 items to trigger fallback
                response.json.return_value = {
                    'success': True,
                    'results': [{'uuid': f'Compendium.dnd5e.spells.{i}', 'name': f'Spell {i}'}
                               for i in range(200)]
                }
            elif query in ['aa', 'ab', 'ac']:
                # Two-letter queries return fewer items
                response.json.return_value = {
                    'success': True,
                    'results': [
                        {'uuid': f'Compendium.dnd5e.spells.{query}1', 'name': f'{query.upper()} Spell'}
                    ]
                }
            else:
                response.json.return_value = {'success': True, 'results': []}

            return response

        mock_get.side_effect = mock_response_side_effect

        items = fetch_items_by_type('spell', use_two_letter_fallback=True)

        # Should have items from both single-letter and two-letter queries
        assert len(items) > 200

    @patch('foundry.items.fetch.requests.get')
    def test_custom_backend_url(self, mock_get):
        """Should use provided backend URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True, 'results': []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetch_items_by_type(
            'spell',
            backend_url='http://custom:9000',
            use_two_letter_fallback=False
        )

        # Verify custom URL was used
        call_args = mock_get.call_args
        assert 'http://custom:9000' in call_args[0][0]

    @patch('foundry.items.fetch.requests.get')
    def test_api_error_handling(self, mock_get):
        """Should raise RuntimeError on API failure."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        with pytest.raises(RuntimeError, match="Failed to search"):
            fetch_items_by_type('spell', use_two_letter_fallback=False)

    @patch('foundry.items.fetch.requests.get')
    def test_handles_failed_success_response(self, mock_get):
        """Should return empty results when success is False."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': False, 'error': 'Search failed'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Should return empty list (all queries returned no results)
        assert len(items) == 0


class TestFetchAllSpells:
    """Tests for fetch_all_spells convenience function."""

    @patch('foundry.items.fetch.fetch_items_by_type')
    def test_calls_fetch_items_by_type(self, mock_fetch):
        """Should call fetch_items_by_type with 'spell' subtype."""
        mock_fetch.return_value = []

        result = fetch_all_spells(backend_url='http://test:8000')

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] == 'spell'
        assert call_args[1]['backend_url'] == 'http://test:8000'


@pytest.mark.integration
class TestFetchItemsIntegration:
    """Integration tests that make real API calls."""

    @pytest.fixture
    def require_backend(self):
        """Ensure backend is running."""
        import httpx

        try:
            response = httpx.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code != 200:
                pytest.fail("Backend not healthy")
        except httpx.ConnectError:
            pytest.fail("Backend not running on localhost:8000")

        # Check Foundry connection
        try:
            response = httpx.get("http://localhost:8000/api/foundry/status", timeout=5.0)
            if response.json().get("status") != "connected":
                pytest.fail("Foundry not connected to backend via WebSocket")
        except Exception as e:
            pytest.fail(f"Failed to check Foundry status: {e}")

        return True

    def test_fetch_real_spells(self, require_backend):
        """Fetch real spells from FoundryVTT (requires running backend + Foundry)."""
        items = fetch_items_by_type('spell', use_two_letter_fallback=False)

        # Should return some spells
        assert len(items) > 0

        # Verify structure
        for item in items[:5]:
            assert 'uuid' in item
            assert 'name' in item
            assert 'Compendium.' in item['uuid']

    def test_fetch_real_weapons(self, require_backend):
        """Fetch real weapons from FoundryVTT (requires running backend + Foundry)."""
        items = fetch_items_by_type('weapon', use_two_letter_fallback=False)

        assert len(items) > 0

        # Verify these are weapons
        for item in items[:5]:
            assert 'uuid' in item
            assert 'name' in item
