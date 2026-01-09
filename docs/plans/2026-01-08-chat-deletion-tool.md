# Chat Deletion Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable natural language deletion of Tablewrite assets (actors, journals, scenes, folders, actor items) via chat.

**Architecture:** New `AssetDeleterTool` that accepts entity type and search query, validates entities are in Tablewrite folders, and executes deletion. Bulk deletes require confirmation. Built on existing WebSocket delete functions with new `list_scenes` and `remove_actor_items` infrastructure.

**Tech Stack:** Python (FastAPI tool), TypeScript (Foundry handlers), pytest

---

## Task 1: Add `handleListScenes` to Foundry Module

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/handlers/scene.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`

**Step 1: Add SceneInfo and SceneListResult types to index.ts**

Add after line 59 (after `ListResult` interface):

```typescript
export interface SceneInfo {
  uuid: string;
  id: string;
  name: string;
  folder: string | null;
}

export interface SceneListResult {
  success: boolean;
  scenes?: SceneInfo[];
  error?: string;
}
```

**Step 2: Update MessageType in index.ts**

Change line 19 to add `'list_scenes'`:

```typescript
export type MessageType = 'actor' | 'journal' | 'get_journal' | 'delete_journal' | 'list_journals' | 'update_journal' | 'scene' | 'get_scene' | 'delete_scene' | 'list_scenes' | 'get_actor' | 'update_actor' | 'delete_actor' | 'list_actors' | 'give_items' | 'add_custom_items' | 'search_items' | 'get_item' | 'list_compendium_items' | 'list_files' | 'upload_file' | 'get_or_create_folder' | 'list_folders' | 'delete_folder' | 'module_progress' | 'connected' | 'pong';
```

**Step 3: Add handleListScenes export in index.ts**

Update line 7:
```typescript
export { handleSceneCreate, handleGetScene, handleDeleteScene, handleListScenes } from './scene.js';
```

Update line 14:
```typescript
import { handleSceneCreate, handleGetScene, handleDeleteScene, handleListScenes } from './scene.js';
```

**Step 4: Implement handleListScenes in scene.ts**

Add at end of file:

```typescript
/**
 * Handle list scenes request - list all world scenes.
 */
export async function handleListScenes(): Promise<SceneListResult> {
  try {
    const scenes = game.scenes?.contents ?? [];
    const sceneInfos: SceneInfo[] = scenes.map(scene => ({
      uuid: `Scene.${scene.id}`,
      id: scene.id ?? '',
      name: scene.name ?? '',
      folder: scene.folder?.id ?? null
    }));

    console.log('[Tablewrite] Listed', sceneInfos.length, 'scenes');
    return {
      success: true,
      scenes: sceneInfos
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list scenes:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
```

**Step 5: Add SceneListResult import to scene.ts**

Update line 9:
```typescript
import type { CreateResult, GetResult, DeleteResult, SceneInfo, SceneListResult } from './index.js';
```

**Step 6: Add message routing in index.ts handleMessage function**

Find the switch statement in `handleMessage` and add case for `list_scenes`:

```typescript
case 'list_scenes': {
  const result = await handleListScenes();
  return {
    responseType: result.success ? 'scenes_list' : 'scene_error',
    data: result.success ? { scenes: result.scenes } : { error: result.error }
  };
}
```

**Step 7: Build and verify**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors

**Step 8: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/handlers/scene.ts \
        foundry-module/tablewrite-assistant/src/handlers/index.ts
git commit -m "feat(foundry): add handleListScenes handler"
```

---

## Task 2: Add `list_scenes` to Backend WebSocket

**Files:**
- Modify: `ui/backend/app/websocket/push.py`
- Test: `ui/backend/tests/websocket/test_push.py`

**Step 1: Write failing test**

Add to `ui/backend/tests/websocket/test_push.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_scenes(ensure_foundry_connected):
    """Test listing all world scenes."""
    from app.websocket.push import list_scenes

    result = await list_scenes(timeout=10.0)

    assert result.success, f"Failed to list scenes: {result.error}"
    assert result.scenes is not None
    # Scenes list may be empty, that's OK
    assert isinstance(result.scenes, list)
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py::test_list_scenes -v`
Expected: FAIL with "cannot import name 'list_scenes'"

**Step 3: Add SceneInfo and SceneListResult dataclasses**

Add after `ListResult` class (around line 622) in `push.py`:

```python
@dataclass
class SceneInfo:
    """Scene info from list results."""
    uuid: str
    id: str
    name: str
    folder: Optional[str] = None


@dataclass
class SceneListResult:
    """Result of listing scenes via WebSocket."""
    success: bool
    scenes: Optional[List[SceneInfo]] = None
    error: Optional[str] = None
```

**Step 4: Implement list_scenes function**

Add after `list_actors` function (around line 622):

```python
async def list_scenes(timeout: float = 30.0) -> SceneListResult:
    """
    List all world scenes from Foundry.

    Args:
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        SceneListResult with list of scenes if successful
    """
    response = await foundry_manager.broadcast_and_wait(
        {"type": "list_scenes", "data": {}},
        timeout=timeout
    )

    if response is None:
        return SceneListResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "scenes_list":
        data = response.get("data", {})
        scenes_data = data.get("scenes", [])
        scenes = [
            SceneInfo(
                uuid=s.get("uuid", ""),
                id=s.get("id", ""),
                name=s.get("name", ""),
                folder=s.get("folder")
            )
            for s in scenes_data
            if s.get("uuid") and s.get("id") and s.get("name")
        ]
        return SceneListResult(success=True, scenes=scenes)
    elif response.get("type") == "scene_error":
        return SceneListResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return SceneListResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py::test_list_scenes -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/websocket/push.py ui/backend/tests/websocket/test_push.py
git commit -m "feat(backend): add list_scenes WebSocket function"
```

---

## Task 3: Add `handleRemoveActorItems` to Foundry Module

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/handlers/actor.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`

**Step 1: Add RemoveItemsResult type to index.ts**

Add after `SceneListResult`:

```typescript
export interface RemoveItemsResult {
  success: boolean;
  actor_uuid?: string;
  items_removed?: number;
  removed_names?: string[];
  error?: string;
}
```

**Step 2: Update MessageType to add 'remove_actor_items'**

Add to the MessageType union in index.ts.

**Step 3: Add handleRemoveActorItems export**

Update actor exports in index.ts:
```typescript
export { handleActorCreate, handleGetActor, handleUpdateActor, handleDeleteActor, handleListActors, handleGiveItems, handleAddCustomItems, handleRemoveActorItems } from './actor.js';
```

And imports:
```typescript
import { handleActorCreate, handleGetActor, handleUpdateActor, handleDeleteActor, handleListActors, handleGiveItems, handleAddCustomItems, handleRemoveActorItems } from './actor.js';
```

**Step 4: Implement handleRemoveActorItems in actor.ts**

Add at end of file:

```typescript
/**
 * Handle remove items from actor request.
 * Removes embedded items (spells, features, weapons, etc.) from an actor by name.
 * Uses case-insensitive partial matching.
 */
export async function handleRemoveActorItems(data: {
  actor_uuid: string;
  item_names: string[];
}): Promise<RemoveItemsResult> {
  try {
    const { actor_uuid, item_names } = data;

    if (!actor_uuid || !item_names || item_names.length === 0) {
      return {
        success: false,
        error: 'actor_uuid and item_names are required'
      };
    }

    const actor = await fromUuid(actor_uuid) as Actor | null;
    if (!actor) {
      return {
        success: false,
        error: `Actor not found: ${actor_uuid}`
      };
    }

    // Find items matching the names (case-insensitive partial match)
    const itemsToRemove: Item[] = [];
    const removedNames: string[] = [];

    for (const searchName of item_names) {
      const searchLower = searchName.toLowerCase();
      const matchingItems = actor.items.filter(item =>
        item.name?.toLowerCase().includes(searchLower)
      );
      for (const item of matchingItems) {
        if (!itemsToRemove.some(i => i.id === item.id)) {
          itemsToRemove.push(item);
          removedNames.push(item.name ?? 'Unknown');
        }
      }
    }

    if (itemsToRemove.length === 0) {
      return {
        success: true,
        actor_uuid,
        items_removed: 0,
        removed_names: []
      };
    }

    // Delete the items
    const itemIds = itemsToRemove.map(i => i.id).filter((id): id is string => id !== null);
    await actor.deleteEmbeddedDocuments('Item', itemIds);

    console.log('[Tablewrite] Removed', itemIds.length, 'items from actor:', actor.name);

    return {
      success: true,
      actor_uuid,
      items_removed: itemIds.length,
      removed_names: removedNames
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to remove actor items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
```

**Step 5: Add RemoveItemsResult import to actor.ts**

Update the import line:
```typescript
import type { CreateResult, GetResult, DeleteResult, ListResult, GiveResult, RemoveItemsResult } from './index.js';
```

**Step 6: Add message routing in handleMessage**

```typescript
case 'remove_actor_items': {
  const result = await handleRemoveActorItems(message.data as { actor_uuid: string; item_names: string[] });
  return {
    responseType: result.success ? 'actor_items_removed' : 'actor_error',
    data: result
  };
}
```

**Step 7: Build and verify**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors

**Step 8: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/handlers/actor.ts \
        foundry-module/tablewrite-assistant/src/handlers/index.ts
git commit -m "feat(foundry): add handleRemoveActorItems handler"
```

---

## Task 4: Add `remove_actor_items` to Backend WebSocket

**Files:**
- Modify: `ui/backend/app/websocket/push.py`
- Test: `ui/backend/tests/websocket/test_push.py`

**Step 1: Write failing test**

Add to `ui/backend/tests/websocket/test_push.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_actor_items(ensure_foundry_connected, test_folders):
    """Test removing items from an actor."""
    from app.websocket.push import push_actor, remove_actor_items, get_or_create_folder

    # Create a test actor with an item
    folder_result = await get_or_create_folder("tests", "Actor")
    assert folder_result.success

    actor_data = {
        "name": "Test Actor for Item Removal",
        "type": "npc",
        "folder": folder_result.folder_id,
        "items": [
            {"name": "Test Sword", "type": "weapon"},
            {"name": "Test Shield", "type": "equipment"}
        ]
    }
    create_result = await push_actor(actor_data)
    assert create_result.success, f"Failed to create actor: {create_result.error}"

    try:
        # Remove the sword
        result = await remove_actor_items(create_result.uuid, ["sword"], timeout=10.0)

        assert result.success, f"Failed to remove items: {result.error}"
        assert result.items_removed == 1
        assert "Test Sword" in result.removed_names
    finally:
        # Cleanup
        from app.websocket.push import delete_actor
        await delete_actor(create_result.uuid)
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py::test_remove_actor_items -v`
Expected: FAIL with "cannot import name 'remove_actor_items'"

**Step 3: Add RemoveItemsResult dataclass**

Add in `push.py`:

```python
@dataclass
class RemoveItemsResult:
    """Result of removing items from an actor."""
    success: bool
    actor_uuid: Optional[str] = None
    items_removed: Optional[int] = None
    removed_names: Optional[List[str]] = None
    error: Optional[str] = None
```

**Step 4: Implement remove_actor_items function**

```python
async def remove_actor_items(
    actor_uuid: str,
    item_names: List[str],
    timeout: float = 30.0
) -> RemoveItemsResult:
    """
    Remove items from an actor by name (case-insensitive partial match).

    Args:
        actor_uuid: The actor UUID (e.g., "Actor.abc123")
        item_names: List of item names to search for and remove
        timeout: Maximum seconds to wait for Foundry response

    Returns:
        RemoveItemsResult with count and names of removed items
    """
    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "remove_actor_items",
            "data": {"actor_uuid": actor_uuid, "item_names": item_names}
        },
        timeout=timeout
    )

    if response is None:
        return RemoveItemsResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "actor_items_removed":
        data = response.get("data", {})
        return RemoveItemsResult(
            success=True,
            actor_uuid=data.get("actor_uuid"),
            items_removed=data.get("items_removed", 0),
            removed_names=data.get("removed_names", [])
        )
    elif response.get("type") == "actor_error":
        return RemoveItemsResult(
            success=False,
            error=response.get("error", "Unknown error from Foundry")
        )
    else:
        return RemoveItemsResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py::test_remove_actor_items -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/websocket/push.py ui/backend/tests/websocket/test_push.py
git commit -m "feat(backend): add remove_actor_items WebSocket function"
```

---

## Task 5: Create AssetDeleterTool - Core Structure

**Files:**
- Create: `ui/backend/app/tools/asset_deleter.py`
- Modify: `ui/backend/app/tools/__init__.py`
- Test: `ui/backend/tests/tools/test_asset_deleter.py`

**Step 1: Write failing test for tool schema**

Create `ui/backend/tests/tools/test_asset_deleter.py`:

```python
"""Tests for AssetDeleterTool."""
import pytest


class TestAssetDeleterToolSchema:
    """Test tool schema validation."""

    def test_tool_has_correct_name(self):
        """Tool name should be 'delete_assets'."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        assert tool.name == "delete_assets"

    def test_schema_has_required_parameters(self):
        """Schema should define entity_type as required."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert schema.name == "delete_assets"
        assert "entity_type" in schema.parameters["properties"]
        assert "entity_type" in schema.parameters["required"]

    def test_schema_entity_type_enum(self):
        """entity_type should be enum with valid values."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        entity_type = schema.parameters["properties"]["entity_type"]
        assert entity_type["enum"] == ["actor", "journal", "scene", "folder", "actor_item"]
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py -v`
Expected: FAIL with "No module named 'app.tools.asset_deleter'"

**Step 3: Create asset_deleter.py with schema**

Create `ui/backend/app/tools/asset_deleter.py`:

```python
"""Asset deletion tool - delete Tablewrite assets via natural language."""
import logging
from typing import List, Optional
from .base import BaseTool, ToolSchema, ToolResponse

logger = logging.getLogger(__name__)


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
        """Execute the deletion."""
        # TODO: Implement in next task
        return ToolResponse(
            type="error",
            message="Not implemented yet",
            data=None
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py -v`
Expected: PASS

**Step 5: Register tool in __init__.py**

Add to `ui/backend/app/tools/__init__.py`:

```python
from .asset_deleter import AssetDeleterTool
```

And:
```python
registry.register(AssetDeleterTool())
```

And add to `__all__`:
```python
'AssetDeleterTool',
```

**Step 6: Commit**

```bash
git add ui/backend/app/tools/asset_deleter.py \
        ui/backend/app/tools/__init__.py \
        ui/backend/tests/tools/test_asset_deleter.py
git commit -m "feat(tools): add AssetDeleterTool schema"
```

---

## Task 6: Implement Tablewrite Folder Validation

**Files:**
- Modify: `ui/backend/app/tools/asset_deleter.py`
- Test: `ui/backend/tests/tools/test_asset_deleter.py`

**Step 1: Write failing test for folder validation**

Add to `test_asset_deleter.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestTablewriteFolderValidation:
    """Test Tablewrite folder validation."""

    async def test_is_in_tablewrite_folder_with_tablewrite_actor(self, ensure_foundry_connected, test_folders):
        """Actor in Tablewrite folder should return True."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create actor in Tablewrite folder
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success

        actor_result = await push_actor({
            "name": "Test Tablewrite Actor",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success

        try:
            result = await is_in_tablewrite_folder(actor_result.uuid, "actor")
            assert result is True
        finally:
            await delete_actor(actor_result.uuid)

    async def test_is_in_tablewrite_folder_with_non_tablewrite_actor(self, ensure_foundry_connected):
        """Actor outside Tablewrite folder should return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor

        # Create actor without folder (root level)
        actor_result = await push_actor({
            "name": "Test Root Actor",
            "type": "npc"
        })
        assert actor_result.success

        try:
            result = await is_in_tablewrite_folder(actor_result.uuid, "actor")
            assert result is False
        finally:
            await delete_actor(actor_result.uuid)
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestTablewriteFolderValidation -v`
Expected: FAIL with "cannot import name 'is_in_tablewrite_folder'"

**Step 3: Implement is_in_tablewrite_folder function**

Add to `asset_deleter.py`:

```python
from app.websocket.push import (
    fetch_actor, fetch_scene, fetch_journal, list_folders
)


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
```

**Step 4: Add missing imports**

Add to imports in `asset_deleter.py`:

```python
from app.websocket.push import (
    fetch_actor, fetch_scene, fetch_journal, list_folders,
    delete_actor, delete_scene, delete_journal, delete_folder,
    list_actors, list_scenes, list_journals, remove_actor_items
)
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestTablewriteFolderValidation -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/tools/asset_deleter.py ui/backend/tests/tools/test_asset_deleter.py
git commit -m "feat(tools): add Tablewrite folder validation"
```

---

## Task 7: Implement Entity Search

**Files:**
- Modify: `ui/backend/app/tools/asset_deleter.py`
- Test: `ui/backend/tests/tools/test_asset_deleter.py`

**Step 1: Write failing test for entity search**

Add to `test_asset_deleter.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestEntitySearch:
    """Test entity search functionality."""

    async def test_find_actors_by_partial_name(self, ensure_foundry_connected, test_folders):
        """Should find actors by partial name match."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create test actor in Tablewrite
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        actor_result = await push_actor({
            "name": "Test Goblin Scout",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success

        try:
            entities = await find_entities("actor", search_query="goblin")
            assert len(entities) >= 1
            assert any(e.name == "Test Goblin Scout" for e in entities)
        finally:
            await delete_actor(actor_result.uuid)

    async def test_find_entities_filters_to_tablewrite(self, ensure_foundry_connected, test_folders):
        """Should only return entities in Tablewrite folders."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create one actor in Tablewrite, one outside
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        tablewrite_actor = await push_actor({
            "name": "Tablewrite Test Actor",
            "type": "npc",
            "folder": folder_result.folder_id
        })

        root_actor = await push_actor({
            "name": "Root Test Actor",
            "type": "npc"
        })

        try:
            entities = await find_entities("actor", search_query="test actor")
            names = [e.name for e in entities]

            assert "Tablewrite Test Actor" in names
            assert "Root Test Actor" not in names
        finally:
            await delete_actor(tablewrite_actor.uuid)
            await delete_actor(root_actor.uuid)
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestEntitySearch -v`
Expected: FAIL with "cannot import name 'find_entities'"

**Step 3: Implement find_entities function**

Add to `asset_deleter.py`:

```python
from dataclasses import dataclass


@dataclass
class EntityInfo:
    """Information about a found entity."""
    uuid: str
    name: str
    entity_type: str
    folder_id: Optional[str] = None


async def find_entities(
    entity_type: str,
    search_query: Optional[str] = None,
    uuid: Optional[str] = None,
    folder_name: Optional[str] = None
) -> List[EntityInfo]:
    """
    Find entities matching criteria, filtered to Tablewrite folders.

    Args:
        entity_type: Type of entity ("actor", "journal", "scene", "folder")
        search_query: Name to search (case-insensitive partial match), "*" for all
        uuid: Specific UUID (takes precedence over search_query)
        folder_name: Limit to specific Tablewrite subfolder

    Returns:
        List of matching EntityInfo objects
    """
    # If UUID provided, validate and return single entity
    if uuid:
        if await is_in_tablewrite_folder(uuid, entity_type):
            # Fetch to get name
            if entity_type == "actor":
                result = await fetch_actor(uuid)
            elif entity_type == "scene":
                result = await fetch_scene(uuid)
            elif entity_type == "journal":
                result = await fetch_journal(uuid)
            else:
                return []

            if result.success and result.entity:
                return [EntityInfo(
                    uuid=uuid,
                    name=result.entity.get("name", "Unknown"),
                    entity_type=entity_type,
                    folder_id=result.entity.get("folder")
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
                    return len(path) >= 2 and path[-2] == target_subfolder
                return True
            current = folder.parent
        return False

    # Filter and search
    results = []
    search_lower = search_query.lower() if search_query and search_query != "*" else None

    for entity in entities:
        # Get folder_id based on entity type
        entity_folder = getattr(entity, 'folder', None)

        # Check Tablewrite hierarchy
        if not is_in_tablewrite_hierarchy(entity_folder, folder_name):
            continue

        # Check name match
        if search_lower and search_lower not in entity.name.lower():
            continue

        results.append(EntityInfo(
            uuid=entity.uuid,
            name=entity.name,
            entity_type=entity_type,
            folder_id=entity_folder
        ))

    return results
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestEntitySearch -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/asset_deleter.py ui/backend/tests/tools/test_asset_deleter.py
git commit -m "feat(tools): add entity search with Tablewrite filtering"
```

---

## Task 8: Implement Tool Execute - Single Deletion

**Files:**
- Modify: `ui/backend/app/tools/asset_deleter.py`
- Test: `ui/backend/tests/tools/test_asset_deleter.py`

**Step 1: Write failing test for single deletion**

Add to `test_asset_deleter.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestAssetDeleterExecution:
    """Test tool execution."""

    async def test_delete_single_actor_by_name(self, ensure_foundry_connected, test_folders):
        """Should delete single actor immediately without confirmation."""
        from app.tools.asset_deleter import AssetDeleterTool
        from app.websocket.push import push_actor, fetch_actor, get_or_create_folder

        tool = AssetDeleterTool()

        # Create test actor
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        actor_result = await push_actor({
            "name": "Unique Test Goblin XYZ",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success

        # Delete by name
        response = await tool.execute(
            entity_type="actor",
            search_query="Unique Test Goblin XYZ"
        )

        assert response.type == "text"
        assert "Deleted" in response.message
        assert "Unique Test Goblin XYZ" in response.message

        # Verify actor is gone
        fetch_result = await fetch_actor(actor_result.uuid)
        assert not fetch_result.success
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestAssetDeleterExecution::test_delete_single_actor_by_name -v`
Expected: FAIL (returns "Not implemented yet")

**Step 3: Implement execute for single deletion**

Update the `execute` method in `asset_deleter.py`:

```python
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
        """Execute the deletion."""
        logger.info(f"AssetDeleterTool.execute: entity_type={entity_type}, search_query={search_query}, uuid={uuid}")

        # Handle actor_item deletion separately
        if entity_type == "actor_item":
            return await self._delete_actor_items(actor_uuid, item_names)

        # Find matching entities
        entities = await find_entities(entity_type, search_query, uuid, folder_name)

        if not entities:
            return ToolResponse(
                type="text",
                message=f"No {entity_type}s found matching '{search_query or uuid}' in Tablewrite folders.",
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

    async def _delete_entity(self, entity: EntityInfo) -> bool:
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
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter.py::TestAssetDeleterExecution::test_delete_single_actor_by_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/asset_deleter.py ui/backend/tests/tools/test_asset_deleter.py
git commit -m "feat(tools): implement AssetDeleterTool execute"
```

---

## Task 9: Integration Test - Full Chat Flow

**Files:**
- Create: `ui/backend/tests/tools/test_asset_deleter_integration.py`

**Step 1: Write comprehensive integration test**

Create `ui/backend/tests/tools/test_asset_deleter_integration.py`:

```python
"""Integration tests for AssetDeleterTool with real Foundry."""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestAssetDeleterIntegration:
    """Full integration tests with real Foundry connection."""

    async def test_delete_actor_roundtrip(self, ensure_foundry_connected, test_folders):
        """Create actor, delete via tool, verify gone."""
        from app.tools.asset_deleter import AssetDeleterTool
        from app.websocket.push import push_actor, fetch_actor, get_or_create_folder

        tool = AssetDeleterTool()

        # Create in Tablewrite
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success

        actor_result = await push_actor({
            "name": "Integration Test Goblin",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success
        actor_uuid = actor_result.uuid

        # Delete via tool
        response = await tool.execute(entity_type="actor", uuid=actor_uuid)

        assert response.type == "text"
        assert "Deleted" in response.message

        # Verify gone
        fetch_result = await fetch_actor(actor_uuid)
        assert not fetch_result.success

    async def test_bulk_delete_requires_confirmation(self, ensure_foundry_connected, test_folders):
        """Multiple actors should require confirmation."""
        from app.tools.asset_deleter import AssetDeleterTool
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        tool = AssetDeleterTool()

        # Create multiple actors
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        actors = []
        for i in range(3):
            result = await push_actor({
                "name": f"Bulk Test Actor {i}",
                "type": "npc",
                "folder": folder_result.folder_id
            })
            actors.append(result.uuid)

        try:
            # First call - should require confirmation
            response = await tool.execute(
                entity_type="actor",
                search_query="Bulk Test Actor"
            )

            assert response.type == "confirmation_required"
            assert "3" in response.message
            assert response.data["pending_deletion"]["count"] == 3

            # Second call with confirmation
            response = await tool.execute(
                entity_type="actor",
                search_query="Bulk Test Actor",
                confirm_bulk=True
            )

            assert response.type == "text"
            assert "Deleted 3" in response.message
        finally:
            # Cleanup any remaining
            for uuid in actors:
                try:
                    await delete_actor(uuid)
                except:
                    pass

    async def test_remove_actor_items_via_tool(self, ensure_foundry_connected, test_folders):
        """Remove items from actor via tool."""
        from app.tools.asset_deleter import AssetDeleterTool
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        tool = AssetDeleterTool()

        # Create actor with items
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        actor_result = await push_actor({
            "name": "Actor With Items",
            "type": "npc",
            "folder": folder_result.folder_id,
            "items": [
                {"name": "Longsword", "type": "weapon"},
                {"name": "Shield", "type": "equipment"}
            ]
        })
        assert actor_result.success

        try:
            # Remove sword via tool
            response = await tool.execute(
                entity_type="actor_item",
                actor_uuid=actor_result.uuid,
                item_names=["sword"]
            )

            assert response.type == "text"
            assert "Removed 1" in response.message
            assert "Longsword" in response.message
        finally:
            await delete_actor(actor_result.uuid)

    async def test_cannot_delete_outside_tablewrite(self, ensure_foundry_connected):
        """Should not delete actors outside Tablewrite folder."""
        from app.tools.asset_deleter import AssetDeleterTool
        from app.websocket.push import push_actor, delete_actor

        tool = AssetDeleterTool()

        # Create actor at root (no folder)
        actor_result = await push_actor({
            "name": "Root Level Actor",
            "type": "npc"
        })
        assert actor_result.success

        try:
            # Try to delete by UUID
            response = await tool.execute(
                entity_type="actor",
                uuid=actor_result.uuid
            )

            # Should not find it (not in Tablewrite)
            assert "No actors found" in response.message or response.type == "error"
        finally:
            await delete_actor(actor_result.uuid)
```

**Step 2: Run integration tests**

Run: `cd ui/backend && uv run pytest tests/tools/test_asset_deleter_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add ui/backend/tests/tools/test_asset_deleter_integration.py
git commit -m "test: add AssetDeleterTool integration tests"
```

---

## Task 10: Final Verification

**Step 1: Run full test suite**

Run: `uv run pytest --full -x`
Expected: All tests PASS

**Step 2: Manual verification**

1. Start backend: `cd ui/backend && uvicorn app.main:app --reload`
2. Ensure Foundry is connected
3. In chat: "Create a goblin"
4. In chat: "Delete the goblin"
5. Verify actor is deleted

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: chat deletion tool for Tablewrite assets

- Add list_scenes and remove_actor_items WebSocket functions
- Add handleListScenes and handleRemoveActorItems Foundry handlers
- Create AssetDeleterTool for natural language deletion
- Support actors, journals, scenes, folders, actor items
- Tablewrite folder safety constraint
- Bulk deletion confirmation flow
- Comprehensive test coverage"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add handleListScenes to Foundry | `scene.ts`, `index.ts` |
| 2 | Add list_scenes to backend | `push.py` |
| 3 | Add handleRemoveActorItems to Foundry | `actor.ts`, `index.ts` |
| 4 | Add remove_actor_items to backend | `push.py` |
| 5 | Create AssetDeleterTool schema | `asset_deleter.py`, `__init__.py` |
| 6 | Implement Tablewrite validation | `asset_deleter.py` |
| 7 | Implement entity search | `asset_deleter.py` |
| 8 | Implement execute method | `asset_deleter.py` |
| 9 | Integration tests | `test_asset_deleter_integration.py` |
| 10 | Final verification | All files |
