"""Journal CRUD endpoints."""

from fastapi import APIRouter, HTTPException

from app.websocket import push_journal, delete_journal

router = APIRouter(prefix="/api/foundry", tags=["journals"])


@router.post("/journal")
async def create_journal_entry(request: dict):
    """
    Create a journal entry in Foundry via WebSocket.

    Args:
        request: Journal data with 'name' and 'pages' or 'content'

    Returns:
        Created journal UUID and name
    """
    journal_data = {
        "journal": {
            "name": request.get("name", "Untitled Journal"),
            "pages": request.get("pages", [
                {
                    "name": "Content",
                    "type": "text",
                    "text": {"content": request.get("content", "")}
                }
            ])
        }
    }

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
