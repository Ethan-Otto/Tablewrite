"""Tests for ActorCreatorTool including WebSocket push (real WebSocket)."""
import os
import pytest
import threading
import asyncio
import queue
from fastapi.testclient import TestClient
from httpx import ASGITransport
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


class TestActorCreatorPush:
    """Test actor creator pushes to Foundry (real WebSocket)."""

    @pytest.mark.asyncio
    async def test_actor_creator_pushes_to_websocket(self):
        """Actor creator pushes full actor data to connected WebSocket client.

        With the request-response pattern:
        1. Tool pushes actor data with request_id
        2. Foundry receives and creates entity, sends UUID response
        3. Tool receives UUID and returns success

        This test mocks the orchestration layer to verify data flow.
        """
        from app.tools.actor_creator import ActorCreatorTool, load_caches
        from caches import SpellCache, IconCache

        # Mock the result from create_actor_from_description
        mock_result = MagicMock()
        mock_result.foundry_uuid = "Actor.test123"
        mock_result.challenge_rating = 0.25
        mock_result.stat_block = MagicMock()
        mock_result.stat_block.name = "Test Goblin"

        # Mock caches
        mock_spell_cache = MagicMock(spec=SpellCache)
        mock_icon_cache = MagicMock(spec=IconCache)

        # Mock load_caches to return mocked caches
        async def mock_load_caches():
            return mock_spell_cache, mock_icon_cache

        # Mock create_actor_from_description
        with patch('app.tools.actor_creator.load_caches', side_effect=mock_load_caches), \
             patch('app.tools.actor_creator.create_actor_from_description', new_callable=AsyncMock) as mock_create:

            mock_create.return_value = mock_result

            tool = ActorCreatorTool()
            result = await tool.execute(
                description="A goblin warrior",
                challenge_rating=0.25
            )

            # Verify tool returned success
            assert result.type == "text"
            assert "Created" in result.message
            assert "Actor.test123" in result.message
            assert "Test Goblin" in result.message

            # Verify create_actor_from_description was called with correct args
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["description"] == "A goblin warrior"
            assert call_kwargs["challenge_rating"] == 0.25
            assert call_kwargs["spell_cache"] == mock_spell_cache
            assert call_kwargs["icon_cache"] == mock_icon_cache


@pytest.mark.integration
@pytest.mark.slow
class TestActorCreatorPushIntegration:
    """Integration tests with real API calls (costs money)."""

    @pytest.mark.skipif(
        not os.getenv("GeminiImageAPI") and not os.getenv("GEMINI_API_KEY"),
        reason="Requires GeminiImageAPI or GEMINI_API_KEY"
    )
    @pytest.mark.asyncio
    async def test_actor_creator_pushes_real_actor_to_websocket(self):
        """
        Real integration test: Create actor via Gemini API and verify push.

        This test:
        - Uses REAL Gemini API to generate actor stats
        - Mocks the push function to capture data (avoiding WebSocket threading issues)
        - Verifies the generated actor data structure

        Warning: This test costs money (Gemini API calls) and requires:
        - GeminiImageAPI environment variable
        - FoundryVTT NOT required (we mock the push)
        """
        from app.tools.actor_creator import ActorCreatorTool
        from app.websocket.push import PushResult

        pushed_data = {}

        async def mock_push_actor(data, timeout=30.0):
            """Capture actor data and return simulated success."""
            pushed_data.update(data)
            # Data structure is {"actor": {...}, "spell_uuids": [...]}
            actor_name = data["actor"]["name"]
            return PushResult(
                success=True,
                uuid="Actor.realtest123",
                id="realtest123",
                name=actor_name
            )

        # Mock load_caches to avoid WebSocket dependency
        mock_spell_cache = MagicMock()
        mock_spell_cache.get_spell_uuid.return_value = None  # No spells found
        mock_icon_cache = MagicMock()
        mock_icon_cache.loaded = True
        mock_icon_cache.get_icon.return_value = None
        mock_icon_cache.get_icon_by_keywords.return_value = None
        # IconCache has async methods that need AsyncMock
        mock_icon_cache.get_icon_with_ai_fallback = AsyncMock(return_value="icons/svg/mystery-man.svg")
        mock_icon_cache.get_icons_batch = AsyncMock(return_value=[])

        async def mock_load_caches():
            return mock_spell_cache, mock_icon_cache

        with patch('app.tools.actor_creator.push_actor', side_effect=mock_push_actor), \
             patch('app.tools.actor_creator.load_caches', side_effect=mock_load_caches):
            tool = ActorCreatorTool()

            # Real API call - creates a simple goblin
            result = await tool.execute(
                description="A basic goblin scout",
                challenge_rating=0.25
            )

            # Verify tool returned success
            assert result.type == "text"
            assert "Created" in result.message

            # Verify the pushed data structure (real actor data from Gemini)
            # Data structure is {"actor": {...}, "spell_uuids": [...]}
            assert "actor" in pushed_data
            assert "spell_uuids" in pushed_data
            actor = pushed_data["actor"]
            assert "name" in actor
            assert actor["type"] == "npc"
            assert "items" in actor
            print(f"[INTEGRATION] Pushed actor: {actor['name']}")


class MockSpell:
    """Mock spell object for testing (avoids MagicMock 'name' issue)."""
    def __init__(self, name: str, uuid: str, type: str = "spell", img: str = "", pack: str = "dnd5e.spells"):
        self.name = name
        self.uuid = uuid
        self.type = type
        self.img = img
        self.pack = pack


class TestLoadCaches:
    """Tests for the load_caches function."""

    @pytest.mark.asyncio
    async def test_load_caches_returns_spell_and_icon_cache(self):
        """Test that load_caches returns both SpellCache and IconCache."""
        from app.tools.actor_creator import load_caches

        # Mock the WebSocket calls - use MockSpell to avoid MagicMock 'name' issue
        mock_spells_result = MagicMock()
        mock_spells_result.success = True
        mock_spells_result.results = [
            MockSpell(name="Fire Bolt", uuid="Compendium.dnd5e.spells.Item.abc")
        ]

        mock_files_result = MagicMock()
        mock_files_result.success = True
        mock_files_result.files = ["icons/magic/fire.webp"]

        with patch('app.tools.actor_creator.list_compendium_items_with_retry', new_callable=AsyncMock, return_value=mock_spells_result), \
             patch('app.tools.actor_creator.list_files_with_retry', new_callable=AsyncMock, return_value=mock_files_result):
            spell_cache, icon_cache = await load_caches()

        assert spell_cache is not None
        assert icon_cache is not None
        assert spell_cache.spell_count > 0
        assert icon_cache.icon_count > 0

    @pytest.mark.asyncio
    async def test_load_caches_raises_on_spell_failure(self):
        """Test that load_caches raises RuntimeError when spell loading fails."""
        from app.tools.actor_creator import load_caches

        mock_spells_result = MagicMock()
        mock_spells_result.success = False
        mock_spells_result.error = "Connection failed"

        with patch('app.tools.actor_creator.list_compendium_items_with_retry', new_callable=AsyncMock, return_value=mock_spells_result):
            with pytest.raises(RuntimeError, match="SpellCache FAILED"):
                await load_caches()

    @pytest.mark.asyncio
    async def test_load_caches_raises_on_empty_spells(self):
        """Test that load_caches raises RuntimeError when no spells returned."""
        from app.tools.actor_creator import load_caches

        mock_spells_result = MagicMock()
        mock_spells_result.success = True
        mock_spells_result.results = []

        with patch('app.tools.actor_creator.list_compendium_items_with_retry', new_callable=AsyncMock, return_value=mock_spells_result):
            with pytest.raises(RuntimeError, match="No spells returned"):
                await load_caches()

    @pytest.mark.asyncio
    async def test_load_caches_raises_on_icon_failure(self):
        """Test that load_caches raises RuntimeError when icon loading fails."""
        from app.tools.actor_creator import load_caches

        mock_spells_result = MagicMock()
        mock_spells_result.success = True
        mock_spells_result.results = [
            MockSpell(name="Fire Bolt", uuid="Compendium.dnd5e.spells.Item.abc")
        ]

        mock_files_result = MagicMock()
        mock_files_result.success = False
        mock_files_result.error = "Files not found"

        with patch('app.tools.actor_creator.list_compendium_items_with_retry', new_callable=AsyncMock, return_value=mock_spells_result), \
             patch('app.tools.actor_creator.list_files_with_retry', new_callable=AsyncMock, return_value=mock_files_result):
            with pytest.raises(RuntimeError, match="IconCache FAILED"):
                await load_caches()

    @pytest.mark.asyncio
    async def test_load_caches_raises_on_missing_fire_bolt(self):
        """Test that load_caches raises RuntimeError when Fire Bolt is missing."""
        from app.tools.actor_creator import load_caches

        mock_spells_result = MagicMock()
        mock_spells_result.success = True
        mock_spells_result.results = [
            MockSpell(name="Magic Missile", uuid="Compendium.dnd5e.spells.Item.xyz")
        ]

        with patch('app.tools.actor_creator.list_compendium_items_with_retry',
                   new_callable=AsyncMock, return_value=mock_spells_result):
            with pytest.raises(RuntimeError, match="Fire Bolt.*not found"):
                await load_caches()
