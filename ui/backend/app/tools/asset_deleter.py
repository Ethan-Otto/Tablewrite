"""Asset deletion tool - delete Tablewrite assets via natural language."""
import logging
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
        # TODO: Implement in next task
        return ToolResponse(
            type="error",
            message="Not implemented yet",
            data=None
        )
