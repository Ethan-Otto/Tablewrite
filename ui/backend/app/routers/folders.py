"""Folder CRUD endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException

from app.websocket import get_or_create_folder, list_folders, delete_folder

router = APIRouter(prefix="/api/foundry", tags=["folders"])


@router.post("/folder")
async def create_folder(request: dict):
    """
    Get or create a folder in Foundry via WebSocket.

    Args:
        request: Folder data with 'name', 'type', and optional 'parent'

    Returns:
        Folder ID and name
    """
    name = request.get("name")
    folder_type = request.get("type")
    parent = request.get("parent")

    if not name or not folder_type:
        raise HTTPException(status_code=400, detail="name and type are required")

    result = await get_or_create_folder(name, folder_type, parent=parent)

    if result.success:
        return {
            "success": True,
            "folder_id": result.folder_id,
            "folder_uuid": result.folder_uuid,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/folders")
async def get_folders(type: Optional[str] = None):
    """
    List all folders in Foundry, optionally filtered by type.

    Args:
        type: Optional folder type filter (Actor, Scene, JournalEntry, etc.)

    Returns:
        List of folders
    """
    result = await list_folders(folder_type=type)

    if result.success:
        return {
            "success": True,
            "folders": result.folders
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.delete("/folder/{folder_id}")
async def delete_folder_endpoint(folder_id: str, delete_contents: bool = True):
    """
    Delete a folder from Foundry, optionally with all its contents.

    Args:
        folder_id: The folder ID to delete
        delete_contents: If True, delete all documents in the folder first (default: True)

    Returns:
        Success status and deleted count
    """
    result = await delete_folder(folder_id, delete_contents=delete_contents)

    if result.success:
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "folder_name": result.folder_name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
