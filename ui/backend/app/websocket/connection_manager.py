"""Manage WebSocket connections from Foundry modules."""
import asyncio
import uuid
from typing import Dict, Any, Optional
from fastapi import WebSocket


class ConnectionManager:
    """Manage active WebSocket connections from Foundry clients."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # Track pending requests waiting for responses
        self._pending_requests: Dict[str, asyncio.Future] = {}

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

    async def broadcast_and_wait(
        self,
        message: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Broadcast a message and wait for a response from any client.

        Args:
            message: JSON-serializable message to broadcast
            timeout: Maximum seconds to wait for response

        Returns:
            Response data from Foundry module, or None if timeout/no clients
        """
        if not self.active_connections:
            return None

        # Generate unique request ID
        request_id = str(uuid.uuid4())
        message["request_id"] = request_id

        # Create a future to wait for the response
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_requests[request_id] = future

        try:
            # Broadcast the message
            await self.broadcast(message)

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                return None
        finally:
            # Clean up pending request
            self._pending_requests.pop(request_id, None)

    def handle_response(self, request_id: str, response_data: Dict[str, Any]) -> bool:
        """
        Handle a response from a Foundry client.

        Args:
            request_id: The request ID this is responding to
            response_data: The response data

        Returns:
            True if a pending request was found and resolved
        """
        future = self._pending_requests.get(request_id)
        if future and not future.done():
            future.set_result(response_data)
            return True
        return False
