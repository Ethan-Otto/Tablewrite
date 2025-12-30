"""Tests for ActorCreatorTool including WebSocket push (real WebSocket)."""
import os
import pytest
import threading
import asyncio
import queue
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


class TestActorCreatorPush:
    """Test actor creator pushes to Foundry (real WebSocket)."""

    def test_actor_creator_pushes_to_websocket(self):
        """Actor creator pushes full actor data to connected WebSocket client."""
        from app.tools.actor_creator import ActorCreatorTool

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

        client = TestClient(app)
        result_queue = queue.Queue()

        with client.websocket_connect("/ws/foundry") as websocket:
            welcome = websocket.receive_json()  # Consume welcome
            assert welcome["type"] == "connected"

            # Mock all the pipeline steps
            with patch('app.tools.actor_creator.generate_actor_description', new_callable=AsyncMock) as mock_gen, \
                 patch('app.tools.actor_creator.parse_raw_text_to_statblock', new_callable=AsyncMock) as mock_parse, \
                 patch('app.tools.actor_creator.parse_stat_block_parallel', new_callable=AsyncMock) as mock_detail, \
                 patch('app.tools.actor_creator.generate_actor_biography', new_callable=AsyncMock) as mock_bio, \
                 patch('app.tools.actor_creator.convert_to_foundry', new_callable=AsyncMock) as mock_convert, \
                 patch('app.tools.actor_creator.SpellCache') as mock_spell_cache, \
                 patch('app.tools.actor_creator.IconCache') as mock_icon_cache:

                mock_gen.return_value = "Test Goblin stat block text"
                mock_parse.return_value = MagicMock()
                mock_detail.return_value = mock_parsed_actor
                mock_bio.return_value = "A fierce goblin warrior."
                mock_convert.return_value = (mock_actor_json, mock_spell_uuids)

                tool = ActorCreatorTool()

                def execute_thread():
                    try:
                        result = asyncio.run(tool.execute(
                            description="A goblin warrior",
                            challenge_rating=0.25
                        ))
                        result_queue.put(("success", result))
                    except Exception as e:
                        result_queue.put(("error", str(e)))

                thread = threading.Thread(target=execute_thread)
                thread.start()
                thread.join(timeout=10)  # 10 second timeout

                if thread.is_alive():
                    pytest.fail("Tool execution timed out")

            # Get tool result
            try:
                status, tool_result = result_queue.get(timeout=1)
                assert status == "success", f"Tool execution failed: {tool_result}"
            except queue.Empty:
                pytest.fail("No result from tool execution")

            # Verify WebSocket received the push with FULL actor data
            try:
                data = websocket.receive_json()
                assert data["type"] == "actor"
                assert data["data"]["name"] == "Test Goblin"
                assert data["data"]["cr"] == 0.25
                # Now we push full actor data, not just name/uuid
                assert "actor" in data["data"]
                assert data["data"]["actor"]["name"] == "Test Goblin"
                assert data["data"]["actor"]["type"] == "npc"
            except Exception as e:
                pytest.fail(f"WebSocket did not receive actor push: {e}")


@pytest.mark.integration
@pytest.mark.slow
class TestActorCreatorPushIntegration:
    """Integration tests with real API calls (costs money)."""

    @pytest.mark.skipif(
        not os.getenv("GeminiImageAPI") and not os.getenv("GEMINI_API_KEY"),
        reason="Requires GeminiImageAPI or GEMINI_API_KEY"
    )
    def test_actor_creator_pushes_real_actor_to_websocket(self):
        """
        Real integration test: Create actor via Gemini API and verify push.

        This test:
        - Uses REAL Gemini API to generate actor stats
        - Pushes FULL actor data via WebSocket (no relay server)
        - Verifies the WebSocket push reaches connected clients

        Warning: This test costs money (Gemini API calls) and requires:
        - GeminiImageAPI environment variable
        - FoundryVTT NOT required (we only test WebSocket push, not Foundry creation)
        """
        from app.tools.actor_creator import ActorCreatorTool

        client = TestClient(app)
        result_queue = queue.Queue()

        with client.websocket_connect("/ws/foundry") as websocket:
            welcome = websocket.receive_json()
            assert welcome["type"] == "connected"

            tool = ActorCreatorTool()

            def execute_thread():
                try:
                    # Real API call - creates a simple goblin
                    result = asyncio.run(tool.execute(
                        description="A basic goblin scout",
                        challenge_rating=0.25
                    ))
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", str(e)))

            thread = threading.Thread(target=execute_thread)
            thread.start()
            # Real API calls take 10-30 seconds
            thread.join(timeout=60)

            if thread.is_alive():
                pytest.fail("Tool execution timed out (>60s)")

            # Get tool result
            try:
                status, tool_result = result_queue.get(timeout=1)
                if status == "error":
                    pytest.fail(f"Tool execution failed: {tool_result}")
            except queue.Empty:
                pytest.fail("No result from tool execution")

            # Verify WebSocket received the push with FULL actor data
            try:
                data = websocket.receive_json()
                assert data["type"] == "actor"
                assert "name" in data["data"]
                assert "cr" in data["data"]
                # Now we push full actor data for Foundry module to create
                assert "actor" in data["data"]
                assert data["data"]["actor"]["type"] == "npc"
                assert "items" in data["data"]["actor"]
                assert "spell_uuids" in data["data"]
                print(f"[INTEGRATION] Pushed actor: {data['data']['name']} (CR {data['data']['cr']})")
            except Exception as e:
                pytest.fail(f"WebSocket did not receive actor push: {e}")
