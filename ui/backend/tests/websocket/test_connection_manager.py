"""Tests for WebSocket connection manager."""
import pytest
from app.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test ConnectionManager class."""

    def test_manager_initializes_empty(self):
        """Manager starts with no connections."""
        manager = ConnectionManager()
        assert manager.active_connections == {}

    def test_connect_adds_client(self):
        """connect() adds client to active_connections."""
        manager = ConnectionManager()
        mock_ws = object()  # Placeholder for WebSocket

        client_id = manager.connect(mock_ws)

        assert client_id in manager.active_connections
        assert manager.active_connections[client_id] == mock_ws

    def test_disconnect_removes_client(self):
        """disconnect() removes client from active_connections."""
        manager = ConnectionManager()
        mock_ws = object()

        client_id = manager.connect(mock_ws)
        manager.disconnect(client_id)

        assert client_id not in manager.active_connections

    def test_disconnect_nonexistent_client_is_safe(self):
        """disconnect() with unknown client_id doesn't raise."""
        manager = ConnectionManager()

        # Should not raise
        manager.disconnect("nonexistent-id")

    def test_multiple_connections_have_unique_ids(self):
        """Multiple connections get unique client IDs (real UUID validation)."""
        import uuid
        manager = ConnectionManager()

        # Connect multiple clients
        client_ids = []
        for _ in range(10):
            mock_ws = object()
            client_id = manager.connect(mock_ws)
            client_ids.append(client_id)

        # Verify all IDs are unique
        assert len(client_ids) == len(set(client_ids)), "Client IDs should be unique"

        # Verify all IDs are valid UUIDs
        for client_id in client_ids:
            # This will raise ValueError if not a valid UUID
            parsed = uuid.UUID(client_id)
            assert str(parsed) == client_id

        # Verify all connections are tracked
        assert len(manager.active_connections) == 10


class TestConnectionManagerBroadcast:
    """Test broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_is_noop(self):
        """broadcast() with no connections doesn't raise."""
        manager = ConnectionManager()

        # Should not raise
        await manager.broadcast({"type": "test"})

    def test_get_connection_count(self):
        """connection_count property returns number of active connections."""
        manager = ConnectionManager()

        assert manager.connection_count == 0

        mock_ws = object()
        manager.connect(mock_ws)

        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connections(self):
        """broadcast() removes connections that fail to receive (real data test)."""
        manager = ConnectionManager()

        # Create a mock WebSocket that raises on send_json
        class FailingWebSocket:
            async def send_json(self, data):
                raise ConnectionError("Connection lost")

        # Connect the failing WebSocket
        failing_ws = FailingWebSocket()
        client_id = manager.connect(failing_ws)

        assert manager.connection_count == 1

        # Broadcast with real message data
        await manager.broadcast({
            "type": "actor",
            "data": {
                "name": "Test Goblin",
                "type": "npc",
                "system": {
                    "abilities": {
                        "str": {"value": 10},
                        "dex": {"value": 14}
                    }
                }
            }
        })

        # Failed connection should have been removed
        assert manager.connection_count == 0
        assert client_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_successful_connections(self):
        """broadcast() sends data to successful connections (real data test)."""
        manager = ConnectionManager()

        # Create a mock WebSocket that tracks received messages
        received_messages = []

        class SuccessfulWebSocket:
            async def send_json(self, data):
                received_messages.append(data)

        # Connect the successful WebSocket
        ws = SuccessfulWebSocket()
        client_id = manager.connect(ws)

        # Broadcast real actor data
        actor_data = {
            "type": "actor",
            "data": {
                "name": "Goblin Shaman",
                "type": "npc",
                "system": {
                    "abilities": {
                        "str": {"value": 8},
                        "dex": {"value": 14},
                        "con": {"value": 10},
                        "int": {"value": 10},
                        "wis": {"value": 14},
                        "cha": {"value": 8}
                    },
                    "attributes": {
                        "hp": {"value": 12, "max": 12},
                        "ac": {"value": 12}
                    }
                }
            }
        }
        await manager.broadcast(actor_data)

        # Connection should still exist
        assert manager.connection_count == 1
        assert client_id in manager.active_connections

        # Message should have been received
        assert len(received_messages) == 1
        assert received_messages[0] == actor_data
        assert received_messages[0]["data"]["name"] == "Goblin Shaman"
