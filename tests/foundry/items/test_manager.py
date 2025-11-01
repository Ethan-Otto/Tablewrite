"""Tests for foundry.items.manager module (ItemManager)."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.items.manager import ItemManager


class TestItemManager:
    """Tests for ItemManager class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ItemManager(
            relay_url="http://localhost:3010",
            foundry_url="http://localhost:30000",
            api_key="test-api-key",
            client_id="test-client-id"
        )

    @patch('foundry.items.manager.requests.get')
    def test_get_all_items_by_name(self, mock_get):
        """Should search for items by name."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {'uuid': 'Compendium.dnd5e.items.1', 'name': 'Longsword'},
                {'uuid': 'Compendium.dnd5e.items.2', 'name': 'Longsword +1'},
            ]
        }
        mock_get.return_value = mock_response

        results = self.manager.get_all_items_by_name("Longsword")

        assert len(results) == 2
        assert results[0]['name'] == 'Longsword'
        mock_get.assert_called_once()

    @patch('foundry.items.manager.requests.get')
    def test_get_item_by_name(self, mock_get):
        """Should return first item matching name."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {'uuid': 'Compendium.dnd5e.items.1', 'name': 'Longsword'},
            ]
        }
        mock_get.return_value = mock_response

        result = self.manager.get_item_by_name("Longsword")

        assert result is not None
        assert result['name'] == 'Longsword'

    @patch('foundry.items.manager.requests.get')
    def test_get_item_by_name_not_found(self, mock_get):
        """Should return None if item not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response

        result = self.manager.get_item_by_name("NonexistentItem")

        assert result is None

    @patch('foundry.items.manager.requests.get')
    def test_get_item_by_uuid(self, mock_get):
        """Should fetch item by UUID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'uuid': 'Compendium.dnd5e.items.123',
            'name': 'Longsword',
            'type': 'weapon'
        }
        mock_get.return_value = mock_response

        result = self.manager.get_item("Compendium.dnd5e.items.123")

        assert result['uuid'] == 'Compendium.dnd5e.items.123'
        assert result['name'] == 'Longsword'

    @patch('foundry.items.manager.requests.get')
    def test_search_with_filter(self, mock_get):
        """Should use filter parameter in search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response

        self.manager.get_all_items_by_name("Test")

        # Verify filter was set to "Item"
        call_args = mock_get.call_args
        assert call_args[1]['params']['filter'] == 'Item'

    @patch('foundry.items.manager.requests.get')
    def test_search_error_handling(self, mock_get):
        """Should raise RuntimeError on API error."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(RuntimeError, match="Failed to search for item"):
            self.manager.get_all_items_by_name("Test")

    @patch('foundry.items.manager.requests.get')
    def test_get_item_error_handling(self, mock_get):
        """Should raise RuntimeError on get error."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(RuntimeError, match="Failed to get item"):
            self.manager.get_item("Compendium.dnd5e.items.123")

    @patch('foundry.items.manager.requests.get')
    def test_handles_list_response(self, mock_get):
        """Should handle response that is a list instead of dict with 'results'."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'uuid': 'Compendium.dnd5e.items.1', 'name': 'Longsword'},
        ]
        mock_get.return_value = mock_response

        results = self.manager.get_all_items_by_name("Longsword")

        assert len(results) == 1
        assert results[0]['name'] == 'Longsword'
