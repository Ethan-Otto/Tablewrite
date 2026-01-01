"""Search, compendium, and file listing API endpoints."""

from fastapi import APIRouter, HTTPException

from app.websocket import search_items, list_compendium_items, list_files

router = APIRouter(prefix="/api/foundry", tags=["search"])


@router.get("/search")
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


@router.get("/compendium")
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


@router.get("/files")
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
