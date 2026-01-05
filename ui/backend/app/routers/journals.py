"""Journal CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.websocket import push_journal, delete_journal, fetch_journal, list_journals, update_journal

router = APIRouter(prefix="/api/foundry", tags=["journals"])


class UpdateJournalRequest(BaseModel):
    """Request body for updating a journal."""
    updates: dict


@router.post("/journal")
async def create_journal_entry(request: dict):
    """
    Create a journal entry in Foundry via WebSocket.

    Args:
        request: Journal data with 'name', 'pages' or 'content', and optional 'folder'

    Returns:
        Created journal UUID and name
    """
    journal = {
        "name": request.get("name", "Untitled Journal"),
        "pages": request.get("pages", [
            {
                "name": "Content",
                "type": "text",
                "text": {"content": request.get("content", "")}
            }
        ])
    }

    # Add folder if provided
    if request.get("folder"):
        journal["folder"] = request.get("folder")

    journal_data = {"journal": journal}

    result = await push_journal(journal_data, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/journal/{uuid}")
async def get_journal_by_uuid(uuid: str):
    """
    Fetch a journal entry from Foundry by UUID via WebSocket.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")

    Returns:
        Journal entity data
    """
    result = await fetch_journal(uuid, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "entity": result.entity
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@router.delete("/journal/{uuid}")
async def delete_journal_by_uuid(uuid: str):
    """
    Delete a journal entry from Foundry by UUID via WebSocket.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")

    Returns:
        Success status with deleted journal info
    """
    result = await delete_journal(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "message": f"Deleted journal: {result.name}"
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@router.get("/journals")
async def get_all_journals():
    """
    List all world journals from Foundry.

    Returns:
        List of journals with uuid, id, name, and folder
    """
    result = await list_journals(timeout=10.0)

    if result.success:
        return {
            "success": True,
            "count": len(result.journals) if result.journals else 0,
            "journals": [
                {"uuid": j.uuid, "id": j.id, "name": j.name, "folder": j.folder}
                for j in (result.journals or [])
            ],
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.patch("/journal/{uuid}")
async def update_journal_by_uuid(uuid: str, request: UpdateJournalRequest):
    """
    Update a journal in Foundry by UUID via WebSocket.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")
        request: UpdateJournalRequest with updates dict

    Returns:
        Updated journal info
    """
    result = await update_journal(uuid, request.updates, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
