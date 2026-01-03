"""Scene management endpoints."""

import asyncio
import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.websocket.push import push_scene, fetch_scene, delete_scene

# Add src to path for scene orchestration import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from scenes.orchestrate import create_scene_from_map_sync

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


# Scene upload endpoint - different prefix to avoid conflict with foundry prefix
scene_upload_router = APIRouter(tags=["scenes"])


@scene_upload_router.post("/api/scenes/create-from-map")
async def create_scene_from_map_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    grid_size: Optional[int] = Form(None),
    skip_walls: bool = Form(False),
):
    """
    Create a FoundryVTT scene from an uploaded battle map image.

    Runs full pipeline: wall detection -> grid detection -> upload -> scene create.
    Takes 40-75 seconds depending on image size.

    Args:
        file: Battle map image file (PNG, JPG, WEBP)
        name: Optional scene name (defaults to filename)
        grid_size: Optional grid size override in pixels
        skip_walls: Skip wall detection step (default: False)

    Returns:
        Scene creation result with UUID, name, grid size, wall count, dimensions
    """
    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / file.filename
    try:
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Run pipeline in thread pool (blocking operations)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: create_scene_from_map_sync(
                image_path=temp_file,
                name=name,
                skip_wall_detection=skip_walls,
                grid_size_override=grid_size,
            )
        )

        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "grid_size": result.grid_size,
            "wall_count": result.wall_count,
            "image_dimensions": result.image_dimensions,
            "foundry_image_path": result.foundry_image_path,
        }
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)