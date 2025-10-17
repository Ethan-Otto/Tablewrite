"""Tests for FoundryVTT API client."""

import pytest
import os
from unittest.mock import Mock, patch
from src.foundry.client import FoundryClient


class TestFoundryClientInit:
    """Tests for FoundryClient initialization."""

    def test_client_initialization_with_env_vars(self, monkeypatch):
        """Test client initializes with environment variables."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-api-key")
        monkeypatch.setenv("FOUNDRY_LOCAL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="local")

        assert client.foundry_url == "http://localhost:30000"
        assert client.api_key == "test-api-key"
        assert client.client_id == "test-client-id"
        assert client.relay_url == "https://relay.example.com"

    def test_client_initialization_forge(self, monkeypatch):
        """Test client initializes with forge environment."""
        monkeypatch.setenv("FOUNDRY_FORGE_URL", "https://game.forge-vtt.com")
        monkeypatch.setenv("FOUNDRY_FORGE_API_KEY", "forge-api-key")
        monkeypatch.setenv("FOUNDRY_FORGE_CLIENT_ID", "forge-client-id")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="forge")

        assert client.foundry_url == "https://game.forge-vtt.com"
        assert client.api_key == "forge-api-key"
        assert client.client_id == "forge-client-id"

    def test_client_raises_on_missing_env_vars(self, monkeypatch):
        """Test client raises ValueError when required env vars missing."""
        # Clear all relevant env vars
        monkeypatch.delenv("FOUNDRY_LOCAL_URL", raising=False)
        monkeypatch.delenv("FOUNDRY_LOCAL_API_KEY", raising=False)
        monkeypatch.delenv("FOUNDRY_RELAY_URL", raising=False)

        with pytest.raises(ValueError, match="FOUNDRY_RELAY_URL not set"):
            FoundryClient(target="local")


class TestJournalOperations:
    """Tests for journal entry operations."""

    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a FoundryClient with mocked environment."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-key")
        monkeypatch.setenv("FOUNDRY_LOCAL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")
        return FoundryClient(target="local")

    @patch('requests.put')
    def test_update_journal_entry_success(self, mock_put, mock_client):
        """Test updating an existing journal entry with UUID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_id": "journal123",
            "name": "Updated Journal",
            "content": "<p>Updated content</p>"
        }
        mock_put.return_value = mock_response

        result = mock_client.update_journal_entry(
            journal_uuid="JournalEntry.journal123",
            content="<p>Updated content</p>"
        )

        assert result["_id"] == "journal123"
        mock_put.assert_called_once()

        # Verify UUID is in query parameter (URL is first positional arg)
        call_args = mock_put.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.journal123" in url

    @patch('requests.get')
    def test_find_journal_by_name(self, mock_get, mock_client):
        """Test finding a journal entry by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"_id": "journal123", "name": "Test Journal"},
            {"_id": "journal456", "name": "Other Journal"}
        ]
        mock_get.return_value = mock_response

        result = mock_client.find_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"
        assert result["name"] == "Test Journal"

    @patch('requests.get')
    def test_find_journal_by_name_not_found(self, mock_get, mock_client):
        """Test finding returns None when journal doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = mock_client.find_journal_by_name("Nonexistent")

        assert result is None

    @patch('requests.post')
    def test_create_journal_entry_success(self, mock_post, mock_client):
        """Test creating a journal entry via REST API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_id": "journal123",
            "name": "Test Journal",
            "content": "<p>Test content</p>"
        }
        mock_post.return_value = mock_response

        result = mock_client.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["_id"] == "journal123"
        assert result["name"] == "Test Journal"
        mock_post.assert_called_once()

        # Verify API key header
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["x-api-key"] == "test-key"

    @patch('requests.post')
    def test_create_journal_entry_failure(self, mock_post, mock_client):
        """Test journal creation handles API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to create journal"):
            mock_client.create_journal_entry(
                name="Test Journal",
                content="<p>Test content</p>"
            )

    @patch('requests.delete')
    def test_delete_journal_entry_success(self, mock_delete, mock_client):
        """Test deleting a journal entry."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_response

        result = mock_client.delete_journal_entry(
            journal_uuid="JournalEntry.journal123"
        )

        assert result["success"] is True
        mock_delete.assert_called_once()

        # Verify UUID is in query parameter (URL is first positional arg)
        call_args = mock_delete.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.journal123" in url

    @patch('requests.delete')
    def test_delete_journal_entry_failure(self, mock_delete, mock_client):
        """Test journal deletion handles API errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Journal not found"
        mock_delete.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to delete journal"):
            mock_client.delete_journal_entry(
                journal_uuid="JournalEntry.nonexistent"
            )

    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_update_creates_when_not_found(self, mock_get, mock_post, mock_client):
        """Test create_or_update creates new journal when not found."""
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

        result = mock_client.create_or_update_journal(
            name="New Journal",
            content="<p>New content</p>"
        )

        assert result["entity"]["_id"] == "new123"
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.put')
    @patch('requests.get')
    def test_create_or_update_updates_when_found(self, mock_get, mock_put, mock_client):
        """Test create_or_update updates existing journal when found."""
        # Search returns existing journal with UUID
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

        # Update succeeds
        mock_update_response = Mock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {
            "_id": "existing123",
            "name": "Existing Journal"
        }
        mock_put.return_value = mock_update_response

        result = mock_client.create_or_update_journal(
            name="Existing Journal",
            content="<p>Updated content</p>"
        )

        assert result["_id"] == "existing123"
        mock_get.assert_called_once()
        mock_put.assert_called_once()

    @patch('requests.put')
    @patch('requests.get')
    def test_create_or_update_constructs_uuid_from_id(self, mock_get, mock_put, mock_client):
        """Test create_or_update constructs UUID when not provided."""
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

        # Update succeeds
        mock_update_response = Mock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {"_id": "test456"}
        mock_put.return_value = mock_update_response

        result = mock_client.create_or_update_journal(
            name="Test Journal",
            content="<p>Content</p>"
        )

        assert result["_id"] == "test456"
        mock_put.assert_called_once()

        # Verify constructed UUID is used (URL is first positional arg)
        call_args = mock_put.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.test456" in url
