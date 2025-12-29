"""Manage WebSocket connections from Foundry modules."""
import uuid
from typing import Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manage active WebSocket connections from Foundry clients."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    def connect(self, websocket: WebSocket) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            client_id: Unique identifier for this connection
        """
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            client_id: The client to disconnect
        """
        self.active_connections.pop(client_id, None)

    @property
    def connection_count(self) -> int:
        """Return number of active connections."""
        return len(self.active_connections)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Send message to all connected clients.

        Automatically removes clients that fail to receive.

        Args:
            message: JSON-serializable message to broadcast
        """
        disconnected = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)

        # Clean up failed connections
        for client_id in disconnected:
            self.disconnect(client_id)
