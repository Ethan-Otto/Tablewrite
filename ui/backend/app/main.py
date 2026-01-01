"""D&D Module Assistant API."""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from app.routers import chat
from app.config import settings
from app.websocket import foundry_websocket_endpoint, foundry_manager, fetch_actor, delete_actor, list_actors


class CreateActorRequest(BaseModel):
    """Request body for actor creation."""
    description: str
    challenge_rating: float = 1.0
    output_dir_base: Optional[str] = None

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
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }


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


@app.get("/api/foundry/status")
async def foundry_status():
    """Check Foundry WebSocket connection status."""
    return {
        "connected_clients": foundry_manager.connection_count,
        "status": "connected" if foundry_manager.connection_count > 0 else "disconnected"
    }


@app.get("/api/foundry/actor/{uuid}")
async def get_actor_by_uuid(uuid: str):
    """
    Fetch an actor from Foundry by UUID via WebSocket.

    Args:
        uuid: The actor UUID (e.g., "Actor.vKEhnoBxM7unbhAL")

    Returns:
        Actor entity data or error
    """
    result = await fetch_actor(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "name": result.entity.get("name") if result.entity else None,
            "entity": result.entity
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@app.delete("/api/foundry/actor/{uuid}")
async def delete_actor_by_uuid(uuid: str):
    """
    Delete an actor from Foundry by UUID via WebSocket.

    Args:
        uuid: The actor UUID (e.g., "Actor.vKEhnoBxM7unbhAL")

    Returns:
        Success status with deleted actor info
    """
    result = await delete_actor(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "message": f"Deleted actor: {result.name}"
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@app.post("/api/foundry/actor")
async def create_actor_raw(request: dict):
    """
    Create a raw actor in Foundry via WebSocket.

    This endpoint accepts a complete FoundryVTT actor JSON structure
    and creates it directly in Foundry. For AI-generated actors from
    descriptions, use /api/actors/create instead.

    Args:
        request: Dict with 'actor' key containing FoundryVTT actor data

    Returns:
        Created actor UUID and name
    """
    from app.websocket import push_actor

    actor_data = request.get("actor")
    if not actor_data:
        raise HTTPException(status_code=400, detail="Missing 'actor' field in request")

    result = await push_actor(actor_data, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.get("/api/foundry/actors")
async def get_all_actors():
    """
    List all world actors from Foundry (not compendium).

    Returns:
        List of actors with uuid, id, and name
    """
    result = await list_actors(timeout=10.0)

    if result.success:
        return {
            "success": True,
            "count": len(result.actors) if result.actors else 0,
            "actors": [
                {"uuid": a.uuid, "id": a.id, "name": a.name}
                for a in (result.actors or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.delete("/api/foundry/actors/duplicates")
async def delete_duplicate_actors():
    """
    Delete all actors with duplicate names, keeping one of each.

    Returns:
        Summary of deleted actors
    """
    from collections import defaultdict

    # Get all actors
    result = await list_actors(timeout=10.0)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    actors = result.actors or []

    # Group by name
    by_name = defaultdict(list)
    for actor in actors:
        by_name[actor.name].append(actor)

    # Find and delete duplicates
    deleted = []
    failed = []

    for name, actor_list in by_name.items():
        if len(actor_list) > 1:
            # Keep first, delete rest
            for actor in actor_list[1:]:
                del_result = await delete_actor(actor.uuid, timeout=10.0)
                if del_result.success:
                    deleted.append({"uuid": actor.uuid, "name": actor.name})
                else:
                    failed.append({"uuid": actor.uuid, "name": actor.name, "error": del_result.error})

    return {
        "success": True,
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed
    }


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


class GiveItemsRequest(BaseModel):
    """Request body for giving items to an actor."""
    item_uuids: list[str]


@app.post("/api/foundry/actor/{uuid}/items")
async def give_items_to_actor(uuid: str, request: GiveItemsRequest):
    """
    Add compendium items to an actor via WebSocket.

    Fetches items from compendiums by UUID and adds them to the actor
    using createEmbeddedDocuments.

    Args:
        uuid: The actor UUID (e.g., "Actor.abc123")
        request: GiveItemsRequest with list of item UUIDs

    Returns:
        Success status with items_added count
    """
    from app.websocket import give_items

    result = await give_items(
        actor_uuid=uuid,
        item_uuids=request.item_uuids,
        timeout=30.0
    )

    if result.success:
        return {
            "success": True,
            "actor_uuid": result.actor_uuid,
            "items_added": result.items_added,
            "errors": result.errors
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.post("/api/actors/create")
async def create_actor_endpoint(request: CreateActorRequest):
    """
    Create a D&D actor from a natural language description.

    This endpoint runs the full actor creation pipeline:
    1. Generate stat block text with Gemini
    2. Parse to StatBlock model
    3. Parse to ParsedActorData
    4. Convert to FoundryVTT format
    5. Upload to FoundryVTT via WebSocket

    Args:
        request: CreateActorRequest with description and optional challenge_rating

    Returns:
        Actor creation result with UUID, name, and file paths
    """
    import sys
    import os
    from app.websocket import list_compendium_items, list_files, push_actor

    # Add src to path for imports
    src_path = str(Path(__file__).parent.parent.parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from actors.orchestrate import create_actor_from_description
    from foundry.actors.spell_cache import SpellCache
    from foundry.icon_cache import IconCache

    try:
        # Pre-fetch spells and icons via direct WebSocket (avoids self-deadlock)
        # When running inside FastAPI, we can't make HTTP requests to ourselves
        spell_result = await list_compendium_items(
            document_type="Item",
            sub_type="spell",
            timeout=60.0
        )
        if not spell_result.success:
            raise RuntimeError(f"Failed to fetch spells: {spell_result.error}")

        icon_result = await list_files(
            path="icons",
            source="public",
            recursive=True,
            extensions=[".webp", ".png", ".jpg", ".svg"],
            timeout=120.0
        )
        if not icon_result.success:
            raise RuntimeError(f"Failed to fetch icons: {icon_result.error}")

        # Create pre-loaded caches
        spell_cache = SpellCache()
        spell_cache.load_from_data([
            {"name": r.name, "uuid": r.uuid, "type": r.type, "img": r.img, "pack": r.pack}
            for r in (spell_result.results or [])
        ])

        icon_cache = IconCache()
        icon_cache.load_from_data(icon_result.files or [])

        # WebSocket-based actor upload function (bypasses relay server)
        async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
            """Upload actor via WebSocket instead of relay."""
            result = await push_actor(actor_data, timeout=30.0)
            if not result.success:
                raise RuntimeError(f"Failed to create actor via WebSocket: {result.error}")
            # TODO: Add spell_uuids via WebSocket give message if needed
            return result.uuid

        result = await create_actor_from_description(
            description=request.description,
            challenge_rating=request.challenge_rating,
            output_dir_base=request.output_dir_base or "output/runs",
            spell_cache=spell_cache,
            icon_cache=icon_cache,
            actor_upload_fn=ws_actor_upload
        )

        return {
            "success": True,
            "foundry_uuid": result.foundry_uuid,
            "name": result.stat_block.name if result.stat_block else None,
            "challenge_rating": result.challenge_rating,
            "output_dir": str(result.output_dir) if result.output_dir else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
