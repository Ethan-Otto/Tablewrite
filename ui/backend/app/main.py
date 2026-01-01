"""D&D Module Assistant API."""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv
from app.routers import actors, chat, health
from app.config import settings
from app.websocket import foundry_websocket_endpoint


# Load environment variables from project root .env
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to backend .env
    load_dotenv()

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(actors.router)


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    """
    Serve generated images from chat_images directory.

    Args:
        filename: Image filename

    Returns:
        Image file

    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: validate filename (no path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only serve .png files
    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files supported")

    file_path = settings.IMAGE_OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")


@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)


# --- Journal WebSocket Endpoints ---

@app.post("/api/foundry/journal")
async def create_journal_entry(request: dict):
    """
    Create a journal entry in Foundry via WebSocket.

    Args:
        request: Journal data with 'name' and 'pages' or 'content'

    Returns:
        Created journal UUID and name
    """
    from app.websocket import push_journal

    # Build journal data for Foundry
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


@app.delete("/api/foundry/journal/{uuid}")
async def delete_journal_by_uuid(uuid: str):
    """
    Delete a journal entry from Foundry by UUID via WebSocket.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")

    Returns:
        Success status with deleted journal info
    """
    from app.websocket import delete_journal

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


@app.get("/api/foundry/search")
async def search_foundry_items(
    query: str = "",
    document_type: str = "Item",
    sub_type: str = None
):
    """
    Search Foundry compendiums for items.

    Args:
        query: Search query (case-insensitive contains match)
        document_type: Document type to search (default: "Item")
        sub_type: Optional subtype filter (e.g., "spell", "weapon")

    Returns:
        List of matching items with uuid, name, type, etc.
    """
    from app.websocket import search_items

    result = await search_items(
        query=query,
        document_type=document_type,
        sub_type=sub_type,
        timeout=30.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.results) if result.results else 0,
            "results": [
                {
                    "uuid": r.uuid,
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "img": r.img,
                    "pack": r.pack
                }
                for r in (result.results or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.get("/api/foundry/compendium")
async def list_compendium_items_endpoint(
    document_type: str = "Item",
    sub_type: str = None
):
    """
    List ALL items of a specific type from Foundry compendiums.

    Much more efficient than search - fetches everything in one request.

    Args:
        document_type: Document type to list (default: "Item")
        sub_type: Optional subtype filter (e.g., "spell", "weapon")

    Returns:
        List of all matching items with uuid, name, type, etc.
    """
    from app.websocket import list_compendium_items

    result = await list_compendium_items(
        document_type=document_type,
        sub_type=sub_type,
        timeout=60.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.results) if result.results else 0,
            "results": [
                {
                    "uuid": r.uuid,
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "img": r.img,
                    "pack": r.pack,
                    "system": r.system if hasattr(r, 'system') and r.system else None
                }
                for r in (result.results or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.get("/api/foundry/files")
async def list_foundry_files(
    path: str = "icons",
    source: str = "public",
    recursive: bool = True,
    extensions: str = None
):
    """
    List files in Foundry file system.

    Args:
        path: Directory path to browse (default: "icons")
        source: File source - "data", "public", or "s3" (default: "public")
        recursive: Whether to recurse into subdirectories (default: True)
        extensions: Comma-separated list of extensions (e.g., ".webp,.png")

    Returns:
        List of file paths
    """
    from app.websocket import list_files

    ext_list = extensions.split(",") if extensions else None

    result = await list_files(
        path=path,
        source=source,
        recursive=recursive,
        extensions=ext_list,
        timeout=60.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.files) if result.files else 0,
            "files": result.files or []
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
