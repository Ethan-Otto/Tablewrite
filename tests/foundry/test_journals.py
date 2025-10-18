"""Tests for JournalManager class."""

import pytest
from unittest.mock import Mock, patch
from src.foundry.journals import JournalManager


class TestJournalManagerInit:
    """Tests for JournalManager initialization."""

    def test_journal_manager_initialization(self):
        """Test JournalManager initializes with correct attributes."""
        manager = JournalManager(
            relay_url="https://relay.example.com",
            foundry_url="http://localhost:30000",
            api_key="test-api-key",
            client_id="test-client-id"
        )

        assert manager.relay_url == "https://relay.example.com"
        assert manager.foundry_url == "http://localhost:30000"
        assert manager.api_key == "test-api-key"
        assert manager.client_id == "test-client-id"


class TestJournalManagerOperations:
    """Tests for journal operations via JournalManager."""

    @pytest.fixture
    def manager(self):
        """Create a JournalManager instance for testing."""
        return JournalManager(
            relay_url="https://relay.example.com",
            foundry_url="http://localhost:30000",
            api_key="test-key",
            client_id="test-client-id"
        )

    @patch('requests.post')
    def test_create_journal_entry_with_pages(self, mock_post, manager):
        """Test creating a journal entry with multiple pages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "journal123"},
            "uuid": "JournalEntry.journal123"
        }
        mock_post.return_value = mock_response

        pages = [
            {"name": "Chapter 1", "content": "<h1>Chapter 1</h1>"},
            {"name": "Chapter 2", "content": "<h1>Chapter 2</h1>"}
        ]

        result = manager.create_journal_entry(
            name="Test Module",
            pages=pages
        )

        assert result["entity"]["_id"] == "journal123"
        mock_post.assert_called_once()

        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["entityType"] == "JournalEntry"
        assert payload["data"]["name"] == "Test Module"
        assert len(payload["data"]["pages"]) == 2
        assert payload["data"]["pages"][0]["name"] == "Chapter 1"
        assert payload["data"]["pages"][0]["type"] == "text"
        assert payload["data"]["pages"][0]["text"]["content"] == "<h1>Chapter 1</h1>"

    @patch('requests.post')
    def test_create_journal_entry_with_content(self, mock_post, manager):
        """Test creating a journal entry with legacy content parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "journal123"},
            "uuid": "JournalEntry.journal123"
        }
        mock_post.return_value = mock_response

        result = manager.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["entity"]["_id"] == "journal123"

        # Verify it creates a single-page journal
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 1
        assert payload["data"]["pages"][0]["name"] == "Test Journal"
        assert payload["data"]["pages"][0]["text"]["content"] == "<p>Test content</p>"

    @patch('requests.post')
    def test_create_journal_entry_with_folder(self, mock_post, manager):
        """Test creating a journal entry with folder parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entity": {"_id": "journal123"}}
        mock_post.return_value = mock_response

        result = manager.create_journal_entry(
            name="Test Journal",
            content="<p>Content</p>",
            folder="folder123"
        )

        # Verify folder is in payload
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["data"]["folder"] == "folder123"

    def test_create_journal_entry_requires_content_or_pages(self, manager):
        """Test that create_journal_entry requires either pages or content."""
        with pytest.raises(ValueError, match="Must provide either 'pages' or 'content'"):
            manager.create_journal_entry(name="Test Journal")

    @patch('requests.post')
    def test_create_journal_entry_handles_api_error(self, mock_post, manager):
        """Test that create_journal_entry raises on API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to create journal entry"):
            manager.create_journal_entry(
                name="Test Journal",
                content="<p>Content</p>"
            )

    @patch('requests.get')
    def test_find_journal_by_name_success(self, mock_get, manager):
        """Test finding a journal entry by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "journal123", "name": "Test Journal"},
            {"id": "journal456", "name": "Other Journal"}
        ]
        mock_get.return_value = mock_response

        result = manager.find_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"  # id normalized to _id
        assert result["name"] == "Test Journal"

    @patch('requests.get')
    def test_find_journal_by_name_not_found(self, mock_get, manager):
        """Test that find_journal_by_name returns None when not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = manager.find_journal_by_name("Nonexistent")

        assert result is None

    @patch('requests.get')
    def test_find_journal_by_name_handles_dict_response(self, mock_get, manager):
        """Test that find_journal_by_name handles dict response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "journal123", "name": "Test Journal"}
            ]
        }
        mock_get.return_value = mock_response

        result = manager.find_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"

    @patch('requests.get')
    def test_find_journal_by_name_handles_search_error(self, mock_get, manager):
        """Test that find_journal_by_name returns None on search error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "QuickInsert module not available"}
        mock_get.return_value = mock_response

        result = manager.find_journal_by_name("Test")

        assert result is None

    @patch('requests.get')
    def test_get_journal_entry_success(self, mock_get, manager):
        """Test getting a journal entry by UUID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "name": "Test Journal",
                "pages": [{"name": "Page 1", "text": {"content": "<p>Content</p>"}}]
            }
        }
        mock_get.return_value = mock_response

        result = manager.get_journal_entry("JournalEntry.journal123")

        assert result["data"]["name"] == "Test Journal"
        assert len(result["data"]["pages"]) == 1

        # Verify URL construction
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.journal123" in url

    @patch('requests.get')
    def test_get_journal_entry_handles_error(self, mock_get, manager):
        """Test that get_journal_entry raises on API error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Journal not found"
        mock_get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to get journal"):
            manager.get_journal_entry("JournalEntry.nonexistent")

    @patch('requests.put')
    def test_update_journal_entry_with_pages(self, mock_put, manager):
        """Test updating a journal entry with multiple pages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"_id": "journal123"}
        mock_put.return_value = mock_response

        pages = [
            {"name": "Updated Page 1", "content": "<h1>Updated</h1>"},
            {"name": "Updated Page 2", "content": "<h2>Updated</h2>"}
        ]

        result = manager.update_journal_entry(
            journal_uuid="JournalEntry.journal123",
            pages=pages,
            name="Updated Journal"
        )

        assert result["_id"] == "journal123"

        # Verify payload
        call_kwargs = mock_put.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 2
        assert payload["data"]["name"] == "Updated Journal"

    @patch('requests.put')
    def test_update_journal_entry_with_content(self, mock_put, manager):
        """Test updating a journal entry with legacy content parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"_id": "journal123"}
        mock_put.return_value = mock_response

        result = manager.update_journal_entry(
            journal_uuid="JournalEntry.journal123",
            content="<p>Updated content</p>",
            name="Updated Name"
        )

        # Verify single-page update
        call_kwargs = mock_put.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 1
        assert payload["data"]["pages"][0]["name"] == "Updated Name"

    @patch('requests.delete')
    def test_delete_journal_entry_success(self, mock_delete, manager):
        """Test deleting a journal entry."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_response

        result = manager.delete_journal_entry("JournalEntry.journal123")

        assert result["success"] is True

        # Verify URL construction
        call_args = mock_delete.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.journal123" in url

    @patch('requests.delete')
    def test_delete_journal_entry_handles_error(self, mock_delete, manager):
        """Test that delete_journal_entry raises on API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_delete.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to delete journal"):
            manager.delete_journal_entry("JournalEntry.journal123")

    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_replace_creates_when_not_found(self, mock_get, mock_post, manager):
        """Test create_or_replace creates new journal when not found."""
        # Search returns no results
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = []
        mock_get.return_value = mock_search_response

        # Create succeeds
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "entity": {"_id": "new123"},
            "uuid": "JournalEntry.new123"
        }
        mock_post.return_value = mock_create_response

        result = manager.create_or_replace_journal(
            name="New Journal",
            content="<p>Content</p>"
        )

        assert result["entity"]["_id"] == "new123"
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.delete')
    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_replace_deletes_and_creates_when_found(self, mock_get, mock_post, mock_delete, manager):
        """Test create_or_replace deletes existing journal and creates new one."""
        # Search returns existing journal
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [
            {
                "name": "Existing Journal",
                "id": "existing123",
                "uuid": "JournalEntry.existing123"
            }
        ]
        mock_get.return_value = mock_search_response

        # Delete succeeds
        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_delete_response

        # Create succeeds
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "entity": {"_id": "new123"},
            "uuid": "JournalEntry.new123"
        }
        mock_post.return_value = mock_create_response

        result = manager.create_or_replace_journal(
            name="Existing Journal",
            content="<p>Updated content</p>"
        )

        assert result["entity"]["_id"] == "new123"
        mock_get.assert_called_once()
        mock_delete.assert_called_once()
        mock_post.assert_called_once()

        # Verify delete was called with correct UUID
        delete_call_args = mock_delete.call_args
        delete_url = delete_call_args[0][0]
        assert "uuid=JournalEntry.existing123" in delete_url

    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_replace_constructs_uuid_from_id(self, mock_get, mock_post, manager):
        """Test create_or_replace constructs UUID when not provided in search results."""
        # Search returns journal with id but no uuid
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [
            {
                "name": "Test Journal",
                "id": "test456",
                "_id": "test456"
            }
        ]
        mock_get.return_value = mock_search_response

        # Delete succeeds
        with patch('requests.delete') as mock_delete:
            mock_delete_response = Mock()
            mock_delete_response.status_code = 200
            mock_delete_response.json.return_value = {"success": True}
            mock_delete.return_value = mock_delete_response

            # Create succeeds
            mock_create_response = Mock()
            mock_create_response.status_code = 200
            mock_create_response.json.return_value = {
                "entity": {"_id": "new123"}
            }
            mock_post.return_value = mock_create_response

            manager.create_or_replace_journal(
                name="Test Journal",
                content="<p>Content</p>"
            )

            # Verify constructed UUID is used
            delete_call_args = mock_delete.call_args
            delete_url = delete_call_args[0][0]
            assert "uuid=JournalEntry.test456" in delete_url

    def test_create_or_replace_requires_content_or_pages(self, manager):
        """Test that create_or_replace requires either pages or content."""
        with pytest.raises(ValueError, match="Must provide either 'pages' or 'content'"):
            manager.create_or_replace_journal(name="Test Journal")
