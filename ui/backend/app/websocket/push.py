"""Push notification helpers for broadcasting to Foundry clients."""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .foundry_endpoint import foundry_manager

logger = logging.getLogger(__name__)


@dataclass
class PushResult:
    """Result of pushing an entity to Foundry."""
    success: bool
    uuid: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FetchResult:
    """Result of fetching an entity from Foundry."""
    success: bool
    entity: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class DeleteResult:
    """Result of deleting an entity from Foundry."""
    success: bool
    uuid: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ActorInfo:
    """Basic actor information."""
    uuid: str
    id: str
    name: str


@dataclass
class ListResult:
    """Result of listing entities from Foundry."""
    success: bool
    actors: Optional[List[ActorInfo]] = None
    error: Optional[str] = None


async def push_actor(actor_data: Dict[str, Any], timeout: float = 30.0) -> PushResult:
    """
    Push an actor to all connected Foundry clients and wait for creation result.

    Args:
        actor_data: FoundryVTT actor data object
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        PushResult with UUID if successful, error if failed
    """
    # Send actor data directly - actor_creator.py already formats it as
    # {actor: {...}, spell_uuids: [...], name: ..., cr: ...}
    response = await foundry_manager.broadcast_and_wait(
        {"type": "actor", "data": actor_data},
        timeout=timeout
    )

    if response is None:
        return PushResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actor_created":
        data = response.get("data", {})
        return PushResult(
            success=True,
            uuid=data.get("uuid"),
            id=data.get("id"),
            name=data.get("name")
        )
    elif response.get("type") == "actor_error":
        return PushResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return PushResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def update_actor(
    uuid: str,
    updates: Dict[str, Any],
    timeout: float = 30.0
) -> PushResult:
    """
    Update an existing actor in Foundry via WebSocket.

    Args:
        uuid: Actor UUID (e.g., "Actor.abc123")
        updates: Dictionary of updates to apply (can use nested paths like "system.abilities.str.value")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        PushResult with UUID if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "update_actor", "data": {"uuid": uuid, "updates": updates}},
        timeout=timeout
    )

    if response is None:
        return PushResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actor_updated":
        data = response.get("data", {})
        return PushResult(
            success=True,
            uuid=data.get("uuid"),
            id=data.get("id"),
            name=data.get("name")
        )
    elif response.get("type") == "actor_error":
        return PushResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return PushResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def push_journal(journal_data: Dict[str, Any], timeout: float = 30.0) -> PushResult:
    """
    Push a journal entry to all connected Foundry clients and wait for creation result.

    Args:
        journal_data: FoundryVTT journal data object
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        PushResult with UUID if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "journal", "data": journal_data},
        timeout=timeout
    )

    if response is None:
        return PushResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "journal_created":
        data = response.get("data", {})
        return PushResult(
            success=True,
            uuid=data.get("uuid"),
            id=data.get("id"),
            name=data.get("name")
        )
    elif response.get("type") == "journal_error":
        return PushResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return PushResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def fetch_journal(uuid: str, timeout: float = 30.0) -> FetchResult:
    """
    Fetch a journal from Foundry by UUID.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        FetchResult with entity data if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "get_journal", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return FetchResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "journal_data":
        data = response.get("data", {})
        return FetchResult(
            success=True,
            entity=data.get("entity")
        )
    elif response.get("type") == "journal_error":
        return FetchResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return FetchResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def delete_journal(uuid: str, timeout: float = 10.0) -> DeleteResult:
    """
    Delete a journal entry from Foundry via WebSocket.

    Args:
        uuid: The journal UUID (e.g., "JournalEntry.abc123")
        timeout: Maximum seconds to wait for response

    Returns:
        DeleteResult with success status
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "delete_journal", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return DeleteResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "journal_deleted":
        data = response.get("data", {})
        return DeleteResult(
            success=True,
            uuid=data.get("uuid"),
            name=data.get("name")
        )
    elif response.get("type") == "journal_error":
        return DeleteResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return DeleteResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class JournalInfo:
    """Basic journal information."""
    uuid: str
    id: str
    name: str
    folder: Optional[str]


@dataclass
class JournalListResult:
    """Result of listing journals from Foundry."""
    success: bool
    journals: Optional[List[JournalInfo]] = None
    error: Optional[str] = None


async def list_journals(timeout: float = 30.0) -> JournalListResult:
    """
    List all world journals from Foundry.

    Args:
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        JournalListResult with list of journals if successful
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "list_journals", "data": {}},
        timeout=timeout
    )

    if response is None:
        return JournalListResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "journals_list":
        data = response.get("data", {})
        journals_data = data.get("journals", [])
        journals = [
            JournalInfo(
                uuid=j.get("uuid", ""),
                id=j.get("id", ""),
                name=j.get("name", ""),
                folder=j.get("folder")
            )
            for j in journals_data
            if j.get("uuid") and j.get("id") and j.get("name")
        ]
        return JournalListResult(success=True, journals=journals)
    elif response.get("type") == "journal_error":
        return JournalListResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return JournalListResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def update_journal(
    uuid: str,
    updates: Dict[str, Any],
    timeout: float = 30.0
) -> PushResult:
    """
    Update an existing journal in Foundry via WebSocket.

    Args:
        uuid: Journal UUID (e.g., "JournalEntry.abc123")
        updates: Dictionary of updates to apply
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        PushResult with UUID if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "update_journal", "data": {"uuid": uuid, "updates": updates}},
        timeout=timeout
    )

    if response is None:
        return PushResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "journal_updated":
        data = response.get("data", {})
        return PushResult(
            success=True,
            uuid=data.get("uuid"),
            id=data.get("id"),
            name=data.get("name")
        )
    elif response.get("type") == "journal_error":
        return PushResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return PushResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def push_scene(scene_data: Dict[str, Any], timeout: float = 30.0) -> PushResult:
    """
    Push a scene to all connected Foundry clients and wait for creation result.

    Args:
        scene_data: FoundryVTT scene data object
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        PushResult with UUID if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "scene", "data": scene_data},
        timeout=timeout
    )

    if response is None:
        return PushResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "scene_created":
        data = response.get("data", {})
        return PushResult(
            success=True,
            uuid=data.get("uuid"),
            id=data.get("id"),
            name=data.get("name")
        )
    elif response.get("type") == "scene_error":
        return PushResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return PushResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def fetch_scene(uuid: str, timeout: float = 30.0) -> FetchResult:
    """
    Fetch a scene from Foundry by UUID.

    Args:
        uuid: The scene UUID (e.g., "Scene.abc123")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        FetchResult with entity data if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "get_scene", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return FetchResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "scene_data":
        data = response.get("data", {})
        return FetchResult(
            success=True,
            entity=data.get("entity")
        )
    elif response.get("type") == "scene_error":
        return FetchResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return FetchResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def delete_scene(uuid: str, timeout: float = 30.0) -> DeleteResult:
    """
    Delete a scene from Foundry by UUID.

    Args:
        uuid: The scene UUID (e.g., "Scene.abc123")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        DeleteResult with success status and deleted entity info
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "delete_scene", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return DeleteResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "scene_deleted":
        data = response.get("data", {})
        return DeleteResult(
            success=True,
            uuid=data.get("uuid"),
            name=data.get("name")
        )
    elif response.get("type") == "scene_error":
        return DeleteResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return DeleteResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def fetch_actor(uuid: str, timeout: float = 30.0) -> FetchResult:
    """
    Fetch an actor from Foundry by UUID.

    Args:
        uuid: The actor UUID (e.g., "Actor.vKEhnoBxM7unbhAL")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        FetchResult with entity data if successful, error if failed
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "get_actor", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return FetchResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actor_data":
        data = response.get("data", {})
        return FetchResult(
            success=True,
            entity=data.get("entity")
        )
    elif response.get("type") == "actor_error":
        return FetchResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return FetchResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def delete_actor(uuid: str, timeout: float = 30.0) -> DeleteResult:
    """
    Delete an actor from Foundry by UUID.

    Args:
        uuid: The actor UUID (e.g., "Actor.vKEhnoBxM7unbhAL")
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        DeleteResult with success status and deleted entity info
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "delete_actor", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return DeleteResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actor_deleted":
        data = response.get("data", {})
        return DeleteResult(
            success=True,
            uuid=data.get("uuid"),
            name=data.get("name")
        )
    elif response.get("type") == "actor_error":
        return DeleteResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return DeleteResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def list_actors(timeout: float = 30.0) -> ListResult:
    """
    List all world actors from Foundry (not compendium actors).

    Args:
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        ListResult with list of actors if successful
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "list_actors", "data": {}},
        timeout=timeout
    )

    if response is None:
        return ListResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actors_list":
        data = response.get("data", {})
        actors_data = data.get("actors", [])
        actors = [
            ActorInfo(uuid=a.get("uuid", ""), id=a.get("id", ""), name=a.get("name", ""))
            for a in actors_data
            if a.get("uuid") and a.get("id") and a.get("name")
        ]
        return ListResult(success=True, actors=actors)
    elif response.get("type") == "actor_error":
        return ListResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return ListResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class SearchResultItem:
    """Item from search results."""
    uuid: str
    id: str
    name: str
    type: Optional[str] = None
    img: Optional[str] = None
    pack: Optional[str] = None
    system: Optional[Dict[str, Any]] = None  # For spell level, school, etc.


@dataclass
class SearchResult:
    """Result of searching items via WebSocket."""
    success: bool
    results: Optional[List[SearchResultItem]] = None
    error: Optional[str] = None


async def search_items(
    query: str,
    document_type: str = "Item",
    sub_type: Optional[str] = None,
    timeout: float = 30.0
) -> SearchResult:
    """
    Search for items in Foundry compendiums via WebSocket.

    Args:
        query: Search query string (case-insensitive contains match)
        document_type: Document type to search (default: "Item")
        sub_type: Optional subtype filter (e.g., "spell", "weapon")
        timeout: Maximum seconds to wait for response

    Returns:
        SearchResult with list of matching items
    """
    data = {"query": query, "documentType": document_type}
    if sub_type:
        data["subType"] = sub_type

    response = await foundry_manager.broadcast_and_wait(
        {"type": "search_items", "data": data},
        timeout=timeout
    )

    if response is None:
        return SearchResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "items_found":
        data = response.get("data", {})
        results_data = data.get("results", [])
        results = [
            SearchResultItem(
                uuid=r.get("uuid", ""),
                id=r.get("id", ""),
                name=r.get("name", ""),
                type=r.get("type"),
                img=r.get("img"),
                pack=r.get("pack")
            )
            for r in results_data
            if r.get("uuid") and r.get("id") and r.get("name")
        ]
        return SearchResult(success=True, results=results)
    elif response.get("type") == "search_error":
        return SearchResult(
            success=False,
            error=response.get("error", "Unknown search error")
        )
    else:
        return SearchResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class FileListResult:
    """Result of listing files via WebSocket."""
    success: bool
    files: Optional[List[str]] = None
    error: Optional[str] = None


@dataclass
class CompendiumListResult:
    """Result of listing compendium items via WebSocket."""
    success: bool
    results: Optional[List[SearchResultItem]] = None
    error: Optional[str] = None


async def list_compendium_items(
    document_type: str = "Item",
    sub_type: Optional[str] = None,
    timeout: float = 60.0
) -> CompendiumListResult:
    """
    List ALL items of a specific type from Foundry compendiums.

    Much more efficient than multiple search queries - fetches everything in one request.

    Args:
        document_type: Document type to list (default: "Item")
        sub_type: Optional subtype filter (e.g., "spell", "weapon")
        timeout: Maximum seconds to wait for response

    Returns:
        CompendiumListResult with list of all matching items
    """
    data = {"documentType": document_type}
    if sub_type:
        data["subType"] = sub_type

    response = await foundry_manager.broadcast_and_wait(
        {"type": "list_compendium_items", "data": data},
        timeout=timeout
    )

    if response is None:
        return CompendiumListResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "compendium_items_list":
        data = response.get("data", {})
        results_data = data.get("results", [])
        results = [
            SearchResultItem(
                uuid=r["uuid"],
                id=r["id"],
                name=r["name"],
                type=r.get("type"),
                img=r.get("img"),
                pack=r.get("pack"),
                system=r.get("system")  # Include spell level, school, etc.
            )
            for r in results_data
        ]
        return CompendiumListResult(success=True, results=results)
    elif response.get("type") == "compendium_items_error":
        return CompendiumListResult(
            success=False,
            error=response.get("error", "Unknown error")
        )
    else:
        return CompendiumListResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class GiveItemsResult:
    """Result of giving items to an actor."""
    success: bool
    actor_uuid: Optional[str] = None
    items_added: Optional[int] = None
    errors: Optional[List[str]] = None
    error: Optional[str] = None


async def give_items(
    actor_uuid: str,
    item_uuids: List[str],
    timeout: float = 30.0
) -> GiveItemsResult:
    """
    Give compendium items to an actor via WebSocket.

    Fetches items from compendiums by UUID and adds them to the actor
    using createEmbeddedDocuments.

    Args:
        actor_uuid: The actor UUID (e.g., "Actor.abc123")
        item_uuids: List of compendium item UUIDs to add
        timeout: Maximum seconds to wait for response

    Returns:
        GiveItemsResult with items_added count if successful
    """
    if not item_uuids:
        return GiveItemsResult(
            success=True,
            actor_uuid=actor_uuid,
            items_added=0
        )

    response = await foundry_manager.broadcast_and_wait(
        {"type": "give_items", "data": {"actor_uuid": actor_uuid, "item_uuids": item_uuids}},
        timeout=timeout
    )

    if response is None:
        return GiveItemsResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "items_given":
        data = response.get("data", {})
        return GiveItemsResult(
            success=True,
            actor_uuid=data.get("actor_uuid"),
            items_added=data.get("items_added"),
            errors=data.get("errors")
        )
    elif response.get("type") == "give_error":
        return GiveItemsResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return GiveItemsResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class FileUploadResult:
    """Result of uploading a file to Foundry."""
    success: bool
    path: Optional[str] = None
    error: Optional[str] = None


async def upload_file(
    filename: str,
    content: str,
    destination: str = "uploaded-maps",
    timeout: float = 60.0
) -> FileUploadResult:
    """
    Upload a file to FoundryVTT world folder via WebSocket.

    Args:
        filename: Name of the file (e.g., "castle.webp")
        content: Base64-encoded file content
        destination: Subdirectory in world folder (default: "uploaded-maps")
        timeout: Maximum seconds to wait for response

    Returns:
        FileUploadResult with Foundry-relative path if successful
    """
    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "upload_file",
            "data": {
                "filename": filename,
                "content": content,
                "destination": destination
            }
        },
        timeout=timeout
    )

    if response is None:
        return FileUploadResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "file_uploaded":
        data = response.get("data", {})
        return FileUploadResult(
            success=True,
            path=data.get("path")
        )
    elif response.get("type") == "file_error":
        return FileUploadResult(
            success=False,
            error=response.get("error", "Unknown upload error")
        )
    else:
        return FileUploadResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def list_files(
    path: str,
    source: str = "public",
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    timeout: float = 60.0
) -> FileListResult:
    """
    List files in a Foundry directory via WebSocket.

    Args:
        path: Directory path to browse (e.g., "icons")
        source: File source ("data", "public", or "s3")
        recursive: Whether to recurse into subdirectories
        extensions: Optional list of file extensions to filter
        timeout: Maximum seconds to wait for response

    Returns:
        FileListResult with list of file paths
    """
    data = {
        "path": path,
        "source": source,
        "recursive": recursive
    }
    if extensions:
        data["extensions"] = extensions

    response = await foundry_manager.broadcast_and_wait(
        {"type": "list_files", "data": data},
        timeout=timeout
    )

    if response is None:
        return FileListResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "files_list":
        data = response.get("data", {})
        return FileListResult(
            success=True,
            files=data.get("files", [])
        )
    elif response.get("type") == "files_error":
        return FileListResult(
            success=False,
            error=response.get("error", "Unknown error")
        )
    else:
        return FileListResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class FolderResult:
    """Result of getting or creating a folder."""
    success: bool
    folder_id: Optional[str] = None
    folder_uuid: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FolderInfo:
    """Information about a folder."""
    id: str
    name: str
    type: str
    parent: Optional[str]


@dataclass
class ListFoldersResult:
    """Result of listing folders."""
    success: bool
    folders: Optional[List[FolderInfo]] = None
    error: Optional[str] = None


@dataclass
class CustomItemDef:
    """Definition of a custom item to add to an actor."""
    name: str
    type: str  # 'weapon' or 'feat'
    description: str
    damage_formula: Optional[str] = None  # e.g., "2d6+3"
    damage_type: Optional[str] = None  # e.g., "psychic"
    attack_bonus: Optional[int] = None
    range: Optional[int] = None
    activation: Optional[str] = None  # "action", "bonus", "reaction", "passive"
    save_dc: Optional[int] = None
    save_ability: Optional[str] = None  # "dex", "con", "wis", etc.


@dataclass
class AddCustomItemsResult:
    """Result of adding custom items to an actor."""
    success: bool
    items_added: Optional[int] = None
    error: Optional[str] = None


async def add_custom_items(
    actor_uuid: str,
    items: List[dict],
    timeout: float = 30.0
) -> AddCustomItemsResult:
    """
    Add custom items (attacks, feats) to an actor via WebSocket.

    Unlike give_items which fetches from compendiums, this creates new items
    with custom properties.

    Args:
        actor_uuid: The actor UUID (e.g., "Actor.abc123")
        items: List of item definitions with name, type, description, etc.
        timeout: Maximum seconds to wait for response

    Returns:
        AddCustomItemsResult with items_added count if successful
    """
    if not items:
        return AddCustomItemsResult(
            success=True,
            items_added=0
        )

    response = await foundry_manager.broadcast_and_wait(
        {"type": "add_custom_items", "data": {"actor_uuid": actor_uuid, "items": items}},
        timeout=timeout
    )

    if response is None:
        return AddCustomItemsResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "custom_items_added":
        data = response.get("data", {})
        return AddCustomItemsResult(
            success=True,
            items_added=data.get("items_added")
        )
    elif response.get("type") == "custom_items_error":
        return AddCustomItemsResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return AddCustomItemsResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def get_or_create_folder(
    name: str,
    folder_type: str,
    parent: Optional[str] = None,
    timeout: float = 5.0
) -> FolderResult:
    """
    Get or create a folder in Foundry.

    Args:
        name: Folder name (e.g., "Tablewrite")
        folder_type: Document type ("Actor", "Scene", "JournalEntry", "Item")
        parent: Optional parent folder ID for nested folders
        timeout: Maximum seconds to wait for response

    Returns:
        FolderResult with folder_id on success
    """
    data = {
        "name": name,
        "type": folder_type
    }
    if parent:
        data["parent"] = parent

    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "get_or_create_folder",
            "data": data
        },
        timeout=timeout
    )

    if response is None:
        return FolderResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "folder_result":
        data = response.get("data", {})
        return FolderResult(
            success=True,
            folder_id=data.get("folder_id"),
            folder_uuid=data.get("folder_uuid"),
            name=data.get("name")
        )
    elif response.get("type") == "folder_error":
        return FolderResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return FolderResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def list_folders(
    folder_type: Optional[str] = None,
    timeout: float = 5.0
) -> ListFoldersResult:
    """
    List all folders in Foundry, optionally filtered by type.

    Args:
        folder_type: Optional document type ("Actor", "Scene", "JournalEntry", "Item")
        timeout: Maximum seconds to wait for response

    Returns:
        ListFoldersResult with list of folders
    """
    data = {}
    if folder_type:
        data["type"] = folder_type

    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "list_folders",
            "data": data
        },
        timeout=timeout
    )

    if response is None:
        return ListFoldersResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "folders_list":
        resp_data = response.get("data", {})
        folders = [
            FolderInfo(
                id=f["id"],
                name=f["name"],
                type=f["type"],
                parent=f.get("parent")
            )
            for f in resp_data.get("folders", [])
        ]
        return ListFoldersResult(
            success=True,
            folders=folders
        )
    elif response.get("type") == "folder_error":
        return ListFoldersResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return ListFoldersResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


@dataclass
class DeleteFolderResult:
    """Result of deleting a folder."""
    success: bool
    deleted_count: Optional[int] = None
    folder_name: Optional[str] = None
    error: Optional[str] = None


async def delete_folder(
    folder_id: str,
    delete_contents: bool = True,
    timeout: float = 30.0
) -> DeleteFolderResult:
    """
    Delete a folder from Foundry, optionally with all its contents.

    Args:
        folder_id: The folder ID to delete
        delete_contents: If True, delete all documents in the folder first (default: True)
        timeout: Maximum seconds to wait for response

    Returns:
        DeleteFolderResult with deleted_count if successful
    """
    data = {
        "folder_id": folder_id,
        "delete_contents": delete_contents
    }

    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "delete_folder",
            "data": data
        },
        timeout=timeout
    )

    if response is None:
        return DeleteFolderResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "folder_deleted":
        resp_data = response.get("data", {})
        return DeleteFolderResult(
            success=True,
            deleted_count=resp_data.get("deleted_count"),
            folder_name=resp_data.get("folder_name")
        )
    elif response.get("type") == "folder_error":
        return DeleteFolderResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return DeleteFolderResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )


async def broadcast_progress(
    stage: str,
    message: str,
    progress: Optional[int] = None,
    module_name: Optional[str] = None
) -> None:
    """
    Broadcast a progress update to all connected Foundry clients.

    Fire-and-forget - does not wait for a response.

    Args:
        stage: Current processing stage (e.g., "splitting_pdf", "extracting_actors")
        message: Human-readable progress message
        progress: Optional progress percentage (0-100)
        module_name: Optional module name being processed
    """
    data: Dict[str, Any] = {
        "stage": stage,
        "message": message
    }
    if progress is not None:
        data["progress"] = progress
    if module_name is not None:
        data["module_name"] = module_name

    await foundry_manager.broadcast({
        "type": "module_progress",
        "data": data
    })


import asyncio
import concurrent.futures

# Store reference to main event loop for cross-thread communication
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store reference to main event loop for sync-to-async calls."""
    global _main_loop
    _main_loop = loop


def broadcast_progress_sync(
    stage: str,
    message: str,
    progress: Optional[int] = None,
    module_name: Optional[str] = None
) -> None:
    """
    Synchronous version of broadcast_progress for use from thread pools.

    Schedules the async broadcast on the main event loop using
    run_coroutine_threadsafe.

    Args:
        stage: Current processing stage
        message: Human-readable progress message
        progress: Optional progress percentage (0-100)
        module_name: Optional module name being processed
    """
    global _main_loop
    if _main_loop is None:
        logger.warning("Main loop not set, cannot broadcast progress")
        return

    try:
        future = asyncio.run_coroutine_threadsafe(
            broadcast_progress(stage, message, progress, module_name),
            _main_loop
        )
        # Don't wait for result - fire and forget
        # But set a short timeout to catch immediate errors
        try:
            future.result(timeout=0.1)
        except concurrent.futures.TimeoutError:
            pass  # Expected - we don't want to block
    except Exception as e:
        logger.warning(f"Failed to broadcast progress: {e}")
