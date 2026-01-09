"""WebSocket endpoint for Foundry module connections."""
import logging
from fastapi import WebSocket, WebSocketDisconnect
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Global connection manager instance
foundry_manager = ConnectionManager()

# Response message types from Foundry module
RESPONSE_TYPES = {
    # Creation responses
    "actor_created",
    "journal_created",
    "scene_created",
    # Fetch responses
    "journal_data",
    "actor_error",
    "journal_error",
    "scene_error",
    # Fetch responses
    "actor_data",
    "scene_data",
    # Update responses
    "actor_updated",
    # Delete responses
    "actor_deleted",
    "journal_deleted",
    "scene_deleted",
    # List responses
    "actors_list",
    "journals_list",
    "scenes_list",
    # Journal update responses
    "journal_updated",
    # Search responses
    "items_found",
    "search_error",
    "item_data",
    "item_error",
    # Compendium list responses (efficient bulk fetch)
    "compendium_items_list",
    "compendium_items_error",
    # File operations responses
    "files_list",
    "files_error",
    "file_uploaded",
    "file_error",
    # Custom items responses
    "custom_items_added",
    "custom_items_error",
    # Give items responses
    "items_given",
    "give_error",
    # Remove items responses
    "actor_items_removed",
    # Folder responses
    "folder_result",
    "folder_deleted",
    "folder_error",
    "folders_list",
}


async def foundry_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Foundry module connections.

    Protocol:
    - On connect: sends {"type": "connected", "client_id": "..."}
    - Client can send {"type": "ping"} -> receives {"type": "pong"}
    - Server pushes content: {"type": "actor|journal|scene", "data": {...}, "request_id": "..."}
    - Client responds: {"type": "actor_created|journal_created|scene_created", "request_id": "...", "data": {...}}
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
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type in RESPONSE_TYPES:
                # This is a response to a request we sent
                request_id = data.get("request_id")
                if request_id:
                    handled = foundry_manager.handle_response(request_id, data)
                    if handled:
                        logger.debug(f"Handled response for request {request_id}")
                    else:
                        logger.warning(f"No pending request for {request_id}")
                else:
                    logger.warning(f"Response missing request_id: {data}")

    except WebSocketDisconnect:
        logger.info(f"Foundry client disconnected: {client_id}")
    finally:
        foundry_manager.disconnect(client_id)
