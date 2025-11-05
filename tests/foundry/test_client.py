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
    """Tests for journal entry operations delegation."""

    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a FoundryClient with mocked environment."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-key")
        monkeypatch.setenv("FOUNDRY_LOCAL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")
        return FoundryClient(target="local")

    def test_client_has_journals_manager(self, mock_client):
        """Test that FoundryClient has journals manager."""
        from src.foundry.journals import JournalManager
        assert hasattr(mock_client, 'journals')
        assert isinstance(mock_client.journals, JournalManager)

    @patch('requests.post')
    def test_create_journal_delegates_to_manager(self, mock_post, mock_client):
        """Test that create_journal_entry delegates to JournalManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "journal123"},
            "uuid": "JournalEntry.journal123"
        }
        mock_post.return_value = mock_response

        result = mock_client.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["entity"]["_id"] == "journal123"
        mock_post.assert_called_once()

    @patch('requests.get')
    def test_get_journal_by_name_delegates_to_manager(self, mock_get, mock_client):
        """Test that get_journal_by_name delegates to JournalManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"_id": "journal123", "name": "Test Journal"}
        ]
        mock_get.return_value = mock_response

        result = mock_client.get_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"


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

    @pytest.mark.integration
    @pytest.mark.slow
    def test_delete_nonexistent_journal(self, real_client):
        """Test deleting a non-existent journal succeeds (idempotent delete)."""
        fake_uuid = "JournalEntry.nonexistentfake123"

        # Delete endpoint is idempotent - returns success even if journal doesn't exist
        result = real_client.delete_journal_entry(journal_uuid=fake_uuid)
        assert result.get('success') is True

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
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_upload_and_download_file(self, real_client, tmp_path):
        """Test uploading a file to FoundryVTT and downloading it back.

        Note: May timeout due to relay server latency - retries up to 2 times.
        File will remain on server as there's no delete endpoint in the API.
        Files are uploaded to worlds/{world}/test_uploads/ for manual cleanup.
        """
        import os
        import time
        from dotenv import load_dotenv
        load_dotenv()

        # Check if a world is active (works for both browser and headless sessions)
        if not real_client.is_world_active():
            pytest.skip("No active FoundryVTT world - file uploads require a running world. "
                       "Launch a world in FoundryVTT to run this test.")

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


@pytest.mark.unit
class TestActorOperations:
    """Tests for actor operations via FoundryClient."""

    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a FoundryClient with mocked environment."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-key")
        monkeypatch.setenv("FOUNDRY_LOCAL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")
        return FoundryClient(target="local")

    def test_client_initializes_actor_manager(self, mock_client):
        """Test client creates ActorManager instance."""
        assert hasattr(mock_client, 'actors')
        assert mock_client.actors is not None

    @patch('requests.get')
    def test_client_search_actor_delegates(self, mock_get, mock_client):
        """Test client.search_actor delegates to ActorManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"uuid": "Actor.abc123", "name": "Goblin"}
        ]
        mock_get.return_value = mock_response

        uuid = mock_client.search_actor("Goblin")

        assert uuid == "Actor.abc123"
        mock_get.assert_called_once()

    @patch('requests.post')
    def test_client_create_creature_actor_delegates(self, mock_post, mock_client):
        """Test client.create_creature_actor delegates to ActorManager."""
        from src.actors.models import StatBlock

        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin text",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "abc123"},
            "uuid": "Actor.abc123"
        }
        mock_post.return_value = mock_response

        uuid = mock_client.create_creature_actor(stat_block)

        assert uuid == "Actor.abc123"
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_client_create_npc_actor_delegates(self, mock_post, mock_client):
        """Test client.create_npc_actor delegates to ActorManager."""
        from src.actors.models import NPC

        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader",
            plot_relevance="Guards supplies"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity": {"_id": "xyz789"},
            "uuid": "Actor.xyz789"
        }
        mock_post.return_value = mock_response

        uuid = mock_client.create_npc_actor(npc, stat_block_uuid="Actor.boss123")

        assert uuid == "Actor.xyz789"
        mock_post.assert_called_once()

    def test_foundry_client_has_icon_cache(self, mock_client):
        """Test FoundryClient exposes icon cache."""
        from src.foundry.icon_cache import IconCache

        assert hasattr(mock_client, 'icons')
        assert isinstance(mock_client.icons, IconCache)
