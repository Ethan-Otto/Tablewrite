"""Tests for foundry.items.manager module (ItemManager via WebSocket backend)."""

import pytest
from unittest.mock import patch, MagicMock
from foundry.items.manager import ItemManager


class TestItemManager:
    """Tests for ItemManager class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ItemManager(backend_url="http://localhost:8000")

    @patch('foundry.items.manager.requests.get')
    def test_get_all_items_by_name(self, mock_get):
        """Should search for items by name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'results': [
                {'uuid': 'Compendium.dnd5e.items.1', 'name': 'Longsword'},
                {'uuid': 'Compendium.dnd5e.items.2', 'name': 'Longsword +1'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = self.manager.get_all_items_by_name("Longsword")

        assert len(results) == 2
        assert results[0]['name'] == 'Longsword'
        mock_get.assert_called_once()

    @patch('foundry.items.manager.requests.get')
    def test_get_item_by_name(self, mock_get):
        """Should return first item matching name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'results': [
                {'uuid': 'Compendium.dnd5e.items.1', 'name': 'Longsword'},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.manager.get_item_by_name("Longsword")

        assert result is not None
        assert result['name'] == 'Longsword'

    @patch('foundry.items.manager.requests.get')
    def test_get_item_by_name_not_found(self, mock_get):
        """Should return None if item not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'results': []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.manager.get_item_by_name("NonexistentItem")

        assert result is None

    def test_get_item_by_uuid_raises_not_implemented(self):
        """Should raise NotImplementedError for get_item by UUID."""
        with pytest.raises(NotImplementedError, match="Get item by UUID via WebSocket backend not yet implemented"):
            self.manager.get_item("Compendium.dnd5e.items.123")

    @patch('foundry.items.manager.requests.get')
    def test_search_uses_document_type_param(self, mock_get):
        """Should use document_type parameter in search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'results': []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        self.manager.get_all_items_by_name("Test")

        # Verify document_type was set to "Item"
        call_args = mock_get.call_args
        assert call_args[1]['params']['document_type'] == 'Item'

    @patch('foundry.items.manager.requests.get')
    def test_search_error_handling(self, mock_get):
        """Should raise RuntimeError on API error."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(RuntimeError, match="Failed to search for item"):
            self.manager.get_all_items_by_name("Test")

    @patch('foundry.items.manager.requests.get')
    def test_handles_failed_response(self, mock_get):
        """Should return empty list if success is False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': False, 'error': 'Search failed'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = self.manager.get_all_items_by_name("Longsword")

        assert len(results) == 0
