"""Asset deletion tool - delete Tablewrite assets via natural language."""
import logging
from dataclasses import dataclass
from typing import List, Optional
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket.push import (
    fetch_actor, fetch_scene, fetch_journal, list_folders,
    delete_actor, delete_scene, delete_journal, delete_folder,
    list_actors, list_scenes, list_journals, remove_actor_items
)

logger = logging.getLogger(__name__)


async def is_in_tablewrite_folder(entity_uuid: str, entity_type: str) -> bool:
    """
    Check if an entity is within a Tablewrite folder hierarchy.

    Args:
        entity_uuid: UUID of the entity (e.g., "Actor.abc123")
        entity_type: Type of entity ("actor", "journal", "scene")

    Returns:
        True if entity is in Tablewrite folder hierarchy, False otherwise
    """
    # Fetch the entity to get its folder
    if entity_type == "actor":
        result = await fetch_actor(entity_uuid)
    elif entity_type == "scene":
        result = await fetch_scene(entity_uuid)
    elif entity_type == "journal":
        result = await fetch_journal(entity_uuid)
    else:
        return False

    if not result.success or not result.entity:
        return False

    # Get folder ID from entity
    folder_id = result.entity.get("folder")
    if not folder_id:
        return False

    # Get all folders and build hierarchy
    folders_result = await list_folders()
    if not folders_result.success or not folders_result.folders:
        return False

    # Build folder lookup
    folder_map = {f.id: f for f in folders_result.folders}

    # Trace up the hierarchy looking for "Tablewrite"
    current_folder_id = folder_id
    while current_folder_id:
        folder = folder_map.get(current_folder_id)
        if not folder:
            return False
        if folder.name == "Tablewrite":
            return True
        current_folder_id = folder.parent

    return False


@dataclass
class EntityMatch:
    """A matched entity from search."""
    uuid: str
    name: str
    entity_type: str
    folder_id: Optional[str] = None


async def find_entities(
    entity_type: str,
    search_query: Optional[str] = None,
    uuid: Optional[str] = None,
    folder_name: Optional[str] = None
) -> List[EntityMatch]:
    """
    Find entities matching the search criteria.

    Args:
        entity_type: "actor", "scene", "journal", or "folder"
        search_query: Name to search for (case-insensitive partial match), or "*" for all
        uuid: Specific UUID (takes precedence over search_query)
        folder_name: Optional Tablewrite subfolder to limit search

    Returns:
        List of matching entities that are in Tablewrite hierarchy
    """
    # If UUID provided, fetch entity once and validate Tablewrite membership
    if uuid:
        # Fetch entity first (avoid duplicate fetch in is_in_tablewrite_folder)
        if entity_type == "actor":
            result = await fetch_actor(uuid)
        elif entity_type == "scene":
            result = await fetch_scene(uuid)
        elif entity_type == "journal":
            result = await fetch_journal(uuid)
        else:
            return []

        if not result.success or not result.entity:
            return []

        # Validate Tablewrite membership using fetched data
        folder_id = result.entity.get("folder")
        if not folder_id:
            return []

        # Get folders and check hierarchy
        folders_result = await list_folders()
        if not folders_result.success or not folders_result.folders:
            return []

        folder_map = {f.id: f for f in folders_result.folders}
        current = folder_id
        in_tablewrite = False
        while current:
            folder = folder_map.get(current)
            if not folder:
                break
            if folder.name == "Tablewrite":
                in_tablewrite = True
                break
            current = folder.parent

        if in_tablewrite:
            return [EntityMatch(
                uuid=uuid,
                name=result.entity.get("name", "Unknown"),
                entity_type=entity_type,
                folder_id=folder_id
            )]
        return []

    # List all entities of type
    if entity_type == "actor":
        list_result = await list_actors()
        entities = list_result.actors or []
    elif entity_type == "scene":
        list_result = await list_scenes()
        entities = list_result.scenes or []
    elif entity_type == "journal":
        list_result = await list_journals()
        entities = list_result.journals or []
    else:
        return []

    # Get folder hierarchy for filtering
    folders_result = await list_folders()
    folder_map = {f.id: f for f in (folders_result.folders or [])}

    def is_in_tablewrite_hierarchy(folder_id: Optional[str], target_subfolder: Optional[str] = None) -> bool:
        """Check if folder is in Tablewrite hierarchy, optionally under specific subfolder."""
        if not folder_id:
            return False

        path = []
        current = folder_id
        while current:
            folder = folder_map.get(current)
            if not folder:
                return False
            path.append(folder.name)
            if folder.name == "Tablewrite":
                # Found Tablewrite - check subfolder if specified
                if target_subfolder:
                    # Path is built from entity folder up to Tablewrite
                    # So if entity is in "Lost Mine" -> "Tablewrite", path = ["Lost Mine", "Tablewrite"]
                    # We want to check if "Lost Mine" is in the path (direct child of Tablewrite)
                    return len(path) >= 2 and path[-2] == target_subfolder
                return True
            current = folder.parent
        return False

    # Filter and search
    results = []
    search_lower = search_query.lower() if search_query and search_query != "*" else None

    for entity in entities:
        # Get folder_id from entity (all entity types include folder in list results)
        entity_folder = getattr(entity, 'folder', None)

        # Check Tablewrite hierarchy
        if not is_in_tablewrite_hierarchy(entity_folder, folder_name):
            continue

        # Check name match
        if search_lower and search_lower not in entity.name.lower():
            continue

        results.append(EntityMatch(
            uuid=entity.uuid,
            name=entity.name,
            entity_type=entity_type,
            folder_id=entity_folder
        ))

    return results


class AssetDeleterTool(BaseTool):
    """Tool for deleting Tablewrite assets (actors, journals, scenes, folders, actor items)."""

    @property
    def name(self) -> str:
        return "delete_assets"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="delete_assets",
            description=(
                "Delete Tablewrite assets from FoundryVTT. Use when user asks to delete, remove, "
                "clear, or clean up actors, journals, scenes, folders, or items within actors. "
                "ONLY works on assets in Tablewrite folders (safety constraint). "
                "For bulk operations (deleting multiple items), first call without confirm_bulk "
                "to see what will be deleted, then call again with confirm_bulk=true to execute."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["actor", "journal", "scene", "folder", "actor_item"],
                        "description": "Type of entity to delete"
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Name or partial name to search for (case-insensitive). Use '*' for all items in a folder."
                    },
                    "uuid": {
                        "type": "string",
                        "description": "Specific UUID to delete (e.g., 'Actor.abc123'). Takes precedence over search_query."
                    },
                    "folder_name": {
                        "type": "string",
                        "description": "Limit deletion to specific Tablewrite subfolder (e.g., 'Lost Mine of Phandelver')"
                    },
                    "actor_uuid": {
                        "type": "string",
                        "description": "For actor_item deletion: the actor UUID containing the items to remove"
                    },
                    "item_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For actor_item deletion: names of items/spells/actions to remove from actor"
                    },
                    "confirm_bulk": {
                        "type": "boolean",
                        "description": "Set to true to confirm bulk deletion (required when deleting more than 1 item)"
                    }
                },
                "required": ["entity_type"]
            }
        )

    async def execute(
        self,
        entity_type: str,
        search_query: Optional[str] = None,
        uuid: Optional[str] = None,
        folder_name: Optional[str] = None,
        actor_uuid: Optional[str] = None,
        item_names: Optional[List[str]] = None,
        confirm_bulk: bool = False,
        **kwargs
    ) -> ToolResponse:
        """Execute the deletion.

        Args:
            entity_type: Type of entity to delete (actor, journal, scene, folder, actor_item)
            search_query: Name or partial name to search for
            uuid: Specific UUID to delete (takes precedence over search_query)
            folder_name: Limit deletion to specific Tablewrite subfolder
            actor_uuid: For actor_item deletion - the actor containing items
            item_names: For actor_item deletion - names of items to remove
            confirm_bulk: Set to true to confirm bulk deletion
            **kwargs: Additional arguments (ignored)

        Returns:
            ToolResponse with result of deletion operation
        """
        logger.info(f"AssetDeleterTool.execute: entity_type={entity_type}, search_query={search_query}, uuid={uuid}")

        # Handle actor_item deletion separately
        if entity_type == "actor_item":
            return await self._delete_actor_items(actor_uuid, item_names)

        # Find matching entities
        entities = await find_entities(entity_type, search_query, uuid, folder_name)

        if not entities:
            return ToolResponse(
                type="text",
                message=f"No {entity_type} matching '{search_query or uuid}' found in Tablewrite folders.",
                data={"found": 0}
            )

        # Single item - delete immediately
        if len(entities) == 1:
            entity = entities[0]
            success = await self._delete_entity(entity)
            if success:
                return ToolResponse(
                    type="text",
                    message=f"Deleted {entity_type} '{entity.name}'",
                    data={"deleted": [{"uuid": entity.uuid, "name": entity.name}]}
                )
            else:
                return ToolResponse(
                    type="error",
                    message=f"Failed to delete {entity_type} '{entity.name}'",
                    data=None
                )

        # Multiple items - require confirmation
        if not confirm_bulk:
            names = [e.name for e in entities]
            return ToolResponse(
                type="confirmation_required",
                message=f"Found {len(entities)} {entity_type}s to delete:\n" +
                        "\n".join(f"- {name}" for name in names[:10]) +
                        (f"\n... and {len(names) - 10} more" if len(names) > 10 else "") +
                        "\n\nSay 'confirm' or 'yes, delete them' to proceed.",
                data={
                    "pending_deletion": {
                        "entity_type": entity_type,
                        "count": len(entities),
                        "entities": [{"uuid": e.uuid, "name": e.name} for e in entities]
                    }
                }
            )

        # Confirmed bulk delete
        deleted = []
        failed = []
        for entity in entities:
            if await self._delete_entity(entity):
                deleted.append(entity)
            else:
                failed.append(entity)

        message = f"Deleted {len(deleted)} {entity_type}(s)"
        if failed:
            message += f", {len(failed)} failed"

        return ToolResponse(
            type="text",
            message=message,
            data={
                "deleted": [{"uuid": e.uuid, "name": e.name} for e in deleted],
                "failed": [{"uuid": e.uuid, "name": e.name} for e in failed]
            }
        )

    async def _delete_entity(self, entity: EntityMatch) -> bool:
        """Delete a single entity. Returns True on success."""
        try:
            if entity.entity_type == "actor":
                result = await delete_actor(entity.uuid)
            elif entity.entity_type == "scene":
                result = await delete_scene(entity.uuid)
            elif entity.entity_type == "journal":
                result = await delete_journal(entity.uuid)
            elif entity.entity_type == "folder":
                result = await delete_folder(entity.uuid, delete_contents=True)
            else:
                return False

            return result.success
        except Exception as e:
            logger.error(f"Failed to delete {entity.entity_type} {entity.uuid}: {e}")
            return False

    async def _delete_actor_items(
        self,
        actor_uuid: Optional[str],
        item_names: Optional[List[str]]
    ) -> ToolResponse:
        """Delete items from an actor."""
        if not actor_uuid:
            return ToolResponse(
                type="error",
                message="actor_uuid is required for actor_item deletion",
                data=None
            )
        if not item_names:
            return ToolResponse(
                type="error",
                message="item_names is required for actor_item deletion",
                data=None
            )

        # Verify actor is in Tablewrite
        if not await is_in_tablewrite_folder(actor_uuid, "actor"):
            return ToolResponse(
                type="error",
                message="Cannot remove items: actor is not in a Tablewrite folder",
                data=None
            )

        result = await remove_actor_items(actor_uuid, item_names)
        if result.success:
            if result.items_removed == 0:
                return ToolResponse(
                    type="text",
                    message=f"No items matching {item_names} found on actor",
                    data={"removed": 0}
                )
            return ToolResponse(
                type="text",
                message=f"Removed {result.items_removed} item(s) from actor: {', '.join(result.removed_names or [])}",
                data={"removed": result.items_removed, "names": result.removed_names}
            )
        else:
            return ToolResponse(
                type="error",
                message=f"Failed to remove items: {result.error}",
                data=None
            )
