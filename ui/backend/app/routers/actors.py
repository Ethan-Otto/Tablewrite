"""Actor-related API endpoints."""

from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.websocket import (
    fetch_actor,
    delete_actor,
    list_actors,
    list_scenes,
    push_actor,
    update_actor,
    list_compendium_items,
    list_files,
    give_items,
    list_folders,
    get_or_create_folder,
    remove_actor_items,
)

router = APIRouter(prefix="/api", tags=["actors"])


class CreateActorRequest(BaseModel):
    """Request body for actor creation."""

    description: str
    challenge_rating: float = 1.0
    output_dir_base: Optional[str] = None


class GiveItemsRequest(BaseModel):
    """Request body for giving items to an actor."""

    item_uuids: list[str]


class RemoveItemsRequest(BaseModel):
    """Request body for removing items from an actor."""

    item_names: list[str]


@router.get("/foundry/actor/{uuid}")
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
            "entity": result.entity,
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


class UpdateActorRequest(BaseModel):
    """Request body for updating an actor."""
    updates: dict


@router.patch("/foundry/actor/{uuid}")
async def update_actor_by_uuid(uuid: str, request: UpdateActorRequest):
    """
    Update an actor in Foundry by UUID via WebSocket.

    Args:
        uuid: The actor UUID (e.g., "Actor.vKEhnoBxM7unbhAL")
        request: UpdateActorRequest with updates dict

    Returns:
        Updated actor info
    """
    result = await update_actor(uuid, request.updates, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.delete("/foundry/actor/{uuid}")
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
            "message": f"Deleted actor: {result.name}",
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@router.post("/foundry/actor")
async def create_actor_raw(request: dict):
    """
    Create a raw actor in Foundry via WebSocket.

    This endpoint accepts a complete FoundryVTT actor JSON structure
    and creates it directly in Foundry. For AI-generated actors from
    descriptions, use /api/actors/create instead.

    Args:
        request: Dict with 'actor' key containing FoundryVTT actor data,
                 and optional 'folder' key for folder ID

    Returns:
        Created actor UUID and name
    """
    actor_data = request.get("actor")
    if not actor_data:
        raise HTTPException(status_code=400, detail="Missing 'actor' field in request")

    # Add folder to actor data if provided
    if request.get("folder"):
        actor_data["folder"] = request.get("folder")

    # Wrap actor data for Foundry handler which expects {"actor": {...}}
    result = await push_actor({"actor": actor_data}, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/foundry/actors")
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
            ],
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/foundry/scenes")
async def get_all_scenes():
    """
    List all world scenes from Foundry.

    Returns:
        List of scenes with uuid, id, and name
    """
    result = await list_scenes(timeout=10.0)

    if result.success:
        return {
            "success": True,
            "count": len(result.scenes) if result.scenes else 0,
            "scenes": [
                {"uuid": s.uuid, "id": s.id, "name": s.name}
                for s in (result.scenes or [])
            ],
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.delete("/foundry/actors/duplicates")
async def delete_duplicate_actors():
    """
    Delete all actors with duplicate names, keeping one of each.

    Returns:
        Summary of deleted actors
    """
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
                    failed.append(
                        {"uuid": actor.uuid, "name": actor.name, "error": del_result.error}
                    )

    return {
        "success": True,
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed,
    }


@router.post("/foundry/actor/{uuid}/items")
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
    result = await give_items(
        actor_uuid=uuid,
        item_uuids=request.item_uuids,
        timeout=30.0,
    )

    if result.success:
        return {
            "success": True,
            "actor_uuid": result.actor_uuid,
            "items_added": result.items_added,
            "errors": result.errors,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.delete("/foundry/actor/{uuid}/items")
async def remove_items_from_actor(uuid: str, request: RemoveItemsRequest):
    """
    Remove items from an actor by name.

    Performs case-insensitive partial matching on item names.

    Args:
        uuid: The actor UUID (e.g., "Actor.abc123")
        request: RemoveItemsRequest with list of item names to remove

    Returns:
        Success status with items_removed count and removed_names
    """
    result = await remove_actor_items(
        actor_uuid=uuid,
        item_names=request.item_names,
        timeout=30.0,
    )

    if result.success:
        return {
            "success": True,
            "actor_uuid": result.actor_uuid,
            "items_removed": result.items_removed,
            "removed_names": result.removed_names,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.post("/actors/create")
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

    # Add src to path for imports
    src_path = str(Path(__file__).parent.parent.parent.parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from actor_pipeline.orchestrate import create_actor_from_description
    from caches import SpellCache, IconCache

    try:
        # Pre-fetch spells and icons via direct WebSocket (avoids self-deadlock)
        # When running inside FastAPI, we can't make HTTP requests to ourselves
        spell_result = await list_compendium_items(
            document_type="Item",
            sub_type="spell",
            timeout=60.0,
        )
        if not spell_result.success:
            raise RuntimeError(f"Failed to fetch spells: {spell_result.error}")

        icon_result = await list_files(
            path="icons",
            source="public",
            recursive=True,
            extensions=[".webp", ".png", ".jpg", ".svg"],
            timeout=120.0,
        )
        if not icon_result.success:
            raise RuntimeError(f"Failed to fetch icons: {icon_result.error}")

        # Create pre-loaded caches
        spell_cache = SpellCache()
        spell_cache.load_from_data(
            [
                {
                    "name": r.name,
                    "uuid": r.uuid,
                    "type": r.type,
                    "img": r.img,
                    "pack": r.pack,
                }
                for r in (spell_result.results or [])
            ]
        )

        icon_cache = IconCache()
        icon_cache.load_from_data(icon_result.files or [])

        # WebSocket-based actor upload function (bypasses relay server)
        async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
            """Upload actor via WebSocket instead of relay."""
            # Wrap in expected format: {actor: {...}, spell_uuids: [...]}
            result = await push_actor({
                "actor": actor_data,
                "spell_uuids": spell_uuids
            }, timeout=30.0)
            if not result.success:
                raise RuntimeError(
                    f"Failed to create actor via WebSocket: {result.error}"
                )
            return result.uuid

        result = await create_actor_from_description(
            description=request.description,
            challenge_rating=request.challenge_rating,
            output_dir_base=request.output_dir_base or "output/runs",
            spell_cache=spell_cache,
            icon_cache=icon_cache,
            actor_upload_fn=ws_actor_upload,
        )

        return {
            "success": True,
            "foundry_uuid": result.foundry_uuid,
            "name": result.stat_block.name if result.stat_block else None,
            "challenge_rating": result.challenge_rating,
            "output_dir": str(result.output_dir) if result.output_dir else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/foundry/folders")
async def list_all_folders(folder_type: Optional[str] = None):
    """
    List all folders in Foundry, optionally filtered by type.

    Args:
        folder_type: Optional document type ("Actor", "Scene", "JournalEntry", "Item")

    Returns:
        List of folders with id, name, type, and parent
    """
    result = await list_folders(folder_type, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "count": len(result.folders) if result.folders else 0,
            "folders": [
                {
                    "id": f.id,
                    "name": f.name,
                    "type": f.type,
                    "parent": f.parent
                }
                for f in (result.folders or [])
            ],
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


class CreateFolderRequest(BaseModel):
    """Request body for folder creation."""

    name: str
    folder_type: str
    parent: Optional[str] = None


@router.post("/foundry/folders")
async def create_folder(request: CreateFolderRequest):
    """
    Create or get a folder in Foundry.

    Args:
        name: Folder name
        folder_type: Document type ("Actor", "Scene", "JournalEntry", "Item")
        parent: Optional parent folder ID

    Returns:
        Created/existing folder info
    """
    from app.websocket import get_or_create_folder

    result = await get_or_create_folder(
        request.name,
        request.folder_type,
        parent=request.parent,
        timeout=10.0
    )

    if result.success:
        return {
            "success": True,
            "folder_id": result.folder_id,
            "folder_uuid": result.folder_uuid,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
