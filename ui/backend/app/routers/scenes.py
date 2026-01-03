"""Scene management endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.websocket.push import push_scene, fetch_scene, delete_scene

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


@router.get("/scene/{uuid:path}")
async def get_scene_endpoint(uuid: str):
    """
    Get a scene by UUID.

    Args:
        uuid: The scene UUID (e.g., "Scene.abc123")

    Returns:
        {"success": true, "entity": {...}} on success

    Raises:
        HTTPException 404: If scene is not found
        HTTPException 500: If fetch fails
        HTTPException 503: If Foundry is not connected
    """
    result = await fetch_scene(uuid, timeout=30.0)

    if not result.success:
        # Check for connection-related errors and return 503
        if result.error and ("not connected" in result.error.lower() or "timeout" in result.error.lower()):
            raise HTTPException(status_code=503, detail=result.error)
        # Check for not found errors and return 404
        if result.error and "not found" in result.error.lower():
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "entity": result.entity
    }


@router.delete("/scene/{uuid:path}")
async def delete_scene_endpoint(uuid: str):
    """
    Delete a scene by UUID.

    Args:
        uuid: The scene UUID (e.g., "Scene.abc123")

    Returns:
        {"success": true, "uuid": "...", "name": "..."} on success

    Raises:
        HTTPException 404: If scene is not found
        HTTPException 500: If deletion fails
        HTTPException 503: If Foundry is not connected
    """
    result = await delete_scene(uuid, timeout=30.0)

    if not result.success:
        # Check for connection-related errors and return 503
        if result.error and ("not connected" in result.error.lower() or "timeout" in result.error.lower()):
            raise HTTPException(status_code=503, detail=result.error)
        # Check for not found errors and return 404
        if result.error and "not found" in result.error.lower():
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "uuid": result.uuid,
        "name": result.name
    }
