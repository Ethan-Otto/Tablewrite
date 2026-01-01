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
    push_actor,
    list_compendium_items,
    list_files,
    give_items,
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
        request: Dict with 'actor' key containing FoundryVTT actor data

    Returns:
        Created actor UUID and name
    """
    actor_data = request.get("actor")
    if not actor_data:
        raise HTTPException(status_code=400, detail="Missing 'actor' field in request")

    result = await push_actor(actor_data, timeout=30.0)

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

    from actors.orchestrate import create_actor_from_description
    from foundry.actors.spell_cache import SpellCache
    from foundry.icon_cache import IconCache

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
            result = await push_actor(actor_data, timeout=30.0)
            if not result.success:
                raise RuntimeError(
                    f"Failed to create actor via WebSocket: {result.error}"
                )
            # TODO: Add spell_uuids via WebSocket give message if needed
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
