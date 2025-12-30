# Foundry Client Consolidation Design

> **Goal:** Consolidate Foundry client code from two locations (`src/foundry/` REST + `ui/backend/app/websocket/`) into a single async-first WebSocket client in `src/foundry/`.

**Date:** 2025-12-30

---

## Decisions

| Decision | Choice |
|----------|--------|
| Sync vs Async | Async-first, sync wrapper for scripts |
| Connection state | Singleton in `src/foundry/websocket/` |
| Relay server code | Archive (not delete) |
| Directory structure | Flat with websocket module |
| ui/backend integration | Direct imports from `src/foundry/` |

---

## New Directory Structure

```
src/foundry/
├── __init__.py              # Exports FoundryClient, run_sync
├── client.py                # Unified async FoundryClient
├── websocket/
│   ├── __init__.py          # Exports manager singleton
│   ├── manager.py           # ConnectionManager (from ui/backend)
│   └── protocol.py          # Message types, response dataclasses
├── actors/
│   ├── __init__.py
│   ├── manager.py           # ActorManager (async methods)
│   ├── converter.py         # (unchanged)
│   ├── parser.py            # (unchanged)
│   └── models.py            # (unchanged)
├── items/
│   ├── __init__.py
│   └── manager.py           # ItemManager (async search/get)
├── journals/
│   ├── __init__.py
│   └── manager.py           # JournalManager (async CRUD)
├── scenes/
│   ├── __init__.py
│   └── manager.py           # SceneManager (async CRUD)
└── _archived/               # Old relay-based code
    ├── README.md
    ├── relay_client.py
    └── relay_fetch.py

ui/backend/
├── app/
│   ├── main.py
│   ├── routers/
│   │   ├── chat.py
│   │   └── foundry.py       # REST endpoints using FoundryClient
│   ├── websocket/
│   │   └── endpoint.py      # Thin /ws/foundry route (~30 lines)
│   ├── tools/               # (unchanged, imports from foundry)
│   ├── services/            # (unchanged)
│   └── _archived/           # Old websocket code
│       ├── README.md
│       ├── push.py
│       └── connection_manager.py
```

---

## Core Components

### 1. WebSocket Manager (`src/foundry/websocket/manager.py`)

Singleton connection manager:

```python
from typing import Dict, Any, Optional
import asyncio
import uuid
from fastapi import WebSocket

class ConnectionManager:
    """Manage active WebSocket connections from Foundry clients."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}

    def connect(self, websocket: WebSocket) -> str:
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    async def broadcast_and_wait(
        self,
        message: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Broadcast message and wait for response."""
        if not self.active_connections:
            return None

        request_id = str(uuid.uuid4())
        message["request_id"] = request_id

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_requests[request_id] = future

        try:
            await self._broadcast(message)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_requests.pop(request_id, None)

    async def _broadcast(self, message: Dict[str, Any]) -> None:
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

    def handle_response(self, request_id: str, response: Dict[str, Any]) -> bool:
        future = self._pending_requests.get(request_id)
        if future and not future.done():
            future.set_result(response)
            return True
        return False

# Singleton
_manager: Optional[ConnectionManager] = None

def get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager

manager = get_manager()
```

### 2. Protocol Types (`src/foundry/websocket/protocol.py`)

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

class MessageType(str, Enum):
    # Outgoing
    ACTOR = "actor"
    JOURNAL = "journal"
    SCENE = "scene"
    SEARCH_ITEMS = "search_items"
    GET_ITEM = "get_item"
    GET_ACTOR = "get_actor"
    DELETE_ACTOR = "delete_actor"
    LIST_ACTORS = "list_actors"
    LIST_FILES = "list_files"

    # Incoming
    ACTOR_CREATED = "actor_created"
    ACTOR_DATA = "actor_data"
    ACTOR_DELETED = "actor_deleted"
    ACTORS_LIST = "actors_list"
    ACTOR_ERROR = "actor_error"
    JOURNAL_CREATED = "journal_created"
    SCENE_CREATED = "scene_created"
    ITEMS_FOUND = "items_found"
    FILES_LIST = "files_list"

@dataclass
class PushResult:
    success: bool
    uuid: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None

@dataclass
class FetchResult:
    success: bool
    entity: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class DeleteResult:
    success: bool
    uuid: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ActorInfo:
    uuid: str
    id: str
    name: str

@dataclass
class ListResult:
    success: bool
    actors: Optional[List[ActorInfo]] = None
    error: Optional[str] = None

@dataclass
class SearchResultItem:
    uuid: str
    id: str
    name: str
    type: Optional[str] = None
    img: Optional[str] = None
    pack: Optional[str] = None

@dataclass
class SearchResult:
    success: bool
    results: Optional[List[SearchResultItem]] = None
    error: Optional[str] = None

@dataclass
class FileListResult:
    success: bool
    files: Optional[List[str]] = None
    error: Optional[str] = None
```

### 3. Unified Client (`src/foundry/client.py`)

```python
from .websocket import manager
from .actors import ActorManager
from .items import ItemManager
from .journals import JournalManager
from .scenes import SceneManager

class FoundryClient:
    """Async client for FoundryVTT via WebSocket."""

    def __init__(self):
        self.actors = ActorManager(manager)
        self.items = ItemManager(manager)
        self.journals = JournalManager(manager)
        self.scenes = SceneManager(manager)

    @property
    def is_connected(self) -> bool:
        return manager.connection_count > 0

def run_sync(coro):
    """Run an async operation synchronously (for scripts)."""
    import asyncio
    return asyncio.run(coro)
```

### 4. Manager Pattern (`src/foundry/actors/manager.py`)

```python
from ..websocket import ConnectionManager
from ..websocket.protocol import MessageType, PushResult, FetchResult, DeleteResult, ListResult, ActorInfo

class ActorManager:
    def __init__(self, connection_manager: ConnectionManager):
        self._manager = connection_manager

    async def create(self, actor_data: dict, timeout: float = 30.0) -> PushResult:
        response = await self._manager.broadcast_and_wait(
            {"type": MessageType.ACTOR.value, "data": actor_data},
            timeout=timeout
        )
        return self._parse_push_response(response, "actor_created", "actor_error")

    async def get(self, uuid: str, timeout: float = 30.0) -> FetchResult:
        response = await self._manager.broadcast_and_wait(
            {"type": MessageType.GET_ACTOR.value, "data": {"uuid": uuid}},
            timeout=timeout
        )
        return self._parse_fetch_response(response)

    async def delete(self, uuid: str, timeout: float = 30.0) -> DeleteResult:
        response = await self._manager.broadcast_and_wait(
            {"type": MessageType.DELETE_ACTOR.value, "data": {"uuid": uuid}},
            timeout=timeout
        )
        return self._parse_delete_response(response)

    async def list_all(self, timeout: float = 30.0) -> ListResult:
        response = await self._manager.broadcast_and_wait(
            {"type": MessageType.LIST_ACTORS.value, "data": {}},
            timeout=timeout
        )
        return self._parse_list_response(response)

    def _parse_push_response(self, response, success_type, error_type) -> PushResult:
        if response is None:
            return PushResult(success=False, error="No connection or timeout")
        if response.get("type") == success_type:
            data = response.get("data", {})
            return PushResult(
                success=True,
                uuid=data.get("uuid"),
                id=data.get("id"),
                name=data.get("name")
            )
        return PushResult(success=False, error=response.get("error", "Unknown error"))

    def _parse_fetch_response(self, response) -> FetchResult:
        if response is None:
            return FetchResult(success=False, error="No connection or timeout")
        if response.get("type") == "actor_data":
            return FetchResult(success=True, entity=response.get("data", {}).get("entity"))
        return FetchResult(success=False, error=response.get("error", "Unknown error"))

    def _parse_delete_response(self, response) -> DeleteResult:
        if response is None:
            return DeleteResult(success=False, error="No connection or timeout")
        if response.get("type") == "actor_deleted":
            data = response.get("data", {})
            return DeleteResult(success=True, uuid=data.get("uuid"), name=data.get("name"))
        return DeleteResult(success=False, error=response.get("error", "Unknown error"))

    def _parse_list_response(self, response) -> ListResult:
        if response is None:
            return ListResult(success=False, error="No connection or timeout")
        if response.get("type") == "actors_list":
            data = response.get("data", {})
            actors = [ActorInfo(uuid=a["uuid"], id=a["id"], name=a["name"])
                      for a in data.get("actors", [])]
            return ListResult(success=True, actors=actors)
        return ListResult(success=False, error=response.get("error", "Unknown error"))
```

### 5. Thin WebSocket Endpoint (`ui/backend/app/websocket/endpoint.py`)

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from foundry.websocket import manager

router = APIRouter()

@router.websocket("/ws/foundry")
async def foundry_websocket(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await websocket.accept()
    client_id = manager.connect(websocket)

    await websocket.send_json({"type": "connected", "client_id": client_id})

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif "request_id" in data:
                manager.handle_response(data["request_id"], data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

---

## Usage Examples

### In FastAPI (async):
```python
from foundry import FoundryClient

client = FoundryClient()

@router.get("/actors")
async def list_actors():
    result = await client.actors.list_all()
    return {"actors": result.actors if result.success else [], "error": result.error}
```

### In Scripts (sync):
```python
from foundry import FoundryClient, run_sync

client = FoundryClient()
result = run_sync(client.actors.create({"name": "Goblin", "type": "npc"}))
print(f"Created: {result.uuid}")
```

---

## Files to Archive

### `src/foundry/_archived/`

| Original | Archived As | Reason |
|----------|-------------|--------|
| `src/foundry/client.py` | `relay_client.py` | Replaced by async WebSocket client |
| `src/foundry/items/fetch.py` | `relay_fetch.py` | Replaced by ItemManager |
| `src/foundry/items/websocket_fetch.py` | `websocket_fetch_legacy.py` | Had brittle sys.path imports |

### `ui/backend/app/_archived/`

| Original | Archived As | Reason |
|----------|-------------|--------|
| `ui/backend/app/websocket/push.py` | `push.py` | Logic moved to managers |
| `ui/backend/app/websocket/connection_manager.py` | `connection_manager.py` | Moved to src/foundry |

---

## Testing Strategy

### Unit Tests (mock connection manager):
```python
@pytest.mark.asyncio
async def test_create_actor():
    mock_manager = AsyncMock()
    mock_manager.broadcast_and_wait.return_value = {
        "type": "actor_created",
        "data": {"uuid": "Actor.abc123", "name": "Goblin"}
    }

    actor_mgr = ActorManager(mock_manager)
    result = await actor_mgr.create({"name": "Goblin", "type": "npc"})

    assert result.success
    assert result.uuid == "Actor.abc123"
```

### Integration Tests (require live Foundry):
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_delete_actor():
    from foundry import FoundryClient

    client = FoundryClient()
    assert client.is_connected, "Foundry not connected - start backend and connect Foundry module"

    result = await client.actors.create({"name": "Test Actor", "type": "npc"})
    assert result.success, f"Failed to create actor: {result.error}"

    delete_result = await client.actors.delete(result.uuid)
    assert delete_result.success, f"Failed to delete actor: {delete_result.error}"
```

---

## Migration Checklist

1. [ ] Create `src/foundry/websocket/` module
2. [ ] Create `src/foundry/websocket/protocol.py` with types
3. [ ] Move ConnectionManager to `src/foundry/websocket/manager.py`
4. [ ] Rewrite `src/foundry/client.py` as async
5. [ ] Update `src/foundry/actors/manager.py` to async
6. [ ] Update `src/foundry/items/manager.py` to async
7. [ ] Update `src/foundry/journals/manager.py` to async
8. [ ] Update `src/foundry/scenes/manager.py` to async
9. [ ] Archive old relay-based files
10. [ ] Slim down `ui/backend/app/websocket/` to just endpoint
11. [ ] Update `ui/backend/app/tools/` imports
12. [ ] Update `ui/backend/app/routers/foundry.py` imports
13. [ ] Update tests
14. [ ] Verify smoke tests pass
