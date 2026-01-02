"""Scene management endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.websocket.push import push_scene

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/foundry", tags=["scenes"])


class SceneCreateRequest(BaseModel):
    """Request body for scene creation."""
    scene: Dict[str, Any]


@router.post("/scene")
async def create_scene(request: SceneCreateRequest):
    """
    Create a scene in FoundryVTT.

    The scene data is sent to the connected Foundry client via WebSocket.
    Supports battle maps with walls, art scenes, and gridless scenes.

    Args:
        request: SceneCreateRequest with scene data including:
            - name: Scene name (required)
            - width: Scene width in pixels
            - height: Scene height in pixels
            - grid: Grid configuration {"size": int, "type": int}
            - walls: List of wall definitions
            - background: Background image {"src": str}
            - folder: Optional folder name

    Returns:
        {"success": true, "uuid": "Scene.xxx", "name": "..."}

    Raises:
        HTTPException 500: If scene creation fails
        HTTPException 503: If Foundry is not connected
    """
    result = await push_scene(request.scene, timeout=30.0)

    if not result.success:
        # Check for connection-related errors and return 503
        if result.error and ("not connected" in result.error.lower() or "timeout" in result.error.lower()):
            raise HTTPException(status_code=503, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "uuid": result.uuid,
        "name": result.name
    }
