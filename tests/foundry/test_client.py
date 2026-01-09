"""Tests for FoundryVTT API client (via WebSocket backend)."""

import os
import pytest
from unittest.mock import Mock, patch
from dotenv import load_dotenv
from foundry.client import FoundryClient


class TestFoundryClientInit:
    """Tests for FoundryClient initialization."""

    def test_client_initialization_with_env_vars(self, monkeypatch):
        """Test client initializes with environment variables."""
        monkeypatch.setenv("BACKEND_URL", "http://localhost:9000")

        client = FoundryClient()

        assert client.backend_url == "http://localhost:9000"

    def test_client_initialization_with_different_urls(self, monkeypatch):
        """Test client initializes with different URL configurations."""
        monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")

        client = FoundryClient()

        assert client.backend_url == "https://backend.example.com"

    def test_client_raises_on_missing_env_vars(self, monkeypatch):
        """Test client uses default backend URL when env var is missing."""
        monkeypatch.delenv("BACKEND_URL", raising=False)

        # Should NOT raise - uses default URL
        client = FoundryClient()
        assert client.backend_url == "http://localhost:8000"


class TestJournalOperations:
    """Tests for journal entry operations delegation."""

    @pytest.fixture
    def mock_client(self, monkeypatch):
        """Create a FoundryClient with mocked environment."""
        monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
        return FoundryClient()

    def test_client_has_journals_manager(self, mock_client):
        """Test that FoundryClient has journals manager."""
        from foundry.journals import JournalManager
        assert hasattr(mock_client, 'journals')
        assert isinstance(mock_client.journals, JournalManager)

    @patch('requests.post')
    def test_create_journal_delegates_to_manager(self, mock_post, mock_client):
        """Test that create_journal_entry delegates to JournalManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "uuid": "JournalEntry.journal123",
            "id": "journal123",
            "name": "Test Journal"
        }
        mock_post.return_value = mock_response

        result = mock_client.create_journal_entry(
            name="Test Journal",
            content="<p>Test content</p>"
        )

        assert result["uuid"] == "JournalEntry.journal123"
        mock_post.assert_called_once()

    @patch('requests.get')
    def test_get_journal_by_name_delegates_to_manager(self, mock_get, mock_client):
        """Test that get_journal_by_name delegates to JournalManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": [
                {"_id": "journal123", "name": "Test Journal", "uuid": "JournalEntry.journal123"}
            ]
        }
        mock_get.return_value = mock_response

        result = mock_client.get_journal_by_name("Test Journal")

        assert result is not None
        assert result["_id"] == "journal123"


class TestFoundryIntegration:
    """Integration tests for FoundryVTT API via WebSocket (requires running backend + Foundry)."""

    # Use environment variable for Docker compatibility
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

    @pytest.fixture
    def require_websocket(self):
        """Ensure backend is running and Foundry is connected via WebSocket."""
        import httpx

        # Check backend health
        try:
            response = httpx.get(f"{self.BACKEND_URL}/health", timeout=5.0)
            if response.status_code != 200:
                pytest.fail("Backend not healthy")
        except httpx.ConnectError:
            pytest.fail("Backend not running on localhost:8000")

        # Check Foundry WebSocket connection
        try:
            response = httpx.get(f"{self.BACKEND_URL}/api/foundry/status", timeout=5.0)
            if response.json().get("status") != "connected":
                pytest.fail("Foundry not connected to backend via WebSocket")
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            pytest.fail(f"Failed to check Foundry status: {e}")

        return True

    @pytest.fixture
    def real_client(self):
        """Create a real FoundryClient for integration tests."""
        return FoundryClient()

    @pytest.mark.smoke
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_create_and_delete(self, require_websocket):
        """Smoke test: Basic FoundryVTT journal CRUD operations via WebSocket

        Test basic create and delete workflow using HTTP -> WebSocket -> Foundry."""
        import httpx

        journal_name = "Integration Test Create Delete WS"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. CREATE via HTTP endpoint (which uses WebSocket internally)
            create_response = await client.post(
                f"{self.BACKEND_URL}/api/foundry/journal",
                json={
                    "name": journal_name,
                    "content": "<h1>Test Content</h1><p>This journal will be deleted immediately.</p>"
                }
            )

            assert create_response.status_code == 200, f"Create failed: {create_response.text}"
            create_result = create_response.json()

            # Extract UUID from create response
            journal_uuid = create_result.get('uuid')
            assert journal_uuid and journal_uuid.startswith('JournalEntry.'), f"Invalid UUID format: {journal_uuid}"

            # 2. DELETE via HTTP endpoint (which uses WebSocket internally)
            delete_response = await client.delete(
                f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}"
            )

            assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
            delete_result = delete_response.json()
            assert delete_result.get('success') is True, "Delete operation did not return success"


@pytest.mark.unit
class TestActorOperations:
    """Tests for actor operations via FoundryClient."""

    @pytest.fixture
    def mock_client(self):
        """Create a FoundryClient using environment variable (for Docker compatibility)."""
        # Uses BACKEND_URL env var if set, otherwise defaults to localhost:8000
        return FoundryClient()

    def test_client_initializes_actor_manager(self, mock_client):
        """Test client creates ActorManager instance."""
        assert hasattr(mock_client, 'actors')
        assert mock_client.actors is not None

    @patch('requests.get')
    def test_client_search_actor_delegates(self, mock_get, mock_client):
        """Test client.search_actor delegates to ActorManager."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": [
                {"uuid": "Actor.abc123", "name": "Goblin"}
            ]
        }
        mock_get.return_value = mock_response

        uuid = mock_client.search_actor("Goblin")

        assert uuid == "Actor.abc123"
        mock_get.assert_called_once()

    def test_client_create_creature_actor_raises_not_implemented(self, mock_client):
        """Test client.create_creature_actor raises NotImplementedError (not yet ported)."""
        from actor_pipeline.models import StatBlock

        stat_block = StatBlock(
            name="Goblin",
            raw_text="Goblin text",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25
        )

        with pytest.raises(NotImplementedError):
            mock_client.create_creature_actor(stat_block)

    @pytest.mark.integration
    def test_client_create_npc_actor_success(self, mock_client):
        """Test client.create_npc_actor creates minimal NPC actor (requires backend)."""
        from actor_pipeline.models import NPC

        npc = NPC(
            name="Klarg",
            creature_stat_block_name="Goblin Boss",
            description="Leader",
            plot_relevance="Guards supplies"
        )

        # create_npc_actor should succeed and return a UUID
        uuid = mock_client.create_npc_actor(npc, stat_block_uuid="Actor.boss123")
        assert uuid is not None
        assert uuid.startswith("Actor.")

    def test_foundry_client_has_icon_cache(self, mock_client):
        """Test FoundryClient exposes icon cache."""
        from caches import IconCache

        assert hasattr(mock_client, 'icons')
        assert isinstance(mock_client.icons, IconCache)
