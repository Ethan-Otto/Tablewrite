"""Tests for push notification helpers (real WebSocket, no mocks)."""
import pytest
import asyncio
import threading
from fastapi.testclient import TestClient
from app.main import app


class TestPushToFoundry:
    """Test push functions with real WebSocket connections."""

    def test_push_actor_reaches_connected_client(self):
        """push_actor() sends actor data to connected WebSocket client."""
        from app.websocket.push import push_actor

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Push actor in separate thread (sync context)
            actor_data = {"name": "Goblin", "type": "npc"}

            def push_thread():
                asyncio.run(push_actor(actor_data))

            thread = threading.Thread(target=push_thread)
            thread.start()

            # Receive the push first (before join to avoid race condition)
            data = websocket.receive_json()
            assert data["type"] == "actor"
            assert data["data"]["name"] == "Goblin"

            thread.join(timeout=5.0)

    def test_push_journal_reaches_connected_client(self):
        """push_journal() sends journal data to connected WebSocket client."""
        from app.websocket.push import push_journal

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            websocket.receive_json()  # Consume welcome

            journal_data = {"name": "Chapter 1", "pages": []}

            def push_thread():
                asyncio.run(push_journal(journal_data))

            thread = threading.Thread(target=push_thread)
            thread.start()

            # Receive the push first (before join to avoid race condition)
            data = websocket.receive_json()
            assert data["type"] == "journal"
            assert data["data"]["name"] == "Chapter 1"

            thread.join(timeout=5.0)

    def test_push_scene_reaches_connected_client(self):
        """push_scene() sends scene data to connected WebSocket client."""
        from app.websocket.push import push_scene

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            websocket.receive_json()  # Consume welcome

            scene_data = {"name": "Cave Entrance", "walls": []}

            def push_thread():
                asyncio.run(push_scene(scene_data))

            thread = threading.Thread(target=push_thread)
            thread.start()

            # Receive the push first (before join to avoid race condition)
            data = websocket.receive_json()
            assert data["type"] == "scene"
            assert data["data"]["name"] == "Cave Entrance"

            thread.join(timeout=5.0)
