"""Tests for JournalManager class (via WebSocket backend)."""

import pytest
from unittest.mock import Mock, patch
from foundry.journals import JournalManager


class TestJournalManagerInit:
    """Tests for JournalManager initialization."""

    def test_journal_manager_initialization(self):
        """Test JournalManager initializes with backend URL."""
        manager = JournalManager(backend_url="http://localhost:8000")

        assert manager.backend_url == "http://localhost:8000"


class TestJournalManagerOperations:
    """Tests for journal operations via JournalManager."""

    @pytest.fixture
    def manager(self):
        """Create a JournalManager instance for testing."""
        return JournalManager(backend_url="http://localhost:8000")

    @patch('requests.post')
    def test_create_journal_entry_with_pages(self, mock_post, manager):
        """Test creating a journal entry with multiple pages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "JournalEntry.journal123",
            "id": "journal123",
            "name": "Test Module"
        }
        mock_post.return_value = mock_response

        pages = [
            {"name": "Chapter 1", "type": "text", "text": {"content": "<h1>Chapter 1</h1>"}},
            {"name": "Chapter 2", "type": "text", "text": {"content": "<h1>Chapter 2</h1>"}}
        ]

        result = manager.create_journal_entry(
            name="Test Module",
            pages=pages
        )

        assert result["uuid"] == "JournalEntry.journal123"
        mock_post.assert_called_once()

        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["name"] == "Test Module"
        assert len(payload["pages"]) == 2
        assert payload["pages"][0]["name"] == "Chapter 1"

    @patch('requests.post')
    def test_create_journal_entry_with_content(self, mock_post, manager):
        """Test creating a journal entry with legacy content parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "JournalEntry.journal123",
            "id": "journal123",
            "name": "Test Journal"
        }
        mock_post.return_value = mock_response

        result = manager.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["uuid"] == "JournalEntry.journal123"

        # Verify it creates a single-page journal
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["pages"]) == 1
        assert payload["pages"][0]["name"] == "Test Journal"
        assert payload["pages"][0]["text"]["content"] == "<p>Test content</p>"

    @patch('requests.post')
    def test_create_journal_entry_with_folder(self, mock_post, manager):
        """Test creating a journal entry with folder parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "JournalEntry.journal123"
        }
        mock_post.return_value = mock_response

        result = manager.create_journal_entry(
            name="Test Journal",
            content="<p>Content</p>",
            folder="folder123"
        )

        # Verify folder is in payload
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["folder"] == "folder123"

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
    def test_get_journal_by_name_success(self, mock_get, manager):
        """Test finding a journal entry by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": [
                {"id": "journal123", "name": "Test Journal", "uuid": "JournalEntry.journal123"},
                {"id": "journal456", "name": "Other Journal", "uuid": "JournalEntry.journal456"}
            ]
        }
        mock_get.return_value = mock_response

        result = manager.get_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"  # id normalized to _id
        assert result["name"] == "Test Journal"

    @patch('requests.get')
    def test_get_journal_by_name_not_found(self, mock_get, manager):
        """Test that get_journal_by_name returns None when not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "results": []}
        mock_get.return_value = mock_response

        result = manager.get_journal_by_name("Nonexistent")

        assert result is None

    @patch('requests.get')
    def test_get_journal_by_name_handles_search_error(self, mock_get, manager):
        """Test that get_journal_by_name returns None on search error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False, "error": "Search failed"}
        mock_get.return_value = mock_response

        result = manager.get_journal_by_name("Test")

        assert result is None

    def test_get_journal_raises_not_implemented(self, manager):
        """Test that get_journal raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Get journal by UUID via WebSocket backend not yet implemented"):
            manager.get_journal("JournalEntry.journal123")

    def test_update_journal_entry_raises_not_implemented(self, manager):
        """Test that update_journal_entry raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Update journal via WebSocket backend not yet implemented"):
            manager.update_journal_entry(
                journal_uuid="JournalEntry.journal123",
                content="<p>Updated</p>"
            )

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
        assert "JournalEntry.journal123" in url

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
        mock_search_response.json.return_value = {"success": True, "results": []}
        mock_get.return_value = mock_search_response

        # Create succeeds
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "success": True,
            "uuid": "JournalEntry.new123",
            "id": "new123",
            "name": "New Journal"
        }
        mock_post.return_value = mock_create_response

        result = manager.create_or_replace_journal(
            name="New Journal",
            content="<p>Content</p>"
        )

        assert result["uuid"] == "JournalEntry.new123"
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
        mock_search_response.json.return_value = {
            "success": True,
            "results": [
                {
                    "name": "Existing Journal",
                    "id": "existing123",
                    "uuid": "JournalEntry.existing123"
                }
            ]
        }
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
            "success": True,
            "uuid": "JournalEntry.new123",
            "id": "new123"
        }
        mock_post.return_value = mock_create_response

        result = manager.create_or_replace_journal(
            name="Existing Journal",
            content="<p>Updated content</p>"
        )

        assert result["uuid"] == "JournalEntry.new123"
        mock_get.assert_called_once()
        mock_delete.assert_called_once()
        mock_post.assert_called_once()

    def test_create_or_replace_requires_content_or_pages(self, manager):
        """Test that create_or_replace requires either pages or content."""
        with pytest.raises(ValueError, match="Must provide either 'pages' or 'content'"):
            manager.create_or_replace_journal(name="Test Journal")
