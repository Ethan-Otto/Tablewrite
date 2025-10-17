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
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="local")

        assert client.foundry_url == "http://localhost:30000"
        assert client.api_key == "test-api-key"
        assert client.relay_url == "https://relay.example.com"

    def test_client_initialization_forge(self, monkeypatch):
        """Test client initializes with forge environment."""
        monkeypatch.setenv("FOUNDRY_FORGE_URL", "https://game.forge-vtt.com")
        monkeypatch.setenv("FOUNDRY_FORGE_API_KEY", "forge-api-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="forge")

        assert client.foundry_url == "https://game.forge-vtt.com"
        assert client.api_key == "forge-api-key"

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
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")
        return FoundryClient(target="local")

    @patch('requests.put')
    def test_update_journal_entry_success(self, mock_put, mock_client):
        """Test updating an existing journal entry."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "_id": "journal123",
            "name": "Updated Journal",
            "content": "<p>Updated content</p>"
        }
        mock_put.return_value = mock_response

        result = mock_client.update_journal_entry(
            journal_id="journal123",
            content="<p>Updated content</p>"
        )

        assert result["_id"] == "journal123"
        mock_put.assert_called_once()

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
