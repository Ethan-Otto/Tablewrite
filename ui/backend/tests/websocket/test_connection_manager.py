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
