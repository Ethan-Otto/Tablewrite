"""WebSocket endpoint for Foundry module connections."""
import logging
from fastapi import WebSocket, WebSocketDisconnect
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Global connection manager instance
foundry_manager = ConnectionManager()


async def foundry_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Foundry module connections.

    Protocol:
    - On connect: sends {"type": "connected", "client_id": "..."}
    - Client can send {"type": "ping"} -> receives {"type": "pong"}
    - Server pushes content: {"type": "actor|journal|scene", "data": {...}}
    """
    await websocket.accept()
    client_id = foundry_manager.connect(websocket)

    logger.info(f"Foundry client connected: {client_id}")

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id
        })

        # Handle incoming messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Foundry client disconnected: {client_id}")
    finally:
        foundry_manager.disconnect(client_id)
