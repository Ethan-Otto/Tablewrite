"""Tests for Foundry WebSocket endpoint (real WebSocket, no mocks)."""
import pytest
import asyncio
import threading
from fastapi.testclient import TestClient
from app.main import app


class TestFoundryWebSocket:
    """Test /ws/foundry endpoint with real WebSocket connections."""

    def test_websocket_connects(self):
        """Client can connect to /ws/foundry."""
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Connection established - receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data

    def test_websocket_receives_ping(self):
        """Client can send ping and receive pong."""
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_broadcast_reaches_connected_client(self):
        """Broadcast sends message to connected WebSocket client."""
        from app.websocket import foundry_manager

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Broadcast a message (need to run in event loop)
            message = {"type": "actor", "data": {"name": "Test Goblin"}}

            # Use the app's event loop to broadcast
            async def do_broadcast():
                await foundry_manager.broadcast(message)

            # TestClient runs in sync context, so we need asyncio.run
            def broadcast_thread():
                asyncio.run(do_broadcast())

            thread = threading.Thread(target=broadcast_thread)
            thread.start()
            thread.join()

            # Receive the broadcast
            data = websocket.receive_json()
            assert data["type"] == "actor"
            assert data["data"]["name"] == "Test Goblin"

    def test_client_id_is_valid_uuid(self):
        """Client ID in welcome message is a valid UUID (real data test)."""
        import uuid
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"

            # Verify client_id is a valid UUID
            client_id = data["client_id"]
            parsed_uuid = uuid.UUID(client_id)
            assert str(parsed_uuid) == client_id

    def test_multiple_clients_can_connect(self):
        """Multiple clients can connect and receive independent welcome messages."""
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws1:
            welcome1 = ws1.receive_json()
            assert welcome1["type"] == "connected"
            client_id_1 = welcome1["client_id"]

            with client.websocket_connect("/ws/foundry") as ws2:
                welcome2 = ws2.receive_json()
                assert welcome2["type"] == "connected"
                client_id_2 = welcome2["client_id"]

                # Client IDs should be different
                assert client_id_1 != client_id_2
