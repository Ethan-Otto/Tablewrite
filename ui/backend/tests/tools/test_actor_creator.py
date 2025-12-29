"""Tests for ActorCreatorTool including WebSocket push (real WebSocket)."""
import os
import pytest
import threading
import asyncio
import queue
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


class TestActorCreatorPush:
    """Test actor creator pushes to Foundry (real WebSocket)."""

    def test_actor_creator_pushes_to_websocket(self):
        """Actor creator pushes result to connected WebSocket client."""
        from app.tools.actor_creator import ActorCreatorTool

        # Mock only the external API call, not the WebSocket
        mock_result = MagicMock()
        mock_result.foundry_uuid = "Actor.abc123"
        mock_result.name = "Test Goblin"
        mock_result.challenge_rating = 0.25
        mock_result.output_dir = "/output"

        client = TestClient(app)

        # Use a queue to communicate between threads
        result_queue = queue.Queue()

        with client.websocket_connect("/ws/foundry") as websocket:
            welcome = websocket.receive_json()  # Consume welcome
            assert welcome["type"] == "connected"

            # Execute tool in thread (mocking only the Gemini API call)
            with patch('app.tools.actor_creator.create_actor', return_value=mock_result):
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

            # Verify WebSocket received the push
            # The push happens during tool execution, so message should be ready
            try:
                data = websocket.receive_json()
                assert data["type"] == "actor"
                assert data["data"]["name"] == "Test Goblin"
                assert data["data"]["uuid"] == "Actor.abc123"
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
        - Uses REAL FoundryVTT connection to create the actor
        - Verifies the WebSocket push reaches connected clients

        Warning: This test costs money (Gemini API calls) and requires:
        - GeminiImageAPI environment variable
        - FoundryVTT running with valid credentials
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

            # Verify WebSocket received the push with real data
            try:
                data = websocket.receive_json()
                assert data["type"] == "actor"
                assert "name" in data["data"]
                assert "uuid" in data["data"]
                assert "cr" in data["data"]
                # Real actor should have a valid UUID format
                assert data["data"]["uuid"].startswith("Actor.")
                print(f"[INTEGRATION] Created actor: {data['data']['name']} (CR {data['data']['cr']})")
            except Exception as e:
                pytest.fail(f"WebSocket did not receive actor push: {e}")
