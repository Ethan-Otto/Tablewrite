"""Tests for FoundryVTT API client."""

import pytest
import os
from unittest.mock import Mock, patch
from dotenv import load_dotenv
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
    def test_get_journal_by_name(self, mock_get, mock_client):
        """Test finding a journal entry by name."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"_id": "journal123", "name": "Test Journal"},
            {"_id": "journal456", "name": "Other Journal"}
        ]
        mock_get.return_value = mock_response

        result = mock_client.get_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"
        assert result["name"] == "Test Journal"

    @patch('requests.get')
    def test_get_journal_by_name_not_found(self, mock_get, mock_client):
        """Test finding returns None when journal doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = mock_client.get_journal_by_name("Nonexistent")

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
    def test_create_or_replace_creates_when_not_found(self, mock_get, mock_post, mock_client):
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

        result = mock_client.create_or_replace_journal(
            name="New Journal",
            content="<p>New content</p>"
        )

        assert result["entity"]["_id"] == "new123"
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.delete')
    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_replace_replaces_when_found(self, mock_get, mock_post, mock_delete, mock_client):
        """Test create_or_replace deletes existing journal and creates new one."""
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

        # Delete succeeds
        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_delete_response

        # Create succeeds
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "entity": {"_id": "new456"},
            "uuid": "JournalEntry.new456"
        }
        mock_post.return_value = mock_create_response

        result = mock_client.create_or_replace_journal(
            name="Existing Journal",
            content="<p>Updated content</p>"
        )

        assert result["entity"]["_id"] == "new456"
        mock_get.assert_called_once()
        mock_delete.assert_called_once()
        mock_post.assert_called_once()

    @patch('requests.delete')
    @patch('requests.post')
    @patch('requests.get')
    def test_create_or_replace_constructs_uuid_from_id(self, mock_get, mock_post, mock_delete, mock_client):
        """Test create_or_replace constructs UUID when not provided."""
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
        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_delete_response

        # Create succeeds
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "entity": {"_id": "new789"},
            "uuid": "JournalEntry.new789"
        }
        mock_post.return_value = mock_create_response

        result = mock_client.create_or_replace_journal(
            name="Test Journal",
            content="<p>Content</p>"
        )

        assert result["entity"]["_id"] == "new789"
        mock_delete.assert_called_once()

        # Verify constructed UUID is used (URL is first positional arg)
        call_args = mock_delete.call_args
        url = call_args[0][0]
        assert "uuid=JournalEntry.test456" in url

    @patch('requests.post')
    def test_create_journal_entry_with_multiple_pages(self, mock_post, mock_client):
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
            {"name": "Chapter 2", "content": "<h1>Chapter 2</h1>"},
            {"name": "Chapter 3", "content": "<h1>Chapter 3</h1>"}
        ]

        result = mock_client.create_journal_entry(
            name="Test Module",
            pages=pages
        )

        assert result["entity"]["_id"] == "journal123"
        mock_post.assert_called_once()

        # Verify payload includes all pages
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 3
        assert payload["data"]["pages"][0]["name"] == "Chapter 1"
        assert payload["data"]["pages"][1]["name"] == "Chapter 2"
        assert payload["data"]["pages"][2]["name"] == "Chapter 3"

    @patch('requests.put')
    def test_update_journal_entry_with_multiple_pages(self, mock_put, mock_client):
        """Test updating a journal entry with multiple pages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"_id": "journal123"}
        mock_put.return_value = mock_response

        pages = [
            {"name": "Updated Chapter 1", "content": "<h1>Updated Chapter 1</h1>"},
            {"name": "Updated Chapter 2", "content": "<h1>Updated Chapter 2</h1>"}
        ]

        result = mock_client.update_journal_entry(
            journal_uuid="JournalEntry.journal123",
            pages=pages,
            name="Updated Module"
        )

        assert result["_id"] == "journal123"
        mock_put.assert_called_once()

        # Verify payload includes all pages
        call_kwargs = mock_put.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 2
        assert payload["data"]["name"] == "Updated Module"

    @patch('requests.post')
    def test_create_journal_entry_legacy_content_param(self, mock_post, mock_client):
        """Test backward compatibility with legacy content parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "journal123"},
            "uuid": "JournalEntry.journal123"
        }
        mock_post.return_value = mock_response

        # Old API: content parameter
        result = mock_client.create_journal_entry(
            name="Test Journal",
            content="<p>Legacy content</p>"
        )

        assert result["entity"]["_id"] == "journal123"
        mock_post.assert_called_once()

        # Verify it creates a single-page journal
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert len(payload["data"]["pages"]) == 1
        assert payload["data"]["pages"][0]["name"] == "Test Journal"
        assert payload["data"]["pages"][0]["text"]["content"] == "<p>Legacy content</p>"

    def test_create_journal_entry_raises_on_missing_content(self, mock_client):
        """Test creating journal without pages or content raises ValueError."""
        with pytest.raises(ValueError, match="Must provide either 'pages' or 'content'"):
            mock_client.create_journal_entry(name="Test Journal")


class TestFoundryIntegration:
    """Integration tests for FoundryVTT API (requires running server)."""

    @pytest.fixture
    def real_client(self):
        """Create a real FoundryClient with environment variables."""
        load_dotenv()

        # Check if required environment variables are set
        required_vars = [
            "FOUNDRY_RELAY_URL",
            "FOUNDRY_LOCAL_URL",
            "FOUNDRY_LOCAL_API_KEY",
            "FOUNDRY_LOCAL_CLIENT_ID"
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

        return FoundryClient(target="local")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_create_and_delete(self, real_client):
        """Test basic create and delete workflow (minimal API calls)."""
        journal_name = "Integration Test Create Delete"

        # 1. CREATE (1 API call)
        create_result = real_client.create_journal_entry(
            name=journal_name,
            content="<h1>Test Content</h1><p>This journal will be deleted immediately.</p>"
        )

        # Extract UUID from create response
        journal_uuid = create_result.get('uuid')
        if not journal_uuid:
            entity_id = create_result.get('entity', {}).get('_id')
            journal_uuid = f"JournalEntry.{entity_id}"

        assert journal_uuid.startswith('JournalEntry.'), f"Invalid UUID format: {journal_uuid}"

        # 2. DELETE (1 API call)
        delete_result = real_client.delete_journal_entry(journal_uuid=journal_uuid)
        assert delete_result.get('success') is True, "Delete operation did not return success"

    @pytest.mark.skip(reason="Disabled to conserve API calls - enable when needed")
    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_crud_workflow(self, real_client):
        """Test complete create → search → update → delete workflow with real server."""
        journal_name = "Integration Test CRUD Workflow"

        # 1. CREATE
        create_result = real_client.create_journal_entry(
            name=journal_name,
            content="<h1>Initial Content</h1><p>This is a test.</p>"
        )
        entity_id = create_result.get('entity', {}).get('_id') or create_result.get('uuid', 'unknown')
        assert entity_id != 'unknown', "Failed to extract entity ID from create response"

        # 2. SEARCH
        found = real_client.get_journal_by_name(journal_name)
        assert found is not None, "Failed to find newly created journal"
        assert found['name'] == journal_name

        # Extract UUID for update/delete
        journal_uuid = found.get('uuid') or f"JournalEntry.{found.get('_id') or found.get('id')}"
        assert journal_uuid.startswith('JournalEntry.'), f"Invalid UUID format: {journal_uuid}"

        # 3. UPDATE
        update_result = real_client.update_journal_entry(
            journal_uuid=journal_uuid,
            content="<h1>Updated Content</h1><p>Content has been updated!</p>",
            name=f"{journal_name} (Updated)"
        )
        assert update_result is not None, "Update operation failed"

        # 4. VERIFY UPDATE
        found_updated = real_client.get_journal_by_name(f"{journal_name} (Updated)")
        if not found_updated:
            # Name update might be delayed, try old name
            found_updated = real_client.get_journal_by_name(journal_name)
        assert found_updated is not None, "Failed to find journal after update"

        # 5. DELETE
        delete_result = real_client.delete_journal_entry(journal_uuid=journal_uuid)
        assert delete_result.get('success') is True, "Delete operation did not return success"

        # 6. VERIFY DELETION
        found_deleted = real_client.get_journal_by_name(journal_name)
        assert found_deleted is None, "Journal still exists after deletion"

    @pytest.mark.skip(reason="Disabled to conserve API calls - enable when needed")
    @pytest.mark.integration
    @pytest.mark.slow
    def test_create_or_replace_workflow(self, real_client):
        """Test create_or_replace creates on first call, deletes and creates on second call."""
        journal_name = "Integration Test Create or Replace"

        try:
            # First call should CREATE
            result1 = real_client.create_or_replace_journal(
                name=journal_name,
                content="<h1>First Version</h1><p>Initial content</p>"
            )

            # Extract ID from create response
            entity1 = result1.get('entity', {})
            if isinstance(entity1, list):
                id1 = entity1[0].get('_id') if entity1 else None
            else:
                id1 = entity1.get('_id')

            assert id1 is not None, "Failed to extract ID from first call"

            # Second call should DELETE old journal and CREATE new one (different ID)
            result2 = real_client.create_or_replace_journal(
                name=journal_name,
                content="<h1>Second Version</h1><p>Updated content!</p>"
            )

            # Extract ID from create response
            entity2 = result2.get('entity', {})
            if isinstance(entity2, list):
                id2 = entity2[0].get('_id') if entity2 else None
            else:
                id2 = entity2.get('_id')

            # Should be different journal (replaced, not updated)
            assert id2 != id1, f"Second call should create new journal with different ID: {id1} vs {id2}"

            # Verify only one journal exists with this name
            found = real_client.get_journal_by_name(journal_name)
            assert found is not None, "Journal not found after create_or_replace"

        finally:
            # Clean up - delete the test journal
            found = real_client.get_journal_by_name(journal_name)
            if found:
                journal_uuid = found.get('uuid') or f"JournalEntry.{found.get('_id') or found.get('id')}"
                real_client.delete_journal_entry(journal_uuid=journal_uuid)

    @pytest.mark.skip(reason="Disabled to conserve API calls - enable when needed")
    @pytest.mark.integration
    @pytest.mark.slow
    def test_delete_nonexistent_journal(self, real_client):
        """Test deleting a non-existent journal succeeds (idempotent delete)."""
        fake_uuid = "JournalEntry.nonexistentfake123"

        # Delete endpoint is idempotent - returns success even if journal doesn't exist
        result = real_client.delete_journal_entry(journal_uuid=fake_uuid)
        assert result.get('success') is True

    @pytest.mark.skip(reason="Disabled to conserve API calls - enable when needed")
    @pytest.mark.integration
    @pytest.mark.slow
    def test_update_nonexistent_journal(self, real_client):
        """Test updating a non-existent journal raises appropriate error."""
        fake_uuid = "JournalEntry.nonexistentfake456"

        with pytest.raises(RuntimeError, match="Failed to update journal"):
            real_client.update_journal_entry(
                journal_uuid=fake_uuid,
                content="<h1>Test</h1>"
            )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_upload_and_download_file(self, real_client, tmp_path):
        """Test uploading a file to FoundryVTT and downloading it back.

        Note: File will remain on server as there's no delete endpoint in the API.
        Files are uploaded to worlds/{world}/test_uploads/ for manual cleanup.
        """
        import os
        import time
        from dotenv import load_dotenv
        load_dotenv()

        # Create a test file with timestamp
        timestamp = time.time()
        test_content = f"Integration test file content\nTimestamp: {timestamp}\nTest run marker"

        upload_file = tmp_path / "test_upload.txt"
        upload_file.write_text(test_content)

        # Get world name from env
        world_name = os.getenv("FOUNDRY_WORLD_NAME", "testing-world")

        # Upload file to test directory
        target_path = f"worlds/{world_name}/test_uploads/integration_test.txt"

        # Upload the file
        upload_result = real_client.upload_file(
            local_path=str(upload_file),
            target_path=target_path,
            overwrite=True
        )

        # Verify upload succeeded
        assert upload_result is not None, "Upload did not return a result"

        # Download the file back
        download_file = tmp_path / "test_download.txt"
        real_client.download_file(
            target_path=target_path,
            local_path=str(download_file)
        )

        # Verify downloaded file exists and content matches
        assert download_file.exists(), "Downloaded file does not exist"
        downloaded_content = download_file.read_text()
        assert downloaded_content == test_content, "Downloaded content does not match uploaded content"
        assert str(timestamp) in downloaded_content, "Timestamp not found in downloaded content"

        # Note: No delete endpoint available in FoundryVTT relay API
        # File at worlds/{world}/test_uploads/integration_test.txt should be manually cleaned up
        # or will be overwritten on next test run
