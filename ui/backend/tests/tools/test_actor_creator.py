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

        This test mocks the push function to verify data structure.
        """
        from app.tools.actor_creator import ActorCreatorTool
        from app.websocket.push import PushResult

        # Mock the actor generation pipeline
        mock_parsed_actor = MagicMock()
        mock_parsed_actor.name = "Test Goblin"
        mock_parsed_actor.challenge_rating = 0.25
        mock_parsed_actor.model_copy = MagicMock(return_value=mock_parsed_actor)

        mock_actor_json = {
            "name": "Test Goblin",
            "type": "npc",
            "system": {
                "details": {"cr": 0.25},
                "abilities": {"str": {"value": 10}}
            },
            "items": []
        }
        mock_spell_uuids = []

        pushed_data = {}

        async def mock_push_actor(actor_data, timeout=30.0):
            """Mock push_actor to capture data and return simulated success."""
            pushed_data.update(actor_data)
            return PushResult(
                success=True,
                uuid="Actor.test123",
                id="test123",
                name=actor_data["name"]
            )

        # Mock all the pipeline steps
        with patch('app.tools.actor_creator.generate_actor_description', new_callable=AsyncMock) as mock_gen, \
             patch('app.tools.actor_creator.parse_raw_text_to_statblock', new_callable=AsyncMock) as mock_parse, \
             patch('app.tools.actor_creator.parse_stat_block_parallel', new_callable=AsyncMock) as mock_detail, \
             patch('app.tools.actor_creator.generate_actor_biography', new_callable=AsyncMock) as mock_bio, \
             patch('app.tools.actor_creator.convert_to_foundry', new_callable=AsyncMock) as mock_convert, \
             patch('app.tools.actor_creator.push_actor', side_effect=mock_push_actor) as mock_push, \
             patch('app.tools.actor_creator.SpellCache') as mock_spell_cache, \
             patch('app.tools.actor_creator.IconCache') as mock_icon_cache:

            mock_gen.return_value = "Test Goblin stat block text"
            mock_parse.return_value = MagicMock()
            mock_detail.return_value = mock_parsed_actor
            mock_bio.return_value = "A fierce goblin warrior."
            mock_convert.return_value = (mock_actor_json, mock_spell_uuids)

            tool = ActorCreatorTool()
            result = await tool.execute(
                description="A goblin warrior",
                challenge_rating=0.25
            )

            # Verify tool returned success
            assert result.type == "text"
            assert "Created" in result.message
            assert "Actor.test123" in result.message

            # Verify the pushed data structure
            assert pushed_data["name"] == "Test Goblin"
            assert pushed_data["cr"] == 0.25
            assert "actor" in pushed_data
            assert pushed_data["actor"]["name"] == "Test Goblin"
            assert pushed_data["actor"]["type"] == "npc"
            assert "spell_uuids" in pushed_data


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

        async def mock_push_actor(actor_data, timeout=30.0):
            """Capture actor data and return simulated success."""
            pushed_data.update(actor_data)
            return PushResult(
                success=True,
                uuid="Actor.realtest123",
                id="realtest123",
                name=actor_data["name"]
            )

        with patch('app.tools.actor_creator.push_actor', side_effect=mock_push_actor):
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
            assert "name" in pushed_data
            assert "cr" in pushed_data
            assert "actor" in pushed_data
            assert pushed_data["actor"]["type"] == "npc"
            assert "items" in pushed_data["actor"]
            assert "spell_uuids" in pushed_data
            print(f"[INTEGRATION] Pushed actor: {pushed_data['name']} (CR {pushed_data['cr']})")
