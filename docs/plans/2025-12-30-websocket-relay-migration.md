# WebSocket Relay Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all relay server HTTP calls with WebSocket messages, enabling full functionality without the relay server.

**Architecture:** Extend the existing WebSocket protocol with new message types (`search_items`, `list_files`) handled by the Foundry module, and update Python code to use these instead of HTTP calls to the relay server.

**Tech Stack:** Python (FastAPI WebSocket), TypeScript (FoundryVTT module handlers), pytest (backend tests)

---

## Current Relay Dependencies

| File | Function | Relay Endpoint | New WebSocket Message |
|------|----------|----------------|----------------------|
| `src/foundry/items/fetch.py` | `search_query()` | `GET /search` | `search_items` |
| `src/foundry/icon_cache.py` | `load()` | `GET /file-system` | `list_files` |
| `src/foundry/client.py` | `upload_file()` | `POST /upload` | `upload_file` |
| `src/foundry/client.py` | `is_world_active()` | `GET /search` | `ping` (already exists) |

---

## Phase 1: Search Items via WebSocket

### Task 1: Add search_items Handler to Foundry Module

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/handlers/items.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`
- Modify: `foundry-module/tablewrite-assistant/types/foundry.d.ts`

**Step 1: Add Foundry type declarations for game.packs**

```typescript
// Add to foundry-module/tablewrite-assistant/types/foundry.d.ts

interface CompendiumCollection {
  get(key: string): Compendium | undefined;
  filter(fn: (pack: Compendium) => boolean): Compendium[];
}

interface Compendium {
  documentName: string;
  metadata: { label: string; packageType: string; packageName: string };
  index: { contents: CompendiumIndexEntry[] } | null;
  getIndex(options?: { fields?: string[] }): Promise<{ contents: CompendiumIndexEntry[] }>;
  getDocument(id: string): Promise<FoundryDocument | null>;
}

interface CompendiumIndexEntry {
  _id: string;
  name: string;
  type?: string;
  img?: string;
  uuid: string;
}

interface Game {
  settings: ClientSettings;
  i18n: Localization;
  actors: ActorCollection | null;
  packs: CompendiumCollection;  // Add this line
}
```

**Step 2: Create items handler**

```typescript
// foundry-module/tablewrite-assistant/src/handlers/items.ts
/**
 * Handle item search messages from backend.
 */

import type { SearchResult, SearchResultItem } from './index.js';

/**
 * Search for items in compendiums by query and optional filters.
 */
export async function handleSearchItems(data: {
  query: string;
  documentType?: string;
  subType?: string;
}): Promise<SearchResult> {
  try {
    const { query, documentType, subType } = data;
    const results: SearchResultItem[] = [];

    // Get all Item compendiums
    const packs = game.packs.filter(
      (p: Compendium) => p.documentName === (documentType || 'Item')
    );

    for (const pack of packs) {
      // Get or build index
      const index = await pack.getIndex({ fields: ['name', 'type', 'img'] });

      for (const entry of index.contents) {
        // Filter by subType if provided
        if (subType && entry.type !== subType) {
          continue;
        }

        // Filter by query (case-insensitive contains)
        if (query && !entry.name.toLowerCase().includes(query.toLowerCase())) {
          continue;
        }

        results.push({
          uuid: entry.uuid,
          id: entry._id,
          name: entry.name,
          type: entry.type,
          img: entry.img,
          pack: pack.metadata.label
        });
      }
    }

    console.log('[Tablewrite] Search returned', results.length, 'items for query:', query);

    return {
      success: true,
      results: results.slice(0, 200)  // Match relay server's 200-result limit
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to search items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Get full item data by UUID.
 */
export async function handleGetItem(uuid: string): Promise<{
  success: boolean;
  item?: Record<string, unknown>;
  error?: string;
}> {
  try {
    const item = await fromUuid(uuid);
    if (!item) {
      return { success: false, error: `Item not found: ${uuid}` };
    }
    return {
      success: true,
      item: item.toObject() as Record<string, unknown>
    };
  } catch (error) {
    return { success: false, error: String(error) };
  }
}
```

**Step 3: Add types and routing to index.ts**

```typescript
// Add to foundry-module/tablewrite-assistant/src/handlers/index.ts

// Add to imports
import { handleSearchItems, handleGetItem } from './items.js';

// Add to MessageType
export type MessageType = 'actor' | 'journal' | 'scene' | 'get_actor' | 'delete_actor' | 'list_actors' | 'search_items' | 'get_item' | 'connected' | 'pong';

// Add interfaces
export interface SearchResultItem {
  uuid: string;
  id: string;
  name: string;
  type?: string;
  img?: string;
  pack?: string;
}

export interface SearchResult {
  success: boolean;
  results?: SearchResultItem[];
  error?: string;
}

// Add to handleMessage switch statement
    case 'search_items':
      if (message.data) {
        const result = await handleSearchItems(message.data as {
          query: string;
          documentType?: string;
          subType?: string;
        });
        return {
          responseType: result.success ? 'items_found' : 'search_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
    case 'get_item':
      if (message.data?.uuid) {
        const result = await handleGetItem(message.data.uuid as string);
        return {
          responseType: result.success ? 'item_data' : 'item_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
```

**Step 4: Build module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: add search_items and get_item WebSocket handlers"
```

---

### Task 2: Add search_items to Python WebSocket Push Module

**Files:**
- Modify: `ui/backend/app/websocket/push.py`
- Modify: `ui/backend/app/websocket/__init__.py`
- Test: `ui/backend/tests/websocket/test_push.py`

**Step 1: Add search_items function to push.py**

```python
# Add to ui/backend/app/websocket/push.py

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
```

**Step 2: Export from __init__.py**

```python
# Update ui/backend/app/websocket/__init__.py
from .push import (
    push_actor, push_journal, push_scene, PushResult,
    fetch_actor, FetchResult,
    delete_actor, DeleteResult,
    list_actors, ListResult, ActorInfo,
    search_items, SearchResult, SearchResultItem  # Add these
)

__all__ = [
    # ... existing exports ...
    'search_items',
    'SearchResult',
    'SearchResultItem'
]
```

**Step 3: Commit**

```bash
git add ui/backend/app/websocket/
git commit -m "feat: add search_items WebSocket function"
```

---

### Task 3: Update SpellCache to Use WebSocket

**Files:**
- Modify: `src/foundry/actors/spell_cache.py`
- Test: `tests/foundry/actors/test_spell_cache.py`

**Step 1: Create WebSocket-based fetch function**

```python
# Create src/foundry/items/websocket_fetch.py
"""Fetch items from FoundryVTT via WebSocket."""

import asyncio
import logging
from typing import Dict, List, Optional
from string import ascii_lowercase

logger = logging.getLogger(__name__)


async def fetch_items_by_type_ws(
    item_subtype: str,
    use_two_letter_fallback: bool = True
) -> List[Dict]:
    """
    Fetch all items of a specific subtype from FoundryVTT via WebSocket.

    Uses alphabet strategy (a-z) to bypass 200-result search limit.

    Args:
        item_subtype: Item subtype to fetch (e.g., "spell", "weapon")
        use_two_letter_fallback: Use two-letter combos for queries that hit 200 limit

    Returns:
        List of item dicts with name, uuid, and other metadata
    """
    # Import here to avoid circular imports
    from ui.backend.app.websocket import search_items

    logger.info(f"Fetching all items of subtype '{item_subtype}' via WebSocket...")

    all_items = {}  # Deduplicate by UUID
    letters_at_limit = []

    # Query with each letter
    for letter in ascii_lowercase:
        result = await search_items(
            query=letter,
            document_type="Item",
            sub_type=item_subtype,
            timeout=30.0
        )

        if not result.success:
            logger.error(f"Search failed for '{letter}': {result.error}")
            continue

        # Deduplicate by UUID
        for item in result.results or []:
            all_items[item.uuid] = {
                "uuid": item.uuid,
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "img": item.img,
                "pack": item.pack
            }

        result_count = len(result.results or [])
        logger.debug(f"Letter '{letter}': {result_count} results (total unique: {len(all_items)})")

        # Track letters that hit the 200 limit
        if result_count == 200 and use_two_letter_fallback:
            letters_at_limit.append(letter)

    # For letters that hit 200, query with two-letter combinations
    if letters_at_limit:
        logger.info(f"Letters at 200 limit: {', '.join(letters_at_limit)}")
        logger.info("Querying with two-letter combinations...")

        for letter in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{letter}{second}"
                result = await search_items(
                    query=query,
                    document_type="Item",
                    sub_type=item_subtype,
                    timeout=30.0
                )

                if result.success:
                    for item in result.results or []:
                        all_items[item.uuid] = {
                            "uuid": item.uuid,
                            "id": item.id,
                            "name": item.name,
                            "type": item.type,
                            "img": item.img,
                            "pack": item.pack
                        }

    # Also try empty query
    result = await search_items(
        query="",
        document_type="Item",
        sub_type=item_subtype,
        timeout=30.0
    )
    if result.success:
        for item in result.results or []:
            all_items[item.uuid] = {
                "uuid": item.uuid,
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "img": item.img,
                "pack": item.pack
            }

    items_list = list(all_items.values())
    items_sorted = sorted(items_list, key=lambda i: i.get('name', ''))

    logger.info(f"Fetched {len(items_sorted)} unique items of subtype '{item_subtype}'")

    return items_sorted


async def fetch_all_spells_ws() -> List[Dict]:
    """Fetch all spells via WebSocket."""
    return await fetch_items_by_type_ws('spell')


def fetch_all_spells_ws_sync() -> List[Dict]:
    """Synchronous wrapper for fetch_all_spells_ws."""
    return asyncio.run(fetch_all_spells_ws())
```

**Step 2: Update SpellCache to use WebSocket**

```python
# Modify src/foundry/actors/spell_cache.py

# Add import at top
from ..items.websocket_fetch import fetch_all_spells_ws_sync

# Modify the load() method to try WebSocket first, fall back to relay
def load(
    self,
    relay_url: Optional[str] = None,
    api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    use_websocket: bool = True  # Add this parameter
) -> None:
    """
    Load all spells from FoundryVTT compendiums.

    Args:
        relay_url: Relay server URL (defaults to env var) - DEPRECATED
        api_key: API key (defaults to env var) - DEPRECATED
        client_id: Client ID (defaults to env var) - DEPRECATED
        use_websocket: If True, use WebSocket (requires running backend with Foundry connected)
    """
    logger.info("Loading spell cache from FoundryVTT...")

    spells = []

    if use_websocket:
        try:
            spells = fetch_all_spells_ws_sync()
        except Exception as e:
            logger.warning(f"WebSocket fetch failed: {e}")
            if relay_url or os.getenv("FOUNDRY_RELAY_URL"):
                logger.info("Falling back to relay server...")
                spells = fetch_all_spells(
                    relay_url=relay_url,
                    api_key=api_key,
                    client_id=client_id
                )
            else:
                raise
    else:
        # Legacy relay-based fetch
        spells = fetch_all_spells(
            relay_url=relay_url,
            api_key=api_key,
            client_id=client_id
        )

    # Build lookup dict (case-insensitive)
    for spell in spells:
        name = spell.get('name', '').lower()
        if name:
            self._spell_by_name[name] = spell

    self._loaded = True
    logger.info(f"Loaded {len(self._spell_by_name)} spells into cache")
```

**Step 3: Commit**

```bash
git add src/foundry/items/websocket_fetch.py src/foundry/actors/spell_cache.py
git commit -m "feat: update SpellCache to use WebSocket instead of relay"
```

---

## Phase 2: List Files via WebSocket

### Task 4: Add list_files Handler to Foundry Module

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/handlers/files.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`
- Modify: `foundry-module/tablewrite-assistant/types/foundry.d.ts`

**Step 1: Add Foundry type declarations for FilePicker**

```typescript
// Add to foundry-module/tablewrite-assistant/types/foundry.d.ts

interface FilePickerOptions {
  bucket?: string;
  source?: 'data' | 'public' | 's3';
  target?: string;
}

interface BrowseResult {
  target: string;
  files: string[];
  dirs: string[];
}

const FilePicker: {
  browse(
    source: 'data' | 'public' | 's3',
    target: string,
    options?: { extensions?: string[] }
  ): Promise<BrowseResult>;
};
```

**Step 2: Create files handler**

```typescript
// foundry-module/tablewrite-assistant/src/handlers/files.ts
/**
 * Handle file system browsing messages from backend.
 */

import type { FileListResult } from './index.js';

/**
 * List files in a directory using FilePicker.browse.
 */
export async function handleListFiles(data: {
  path: string;
  source?: 'data' | 'public' | 's3';
  recursive?: boolean;
  extensions?: string[];
}): Promise<FileListResult> {
  try {
    const { path, source = 'public', recursive = false, extensions } = data;

    const allFiles: string[] = [];

    async function browseDir(dirPath: string): Promise<void> {
      const result = await FilePicker.browse(source, dirPath, { extensions });

      allFiles.push(...result.files);

      if (recursive) {
        for (const subDir of result.dirs) {
          await browseDir(subDir);
        }
      }
    }

    await browseDir(path);

    console.log('[Tablewrite] Listed', allFiles.length, 'files from:', path);

    return {
      success: true,
      files: allFiles
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list files:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
```

**Step 3: Add to index.ts**

```typescript
// Add to foundry-module/tablewrite-assistant/src/handlers/index.ts

import { handleListFiles } from './files.js';

// Add to MessageType
export type MessageType = ... | 'list_files';

// Add interface
export interface FileListResult {
  success: boolean;
  files?: string[];
  error?: string;
}

// Add to handleMessage switch
    case 'list_files':
      if (message.data) {
        const result = await handleListFiles(message.data as {
          path: string;
          source?: 'data' | 'public' | 's3';
          recursive?: boolean;
          extensions?: string[];
        });
        return {
          responseType: result.success ? 'files_list' : 'files_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      break;
```

**Step 4: Build and commit**

```bash
cd foundry-module/tablewrite-assistant && npm run build
git add foundry-module/tablewrite-assistant/
git commit -m "feat: add list_files WebSocket handler"
```

---

### Task 5: Add list_files to Python WebSocket Module

**Files:**
- Modify: `ui/backend/app/websocket/push.py`
- Modify: `ui/backend/app/websocket/__init__.py`

**Step 1: Add list_files function**

```python
# Add to ui/backend/app/websocket/push.py

@dataclass
class FileListResult:
    """Result of listing files via WebSocket."""
    success: bool
    files: Optional[List[str]] = None
    error: Optional[str] = None


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
```

**Step 2: Export from __init__.py**

```python
# Update exports
from .push import (
    # ... existing ...
    list_files, FileListResult  # Add these
)
```

**Step 3: Commit**

```bash
git add ui/backend/app/websocket/
git commit -m "feat: add list_files WebSocket function"
```

---

### Task 6: Update IconCache to Use WebSocket

**Files:**
- Modify: `src/foundry/icon_cache.py`

**Step 1: Update IconCache.load() to use WebSocket**

```python
# Modify src/foundry/icon_cache.py

# Add import
import asyncio

def load(
    self,
    relay_url: Optional[str] = None,
    api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    icon_extensions: Optional[List[str]] = None,
    use_websocket: bool = True  # Add this parameter
) -> None:
    """
    Load all icon files from FoundryVTT file system.

    Args:
        use_websocket: If True, use WebSocket (requires Foundry connected)
    """
    logger.info("Loading icon cache from FoundryVTT file system...")

    icon_extensions = icon_extensions or ['.webp', '.png', '.jpg', '.svg']

    if use_websocket:
        files = self._load_via_websocket(icon_extensions)
    else:
        files = self._load_via_relay(relay_url, api_key, client_id, icon_extensions)

    for path in files:
        if any(path.endswith(ext) for ext in icon_extensions):
            self._all_icons.append(path)
            self._categorize_icon(path)

    self._loaded = True
    logger.info(f"Loaded {len(self._all_icons)} icons into cache")


def _load_via_websocket(self, extensions: List[str]) -> List[str]:
    """Load icons via WebSocket."""
    from ui.backend.app.websocket import list_files

    async def fetch():
        result = await list_files(
            path="icons",
            source="public",
            recursive=True,
            extensions=extensions,
            timeout=60.0
        )
        if not result.success:
            raise RuntimeError(f"Failed to list files: {result.error}")
        return result.files or []

    return asyncio.run(fetch())


def _load_via_relay(
    self,
    relay_url: Optional[str],
    api_key: Optional[str],
    client_id: Optional[str],
    extensions: List[str]
) -> List[str]:
    """Load icons via relay server (legacy)."""
    # ... existing relay-based code ...
```

**Step 2: Commit**

```bash
git add src/foundry/icon_cache.py
git commit -m "feat: update IconCache to use WebSocket instead of relay"
```

---

## Phase 3: Update Tests and Smoke Tests

### Task 7: Add Integration Tests for WebSocket Search

**Files:**
- Create: `ui/backend/tests/websocket/test_search_items.py`

**Step 1: Write integration test**

```python
# ui/backend/tests/websocket/test_search_items.py
"""Integration tests for search_items (requires Foundry connection)."""
import pytest
import httpx

BACKEND_URL = "http://localhost:8000"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_items_via_websocket():
    """
    Search for spells via WebSocket.

    Requires: Backend running + Foundry with Tablewrite module connected.
    """
    from app.websocket import search_items

    # First check connection
    async with httpx.AsyncClient() as client:
        status = await client.get(f"{BACKEND_URL}/api/foundry/status")
        if status.json()["status"] != "connected":
            pytest.skip("Foundry not connected")

    # Search for spells starting with "fire"
    result = await search_items(query="fire", sub_type="spell", timeout=30.0)

    assert result.success, f"Search failed: {result.error}"
    assert result.results is not None
    assert len(result.results) > 0, "Expected at least one spell matching 'fire'"

    # Verify result structure
    first = result.results[0]
    assert first.uuid is not None
    assert first.name is not None
    assert "fire" in first.name.lower()
```

**Step 2: Commit**

```bash
git add ui/backend/tests/websocket/test_search_items.py
git commit -m "test: add integration test for search_items WebSocket"
```

---

### Task 8: Update Smoke Tests

**Files:**
- Modify: `tests/actors/test_orchestrate_integration.py`

**Step 1: Ensure test uses WebSocket**

The existing test should now work with WebSocket instead of relay. Verify it passes:

```bash
cd /path/to/project
# Start backend
uvicorn ui.backend.app.main:app --reload --port 8000 &

# Refresh Foundry to reconnect
# Then run test
uv run pytest tests/actors/test_orchestrate_integration.py -v -m smoke
```

**Step 2: If test still fails, update SpellCache usage in orchestrate.py**

```python
# In src/actors/orchestrate.py, update SpellCache.load() call:
spell_cache.load(use_websocket=True)
```

**Step 3: Commit any fixes**

```bash
git add src/actors/orchestrate.py tests/
git commit -m "fix: update orchestrate to use WebSocket for SpellCache"
```

---

### Task 9: Update CLAUDE.md Documentation

**Files:**
- Modify: `ui/CLAUDE.md`

**Step 1: Update WebSocket documentation**

Add to the WebSocket section:

```markdown
### Additional WebSocket Operations

Beyond entity creation, the WebSocket supports:

**Search Items:**
```python
from app.websocket import search_items

result = await search_items(query="fire", sub_type="spell")
for item in result.results:
    print(f"{item.name}: {item.uuid}")
```

**List Files:**
```python
from app.websocket import list_files

result = await list_files(path="icons", recursive=True, extensions=[".webp", ".png"])
for file_path in result.files:
    print(file_path)
```

**Message Types:**
| Type | Direction | Description |
|------|-----------|-------------|
| `actor` | Backend → Foundry | Create actor |
| `search_items` | Backend → Foundry | Search compendiums |
| `items_found` | Foundry → Backend | Search results |
| `list_files` | Backend → Foundry | Browse file system |
| `files_list` | Foundry → Backend | File list results |
```

**Step 2: Commit**

```bash
git add ui/CLAUDE.md
git commit -m "docs: update WebSocket documentation with search and file operations"
```

---

### Task 10: Mark Relay Server as Deprecated

**Files:**
- Modify: `relay-server/ARCHIVED.md`
- Modify: `CLAUDE.md`

**Step 1: Update ARCHIVED.md**

```markdown
# Relay Server - ARCHIVED

**Status:** Deprecated as of 2025-12-30

The relay server has been fully replaced by direct WebSocket communication:

| Old (Relay) | New (WebSocket) |
|-------------|-----------------|
| `GET /search` | `search_items` message |
| `GET /file-system` | `list_files` message |
| `POST /upload` | `upload_file` message (planned) |
| All entity CRUD | Direct WebSocket handlers |

## Migration Complete

All functionality previously provided by the relay server is now available via WebSocket:
- SpellCache uses `search_items` WebSocket message
- IconCache uses `list_files` WebSocket message
- Actor/Journal/Scene creation uses direct WebSocket push

No configuration changes needed - just ensure Foundry module is connected.
```

**Step 2: Update main CLAUDE.md**

Remove relay server references from the main documentation or mark as deprecated.

**Step 3: Commit**

```bash
git add relay-server/ARCHIVED.md CLAUDE.md
git commit -m "docs: mark relay server as fully deprecated"
```

---

## Summary

**Total Tasks:** 10

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 | 1-3 | Search items via WebSocket |
| Phase 2 | 4-6 | List files via WebSocket |
| Phase 3 | 7-10 | Tests and documentation |

**Key Changes:**
1. `foundry-module/tablewrite-assistant/src/handlers/items.ts` - Search compendiums
2. `foundry-module/tablewrite-assistant/src/handlers/files.ts` - Browse file system
3. `src/foundry/items/websocket_fetch.py` - WebSocket-based item fetching
4. `src/foundry/actors/spell_cache.py` - Use WebSocket by default
5. `src/foundry/icon_cache.py` - Use WebSocket by default

**Testing:**
- Requires running backend + Foundry with Tablewrite module
- Smoke tests should pass once migration complete
