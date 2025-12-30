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
            ActorInfo(uuid=a["uuid"], id=a["id"], name=a["name"])
            for a in actors_data
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
                uuid=r["uuid"],
                id=r["id"],
                name=r["name"],
                type=r.get("type"),
                img=r.get("img"),
                pack=r.get("pack")
            )
            for r in results_data
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
