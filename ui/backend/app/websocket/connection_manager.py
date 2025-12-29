"""Manage WebSocket connections from Foundry modules."""
import uuid
from typing import Dict
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
